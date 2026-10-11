"""Separate brand-wide (e.g. My BMW app) review counts on themes.

Revision ID: 0003_brand_wide_counts
Revises: 0002_findings_and_council
Create Date: 2026-10-11
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_brand_wide_counts"
down_revision = "0002_findings_and_council"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("themes", sa.Column("brand_review_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("themes", sa.Column("brand_record_ids", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("themes", "brand_record_ids")
    op.drop_column("themes", "brand_review_count")
