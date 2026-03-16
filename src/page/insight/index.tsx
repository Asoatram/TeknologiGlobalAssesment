import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fetchInsights } from './api/insights'
import type { InsightPayload, InsightStatusDistribution } from './types'
import './InsightPage.css'

const numberFormatter = new Intl.NumberFormat('en-US')

const statusMeta: Record<InsightStatusDistribution['status'], { label: string; color: string }> = {
  in_stock: { label: 'In Stock', color: '#10b981' },
  low_stock: { label: 'Low Stock', color: '#f4b71f' },
  out_of_stock: { label: 'Out Stock', color: '#f43f5e' },
}

const emptyPayload: InsightPayload = {
  kpis: {
    totalItems: 0,
    lowStockItems: 0,
    outOfStockItems: 0,
  },
  lowStockByWarehouse: [],
  statusDistribution: [],
  itemsByCategory: [],
  quantityByCategory: [],
  meta: {
    lastSyncAt: null,
  },
}

function formatNumber(value: number) {
  return numberFormatter.format(value)
}

function formatTooltipNumber(value: unknown) {
  if (typeof value === 'number') {
    return formatNumber(value)
  }

  const parsed = Number(value)
  if (Number.isFinite(parsed)) {
    return formatNumber(parsed)
  }

  return String(value ?? '-')
}

function shortWarehouseLabel(name: string) {
  return name.replace(/^warehouse\s+/i, '').toUpperCase()
}

export function InsightPage() {
  const [data, setData] = useState<InsightPayload>(emptyPayload)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function loadInsights() {
      try {
        setIsLoading(true)
        setErrorMessage(null)

        const payload = await fetchInsights(controller.signal)
        setData(payload)
      } catch (error) {
        if (controller.signal.aborted) {
          return
        }

        const message = error instanceof Error ? error.message : 'Failed to load insights page'
        setErrorMessage(message)
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      }
    }

    loadInsights()

    return () => controller.abort()
  }, [])

  const lowStockChartData = useMemo(() => {
    return data.lowStockByWarehouse.slice(0, 5).map((row) => ({
      id: row.warehouseId,
      label: shortWarehouseLabel(row.warehouseName),
      value: row.lowStockCount,
      fullName: row.warehouseName,
    }))
  }, [data.lowStockByWarehouse])

  const itemsByCategoryData = useMemo(() => {
    return data.itemsByCategory.slice(0, 5).map((row, index) => ({
      id: `${row.category}-${index}`,
      label: row.category,
      value: row.skuCount,
      fill: `rgba(19, 127, 236, ${Math.max(0.38, 1 - index * 0.14)})`,
    }))
  }, [data.itemsByCategory])

  const quantityByCategoryData = useMemo(() => {
    return data.quantityByCategory.slice(0, 5).map((row, index) => ({
      id: `${row.category}-${index}`,
      label: row.category,
      value: row.totalQuantity,
    }))
  }, [data.quantityByCategory])

  const statusList = useMemo(() => {
    const map = new Map(data.statusDistribution.map((row) => [row.status, row]))

    return (['in_stock', 'low_stock', 'out_of_stock'] as const).map((status) => {
      const row = map.get(status)
      return {
        status,
        label: statusMeta[status].label,
        color: statusMeta[status].color,
        count: row?.count ?? 0,
        percentage: row?.percentage ?? 0,
      }
    })
  }, [data.statusDistribution])

  const statusTotalCount = useMemo(() => {
    return statusList.reduce((total, row) => total + row.count, 0)
  }, [statusList])

  const totalQuantity = useMemo(() => {
    return quantityByCategoryData.reduce((sum, row) => sum + row.value, 0)
  }, [quantityByCategoryData])

  return (
    <section className="insight-page" data-node-id="1:262">
      <header className="insight-header" data-node-id="1:263">
        <div>
          <h2 className="insight-title" data-node-id="1:266">
            Inventory Insights
          </h2>
          <p className="insight-subtitle" data-node-id="1:268">
            Overview of inventory levels and operational stock health across all regions
          </p>
        </div>
      </header>

      {errorMessage && (
        <div className="insight-api-state insight-api-state--error" role="alert">
          {errorMessage}
        </div>
      )}

      {isLoading && <div className="insight-api-state">Loading insights...</div>}

      <div className="insight-kpi-grid" data-node-id="1:278">
        <article className="insight-card insight-kpi-card" data-node-id="1:279">
          <p className="insight-kpi-label">TOTAL ITEMS</p>
          <div className="insight-kpi-value-row">
            <strong className="insight-kpi-value">{formatNumber(data.kpis.totalItems)}</strong>
          </div>
        </article>

        <article className="insight-card insight-kpi-card" data-node-id="1:293">
          <p className="insight-kpi-label">LOW STOCK ITEMS</p>
          <div className="insight-kpi-value-row">
            <strong className="insight-kpi-value">{formatNumber(data.kpis.lowStockItems)}</strong>
          </div>
        </article>

        <article className="insight-card insight-kpi-card" data-node-id="1:307">
          <p className="insight-kpi-label">OUT OF STOCK</p>
          <div className="insight-kpi-value-row">
            <strong className="insight-kpi-value">{formatNumber(data.kpis.outOfStockItems)}</strong>
          </div>
        </article>
      </div>

      <div className="insight-grid" data-node-id="1:321">
        <article className="insight-card insight-chart-card" data-node-id="1:322">
          <h3>Low Stock Items by Warehouse</h3>
          <p>Distribution of items below threshold</p>

          <div className="insight-chart-wrap" data-node-id="1:328">
            {lowStockChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={lowStockChartData} margin={{ top: 18, right: 8, left: 8, bottom: 8 }}>
                  <CartesianGrid stroke="#eef2f7" vertical={false} />
                  <XAxis
                    dataKey="label"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#64748b', fontSize: 11, fontWeight: 700 }}
                  />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 11 }} />
                  <Tooltip
                    formatter={(value) => [formatTooltipNumber(value), 'Low stock items']}
                    labelFormatter={(_label, payload) => payload?.[0]?.payload?.fullName ?? ''}
                  />
                  <Bar dataKey="value" fill="#137fec" radius={[8, 8, 0, 0]} maxBarSize={48} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="insight-empty-chart">No warehouse data yet</div>
            )}
          </div>
        </article>

        <article className="insight-card insight-chart-card" data-node-id="1:346">
          <h3>Inventory Status Distribution</h3>
          <p>Overall stock health across catalog</p>

          <div className="insight-status-layout" data-node-id="1:352">
            <div className="insight-donut-wrap">
              <ResponsiveContainer width={192} height={192}>
                <PieChart>
                  <Pie
                    data={statusList}
                    dataKey="count"
                    nameKey="label"
                    innerRadius={62}
                    outerRadius={86}
                    stroke="none"
                    paddingAngle={1}
                  >
                    {statusList.map((slice) => (
                      <Cell key={slice.status} fill={slice.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="insight-donut-center">
                <strong>{statusTotalCount > 0 ? '100%' : '0%'}</strong>
                <span>Total SKUs</span>
              </div>
            </div>

            <ul className="insight-status-legend" data-node-id="1:364">
              {statusList.map((slice) => (
                <li key={slice.status}>
                  <span style={{ backgroundColor: slice.color }} />
                  {`${slice.label} (${slice.percentage.toFixed(0)}%)`}
                </li>
              ))}
            </ul>
          </div>
        </article>

        <article className="insight-card insight-chart-card" data-node-id="1:377">
          <h3>Items by Category</h3>
          <p>SKU count per product vertical</p>

          <div className="insight-chart-wrap insight-chart-wrap--horizontal" data-node-id="1:383">
            {itemsByCategoryData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={itemsByCategoryData}
                  layout="vertical"
                  margin={{ top: 8, right: 12, left: 10, bottom: 8 }}
                  barCategoryGap={14}
                >
                  <CartesianGrid stroke="#eef2f7" horizontal={false} />
                  <XAxis type="number" hide />
                  <YAxis
                    dataKey="label"
                    type="category"
                    width={110}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#64748b', fontSize: 11, fontWeight: 700 }}
                  />
                  <Tooltip formatter={(value) => [`${formatTooltipNumber(value)} items`, 'SKUs']} />
                  <Bar dataKey="value" radius={[0, 8, 8, 0]} barSize={14}>
                    {itemsByCategoryData.map((row) => (
                      <Cell key={row.id} fill={row.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="insight-empty-chart">No category data yet</div>
            )}
          </div>
        </article>

        <article className="insight-card insight-chart-card" data-node-id="1:417">
          <h3>Inventory Quantity by Category</h3>
          <p>Total physical units in warehouses</p>

          <div className="insight-chart-wrap" data-node-id="1:423">
            {quantityByCategoryData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={quantityByCategoryData} margin={{ top: 18, right: 8, left: 8, bottom: 8 }}>
                  <CartesianGrid stroke="#eef2f7" vertical={false} />
                  <XAxis
                    dataKey="label"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#64748b', fontSize: 11, fontWeight: 700 }}
                  />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 11 }} />
                  <Tooltip formatter={(value) => [formatTooltipNumber(value), 'Total units']} />
                  <Bar dataKey="value" fill="#2d87e8" radius={[8, 8, 0, 0]} maxBarSize={48} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="insight-empty-chart">No quantity data yet</div>
            )}
          </div>
          <p className="insight-quantity-footnote">{`${formatNumber(totalQuantity)} total units across all locations`}</p>
        </article>
      </div>
    </section>
  )
}
