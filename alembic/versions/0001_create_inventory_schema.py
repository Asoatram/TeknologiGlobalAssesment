"""create inventory schema

Revision ID: 0001_create_inventory_schema
Revises:
Create Date: 2026-03-16 18:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_create_inventory_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    transaction_event_type = postgresql.ENUM(
        "restock",
        "sale",
        "adjustment",
        name="inventory_event_type",
        create_type=False,
    )
    transaction_event_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "Items",
        sa.Column("ItemID", sa.Integer(), nullable=False),
        sa.Column("SKU", sa.String(length=64), nullable=False),
        sa.Column("Name", sa.String(length=255), nullable=False),
        sa.Column("Category", sa.String(length=120), nullable=True),
        sa.PrimaryKeyConstraint("ItemID"),
        sa.UniqueConstraint("ItemID"),
        sa.UniqueConstraint("SKU"),
    )
    op.create_index("ix_Items_ItemID", "Items", ["ItemID"], unique=False)
    op.create_index("ix_Items_SKU", "Items", ["SKU"], unique=False)
    op.create_index("ix_Items_Name", "Items", ["Name"], unique=False)
    op.create_index("ix_Items_Category", "Items", ["Category"], unique=False)

    op.create_table(
        "Warehouse",
        sa.Column("WarehouseID", sa.Integer(), nullable=False),
        sa.Column("Name", sa.String(length=255), nullable=False),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("WarehouseID"),
        sa.UniqueConstraint("WarehouseID"),
        sa.UniqueConstraint("Name"),
    )
    op.create_index("ix_Warehouse_WarehouseID", "Warehouse", ["WarehouseID"], unique=False)

    op.create_table(
        "Inventory_Stock",
        sa.Column("InventoryStockID", sa.Integer(), nullable=False),
        sa.Column("ItemID", sa.Integer(), nullable=False),
        sa.Column("WarehouseID", sa.Integer(), nullable=False),
        sa.Column("Quantity_On_Hand", sa.Integer(), nullable=False),
        sa.Column("ReorderThreshold", sa.Integer(), nullable=False),
        sa.Column("UpdatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint('"Quantity_On_Hand" >= 0', name="ck_inventory_stock_non_negative"),
        sa.CheckConstraint('"ReorderThreshold" >= 0', name="ck_reorder_threshold_non_negative"),
        sa.ForeignKeyConstraint(["ItemID"], ["Items.ItemID"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["WarehouseID"], ["Warehouse.WarehouseID"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("InventoryStockID"),
        sa.UniqueConstraint("InventoryStockID"),
        sa.UniqueConstraint("ItemID", "WarehouseID", name="uq_item_warehouse_stock"),
    )
    op.create_index("ix_Inventory_Stock_ItemID", "Inventory_Stock", ["ItemID"], unique=False)
    op.create_index("ix_Inventory_Stock_WarehouseID", "Inventory_Stock", ["WarehouseID"], unique=False)
    op.create_index(
        "ix_inventory_stock_quantity_on_hand",
        "Inventory_Stock",
        ["Quantity_On_Hand"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_stock_updated_at",
        "Inventory_Stock",
        ["UpdatedAt"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_stock_warehouse_updated_at",
        "Inventory_Stock",
        ["WarehouseID", "UpdatedAt"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_stock_warehouse_quantity",
        "Inventory_Stock",
        ["WarehouseID", "Quantity_On_Hand"],
        unique=False,
    )
    op.create_index(
        "ix_Inventory_Stock_ReorderThreshold",
        "Inventory_Stock",
        ["ReorderThreshold"],
        unique=False,
    )

    op.create_table(
        "Inventory_Transaction",
        sa.Column("TransactionID", sa.Integer(), nullable=False),
        sa.Column("ItemID", sa.Integer(), nullable=False),
        sa.Column("WarehouseID", sa.Integer(), nullable=False),
        sa.Column("EventType", transaction_event_type, nullable=False),
        sa.Column("Quantity", sa.Integer(), nullable=False),
        sa.Column("Timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint('"Quantity" > 0', name="ck_transaction_quantity_positive"),
        sa.ForeignKeyConstraint(["ItemID"], ["Items.ItemID"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["WarehouseID"], ["Warehouse.WarehouseID"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("TransactionID"),
        sa.UniqueConstraint("TransactionID"),
    )
    op.create_index(
        "ix_Inventory_Transaction_ItemID", "Inventory_Transaction", ["ItemID"], unique=False
    )
    op.create_index(
        "ix_Inventory_Transaction_WarehouseID",
        "Inventory_Transaction",
        ["WarehouseID"],
        unique=False,
    )

    op.create_table(
        "Parsed_Item",
        sa.Column("ParsedEventID", sa.Integer(), nullable=False),
        sa.Column("ItemID", sa.Integer(), nullable=True),
        sa.Column("SKU", sa.String(length=64), nullable=False),
        sa.Column("Quantity", sa.Integer(), nullable=False),
        sa.Column("Message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["ItemID"], ["Items.ItemID"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("ParsedEventID"),
        sa.UniqueConstraint("ParsedEventID"),
    )
    op.create_index("ix_Parsed_Item_ItemID", "Parsed_Item", ["ItemID"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_Parsed_Item_ItemID", table_name="Parsed_Item")
    op.drop_table("Parsed_Item")

    op.drop_index("ix_Inventory_Transaction_WarehouseID", table_name="Inventory_Transaction")
    op.drop_index("ix_Inventory_Transaction_ItemID", table_name="Inventory_Transaction")
    op.drop_table("Inventory_Transaction")

    op.drop_index("ix_Inventory_Stock_ReorderThreshold", table_name="Inventory_Stock")
    op.drop_index("ix_inventory_stock_warehouse_quantity", table_name="Inventory_Stock")
    op.drop_index("ix_inventory_stock_warehouse_updated_at", table_name="Inventory_Stock")
    op.drop_index("ix_inventory_stock_updated_at", table_name="Inventory_Stock")
    op.drop_index("ix_inventory_stock_quantity_on_hand", table_name="Inventory_Stock")
    op.drop_index("ix_Inventory_Stock_WarehouseID", table_name="Inventory_Stock")
    op.drop_index("ix_Inventory_Stock_ItemID", table_name="Inventory_Stock")
    op.drop_table("Inventory_Stock")

    op.drop_index("ix_Warehouse_WarehouseID", table_name="Warehouse")
    op.drop_table("Warehouse")

    op.drop_index("ix_Items_Category", table_name="Items")
    op.drop_index("ix_Items_Name", table_name="Items")
    op.drop_index("ix_Items_SKU", table_name="Items")
    op.drop_index("ix_Items_ItemID", table_name="Items")
    op.drop_table("Items")

    postgresql.ENUM(name="inventory_event_type").drop(op.get_bind(), checkfirst=True)
