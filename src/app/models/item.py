from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.inventory import InventoryStock, InventoryTransaction


class Item(Base):
    __tablename__ = "Items"

    item_id: Mapped[int] = mapped_column("ItemID", primary_key=True, unique=True, index=True)
    sku: Mapped[str] = mapped_column("SKU", String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column("Name", String(255), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column("Category", String(120), nullable=True, index=True)

    stocks: Mapped[list["InventoryStock"]] = relationship(back_populates="item")
    transactions: Mapped[list["InventoryTransaction"]] = relationship(back_populates="item")
