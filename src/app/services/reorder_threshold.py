from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryStock, InventoryTransaction, TransactionEventType

WINDOW_DAYS = 30
LEAD_TIME_DAYS = 7
SAFETY_FACTOR = 1.25
NO_SALES_FLOOR = 5
MIN_WITH_SALES = 1
MAX_THRESHOLD = 500


def compute_reorder_threshold(total_sales_qty: int) -> int:
    if total_sales_qty <= 0:
        return NO_SALES_FLOOR

    avg_daily_sales = total_sales_qty / WINDOW_DAYS
    raw_threshold = ceil(avg_daily_sales * LEAD_TIME_DAYS * SAFETY_FACTOR)
    return min(max(raw_threshold, MIN_WITH_SALES), MAX_THRESHOLD)


def recalculate_reorder_threshold_for_stock(
    session: Session,
    *,
    item_id: int,
    warehouse_id: int,
    as_of: datetime | None = None,
) -> int:
    point_in_time = as_of or datetime.now(UTC)
    window_start = point_in_time - timedelta(days=WINDOW_DAYS)

    total_sales_qty = int(
        session.execute(
            select(func.coalesce(func.sum(InventoryTransaction.quantity), 0)).where(
                InventoryTransaction.item_id == item_id,
                InventoryTransaction.warehouse_id == warehouse_id,
                InventoryTransaction.event_type == TransactionEventType.SALE.value,
                InventoryTransaction.timestamp >= window_start,
            )
        ).scalar_one()
    )
    threshold = compute_reorder_threshold(total_sales_qty)

    stock = session.execute(
        select(InventoryStock)
        .where(InventoryStock.item_id == item_id, InventoryStock.warehouse_id == warehouse_id)
        .with_for_update()
    ).scalar_one_or_none()
    if stock is not None:
        stock.reorder_threshold = threshold

    return threshold


def recalculate_all_reorder_thresholds(
    session: Session,
    *,
    as_of: datetime | None = None,
) -> int:
    point_in_time = as_of or datetime.now(UTC)
    window_start = point_in_time - timedelta(days=WINDOW_DAYS)

    sales_rows = session.execute(
        select(
            InventoryTransaction.item_id,
            InventoryTransaction.warehouse_id,
            func.coalesce(func.sum(InventoryTransaction.quantity), 0).label("sales_qty"),
        )
        .where(
            InventoryTransaction.event_type == TransactionEventType.SALE.value,
            InventoryTransaction.timestamp >= window_start,
        )
        .group_by(InventoryTransaction.item_id, InventoryTransaction.warehouse_id)
    ).all()
    sales_map = {
        (row.item_id, row.warehouse_id): int(row.sales_qty)
        for row in sales_rows
    }

    stocks = session.scalars(select(InventoryStock)).all()
    for stock in stocks:
        sales_qty = sales_map.get((stock.item_id, stock.warehouse_id), 0)
        stock.reorder_threshold = compute_reorder_threshold(sales_qty)

    return len(stocks)
