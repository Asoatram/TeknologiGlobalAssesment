import type {
  DashboardPayload,
  InventoryItem,
  ListFilters,
  PaginationMeta,
  SortState,
  StockStatus,
  WarehouseOption,
} from '../types'

interface DashboardApiResponse {
  summary: {
    in_stock_count: number
    out_of_stock_count: number
    low_stock_count: number
  }
  filters: {
    categories: string[]
    warehouses: Array<{ id: number; name: string }>
    stock_statuses: StockStatus[]
  }
  items: Array<{
    item_id: number
    item_name: string
    sku: string
    category: string
    warehouse_id: number
    warehouse_name: string
    quantity_on_hand: number
    reorder_threshold: number | null
    stock_status: StockStatus
    last_updated: string
  }>
  pagination: {
    page: number
    page_size: number
    total_items: number
    total_pages: number
  }
}

function getBackendUrl() {
  const raw = import.meta.env.BACKEND_URL?.trim()

  if (!raw) {
    throw new Error('BACKEND_URL is not set in .env')
  }

  if (raw.startsWith('http://') || raw.startsWith('https://')) {
    return raw
  }

  return `http://${raw}`
}

function buildDashboardUrl(
  filters: ListFilters,
  page: number,
  pageSize: number,
  sort: SortState,
) {
  const url = import.meta.env.DEV
    ? new URL('/api/v1/inventory/dashboard', window.location.origin)
    : new URL('/api/v1/inventory/dashboard', getBackendUrl())

  if (filters.search.trim()) {
    url.searchParams.set('q', filters.search.trim())
  }

  if (filters.category !== 'all') {
    url.searchParams.set('category', filters.category)
  }

  if (filters.warehouseId !== 'all') {
    url.searchParams.set('warehouse_id', String(filters.warehouseId))
  }

  if (filters.status !== 'all') {
    url.searchParams.set('stock_status', filters.status)
  }

  url.searchParams.set('sort_by', sort.sortBy)
  url.searchParams.set('sort_order', sort.sortOrder)
  url.searchParams.set('page', String(page))
  url.searchParams.set('pagination_size', String(pageSize))
  url.searchParams.set('page_size', String(pageSize))

  return url
}

function formatDate(dateText: string) {
  const parsed = new Date(dateText)

  if (Number.isNaN(parsed.getTime())) {
    return dateText
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
  }).format(parsed)
}

function mapItems(items: DashboardApiResponse['items']): InventoryItem[] {
  return items.map((item) => ({
    rowKey: `${item.item_id}-${item.warehouse_id}-${item.sku}`,
    id: item.item_id,
    name: item.item_name,
    sku: item.sku,
    category: item.category,
    warehouseId: item.warehouse_id,
    warehouse: item.warehouse_name,
    qtyOnHand: item.quantity_on_hand,
    threshold: item.reorder_threshold,
    status: item.stock_status,
    lastUpdated: formatDate(item.last_updated),
  }))
}

function mapPagination(pagination: DashboardApiResponse['pagination']): PaginationMeta {
  return {
    page: pagination.page,
    pageSize: pagination.page_size,
    totalItems: pagination.total_items,
    totalPages: pagination.total_pages,
  }
}

function mapWarehouses(warehouses: DashboardApiResponse['filters']['warehouses']): WarehouseOption[] {
  return warehouses.map((warehouse) => ({ id: warehouse.id, name: warehouse.name }))
}

export async function fetchDashboard(
  filters: ListFilters,
  page: number,
  pageSize: number,
  sort: SortState,
  signal?: AbortSignal,
): Promise<DashboardPayload> {
  const url = buildDashboardUrl(filters, page, pageSize, sort)
  const response = await fetch(url, { signal })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`

    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) {
        detail = body.detail
      }
    } catch {
      // keep default detail
    }

    throw new Error(`Failed to load inventory dashboard: ${detail}`)
  }

  const data = (await response.json()) as DashboardApiResponse

  return {
    summary: {
      inStock: data.summary.in_stock_count,
      outOfStock: data.summary.out_of_stock_count,
    },
    categories: data.filters.categories,
    warehouses: mapWarehouses(data.filters.warehouses),
    items: mapItems(data.items),
    pagination: mapPagination(data.pagination),
  }
}
