import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

const links = [
  { to: '/', label: 'Overview', end: true },
  { to: '/upload', label: 'Add papers' },
  { to: '/documents', label: 'Library' },
  { to: '/chat', label: 'Ask' },
]

export default function Sidebar({ health, documentCount, onOpenSettings }) {
  const { user, logout } = useAuth()

  return (
    <aside className="flex shrink-0 flex-col gap-6 border-b border-line bg-surface px-6 py-6 md:h-screen md:w-64 md:border-b-0 md:border-r">
      <div>
        <p className="font-read text-xl font-semibold tracking-tight text-pine-700">Data Pilot</p>
        <p className="mt-1 text-xs leading-relaxed text-muted">
          Ask questions, get answers with the page they came from.
        </p>
      </div>

      <nav className="flex flex-wrap gap-1 md:flex-col">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) =>
              `rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? 'bg-pine-50 font-medium text-pine-700'
                  : 'text-muted hover:bg-pine-50/60 hover:text-ink'
              }`
            }
          >
            {link.label}
            {link.to === '/documents' && documentCount > 0 && (
              <span className="ml-2 text-xs text-muted">{documentCount}</span>
            )}
          </NavLink>
        ))}
        <button
          type="button"
          onClick={onOpenSettings}
          className="rounded-md px-3 py-2 text-left text-sm text-muted hover:bg-pine-50/60 hover:text-ink md:hidden"
        >
          ⚙ Settings
        </button>
      </nav>

      {/* User Card & Logout */}
      {user && (
        <div className="mt-auto border-t border-line pt-3.5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-pine-100 font-mono text-xs font-semibold text-pine-700 border border-pine-200">
              {user.full_name ? user.full_name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-ink">{user.full_name || 'Researcher'}</p>
              <p className="truncate text-[0.68rem] text-muted">{user.email}</p>
            </div>
            <button
              type="button"
              onClick={logout}
              title="Logout"
              className="rounded px-2 py-1 text-xs text-muted hover:bg-flag/10 hover:text-flag transition-colors cursor-pointer"
            >
              Sign out
            </button>
          </div>
        </div>
      )}

      <div className="space-y-3 border-t border-line pt-3 text-xs text-muted">
        {health ? (
          <>
            <p>
              Indexed: {health.documents} papers, {health.chunks} passages
            </p>
            <p>Embeddings: {health.embedding_provider}</p>
            <p className={health.llm_configured ? '' : 'text-flag'}>
              {health.llm_configured
                ? `Answering with ${health.llm_model}`
                : 'No API key set — answering is disabled'}
            </p>
          </>
        ) : (
          <p className="text-flag">Server unreachable</p>
        )}
        <button
          type="button"
          onClick={onOpenSettings}
          className="w-full rounded border border-line bg-surface px-2.5 py-1.5 text-xs font-medium text-ink transition-colors hover:border-pine-500 hover:text-pine-700"
        >
          ⚙ API Key & Settings
        </button>
      </div>
    </aside>
  )
}
