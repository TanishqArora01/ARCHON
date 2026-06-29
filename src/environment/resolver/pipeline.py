from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, List, Tuple

from src.db.models import SymbolNode, SymbolEdge, UnresolvedReference, Snapshot
from src.observability.decorators import trace_and_time
from src.observability.telemetry import set_resolver_accuracy
from src.environment.resolver.stage_one_alias import AliasResolutionStage
from src.environment.resolver.stage_two_relative import RelativeImportResolutionStage
from src.environment.resolver.stage_three_package import PackageResolutionStage
from src.environment.resolver.stage_four_export import ExportResolutionStage
from src.environment.resolver.stage_five_reexport import ReExportResolutionStage
from src.environment.resolver.stage_six_symbol import SymbolResolutionStage

class SymbolResolverPipeline:
    def __init__(self):
        # The parser instances and queries have been moved to their respective stages.
        pass

    @trace_and_time("resolver_duration")
    async def execute_pipeline(self, snapshot_id: str, session: AsyncSession):
        stmt = select(SymbolNode).where(SymbolNode.snapshot_id == snapshot_id)
        result = await session.execute(stmt)
        nodes = list(result.scalars().all())
        
        # Get snapshot for repository path
        snapshot = await session.get(Snapshot, snapshot_id)
        repository_path = snapshot.repository_path if snapshot else None

        # Fast lookups
        path_to_nodes: Dict[str, List[SymbolNode]] = {}
        name_to_node: Dict[Tuple[str, str], SymbolNode] = {} # (file_path, symbol_name) -> SymbolNode
        for node in nodes:
            path_to_nodes.setdefault(node.file_path, []).append(node)
            name_to_node[(node.file_path, node.symbol_name)] = node

        new_edges = []
        new_errors = []

        # Pre-pass: Stage 1 (Alias Resolution)
        stage_one = AliasResolutionStage()
        alias_registry = stage_one.build_alias_registry(nodes)
        
        # Pass 1: Stage 2 (Relative Import Resolution)
        stage_two = RelativeImportResolutionStage()
        edges_s2, errors_s2 = stage_two.resolve(nodes, path_to_nodes, name_to_node, snapshot_id)
        new_edges.extend(edges_s2)
        new_errors.extend(errors_s2)

        # Pass 2 & 3: Stage 6 (Symbol Resolution: Calls, Inherits, Implements, Exposes)
        # Note: Stage 4 (Export Resolution) is used internally by Stage 2, which is correct
        # as relative imports must resolve against target module exports.
        stage_six = SymbolResolutionStage()
        edges_s6, errors_s6 = stage_six.resolve(nodes, name_to_node, alias_registry, snapshot_id)
        new_edges.extend(edges_s6)
        new_errors.extend(errors_s6)

        # Stage 5: Re-export Resolution
        reexport_stage = ReExportResolutionStage()
        new_edges = reexport_stage.resolve(new_edges, nodes, path_to_nodes)

        # Stage 3: Package Resolution
        package_stage = PackageResolutionStage()
        package_stage.resolve(new_errors, repository_path)

        session.add_all(new_edges)
        session.add_all(new_errors)
        await session.commit()
        
        # Calculate and record accuracy ratio
        resolved_errors = [e for e in new_errors if e.failure_category == "EXTERNAL_DEPENDENCY"]
        unresolved_errors = [e for e in new_errors if e.failure_category != "EXTERNAL_DEPENDENCY"]
        
        total_references = len(new_edges) + len(resolved_errors) + len(unresolved_errors)
        if total_references > 0:
            accuracy_ratio = (len(new_edges) + len(resolved_errors)) / total_references
        elif len(new_edges) > 0 or len(resolved_errors) > 0:
            accuracy_ratio = 1.0
        else:
            accuracy_ratio = 0.0
        set_resolver_accuracy(accuracy_ratio)
