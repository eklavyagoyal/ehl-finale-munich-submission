"""Triage of online reviews (vehicle, engine, author, relevance) and owner counts per theme.

Revision ID: 0005_record_triage
Revises: 0004_need_count
Create Date: 2026-10-11
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_record_triage"
down_revision = "0004_need_count"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "record_triage",
        sa.Column("record_id", sa.String(length=240), sa.ForeignKey("records.record_id"), primary_key=True),
        sa.Column("target_model", sa.String(length=60), nullable=False),
        sa.Column("vehicle", sa.String(length=30), nullable=False),
        sa.Column("engine", sa.String(length=20), nullable=False),
        sa.Column("author", sa.String(length=20), nullable=False),
        sa.Column("relevant", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=True),
        sa.Column("prompt_version", sa.String(length=40), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_record_triage_vehicle", "record_triage", ["vehicle"])
    op.create_index("ix_record_triage_author", "record_triage", ["author"])
    op.create_index("ix_record_triage_relevant", "record_triage", ["relevant"])
    op.add_column("themes", sa.Column("owner_review_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("themes", "owner_review_count")
    op.drop_table("record_triage")
