import { FilterSelect, type FilterOption } from './FilterSelect'
import type { ListFilters, WarehouseOption } from '../types'

const searchIconUrl = 'https://www.figma.com/api/mcp/asset/681a5c4b-dc84-4cdc-be5f-699b84eed365'
const uploadIconUrl = 'https://www.figma.com/api/mcp/asset/192b43de-da0f-4323-822c-a4d2f29aacb5'

interface ListToolbarProps {
  filters: ListFilters
  categories: string[]
  warehouses: WarehouseOption[]
  searchError?: string
  onUploadCsvClick: () => void
  onFilterChange: (next: ListFilters) => void
}

export function ListToolbar({
  filters,
  categories,
  warehouses,
  searchError,
  onUploadCsvClick,
  onFilterChange,
}: ListToolbarProps) {
  const updateFilter = <K extends keyof ListFilters>(key: K, value: ListFilters[K]) => {
    onFilterChange({ ...filters, [key]: value })
  }

  const categoryOptions: FilterOption[] = [
    { value: 'all', label: 'All Categories' },
    ...categories.map((category) => ({ value: category, label: category })),
  ]

  const warehouseOptions: FilterOption[] = [
    { value: 'all', label: 'All Warehouses' },
    ...warehouses.map((warehouse) => ({ value: String(warehouse.id), label: warehouse.name })),
  ]

  const statusOptions: FilterOption[] = [
    { value: 'all', label: 'All Stock Status' },
    { value: 'in_stock', label: 'In Stock' },
    { value: 'low_stock', label: 'Low Stock' },
    { value: 'out_of_stock', label: 'Out of Stock' },
  ]

  return (
    <section className="list-toolbar-wrap">
      <div className="list-toolbar-left">
        <label className="list-search-input-wrap" aria-label="Search">
          <img src={searchIconUrl} alt="Search" className="list-search-icon" />
          <input
            className="list-search-input"
            placeholder="Search item name or SKU..."
            value={filters.search}
            onChange={(event) => updateFilter('search', event.target.value)}
          />
        </label>

        <FilterSelect
          value={filters.category}
          onChange={(value) => updateFilter('category', value)}
          ariaLabel="Category"
          options={categoryOptions}
        />

        <FilterSelect
          value={filters.warehouseId === 'all' ? 'all' : String(filters.warehouseId)}
          onChange={(value) => updateFilter('warehouseId', value === 'all' ? 'all' : Number(value))}
          ariaLabel="Warehouse"
          options={warehouseOptions}
        />

        <FilterSelect
          value={filters.status}
          onChange={(value) => updateFilter('status', value as ListFilters['status'])}
          ariaLabel="Stock status"
          options={statusOptions}
        />
      </div>

      <div className="list-toolbar-right">
        <button type="button" className="list-upload-btn" onClick={onUploadCsvClick}>
          <img src={uploadIconUrl} alt="" aria-hidden="true" />
          Upload CSV
        </button>
      </div>

      {searchError && <p className="list-search-error">{searchError}</p>}
    </section>
  )
}
