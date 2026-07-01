"""make analysis_run snapshot_id nullable

Revision ID: 0002_nullable_snapshot_id
Revises: 0001_initial_schema
Create Date: 2026-06-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_nullable_snapshot_id"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("analysis_runs") as batch_op:
        batch_op.alter_column(
            "snapshot_id",
            existing_type=sa.String(),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("analysis_runs") as batch_op:
        batch_op.alter_column(
            "snapshot_id",
            existing_type=sa.String(),
            nullable=False,
        )