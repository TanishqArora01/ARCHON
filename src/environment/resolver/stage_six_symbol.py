import pathlib
from typing import Dict, List, Tuple, Optional

import tree_sitter_python as tspython
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser, Query, QueryCursor

from src.db.models import SymbolNode, SymbolEdge, UnresolvedReference
from src.environment.parser.schemas import SymbolType

def _decode(b: bytes | None) -> str:
    return b.decode("utf-8") if b else ""

class SymbolResolutionStage:
    def __init__(self):
        self.py_lang = Language(tspython.language())
        self.ts_lang = Language(tstypescript.language_typescript())
        self.py_parser = Parser(self.py_lang)
        self.ts_parser = Parser(self.ts_lang)

        self.py_call_query = Query(self.py_lang, """
        (call function: (identifier) @call.name)
        (call function: (attribute attribute: (identifier) @call.name))
        """)
        self.ts_call_query = Query(self.ts_lang, """
        (call_expression function: (identifier) @call.name)
        (call_expression function: (member_expression property: (property_identifier) @call.name))
        """)

        self.py_inherits_query = Query(self.py_lang, "(class_definition superclasses: (argument_list (identifier) @inherits))")
        self.ts_inherits_query = Query(self.ts_lang, """
        (class_heritage (extends_clause value: (identifier) @inherits))
        """)
        self.ts_implements_query = Query(self.ts_lang, """
        (class_heritage (implements_clause (type_identifier) @implements))
        """)

    def resolve(
        self, 
        nodes: List[SymbolNode], 
        name_to_node: Dict[Tuple[str, str], SymbolNode], 
        alias_registry: Dict[Tuple[str, str], SymbolNode],
        snapshot_id: str
    ) -> Tuple[List[SymbolEdge], List[UnresolvedReference]]:
        
        new_edges = []
        new_errors = []

        for node in nodes:
            ext = pathlib.Path(node.file_path).suffix
            
            # Resolve Calls
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
                        
                        target = name_to_node.get((node.file_path, call_name))
                        if not target:
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

            # Resolve INHERITS and IMPLEMENTS
            elif node.symbol_type == SymbolType.CLASS.value:
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
                                
            # Resolve EXPOSES
            elif node.symbol_type == SymbolType.EXPORT.value:
                file_node_id = f"{snapshot_id}::{node.file_path}::__FILE__"
                new_edges.append(SymbolEdge(
                    snapshot_id=snapshot_id, from_node_id=file_node_id, to_node_id=node.id, edge_type="EXPOSES"
                ))

        return new_edges, new_errors
