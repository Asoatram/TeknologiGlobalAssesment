# Inventory Backend (FastAPI + PostgreSQL)

This project implements the backend for an inventory module used in a technical assessment context. The backend focuses on inventory listing, low-stock visibility, CSV bulk import with validation/confirmation, and inventory insights.

## Objective

The goal is to provide a practical, maintainable backend that supports:
- searchable, filterable, sortable inventory listing
- stock status derivation (`in_stock`, `low_stock`, `out_of_stock`)
- partial-success CSV import with row-level validation feedback
- visualization-ready inventory insight aggregates
- item detail data for warehouse stock and transaction history

## Architecture Overview

```mermaid
flowchart LR
    C[Client / Frontend] --> R[FastAPI Routers\nsrc/app/api/v1/endpoints]
    R --> S[Service Layer\nsrc/app/services]
    S --> M[SQLAlchemy Models\nsrc/app/models]
    M --> DB[(PostgreSQL)]

    R --> SC[Schemas\nsrc/app/schemas]
    S --> SC

    CMD[Command Scripts\nsrc/command] --> M
    MIG[Alembic Migrations\nalembic/versions] --> DB
```

### Layer Responsibilities

- **Routers (`api/v1/endpoints`)**
  - HTTP input/output boundary.
  - Parses query/body/file input, maps domain exceptions to HTTP errors.
- **Services (`services`)**
  - Core business logic (dashboard queries, import validation/apply flow, item details, insights).
  - Keeps endpoint functions thin and testable.
- **Schemas (`schemas`)**
  - API contracts (request/response payloads).
- **Models (`models`)**
  - Persistence model and constraints.
- **Migrations (`alembic`)**
  - Incremental schema evolution and compatibility.
- **Command scripts (`src/command`)**
  - Local data bootstrap and fixture generation.

## Data Model (From ERD to Implementation)

The design intentionally separates **current state** from **event history**.

### Core Tables

1. **`Items`**
- Product identity and metadata.
- Key fields: `ItemID`, `SKU` (unique), `Name`, `Category`.

2. **`Warehouse`**
- Inventory locations.
- Key fields: `WarehouseID`, `Name` (unique), `CreatedAt`.

3. **`Inventory_Stock`**
- Current snapshot of quantity per `(item, warehouse)`.
- Key fields: `ItemID`, `WarehouseID`, `Quantity_On_Hand`, `ReorderThreshold`, `UpdatedAt`.
- Important constraints:
  - `UNIQUE(ItemID, WarehouseID)`
  - non-negative stock quantity check
  - non-negative reorder threshold check (nullable allowed)

4. **`Inventory_Transaction`**
- Append-only-ish event stream for stock movement.
- Key fields: `TransactionID`, `ItemID`, `WarehouseID`, `EventType`, `Quantity`, `Timestamp`.
- `EventType` enum values: `restock`, `sale`, `adjustment`.
- Quantity must be `> 0`.

### Import Workflow Tables

5. **`Import_Document`**
- Tracks one uploaded CSV processing lifecycle.
- Stores aggregate counters (`total_rows`, `accepted_rows`, `rejected_rows`, `pending_rows`) and status.

6. **`Parsed_Item`**
- Stores parsed CSV rows and validation/apply result per row.
- Supports correction-and-confirm flow for invalid rows.
- Linked to `Import_Document`; may link to applied `Inventory_Transaction`.

### Relationships

- `Items (1) -> (many) Inventory_Stock`
- `Warehouse (1) -> (many) Inventory_Stock`
- `Items (1) -> (many) Inventory_Transaction`
- `Warehouse (1) -> (many) Inventory_Transaction`
- `Import_Document (1) -> (many) Parsed_Item`

### Derived Stock Status Logic

Status is computed in query logic (not persisted):
- `out_of_stock`: `quantity_on_hand <= 0`
- `low_stock`: `reorder_threshold IS NOT NULL AND quantity_on_hand <= reorder_threshold`
- `in_stock`: otherwise

This avoids duplicated state and keeps status consistent with source quantities.

## Core Request Flows

### 1) Inventory Dashboard / Insights / Item Details

```mermaid
sequenceDiagram
    participant U as UI
    participant API as FastAPI Router
    participant SV as Service
    participant DB as PostgreSQL

    U->>API: GET /api/v1/inventory/*
    API->>SV: validated params
    SV->>DB: SQLAlchemy queries
    DB-->>SV: rows/aggregates
    SV-->>API: response schema objects
    API-->>U: JSON
```

### 2) CSV Import (Partial Success + Confirmation)

```mermaid
sequenceDiagram
    participant U as UI
    participant API as FastAPI Router
    participant SV as Import Service
    participant DB as PostgreSQL

    U->>API: POST /inventory/imports (file)
    API->>SV: file bytes + filename
    SV->>SV: parse and validate each row
    SV->>DB: apply valid rows to stock + transactions
    SV->>DB: store invalid/pending rows in Parsed_Item
    SV-->>API: document summary + validation_errors + references
    API-->>U: upload result

    U->>API: POST /inventory/imports/{document_id}/confirm
    API->>SV: corrected rows
    SV->>SV: revalidate patched rows
    SV->>DB: apply only now-valid rows
    SV-->>API: updated counters + still-invalid rows
    API-->>U: confirm result
```

## API Surface (Summary)

Base path: `/api/v1`

- `GET /health`
- `GET /health/db`
- `GET /inventory/dashboard`
- `GET /inventory/insights`
- `POST /inventory/imports`
- `POST /inventory/imports/{document_id}/confirm`
- `GET /inventory/items/{item_id}/details`
- `GET /inventory/items/by-sku/{sku}/details`

OpenAPI docs: `/docs`

## Codebase Reading Guide

Start here in this order:

1. **`src/app/api/v1/endpoints/inventory.py`**
- Understand available endpoints and request parameters.

2. **`src/app/services/`**
- `inventory_dashboard.py`: listing/search/filter/sort/pagination and summary/filter options.
- `inventory_import.py`: CSV parse, validation, apply rules, pending confirmation flow.
- `inventory_insights.py`: KPI and chart aggregate queries.
- `inventory_item_details.py`: item details, stock overview, paginated history, quick insight text.

3. **`src/app/models/` + `alembic/versions/`**
- Confirm domain constraints and migration history.

4. **`src/app/schemas/`**
- Verify API payload contracts.

5. **`tests/`**
- Current minimal test coverage for stock status logic, import validation logic, and one endpoint.

## Engineering Assumptions and Tradeoffs

### Assumptions

- **Partial success import is preferred** over all-or-nothing import.
  - Valid rows should apply immediately.
  - Invalid rows should remain editable and confirmable.
- **Transaction type values are canonical lowercase** (`restock`, `sale`, `adjustment`).
- **`ReorderThreshold` is nullable**.
  - Threshold can be deferred for future intelligence-based recommendation.
- **No auth/authorization layer** in this assessment scope.
- **Supplier fields in item details are placeholders** (`null`) because supplier domain tables are not yet modeled.

### Tradeoffs and Limitations

- **Service-heavy query logic over repository abstraction**
  - Pro: direct, fast iteration for assessment scope.
  - Con: larger service modules; potential need for query composition/repository pattern as codebase scales.
- **Synchronous endpoint handlers with SQLAlchemy ORM**
  - Pro: simpler code and debugging.
  - Con: async DB stack may scale better for high-concurrency workloads.
- **Status derived at query-time**
  - Pro: no stale status column.
  - Con: repeated CASE logic across multiple query paths.
- **Import validation stores raw row strings and corrected state in DB**
  - Pro: recoverable workflow with explicit audit trail per parsed row.
  - Con: more schema complexity than ephemeral validation-only processing.
- **Known issue**
  - Current PostgreSQL query for `GET /inventory/insights` has a grouping edge-case in category aggregation and may need a minor SQLAlchemy grouping fix.

## Setup Instructions

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- `venv` support

### 1) Create and activate virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
.venv/bin/pip install \
  fastapi uvicorn sqlalchemy alembic psycopg psycopg-binary \
  python-dotenv python-multipart pydantic
```

### 3) Configure environment

Copy `.env.example` to `.env` and adjust values:

```env
APP_NAME=FastAPI PostgreSQL App
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/app_db
```

### 4) Run migrations

```bash
source .venv/bin/activate
alembic upgrade head
```

## Run the Application

```bash
PYTHONPATH=src uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open:
- `http://localhost:8000/docs`

## Seed and CSV Fixture Commands

Seed database:

```bash
PYTHONPATH=src .venv/bin/python -m command.seed_data --mode reset --size medium --seed 42
```

Generate CSV fixtures:

```bash
PYTHONPATH=src .venv/bin/python -m command.generate_transactions_csv --rows 400 --invalid-ratio 0.1 --seed 42
```

Outputs:
- `data/csv/inventory_transactions_valid.csv`
- `data/csv/inventory_transactions_mixed.csv`

## Run Tests

Install pytest (if missing):

```bash
.venv/bin/pip install pytest
```

Run tests:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
```

Current tests include:
- stock status logic
- import validation logic
- one backend endpoint (`/health`)

## Improvements with More Time

- Fix and harden insights aggregate query path across DB dialects.
- Add authentication/authorization and request-level audit logging.
- Add stronger transactional idempotency/locking strategy for import workflows.
- Expand tests to include integration tests for import/confirm happy-path and failure-path flows.
- Add CI pipeline and dependency lock management.
- Add frontend contract tests from OpenAPI schema.
