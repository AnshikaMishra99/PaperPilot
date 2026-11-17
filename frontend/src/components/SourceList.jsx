import { useState } from 'react'

/**
 * Sources are presented like footnotes in a printed paper: a hairline rule,
 * the marker that appears in the answer, then the paper and page. Expanding a
 * source shows the exact passage the model was given, so any claim can be
 * checked against the retrieved text.
 */
export default function SourceList({ sources, grounded, activeSource, onToggleSource }) {
  const [internalOpen, setInternalOpen] = useState(null)

  const currentOpen = activeSource !== undefined ? activeSource : internalOpen

  const handleToggle = (idOrLabel) => {
    if (onToggleSource) {
      onToggleSource(currentOpen === idOrLabel ? null : idOrLabel)
    } else {
      setInternalOpen(currentOpen === idOrLabel ? null : idOrLabel)
    }
  }

  if (!sources.length) return null

  return (
    <div className="mt-5 border-t border-line pt-3">
      <p className="text-xs text-muted">
        {grounded
          ? 'Passages cited in this answer'
          : 'Passages retrieved for this question (the answer did not cite them directly)'}
      </p>

      <ol className="mt-2 space-y-1.5">
        {sources.map((source) => {
          const isOpen = currentOpen === source.label || currentOpen === source.chunk_id
          return (
            <li
              key={source.chunk_id}
              id={`source-item-${source.label}`}
              className="text-sm p-1.5 rounded transition-all duration-300"
            >
              <button
                type="button"
                onClick={() => handleToggle(source.label)}
                className="flex w-full items-baseline gap-2 text-left hover:text-pine-700"
                aria-expanded={isOpen}
              >
                <span className="font-read text-xs font-semibold text-ochre bg-ochre/10 px-1.5 py-0.5 rounded">
                  {source.label}
                </span>
                <span className="min-w-0 flex-1 truncate text-ink">{source.filename}</span>
                <span className="text-xs text-muted">page {source.page}</span>
                <span className="text-xs text-muted">{Math.round(source.score * 100)}% match</span>
              </button>

              {isOpen && (
                <p className="mt-2 border-l-2 border-ochre pl-3 font-read text-sm leading-relaxed text-muted bg-pine-50/30 p-2 rounded">
                  {source.excerpt}
                </p>
              )}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
