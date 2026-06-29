from typing import List
from pydantic import BaseModel, Field

class StructuralContext(BaseModel):
    impacted_file_paths: List[str] = Field(default_factory=list)
    impacted_symbol_ids: List[str] = Field(default_factory=list)
    blast_radius_score: float = Field(default=0.0)
    choke_points: List[dict] = Field(default_factory=list)
    architecture_violations: List[dict] = Field(default_factory=list)

class SemanticContext(BaseModel):
    documentation_chunks: List[str] = Field(default_factory=list)
    relevance_scores: List[float] = Field(default_factory=list)
    source_files: List[str] = Field(default_factory=list)

class AssembledAgentContext(BaseModel):
    tracking_token: str
    repository_name: str
    query_text: str
    structural: StructuralContext
    semantic: SemanticContext
