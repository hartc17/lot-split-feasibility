"""add reports table

Revision ID: b2a3f91dc017
Revises: a1f1873cc084
Create Date: 2026-06-28

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "b2a3f91dc017"
down_revision = "a1f1873cc084"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("geometry_geojson", JSONB(), nullable=False),
        sa.Column("frontage_edge_index", sa.Integer(), nullable=False),
        sa.Column("zoning_rules", JSONB(), nullable=False),
        sa.Column("result", JSONB(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("reports")
