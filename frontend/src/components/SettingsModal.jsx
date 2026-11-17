import { useState } from 'react'
import { api } from '../api/client.js'

export default function SettingsModal({ isOpen, onClose, health, onUpdated, notify }) {
  const [apiKey, setApiKey] = useState('')
  const [provider, setProvider] = useState(health?.embedding_provider || 'google')
  const [saving, setSaving] = useState(false)
  const [showKey, setShowKey] = useState(false)

  if (!isOpen) return null

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = { embedding_provider: provider }
      if (apiKey.trim()) {
        payload.google_api_key = apiKey.trim()
      }
      await api.updateSettings(payload)
      notify('Settings saved successfully!', 'success')
      setApiKey('')
      await onUpdated?.()
      onClose()
    } catch (err) {
      notify(err.message || 'Failed to update settings', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-xl border border-line bg-surface p-6 shadow-xl">
        <div className="flex items-start justify-between border-b border-line pb-4">
          <div>
            <h2 className="font-read text-2xl font-medium text-ink">API Key & Settings</h2>
            <p className="mt-1 text-xs text-muted">
              Configure your Gemini model credentials and embedding provider.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-lg text-muted hover:text-ink"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSave} className="mt-5 space-y-5">
          <div>
            <label className="block text-xs font-medium text-ink">
              Google AI Studio API Key (Gemini)
            </label>
            <p className="mt-0.5 text-xs text-muted">
              Required for answering questions and for Google embeddings.{' '}
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noreferrer"
                className="text-pine-700 underline hover:text-pine-500"
              >
                Get a free key here ↗
              </a>
            </p>
            <div className="relative mt-2">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={health?.llm_configured ? '•••••••••••••••• (API key is set)' : 'AIzaSy...'}
                className="field pr-16"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded px-2 py-1 text-xs text-muted hover:text-ink"
              >
                {showKey ? 'Hide' : 'Show'}
              </button>
            </div>
            {health?.llm_configured && (
              <p className="mt-1.5 flex items-center gap-1.5 text-xs text-pine-700">
                <span className="inline-block h-2 w-2 rounded-full bg-pine-500" />
                API key is currently active. Enter a new key above only if you want to replace it.
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-ink">Embedding Provider</label>
            <p className="mt-0.5 text-xs text-muted">
              Choose how document text passages are converted into searchable vectors.
            </p>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <label
                className={`cursor-pointer rounded-lg border p-3.5 text-left transition-colors ${
                  provider === 'google'
                    ? 'border-pine-600 bg-pine-50/50'
                    : 'border-line bg-surface hover:border-pine-500/50'
                }`}
              >
                <div className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="provider"
                    value="google"
                    checked={provider === 'google'}
                    onChange={() => setProvider('google')}
                    className="accent-pine-600"
                  />
                  <span className="text-sm font-medium text-ink">Google API</span>
                </div>
                <p className="mt-1 text-xs text-muted">
                  gemini-embedding-001. Asymmetric retrieval, high quality, requires API key.
                </p>
              </label>

              <label
                className={`cursor-pointer rounded-lg border p-3.5 text-left transition-colors ${
                  provider === 'local'
                    ? 'border-pine-600 bg-pine-50/50'
                    : 'border-line bg-surface hover:border-pine-500/50'
                }`}
              >
                <div className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="provider"
                    value="local"
                    checked={provider === 'local'}
                    onChange={() => setProvider('local')}
                    className="accent-pine-600"
                  />
                  <span className="text-sm font-medium text-ink">Local (ONNX)</span>
                </div>
                <p className="mt-1 text-xs text-muted">
                  all-MiniLM-L6-v2. Runs locally on your device, works completely offline.
                </p>
              </label>
            </div>
          </div>

          <div className="flex justify-end gap-3 border-t border-line pt-4">
            <button type="button" onClick={onClose} className="btn-quiet" disabled={saving}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
