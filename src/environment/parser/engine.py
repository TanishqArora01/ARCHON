import aiofiles
from pathlib import Path
from typing import Dict, Tuple, Optional

import tree_sitter_python as tspython
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser, Query, QueryCursor, Node

from .schemas import BaseASTToken, SymbolType, FileAnalysisSnapshot, UnresolvedSyntax
from src.observability.decorators import trace_and_time
from dataclasses import dataclass, field as dc_field
from typing import List as _List

@dataclass
class ASTValidationResult:
    """Result of an in-memory Tree-sitter syntax check."""
    is_valid: bool
    error_nodes: _List[str] = dc_field(default_factory=list)


class ParserEngine:
    def __init__(self):
        self.py_lang = Language(tspython.language())
        self.ts_lang = Language(tstypescript.language_typescript())
        
        queries_dir = Path(__file__).parent / "queries"
        with open(queries_dir / "python.scm", "r", encoding="utf-8") as f:
            self.py_query = Query(self.py_lang, f.read())
            
        with open(queries_dir / "typescript.scm", "r", encoding="utf-8") as f:
            self.ts_query = Query(self.ts_lang, f.read())

    def _get_language_and_query(self, extension: str) -> Tuple[str, Language, Query]:
        if extension == ".py":
            return "python", self.py_lang, self.py_query
        elif extension in {".ts", ".js"}:
            return "typescript", self.ts_lang, self.ts_query
        else:
            raise ValueError(f"Unsupported extension: {extension}")

    def _calculate_complexity(self, node: Node) -> int:
        complexity = 1
        branching_types = {
            "if_statement", "for_statement", "while_statement", 
            "case_clause", "except_clause", "conditional_expression",
            "for_in_statement", "elif_clause"
        }
        
        def walk(n: Node):
            nonlocal complexity
            if n.type in branching_types:
                complexity += 1
            elif n.type == "binary_operator":
                # TypeScript/JS: &&, ||
                operator_node = n.child_by_field_name("operator")
                if operator_node and operator_node.type in ["&&", "||"]:
                    complexity += 1
            elif n.type == "boolean_operator":
                # Python: and, or
                for child in n.children:
                    if child.type in ["and", "or"]:
                        complexity += 1

            for child in n.children:
                walk(child)

        walk(node)
        return complexity

    def parse_code_string(self, code: str, language: str) -> "ASTValidationResult":
        """
        Perform an in-memory Tree-sitter syntax validation pass on a raw code string.

        This is the constitutional invariant gate — no generated code may be
        published as a patch unless it passes this check with zero ERROR / MISSING nodes.

        Parameters
        ----------
        code : str
            The code string to validate (e.g. the proposed_code_block from RemediationPlan).
        language : str
            Either ``"python"`` or ``"typescript"``.

        Returns
        -------
        ASTValidationResult
            ``is_valid=True`` when the AST is error-free; ``error_nodes`` lists
            the node types that failed (e.g. ``["ERROR", "MISSING"]``).
        """
        if language == "python":
            lang_obj = self.py_lang
        elif language in ("typescript", "javascript"):
            lang_obj = self.ts_lang
        else:
            # Unsupported language — block the patch conservatively
            return ASTValidationResult(is_valid=False, error_nodes=[f"UNSUPPORTED_LANGUAGE:{language}"])

        code_bytes = code.encode("utf-8")
        parser = Parser(lang_obj)
        tree = parser.parse(code_bytes)

        error_nodes: list[str] = []

        def _walk(node: Node) -> None:
            if node.type in ("ERROR", "MISSING"):
                snippet = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                error_nodes.append(f"{node.type}@L{node.start_point[0]}:{snippet[:40]!r}")
            for child in node.children:
                _walk(child)

        _walk(tree.root_node)

        return ASTValidationResult(is_valid=len(error_nodes) == 0, error_nodes=error_nodes)

    @trace_and_time("parse_duration")
    async def parse_repository_file(self, file_path: Path, language: str) -> FileAnalysisSnapshot:
        async with aiofiles.open(file_path, "rb") as f:
            file_bytes = await f.read()

        lang_name, lang_obj, query = self._get_language_and_query(file_path.suffix)
        
        parser = Parser(lang_obj)
        tree = parser.parse(file_bytes)
        cursor = QueryCursor(query)
        captures = cursor.captures(tree.root_node)

        node_to_token: Dict[int, BaseASTToken] = {}
        parsed_nodes = set()

        tag_to_type = {
            "class": SymbolType.CLASS,
            "function": SymbolType.FUNCTION,
            "method": SymbolType.METHOD,
            "import": SymbolType.IMPORT,
            "export": SymbolType.EXPORT,
            "interface": SymbolType.INTERFACE,
            "arrow": SymbolType.FUNCTION,
        }

        name_nodes: Dict[int, str] = {}
        for name_tag in ["class.name", "function.name", "method.name", "interface.name", "arrow.name"]:
            for node in captures.get(name_tag, []):
                if node.parent:
                    name_nodes[node.parent.id] = file_bytes[node.start_byte:node.end_byte].decode('utf-8')

        for tag_prefix, symbol_type in tag_to_type.items():
            def_nodes = captures.get(f"{tag_prefix}.def", []) + captures.get(f"{tag_prefix}.stmt", [])
            for node in def_nodes:
                parsed_nodes.add(node.id)
                name = name_nodes.get(node.id, "")
                if not name and symbol_type in (SymbolType.IMPORT, SymbolType.EXPORT):
                    name = file_bytes[node.start_byte:node.end_byte].decode('utf-8').strip()
                if not name:
                    name = f"anonymous_{node.type}"

                token = BaseASTToken(
                    name=name,
                    symbol_type=symbol_type,
                    literal_text=file_bytes[node.start_byte:node.end_byte].decode('utf-8'),
                    line_range=(node.start_point.row, node.end_point.row),
                    byte_range=(node.start_byte, node.end_byte),
                    children=[],
                    meta_data={}
                )
                if symbol_type in (SymbolType.FUNCTION, SymbolType.METHOD):
                    token.meta_data["cyclomatic_complexity"] = self._calculate_complexity(node)
                
                node_to_token[node.id] = token


        root_tokens = []
        unresolved = []

        def traverse(node: Node, current_parent: Optional[BaseASTToken]):
            token = node_to_token.get(node.id)
            is_token = token is not None
            
            if not is_token and node.type in ["expression_statement", "if_statement", "return_statement"]:
                unresolved.append(UnresolvedSyntax(
                    kind=node.type,
                    literal_text=file_bytes[node.start_byte:node.end_byte].decode('utf-8'),
                    line_range=(node.start_point.row, node.end_point.row),
                    byte_range=(node.start_byte, node.end_byte)
                ))

            new_parent = token if is_token else current_parent
            
            for child in node.children:
                traverse(child, new_parent)

            if is_token and token is not None:
                if current_parent:
                    if not any(c.name == token.name and c.byte_range == token.byte_range for c in current_parent.children):
                        current_parent.children.append(token)
                else:
                    root_tokens.append(token)

        traverse(tree.root_node, None)

        return FileAnalysisSnapshot(
            file_path=str(file_path),
            language=lang_name,
            tokens=root_tokens,
            unresolved_syntax_blocks=unresolved
        )
