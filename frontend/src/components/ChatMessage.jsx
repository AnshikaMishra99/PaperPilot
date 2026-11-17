import { useState } from 'react'
import SourceList from './SourceList.jsx'

/**
 * Renders answer text, turning the model's [S1] citation markers into interactive
 * linked badges so users can click any citation and immediately jump to the source footnote.
 */
function renderWithCitations(text, onSelectSource) {
  // Matches [S1], [s1], [S1, S2], [S1][S2], etc. (case-insensitive)
  const regex = /(\[\s*[Ss]\d+(?:\s*,\s*[Ss]\d+)*\s*\])/gi
  const parts = text.split(regex)

  return parts.map((part, index) => {
    const match = part.match(/^\[(.*)\]$/)
    if (!match) return <span key={index}>{part}</span>

    const labels = match[1]
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter((s) => /^S\d+$/.test(s))

    if (!labels.length) return <span key={index}>{part}</span>

    return (
      <span key={index} className="inline-flex items-center align-baseline">
        {labels.map((label) => (
          <button
            key={label}
            type="button"
            onClick={() => onSelectSource(label)}
            title={`Jump to source ${label}`}
            className="inline-flex items-center justify-center ml-1 px-1.5 py-0.5 rounded font-mono text-[0.72rem] font-semibold text-ochre bg-ochre/10 hover:bg-ochre hover:text-white border border-ochre/30 transition-all cursor-pointer shadow-2xs select-none"
          >
            [{label}]
          </button>
        ))}
      </span>
    )
  })
}

export default function ChatMessage({ message }) {
  const [activeSource, setActiveSource] = useState(null)

  const handleSelectSource = (label) => {
    setActiveSource(label)
    const el = document.getElementById(`source-item-${label}`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el.classList.add('ring-2', 'ring-ochre', 'bg-ochre/10')
      setTimeout(() => {
        el.classList.remove('ring-2', 'ring-ochre', 'bg-ochre/10')
      }, 2500)
    }
  }

  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <p className="max-w-reading rounded-lg rounded-br-sm bg-pine-600 px-4 py-2.5 text-sm leading-relaxed text-white">
          {message.content}
        </p>
      </div>
    )
  }

  if (message.role === 'error') {
    return (
      <div className="max-w-reading rounded-lg border border-flag/30 bg-flag/5 px-4 py-3">
        <p className="text-sm text-flag">{message.content}</p>
        {message.detail && <p className="mt-1 text-xs text-flag/70">{message.detail}</p>}
      </div>
    )
  }

  return (
    <div className="max-w-reading">
      <article className="whitespace-pre-wrap font-read text-[0.975rem] leading-[1.7] text-ink">
        {renderWithCitations(message.content, handleSelectSource)}
      </article>

      <SourceList
        sources={message.sources || []}
        grounded={message.grounded}
        activeSource={activeSource}
        onToggleSource={setActiveSource}
      />

      {message.mode && (
        <p className="mt-3 text-xs text-muted">
          Answered in {message.mode === 'technical' ? 'technical' : 'plain-language'} mode
          {message.documentsSearched ? ` across ${message.documentsSearched} paper(s)` : ''}
        </p>
      )}
    </div>
  )
}
