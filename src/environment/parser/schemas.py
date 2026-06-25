from enum import Enum
from typing import List, Tuple
from pydantic import BaseModel, Field

class SymbolType(str, Enum):
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    IMPORT = "IMPORT"
    EXPORT = "EXPORT"
    INTERFACE = "INTERFACE"
    UNKNOWN = "UNKNOWN"

class BaseASTToken(BaseModel):
    name: str
    symbol_type: SymbolType
    literal_text: str
    line_range: Tuple[int, int]
    byte_range: Tuple[int, int]
    children: List['BaseASTToken'] = Field(default_factory=list)

class UnresolvedSyntax(BaseModel):
    kind: str
    literal_text: str
    line_range: Tuple[int, int]
    byte_range: Tuple[int, int]

class FileAnalysisSnapshot(BaseModel):
    file_path: str
    language: str
    tokens: List[BaseASTToken] = Field(default_factory=list)
    unresolved_syntax_blocks: List[UnresolvedSyntax] = Field(default_factory=list)
