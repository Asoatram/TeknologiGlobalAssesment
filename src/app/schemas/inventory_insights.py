from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

StockStatus = Literal["in_stock", "low_stock", "out_of_stock"]


class InsightsKpis(BaseModel):
    total_items: int
    low_stock_items: int
    out_of_stock_items: int


class LowStockByWarehousePoint(BaseModel):
    warehouse_id: int
    warehouse_name: str
    low_stock_count: int


class StatusDistributionPoint(BaseModel):
    status: StockStatus
    count: int
    percentage: float


class ItemsByCategoryPoint(BaseModel):
    category: str
    sku_count: int


class QuantityByCategoryPoint(BaseModel):
    category: str
    total_quantity: int


class InsightsMeta(BaseModel):
    last_sync_at: datetime | None


class InventoryInsightsResponse(BaseModel):
    kpis: InsightsKpis
    low_stock_by_warehouse: list[LowStockByWarehousePoint]
    status_distribution: list[StatusDistributionPoint]
    items_by_category: list[ItemsByCategoryPoint]
    quantity_by_category: list[QuantityByCategoryPoint]
    meta: InsightsMeta
