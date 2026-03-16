from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

StockStatus = Literal["in_stock", "low_stock", "out_of_stock"]


class WarehouseOption(BaseModel):
    id: int
    name: str


class DashboardFilters(BaseModel):
    categories: list[str]
    warehouses: list[WarehouseOption]
    stock_statuses: list[StockStatus]


class DashboardSummary(BaseModel):
    in_stock_count: int
    out_of_stock_count: int
    low_stock_count: int


class DashboardItem(BaseModel):
    item_id: int
    item_name: str
    sku: str
    category: str | None
    warehouse_id: int
    warehouse_name: str
    quantity_on_hand: int
    reorder_threshold: int | None
    stock_status: StockStatus
    last_updated: datetime


class DashboardPagination(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class InventoryDashboardResponse(BaseModel):
    summary: DashboardSummary
    filters: DashboardFilters
    items: list[DashboardItem]
    pagination: DashboardPagination
