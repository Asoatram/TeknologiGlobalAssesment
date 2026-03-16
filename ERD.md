# ERD and Schema Notes

This document is the schema reference for the current backend implementation.

## ER Diagram

```mermaid
erDiagram
    Items ||--o{ Inventory_Stock : has
    Warehouse ||--o{ Inventory_Stock : stores
    Items ||--o{ Inventory_Transaction : records
    Warehouse ||--o{ Inventory_Transaction : records
    Import_Document ||--o{ Parsed_Item : contains
    Items o|--o{ Parsed_Item : references
    Warehouse o|--o{ Parsed_Item : references
    Inventory_Transaction o|--o{ Parsed_Item : applied_as

    Items {
      int ItemID PK
      string SKU UK
      string Name
      string Category nullable
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
      int ReorderThreshold nullable
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
      int RowNumber
      int ItemID FK nullable
      int WarehouseID FK nullable
      string SKU
      string Warehouse nullable
      string TransactionType nullable
      string QuantityRaw nullable
      string TimestampRaw nullable
      int Quantity nullable
      string RowStatus
      int AppliedTransactionID FK nullable
      string Message nullable
    }
```

## Key Constraints

- `Items.SKU` is unique.
- `Warehouse.Name` is unique.
- `Inventory_Stock` has one row per `(ItemID, WarehouseID)` via unique constraint.
- `Inventory_Stock.Quantity_On_Hand >= 0`.
- `Inventory_Stock.ReorderThreshold IS NULL OR ReorderThreshold >= 0`.
- `Inventory_Transaction.Quantity > 0`.
- `Inventory_Transaction.EventType` enum values:
  - `restock`
  - `sale`
  - `adjustment`
- `Parsed_Item` has unique `(DocumentID, RowNumber)`.

## Derived Stock Status Rule

Stock status is computed at query time from `Inventory_Stock`:

- `out_of_stock` when `Quantity_On_Hand <= 0`
- `low_stock` when `ReorderThreshold IS NOT NULL AND Quantity_On_Hand <= ReorderThreshold`
- `in_stock` otherwise

## Import Flow Data Model

- One CSV upload creates one `Import_Document` row.
- Each parsed CSV line creates one `Parsed_Item` row.
- Valid rows are applied to `Inventory_Stock` and recorded in `Inventory_Transaction`.
- Invalid rows remain in `Parsed_Item` with `RowStatus = pending_confirmation` until confirmed.
