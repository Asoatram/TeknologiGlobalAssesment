from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryStock
from app.models.item import Item
from app.models.warehouse import Warehouse
from app.schemas.inventory_insights import (
    InsightsKpis,
    InsightsMeta,
    InventoryInsightsResponse,
    ItemsByCategoryPoint,
    LowStockByWarehousePoint,
    QuantityByCategoryPoint,
    StatusDistributionPoint,
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


def _base_filters(
    *,
    q: str | None,
    category: str | None,
    warehouse_id: int | None,
    from_date: date | None,
    to_date: date | None,
) -> list:
    filters = []
    if q:
        query = f"%{q.strip()}%"
        filters.append(or_(Item.name.ilike(query), Item.sku.ilike(query)))
    if category:
        filters.append(Item.category == category)
    if warehouse_id is not None:
        filters.append(InventoryStock.warehouse_id == warehouse_id)
    if from_date is not None:
        start = datetime.combine(from_date, time.min).replace(tzinfo=UTC)
        filters.append(InventoryStock.updated_at >= start)
    if to_date is not None:
        end = datetime.combine(to_date + timedelta(days=1), time.min).replace(tzinfo=UTC)
        filters.append(InventoryStock.updated_at < end)
    return filters


def get_inventory_insights(
    session: Session,
    *,
    q: str | None,
    category: str | None,
    warehouse_id: int | None,
    from_date: date | None,
    to_date: date | None,
) -> InventoryInsightsResponse:
    status_expr = _stock_status_expr().label("stock_status")
    filters = _base_filters(
        q=q,
        category=category,
        warehouse_id=warehouse_id,
        from_date=from_date,
        to_date=to_date,
    )

    snapshot = (
        select(
            InventoryStock.inventory_stock_id.label("stock_id"),
            InventoryStock.item_id.label("item_id"),
            Item.category.label("category"),
            InventoryStock.warehouse_id.label("warehouse_id"),
            Warehouse.name.label("warehouse_name"),
            InventoryStock.quantity_on_hand.label("quantity_on_hand"),
            status_expr,
            InventoryStock.updated_at.label("updated_at"),
        )
        .select_from(InventoryStock)
        .join(Item, Item.item_id == InventoryStock.item_id)
        .join(Warehouse, Warehouse.warehouse_id == InventoryStock.warehouse_id)
        .where(*filters)
        .subquery()
    )

    total_items = int(
        session.execute(select(func.count(func.distinct(snapshot.c.item_id)))).scalar_one()
    )
    low_stock_items = int(
        session.execute(
            select(func.count(func.distinct(snapshot.c.item_id))).where(
                snapshot.c.stock_status == "low_stock"
            )
        ).scalar_one()
    )
    out_of_stock_items = int(
        session.execute(
            select(func.count(func.distinct(snapshot.c.item_id))).where(
                snapshot.c.stock_status == "out_of_stock"
            )
        ).scalar_one()
    )

    low_stock_by_warehouse_rows = session.execute(
        select(
            snapshot.c.warehouse_id,
            snapshot.c.warehouse_name,
            func.count().label("low_stock_count"),
        )
        .where(snapshot.c.stock_status == "low_stock")
        .group_by(snapshot.c.warehouse_id, snapshot.c.warehouse_name)
        .order_by(func.count().desc(), snapshot.c.warehouse_name.asc())
    ).all()

    status_counts = session.execute(
        select(snapshot.c.stock_status, func.count().label("count"))
        .group_by(snapshot.c.stock_status)
    ).all()
    status_count_map = {status: int(count) for status, count in status_counts}
    total_status = sum(status_count_map.values())
    ordered_statuses = ("in_stock", "low_stock", "out_of_stock")
    status_distribution = [
        StatusDistributionPoint(
            status=status,
            count=status_count_map.get(status, 0),
            percentage=(
                round((status_count_map.get(status, 0) * 100.0) / total_status, 2)
                if total_status
                else 0.0
            ),
        )
        for status in ordered_statuses
    ]

    items_by_category_rows = session.execute(
        select(
            func.coalesce(snapshot.c.category, "Uncategorized").label("category"),
            func.count(func.distinct(snapshot.c.item_id)).label("sku_count"),
        )
        .group_by(snapshot.c.category)
        .order_by(func.count(func.distinct(snapshot.c.item_id)).desc())
    ).all()

    quantity_by_category_rows = session.execute(
        select(
            func.coalesce(snapshot.c.category, "Uncategorized").label("category"),
            func.coalesce(func.sum(snapshot.c.quantity_on_hand), 0).label("total_quantity"),
        )
        .group_by(snapshot.c.category)
        .order_by(func.coalesce(func.sum(snapshot.c.quantity_on_hand), 0).desc())
    ).all()

    last_sync_at = session.execute(select(func.max(snapshot.c.updated_at))).scalar_one()

    return InventoryInsightsResponse(
        kpis=InsightsKpis(
            total_items=total_items,
            low_stock_items=low_stock_items,
            out_of_stock_items=out_of_stock_items,
        ),
        low_stock_by_warehouse=[
            LowStockByWarehousePoint(
                warehouse_id=row.warehouse_id,
                warehouse_name=row.warehouse_name,
                low_stock_count=int(row.low_stock_count),
            )
            for row in low_stock_by_warehouse_rows
        ],
        status_distribution=status_distribution,
        items_by_category=[
            ItemsByCategoryPoint(category=row.category, sku_count=int(row.sku_count))
            for row in items_by_category_rows
        ],
        quantity_by_category=[
            QuantityByCategoryPoint(category=row.category, total_quantity=int(row.total_quantity))
            for row in quantity_by_category_rows
        ],
        meta=InsightsMeta(last_sync_at=last_sync_at),
    )
