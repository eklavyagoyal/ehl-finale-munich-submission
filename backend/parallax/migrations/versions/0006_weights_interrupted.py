"""Weighted review counts per theme; runs killed by a restart get their own status.

Revision ID: 0006_weights_interrupted
Revises: 0005_record_triage
Create Date: 2026-10-11
"""
import sqlalchemy as sa
from alembic import op

revision = "0006_weights_interrupted"
down_revision = "0005_record_triage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("themes", sa.Column("weighted_review_count", sa.Float(), nullable=False, server_default="0"))
    op.add_column("themes", sa.Column("weighted_need_count", sa.Float(), nullable=False, server_default="0"))
    op.execute("UPDATE sim_runs SET status = 'interrupted' WHERE status = 'failed' AND error LIKE 'Interrupted:%'")


def downgrade() -> None:
    op.execute("UPDATE sim_runs SET status = 'failed' WHERE status = 'interrupted'")
    op.drop_column("themes", "weighted_need_count")
    op.drop_column("themes", "weighted_review_count")
