import type { InventoryItem, SortBy, SortState } from '../types'
import { StatusBadge } from './StatusBadge'
import { Link } from 'react-router-dom'

interface InventoryTableProps {
  items: InventoryItem[]
  sort: SortState
  onSortChange: (sortBy: SortBy) => void
}

function SortHeader({
  label,
  active,
  order,
  onClick,
}: {
  label: string
  active: boolean
  order: 'asc' | 'desc'
  onClick: () => void
}) {
  return (
    <button
      type="button"
      className={`list-sort-button ${active ? `is-active is-${order}` : ''}`}
      onClick={onClick}
      aria-label={`${label}, sorted ${active ? order : 'not active'}`}
    >
      <span>{label}</span>
      <span className="list-sort-icon" aria-hidden="true">
        <svg viewBox="0 0 10 14" focusable="false">
          <path
            className={`list-sort-chevron ${active && order === 'asc' ? 'is-active' : ''}`}
            d="M5 2L8 5H2L5 2Z"
          />
          <path
            className={`list-sort-chevron ${active && order === 'desc' ? 'is-active' : ''}`}
            d="M5 12L2 9H8L5 12Z"
          />
        </svg>
      </span>
    </button>
  )
}

export function InventoryTable({ items, sort, onSortChange }: InventoryTableProps) {
  return (
    <div className="list-table-container">
      <table className="list-table">
        <thead>
          <tr>
            <th>
              <SortHeader
                label="Item Name"
                active={sort.sortBy === 'name'}
                order={sort.sortOrder}
                onClick={() => onSortChange('name')}
              />
            </th>
            <th>SKU</th>
            <th>Category</th>
            <th>Warehouse</th>
            <th>
              <SortHeader
                label="Qty On Hand"
                active={sort.sortBy === 'quantity'}
                order={sort.sortOrder}
                onClick={() => onSortChange('quantity')}
              />
            </th>
            <th>Threshold</th>
            <th>Status</th>
            <th>
              <SortHeader
                label="Last Updated"
                active={sort.sortBy === 'last_updated'}
                order={sort.sortOrder}
                onClick={() => onSortChange('last_updated')}
              />
            </th>
            <th>More Options</th>
          </tr>
        </thead>

        <tbody>
          {items.length === 0 ? (
            <tr>
              <td className="list-empty-state" colSpan={9}>
                No inventory items match your filters.
              </td>
            </tr>
          ) : (
            items.map((item) => (
              <tr key={item.rowKey}>
                <td className="list-item-name">{item.name}</td>
                <td className="list-item-sku">{item.sku}</td>
                <td>{item.category}</td>
                <td>{item.warehouse}</td>
                <td
                  className={
                    item.status === 'out_of_stock'
                      ? 'list-qty list-qty--out'
                      : item.status === 'low_stock'
                        ? 'list-qty list-qty--low'
                        : 'list-qty'
                  }
                >
                  {item.qtyOnHand}
                </td>
                <td>{item.threshold ?? '-'}</td>
                <td>
                  <StatusBadge status={item.status} />
                </td>
                <td>{item.lastUpdated}</td>
                <td>
                  <Link to={`/inventory/items/sku/${encodeURIComponent(item.sku)}`} className="list-row-link-btn">
                    View
                  </Link>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
