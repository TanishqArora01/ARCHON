"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("meta_data", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_tenants_name"), "tenants", ["name"])
    op.create_index(op.f("ix_tenants_slug"), "tenants", ["slug"])
    op.create_table(
        "vcs_installations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("provider_account_id", sa.String(), nullable=True),
        sa.Column("installation_id", sa.String(), nullable=True),
        sa.Column("access_token_ciphertext", sa.Text(), nullable=True),
        sa.Column("refresh_token_ciphertext", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("meta_data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vcs_installations_installation_id"), "vcs_installations", ["installation_id"])
    op.create_index(op.f("ix_vcs_installations_provider"), "vcs_installations", ["provider"])
    op.create_index(op.f("ix_vcs_installations_provider_account_id"), "vcs_installations", ["provider_account_id"])
    op.create_index(op.f("ix_vcs_installations_tenant_id"), "vcs_installations", ["tenant_id"])
    op.create_table(
        "repositories",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("installation_id", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("owner", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("clone_url", sa.String(), nullable=False),
        sa.Column("default_branch", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("meta_data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["installation_id"], ["vcs_installations.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_repositories_installation_id"), "repositories", ["installation_id"])
    op.create_index(op.f("ix_repositories_name"), "repositories", ["name"])
    op.create_index(op.f("ix_repositories_owner"), "repositories", ["owner"])
    op.create_index(op.f("ix_repositories_provider"), "repositories", ["provider"])
    op.create_index(op.f("ix_repositories_tenant_id"), "repositories", ["tenant_id"])
    op.create_table(
        "snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("repository_path", sa.String(), nullable=True),
        sa.Column("repository_url", sa.String(), nullable=True),
        sa.Column("commit_sha", sa.String(), nullable=True),
        sa.Column("repository_id", sa.String(), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_snapshots_repository_id"), "snapshots", ["repository_id"])
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("snapshot_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("repository_id", sa.String(), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_runs_repository_id"), "analysis_runs", ["repository_id"])
    op.create_index(op.f("ix_analysis_runs_status"), "analysis_runs", ["status"])
    op.create_table(
        "repository_documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("snapshot_id", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("document_type", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("meta_data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_repository_documents_content_hash"), "repository_documents", ["content_hash"])
    op.create_index(op.f("ix_repository_documents_document_type"), "repository_documents", ["document_type"])
    op.create_index(op.f("ix_repository_documents_file_path"), "repository_documents", ["file_path"])
    op.create_index(op.f("ix_repository_documents_snapshot_id"), "repository_documents", ["snapshot_id"])
    op.create_table(
        "symbol_nodes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("snapshot_id", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("symbol_name", sa.String(), nullable=False),
        sa.Column("symbol_type", sa.String(), nullable=False),
        sa.Column("meta_data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_symbol_nodes_file_path"), "symbol_nodes", ["file_path"])
    op.create_index(op.f("ix_symbol_nodes_symbol_name"), "symbol_nodes", ["symbol_name"])
    op.create_index(op.f("ix_symbol_nodes_symbol_type"), "symbol_nodes", ["symbol_type"])
    op.create_table(
        "review_reports",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("analysis_run_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("tracking_token", sa.String(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_review_reports_analysis_run_id"), "review_reports", ["analysis_run_id"])
    op.create_index(op.f("ix_review_reports_tracking_token"), "review_reports", ["tracking_token"])
    op.create_table(
        "symbol_edges",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("snapshot_id", sa.String(), nullable=False),
        sa.Column("from_node_id", sa.String(), nullable=False),
        sa.Column("to_node_id", sa.String(), nullable=False),
        sa.Column("edge_type", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["from_node_id"], ["symbol_nodes.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["snapshots.id"]),
        sa.ForeignKeyConstraint(["to_node_id"], ["symbol_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_symbol_edges_edge_type"), "symbol_edges", ["edge_type"])
    op.create_table(
        "unresolved_references",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("snapshot_id", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("failure_category", sa.String(), nullable=False),
        sa.Column("literal_text", sa.Text(), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_unresolved_references_file_path"), "unresolved_references", ["file_path"])
    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("repository_id", sa.String(), nullable=True),
        sa.Column("analysis_run_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("queue_name", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"]),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_jobs_analysis_run_id"), "analysis_jobs", ["analysis_run_id"])
    op.create_index(op.f("ix_analysis_jobs_queue_name"), "analysis_jobs", ["queue_name"])
    op.create_index(op.f("ix_analysis_jobs_repository_id"), "analysis_jobs", ["repository_id"])
    op.create_index(op.f("ix_analysis_jobs_status"), "analysis_jobs", ["status"])
    op.create_index(op.f("ix_analysis_jobs_tenant_id"), "analysis_jobs", ["tenant_id"])
    op.create_table(
        "pull_request_reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("repository_id", sa.String(), nullable=False),
        sa.Column("analysis_run_id", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("pull_request_number", sa.Integer(), nullable=False),
        sa.Column("head_sha", sa.String(), nullable=False),
        sa.Column("base_sha", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("meta_data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"]),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pull_request_reviews_analysis_run_id"), "pull_request_reviews", ["analysis_run_id"])
    op.create_index(op.f("ix_pull_request_reviews_head_sha"), "pull_request_reviews", ["head_sha"])
    op.create_index(op.f("ix_pull_request_reviews_provider"), "pull_request_reviews", ["provider"])
    op.create_index(op.f("ix_pull_request_reviews_repository_id"), "pull_request_reviews", ["repository_id"])
    op.create_index(op.f("ix_pull_request_reviews_status"), "pull_request_reviews", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_pull_request_reviews_status"), table_name="pull_request_reviews")
    op.drop_index(op.f("ix_pull_request_reviews_repository_id"), table_name="pull_request_reviews")
    op.drop_index(op.f("ix_pull_request_reviews_provider"), table_name="pull_request_reviews")
    op.drop_index(op.f("ix_pull_request_reviews_head_sha"), table_name="pull_request_reviews")
    op.drop_index(op.f("ix_pull_request_reviews_analysis_run_id"), table_name="pull_request_reviews")
    op.drop_table("pull_request_reviews")
    op.drop_index(op.f("ix_analysis_jobs_tenant_id"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_status"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_repository_id"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_queue_name"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_analysis_run_id"), table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
    op.drop_index(op.f("ix_unresolved_references_file_path"), table_name="unresolved_references")
    op.drop_table("unresolved_references")
    op.drop_index(op.f("ix_symbol_edges_edge_type"), table_name="symbol_edges")
    op.drop_table("symbol_edges")
    op.drop_index(op.f("ix_review_reports_tracking_token"), table_name="review_reports")
    op.drop_index(op.f("ix_review_reports_analysis_run_id"), table_name="review_reports")
    op.drop_table("review_reports")
    op.drop_index(op.f("ix_symbol_nodes_symbol_type"), table_name="symbol_nodes")
    op.drop_index(op.f("ix_symbol_nodes_symbol_name"), table_name="symbol_nodes")
    op.drop_index(op.f("ix_symbol_nodes_file_path"), table_name="symbol_nodes")
    op.drop_table("symbol_nodes")
    op.drop_index(op.f("ix_repository_documents_snapshot_id"), table_name="repository_documents")
    op.drop_index(op.f("ix_repository_documents_file_path"), table_name="repository_documents")
    op.drop_index(op.f("ix_repository_documents_document_type"), table_name="repository_documents")
    op.drop_index(op.f("ix_repository_documents_content_hash"), table_name="repository_documents")
    op.drop_table("repository_documents")
    op.drop_index(op.f("ix_analysis_runs_repository_id"), table_name="analysis_runs")
    op.drop_index(op.f("ix_analysis_runs_status"), table_name="analysis_runs")
    op.drop_table("analysis_runs")
    op.drop_index(op.f("ix_snapshots_repository_id"), table_name="snapshots")
    op.drop_table("snapshots")
    op.drop_index(op.f("ix_repositories_tenant_id"), table_name="repositories")
    op.drop_index(op.f("ix_repositories_provider"), table_name="repositories")
    op.drop_index(op.f("ix_repositories_owner"), table_name="repositories")
    op.drop_index(op.f("ix_repositories_name"), table_name="repositories")
    op.drop_index(op.f("ix_repositories_installation_id"), table_name="repositories")
    op.drop_table("repositories")
    op.drop_index(op.f("ix_vcs_installations_tenant_id"), table_name="vcs_installations")
    op.drop_index(op.f("ix_vcs_installations_provider_account_id"), table_name="vcs_installations")
    op.drop_index(op.f("ix_vcs_installations_provider"), table_name="vcs_installations")
    op.drop_index(op.f("ix_vcs_installations_installation_id"), table_name="vcs_installations")
    op.drop_table("vcs_installations")
    op.drop_index(op.f("ix_tenants_slug"), table_name="tenants")
    op.drop_index(op.f("ix_tenants_name"), table_name="tenants")
    op.drop_table("tenants")
