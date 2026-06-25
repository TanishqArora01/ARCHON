import pathlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, List
import re

import tree_sitter_python as tspython
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser, Query, QueryCursor

from src.db.models import SymbolNode, SymbolEdge, UnresolvedReference
from src.environment.parser.schemas import SymbolType
from src.observability.decorators import trace_and_time
from src.observability.telemetry import set_resolver_accuracy
from src.environment.resolver.stage_three_package import PackageResolutionStage
from src.environment.resolver.stage_five_reexport import ReExportResolutionStage
from src.environment.resolver.stage_one_alias import AliasResolutionStage
from src.environment.resolver.stage_four_export import ExportResolutionStage

class SymbolResolverPipeline:
    def __init__(self):
        self.py_lang = Language(tspython.language())
        self.ts_lang = Language(tstypescript.language_typescript())
        self.py_parser = Parser(self.py_lang)
        self.ts_parser = Parser(self.ts_lang)

        # Stage 6: Call graph queries
        self.py_call_query = Query(self.py_lang, """
        (call function: (identifier) @call.name)
        (call function: (attribute attribute: (identifier) @call.name))
        """)
        self.ts_call_query = Query(self.ts_lang, """
        (call_expression function: (identifier) @call.name)
        (call_expression function: (member_expression property: (property_identifier) @call.name))
        """)

        # Stage 2: Import queries
        self.py_import_query = Query(self.py_lang, """
        (import_from_statement module_name: (relative_import) @module name: (dotted_name)? @name)
        """)
        self.ts_import_query = Query(self.ts_lang, """
        (import_statement source: (string) @import.source)
        """)

        # Stage 3: Class heritage queries
        self.py_inherits_query = Query(self.py_lang, "(class_definition superclasses: (argument_list (identifier) @inherits))")
        self.ts_inherits_query = Query(self.ts_lang, """
        (class_heritage (extends_clause value: (identifier) @inherits))
        """)
        self.ts_implements_query = Query(self.ts_lang, """
        (class_heritage (implements_clause (type_identifier) @implements))
        """)
        self.ts_import_query = Query(self.ts_lang, """
        (import_statement source: (string) @import.source)
        """)

    @trace_and_time("resolver_duration")
    async def execute_pipeline(self, snapshot_id: str, session: AsyncSession):
        stmt = select(SymbolNode).where(SymbolNode.snapshot_id == snapshot_id)
        result = await session.execute(stmt)
        nodes = list(result.scalars().all())

        # Fast lookups
        path_to_nodes: Dict[str, List[SymbolNode]] = {}
        name_to_node = {} # (file_path, symbol_name) -> SymbolNode
        for node in nodes:
            path_to_nodes.setdefault(node.file_path, []).append(node)
            name_to_node[(node.file_path, node.symbol_name)] = node

        new_edges = []
        new_errors = []

        def _decode(b: bytes | None) -> str:
            return b.decode("utf-8") if b else ""

        # Pre-pass: Stage 1 (Alias Resolution)
        stage_one = AliasResolutionStage()
        alias_registry = stage_one.build_alias_registry(nodes)
        
        # Pre-pass: Stage 4 (Export Resolution)
        stage_four = ExportResolutionStage()

        for node in nodes:
            ext = pathlib.Path(node.file_path).suffix
            
            # Pass 1: Resolve Imports
            if node.symbol_type == SymbolType.IMPORT.value:
                if ext == ".py":
                    tree = self.py_parser.parse(node.meta_data["literal_text"].encode("utf-8"))
                    cursor = QueryCursor(self.py_import_query)
                    captures = cursor.captures(tree.root_node)
                    
                    if "module" in captures:
                        rel_module = _decode(captures["module"][0].text) # e.g. ".core"
                        if rel_module.startswith("."):
                            # Resolve against the file's parent directory
                            if rel_module == ".":
                                target_file = str(pathlib.Path(node.file_path).parent / "__init__.py")
                            else:
                                target_file = str(pathlib.Path(node.file_path).parent / f"{rel_module[1:]}.py")
                            
                            # If specific names are imported: from .core import A, B
                            if "name" in captures:
                                for name_node in captures["name"]:
                                    imported_name = _decode(name_node.text)
                                    # Stage 4: Export Resolution (Map public to internal name)
                                    internal_name = stage_four.resolve_export_name(target_file, imported_name, path_to_nodes)
                                    target = name_to_node.get((target_file, internal_name))
                                    if target:
                                        new_edges.append(SymbolEdge(
                                            snapshot_id=snapshot_id, from_node_id=node.id, to_node_id=target.id, edge_type="IMPORTS"
                                        ))
                                    else:
                                        found_target = None
                                        for tn in path_to_nodes.get(target_file, []):
                                            if tn.symbol_type in [SymbolType.IMPORT.value, SymbolType.EXPORT.value]:
                                                if imported_name in tn.meta_data.get("literal_text", ""):
                                                    found_target = tn
                                                    break
                                        if found_target:
                                            new_edges.append(SymbolEdge(
                                                snapshot_id=snapshot_id, from_node_id=node.id, to_node_id=found_target.id, edge_type="IMPORTS"
                                            ))
                                        else:
                                            new_errors.append(UnresolvedReference(
                                                snapshot_id=snapshot_id, file_path=node.file_path, name=imported_name, failure_category="UNRESOLVED_RELATIVE_IMPORT"
                                            ))
                            else:
                                # Just importing the module, link to the first node in the target file as a fallback, or we would link to a module node if we tracked them
                                pass
                        else:
                            # Absolute import or a package import
                            text = node.meta_data.get("literal_text", "")
                            match = re.search(r"^(?:from|import)\s+([a-zA-Z0-9_\.]+)", text)
                            if match:
                                imported_module = match.group(1)
                                new_errors.append(UnresolvedReference(
                                    snapshot_id=snapshot_id, file_path=node.file_path, name=imported_module, failure_category="UNRESOLVED_PACKAGE"
                                ))
                    else:
                        text = node.meta_data.get("literal_text", "")
                        match = re.search(r"^(?:from|import)\s+([a-zA-Z0-9_\.]+)", text)
                        if match:
                            imported_module = match.group(1)
                            new_errors.append(UnresolvedReference(
                                snapshot_id=snapshot_id, file_path=node.file_path, name=imported_module, failure_category="UNRESOLVED_PACKAGE"
                            ))
                elif ext in [".ts", ".js"]:
                    tree = self.ts_parser.parse(node.meta_data["literal_text"].encode("utf-8"))
                    cursor = QueryCursor(self.ts_import_query)
                    captures = cursor.captures(tree.root_node)
                    if "import.source" in captures:
                        source = _decode(captures["import.source"][0].text).strip("\"'")
                        target_file = str((pathlib.Path(node.file_path).parent / source).resolve())
                        if not target_file.endswith(".ts"):
                            target_file += ".ts"
                        
                        target_nodes = path_to_nodes.get(target_file, [])
                        if target_nodes:
                            # Stage 4: Export Resolution for TypeScript (Default exports handled differently, but we can resolve named exports)
                            # Actually, for TypeScript, the original pipeline linked to ALL exports if it's a namespace import or default import.
                            # But wait, if it imports `{ Widget }`, `source` is just the file. The original code doesn't extract named imports!
                            # It just linked the file import to all exported symbols in the target file.
                            # We will keep the original fallback, but if we parsed the named imports, we could be more precise.
                            for target in target_nodes:
                                if target.symbol_type in [SymbolType.CLASS.value, SymbolType.FUNCTION.value, SymbolType.EXPORT.value, SymbolType.INTERFACE.value]:
                                    new_edges.append(SymbolEdge(
                                        snapshot_id=snapshot_id, from_node_id=node.id, to_node_id=target.id, edge_type="IMPORTS"
                                    ))
                        else:
                            new_errors.append(UnresolvedReference(snapshot_id=snapshot_id, file_path=node.file_path, name=source, failure_category="UNRESOLVED_RELATIVE_IMPORT"))

            # Pass 2: Resolve Calls
            if node.symbol_type in [SymbolType.FUNCTION.value, SymbolType.METHOD.value]:
                if ext == ".py":
                    tree = self.py_parser.parse(node.meta_data["literal_text"].encode("utf-8"))
                    cursor = QueryCursor(self.py_call_query)
                elif ext in [".ts", ".js"]:
                    tree = self.ts_parser.parse(node.meta_data["literal_text"].encode("utf-8"))
                    cursor = QueryCursor(self.ts_call_query)
                else:
                    continue
                
                captures = cursor.captures(tree.root_node)
                if "call.name" in captures:
                    for call_node in captures["call.name"]:
                        call_name = _decode(call_node.text)
                        
                        # Local resolution for now (as required by test constraints)
                        target = name_to_node.get((node.file_path, call_name))
                        if not target:
                            # Stage 1: Alias Resolution Intercept
                            alias_target_node = alias_registry.get((node.file_path, call_name))
                            if alias_target_node:
                                target = alias_target_node

                        if target:
                            new_edges.append(SymbolEdge(
                                snapshot_id=snapshot_id, from_node_id=node.id, to_node_id=target.id, edge_type="CALLS"
                            ))
                        else:
                            new_errors.append(UnresolvedReference(
                                snapshot_id=snapshot_id, file_path=node.file_path, name=call_name, failure_category="UNRESOLVED_ALIAS"
                            ))

        # Pass 3: Resolve INHERITS and IMPLEMENTS
            if node.symbol_type == SymbolType.CLASS.value:
                if ext == ".py":
                    tree = self.py_parser.parse(node.meta_data["literal_text"].encode("utf-8"))
                    cursor = QueryCursor(self.py_inherits_query)
                    captures = cursor.captures(tree.root_node)
                    if "inherits" in captures:
                        for target_node in captures["inherits"]:
                            target_name = _decode(target_node.text)
                            target = name_to_node.get((node.file_path, target_name))
                            if not target:
                                alias_target_node = alias_registry.get((node.file_path, target_name))
                                if alias_target_node:
                                    target = alias_target_node

                            if target:
                                new_edges.append(SymbolEdge(
                                    snapshot_id=snapshot_id, from_node_id=node.id, to_node_id=target.id, edge_type="INHERITS"
                                ))
                            else:
                                new_errors.append(UnresolvedReference(
                                    snapshot_id=snapshot_id, file_path=node.file_path, name=target_name, failure_category="UNRESOLVED_ALIAS"
                                ))
                elif ext in [".ts", ".js"]:
                    tree = self.ts_parser.parse(node.meta_data["literal_text"].encode("utf-8"))
                    # INHERITS
                    cursor_inherits = QueryCursor(self.ts_inherits_query)
                    captures_inherits = cursor_inherits.captures(tree.root_node)
                    if "inherits" in captures_inherits:
                        for target_node in captures_inherits["inherits"]:
                            target_name = _decode(target_node.text)
                            target = name_to_node.get((node.file_path, target_name))
                            if not target:
                                alias_target_node = alias_registry.get((node.file_path, target_name))
                                if alias_target_node:
                                    target = alias_target_node

                            if target:
                                new_edges.append(SymbolEdge(
                                    snapshot_id=snapshot_id, from_node_id=node.id, to_node_id=target.id, edge_type="INHERITS"
                                ))
                            else:
                                new_errors.append(UnresolvedReference(
                                    snapshot_id=snapshot_id, file_path=node.file_path, name=target_name, failure_category="UNRESOLVED_ALIAS"
                                ))
                    # IMPLEMENTS
                    cursor_implements = QueryCursor(self.ts_implements_query)
                    captures_implements = cursor_implements.captures(tree.root_node)
                    if "implements" in captures_implements:
                        for target_node in captures_implements["implements"]:
                            target_name = _decode(target_node.text)
                            target = name_to_node.get((node.file_path, target_name))
                            if not target:
                                alias_target_node = alias_registry.get((node.file_path, target_name))
                                if alias_target_node:
                                    target = alias_target_node

                            if target:
                                new_edges.append(SymbolEdge(
                                    snapshot_id=snapshot_id, from_node_id=node.id, to_node_id=target.id, edge_type="IMPLEMENTS"
                                ))
                            else:
                                new_errors.append(UnresolvedReference(
                                    snapshot_id=snapshot_id, file_path=node.file_path, name=target_name, failure_category="UNRESOLVED_ALIAS"
                                ))
                                
            # Pass 4: Resolve EXPOSES
            if node.symbol_type == SymbolType.EXPORT.value:
                file_node_id = f"{snapshot_id}::{node.file_path}::__FILE__"
                # To be precise, EXPORT symbol nodes wrap another node, but for now we just link the FILE to this EXPORT node
                new_edges.append(SymbolEdge(
                    snapshot_id=snapshot_id, from_node_id=file_node_id, to_node_id=node.id, edge_type="EXPOSES"
                ))

        # Stage 5: Re-export Resolution
        reexport_stage = ReExportResolutionStage()
        new_edges = reexport_stage.resolve(new_edges, nodes, path_to_nodes)

        # Stage 3: Package Resolution
        package_stage = PackageResolutionStage()
        package_stage.resolve(new_errors)

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
