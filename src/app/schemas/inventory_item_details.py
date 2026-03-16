from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

StockStatus = Literal["in_stock", "low_stock", "out_of_stock"]


class ItemDetails(BaseModel):
    item_id: int
    sku: str
    name: str
    category: str | None


class StockLevelRow(BaseModel):
    warehouse_id: int
    warehouse_name: str
    quantity_on_hand: int
    reorder_threshold: int | None
    stock_status: StockStatus
    last_updated: datetime


class StockOverview(BaseModel):
    total_units: int
    warehouses_count: int
    in_stock_warehouses: int
    low_stock_warehouses: int
    out_of_stock_warehouses: int


class TransactionHistoryRow(BaseModel):
    transaction_id: int
    timestamp: datetime
    warehouse_id: int
    warehouse_name: str
    event_type: Literal["restock", "sale", "adjustment"]
    quantity_change: int


class TransactionHistory(BaseModel):
    page: int
    page_size: int
    total_records: int
    total_pages: int
    records: list[TransactionHistoryRow]


class SupplierInfo(BaseModel):
    supplier_name: str | None
    supplier_id: str | None
    email: str | None
    phone: str | None


class QuickInsight(BaseModel):
    message: str


class InventoryItemDetailsResponse(BaseModel):
    item: ItemDetails
    stock_overview: StockOverview
    stock_levels: list[StockLevelRow]
    transaction_history: TransactionHistory
    supplier_info: SupplierInfo | None
    quick_insight: QuickInsight
