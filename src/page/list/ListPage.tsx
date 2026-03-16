import { useEffect, useMemo, useState } from 'react'
import { fetchDashboard } from './api/dashboard'
import { InventoryTable } from './component/InventoryTable'
import { ListToolbar } from './component/ListToolbar'
import { PageSummary } from './component/PageSummary'
import { PaginationBar } from './component/PaginationBar'
import { UploadCsvModal } from './component/UploadCsvModal'
import { validateListFilters } from './form-validation/filters'
import type {
  DashboardPayload,
  InventorySummary,
  ListFilters,
  PaginationMeta,
  SortBy,
  SortState,
} from './types'
import './ListPage.css'

const initialFilters: ListFilters = {
  search: '',
  category: 'all',
  warehouseId: 'all',
  status: 'all',
}

const initialSort: SortState = {
  sortBy: 'last_updated',
  sortOrder: 'desc',
}

const defaultSummary: InventorySummary = {
  inStock: 0,
  outOfStock: 0,
}

const defaultPagination: PaginationMeta = {
  page: 1,
  pageSize: 5,
  totalItems: 0,
  totalPages: 0,
}

export function ListPage() {
  const [filters, setFilters] = useState<ListFilters>(initialFilters)
  const [sort, setSort] = useState<SortState>(initialSort)
  const [data, setData] = useState<DashboardPayload | null>(null)
  const [pagination, setPagination] = useState<PaginationMeta>(defaultPagination)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const validationResult = useMemo(() => validateListFilters(filters), [filters])

  useEffect(() => {
    if (!validationResult.isValid) {
      return
    }

    const abortController = new AbortController()

    async function loadDashboard() {
      try {
        setIsLoading(true)
        setErrorMessage(null)

        const response = await fetchDashboard(
          filters,
          pagination.page,
          pagination.pageSize,
          sort,
          abortController.signal,
        )

        setData(response)
        setPagination(response.pagination)
      } catch (error) {
        if (abortController.signal.aborted) {
          return
        }

        const message = error instanceof Error ? error.message : 'Failed to load dashboard data'
        setErrorMessage(message)
      } finally {
        if (!abortController.signal.aborted) {
          setIsLoading(false)
        }
      }
    }

    loadDashboard()

    return () => abortController.abort()
  }, [filters, pagination.page, pagination.pageSize, sort, validationResult.isValid, refreshKey])

  const updateFilters = (next: ListFilters) => {
    setFilters(next)
    setPagination((prev) => ({ ...prev, page: 1 }))
  }

  const updateSort = (sortBy: SortBy) => {
    setSort((prev) => {
      if (prev.sortBy === sortBy) {
        return { sortBy, sortOrder: prev.sortOrder === 'asc' ? 'desc' : 'asc' }
      }

      return { sortBy, sortOrder: 'asc' }
    })
    setPagination((prev) => ({ ...prev, page: 1 }))
  }

  const currentPage = pagination.page
  const totalItems = pagination.totalItems
  const totalPages = pagination.totalPages

  const showingFrom = totalItems === 0 ? 0 : (currentPage - 1) * pagination.pageSize + 1
  const showingTo = data?.items.length ? showingFrom + data.items.length - 1 : 0

  return (
    <section className="list-page">
      <PageSummary summary={data?.summary ?? defaultSummary} />

      <div className="list-card-wrap">
        <ListToolbar
          filters={filters}
          categories={data?.categories ?? []}
          warehouses={data?.warehouses ?? []}
          searchError={validationResult.errors.search}
          onUploadCsvClick={() => setIsUploadModalOpen(true)}
          onFilterChange={updateFilters}
        />

        {errorMessage && (
          <div className="list-api-state list-api-state--error" role="alert">
            {errorMessage}
          </div>
        )}

        {isLoading && <div className="list-api-state">Loading inventory...</div>}

        <InventoryTable
          items={data?.items ?? []}
          sort={sort}
          onSortChange={updateSort}
        />

        <PaginationBar
          showingFrom={showingFrom}
          showingTo={showingTo}
          totalItems={totalItems}
          currentPage={currentPage}
          totalPages={totalPages || 1}
          pageSize={pagination.pageSize}
          onPageChange={(page) => setPagination((prev) => ({ ...prev, page }))}
          onPageSizeChange={(pageSize) => setPagination((prev) => ({ ...prev, page: 1, pageSize }))}
        />
      </div>

      <UploadCsvModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onImportSuccess={() => setRefreshKey((prev) => prev + 1)}
      />
    </section>
  )
}
