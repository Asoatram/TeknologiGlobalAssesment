from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.inventory import InventoryStock
from app.models.item import Item
from app.models.warehouse import Warehouse
from app.services.inventory_dashboard import _stock_status_expr


def test_stock_status_logic_in_stock_low_stock_out_of_stock() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        warehouse = Warehouse(name="Warehouse East")
        session.add(warehouse)
        session.flush()

        in_stock_item = Item(sku="SKU-IN", name="In Stock Item", category="General")
        low_stock_item = Item(sku="SKU-LOW", name="Low Stock Item", category="General")
        out_item = Item(sku="SKU-OUT", name="Out Item", category="General")
        session.add_all([in_stock_item, low_stock_item, out_item])
        session.flush()

        session.add_all(
            [
                InventoryStock(
                    item_id=in_stock_item.item_id,
                    warehouse_id=warehouse.warehouse_id,
                    quantity_on_hand=20,
                    reorder_threshold=5,
                ),
                InventoryStock(
                    item_id=low_stock_item.item_id,
                    warehouse_id=warehouse.warehouse_id,
                    quantity_on_hand=5,
                    reorder_threshold=5,
                ),
                InventoryStock(
                    item_id=out_item.item_id,
                    warehouse_id=warehouse.warehouse_id,
                    quantity_on_hand=0,
                    reorder_threshold=5,
                ),
            ]
        )
        session.commit()

        status_expr = _stock_status_expr().label("stock_status")
        rows = session.execute(
            select(Item.sku, status_expr)
            .join(InventoryStock, InventoryStock.item_id == Item.item_id)
            .order_by(Item.sku)
        ).all()

    assert dict(rows) == {
        "SKU-IN": "in_stock",
        "SKU-LOW": "low_stock",
        "SKU-OUT": "out_of_stock",
    }
