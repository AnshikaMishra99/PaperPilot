import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import ChatMessage from '../components/ChatMessage.jsx'
import ModeToggle from '../components/ModeToggle.jsx'
import { api } from '../api/client.js'
import { useApp } from '../useApp.js'

const STARTERS = [
  'What problem does this paper address?',
  'What methodology is used?',
  'What are the main findings?',
  'What limitations do the authors acknowledge?',
]

const COMPARE_STARTER = 'Compare the methodologies used in these papers.'

export default function ChatPage() {
  const { documents, messages, setMessages, mode, setMode, health, openSettings } = useApp()

  const [question, setQuestion] = useState('')
  const [pending, setPending] = useState(false)
  const [selected, setSelected] = useState([])
  const [showFilter, setShowFilter] = useState(false)
  const endRef = useRef(null)

  // Drop selections that point at papers which have since been deleted.
  useEffect(() => {
    const ids = new Set(documents.map((doc) => doc.id))
    setSelected((current) => current.filter((id) => ids.has(id)))
  }, [documents])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, pending])

  const starters = useMemo(
    () => (documents.length > 1 ? [...STARTERS, COMPARE_STARTER] : STARTERS),
    [documents.length],
  )

  const send = async (text) => {
    const trimmed = (text ?? question).trim()
    if (!trimmed || pending) return

    const history = messages
      .filter((message) => message.role === 'user' || message.role === 'assistant')
      .slice(-6)
      .map((message) => ({ role: message.role, content: message.content }))

    setMessages((current) => [...current, { id: crypto.randomUUID(), role: 'user', content: trimmed }])
    setQuestion('')
    setPending(true)

    try {
      const response = await api.ask({
        question: trimmed,
        mode,
        documentIds: selected,
        history,
      })
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          grounded: response.grounded,
          mode: response.mode,
          documentsSearched: response.documents_searched,
        },
      ])
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'error',
          content: error.message,
          detail: error.code === 'internal_error' ? error.detail : null,
        },
      ])
    } finally {
      setPending(false)
    }
  }

  const toggleDocument = (id) => {
    setSelected((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    )
  }

  const scopeLabel =
    selected.length === 0
      ? `Searching all ${documents.length} paper${documents.length === 1 ? '' : 's'}`
      : `Searching ${selected.length} selected paper${selected.length === 1 ? '' : 's'}`

  return (
    <div className="flex h-screen flex-col">
      <header className="flex flex-wrap items-center gap-3 border-b border-line bg-surface px-6 py-4 md:px-10">
        <div className="mr-auto">
          <h1 className="font-read text-xl tracking-tight">Ask your papers</h1>
          <button
            type="button"
            onClick={() => setShowFilter((open) => !open)}
            className="mt-0.5 text-xs text-muted hover:text-pine-700"
            disabled={documents.length === 0}
          >
            {scopeLabel} · change
          </button>
        </div>

        <ModeToggle mode={mode} onChange={setMode} />

        <button
          type="button"
          className="btn-quiet"
          onClick={() => setMessages([])}
          disabled={messages.length === 0}
        >
          Clear chat
        </button>
      </header>

      {showFilter && documents.length > 0 && (
        <div className="border-b border-line bg-pine-50/50 px-6 py-4 md:px-10">
          <p className="text-xs text-muted">
            Select papers to search. With none selected, every paper is searched.
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {documents.map((doc) => (
              <button
                key={doc.id}
                type="button"
                onClick={() => toggleDocument(doc.id)}
                aria-pressed={selected.includes(doc.id)}
                className={`max-w-xs truncate rounded-full border px-3 py-1 text-xs transition-colors ${
                  selected.includes(doc.id)
                    ? 'border-pine-600 bg-pine-600 text-white'
                    : 'border-line bg-surface text-muted hover:border-pine-500'
                }`}
              >
                {doc.filename}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-6 py-8 md:px-10">
        {documents.length === 0 ? (
          <div className="mx-auto max-w-reading py-16 text-center">
            <p className="font-read text-lg">Nothing to ask about yet</p>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              PaperPilot only answers from papers you have indexed, so add one first.
            </p>
            <Link to="/upload" className="btn-primary mt-5">
              Add papers
            </Link>
          </div>
        ) : messages.length === 0 ? (
          <div className="mx-auto max-w-reading">
            <p className="font-read text-lg">
              Ask anything that the text of your papers can answer.
            </p>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              Answers come only from retrieved passages. If nothing relevant is found, PaperPilot
              says so instead of guessing.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              {starters.map((starter) => (
                <button
                  key={starter}
                  type="button"
                  onClick={() => send(starter)}
                  className="rounded-full border border-line bg-surface px-3.5 py-1.5 text-xs text-muted hover:border-pine-500 hover:text-pine-700"
                >
                  {starter}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-8">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}

            {pending && (
              <p className="font-read text-sm text-muted">
                <span className="mr-2 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-pine-600 align-middle" />
                Searching passages and drafting a grounded answer…
              </p>
            )}

            <div ref={endRef} />
          </div>
        )}
      </div>

      <footer className="border-t border-line bg-surface px-6 py-4 md:px-10">
        <div className="mx-auto flex max-w-3xl items-end gap-3">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                send()
              }
            }}
            rows={1}
            placeholder={
              documents.length === 0 ? 'Add a paper first' : 'Ask about your papers…'
            }
            disabled={documents.length === 0 || pending}
            className="field max-h-40 min-h-[2.75rem] flex-1 resize-y font-read"
          />
          <button
            type="button"
            className="btn-primary"
            onClick={() => send()}
            disabled={!question.trim() || pending || documents.length === 0}
          >
            {pending ? 'Thinking…' : 'Send'}
          </button>
        </div>
        {health && !health.llm_configured && (
          <div className="mx-auto mt-2 flex max-w-3xl items-center justify-between text-xs text-flag">
            <span>No model API key is set, so questions will fail.</span>
            <button
              type="button"
              onClick={openSettings}
              className="underline hover:text-ink"
            >
              Configure API key now
            </button>
          </div>
        )}
      </footer>
    </div>
  )
}
