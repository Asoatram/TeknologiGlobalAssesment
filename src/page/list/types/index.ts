export type StockStatus = 'in_stock' | 'low_stock' | 'out_of_stock'
export type SortBy = 'name' | 'quantity' | 'last_updated'
export type SortOrder = 'asc' | 'desc'

export interface InventoryItem {
  rowKey: string
  id: number
  name: string
  sku: string
  category: string
  warehouseId: number
  warehouse: string
  qtyOnHand: number
  threshold: number | null
  status: StockStatus
  lastUpdated: string
}

export interface InventorySummary {
  inStock: number
  outOfStock: number
}

export interface PaginationMeta {
  page: number
  pageSize: number
  totalItems: number
  totalPages: number
}

export interface WarehouseOption {
  id: number
  name: string
}

export interface ListFilters {
  search: string
  category: string
  warehouseId: 'all' | number
  status: 'all' | StockStatus
}

export interface SortState {
  sortBy: SortBy
  sortOrder: SortOrder
}

export interface FilterValidationResult {
  isValid: boolean
  errors: Partial<Record<keyof ListFilters, string>>
}

export interface DashboardPayload {
  summary: InventorySummary
  categories: string[]
  warehouses: WarehouseOption[]
  items: InventoryItem[]
  pagination: PaginationMeta
}

export interface InventoryImportDocument {
  document_id: number
  file_name: string
  status: string
  total_rows: number
  accepted_rows: number
  rejected_rows: number
  pending_rows: number
  created_at: string
  updated_at: string
}

export interface InventoryImportValidationError {
  parsed_event_id: number
  row_number: number
  sku: string
  warehouse: string
  transaction_type: string
  quantity: string
  timestamp: string
  error_fields: string[]
  error_messages: string[]
  error_message: string
}

export interface InventoryImportResponse {
  document: InventoryImportDocument
  references?: {
    available_skus: string[]
    available_warehouses: string[]
    available_transaction_types: string[]
  }
  validation_errors: InventoryImportValidationError[]
  requested_rows?: number
  applied_rows?: number
  still_invalid_rows?: number
}
