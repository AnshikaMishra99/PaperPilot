import { Link } from 'react-router-dom'
import DocumentCard from '../components/DocumentCard.jsx'
import { api } from '../api/client.js'
import { useApp } from '../useApp.js'

export default function DocumentsPage() {
  const { documents, loadingDocuments, refreshDocuments, refreshHealth, notify } = useApp()

  const handleDelete = async (document) => {
    try {
      await api.deleteDocument(document.id)
      notify(`Removed ${document.filename}.`, 'success')
      await refreshDocuments()
      await refreshHealth()
    } catch (error) {
      notify(error.message, 'error')
    }
  }

  return (
    <div className="px-6 py-10 md:px-12 md:py-14">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-reading">
          <h1 className="font-read text-3xl tracking-tight">Library</h1>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Removing a paper deletes its passages from the search index straight away, so later
            answers can no longer draw on it.
          </p>
        </div>
        <Link to="/upload" className="btn-quiet">
          Add papers
        </Link>
      </header>

      <div className="mt-8 max-w-3xl rounded-lg border border-line bg-surface px-5">
        {loadingDocuments ? (
          <p className="py-10 text-center text-sm text-muted">Loading your library…</p>
        ) : documents.length === 0 ? (
          <div className="py-12 text-center">
            <p className="font-read text-lg">Your library is empty</p>
            <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-muted">
              Add a research PDF and it will be indexed into searchable passages.
            </p>
            <Link to="/upload" className="btn-primary mt-5">
              Add your first paper
            </Link>
          </div>
        ) : (
          <ul>
            {documents.map((document) => (
              <DocumentCard key={document.id} document={document} onDelete={handleDelete} />
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
