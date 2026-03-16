import type { InventoryImportResponse } from '../types'

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

function buildInventoryImportUrl() {
  return import.meta.env.DEV
    ? new URL('/api/v1/inventory/imports', window.location.origin)
    : new URL('/api/v1/inventory/imports', getBackendUrl())
}

function buildInventoryImportConfirmUrl(documentId: number) {
  return import.meta.env.DEV
    ? new URL(`/api/v1/inventory/imports/${documentId}/confirm`, window.location.origin)
    : new URL(`/api/v1/inventory/imports/${documentId}/confirm`, getBackendUrl())
}

interface ConfirmImportRowInput {
  parsed_event_id: number
  sku: string
  warehouse: string
  transaction_type: string
  quantity: string
  timestamp: string
}

export async function uploadInventoryCsv(file: File): Promise<InventoryImportResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(buildInventoryImportUrl(), {
    method: 'POST',
    body: formData,
  })

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

    throw new Error(`Failed to upload CSV: ${detail}`)
  }

  return (await response.json()) as InventoryImportResponse
}

export async function confirmInventoryImportRows(
  documentId: number,
  rows: ConfirmImportRowInput[],
): Promise<InventoryImportResponse> {
  const response = await fetch(buildInventoryImportConfirmUrl(documentId), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ rows }),
  })

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

    throw new Error(`Failed to confirm edited rows: ${detail}`)
  }

  return (await response.json()) as InventoryImportResponse
}
