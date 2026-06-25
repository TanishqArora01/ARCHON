from typing import Dict, List, Tuple
import tree_sitter_python as tspython
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser, Query, QueryCursor
from src.db.models import SymbolNode
from src.environment.parser.schemas import SymbolType

class AliasResolutionStage:
    def __init__(self):
        self.py_lang = Language(tspython.language())
        self.ts_lang = Language(tstypescript.language_typescript())
        self.ts_parser = Parser(self.ts_lang)
        self.py_parser = Parser(self.py_lang)
        
        self.ts_alias_query = Query(self.ts_lang, """
        (import_statement
          (import_clause
            (named_imports
              (import_specifier
                name: (identifier) @import.name
                alias: (identifier) @import.alias))))
                
        (import_statement
          (import_clause
            (namespace_import (identifier) @import.namespace)))
        """)
        
        self.py_alias_query = Query(self.py_lang, """
        (import_from_statement
          module_name: (dotted_name) @module.name
          (aliased_import
            name: (dotted_name) @import.name
            alias: (identifier) @import.alias))

        (import_statement
          (aliased_import
            name: (dotted_name) @import.name
            alias: (identifier) @import.alias))
        """)

    @staticmethod
    def _decode_text(value: bytes | None) -> str:
        return value.decode("utf-8") if value else ""

    def build_alias_registry(self, nodes: List[SymbolNode]) -> Dict[Tuple[str, str], SymbolNode]:
        """
        Builds a registry of local_name -> IMPORT SymbolNode.
        Returns a dict of (file_path, local_alias) -> SymbolNode (the IMPORT node containing it).
        """
        registry = {}
        for node in nodes:
            if node.symbol_type != SymbolType.IMPORT.value:
                continue
                
            text = node.meta_data.get("literal_text", "")
            if not text:
                continue

            if node.file_path.endswith(".py"):
                tree = self.py_parser.parse(text.encode("utf-8"))
                cursor = QueryCursor(self.py_alias_query)
                captures = cursor.captures(tree.root_node)
                
                # Check for aliased imports
                if "import.alias" in captures:
                    for alias_node in captures["import.alias"]:
                        alias_name = self._decode_text(alias_node.text)
                        registry[(node.file_path, alias_name)] = node
                        
            elif node.file_path.endswith(".ts") or node.file_path.endswith(".js"):
                tree = self.ts_parser.parse(text.encode("utf-8"))
                cursor = QueryCursor(self.ts_alias_query)
                captures = cursor.captures(tree.root_node)
                
                if "import.alias" in captures:
                    for alias_node in captures["import.alias"]:
                        alias_name = self._decode_text(alias_node.text)
                        registry[(node.file_path, alias_name)] = node
                
                if "import.namespace" in captures:
                    for ns_node in captures["import.namespace"]:
                        ns_name = self._decode_text(ns_node.text)
                        registry[(node.file_path, ns_name)] = node

        return registry
