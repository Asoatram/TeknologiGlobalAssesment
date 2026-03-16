# Inventory Backend

FastAPI + PostgreSQL backend for inventory listing, insights, and CSV transaction import with validation/confirmation.

## Architecture

```mermaid
flowchart LR
    UI[Frontend] --> API[FastAPI Routers]
    API --> SVC[Service Layer]
    SVC --> ORM[SQLAlchemy Models]
    ORM --> DB[(PostgreSQL)]
    API --> DTO[Schemas]
    MIG[Alembic] --> DB
    CMD[Seed/CSV Commands] --> DB
```

## ERD

```mermaid
erDiagram
    Items ||--o{ Inventory_Stock : has
    Warehouse ||--o{ Inventory_Stock : stores
    Items ||--o{ Inventory_Transaction : logs
    Warehouse ||--o{ Inventory_Transaction : logs
    Import_Document ||--o{ Parsed_Item : contains
    Inventory_Transaction o|--o{ Parsed_Item : applied_from

    Items {
      int ItemID PK
      string SKU UK
      string Name
      string Category
    }

    Warehouse {
      int WarehouseID PK
      string Name UK
      datetime CreatedAt
    }

    Inventory_Stock {
      int InventoryStockID PK
      int ItemID FK
      int WarehouseID FK
      int Quantity_On_Hand
      int ReorderThreshold
      datetime UpdatedAt
    }

    Inventory_Transaction {
      int TransactionID PK
      int ItemID FK
      int WarehouseID FK
      string EventType
      int Quantity
      datetime Timestamp
    }

    Import_Document {
      int DocumentID PK
      string FileName
      string Status
      int TotalRows
      int AcceptedRows
      int RejectedRows
      int PendingRows
      datetime CreatedAt
      datetime UpdatedAt
    }

    Parsed_Item {
      int ParsedEventID PK
      int DocumentID FK
      int ItemID FK
      int WarehouseID FK
      string SKU
      string Warehouse
      string TransactionType
      string QuantityRaw
      string TimestampRaw
      int Quantity
      string RowStatus
      int AppliedTransactionID FK
      string Message
    }
```

## Business Rules

```mermaid
flowchart TD
    Q[quantity_on_hand] --> O{<= 0?}
    O -- Yes --> OUT[out_of_stock]
    O -- No --> R{reorder_threshold is set\nand quantity <= threshold?}
    R -- Yes --> LOW[low_stock]
    R -- No --> IN[in_stock]
```

- Transaction types: `restock`, `sale`, `adjustment`
- Import strategy: partial success (valid applied, invalid pending)

## Main Flows

### Read Flow

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as Router
    participant S as Service
    participant DB as PostgreSQL

    FE->>API: GET /inventory/dashboard|insights|items/*
    API->>S: validated params
    S->>DB: query + aggregate
    DB-->>S: rows
    S-->>API: response DTO
    API-->>FE: JSON
```

### Import Flow

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as Router
    participant S as Import Service
    participant DB as PostgreSQL

    FE->>API: POST /inventory/imports (csv)
    API->>S: bytes + filename
    S->>S: parse + validate rows
    S->>DB: apply valid rows
    S->>DB: store invalid rows (pending)
    API-->>FE: summary + validation_errors + references

    FE->>API: POST /inventory/imports/{id}/confirm
    API->>S: corrected rows
    S->>DB: apply newly valid rows only
    API-->>FE: updated counters + remaining errors
```

## Project Map

```text
src/app/api/v1/endpoints/   # HTTP routes
src/app/services/           # business logic
src/app/schemas/            # request/response contracts
src/app/models/             # ORM models
alembic/versions/           # schema migrations
src/command/                # seed and CSV generation
tests/                      # baseline tests
```

## API Surface

- `GET /api/v1/health`
- `GET /api/v1/health/db`
- `GET /api/v1/inventory/dashboard`
- `GET /api/v1/inventory/insights`
- `POST /api/v1/inventory/imports`
- `POST /api/v1/inventory/imports/{document_id}/confirm`
- `GET /api/v1/inventory/items/{item_id}/details`
- `GET /api/v1/inventory/items/by-sku/{sku}/details`

Docs: `http://localhost:8000/docs`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/pip install fastapi uvicorn sqlalchemy alembic psycopg psycopg-binary python-dotenv python-multipart pydantic
cp .env.example .env
alembic upgrade head
PYTHONPATH=src uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Test & Data Commands

```bash
# tests
.venv/bin/pip install pytest
PYTHONPATH=src .venv/bin/python -m pytest -q

# seed
PYTHONPATH=src .venv/bin/python -m command.seed_data --mode reset --size medium --seed 42

# csv fixture generation
PYTHONPATH=src .venv/bin/python -m command.generate_transactions_csv --rows 400 --invalid-ratio 0.1 --seed 42
```

## Assumptions / Tradeoffs

- `ReorderThreshold` nullable by design (future intelligence feature).
- No auth layer (assessment scope).
- Supplier section is placeholder in item details (no supplier table).
- Known issue: `GET /inventory/insights` has a PostgreSQL grouping edge case to fix.
