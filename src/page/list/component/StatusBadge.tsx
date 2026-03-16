import type { StockStatus } from '../types'

interface StatusBadgeProps {
  status: StockStatus
}

const statusLabels: Record<StockStatus, string> = {
  in_stock: 'In Stock',
  low_stock: 'Low Stock',
  out_of_stock: 'Out of Stock',
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`list-status-badge list-status-badge--${status}`}>{statusLabels[status]}</span>
}
