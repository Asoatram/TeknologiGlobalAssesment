from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.inventory import (
    ImportDocument,
    InventoryStock,
    InventoryTransaction,
    ParsedItem,
    TransactionEventType,
)
from app.models.item import Item
from app.models.warehouse import Warehouse
from app.services.reorder_threshold import recalculate_all_reorder_thresholds


@dataclass(frozen=True)
class SeedProfile:
    items: int
    warehouses: int
    transactions: int


SEED_PROFILES: dict[str, SeedProfile] = {
    "small": SeedProfile(items=15, warehouses=2, transactions=90),
    "medium": SeedProfile(items=48, warehouses=4, transactions=576),
    "large": SeedProfile(items=120, warehouses=6, transactions=3600),
}

EVENT_VALUES = [t.value for t in TransactionEventType]
CATEGORY_OPTIONS = [
    "Electronics",
    "Office Supplies",
    "Home Goods",
    "Healthcare",
    "Food",
    "Automotive",
    "Apparel",
    "Tools",
]

CATEGORY_NAME_POOLS: dict[str, list[str]] = {
    "Electronics": [
        "Noise Cancelling Headphones",
        "Wireless Keyboard",
        "4K Monitor",
        "Bluetooth Speaker",
        "USB-C Docking Station",
        "Portable SSD",
    ],
    "Office Supplies": [
        "Executive Notebook",
        "Gel Ink Pen Set",
        "A4 Copy Paper Pack",
        "Desktop File Organizer",
        "Stapler Pro",
        "Whiteboard Marker Set",
    ],
    "Home Goods": [
        "Ergonomic Chair Pro",
        "LED Desk Lamp",
        "Memory Foam Pillow",
        "Cotton Bath Towel Set",
        "Stainless Steel Water Bottle",
        "Storage Box Set",
    ],
    "Healthcare": [
        "Digital Thermometer",
        "First Aid Kit",
        "Nitrile Gloves Box",
        "Hand Sanitizer 500ml",
        "Surgical Mask Pack",
        "Blood Pressure Monitor",
    ],
    "Food": [
        "Kellogg's Corn Flakes",
        "Nestle Milo 3in1",
        "Indomie Mi Goreng",
        "Heinz Tomato Ketchup",
        "Lay's Classic Chips",
        "Oreo Original Cookies",
        "Nutella Hazelnut Spread",
        "Coca-Cola Zero Sugar",
    ],
    "Automotive": [
        "Engine Oil 5W-30",
        "Car Wash Shampoo",
        "Microfiber Drying Towel",
        "Windshield Washer Fluid",
        "Tire Pressure Gauge",
        "Car Battery 12V",
    ],
    "Apparel": [
        "Classic Cotton T-Shirt",
        "Athletic Running Socks",
        "Slim Fit Chino Pants",
        "Lightweight Hoodie",
        "Windbreaker Jacket",
        "Canvas Sneakers",
    ],
    "Tools": [
        "Cordless Drill Set",
        "Precision Screwdriver Kit",
        "Adjustable Wrench",
        "Claw Hammer",
        "Laser Distance Meter",
        "Tape Measure 5m",
    ],
}

NAME_VARIANTS = [
    "Standard",
    "Plus",
    "Pro",
    "Max",
    "Lite",
    "Edition",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed inventory data for local development.")
    parser.add_argument(
        "--size",
        default="medium",
        choices=sorted(SEED_PROFILES.keys()),
        help="Dataset size profile.",
    )
    parser.add_argument(
        "--mode",
        default="reset",
        choices=["reset", "upsert", "fail-if-not-empty"],
        help="How to behave when data already exists.",
    )
    parser.add_argument(
        "--seed",
        default=42,
        type=int,
        help="Deterministic random seed.",
    )
    return parser.parse_args()


def _build_item_name(category: str, ordinal: int, rng: random.Random) -> str:
    base_names = CATEGORY_NAME_POOLS[category]
    base_name = base_names[(ordinal - 1) % len(base_names)]
    variant = NAME_VARIANTS[rng.randint(0, len(NAME_VARIANTS) - 1)]

    # Keep the core product name realistic and append a compact deterministic token for uniqueness.
    return f"{base_name} {variant} #{ordinal:03d}"


def _target_items(profile: SeedProfile, rng: random.Random) -> list[tuple[str, str, str]]:
    targets: list[tuple[str, str, str]] = []
    for i in range(1, profile.items + 1):
        sku = f"SKU-{i:04d}"
        category = CATEGORY_OPTIONS[(i - 1) % len(CATEGORY_OPTIONS)]
        name = _build_item_name(category, i, rng)
        targets.append((sku, name, category))
    return targets


def _target_warehouses(profile: SeedProfile) -> list[str]:
    labels = ["North", "South", "East", "West", "Central", "Overflow", "Transit", "Regional"]
    return [f"Warehouse {labels[i]}" for i in range(profile.warehouses)]


def _stock_quantity(rng: random.Random) -> int:
    # Keep ~10% out-of-stock and a broad positive spread for UI sorting/pagination.
    if rng.random() < 0.10:
        return 0
    return rng.randint(1, 240)


def _recent_timestamp(rng: random.Random, days_back: int = 90) -> datetime:
    now = datetime.now(UTC)
    delta = timedelta(
        days=rng.randint(0, days_back),
        hours=rng.randint(0, 23),
        minutes=rng.randint(0, 59),
        seconds=rng.randint(0, 59),
    )
    return now - delta


def _table_has_rows(session: Session, model: type) -> bool:
    return session.execute(select(model).limit(1)).first() is not None


def _reset_core_tables(session: Session) -> None:
    session.execute(delete(InventoryTransaction))
    session.execute(delete(InventoryStock))
    session.execute(delete(ParsedItem))
    session.execute(delete(ImportDocument))
    session.execute(delete(Item))
    session.execute(delete(Warehouse))


def _seed_transactions(
    session: Session,
    profile: SeedProfile,
    rng: random.Random,
    stocks: list[InventoryStock],
) -> int:
    if not stocks:
        return 0

    item_frequency_weight: dict[int, int] = {}
    for rank, item_id in enumerate(sorted({s.item_id for s in stocks}), start=1):
        item_frequency_weight[item_id] = max(1, profile.items // rank)

    stock_weights = [item_frequency_weight[s.item_id] for s in stocks]
    transactions: list[InventoryTransaction] = []

    # Ensure all event types appear at least once.
    anchor_stock = stocks[0]
    for event_type in EVENT_VALUES:
        transactions.append(
            InventoryTransaction(
                item_id=anchor_stock.item_id,
                warehouse_id=anchor_stock.warehouse_id,
                event_type=event_type,
                quantity=rng.randint(1, 25),
                timestamp=_recent_timestamp(rng),
            )
        )

    remaining = max(0, profile.transactions - len(transactions))
    for _ in range(remaining):
        stock = rng.choices(stocks, weights=stock_weights, k=1)[0]
        event_type = rng.choices(
            population=EVENT_VALUES,
            weights=[25, 60, 15],  # restock, sale, adjustment
            k=1,
        )[0]
        quantity = rng.randint(1, 40) if event_type == TransactionEventType.SALE.value else rng.randint(1, 75)
        transactions.append(
            InventoryTransaction(
                item_id=stock.item_id,
                warehouse_id=stock.warehouse_id,
                event_type=event_type,
                quantity=quantity,
                timestamp=_recent_timestamp(rng),
            )
        )

    session.add_all(transactions)
    return len(transactions)


def _seed_reset(session: Session, profile: SeedProfile, rng: random.Random) -> dict[str, int]:
    _reset_core_tables(session)

    warehouse_names = _target_warehouses(profile)
    warehouses = [Warehouse(name=name) for name in warehouse_names]
    session.add_all(warehouses)
    session.flush()

    item_targets = _target_items(profile, rng)
    items = [Item(sku=sku, name=name, category=category) for sku, name, category in item_targets]
    session.add_all(items)
    session.flush()

    stocks: list[InventoryStock] = []
    for item in items:
        for warehouse in warehouses:
            stocks.append(
                InventoryStock(
                    item_id=item.item_id,
                    warehouse_id=warehouse.warehouse_id,
                    quantity_on_hand=_stock_quantity(rng),
                    reorder_threshold=None,
                    updated_at=_recent_timestamp(rng),
                )
            )
    session.add_all(stocks)
    session.flush()

    transaction_count = _seed_transactions(session, profile, rng, stocks)
    recalculate_all_reorder_thresholds(session)
    return {
        "warehouses": len(warehouses),
        "items": len(items),
        "stocks": len(stocks),
        "transactions": transaction_count,
    }


def _seed_upsert(session: Session, profile: SeedProfile, rng: random.Random) -> dict[str, int]:
    inserted_warehouses = 0
    inserted_items = 0
    inserted_stocks = 0

    existing_warehouse = {
        name: wid
        for name, wid in session.execute(select(Warehouse.name, Warehouse.warehouse_id)).all()
    }
    for name in _target_warehouses(profile):
        if name not in existing_warehouse:
            warehouse = Warehouse(name=name)
            session.add(warehouse)
            session.flush()
            existing_warehouse[name] = warehouse.warehouse_id
            inserted_warehouses += 1

    existing_items = {
        sku: iid
        for sku, iid in session.execute(select(Item.sku, Item.item_id)).all()
    }
    for sku, name, category in _target_items(profile, rng):
        if sku not in existing_items:
            item = Item(sku=sku, name=name, category=category)
            session.add(item)
            session.flush()
            existing_items[sku] = item.item_id
            inserted_items += 1

    existing_pairs = set(
        session.execute(select(InventoryStock.item_id, InventoryStock.warehouse_id)).all()
    )
    for item_id in existing_items.values():
        for warehouse_id in existing_warehouse.values():
            if (item_id, warehouse_id) not in existing_pairs:
                session.add(
                    InventoryStock(
                        item_id=item_id,
                        warehouse_id=warehouse_id,
                        quantity_on_hand=_stock_quantity(rng),
                        reorder_threshold=None,
                        updated_at=_recent_timestamp(rng),
                    )
                )
                inserted_stocks += 1
    session.flush()

    stocks = session.scalars(select(InventoryStock)).all()
    transaction_count = _seed_transactions(session, profile, rng, stocks)
    recalculate_all_reorder_thresholds(session)
    return {
        "warehouses": inserted_warehouses,
        "items": inserted_items,
        "stocks": inserted_stocks,
        "transactions": transaction_count,
    }


def main() -> None:
    args = parse_args()
    profile = SEED_PROFILES[args.size]
    rng = random.Random(args.seed)

    with SessionLocal() as session:
        if args.mode == "fail-if-not-empty":
            if any(
                _table_has_rows(session, model)
                for model in (Item, Warehouse, InventoryStock, InventoryTransaction)
            ):
                raise SystemExit("Seed aborted: core tables already contain data.")
            summary = _seed_reset(session, profile, rng)
        elif args.mode == "upsert":
            summary = _seed_upsert(session, profile, rng)
        else:
            summary = _seed_reset(session, profile, rng)

        session.commit()

    print(
        "Seed complete:",
        f"mode={args.mode}",
        f"size={args.size}",
        f"warehouses={summary['warehouses']}",
        f"items={summary['items']}",
        f"stocks={summary['stocks']}",
        f"transactions={summary['transactions']}",
    )


if __name__ == "__main__":
    main()
