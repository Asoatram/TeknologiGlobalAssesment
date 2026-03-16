import type { StockStatus } from '../../list/types'
import type {
  InsightPayload,
  InsightStatusDistribution,
  InsightWarehouseLowStock,
  InsightItemsByCategory,
  InsightQuantityByCategory,
} from '../types'

interface InsightsApiResponse {
  kpis: {
    total_items: number
    low_stock_items: number
    out_of_stock_items: number
  }
  low_stock_by_warehouse: Array<{
    warehouse_id: number
    warehouse_name: string
    low_stock_count: number
  }>
  status_distribution: Array<{
    status: StockStatus
    count: number
    percentage: number
  }>
  items_by_category: Array<{
    category: string
    sku_count: number
  }>
  quantity_by_category: Array<{
    category: string
    total_quantity: number
  }>
  meta: {
    last_sync_at: string | null
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

function buildInsightsUrl() {
  return import.meta.env.DEV
    ? new URL('/api/v1/inventory/insights', window.location.origin)
    : new URL('/api/v1/inventory/insights', getBackendUrl())
}

function mapLowStockByWarehouse(
  rows: InsightsApiResponse['low_stock_by_warehouse'],
): InsightWarehouseLowStock[] {
  return rows.map((row) => ({
    warehouseId: row.warehouse_id,
    warehouseName: row.warehouse_name,
    lowStockCount: row.low_stock_count,
  }))
}

function mapStatusDistribution(
  rows: InsightsApiResponse['status_distribution'],
): InsightStatusDistribution[] {
  return rows.map((row) => ({
    status: row.status,
    count: row.count,
    percentage: row.percentage,
  }))
}

function mapItemsByCategory(rows: InsightsApiResponse['items_by_category']): InsightItemsByCategory[] {
  return rows.map((row) => ({
    category: row.category,
    skuCount: row.sku_count,
  }))
}

function mapQuantityByCategory(
  rows: InsightsApiResponse['quantity_by_category'],
): InsightQuantityByCategory[] {
  return rows.map((row) => ({
    category: row.category,
    totalQuantity: row.total_quantity,
  }))
}

export async function fetchInsights(signal?: AbortSignal): Promise<InsightPayload> {
  const response = await fetch(buildInsightsUrl(), { signal })

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

    throw new Error(`Failed to load insights: ${detail}`)
  }

  const data = (await response.json()) as InsightsApiResponse

  return {
    kpis: {
      totalItems: data.kpis.total_items,
      lowStockItems: data.kpis.low_stock_items,
      outOfStockItems: data.kpis.out_of_stock_items,
    },
    lowStockByWarehouse: mapLowStockByWarehouse(data.low_stock_by_warehouse),
    statusDistribution: mapStatusDistribution(data.status_distribution),
    itemsByCategory: mapItemsByCategory(data.items_by_category),
    quantityByCategory: mapQuantityByCategory(data.quantity_by_category),
    meta: {
      lastSyncAt: data.meta.last_sync_at,
    },
  }
}
