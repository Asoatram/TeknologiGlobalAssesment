import { useEffect, useMemo, useRef, useState, type MouseEvent } from 'react'
import { confirmInventoryImportRows, uploadInventoryCsv } from '../api/imports'
import type { InventoryImportResponse } from '../types'

interface UploadCsvModalProps {
  isOpen: boolean
  onClose: () => void
  onImportSuccess: () => void
}

export function UploadCsvModal({ isOpen, onClose, onImportSuccess }: UploadCsvModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragActive, setIsDragActive] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [importResult, setImportResult] = useState<InventoryImportResponse | null>(null)
  const [editableRows, setEditableRows] = useState<InventoryImportResponse['validation_errors']>([])
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    if (!isOpen) {
      setSelectedFile(null)
      setIsDragActive(false)
      setIsSubmitting(false)
      setSubmitError(null)
      setImportResult(null)
      setEditableRows([])
      return
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isSubmitting) {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = previousOverflow
    }
  }, [isOpen, isSubmitting, onClose])

  const fileLabel = useMemo(() => {
    if (!selectedFile) {
      return 'Drag and drop CSV file or click to upload'
    }

    return selectedFile.name
  }, [selectedFile])

  if (!isOpen) {
    return null
  }

  const stopBackdropClose = (event: MouseEvent<HTMLDivElement>) => {
    event.stopPropagation()
  }

  const onSelectFile = (file: File | null) => {
    if (!file) {
      return
    }

    setSelectedFile(file)
    setSubmitError(null)
    setImportResult(null)
  }

  const handleSubmit = async () => {
    if (!selectedFile || isSubmitting) {
      return
    }

    try {
      setIsSubmitting(true)
      setSubmitError(null)

      const response = await uploadInventoryCsv(selectedFile)
      const shouldClose =
        response.validation_errors.length === 0 ||
        response.document.pending_rows === 0 ||
        response.document.status === 'completed'

      if (shouldClose) {
        onImportSuccess()
        onClose()
        return
      }

      setImportResult(response)
      setEditableRows(response.validation_errors)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to upload CSV'
      setSubmitError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const toApiTimestamp = (value: string) => {
    if (!value) {
      return value
    }

    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) {
      return value
    }

    return parsed.toISOString()
  }

  const handleConfirmEdits = async () => {
    if (!importResult || editableRows.length === 0 || isSubmitting) {
      return
    }

    try {
      setIsSubmitting(true)
      setSubmitError(null)

      const payloadRows = editableRows.map((row) => ({
        parsed_event_id: row.parsed_event_id,
        sku: row.sku,
        warehouse: row.warehouse,
        transaction_type: row.transaction_type,
        quantity: row.quantity,
        timestamp: toApiTimestamp(row.timestamp),
      }))

      const response = await confirmInventoryImportRows(importResult.document.document_id, payloadRows)
      const shouldClose =
        response.validation_errors.length === 0 ||
        response.document.pending_rows === 0 ||
        response.document.status === 'completed'

      if (shouldClose) {
        onImportSuccess()
        onClose()
        return
      }

      const mergedReferences = response.references ?? importResult.references
      setImportResult({ ...response, references: mergedReferences })
      setEditableRows(response.validation_errors)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to confirm edited rows'
      setSubmitError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const isActionRequired = (importResult?.document.rejected_rows ?? 0) > 0
  const skuOptions = importResult?.references?.available_skus ?? []
  const warehouseOptions = importResult?.references?.available_warehouses ?? []
  const transactionTypeOptions = importResult?.references?.available_transaction_types ?? []

  const toDatetimeLocal = (value: string) => {
    if (!value) {
      return ''
    }

    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) {
      return ''
    }

    const pad = (num: number) => String(num).padStart(2, '0')
    const year = parsed.getFullYear()
    const month = pad(parsed.getMonth() + 1)
    const day = pad(parsed.getDate())
    const hour = pad(parsed.getHours())
    const minute = pad(parsed.getMinutes())
    return `${year}-${month}-${day}T${hour}:${minute}`
  }

  const updateEditableRow = (
    parsedEventId: number,
    field: 'sku' | 'warehouse' | 'transaction_type' | 'quantity' | 'timestamp',
    value: string,
  ) => {
    setEditableRows((prev) =>
      prev.map((row) => (row.parsed_event_id === parsedEventId ? { ...row, [field]: value } : row)),
    )
  }

  return (
    <div className="upload-modal-backdrop" onClick={() => !isSubmitting && onClose()} role="presentation">
      <section
        className="upload-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-modal-title"
        onClick={stopBackdropClose}
      >
        <header className="upload-modal-header">
          <h2 id="upload-modal-title" className="upload-modal-title">
            <span className="upload-modal-title-icon" aria-hidden="true">
              <svg viewBox="0 0 16 20" focusable="false">
                <path d="M3 0a3 3 0 0 0-3 3v14a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3V6.2a3 3 0 0 0-.88-2.12L11.92.88A3 3 0 0 0 9.8 0H3Zm8 2.25 2.75 2.74a1 1 0 0 1 .25.66V6h-2a1 1 0 0 1-1-1V2.25ZM8 7a1 1 0 0 1 1 1v2.58l.8-.79a1 1 0 1 1 1.4 1.42l-2.5 2.45a1 1 0 0 1-1.4 0l-2.5-2.45A1 1 0 0 1 6.2 9.8l.8.78V8a1 1 0 0 1 1-1Zm-4 9a1 1 0 1 1 0-2h8a1 1 0 1 1 0 2H4Z" />
              </svg>
            </span>
            Upload Inventory Transactions
          </h2>
          <button
            type="button"
            className="upload-modal-close"
            onClick={onClose}
            aria-label="Close upload dialog"
            disabled={isSubmitting}
          >
            <svg viewBox="0 0 16 16" focusable="false">
              <path d="M3.34 2.27a.75.75 0 0 0-1.06 1.06L6.94 8l-4.66 4.67a.75.75 0 1 0 1.06 1.06L8 9.06l4.67 4.67a.75.75 0 0 0 1.06-1.06L9.06 8l4.67-4.67a.75.75 0 0 0-1.06-1.06L8 6.94 3.34 2.27Z" />
            </svg>
          </button>
        </header>

        <div className="upload-modal-body">
          <div
            className={`upload-dropzone${isDragActive ? ' is-drag-active' : ''}${isSubmitting ? ' is-disabled' : ''}`}
            onClick={() => !isSubmitting && fileInputRef.current?.click()}
            onDragOver={(event) => {
              event.preventDefault()
              if (!isSubmitting) {
                setIsDragActive(true)
              }
            }}
            onDragLeave={() => setIsDragActive(false)}
            onDrop={(event) => {
              event.preventDefault()
              setIsDragActive(false)
              if (isSubmitting) {
                return
              }
              onSelectFile(event.dataTransfer.files?.[0] ?? null)
            }}
            role="button"
            tabIndex={isSubmitting ? -1 : 0}
            onKeyDown={(event) => {
              if ((event.key === 'Enter' || event.key === ' ') && !isSubmitting) {
                event.preventDefault()
                fileInputRef.current?.click()
              }
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              className="upload-dropzone-input"
              onChange={(event) => onSelectFile(event.target.files?.[0] ?? null)}
              disabled={isSubmitting}
            />
            <div className="upload-dropzone-icon" aria-hidden="true">
              <svg viewBox="0 0 28 20" focusable="false">
                <path d="M10.25 16h8a5.75 5.75 0 0 0 .95-11.42A6.73 6.73 0 0 0 6.9 5.72 5.5 5.5 0 0 0 6.25 16h4Zm4.53-10.53a1.1 1.1 0 0 0-1.56 0L9.6 9.1a1.1 1.1 0 0 0 1.56 1.56l1.73-1.73V14a1.1 1.1 0 1 0 2.2 0V8.93l1.74 1.73a1.1 1.1 0 1 0 1.55-1.56l-3.6-3.63Z" />
              </svg>
            </div>
            <p className="upload-dropzone-title">{fileLabel}</p>
            <p className="upload-dropzone-subtitle">Maximum file size: 10MB</p>
          </div>

          <div className="upload-modal-grid">
            <section>
              <h4 className="upload-modal-caption">Supported Format (CSV)</h4>
              <pre className="upload-modal-code">sku,warehouse,transaction_type,quantity,timestamp</pre>
            </section>
            <section>
              <h4 className="upload-modal-caption">Transaction Types</h4>
              <div className="upload-type-tags" aria-label="Transaction types">
                <span className="upload-type-tag upload-type-tag--restock">restock</span>
                <span className="upload-type-tag upload-type-tag--sale">sale</span>
                <span className="upload-type-tag upload-type-tag--adjustment">adjustment</span>
              </div>
            </section>
          </div>

          {submitError && (
            <div className="upload-submit-error" role="alert">
              {submitError}
            </div>
          )}

          {importResult && (
            <section className="upload-summary-wrap" aria-label="Import summary preview">
              <div className="upload-summary-header">
                <h3 className="upload-summary-title">Import Summary</h3>
                <span
                  className={`upload-summary-chip ${
                    isActionRequired ? 'upload-summary-chip--warning' : 'upload-summary-chip--success'
                  }`}
                >
                  <svg viewBox="0 0 13 12" focusable="false">
                    <path d="M7.1 1.02c-.27-.46-.94-.46-1.21 0L.4 10.25a.7.7 0 0 0 .61 1.05h10.98a.7.7 0 0 0 .61-1.05L7.1 1.02Zm-.6 3.17c.4 0 .73.31.73.7v2.38a.72.72 0 0 1-1.45 0V4.89c0-.39.33-.7.72-.7Zm0 4.9c.43 0 .78.33.78.74s-.35.74-.78.74a.76.76 0 0 1-.78-.74c0-.4.35-.73.78-.73Z" />
                  </svg>
                  {isActionRequired ? 'Action Required' : 'Ready'}
                </span>
              </div>

              <div className="upload-summary-cards">
                <article className="upload-summary-card upload-summary-card--total">
                  <p>Total Rows</p>
                  <strong>{importResult.document.total_rows}</strong>
                </article>
                <article className="upload-summary-card upload-summary-card--accepted">
                  <p>Accepted</p>
                  <strong>{importResult.document.accepted_rows}</strong>
                </article>
                <article className="upload-summary-card upload-summary-card--rejected">
                  <p>Rejected</p>
                  <strong>{importResult.document.rejected_rows}</strong>
                </article>
              </div>

              {editableRows.length > 0 && (
                <div className="upload-rejected-table-wrap">
                  <table className="upload-rejected-table">
                    <thead>
                      <tr>
                        <th>Row</th>
                        <th>SKU</th>
                        <th>Warehouse</th>
                        <th>Transaction Type</th>
                        <th>Quantity</th>
                        <th>Timestamp</th>
                        <th>Error Message</th>
                      </tr>
                    </thead>
                    <tbody>
                      {editableRows.map((row) => (
                        <tr key={row.parsed_event_id}>
                          <td>{row.row_number}</td>
                          <td>
                            <input
                              className="upload-cell-input"
                              value={row.sku}
                              list="upload-sku-options"
                              onChange={(event) => updateEditableRow(row.parsed_event_id, 'sku', event.target.value)}
                              aria-label={`SKU row ${row.row_number}`}
                            />
                          </td>
                          <td>
                            <select
                              className="upload-cell-input upload-cell-select"
                              value={row.warehouse}
                              onChange={(event) =>
                                updateEditableRow(row.parsed_event_id, 'warehouse', event.target.value)
                              }
                              aria-label={`Warehouse row ${row.row_number}`}
                            >
                              {!warehouseOptions.includes(row.warehouse) && (
                                <option value={row.warehouse}>{row.warehouse}</option>
                              )}
                              {warehouseOptions.map((warehouse) => (
                                <option key={warehouse} value={warehouse}>
                                  {warehouse}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <select
                              className="upload-cell-input upload-cell-select"
                              value={row.transaction_type}
                              onChange={(event) =>
                                updateEditableRow(row.parsed_event_id, 'transaction_type', event.target.value)
                              }
                              aria-label={`Transaction type row ${row.row_number}`}
                            >
                              {!transactionTypeOptions.includes(row.transaction_type) && (
                                <option value={row.transaction_type}>{row.transaction_type}</option>
                              )}
                              {transactionTypeOptions.map((transactionType) => (
                                <option key={transactionType} value={transactionType}>
                                  {transactionType}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <input
                              className="upload-cell-input"
                              value={row.quantity}
                              onChange={(event) =>
                                updateEditableRow(row.parsed_event_id, 'quantity', event.target.value)
                              }
                              aria-label={`Quantity row ${row.row_number}`}
                            />
                          </td>
                          <td>
                            <input
                              className="upload-cell-input"
                              type="datetime-local"
                              value={toDatetimeLocal(row.timestamp)}
                              onChange={(event) =>
                                updateEditableRow(row.parsed_event_id, 'timestamp', event.target.value)
                              }
                              aria-label={`Timestamp row ${row.row_number}`}
                            />
                          </td>
                          <td>
                            <span className="upload-error-cell">
                              <svg viewBox="0 0 12 12" focusable="false" aria-hidden="true">
                                <path d="M6 0a6 6 0 1 0 0 12A6 6 0 0 0 6 0Zm0 9.25a.76.76 0 0 1-.78-.74c0-.4.35-.73.78-.73s.78.33.78.73-.35.74-.78.74Zm.72-5.5V6.5a.72.72 0 0 1-1.44 0V3.75a.72.72 0 0 1 1.44 0Z" />
                              </svg>
                              <span className="upload-cell-pill">{row.error_message}</span>
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <datalist id="upload-sku-options">
                    {skuOptions.map((sku) => (
                      <option key={sku} value={sku} />
                    ))}
                  </datalist>
                </div>
              )}
            </section>
          )}
        </div>

        <footer className="upload-modal-footer">
          <button type="button" className="upload-modal-cancel" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </button>
          <button
            type="button"
            className="upload-modal-confirm"
            onClick={importResult ? handleConfirmEdits : handleSubmit}
            disabled={importResult ? isSubmitting || editableRows.length === 0 : !selectedFile || isSubmitting}
          >
            <svg viewBox="0 0 12 12" focusable="false" aria-hidden="true">
              <path d="M6 0a6 6 0 1 0 0 12A6 6 0 0 0 6 0Zm2.67 4.66-3 3a.73.73 0 0 1-1.04 0l-1.3-1.3a.73.73 0 0 1 1.04-1.04l.78.78 2.48-2.48a.73.73 0 1 1 1.04 1.04Z" />
            </svg>
            {isSubmitting ? 'Processing...' : importResult ? 'Apply Corrections' : 'Upload and Process'}
          </button>
        </footer>
      </section>
    </div>
  )
}
