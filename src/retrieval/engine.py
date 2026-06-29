import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.analysis.debt_forecaster import TopologicalDebtForecaster
from src.architecture.drift_engine import DriftEngine
from src.architecture.rules import ArchitectureRules
from src.db.models import Snapshot
from src.graph.builder import NetworkXGraphBuilder
from src.graph.traverser import GraphImpactTraverser
from src.memory.interfaces import BaseEmbeddingProvider
from src.memory.vector_store import QdrantMemoryStore
from src.retrieval.schemas import StructuralContext, SemanticContext, AssembledAgentContext
from src.observability.decorators import trace_and_time

class HybridRetrievalEngine:
    def __init__(self, provider: BaseEmbeddingProvider):
        self.provider = provider
        self.graph_builder = NetworkXGraphBuilder()
        
    @trace_and_time("retrieval_latency")
    async def execute_fused_retrieval(
        self, 
        db_session: AsyncSession, 
        qdrant_store: QdrantMemoryStore, 
        snapshot_id: str,
        collection_name: str,
        target_symbol_id: str, 
        query_text: str,
        semantic_limit: int = 5
    ) -> AssembledAgentContext:
        """
        Executes a fused structural and semantic retrieval.
        """
        # Step 1: Structural Pass
        graph = await self.graph_builder.build_snapshot_graph(db_session, snapshot_id)
        
        impact_result = GraphImpactTraverser.calculate_blast_radius(graph, target_symbol_id)
        impacted_node_ids = impact_result["impacted_node_ids"]
        blast_score = impact_result["blast_radius_score"]
        
        # Calculate choke points for debt forecasting
        choke_points = TopologicalDebtForecaster.compute_technical_debt_index(graph)
        choke_point_dicts = [cp.model_dump(mode="json") for cp in choke_points]
        
        # Resolve file paths for impacted nodes
        impacted_file_paths = set()
        for node_id in impacted_node_ids:
            if node_id in graph:
                file_path = graph.nodes[node_id].get("file_path")
                if file_path:
                    impacted_file_paths.add(file_path)
                    
        # Include the target node's file path as well
        if target_symbol_id in graph:
            target_path = graph.nodes[target_symbol_id].get("file_path")
            if target_path:
                impacted_file_paths.add(target_path)
                
        structural_context = StructuralContext(
            impacted_file_paths=list(impacted_file_paths),
            impacted_symbol_ids=impacted_node_ids,
            blast_radius_score=blast_score,
            choke_points=choke_point_dicts,
            architecture_violations=await self._load_architecture_violations(
                db_session,
                snapshot_id,
                graph,
            ),
        )
        
        # Step 2: Semantic Pass
        query_embedding = await self.provider.embed_query(query_text)
        
        semantic_context = SemanticContext()
        
        # Query Qdrant
        search_results = await qdrant_store.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=semantic_limit,
            filter_payload={"snapshot_id": snapshot_id}
        )
            
        # Standard vector search already returns the most semantically relevant items.
        for result in search_results:
            semantic_context.documentation_chunks.append(result["text"])
            semantic_context.relevance_scores.append(result["score"])
            semantic_context.source_files.append(result["file_path"])
                
        # Resolve repository name
        repository_name = "unknown"
        snapshot_result = await db_session.execute(
            select(Snapshot).where(Snapshot.id == snapshot_id)
        )
        snapshot = snapshot_result.scalar_one_or_none()
        if snapshot and snapshot.repository_id:
            from src.db.models import Repository
            repo_result = await db_session.execute(
                select(Repository).where(Repository.id == snapshot.repository_id)
            )
            repo = repo_result.scalar_one_or_none()
            if repo:
                repository_name = repo.name

        tracking_token = str(uuid.uuid4())
        
        return AssembledAgentContext(
            tracking_token=tracking_token,
            repository_name=repository_name,
            query_text=query_text,
            structural=structural_context,
            semantic=semantic_context
        )

    async def _load_architecture_violations(
        self,
        db_session: AsyncSession,
        snapshot_id: str,
        graph,
    ) -> list[dict]:
        snapshot_result = await db_session.execute(
            select(Snapshot).where(Snapshot.id == str(snapshot_id))
        )
        snapshot = snapshot_result.scalar_one_or_none()
        if not snapshot or not snapshot.repository_path:
            return []

        rules_path = Path(snapshot.repository_path) / ".aegis" / "rules.yaml"
        rules = ArchitectureRules.load_from_file(str(rules_path))
        if not rules.components:
            return []

        violations = DriftEngine(rules).detect_drift(graph)
        return [violation.model_dump(mode="json") for violation in violations]
