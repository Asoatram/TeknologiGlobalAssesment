# Backend to Frontend API Handover

This document describes how the frontend should consume the current FastAPI backend.

## 1. Quick Facts

- API base path: `/api/v1`
- OpenAPI docs: `/docs`
- Health endpoints:
  - `GET /api/v1/health`
  - `GET /api/v1/health/db`
- Auth: none implemented (all endpoints are currently public)
- Content types:
  - JSON for regular API calls
  - `multipart/form-data` for CSV upload

## 2. Run and Access

Run app locally:

```bash
PYTHONPATH=src uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Typical local base URL:

- `http://localhost:8000/api/v1`

Required env var in `.env`:

- `DATABASE_URL=postgresql+psycopg://...`

## 3. Domain and Data Rules

### Stock Status Logic

Used consistently across dashboard, insights, and item details:

- `out_of_stock`: `quantity_on_hand <= 0`
- `low_stock`: `reorder_threshold != null` AND `quantity_on_hand <= reorder_threshold`
- `in_stock`: everything else

### Transaction Types

Only these lowercase values are valid:

- `restock`
- `sale`
- `adjustment`

### Quantity semantics

- Transactions require `quantity > 0`
- For item detail history, backend returns `quantity_change` with sign:
  - `sale` becomes negative
  - `restock` and `adjustment` are positive

### SKU format in seeded data

Current seed/generator uses deterministic SKU format:

- `SKU-0001`, `SKU-0002`, ...

## 4. Endpoints

## 4.1 Inventory Dashboard

`GET /api/v1/inventory/dashboard`

Purpose:
- Main list page with filters, summary cards, and paginated rows.

Query params:
- `q` (string, optional): search name or SKU
- `category` (string, optional)
- `warehouse_id` (int, optional)
- `stock_status` (optional enum): `in_stock | low_stock | out_of_stock`
- `sort_by` (enum, default `last_updated`): `name | quantity | last_updated`
- `sort_order` (enum, default `desc`): `asc | desc`
- `page` (int, default 1, min 1)
- `page_size` (int, default 10, min 1, max 100)

Response shape:

- `summary`
  - `in_stock_count`
  - `out_of_stock_count`
  - `low_stock_count`
- `filters`
  - `categories: string[]`
  - `warehouses: { id, name }[]`
  - `stock_statuses: ["in_stock", "low_stock", "out_of_stock"]`
- `items[]`
  - `item_id, item_name, sku, category`
  - `warehouse_id, warehouse_name`
  - `quantity_on_hand, reorder_threshold`
  - `stock_status`
  - `last_updated`
- `pagination`
  - `page, page_size, total_items, total_pages`

Notes for frontend:
- `summary` ignores `stock_status` filter but respects `q/category/warehouse_id`.
- `total_pages` can be `0` when no data.

## 4.2 Inventory Insights

`GET /api/v1/inventory/insights`

Purpose:
- Analytics payload for charts and KPI cards.

Query params:
- `q` (string, optional)
- `category` (string, optional)
- `warehouse_id` (int, optional)
- `from` (date `YYYY-MM-DD`, optional)
- `to` (date `YYYY-MM-DD`, optional)

Response shape:

- `kpis`
  - `total_items`
  - `low_stock_items`
  - `out_of_stock_items`
- `low_stock_by_warehouse[]`
  - `warehouse_id, warehouse_name, low_stock_count`
- `status_distribution[]`
  - `status, count, percentage`
- `items_by_category[]`
  - `category, sku_count`
- `quantity_by_category[]`
  - `category, total_quantity`
- `meta`
  - `last_sync_at`

Notes:
- Date filter is applied against `Inventory_Stock.updated_at`.
- Percentage is precomputed by backend.

## 4.3 CSV Upload (Import Phase)

`POST /api/v1/inventory/imports`

Purpose:
- Upload a CSV and immediately apply valid rows.
- Invalid rows are stored for correction/confirmation.

Request:
- `multipart/form-data`
- field: `file` (CSV)

Required CSV header (exact order):

```csv
sku,warehouse,transaction_type,quantity,timestamp
```

Validation highlights:
- `sku` must exist in Items
- `warehouse` must exist in Warehouse.Name
- `transaction_type` must be one of `restock|sale|adjustment`
- `quantity` must be positive integer
- `timestamp` must be ISO parseable (supports `Z`)
- `sale` fails if stock would go negative

Response:
- `document`
  - `document_id, file_name, status`
  - `total_rows, accepted_rows, rejected_rows, pending_rows`
  - `created_at, updated_at`
- `references`
  - `available_skus: string[]`
  - `available_warehouses: string[]`
  - `available_transaction_types: string[]` (currently `restock|sale|adjustment`)
- `validation_errors[]`
  - `parsed_event_id`
  - `row_number`
  - row data snapshot: `sku, warehouse, transaction_type, quantity, timestamp`
  - `error_fields[]`
  - `error_messages[]`
  - `error_message` (joined text)

Important behavior:
- Partial success is enabled.
- Valid rows are applied immediately.
- Invalid rows stay `pending_confirmation` and can be fixed via confirm endpoint.

## 4.4 CSV Confirm (Correction Phase)

`POST /api/v1/inventory/imports/{document_id}/confirm`

Purpose:
- Submit corrected rows for previously invalid records.
- Applies valid corrected rows only.

Request body:

```json
{
  "rows": [
    {
      "parsed_event_id": 123,
      "sku": "SKU-0001",
      "warehouse": "Warehouse East",
      "transaction_type": "sale",
      "quantity": "8",
      "timestamp": "2026-03-16T05:00:00Z"
    }
  ]
}
```

Notes:
- `rows` must not be empty (400 if empty).
- All fields except `parsed_event_id` are optional patch fields.
- Omitted fields keep existing stored values.

Response:
- `document` (same shape as upload)
- `requested_rows`
- `applied_rows`
- `still_invalid_rows`
- `validation_errors[]` (same shape as upload)

Important behavior:
- If a row is still invalid, it remains pending and is returned again in `validation_errors`.
- Rows not found in pending state return an error item with `parsed_event_id` field error.

## 4.5 Item Details by Item ID

`GET /api/v1/inventory/items/{item_id}/details`

Purpose:
- Item detail page payload (header, stock by warehouse, transaction history, quick insight).

Query params:
- `transaction_page` (int, default 1, min 1)
- `transaction_page_size` (int, default 10, min 1, max 100)

Response:
- `item`
  - `item_id, sku, name, category`
- `stock_overview`
  - `total_units`
  - `warehouses_count`
  - `in_stock_warehouses`
  - `low_stock_warehouses`
  - `out_of_stock_warehouses`
- `stock_levels[]`
  - `warehouse_id, warehouse_name`
  - `quantity_on_hand, reorder_threshold, stock_status, last_updated`
- `transaction_history`
  - `page, page_size, total_records, total_pages, records[]`
  - each record: `transaction_id, timestamp, warehouse_id, warehouse_name, event_type, quantity_change`
- `supplier_info`
  - currently placeholder null fields (`supplier_name`, `supplier_id`, `email`, `phone`)
- `quick_insight`
  - `message`

## 4.6 Item Details by SKU

`GET /api/v1/inventory/items/by-sku/{sku}/details`

Purpose:
- Same payload as item-id details, resolved by SKU.

Query params:
- same as item-id endpoint (`transaction_page`, `transaction_page_size`)

## 5. Error Handling Contract

Typical status codes:
- `200` success
- `400` bad input (empty rows, invalid CSV header, empty file, etc.)
- `404` missing document/item/SKU
- `503` DB unavailable (`/health/db`)
- `500` unhandled server errors

For frontend:
- For `400`/`404`, FastAPI returns `{ "detail": "..." }` for endpoint-level errors.
- For import flow row-level issues, rely on `validation_errors[]` instead of HTTP errors.

## 6. Recommended Frontend Integration Flow

## 6.1 Dashboard Page

1. Call `GET /inventory/dashboard` with filter/sort/pagination state.
2. Render:
   - summary cards from `summary`
   - filter controls from `filters`
   - table rows from `items`
   - pagination from `pagination`
3. For stock badge mapping:
   - `in_stock` green
   - `low_stock` amber
   - `out_of_stock` red

## 6.2 Insights Page

1. Call `GET /inventory/insights` with current filter/date range.
2. Use:
   - `kpis` for cards
   - `low_stock_by_warehouse`, `items_by_category`, `quantity_by_category` for charts
   - `status_distribution` for donut/pie/stacked bars

## 6.3 CSV Import Page

1. User uploads CSV -> `POST /inventory/imports`.
2. Show import summary from `document`.
3. If `validation_errors.length > 0`, show editable row error table:
   - prefill with row fields from each error item
   - highlight inputs based on `error_fields`
   - show human message from `error_messages` / `error_message`
4. Submit edits via `POST /inventory/imports/{document_id}/confirm`.
5. Repeat until `still_invalid_rows = 0` and `document.status = completed`.

## 7. Known Caveats / Open Items

- `supplier_info` is placeholder only; no supplier master data table yet.
- Reorder threshold is nullable and currently not auto-derived by AI in API layer.
- Keep transaction_type lowercase in frontend payloads.
- `row_number` in import error payload reflects CSV line numbering (header is line 1).
- On PostgreSQL, `GET /inventory/insights` may still throw a grouping error in category aggregations until backend query grouping is adjusted.

## 8. Minimal Frontend TypeScript Types (optional starter)

```ts
export type StockStatus = "in_stock" | "low_stock" | "out_of_stock";

export interface ValidationErrorItem {
  parsed_event_id: number;
  row_number: number | null;
  sku: string | null;
  warehouse: string | null;
  transaction_type: string | null;
  quantity: string | null;
  timestamp: string | null;
  error_fields: string[];
  error_messages: string[];
  error_message: string;
}
```

## 9. Smoke Test Commands (for another agent)

```bash
# Health
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/db

# Dashboard
curl "http://localhost:8000/api/v1/inventory/dashboard?page=1&page_size=10"

# Insights
curl "http://localhost:8000/api/v1/inventory/insights"

# Item details by SKU
curl "http://localhost:8000/api/v1/inventory/items/by-sku/SKU-0001/details"

# CSV upload
curl -X POST "http://localhost:8000/api/v1/inventory/imports" \
  -F "file=@data/csv/inventory_transactions_mixed.csv"
```
