from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import (
    ImportDocument,
    ImportDocumentStatus,
    InventoryStock,
    InventoryTransaction,
    ParsedItem,
    ParsedRowStatus,
    TransactionEventType,
)
from app.models.item import Item
from app.models.warehouse import Warehouse
from app.schemas.inventory_import import (
    ConfirmRowPatch,
    ImportDocumentMeta,
    ImportReferenceData,
    InventoryImportConfirmRequest,
    InventoryImportConfirmResponse,
    InventoryImportUploadResponse,
    ValidationErrorItem,
)

EXPECTED_CSV_HEADERS = ["sku", "warehouse", "transaction_type", "quantity", "timestamp"]


@dataclass
class ValidatedRow:
    row_number: int
    sku: str
    warehouse: str
    transaction_type: str
    quantity_raw: str
    timestamp_raw: str
    item_id: int | None
    warehouse_id: int | None
    quantity: int | None
    timestamp: datetime | None
    errors: list[tuple[str, str]]


def _parse_csv_rows(content: bytes) -> list[dict[str, str]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV file must be UTF-8 encoded.") from exc

    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames != EXPECTED_CSV_HEADERS:
        raise ValueError(
            "Invalid CSV headers. Expected: sku,warehouse,transaction_type,quantity,timestamp"
        )

    rows: list[dict[str, str]] = []
    for row in reader:
        normalized = {key: (value or "").strip() for key, value in row.items() if key is not None}
        if not any(normalized.values()):
            continue
        rows.append(normalized)
    return rows


def _parse_timestamp(raw: str) -> datetime:
    value = raw.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _validate_row(
    row_number: int,
    row: dict[str, str],
    item_by_sku: dict[str, int],
    warehouse_by_name: dict[str, int],
) -> ValidatedRow:
    sku = row.get("sku", "")
    warehouse = row.get("warehouse", "")
    transaction_type = row.get("transaction_type", "").lower()
    quantity_raw = row.get("quantity", "")
    timestamp_raw = row.get("timestamp", "")

    errors: list[tuple[str, str]] = []

    item_id = item_by_sku.get(sku)
    if not sku:
        errors.append(("sku", "SKU is required."))
    elif item_id is None:
        errors.append(("sku", f"Unknown SKU: {sku}"))

    warehouse_id = warehouse_by_name.get(warehouse)
    if not warehouse:
        errors.append(("warehouse", "Warehouse is required."))
    elif warehouse_id is None:
        errors.append(("warehouse", f"Unknown warehouse: {warehouse}"))

    if transaction_type not in {event.value for event in TransactionEventType}:
        errors.append(
            (
                "transaction_type",
                "transaction_type must be one of: restock, sale, adjustment.",
            )
        )

    quantity: int | None = None
    try:
        quantity = int(quantity_raw)
        if quantity <= 0:
            errors.append(("quantity", "Quantity must be a positive integer."))
    except ValueError:
        errors.append(("quantity", f"Quantity must be an integer, got: {quantity_raw}"))

    timestamp: datetime | None = None
    try:
        timestamp = _parse_timestamp(timestamp_raw)
    except ValueError:
        errors.append(("timestamp", f"Invalid timestamp format: {timestamp_raw}"))

    return ValidatedRow(
        row_number=row_number,
        sku=sku,
        warehouse=warehouse,
        transaction_type=transaction_type,
        quantity_raw=quantity_raw,
        timestamp_raw=timestamp_raw,
        item_id=item_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        timestamp=timestamp,
        errors=errors,
    )


def _get_or_create_stock(
    session: Session,
    *,
    item_id: int,
    warehouse_id: int,
    timestamp: datetime,
) -> InventoryStock:
    stock = session.execute(
        select(InventoryStock)
        .where(InventoryStock.item_id == item_id, InventoryStock.warehouse_id == warehouse_id)
        .with_for_update()
    ).scalar_one_or_none()

    if stock is not None:
        return stock

    stock = InventoryStock(
        item_id=item_id,
        warehouse_id=warehouse_id,
        quantity_on_hand=0,
        reorder_threshold=None,
        updated_at=timestamp,
    )
    session.add(stock)
    session.flush()
    return stock


def _apply_row(
    session: Session,
    *,
    validated: ValidatedRow,
) -> tuple[int | None, list[tuple[str, str]]]:
    if validated.item_id is None or validated.warehouse_id is None:
        return None, [("row", "Cannot apply row with unresolved references.")]
    if validated.quantity is None or validated.timestamp is None:
        return None, [("row", "Cannot apply row with invalid quantity or timestamp.")]

    stock = _get_or_create_stock(
        session,
        item_id=validated.item_id,
        warehouse_id=validated.warehouse_id,
        timestamp=validated.timestamp,
    )

    if validated.transaction_type == TransactionEventType.RESTOCK.value:
        stock.quantity_on_hand += validated.quantity
    elif validated.transaction_type == TransactionEventType.SALE.value:
        if stock.quantity_on_hand - validated.quantity < 0:
            return None, [("quantity", "Insufficient stock for sale transaction.")]
        stock.quantity_on_hand -= validated.quantity
    else:
        stock.quantity_on_hand = validated.quantity

    stock.updated_at = validated.timestamp

    transaction = InventoryTransaction(
        item_id=validated.item_id,
        warehouse_id=validated.warehouse_id,
        event_type=validated.transaction_type,
        quantity=validated.quantity,
        timestamp=validated.timestamp,
    )
    session.add(transaction)
    session.flush()
    return transaction.transaction_id, []


def _document_meta(document: ImportDocument) -> ImportDocumentMeta:
    return ImportDocumentMeta(
        document_id=document.document_id,
        file_name=document.file_name,
        status=document.status,
        total_rows=document.total_rows,
        accepted_rows=document.accepted_rows,
        rejected_rows=document.rejected_rows,
        pending_rows=document.pending_rows,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _row_errors_to_response(parsed_item: ParsedItem, errors: list[tuple[str, str]]) -> ValidationErrorItem:
    fields = [field for field, _ in errors]
    messages = [message for _, message in errors]
    return ValidationErrorItem(
        parsed_event_id=parsed_item.parsed_event_id,
        row_number=parsed_item.row_number,
        sku=parsed_item.sku,
        warehouse=parsed_item.warehouse,
        transaction_type=parsed_item.transaction_type,
        quantity=parsed_item.quantity_raw,
        timestamp=parsed_item.timestamp_raw,
        error_fields=fields,
        error_messages=messages,
        error_message="; ".join(messages),
    )


def upload_inventory_import(
    session: Session,
    *,
    file_name: str,
    content: bytes,
) -> InventoryImportUploadResponse:
    rows = _parse_csv_rows(content)

    item_by_sku = {
        sku: item_id for sku, item_id in session.execute(select(Item.sku, Item.item_id)).all()
    }
    warehouse_by_name = {
        name: warehouse_id
        for name, warehouse_id in session.execute(select(Warehouse.name, Warehouse.warehouse_id)).all()
    }

    document = ImportDocument(
        file_name=file_name,
        status=ImportDocumentStatus.COMPLETED.value,
        total_rows=len(rows),
        accepted_rows=0,
        rejected_rows=0,
        pending_rows=0,
    )
    session.add(document)
    session.flush()

    validation_errors: list[ValidationErrorItem] = []
    accepted_rows = 0
    rejected_rows = 0

    for index, row in enumerate(rows, start=1):
        row_number = index + 1
        validated = _validate_row(row_number, row, item_by_sku, warehouse_by_name)

        parsed_item = ParsedItem(
            document_id=document.document_id,
            row_number=row_number,
            item_id=validated.item_id,
            warehouse_id=validated.warehouse_id,
            sku=validated.sku,
            warehouse=validated.warehouse,
            transaction_type=validated.transaction_type,
            quantity_raw=validated.quantity_raw,
            timestamp_raw=validated.timestamp_raw,
            quantity=validated.quantity,
            row_status=ParsedRowStatus.PENDING_CONFIRMATION.value,
            message=None,
        )
        session.add(parsed_item)
        session.flush()

        row_errors = list(validated.errors)
        if not row_errors:
            transaction_id, apply_errors = _apply_row(session, validated=validated)
            row_errors.extend(apply_errors)
            if transaction_id is not None and not row_errors:
                parsed_item.row_status = ParsedRowStatus.APPLIED.value
                parsed_item.applied_transaction_id = transaction_id

        if row_errors:
            rejected_rows += 1
            parsed_item.row_status = ParsedRowStatus.PENDING_CONFIRMATION.value
            parsed_item.message = "; ".join(message for _, message in row_errors)
            validation_errors.append(_row_errors_to_response(parsed_item, row_errors))
        else:
            accepted_rows += 1
            parsed_item.message = None

    document.accepted_rows = accepted_rows
    document.rejected_rows = rejected_rows
    document.pending_rows = rejected_rows
    document.status = (
        ImportDocumentStatus.PENDING_CONFIRMATION.value
        if rejected_rows > 0
        else ImportDocumentStatus.COMPLETED.value
    )

    session.commit()
    session.refresh(document)

    return InventoryImportUploadResponse(
        document=_document_meta(document),
        references=ImportReferenceData(
            available_skus=sorted(item_by_sku.keys()),
            available_warehouses=sorted(warehouse_by_name.keys()),
            available_transaction_types=[event.value for event in TransactionEventType],
        ),
        validation_errors=validation_errors,
    )


def _update_document_stats(session: Session, document: ImportDocument) -> None:
    rows = session.scalars(
        select(ParsedItem).where(ParsedItem.document_id == document.document_id)
    ).all()
    total = len(rows)
    accepted = sum(1 for row in rows if row.row_status == ParsedRowStatus.APPLIED.value)
    pending = total - accepted

    document.total_rows = total
    document.accepted_rows = accepted
    document.rejected_rows = pending
    document.pending_rows = pending
    document.status = (
        ImportDocumentStatus.PENDING_CONFIRMATION.value
        if pending > 0
        else ImportDocumentStatus.COMPLETED.value
    )


def confirm_inventory_import(
    session: Session,
    *,
    document_id: int,
    payload: InventoryImportConfirmRequest,
) -> InventoryImportConfirmResponse:
    document = session.get(ImportDocument, document_id)
    if document is None:
        raise LookupError(f"Import document {document_id} was not found.")

    requested_ids = [row.parsed_event_id for row in payload.rows]
    patch_by_id: dict[int, ConfirmRowPatch] = {row.parsed_event_id: row for row in payload.rows}

    target_rows = session.scalars(
        select(ParsedItem).where(
            ParsedItem.document_id == document_id,
            ParsedItem.parsed_event_id.in_(requested_ids),
            ParsedItem.row_status == ParsedRowStatus.PENDING_CONFIRMATION.value,
        )
    ).all()

    target_row_by_id = {row.parsed_event_id: row for row in target_rows}

    validation_errors: list[ValidationErrorItem] = []
    applied_rows = 0

    item_by_sku = {
        sku: item_id for sku, item_id in session.execute(select(Item.sku, Item.item_id)).all()
    }
    warehouse_by_name = {
        name: warehouse_id
        for name, warehouse_id in session.execute(select(Warehouse.name, Warehouse.warehouse_id)).all()
    }

    for parsed_event_id in requested_ids:
        parsed_row = target_row_by_id.get(parsed_event_id)
        if parsed_row is None:
            validation_errors.append(
                ValidationErrorItem(
                    parsed_event_id=parsed_event_id,
                    row_number=None,
                    sku=None,
                    warehouse=None,
                    transaction_type=None,
                    quantity=None,
                    timestamp=None,
                    error_fields=["parsed_event_id"],
                    error_messages=["Parsed row not found in pending state for this document."],
                    error_message="Parsed row not found in pending state for this document.",
                )
            )
            continue

        patch = patch_by_id[parsed_event_id]
        merged = {
            "sku": patch.sku if patch.sku is not None else parsed_row.sku,
            "warehouse": patch.warehouse if patch.warehouse is not None else (parsed_row.warehouse or ""),
            "transaction_type": (
                patch.transaction_type
                if patch.transaction_type is not None
                else (parsed_row.transaction_type or "")
            ),
            "quantity": patch.quantity if patch.quantity is not None else (parsed_row.quantity_raw or ""),
            "timestamp": patch.timestamp if patch.timestamp is not None else (parsed_row.timestamp_raw or ""),
        }

        validated = _validate_row(parsed_row.row_number, merged, item_by_sku, warehouse_by_name)

        parsed_row.sku = validated.sku
        parsed_row.warehouse = validated.warehouse
        parsed_row.transaction_type = validated.transaction_type
        parsed_row.quantity_raw = validated.quantity_raw
        parsed_row.timestamp_raw = validated.timestamp_raw
        parsed_row.item_id = validated.item_id
        parsed_row.warehouse_id = validated.warehouse_id
        parsed_row.quantity = validated.quantity

        row_errors = list(validated.errors)
        if not row_errors:
            transaction_id, apply_errors = _apply_row(session, validated=validated)
            row_errors.extend(apply_errors)
            if transaction_id is not None and not row_errors:
                parsed_row.row_status = ParsedRowStatus.APPLIED.value
                parsed_row.applied_transaction_id = transaction_id
                parsed_row.message = None
                applied_rows += 1

        if row_errors:
            parsed_row.row_status = ParsedRowStatus.PENDING_CONFIRMATION.value
            parsed_row.message = "; ".join(message for _, message in row_errors)
            validation_errors.append(_row_errors_to_response(parsed_row, row_errors))

    _update_document_stats(session, document)
    session.commit()
    session.refresh(document)

    still_invalid_rows = sum(
        1
        for row in payload.rows
        if any(error.parsed_event_id == row.parsed_event_id for error in validation_errors)
    )

    return InventoryImportConfirmResponse(
        document=_document_meta(document),
        requested_rows=len(payload.rows),
        applied_rows=applied_rows,
        still_invalid_rows=still_invalid_rows,
        validation_errors=validation_errors,
    )
