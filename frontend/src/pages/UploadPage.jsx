import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import DropZone from '../components/DropZone.jsx'
import { api } from '../api/client.js'
import { useApp } from '../useApp.js'

export default function UploadPage() {
  const { refreshDocuments, refreshHealth, notify } = useApp()
  const navigate = useNavigate()

  const [limits, setLimits] = useState({ max_upload_mb: 25, max_files_per_request: 10 })
  const [queue, setQueue] = useState([])
  const [progress, setProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [results, setResults] = useState([])

  useEffect(() => {
    api
      .limits()
      .then(setLimits)
      .catch(() => {})
  }, [])

  const addFiles = (files) => {
    const accepted = []
    files.forEach((file) => {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        notify(`${file.name} is not a PDF, so it was skipped.`, 'error')
        return
      }
      if (file.size > limits.max_upload_mb * 1024 * 1024) {
        notify(`${file.name} is over the ${limits.max_upload_mb} MB limit.`, 'error')
        return
      }
      if (file.size === 0) {
        notify(`${file.name} is empty.`, 'error')
        return
      }
      accepted.push(file)
    })

    setQueue((current) => {
      const names = new Set(current.map((file) => file.name + file.size))
      const merged = [...current]
      accepted.forEach((file) => {
        if (!names.has(file.name + file.size)) merged.push(file)
      })
      return merged.slice(0, limits.max_files_per_request)
    })
  }

  const upload = async () => {
    if (!queue.length) return
    setUploading(true)
    setProgress(0)
    setResults([])

    try {
      const response = await api.uploadDocuments(queue, setProgress)
      setResults(response.uploaded)
      setQueue([])
      await refreshDocuments()
      await refreshHealth()

      if (response.succeeded) {
        notify(
          `Indexed ${response.succeeded} paper${response.succeeded > 1 ? 's' : ''}.`,
          'success',
        )
      }
      if (response.failed) {
        notify(`${response.failed} file(s) could not be indexed. See the details below.`, 'error')
      }
    } catch (error) {
      notify(error.message, 'error')
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }

  return (
    <div className="px-6 py-10 md:px-12 md:py-14">
      <header className="max-w-reading">
        <h1 className="font-read text-3xl tracking-tight">Add papers</h1>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          Indexing happens once per paper: text is extracted page by page, split into passages, and
          stored as vectors. A long paper takes a few seconds.
        </p>
      </header>

      <div className="mt-8 max-w-3xl">
        <DropZone
          onFiles={addFiles}
          disabled={uploading}
          maxMb={limits.max_upload_mb}
          maxFiles={limits.max_files_per_request}
        />

        {queue.length > 0 && (
          <div className="mt-6 rounded-lg border border-line bg-surface p-5">
            <p className="text-sm font-medium">Ready to index</p>
            <ul className="mt-3 divide-y divide-line">
              {queue.map((file) => (
                <li key={file.name + file.size} className="flex items-center gap-4 py-2.5 text-sm">
                  <span className="min-w-0 flex-1 truncate font-read">{file.name}</span>
                  <span className="shrink-0 text-xs text-muted">
                    {(file.size / (1024 * 1024)).toFixed(1)} MB
                  </span>
                  <button
                    type="button"
                    className="shrink-0 text-xs text-muted hover:text-flag"
                    disabled={uploading}
                    onClick={() => setQueue((current) => current.filter((item) => item !== file))}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>

            {uploading && (
              <div className="mt-4">
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-line">
                  <div
                    className="h-full bg-pine-600 transition-[width] duration-200"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="mt-2 text-xs text-muted">
                  {progress < 100
                    ? `Uploading ${progress}%`
                    : 'Extracting text, splitting and embedding…'}
                </p>
              </div>
            )}

            <div className="mt-5 flex gap-3">
              <button type="button" className="btn-primary" onClick={upload} disabled={uploading}>
                {uploading ? 'Indexing…' : `Index ${queue.length} paper(s)`}
              </button>
              <button
                type="button"
                className="btn-quiet"
                disabled={uploading}
                onClick={() => setQueue([])}
              >
                Clear list
              </button>
            </div>
          </div>
        )}

        {results.length > 0 && (
          <div className="mt-6 rounded-lg border border-line bg-surface p-5">
            <p className="text-sm font-medium">Results</p>
            <ul className="mt-3 divide-y divide-line">
              {results.map((result) => (
                <li key={result.filename} className="py-3 text-sm">
                  <div className="flex items-baseline gap-3">
                    <span
                      className={`shrink-0 text-xs ${result.success ? 'text-pine-700' : 'text-flag'}`}
                    >
                      {result.success ? 'Indexed' : 'Failed'}
                    </span>
                    <span className="min-w-0 flex-1 truncate font-read">{result.filename}</span>
                  </div>
                  <p className="mt-1 text-xs text-muted">
                    {result.success
                      ? `${result.document.pages} pages · ${result.document.chunks} passages`
                      : result.error}
                  </p>
                </li>
              ))}
            </ul>

            {results.some((result) => result.success) && (
              <button type="button" className="btn-primary mt-4" onClick={() => navigate('/chat')}>
                Ask a question
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
