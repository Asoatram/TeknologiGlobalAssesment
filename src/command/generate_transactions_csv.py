from __future__ import annotations

import argparse
import csv
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.inventory import TransactionEventType
from app.models.item import Item
from app.models.warehouse import Warehouse

CSV_HEADERS = ["sku", "warehouse", "transaction_type", "quantity", "timestamp"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate inventory transaction CSV fixtures.")
    parser.add_argument("--rows", type=int, default=400, help="Number of valid rows to generate.")
    parser.add_argument(
        "--invalid-ratio",
        type=float,
        default=0.2,
        help="Invalid row ratio for mixed file (0.0 - 1.0).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/csv"),
        help="Output directory for generated CSV files.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed.")
    return parser.parse_args()


def _random_timestamp(rng: random.Random, days_back: int = 120) -> str:
    now = datetime.now(UTC)
    delta = timedelta(
        days=rng.randint(0, days_back),
        hours=rng.randint(0, 23),
        minutes=rng.randint(0, 59),
        seconds=rng.randint(0, 59),
    )
    return (now - delta).isoformat()


def _valid_row(rng: random.Random, skus: list[str], warehouses: list[str]) -> dict[str, str]:
    event_type = rng.choices(
        population=[t.value for t in TransactionEventType],
        weights=[25, 60, 15],  # restock, sale, adjustment
        k=1,
    )[0]
    quantity = rng.randint(1, 40) if event_type == TransactionEventType.SALE.value else rng.randint(1, 80)
    return {
        "sku": rng.choice(skus),
        "warehouse": rng.choice(warehouses),
        "transaction_type": event_type,
        "quantity": str(quantity),
        "timestamp": _random_timestamp(rng),
    }


def _invalid_row(
    rng: random.Random,
    skus: list[str],
    warehouses: list[str],
    invalid_type: str,
) -> dict[str, str]:
    row = _valid_row(rng, skus, warehouses)
    if invalid_type == "unknown_sku":
        row["sku"] = f"UNKNOWN-{rng.randint(1000, 9999)}"
    elif invalid_type == "unknown_warehouse":
        row["warehouse"] = f"Warehouse X-{rng.randint(1, 99)}"
    elif invalid_type == "invalid_event":
        row["transaction_type"] = "return"
    elif invalid_type == "non_positive_quantity":
        row["quantity"] = str(rng.choice([0, -3, -10]))
    elif invalid_type == "invalid_timestamp":
        row["timestamp"] = "not-a-timestamp"
    return row


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    if args.rows <= 0:
        raise SystemExit("--rows must be greater than 0.")
    if not 0.0 <= args.invalid_ratio <= 1.0:
        raise SystemExit("--invalid-ratio must be between 0.0 and 1.0.")

    rng = random.Random(args.seed)

    with SessionLocal() as session:
        skus = session.scalars(select(Item.sku).order_by(Item.sku)).all()
        warehouses = session.scalars(select(Warehouse.name).order_by(Warehouse.name)).all()

    if not skus or not warehouses:
        raise SystemExit("No items/warehouses found. Run the seed command first.")

    valid_rows = [_valid_row(rng, skus, warehouses) for _ in range(args.rows)]
    invalid_count = int(args.rows * args.invalid_ratio)
    mixed_rows = valid_rows.copy()

    invalid_types = [
        "unknown_sku",
        "unknown_warehouse",
        "invalid_event",
        "non_positive_quantity",
        "invalid_timestamp",
    ]
    for i in range(invalid_count):
        mixed_rows[i] = _invalid_row(rng, skus, warehouses, invalid_types[i % len(invalid_types)])
    rng.shuffle(mixed_rows)

    valid_path = args.out_dir / "inventory_transactions_valid.csv"
    mixed_path = args.out_dir / "inventory_transactions_mixed.csv"
    _write_csv(valid_path, valid_rows)
    _write_csv(mixed_path, mixed_rows)

    print(
        "CSV generation complete:",
        f"valid_file={valid_path}",
        f"mixed_file={mixed_path}",
        f"valid_rows={len(valid_rows)}",
        f"mixed_rows={len(mixed_rows)}",
        f"invalid_rows_in_mixed={invalid_count}",
    )


if __name__ == "__main__":
    main()
