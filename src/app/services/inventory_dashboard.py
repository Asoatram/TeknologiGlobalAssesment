from __future__ import annotations

from math import ceil

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryStock
from app.models.item import Item
from app.models.warehouse import Warehouse
from app.schemas.inventory_dashboard import (
    DashboardFilters,
    DashboardItem,
    DashboardPagination,
    DashboardSummary,
    InventoryDashboardResponse,
    WarehouseOption,
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


def _base_filters(q: str | None, category: str | None, warehouse_id: int | None) -> list:
    filters = []
    if q:
        query = f"%{q.strip()}%"
        filters.append(or_(Item.name.ilike(query), Item.sku.ilike(query)))
    if category:
        filters.append(Item.category == category)
    if warehouse_id is not None:
        filters.append(InventoryStock.warehouse_id == warehouse_id)
    return filters


def _build_summary(session: Session, filters: list) -> DashboardSummary:
    out_of_stock_count = func.sum(case((InventoryStock.quantity_on_hand <= 0, 1), else_=0))
    low_stock_count = func.sum(
        case(
            (
                and_(
                    InventoryStock.quantity_on_hand > 0,
                    InventoryStock.reorder_threshold.is_not(None),
                    InventoryStock.quantity_on_hand <= InventoryStock.reorder_threshold,
                ),
                1,
            ),
            else_=0,
        )
    )
    in_stock_count = func.sum(
        case(
            (
                and_(
                    InventoryStock.quantity_on_hand > 0,
                    or_(
                        InventoryStock.reorder_threshold.is_(None),
                        InventoryStock.quantity_on_hand > InventoryStock.reorder_threshold,
                    ),
                ),
                1,
            ),
            else_=0,
        )
    )

    stmt = (
        select(
            func.coalesce(in_stock_count, 0),
            func.coalesce(out_of_stock_count, 0),
            func.coalesce(low_stock_count, 0),
        )
        .select_from(InventoryStock)
        .join(Item, Item.item_id == InventoryStock.item_id)
        .where(*filters)
    )
    in_stock, out_of_stock, low_stock = session.execute(stmt).one()
    return DashboardSummary(
        in_stock_count=int(in_stock),
        out_of_stock_count=int(out_of_stock),
        low_stock_count=int(low_stock),
    )


def _build_filter_options(session: Session) -> DashboardFilters:
    categories = session.scalars(
        select(Item.category).where(Item.category.is_not(None)).distinct().order_by(Item.category)
    ).all()
    warehouses = session.execute(
        select(Warehouse.warehouse_id, Warehouse.name).order_by(Warehouse.name)
    ).all()
    return DashboardFilters(
        categories=[c for c in categories if c is not None],
        warehouses=[WarehouseOption(id=wid, name=name) for wid, name in warehouses],
        stock_statuses=["in_stock", "low_stock", "out_of_stock"],
    )


def get_inventory_dashboard(
    session: Session,
    *,
    q: str | None,
    category: str | None,
    warehouse_id: int | None,
    stock_status: str | None,
    sort_by: str,
    sort_order: str,
    page: int,
    page_size: int,
) -> InventoryDashboardResponse:
    base_filters = _base_filters(q=q, category=category, warehouse_id=warehouse_id)
    status_expr = _stock_status_expr().label("stock_status")

    row_filters = list(base_filters)
    if stock_status is not None:
        row_filters.append(status_expr == stock_status)

    sort_columns = {
        "name": Item.name,
        "quantity": InventoryStock.quantity_on_hand,
        "last_updated": InventoryStock.updated_at,
    }
    sort_column = sort_columns[sort_by]
    order_by = sort_column.desc() if sort_order == "desc" else sort_column.asc()

    count_stmt = (
        select(func.count())
        .select_from(InventoryStock)
        .join(Item, Item.item_id == InventoryStock.item_id)
        .where(*row_filters)
    )
    total_items = int(session.execute(count_stmt).scalar_one())
    total_pages = ceil(total_items / page_size) if total_items > 0 else 0
    offset = (page - 1) * page_size

    rows_stmt = (
        select(
            Item.item_id,
            Item.name.label("item_name"),
            Item.sku,
            Item.category,
            Warehouse.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            InventoryStock.quantity_on_hand,
            InventoryStock.reorder_threshold,
            status_expr,
            InventoryStock.updated_at.label("last_updated"),
        )
        .select_from(InventoryStock)
        .join(Item, Item.item_id == InventoryStock.item_id)
        .join(Warehouse, Warehouse.warehouse_id == InventoryStock.warehouse_id)
        .where(*row_filters)
        .order_by(order_by, InventoryStock.inventory_stock_id.asc())
        .offset(offset)
        .limit(page_size)
    )

    items = [
        DashboardItem(
            item_id=row.item_id,
            item_name=row.item_name,
            sku=row.sku,
            category=row.category,
            warehouse_id=row.warehouse_id,
            warehouse_name=row.warehouse_name,
            quantity_on_hand=row.quantity_on_hand,
            reorder_threshold=row.reorder_threshold,
            stock_status=row.stock_status,
            last_updated=row.last_updated,
        )
        for row in session.execute(rows_stmt).all()
    ]

    return InventoryDashboardResponse(
        summary=_build_summary(session, base_filters),
        filters=_build_filter_options(session),
        items=items,
        pagination=DashboardPagination(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )
