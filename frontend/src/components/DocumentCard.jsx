import { useState } from 'react'

function formatSize(bytes) {
  if (!bytes) return '—'
  const mb = bytes / (1024 * 1024)
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`
}

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export default function DocumentCard({ document, onDelete }) {
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)

  return (
    <li className="flex items-start gap-4 border-b border-line py-4 last:border-b-0">

      <div className="min-w-0 flex-1">
        <p className="truncate font-read text-base text-ink" title={document.filename}>
          {document.filename}
        </p>
        <p className="mt-1 text-xs text-muted">
          {document.pages} pages · {document.chunks} passages indexed · {formatSize(document.size_bytes)} ·
          added {formatDate(document.uploaded_at)}
        </p>
      </div>

      <div className="flex items-center gap-3">
        <span className="rounded-full bg-pine-50 px-2.5 py-1 text-xs text-pine-700">
          {document.status === 'ready' ? 'Indexed' : 'Failed'}
        </span>

        {confirming ? (
          <span className="flex items-center gap-2 text-xs">
            <button
              type="button"
              disabled={busy}
              className="font-medium text-flag hover:underline"
              onClick={async () => {
                setBusy(true)
                try {
                  await onDelete(document)
                } finally {
                  setBusy(false)
                  setConfirming(false)
                }
              }}
            >
              {busy ? 'Deleting…' : 'Delete'}
            </button>
            <button
              type="button"
              className="text-muted hover:text-ink"
              onClick={() => setConfirming(false)}
            >
              Keep
            </button>
          </span>
        ) : (
          <button
            type="button"
            className="text-xs text-muted hover:text-flag"
            onClick={() => setConfirming(true)}
          >
            Remove
          </button>
        )}
      </div>
    </li>
  )
}
