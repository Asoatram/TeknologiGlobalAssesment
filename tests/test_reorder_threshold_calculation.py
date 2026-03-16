from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.inventory import InventoryStock, InventoryTransaction, TransactionEventType
from app.models.item import Item
from app.models.warehouse import Warehouse
from app.services.reorder_threshold import (
    compute_reorder_threshold,
    recalculate_reorder_threshold_for_stock,
)


def test_compute_reorder_threshold_no_sales_floor() -> None:
    assert compute_reorder_threshold(0) == 5


def test_compute_reorder_threshold_caps_maximum() -> None:
    assert compute_reorder_threshold(100_000) == 500


def test_recalculate_reorder_threshold_uses_recent_sales_only() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    as_of = datetime(2026, 3, 16, 12, 0, tzinfo=UTC)

    with Session(engine) as session:
        item = Item(sku="SKU-0001", name="Demo", category="General")
        warehouse = Warehouse(name="Warehouse East")
        session.add_all([item, warehouse])
        session.flush()

        stock = InventoryStock(
            item_id=item.item_id,
            warehouse_id=warehouse.warehouse_id,
            quantity_on_hand=30,
            reorder_threshold=None,
            updated_at=as_of,
        )
        session.add(stock)
        session.flush()

        session.add_all(
            [
                InventoryTransaction(
                    item_id=item.item_id,
                    warehouse_id=warehouse.warehouse_id,
                    event_type=TransactionEventType.SALE.value,
                    quantity=60,
                    timestamp=as_of - timedelta(days=10),
                ),
                InventoryTransaction(
                    item_id=item.item_id,
                    warehouse_id=warehouse.warehouse_id,
                    event_type=TransactionEventType.SALE.value,
                    quantity=100,
                    timestamp=as_of - timedelta(days=40),
                ),
                InventoryTransaction(
                    item_id=item.item_id,
                    warehouse_id=warehouse.warehouse_id,
                    event_type=TransactionEventType.ADJUSTMENT.value,
                    quantity=999,
                    timestamp=as_of - timedelta(days=5),
                ),
            ]
        )
        session.flush()

        threshold = recalculate_reorder_threshold_for_stock(
            session,
            item_id=item.item_id,
            warehouse_id=warehouse.warehouse_id,
            as_of=as_of,
        )
        session.flush()

        # 60 sales in 30d -> avg daily 2 -> 2 * 7 * 1.25 = 17.5 -> ceil 18
        assert threshold == 18
        assert stock.reorder_threshold == 18
