from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.item import Item
    from app.models.warehouse import Warehouse


class TransactionEventType(str, Enum):
    RESTOCK = "restock"
    SALE = "sale"
    ADJUSTMENT = "adjustment"


class ImportDocumentStatus(str, Enum):
    COMPLETED = "completed"
    PENDING_CONFIRMATION = "pending_confirmation"


class ParsedRowStatus(str, Enum):
    APPLIED = "applied"
    PENDING_CONFIRMATION = "pending_confirmation"


class InventoryStock(Base):
    __tablename__ = "Inventory_Stock"
    __table_args__ = (
        UniqueConstraint("ItemID", "WarehouseID", name="uq_item_warehouse_stock"),
        CheckConstraint('"Quantity_On_Hand" >= 0', name="ck_inventory_stock_non_negative"),
        CheckConstraint(
            '"ReorderThreshold" IS NULL OR "ReorderThreshold" >= 0',
            name="ck_reorder_threshold_non_negative",
        ),
        Index("ix_inventory_stock_quantity_on_hand", "Quantity_On_Hand"),
        Index("ix_inventory_stock_updated_at", "UpdatedAt"),
        Index("ix_inventory_stock_warehouse_updated_at", "WarehouseID", "UpdatedAt"),
        Index("ix_inventory_stock_warehouse_quantity", "WarehouseID", "Quantity_On_Hand"),
    )

    inventory_stock_id: Mapped[int] = mapped_column(
        "InventoryStockID", primary_key=True, unique=True
    )
    item_id: Mapped[int] = mapped_column(
        "ItemID",
        ForeignKey("Items.ItemID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[int] = mapped_column(
        "WarehouseID",
        ForeignKey("Warehouse.WarehouseID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity_on_hand: Mapped[int] = mapped_column(
        "Quantity_On_Hand", Integer, nullable=False, default=0
    )
    reorder_threshold: Mapped[int | None] = mapped_column(
        "ReorderThreshold", Integer, nullable=True, default=None, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        "UpdatedAt",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    item: Mapped["Item"] = relationship(back_populates="stocks")
    warehouse: Mapped["Warehouse"] = relationship(back_populates="stocks")


class InventoryTransaction(Base):
    __tablename__ = "Inventory_Transaction"
    __table_args__ = (CheckConstraint('"Quantity" > 0', name="ck_transaction_quantity_positive"),)

    transaction_id: Mapped[int] = mapped_column("TransactionID", primary_key=True, unique=True)
    item_id: Mapped[int] = mapped_column(
        "ItemID",
        ForeignKey("Items.ItemID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[int] = mapped_column(
        "WarehouseID",
        ForeignKey("Warehouse.WarehouseID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[TransactionEventType] = mapped_column(
        "EventType",
        SQLEnum(
            TransactionEventType,
            name="inventory_event_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column("Quantity", Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        "Timestamp", DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    item: Mapped["Item"] = relationship(back_populates="transactions")
    warehouse: Mapped["Warehouse"] = relationship(back_populates="transactions")


class ImportDocument(Base):
    __tablename__ = "Import_Document"
    __table_args__ = (Index("ix_import_document_status_created_at", "Status", "CreatedAt"),)

    document_id: Mapped[int] = mapped_column("DocumentID", primary_key=True, unique=True)
    file_name: Mapped[str] = mapped_column("FileName", String(255), nullable=False)
    status: Mapped[str] = mapped_column("Status", String(32), nullable=False, index=True)
    total_rows: Mapped[int] = mapped_column("TotalRows", Integer, nullable=False, default=0)
    accepted_rows: Mapped[int] = mapped_column("AcceptedRows", Integer, nullable=False, default=0)
    rejected_rows: Mapped[int] = mapped_column("RejectedRows", Integer, nullable=False, default=0)
    pending_rows: Mapped[int] = mapped_column("PendingRows", Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        "UpdatedAt",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    parsed_items: Mapped[list["ParsedItem"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class ParsedItem(Base):
    __tablename__ = "Parsed_Item"
    __table_args__ = (
        UniqueConstraint("DocumentID", "RowNumber", name="uq_parsed_item_document_row"),
        Index("ix_parsed_item_document_row_status", "DocumentID", "RowStatus"),
    )

    parsed_event_id: Mapped[int] = mapped_column("ParsedEventID", primary_key=True, unique=True)
    document_id: Mapped[int] = mapped_column(
        "DocumentID",
        ForeignKey("Import_Document.DocumentID", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_number: Mapped[int] = mapped_column("RowNumber", Integer, nullable=False)
    item_id: Mapped[int | None] = mapped_column(
        "ItemID", ForeignKey("Items.ItemID", ondelete="SET NULL"), nullable=True, index=True
    )
    warehouse_id: Mapped[int | None] = mapped_column(
        "WarehouseID",
        ForeignKey("Warehouse.WarehouseID", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sku: Mapped[str] = mapped_column("SKU", String(64), nullable=False)
    warehouse: Mapped[str | None] = mapped_column("Warehouse", String(255), nullable=True)
    transaction_type: Mapped[str | None] = mapped_column("TransactionType", String(32), nullable=True)
    quantity_raw: Mapped[str | None] = mapped_column("QuantityRaw", String(64), nullable=True)
    timestamp_raw: Mapped[str | None] = mapped_column("TimestampRaw", String(64), nullable=True)
    quantity: Mapped[int | None] = mapped_column("Quantity", Integer, nullable=True)
    row_status: Mapped[str] = mapped_column("RowStatus", String(32), nullable=False, index=True)
    applied_transaction_id: Mapped[int | None] = mapped_column(
        "AppliedTransactionID",
        ForeignKey("Inventory_Transaction.TransactionID", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    message: Mapped[str | None] = mapped_column("Message", Text, nullable=True)

    document: Mapped["ImportDocument"] = relationship(back_populates="parsed_items")
