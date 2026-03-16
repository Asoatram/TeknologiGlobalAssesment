from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.inventory_dashboard import InventoryDashboardResponse
from app.schemas.inventory_import import (
    InventoryImportConfirmRequest,
    InventoryImportConfirmResponse,
    InventoryImportUploadResponse,
)
from app.schemas.inventory_insights import InventoryInsightsResponse
from app.schemas.inventory_item_details import InventoryItemDetailsResponse
from app.services.inventory_import import confirm_inventory_import, upload_inventory_import
from app.services.inventory_dashboard import get_inventory_dashboard
from app.services.inventory_insights import get_inventory_insights
from app.services.inventory_item_details import (
    get_inventory_item_details,
    get_inventory_item_details_by_sku,
)

router = APIRouter()


@router.get("/inventory/dashboard", response_model=InventoryDashboardResponse)
def inventory_dashboard(
    q: str | None = Query(default=None, description="Search item name or SKU."),
    category: str | None = Query(default=None),
    warehouse_id: int | None = Query(default=None),
    stock_status: Literal["in_stock", "low_stock", "out_of_stock"] | None = Query(default=None),
    sort_by: Literal["name", "quantity", "last_updated"] = Query(default="last_updated"),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> InventoryDashboardResponse:
    return get_inventory_dashboard(
        db,
        q=q,
        category=category,
        warehouse_id=warehouse_id,
        stock_status=stock_status,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/inventory/insights", response_model=InventoryInsightsResponse)
def inventory_insights(
    q: str | None = Query(default=None, description="Search inventory by item name or SKU."),
    category: str | None = Query(default=None),
    warehouse_id: int | None = Query(default=None),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
) -> InventoryInsightsResponse:
    return get_inventory_insights(
        db,
        q=q,
        category=category,
        warehouse_id=warehouse_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.post("/inventory/imports", response_model=InventoryImportUploadResponse)
async def upload_inventory_csv(
    file: UploadFile = File(..., description="CSV file with inventory transactions."),
    db: Session = Depends(get_db),
) -> InventoryImportUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must include a filename.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")

    try:
        return upload_inventory_import(db, file_name=file.filename, content=content)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/inventory/imports/{document_id}/confirm",
    response_model=InventoryImportConfirmResponse,
)
def confirm_inventory_csv(
    document_id: int,
    payload: InventoryImportConfirmRequest,
    db: Session = Depends(get_db),
) -> InventoryImportConfirmResponse:
    if not payload.rows:
        raise HTTPException(status_code=400, detail="rows must not be empty.")

    try:
        return confirm_inventory_import(db, document_id=document_id, payload=payload)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/inventory/items/{item_id}/details",
    response_model=InventoryItemDetailsResponse,
)
def inventory_item_details(
    item_id: int,
    transaction_page: int = Query(default=1, ge=1),
    transaction_page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> InventoryItemDetailsResponse:
    try:
        return get_inventory_item_details(
            db,
            item_id=item_id,
            transaction_page=transaction_page,
            transaction_page_size=transaction_page_size,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/inventory/items/by-sku/{sku}/details",
    response_model=InventoryItemDetailsResponse,
)
def inventory_item_details_by_sku(
    sku: str,
    transaction_page: int = Query(default=1, ge=1),
    transaction_page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> InventoryItemDetailsResponse:
    try:
        return get_inventory_item_details_by_sku(
            db,
            sku=sku,
            transaction_page=transaction_page,
            transaction_page_size=transaction_page_size,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
