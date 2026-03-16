from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.inventory import InventoryStock
from app.models.item import Item
from app.models.warehouse import Warehouse
from app.services.inventory_import import upload_inventory_import


def test_upload_import_recalculates_reorder_threshold() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        item = Item(sku="SKU-0001", name="Demo", category="General")
        warehouse = Warehouse(name="Warehouse East")
        session.add_all([item, warehouse])
        session.flush()

        stock = InventoryStock(
            item_id=item.item_id,
            warehouse_id=warehouse.warehouse_id,
            quantity_on_hand=50,
            reorder_threshold=None,
            updated_at=datetime.now(UTC),
        )
        session.add(stock)
        session.commit()

        csv_bytes = (
            "sku,warehouse,transaction_type,quantity,timestamp\n"
            "SKU-0001,Warehouse East,sale,10,2026-03-16T10:00:00Z\n"
        ).encode("utf-8")

        response = upload_inventory_import(
            session,
            file_name="inventory.csv",
            content=csv_bytes,
        )

        updated_stock = session.execute(
            select(InventoryStock).where(
                InventoryStock.item_id == item.item_id,
                InventoryStock.warehouse_id == warehouse.warehouse_id,
            )
        ).scalar_one()

        assert response.document.accepted_rows == 1
        assert response.validation_errors == []

        # 10 sales in 30d -> avg daily 0.333 -> *7*1.25 = 2.916 -> ceil 3
        assert updated_stock.reorder_threshold == 3
