"""Findings (condensed signals) and forced trade-off fields on persona responses.

Revision ID: 0002_findings_and_council
Revises: 0001_initial
Create Date: 2026-10-11
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_findings_and_council"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("target_model", sa.String(length=60), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=True),
        sa.Column("feature_key", sa.String(length=200), nullable=False),
        sa.Column("theme_label", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("record_ids", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("review_count", sa.Integer(), nullable=False),
        sa.Column("share_of_theme", sa.Float(), nullable=False),
        sa.Column("quotes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=True),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_findings_market", "findings", ["market"])
    op.create_index("ix_findings_feature_key", "findings", ["feature_key"])
    op.add_column("persona_responses", sa.Column("budget_points", sa.Float(), nullable=True))
    op.add_column("persona_responses", sa.Column("verdict", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("persona_responses", "verdict")
    op.drop_column("persona_responses", "budget_points")
    op.drop_index("ix_findings_feature_key", table_name="findings")
    op.drop_index("ix_findings_market", table_name="findings")
    op.drop_table("findings")
