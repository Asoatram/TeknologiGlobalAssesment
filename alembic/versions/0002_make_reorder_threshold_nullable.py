"""make reorder threshold nullable

Revision ID: 0002_reorder_threshold_nullable
Revises: 0001_create_inventory_schema
Create Date: 2026-03-16 20:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_reorder_threshold_nullable"
down_revision = "0001_create_inventory_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_reorder_threshold_non_negative",
        "Inventory_Stock",
        type_="check",
    )
    op.alter_column(
        "Inventory_Stock",
        "ReorderThreshold",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_reorder_threshold_non_negative",
        "Inventory_Stock",
        '"ReorderThreshold" IS NULL OR "ReorderThreshold" >= 0',
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_reorder_threshold_non_negative",
        "Inventory_Stock",
        type_="check",
    )
    op.alter_column(
        "Inventory_Stock",
        "ReorderThreshold",
        existing_type=sa.Integer(),
        nullable=False,
        existing_server_default=sa.text("0"),
    )
    op.create_check_constraint(
        "ck_reorder_threshold_non_negative",
        "Inventory_Stock",
        '"ReorderThreshold" >= 0',
    )
