import { Link, useNavigate, useParams } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import type { StockStatus } from '../list/types'
import './ItemDetailsPage.css'

type ItemEventType = 'sale' | 'restock' | 'adjustment' | string

interface ItemDetailsApiResponse {
  item: {
    item_id: number
    sku: string
    name: string
    category: string
  }
  stock_overview: {
    total_units: number
    warehouses_count: number
    in_stock_warehouses: number
    low_stock_warehouses: number
    out_of_stock_warehouses: number
  }
  stock_levels: Array<{
    warehouse_id: number
    warehouse_name: string
    quantity_on_hand: number
    reorder_threshold: number | null
    stock_status: StockStatus
    last_updated: string
  }>
  transaction_history: {
    page: number
    page_size: number
    total_records: number
    total_pages: number
    records: Array<{
      transaction_id: number
      timestamp: string
      warehouse_id: number
      warehouse_name: string
      event_type: ItemEventType
      quantity_change: number
    }>
  }
  supplier_info: {
    supplier_name: string | null
    supplier_id: string | null
    email: string | null
    phone: string | null
  }
  quick_insight: {
    message: string
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

function buildItemDetailsUrl(sku: string) {
  const encodedSku = encodeURIComponent(sku)
  const url = import.meta.env.DEV
    ? new URL(`/api/v1/inventory/items/by-sku/${encodedSku}/details`, window.location.origin)
    : new URL(`/api/v1/inventory/items/by-sku/${encodedSku}/details`, getBackendUrl())

  url.searchParams.set('transaction_page', '1')
  url.searchParams.set('transaction_page_size', '10')

  return url
}

function toTitle(value: string) {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatStockLevelDate(value: string) {
  const parsed = new Date(value)

  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  })
    .format(parsed)
    .replace(',', '')
}

function formatTransactionDate(value: string) {
  const parsed = new Date(value)

  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  }).format(parsed)
}

function statusLabel(status: StockStatus) {
  if (status === 'in_stock') {
    return 'In Stock'
  }

  if (status === 'low_stock') {
    return 'Low Stock'
  }

  return 'Out of Stock'
}

function EventType({ eventType }: { eventType: ItemEventType }) {
  const normalized = eventType.toLowerCase()
  const className =
    normalized === 'restock'
      ? 'item-details-event item-details-event--restock'
      : normalized === 'sale'
        ? 'item-details-event item-details-event--sale'
        : 'item-details-event item-details-event--adjustment'

  const icon =
    normalized === 'restock' ? '+' : normalized === 'sale' ? '-' : '~'

  return (
    <span className={className}>
      <span className="item-details-event-icon">{icon}</span>
      {toTitle(normalized)}
    </span>
  )
}

export function ItemDetailsPage() {
  const navigate = useNavigate()
  const { sku } = useParams<{ sku: string }>()
  const [data, setData] = useState<ItemDetailsApiResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!sku) {
      return
    }
    const resolvedSku = sku

    const controller = new AbortController()

    async function loadDetails() {
      try {
        setIsLoading(true)
        setErrorMessage(null)

        const response = await fetch(buildItemDetailsUrl(resolvedSku), { signal: controller.signal })

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

          throw new Error(`Failed to load item details: ${detail}`)
        }

        const payload = (await response.json()) as ItemDetailsApiResponse
        setData(payload)
      } catch (error) {
        if (controller.signal.aborted) {
          return
        }

        const message = error instanceof Error ? error.message : 'Failed to load item details'
        setErrorMessage(message)
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      }
    }

    loadDetails()

    return () => controller.abort()
  }, [sku])

  const totalUnits = useMemo(() => data?.stock_overview.total_units ?? 0, [data])

  return (
    <section className="item-details-page">
      <div className="item-details-topbar">
        <nav className="item-details-breadcrumbs" aria-label="Breadcrumb">
          <span>Home</span>
          <span>/</span>
          <Link to="/inventory">Inventory</Link>
          <span>/</span>
          <strong>Item Details</strong>
        </nav>

        <button
          type="button"
          className="item-details-back-btn"
          onClick={() => {
            if (window.history.length > 1) {
              navigate(-1)
              return
            }
            navigate('/inventory')
          }}
        >
          Go Back
        </button>
      </div>

      {errorMessage && (
        <div className="item-details-state item-details-state--error" role="alert">
          {errorMessage}
        </div>
      )}

      {isLoading && <div className="item-details-state">Loading item details...</div>}

      {data && (
        <>
          <header className="item-details-header-card">
            <div className="item-details-header-left">
              <div className="item-details-header-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M7 4a2 2 0 0 0-2 2v2H3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2v2a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-2h2a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2h-2V6a2 2 0 0 0-2-2H7Zm0 2h10v4H7V6Zm-4 4h18v6H3v-6Zm4 8h10v2H7v-2Z" />
                </svg>
              </div>
              <div>
                <p className="item-details-label">Inventory Item</p>
                <h1 className="item-details-title">{data.item.name}</h1>
                <div className="item-details-tags">
                  <span>SKU: {data.item.sku}</span>
                  <span>Category: {data.item.category}</span>
                </div>
              </div>
            </div>

          </header>

          <div className="item-details-grid">
            <main className="item-details-main">
              <section className="item-details-card">
                <div className="item-details-card-head">
                  <h2>Stock Levels</h2>
                  <p>Total: {totalUnits} units</p>
                </div>
                <div className="item-details-table-wrap">
                  <table className="item-details-table">
                    <thead>
                      <tr>
                        <th>Warehouse</th>
                        <th>Quantity</th>
                        <th>Threshold</th>
                        <th>Status</th>
                        <th>Last Updated</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.stock_levels.map((stockLevel) => (
                        <tr key={stockLevel.warehouse_id}>
                          <td className="item-details-warehouse">{stockLevel.warehouse_name}</td>
                          <td>{stockLevel.quantity_on_hand}</td>
                          <td>{stockLevel.reorder_threshold ?? '-'}</td>
                          <td>
                            <span className={`item-details-status item-details-status--${stockLevel.stock_status}`}>
                              {statusLabel(stockLevel.stock_status)}
                            </span>
                          </td>
                          <td className="item-details-date">{formatStockLevelDate(stockLevel.last_updated)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="item-details-card">
                <div className="item-details-card-head">
                  <h2>Transaction History</h2>
                </div>

                <div className="item-details-table-wrap">
                  <table className="item-details-table">
                    <thead>
                      <tr>
                        <th>Timestamp</th>
                        <th>Warehouse</th>
                        <th>Event Type</th>
                        <th>Qty Change</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.transaction_history.records.map((record) => (
                        <tr key={record.transaction_id}>
                          <td className="item-details-date">{formatTransactionDate(record.timestamp)}</td>
                          <td className="item-details-warehouse">{record.warehouse_name}</td>
                          <td>
                            <EventType eventType={record.event_type} />
                          </td>
                          <td
                            className={
                              record.quantity_change > 0
                                ? 'item-details-qty item-details-qty--plus'
                                : record.quantity_change < 0
                                  ? 'item-details-qty item-details-qty--minus'
                                  : 'item-details-qty'
                            }
                          >
                            {record.quantity_change > 0 ? `+${record.quantity_change}` : record.quantity_change}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </main>

            <aside className="item-details-side">
              <section className="item-details-card item-details-supplier-card">
                <h3>Supplier Information</h3>
                <div>
                  <p className="item-details-supplier-name">Lorem Ipsum Supplier</p>
                  <p className="item-details-supplier-id">Supplier ID: LRM-001</p>
                </div>
                <div className="item-details-supplier-contact">
                  <p>lorem.ipsum@example.com</p>
                  <p>+1 (000) 000-0000</p>
                  <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
                </div>
              </section>

              <section className="item-details-card item-details-insight-card">
                <h3>Quick Insight</h3>
                <p>{data.quick_insight.message}</p>
              </section>
            </aside>
          </div>
        </>
      )}
    </section>
  )
}
