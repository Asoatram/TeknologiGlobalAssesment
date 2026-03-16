from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.inventory import InventoryStock, InventoryTransaction


class Warehouse(Base):
    __tablename__ = "Warehouse"

    warehouse_id: Mapped[int] = mapped_column(
        "WarehouseID", primary_key=True, unique=True, index=True
    )
    name: Mapped[str] = mapped_column("Name", String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    stocks: Mapped[list["InventoryStock"]] = relationship(back_populates="warehouse")
    transactions: Mapped[list["InventoryTransaction"]] = relationship(back_populates="warehouse")
