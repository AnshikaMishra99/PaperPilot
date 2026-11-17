import { useCallback, useEffect, useState } from 'react'
import { Outlet, Route, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar.jsx'
import SettingsModal from './components/SettingsModal.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import { ToastProvider, useToast } from './components/Toast.jsx'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'
import { api } from './api/client.js'
import Dashboard from './pages/Dashboard.jsx'
import UploadPage from './pages/UploadPage.jsx'
import DocumentsPage from './pages/DocumentsPage.jsx'
import ChatPage from './pages/ChatPage.jsx'
import LoginPage from './pages/LoginPage.jsx'

function Shell() {
  const { notify } = useToast()
  const { user, logout } = useAuth()
  const [documents, setDocuments] = useState([])
  const [health, setHealth] = useState(null)
  const [loadingDocuments, setLoadingDocuments] = useState(true)

  // Chat lives here rather than in ChatPage so a conversation survives
  // navigating to the library and back.
  const [messages, setMessages] = useState([])
  const [mode, setMode] = useState('simple')
  const [settingsOpen, setSettingsOpen] = useState(false)

  const refreshDocuments = useCallback(async () => {
    setLoadingDocuments(true)
    try {
      const data = await api.listDocuments()
      setDocuments(data.documents)
      return data.documents
    } catch (error) {
      notify(error.message, 'error')
      return []
    } finally {
      setLoadingDocuments(false)
    }
  }, [notify])

  const refreshHealth = useCallback(async () => {
    try {
      setHealth(await api.health())
    } catch {
      setHealth(null)
    }
  }, [])

  useEffect(() => {
    refreshDocuments()
    refreshHealth()
  }, [refreshDocuments, refreshHealth])

  const context = {
    documents,
    loadingDocuments,
    refreshDocuments,
    health,
    refreshHealth,
    messages,
    setMessages,
    mode,
    setMode,
    notify,
    openSettings: () => setSettingsOpen(true),
  }

  return (
    <div className="flex min-h-screen flex-col md:flex-row bg-paper">
      <Sidebar
        health={health}
        documentCount={documents.length}
        onOpenSettings={() => setSettingsOpen(true)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top Navigation Bar with User Badge & Logout */}
        <header className="flex h-14 items-center justify-between border-b border-line bg-surface/80 px-6 backdrop-blur-xs">
          <div className="flex items-center gap-3">
            <span className="font-read text-sm font-medium text-ink">Research Workspace</span>
            <span className="text-line">•</span>
            <span className="text-xs text-muted">
              {documents.length} paper{documents.length === 1 ? '' : 's'} indexed
            </span>
          </div>

          <div className="flex items-center gap-4">
            {user && (
              <div className="flex items-center gap-2 rounded-full border border-line bg-surface py-1 pl-1.5 pr-3 shadow-2xs">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-pine-100 font-mono text-xs font-semibold text-pine-700">
                  {user.full_name ? user.full_name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}
                </div>
                <span className="max-w-[130px] truncate text-xs font-medium text-ink">
                  {user.full_name || user.email}
                </span>
                <span className="rounded bg-pine-50 px-1.5 py-0.2 font-mono text-[0.65rem] text-pine-700 border border-pine-200">
                  {user.email === 'demo@datapilot.local' ? 'Demo Guest' : 'Account'}
                </span>
              </div>
            )}

            <button
              type="button"
              onClick={logout}
              className="rounded-md border border-line bg-surface px-2.5 py-1 text-xs font-medium text-muted hover:border-flag/30 hover:bg-flag/5 hover:text-flag transition-colors cursor-pointer"
            >
              Sign out
            </button>
          </div>
        </header>

        <main className="min-w-0 flex-1">
          <Outlet context={context} />
        </main>
      </div>

      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        health={health}
        onUpdated={refreshHealth}
        notify={notify}
      />
    </div>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <ProtectedRoute>
                <Shell />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="upload" element={<UploadPage />} />
            <Route path="documents" element={<DocumentsPage />} />
            <Route path="chat" element={<ChatPage />} />
            <Route
              path="*"
              element={
                <div className="p-10">
                  <h1 className="font-read text-2xl">Page not found</h1>
                  <p className="mt-2 text-sm text-muted">Pick a section from the menu.</p>
                </div>
              }
            />
          </Route>
        </Routes>
      </AuthProvider>
    </ToastProvider>
  )
}
