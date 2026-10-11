"""Distinct reviews with a pain or a wish per theme (y axis of the signal map).

Revision ID: 0004_need_count
Revises: 0003_brand_wide_counts
Create Date: 2026-10-11
"""
import sqlalchemy as sa
from alembic import op

revision = "0004_need_count"
down_revision = "0003_brand_wide_counts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("themes", sa.Column("need_review_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("themes", "need_review_count")
