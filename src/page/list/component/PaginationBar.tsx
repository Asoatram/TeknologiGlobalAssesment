import { FilterSelect, type FilterOption } from './FilterSelect'

interface PaginationBarProps {
  showingFrom: number
  showingTo: number
  totalItems: number
  currentPage: number
  totalPages: number
  pageSize: number
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
}

const prevIconUrl = 'https://www.figma.com/api/mcp/asset/fe807de3-fdbd-4019-9eec-cbcb50916271'
const nextIconUrl = 'https://www.figma.com/api/mcp/asset/0ecc9a8c-ac55-4547-bd76-04dc6ba741b7'
const PAGE_SIZE_OPTIONS = [5, 10, 20, 50, 100]

const pageSizeOptions: FilterOption[] = PAGE_SIZE_OPTIONS.map((size) => ({
  value: String(size),
  label: String(size),
}))

type PageToken = number | 'ellipsis-left' | 'ellipsis-right'

function buildPageTokens(currentPage: number, totalPages: number): PageToken[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1)
  }

  const tokens: PageToken[] = [1]
  const start = Math.max(2, currentPage - 1)
  const end = Math.min(totalPages - 1, currentPage + 1)

  if (start > 2) {
    tokens.push('ellipsis-left')
  }

  for (let page = start; page <= end; page += 1) {
    tokens.push(page)
  }

  if (end < totalPages - 1) {
    tokens.push('ellipsis-right')
  }

  tokens.push(totalPages)
  return tokens
}

export function PaginationBar({
  showingFrom,
  showingTo,
  totalItems,
  currentPage,
  totalPages,
  pageSize,
  onPageChange,
  onPageSizeChange,
}: PaginationBarProps) {
  const canGoPrev = currentPage > 1
  const canGoNext = currentPage < totalPages

  const pageTokens = buildPageTokens(currentPage, totalPages)

  return (
    <footer className="list-pagination-bar">
      <div className="list-pagination-left">
        <p>
          Showing <strong>{showingFrom}</strong> to <strong>{showingTo}</strong> of <strong>{totalItems}</strong>{' '}
          items
        </p>

        <label className="list-page-size-wrap">
          <span>Rows</span>
          <FilterSelect
            className="list-page-size-select-wrap"
            value={String(pageSize)}
            onChange={(value) => onPageSizeChange(Number(value))}
            ariaLabel="Rows per page"
            options={pageSizeOptions}
          />
        </label>
      </div>

      <div className="list-pagination-actions">
        <button
          type="button"
          className="list-page-nav list-page-nav--muted"
          aria-label="Previous page"
          disabled={!canGoPrev}
          onClick={() => canGoPrev && onPageChange(currentPage - 1)}
        >
          <img src={prevIconUrl} alt="" aria-hidden="true" />
        </button>

        {pageTokens.map((token) =>
          typeof token === 'number' ? (
            <button
              type="button"
              key={token}
              className={`list-page-number ${currentPage === token ? 'list-page-number--active' : ''}`}
              onClick={() => onPageChange(token)}
            >
              {token}
            </button>
          ) : (
            <span key={token} className="list-page-ellipsis">
              ...
            </span>
          ),
        )}

        <button
          type="button"
          className="list-page-nav"
          aria-label="Next page"
          disabled={!canGoNext}
          onClick={() => canGoNext && onPageChange(currentPage + 1)}
        >
          <img src={nextIconUrl} alt="" aria-hidden="true" />
        </button>
      </div>
    </footer>
  )
}
