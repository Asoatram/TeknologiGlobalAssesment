from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryStock, InventoryTransaction, TransactionEventType
from app.models.item import Item
from app.models.warehouse import Warehouse
from app.schemas.inventory_item_details import (
    InventoryItemDetailsResponse,
    ItemDetails,
    QuickInsight,
    StockLevelRow,
    StockOverview,
    SupplierInfo,
    TransactionHistory,
    TransactionHistoryRow,
)


def _stock_status_expr():
    return case(
        (InventoryStock.quantity_on_hand <= 0, "out_of_stock"),
        (
            and_(
                InventoryStock.reorder_threshold.is_not(None),
                InventoryStock.quantity_on_hand <= InventoryStock.reorder_threshold,
            ),
            "low_stock",
        ),
        else_="in_stock",
    )


def _build_quick_insight(session: Session, item_id: int) -> QuickInsight:
    now = datetime.now(UTC)
    last_30_start = now - timedelta(days=30)
    prev_30_start = now - timedelta(days=60)

    last_30_sales = session.execute(
        select(func.coalesce(func.sum(InventoryTransaction.quantity), 0)).where(
            InventoryTransaction.item_id == item_id,
            InventoryTransaction.event_type == TransactionEventType.SALE.value,
            InventoryTransaction.timestamp >= last_30_start,
        )
    ).scalar_one()

    prev_30_sales = session.execute(
        select(func.coalesce(func.sum(InventoryTransaction.quantity), 0)).where(
            InventoryTransaction.item_id == item_id,
            InventoryTransaction.event_type == TransactionEventType.SALE.value,
            InventoryTransaction.timestamp >= prev_30_start,
            InventoryTransaction.timestamp < last_30_start,
        )
    ).scalar_one()

    top_warehouse = session.execute(
        select(Warehouse.name, func.coalesce(func.sum(InventoryTransaction.quantity), 0).label("sales_qty"))
        .join(Warehouse, Warehouse.warehouse_id == InventoryTransaction.warehouse_id)
        .where(
            InventoryTransaction.item_id == item_id,
            InventoryTransaction.event_type == TransactionEventType.SALE.value,
            InventoryTransaction.timestamp >= last_30_start,
        )
        .group_by(Warehouse.name)
        .order_by(desc("sales_qty"), Warehouse.name.asc())
        .limit(1)
    ).first()

    if prev_30_sales > 0 and last_30_sales > prev_30_sales:
        growth = ((last_30_sales - prev_30_sales) / prev_30_sales) * 100
        warehouse_name = top_warehouse.name if top_warehouse else "highest-volume warehouse"
        return QuickInsight(
            message=(
                f"This item has seen a {growth:.1f}% increase in sales velocity over the last 30 days. "
                f"Consider reviewing reorder thresholds for {warehouse_name}."
            )
        )

    if last_30_sales == 0:
        return QuickInsight(
            message=(
                "No sale transactions were recorded for this item in the last 30 days. "
                "Review demand trends before adjusting stock policies."
            )
        )

    return QuickInsight(
        message=(
            "Sales velocity is stable compared with the previous 30-day period. "
            "Current reorder thresholds appear reasonable."
        )
    )


def get_inventory_item_details(
    session: Session,
    *,
    item_id: int,
    transaction_page: int,
    transaction_page_size: int,
) -> InventoryItemDetailsResponse:
    item = session.get(Item, item_id)
    if item is None:
        raise LookupError(f"Item {item_id} was not found.")

    stock_status = _stock_status_expr().label("stock_status")

    stock_rows = session.execute(
        select(
            Warehouse.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            InventoryStock.quantity_on_hand,
            InventoryStock.reorder_threshold,
            stock_status,
            InventoryStock.updated_at.label("last_updated"),
        )
        .join(Warehouse, Warehouse.warehouse_id == InventoryStock.warehouse_id)
        .where(InventoryStock.item_id == item_id)
        .order_by(Warehouse.name.asc())
    ).all()

    stock_levels = [
        StockLevelRow(
            warehouse_id=row.warehouse_id,
            warehouse_name=row.warehouse_name,
            quantity_on_hand=row.quantity_on_hand,
            reorder_threshold=row.reorder_threshold,
            stock_status=row.stock_status,
            last_updated=row.last_updated,
        )
        for row in stock_rows
    ]

    total_units = sum(row.quantity_on_hand for row in stock_rows)
    in_stock_warehouses = sum(1 for row in stock_rows if row.stock_status == "in_stock")
    low_stock_warehouses = sum(1 for row in stock_rows if row.stock_status == "low_stock")
    out_of_stock_warehouses = sum(1 for row in stock_rows if row.stock_status == "out_of_stock")

    total_transactions = int(
        session.execute(
            select(func.count()).where(InventoryTransaction.item_id == item_id)
        ).scalar_one()
    )
    total_pages = ceil(total_transactions / transaction_page_size) if total_transactions > 0 else 0
    offset = (transaction_page - 1) * transaction_page_size

    transaction_rows = session.execute(
        select(
            InventoryTransaction.transaction_id,
            InventoryTransaction.timestamp,
            Warehouse.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            InventoryTransaction.event_type,
            InventoryTransaction.quantity,
        )
        .join(Warehouse, Warehouse.warehouse_id == InventoryTransaction.warehouse_id)
        .where(InventoryTransaction.item_id == item_id)
        .order_by(InventoryTransaction.timestamp.desc(), InventoryTransaction.transaction_id.desc())
        .offset(offset)
        .limit(transaction_page_size)
    ).all()

    history_rows = [
        TransactionHistoryRow(
            transaction_id=row.transaction_id,
            timestamp=row.timestamp,
            warehouse_id=row.warehouse_id,
            warehouse_name=row.warehouse_name,
            event_type=row.event_type,
            quantity_change=(
                -int(row.quantity)
                if row.event_type == TransactionEventType.SALE.value
                else int(row.quantity)
            ),
        )
        for row in transaction_rows
    ]

    return InventoryItemDetailsResponse(
        item=ItemDetails(
            item_id=item.item_id,
            sku=item.sku,
            name=item.name,
            category=item.category,
        ),
        stock_overview=StockOverview(
            total_units=int(total_units),
            warehouses_count=len(stock_rows),
            in_stock_warehouses=in_stock_warehouses,
            low_stock_warehouses=low_stock_warehouses,
            out_of_stock_warehouses=out_of_stock_warehouses,
        ),
        stock_levels=stock_levels,
        transaction_history=TransactionHistory(
            page=transaction_page,
            page_size=transaction_page_size,
            total_records=total_transactions,
            total_pages=total_pages,
            records=history_rows,
        ),
        supplier_info=SupplierInfo(
            supplier_name=None,
            supplier_id=None,
            email=None,
            phone=None,
        ),
        quick_insight=_build_quick_insight(session, item_id),
    )


def get_inventory_item_details_by_sku(
    session: Session,
    *,
    sku: str,
    transaction_page: int,
    transaction_page_size: int,
) -> InventoryItemDetailsResponse:
    item_id = session.execute(select(Item.item_id).where(Item.sku == sku)).scalar_one_or_none()
    if item_id is None:
        raise LookupError(f"Item with SKU '{sku}' was not found.")
    return get_inventory_item_details(
        session,
        item_id=item_id,
        transaction_page=transaction_page,
        transaction_page_size=transaction_page_size,
    )
