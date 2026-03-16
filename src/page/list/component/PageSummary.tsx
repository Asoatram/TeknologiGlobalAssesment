import type { InventorySummary } from '../types'

const inStockIconUrl = 'https://www.figma.com/api/mcp/asset/86a0c2a9-9bb7-4bde-b1a1-58fb86db8046'
const outOfStockIconUrl = 'https://www.figma.com/api/mcp/asset/90c9bff2-be66-4d24-8f5c-fa34bf506d75'

interface PageSummaryProps {
  summary: InventorySummary
}

export function PageSummary({ summary }: PageSummaryProps) {
  return (
    <section className="list-page-summary">
      <div>
        <h2 className="list-page-title">Inventory List</h2>
        <p className="list-breadcrumbs">Home / Inventory</p>
      </div>

      <div className="list-summary-cards">
        <article className="list-summary-card">
          <img src={inStockIconUrl} alt="In stock" className="list-summary-icon" />
          <div>
            <p className="list-summary-label">IN STOCK</p>
            <p className="list-summary-value">{summary.inStock.toLocaleString()}</p>
          </div>
        </article>

        <article className="list-summary-card">
          <img src={outOfStockIconUrl} alt="Out of stock" className="list-summary-icon" />
          <div>
            <p className="list-summary-label">OUT OF STOCK</p>
            <p className="list-summary-value">{summary.outOfStock.toLocaleString()}</p>
          </div>
        </article>
      </div>
    </section>
  )
}
