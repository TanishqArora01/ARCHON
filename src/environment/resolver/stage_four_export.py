from typing import Dict, List
import tree_sitter_python as tspython
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser, Query, QueryCursor
from src.db.models import SymbolNode

class ExportResolutionStage:
    def __init__(self):
        self.py_lang = Language(tspython.language())
        self.ts_lang = Language(tstypescript.language_typescript())
        self.ts_parser = Parser(self.ts_lang)
        self.py_parser = Parser(self.py_lang)
        
        self.ts_export_query = Query(self.ts_lang, """
        (export_statement
          (export_clause
            (export_specifier
              name: (identifier) @export.name
              alias: (identifier) @export.alias)))
              
        (export_statement
          value: (identifier) @export.default)
        """)
        
        self.py_export_query = Query(self.py_lang, """
        (assignment
          left: (identifier) @export.alias
          right: (identifier) @export.name)
        """)

    @staticmethod
    def _decode_text(value: bytes | None) -> str:
        return value.decode("utf-8") if value else ""

    def resolve_export_name(self, target_file: str, public_name: str, path_to_nodes: Dict[str, List[SymbolNode]]) -> str:
        """
        Check if the public_name is an alias exported by target_file.
        If it is, return the internal_name (e.g. what it was aliased from).
        Otherwise, return the public_name itself.
        """
        nodes = path_to_nodes.get(target_file, [])
        if not nodes:
            return public_name
            
        is_ts = target_file.endswith(".ts") or target_file.endswith(".js")
        is_py = target_file.endswith(".py")
        
        if not is_ts and not is_py:
            return public_name

        if is_ts:
            # For TS, we can just look at EXPORT nodes
            export_nodes = [n for n in nodes if n.symbol_type == "EXPORT"]
            for export_node in export_nodes:
                text = export_node.meta_data.get("literal_text", "")
                if not text:
                    continue
                tree = self.ts_parser.parse(text.encode("utf-8"))
                cursor = QueryCursor(self.ts_export_query)
                captures = cursor.captures(tree.root_node)
                
                if public_name == "default":
                    if "export.default" in captures:
                        for node in captures["export.default"]:
                            return self._decode_text(node.text)
                            
                if "export.alias" in captures and "export.name" in captures:
                    for alias_node, name_node in zip(captures["export.alias"], captures["export.name"], strict=False):
                        if self._decode_text(alias_node.text) == public_name:
                            return self._decode_text(name_node.text)

        elif is_py:
            # For Python, assignments are not natively captured as EXPORT nodes,
            # so we must parse the entire file. We can read it from disk.
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                return public_name

            tree = self.py_parser.parse(text.encode("utf-8"))
            cursor = QueryCursor(self.py_export_query)
            captures = cursor.captures(tree.root_node)
            
            if "export.alias" in captures and "export.name" in captures:
                for alias_node, name_node in zip(captures["export.alias"], captures["export.name"], strict=False):
                    if self._decode_text(alias_node.text) == public_name:
                        return self._decode_text(name_node.text)
                        
        return public_name
