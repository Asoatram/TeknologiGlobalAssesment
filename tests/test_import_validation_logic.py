from __future__ import annotations

from app.services.inventory_import import _validate_row


def test_validate_row_collects_expected_errors() -> None:
    row = {
        "sku": "UNKNOWN-SKU",
        "warehouse": "Unknown Warehouse",
        "transaction_type": "return",
        "quantity": "not-an-int",
        "timestamp": "bad-ts",
    }

    validated = _validate_row(
        row_number=2,
        row=row,
        item_by_sku={"SKU-0001": 1},
        warehouse_by_name={"Warehouse East": 1},
    )

    fields = {field for field, _ in validated.errors}
    assert fields == {"sku", "warehouse", "transaction_type", "quantity", "timestamp"}


def test_validate_row_normalizes_uppercase_transaction_type() -> None:
    row = {
        "sku": "SKU-0001",
        "warehouse": "Warehouse East",
        "transaction_type": "SALE",
        "quantity": "3",
        "timestamp": "2026-03-16T10:00:00Z",
    }

    validated = _validate_row(
        row_number=2,
        row=row,
        item_by_sku={"SKU-0001": 1},
        warehouse_by_name={"Warehouse East": 1},
    )

    assert validated.errors == []
    assert validated.transaction_type == "sale"
    assert validated.quantity == 3
    assert validated.item_id == 1
    assert validated.warehouse_id == 1
