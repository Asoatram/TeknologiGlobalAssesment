"""add import documents and parsed row workflow

Revision ID: 0003_import_documents
Revises: 0002_reorder_threshold_nullable
Create Date: 2026-03-16 22:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_import_documents"
down_revision = "0002_reorder_threshold_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "Import_Document",
        sa.Column("DocumentID", sa.Integer(), nullable=False),
        sa.Column("FileName", sa.String(length=255), nullable=False),
        sa.Column("Status", sa.String(length=32), nullable=False),
        sa.Column("TotalRows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("AcceptedRows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("RejectedRows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("PendingRows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("CreatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("UpdatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            '"Status" IN (\'completed\', \'pending_confirmation\')',
            name="ck_import_document_status",
        ),
        sa.PrimaryKeyConstraint("DocumentID"),
        sa.UniqueConstraint("DocumentID"),
    )
    op.create_index("ix_Import_Document_Status", "Import_Document", ["Status"], unique=False)
    op.create_index(
        "ix_import_document_status_created_at",
        "Import_Document",
        ["Status", "CreatedAt"],
        unique=False,
    )

    op.add_column("Parsed_Item", sa.Column("DocumentID", sa.Integer(), nullable=True))
    op.add_column("Parsed_Item", sa.Column("RowNumber", sa.Integer(), nullable=True))
    op.add_column("Parsed_Item", sa.Column("WarehouseID", sa.Integer(), nullable=True))
    op.add_column("Parsed_Item", sa.Column("Warehouse", sa.String(length=255), nullable=True))
    op.add_column("Parsed_Item", sa.Column("TransactionType", sa.String(length=32), nullable=True))
    op.add_column("Parsed_Item", sa.Column("QuantityRaw", sa.String(length=64), nullable=True))
    op.add_column("Parsed_Item", sa.Column("TimestampRaw", sa.String(length=64), nullable=True))
    op.add_column("Parsed_Item", sa.Column("RowStatus", sa.String(length=32), nullable=True))
    op.add_column("Parsed_Item", sa.Column("AppliedTransactionID", sa.Integer(), nullable=True))

    op.alter_column("Parsed_Item", "Quantity", existing_type=sa.Integer(), nullable=True)

    bind = op.get_bind()
    has_rows = bool(bind.execute(sa.text('SELECT EXISTS (SELECT 1 FROM "Parsed_Item")')).scalar())
    if has_rows:
        total_rows = bind.execute(sa.text('SELECT COUNT(*) FROM "Parsed_Item"')).scalar_one()
        legacy_document_id = bind.execute(
            sa.text(
                'INSERT INTO "Import_Document" '
                '("FileName", "Status", "TotalRows", "AcceptedRows", "RejectedRows", "PendingRows") '
                'VALUES (:file_name, :status, :total_rows, :accepted_rows, :rejected_rows, :pending_rows) '
                'RETURNING "DocumentID"'
            ),
            {
                "file_name": "legacy_parsed_rows.csv",
                "status": "pending_confirmation",
                "total_rows": total_rows,
                "accepted_rows": 0,
                "rejected_rows": total_rows,
                "pending_rows": total_rows,
            },
        ).scalar_one()

        bind.execute(
            sa.text(
                'UPDATE "Parsed_Item" SET '
                '"DocumentID" = :document_id, '
                '"RowNumber" = "ParsedEventID", '
                '"QuantityRaw" = CAST("Quantity" AS TEXT), '
                '"RowStatus" = :row_status, '
                '"Message" = COALESCE("Message", :message)'
            ),
            {
                "document_id": legacy_document_id,
                "row_status": "pending_confirmation",
                "message": "Legacy parsed row migrated without source document metadata.",
            },
        )

    op.alter_column("Parsed_Item", "DocumentID", existing_type=sa.Integer(), nullable=False)
    op.alter_column("Parsed_Item", "RowNumber", existing_type=sa.Integer(), nullable=False)
    op.alter_column("Parsed_Item", "RowStatus", existing_type=sa.String(length=32), nullable=False)

    op.create_foreign_key(
        "fk_parsed_item_document",
        "Parsed_Item",
        "Import_Document",
        ["DocumentID"],
        ["DocumentID"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_parsed_item_warehouse",
        "Parsed_Item",
        "Warehouse",
        ["WarehouseID"],
        ["WarehouseID"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_parsed_item_applied_transaction",
        "Parsed_Item",
        "Inventory_Transaction",
        ["AppliedTransactionID"],
        ["TransactionID"],
        ondelete="SET NULL",
    )

    op.create_index("ix_Parsed_Item_DocumentID", "Parsed_Item", ["DocumentID"], unique=False)
    op.create_index("ix_Parsed_Item_WarehouseID", "Parsed_Item", ["WarehouseID"], unique=False)
    op.create_index("ix_Parsed_Item_RowStatus", "Parsed_Item", ["RowStatus"], unique=False)
    op.create_index(
        "ix_parsed_item_document_row_status",
        "Parsed_Item",
        ["DocumentID", "RowStatus"],
        unique=False,
    )
    op.create_index(
        "ix_Parsed_Item_AppliedTransactionID",
        "Parsed_Item",
        ["AppliedTransactionID"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_parsed_item_document_row",
        "Parsed_Item",
        ["DocumentID", "RowNumber"],
    )
    op.create_check_constraint(
        "ck_parsed_item_row_status",
        "Parsed_Item",
        '"RowStatus" IN (\'applied\', \'pending_confirmation\')',
    )


def downgrade() -> None:
    op.drop_constraint("ck_parsed_item_row_status", "Parsed_Item", type_="check")
    op.drop_constraint("uq_parsed_item_document_row", "Parsed_Item", type_="unique")
    op.drop_index("ix_Parsed_Item_AppliedTransactionID", table_name="Parsed_Item")
    op.drop_index("ix_parsed_item_document_row_status", table_name="Parsed_Item")
    op.drop_index("ix_Parsed_Item_RowStatus", table_name="Parsed_Item")
    op.drop_index("ix_Parsed_Item_WarehouseID", table_name="Parsed_Item")
    op.drop_index("ix_Parsed_Item_DocumentID", table_name="Parsed_Item")

    op.drop_constraint("fk_parsed_item_applied_transaction", "Parsed_Item", type_="foreignkey")
    op.drop_constraint("fk_parsed_item_warehouse", "Parsed_Item", type_="foreignkey")
    op.drop_constraint("fk_parsed_item_document", "Parsed_Item", type_="foreignkey")

    op.alter_column("Parsed_Item", "Quantity", existing_type=sa.Integer(), nullable=False)

    op.drop_column("Parsed_Item", "AppliedTransactionID")
    op.drop_column("Parsed_Item", "RowStatus")
    op.drop_column("Parsed_Item", "TimestampRaw")
    op.drop_column("Parsed_Item", "QuantityRaw")
    op.drop_column("Parsed_Item", "TransactionType")
    op.drop_column("Parsed_Item", "Warehouse")
    op.drop_column("Parsed_Item", "WarehouseID")
    op.drop_column("Parsed_Item", "RowNumber")
    op.drop_column("Parsed_Item", "DocumentID")

    op.drop_index("ix_import_document_status_created_at", table_name="Import_Document")
    op.drop_index("ix_Import_Document_Status", table_name="Import_Document")
    op.drop_table("Import_Document")
