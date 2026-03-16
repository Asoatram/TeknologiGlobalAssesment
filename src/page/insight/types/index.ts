import type { StockStatus } from '../../list/types'

export interface InsightKpis {
  totalItems: number
  lowStockItems: number
  outOfStockItems: number
}

export interface InsightWarehouseLowStock {
  warehouseId: number
  warehouseName: string
  lowStockCount: number
}

export interface InsightStatusDistribution {
  status: StockStatus
  count: number
  percentage: number
}

export interface InsightItemsByCategory {
  category: string
  skuCount: number
}

export interface InsightQuantityByCategory {
  category: string
  totalQuantity: number
}

export interface InsightMeta {
  lastSyncAt: string | null
}

export interface InsightPayload {
  kpis: InsightKpis
  lowStockByWarehouse: InsightWarehouseLowStock[]
  statusDistribution: InsightStatusDistribution[]
  itemsByCategory: InsightItemsByCategory[]
  quantityByCategory: InsightQuantityByCategory[]
  meta: InsightMeta
}
