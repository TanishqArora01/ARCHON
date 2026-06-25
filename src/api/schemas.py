from __future__ import annotations

from pydantic import BaseModel, Field


class RepositoryCreate(BaseModel):
    provider: str = "github"
    owner: str
    name: str
    clone_url: str
    default_branch: str | None = None


class RepositoryRead(BaseModel):
    id: str
    provider: str
    owner: str
    name: str
    clone_url: str
    default_branch: str | None = None


class ProviderRepositoryRead(BaseModel):
    provider: str
    owner: str
    name: str
    clone_url: str
    default_branch: str | None = None
    private: bool = False


class ProviderRepositoryImport(BaseModel):
    provider: str
    owner: str
    name: str
    clone_url: str
    default_branch: str | None = None


class AnalysisRunRead(BaseModel):
    id: str
    snapshot_id: str
    status: str
    repository_id: str | None = None
    meta_data: dict = Field(default_factory=dict)


class ReviewReportRead(BaseModel):
    id: str
    analysis_run_id: str
    tracking_token: str
    report: dict


class JobRead(BaseModel):
    id: str
    status: str
    repository_id: str | None = None
    analysis_run_id: str | None = None
    attempts: int
    last_error: str | None = None
    payload: dict


class SymbolNodeRead(BaseModel):
    id: str
    snapshot_id: str
    file_path: str
    symbol_name: str
    symbol_type: str
    meta_data: dict = Field(default_factory=dict)


class ImpactAnalysisResponse(BaseModel):
    impacted_nodes: list[SymbolNodeRead]
    blast_radius_score: float
