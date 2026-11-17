import { Link } from 'react-router-dom'
import { useApp } from '../useApp.js'

const pipeline = [
  ['Read', 'Text and page numbers are pulled out of each PDF.'],
  ['Split', 'Each page becomes overlapping passages of about 1,000 characters.'],
  ['Embed', 'Every passage becomes a vector that captures its meaning.'],
  ['Search', 'Your question becomes a vector too, and the closest passages win.'],
  ['Answer', 'Only those passages go to the model, with the page they came from.'],
]

export default function Dashboard() {
  const { documents, health, openSettings } = useApp()
  const recent = documents.slice(0, 4)
  const chunks = documents.reduce((total, doc) => total + doc.chunks, 0)
  const pages = documents.reduce((total, doc) => total + doc.pages, 0)

  return (
    <div className="px-6 py-10 md:px-12 md:py-14">
      <header className="max-w-reading">
        <h1 className="font-read text-4xl leading-tight tracking-tight text-ink">
          Read less of the paper, find more of the answer.
        </h1>
        <p className="mt-4 text-[0.95rem] leading-relaxed text-muted">
          Upload research PDFs and ask them questions in plain English. PaperPilot searches the
          passages it indexed, answers from those passages only, and shows you the file and page
          behind every claim so you can check it yourself.
        </p>
      </header>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link to="/upload" className="btn-primary">
          Add papers
        </Link>
        <Link to="/chat" className="btn-quiet">
          Ask a question
        </Link>
      </div>

      <section className="mt-12 grid gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-3">
        {[
          ['Papers indexed', documents.length],
          ['Pages read', pages],
          ['Searchable passages', chunks],
        ].map(([label, value]) => (
          <div key={label} className="bg-surface px-5 py-6">
            <p className="font-read text-3xl text-pine-700">{value}</p>
            <p className="mt-1 text-sm text-muted">{label}</p>
          </div>
        ))}
      </section>

      {!health?.llm_configured && (
        <div className="mt-6 flex max-w-reading flex-wrap items-center justify-between gap-4 rounded-md border border-flag/30 bg-flag/5 px-4 py-3 text-sm text-flag">
          <span>
            No Gemini API key is configured, so questions cannot be answered yet.
          </span>
          <button
            type="button"
            onClick={openSettings}
            className="rounded bg-flag/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-flag hover:bg-flag/20"
          >
            Configure API Key
          </button>
        </div>
      )}

      <section className="mt-12 grid gap-10 lg:grid-cols-2">
        <div>
          <h2 className="font-read text-xl text-ink">Recently added</h2>
          {recent.length === 0 ? (
            <p className="mt-3 max-w-reading text-sm leading-relaxed text-muted">
              Nothing indexed yet. Add a PDF and it will appear here with its page and passage
              counts.
            </p>
          ) : (
            <ul className="mt-3 divide-y divide-line border-y border-line">
              {recent.map((doc) => (
                <li key={doc.id} className="flex items-baseline justify-between gap-4 py-3">
                  <span className="min-w-0 truncate font-read text-[0.95rem]">{doc.filename}</span>
                  <span className="shrink-0 text-xs text-muted">
                    {doc.pages} pages · {doc.chunks} passages
                  </span>
                </li>
              ))}
            </ul>
          )}
          {documents.length > recent.length && (
            <Link to="/documents" className="mt-3 inline-block text-sm text-pine-700 hover:underline">
              See all {documents.length} papers
            </Link>
          )}
        </div>

        <div>
          <h2 className="font-read text-xl text-ink">What happens to a paper</h2>
          <ol className="mt-3 space-y-3 border-l border-line pl-5">
            {pipeline.map(([step, description], index) => (
              <li key={step} className="relative">
                <span className="absolute -left-[1.55rem] top-1 font-read text-xs text-ochre">
                  {index + 1}
                </span>
                <p className="text-sm font-medium text-ink">{step}</p>
                <p className="text-sm leading-relaxed text-muted">{description}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>
    </div>
  )
}
