from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ImportDocumentStatus = Literal["completed", "pending_confirmation"]
ParsedRowStatus = Literal["applied", "pending_confirmation"]


class ValidationErrorItem(BaseModel):
    parsed_event_id: int
    row_number: int | None = None
    sku: str | None = None
    warehouse: str | None = None
    transaction_type: str | None = None
    quantity: str | None = None
    timestamp: str | None = None
    error_fields: list[str]
    error_messages: list[str]
    error_message: str


class ImportDocumentMeta(BaseModel):
    document_id: int
    file_name: str
    status: ImportDocumentStatus
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    pending_rows: int
    created_at: datetime
    updated_at: datetime


class ImportReferenceData(BaseModel):
    available_skus: list[str]
    available_warehouses: list[str]
    available_transaction_types: list[str]


class InventoryImportUploadResponse(BaseModel):
    document: ImportDocumentMeta
    references: ImportReferenceData
    validation_errors: list[ValidationErrorItem]


class ConfirmRowPatch(BaseModel):
    parsed_event_id: int
    sku: str | None = None
    warehouse: str | None = None
    transaction_type: str | None = None
    quantity: str | None = None
    timestamp: str | None = None


class InventoryImportConfirmRequest(BaseModel):
    rows: list[ConfirmRowPatch] = Field(default_factory=list)


class InventoryImportConfirmResponse(BaseModel):
    document: ImportDocumentMeta
    requested_rows: int
    applied_rows: int
    still_invalid_rows: int
    validation_errors: list[ValidationErrorItem]
