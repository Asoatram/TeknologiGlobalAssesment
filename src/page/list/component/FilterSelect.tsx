import { useEffect, useMemo, useRef, useState } from 'react'

export interface FilterOption {
  value: string
  label: string
}

interface FilterSelectProps {
  value: string
  onChange: (value: string) => void
  ariaLabel: string
  options: FilterOption[]
  className?: string
}

export function FilterSelect({ value, onChange, ariaLabel, options, className }: FilterSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement | null>(null)

  const selectedLabel = useMemo(() => {
    return options.find((option) => option.value === value)?.label ?? options[0]?.label ?? ''
  }, [options, value])

  useEffect(() => {
    if (!isOpen) {
      return
    }

    const handlePointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    window.addEventListener('mousedown', handlePointerDown)
    window.addEventListener('keydown', handleEscape)

    return () => {
      window.removeEventListener('mousedown', handlePointerDown)
      window.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  const wrapperClass = `list-select-wrap ${isOpen ? 'is-open' : ''} ${className ?? ''}`.trim()

  return (
    <div className={wrapperClass} ref={rootRef}>
      <button
        type="button"
        className="list-select-trigger"
        aria-label={ariaLabel}
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
      >
        <span className="list-select-value">{selectedLabel}</span>
        <span className="list-select-caret" aria-hidden="true">
          <svg viewBox="0 0 12 8" focusable="false">
            <path
              d="M1 1.5L6 6.5L11 1.5"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
      </button>

      <ul className="list-select-menu" role="listbox" aria-label={ariaLabel} aria-hidden={!isOpen}>
        {options.map((option) => {
          const isSelected = option.value === value

          return (
            <li key={option.value}>
              <button
                type="button"
                role="option"
                aria-selected={isSelected}
                className={`list-select-item ${isSelected ? 'is-selected' : ''}`}
                onClick={() => {
                  onChange(option.value)
                  setIsOpen(false)
                }}
              >
                {option.label}
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
