import uuid
import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class Snapshot(Base):
    __tablename__ = "snapshots"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
    repository_path: Mapped[str | None] = mapped_column(String, nullable=True)
    repository_url: Mapped[str | None] = mapped_column(String, nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String, nullable=True)
    repository_id: Mapped[str | None] = mapped_column(ForeignKey("repositories.id"), nullable=True, index=True)
    meta_data: Mapped[dict] = mapped_column(JSON, default=dict)

    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="snapshot")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
    status: Mapped[str] = mapped_column(String, default="created", index=True)
    repository_id: Mapped[str | None] = mapped_column(ForeignKey("repositories.id"), nullable=True, index=True)
    meta_data: Mapped[dict] = mapped_column(JSON, default=dict)

    snapshot: Mapped["Snapshot"] = relationship(back_populates="analysis_runs")


class SymbolNode(Base):
    __tablename__ = "symbol_nodes"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id"))
    file_path: Mapped[str] = mapped_column(String, index=True)
    symbol_name: Mapped[str] = mapped_column(String, index=True)
    symbol_type: Mapped[str] = mapped_column(String, index=True)
    meta_data: Mapped[dict] = mapped_column(JSON)


class SymbolEdge(Base):
    __tablename__ = "symbol_edges"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id"))
    from_node_id: Mapped[str] = mapped_column(ForeignKey("symbol_nodes.id"))
    to_node_id: Mapped[str] = mapped_column(ForeignKey("symbol_nodes.id"))
    edge_type: Mapped[str] = mapped_column(String, index=True)


class UnresolvedReference(Base):
    __tablename__ = "unresolved_references"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id"))
    file_path: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    failure_category: Mapped[str] = mapped_column(String)
    literal_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_data: Mapped[dict] = mapped_column(JSON, default=dict)


class RepositoryDocument(Base):
    __tablename__ = "repository_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id"), index=True)
    file_path: Mapped[str] = mapped_column(String, index=True)
    document_type: Mapped[str] = mapped_column(String, index=True)
    content_hash: Mapped[str] = mapped_column(String, index=True)
    meta_data: Mapped[dict] = mapped_column(JSON, default=dict)


class ReviewReport(Base):
    __tablename__ = "review_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
    tracking_token: Mapped[str] = mapped_column(String, index=True)
    report: Mapped[dict] = mapped_column(JSON, default=dict)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, index=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
    meta_data: Mapped[dict] = mapped_column(JSON, default=dict)


class VCSInstallation(Base):
    __tablename__ = "vcs_installations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    provider: Mapped[str] = mapped_column(String, index=True)
    provider_account_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    installation_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    access_token_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
    meta_data: Mapped[dict] = mapped_column(JSON, default=dict)


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    installation_id: Mapped[str | None] = mapped_column(ForeignKey("vcs_installations.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String, index=True)
    owner: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    clone_url: Mapped[str] = mapped_column(String)
    default_branch: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
    meta_data: Mapped[dict] = mapped_column(JSON, default=dict)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str | None] = mapped_column(ForeignKey("tenants.id"), nullable=True, index=True)
    repository_id: Mapped[str | None] = mapped_column(ForeignKey("repositories.id"), nullable=True, index=True)
    analysis_run_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_runs.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String, default="queued", index=True)
    queue_name: Mapped[str] = mapped_column(String, default="archon:webhook:queue", index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)


class PullRequestReview(Base):
    __tablename__ = "pull_request_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"), index=True)
    analysis_run_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_runs.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String, index=True)
    pull_request_number: Mapped[int]
    head_sha: Mapped[str] = mapped_column(String, index=True)
    base_sha: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="queued", index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utc_now)
    meta_data: Mapped[dict] = mapped_column(JSON, default=dict)
