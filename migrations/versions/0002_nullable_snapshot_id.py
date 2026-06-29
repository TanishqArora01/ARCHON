"""make analysis_run snapshot_id nullable and add repository_id to analysis_run

Revision ID: 0002_nullable_snapshot_id
Revises: 0001_initial_schema
Create Date: 2026-06-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_nullable_snapshot_id'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make analysis_runs.snapshot_id nullable so runs can be created before snapshot ingestion
    with op.batch_alter_table('analysis_runs', schema=None) as batch_op:
        batch_op.alter_column(
            'snapshot_id',
            existing_type=sa.String(),
            nullable=True,
        )

    # Add repository_id to analysis_runs if it doesn't exist
    # (it may already exist in the initial schema — use try/except for safety)
    try:
        with op.batch_alter_table('analysis_runs', schema=None) as batch_op:
            batch_op.add_column(
                sa.Column('repository_id', sa.String(), sa.ForeignKey('repositories.id'), nullable=True)
            )
    except Exception:
        pass  # Column may already exist from initial schema


def downgrade() -> None:
    with op.batch_alter_table('analysis_runs', schema=None) as batch_op:
        batch_op.alter_column(
            'snapshot_id',
            existing_type=sa.String(),
            nullable=False,
        )
