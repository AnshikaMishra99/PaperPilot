import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [demoLoading, setDemoLoading] = useState(false)
  const [error, setError] = useState(null)

  const { login, register, demoLogin } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const destination = location.state?.from?.pathname || '/'

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      if (isRegister) {
        await register(email, password, fullName)
      } else {
        await login(email, password)
      }
      navigate(destination, { replace: true })
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify your credentials.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDemoLogin = async () => {
    setError(null)
    setDemoLoading(true)
    try {
      await demoLogin()
      navigate(destination, { replace: true })
    } catch (err) {
      setError(err.message || 'Could not initiate demo session.')
    } finally {
      setDemoLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-4 py-12">
      <div className="w-full max-w-md rounded-2xl border border-line bg-surface p-8 shadow-sm">
        {/* Brand Header */}
        <div className="text-center">
          <h1 className="font-read text-3xl font-semibold tracking-tight text-pine-700">Data Pilot</h1>
          <p className="mt-1.5 font-read text-sm text-muted">
            Intelligent RAG assistant for academic & scientific research
          </p>
        </div>

        {/* Tab Toggle */}
        <div className="mt-7 flex rounded-lg bg-pine-50/60 p-1 border border-line/60">
          <button
            type="button"
            onClick={() => {
              setIsRegister(false)
              setError(null)
            }}
            className={`flex-1 rounded-md py-1.5 text-xs font-medium transition-all ${
              !isRegister
                ? 'bg-surface font-semibold text-pine-700 shadow-2xs'
                : 'text-muted hover:text-ink'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setIsRegister(true)
              setError(null)
            }}
            className={`flex-1 rounded-md py-1.5 text-xs font-medium transition-all ${
              isRegister
                ? 'bg-surface font-semibold text-pine-700 shadow-2xs'
                : 'text-muted hover:text-ink'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mt-4 rounded-lg border border-flag/30 bg-flag/5 px-3.5 py-2.5 text-xs text-flag leading-relaxed">
            {error}
          </div>
        )}

        {/* Auth Form */}
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          {isRegister && (
            <div>
              <label className="block text-xs font-medium text-ink">Full Name</label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Dr. Eleanor Vance"
                className="field mt-1 text-sm"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-ink">Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="researcher@university.edu"
              className="field mt-1 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-ink">Password</label>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="field mt-1 text-sm"
            />
            {isRegister && (
              <p className="mt-1 text-[0.7rem] text-muted">Minimum 6 characters</p>
            )}
          </div>

          <button
            type="submit"
            disabled={submitting || demoLoading}
            className="w-full rounded-lg bg-pine-600 py-2.5 text-sm font-medium text-white transition-colors hover:bg-pine-500 disabled:opacity-50 cursor-pointer shadow-xs"
          >
            {submitting
              ? isRegister
                ? 'Creating account...'
                : 'Signing in...'
              : isRegister
              ? 'Create Research Account'
              : 'Sign In to Workspace'}
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-5">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-line" />
          </div>
          <div className="relative flex justify-center text-xs">
            <span className="bg-surface px-2 text-muted">or evaluate instantly</span>
          </div>
        </div>

        {/* Prominent Demo Guest Button */}
        <button
          type="button"
          onClick={handleDemoLogin}
          disabled={submitting || demoLoading}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-ochre/40 bg-ochre/5 py-2.5 text-sm font-medium text-ochre transition-all hover:bg-ochre hover:text-white disabled:opacity-50 cursor-pointer shadow-2xs"
        >
          {demoLoading ? (
            'Preparing guest session...'
          ) : (
            <>
              <span className="inline-block h-2 w-2 rounded-full bg-ochre animate-pulse" />
              Continue as Demo Guest
            </>
          )}
        </button>

        <p className="mt-5 text-center text-xs text-muted">
          Your uploaded papers and queries are isolated to your private account.
        </p>
      </div>
    </div>
  )
}
