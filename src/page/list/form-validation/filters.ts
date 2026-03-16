import type { FilterValidationResult, ListFilters } from '../types'

const MAX_SEARCH_LENGTH = 120

export function validateListFilters(filters: ListFilters): FilterValidationResult {
  const errors: FilterValidationResult['errors'] = {}

  if (filters.search.length > MAX_SEARCH_LENGTH) {
    errors.search = `Search must be ${MAX_SEARCH_LENGTH} characters or less.`
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  }
}
