import pathlib
import re
from typing import Dict, List, Tuple, Optional

import tree_sitter_python as tspython
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser, Query, QueryCursor

from src.db.models import SymbolNode, SymbolEdge, UnresolvedReference
from src.environment.parser.schemas import SymbolType
from src.environment.resolver.stage_four_export import ExportResolutionStage

def _decode(b: bytes | None) -> str:
    return b.decode("utf-8") if b else ""

class RelativeImportResolutionStage:
    def __init__(self):
        self.py_lang = Language(tspython.language())
        self.ts_lang = Language(tstypescript.language_typescript())
        self.py_parser = Parser(self.py_lang)
        self.ts_parser = Parser(self.ts_lang)

        self.py_import_query = Query(self.py_lang, """
        (import_from_statement module_name: (relative_import) @module name: (dotted_name)? @name)
        """)
        self.ts_import_query = Query(self.ts_lang, """
        (import_statement source: (string) @import.source)
        """)
        
        self.stage_four = ExportResolutionStage()

    def resolve(
        self, 
        nodes: List[SymbolNode], 
        path_to_nodes: Dict[str, List[SymbolNode]], 
        name_to_node: Dict[Tuple[str, str], SymbolNode], 
        snapshot_id: str
    ) -> Tuple[List[SymbolEdge], List[UnresolvedReference]]:
        
        new_edges = []
        new_errors = []

        for node in nodes:
            if node.symbol_type != SymbolType.IMPORT.value:
                continue
                
            ext = pathlib.Path(node.file_path).suffix
            
            if ext == ".py":
                tree = self.py_parser.parse(node.meta_data["literal_text"].encode("utf-8"))
                cursor = QueryCursor(self.py_import_query)
                captures = cursor.captures(tree.root_node)
                
                if "module" in captures:
                    rel_module = _decode(captures["module"][0].text)
                    if rel_module.startswith("."):
                        if rel_module == ".":
                            target_file = (pathlib.Path(node.file_path).parent / "__init__.py").as_posix()
                        else:
                            target_file = (pathlib.Path(node.file_path).parent / f"{rel_module[1:]}.py").as_posix()
                        
                        if "name" in captures:
                            for name_node in captures["name"]:
                                imported_name = _decode(name_node.text)
                                internal_name = self.stage_four.resolve_export_name(target_file, imported_name, path_to_nodes)
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
                            pass
                    else:
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
                    import posixpath
                    target_file = posixpath.normpath(str(pathlib.Path(node.file_path).parent / source)).replace('\\', '/')
                    if not target_file.endswith(".ts"):
                        target_file += ".ts"
                    
                    target_nodes = path_to_nodes.get(target_file, [])
                    if target_nodes:
                        for target in target_nodes:
                            if target.symbol_type in [SymbolType.CLASS.value, SymbolType.FUNCTION.value, SymbolType.EXPORT.value, SymbolType.INTERFACE.value]:
                                new_edges.append(SymbolEdge(
                                    snapshot_id=snapshot_id, from_node_id=node.id, to_node_id=target.id, edge_type="IMPORTS"
                                ))
                    else:
                        new_errors.append(UnresolvedReference(snapshot_id=snapshot_id, file_path=node.file_path, name=source, failure_category="UNRESOLVED_RELATIVE_IMPORT"))

        return new_edges, new_errors
