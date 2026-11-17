import { createContext, useContext, useEffect, useState } from 'react'
import { api } from '../api/client.js'

const AuthContext = createContext(null)

const TOKEN_KEY = 'datapilot_token'
const USER_KEY = 'datapilot_user'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem(USER_KEY)
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })
  const [loading, setLoading] = useState(true)

  // Validate stored token on mount
  useEffect(() => {
    async function initAuth() {
      const storedToken = localStorage.getItem(TOKEN_KEY)
      if (storedToken) {
        try {
          const profile = await api.getMe()
          setUser(profile)
          localStorage.setItem(USER_KEY, JSON.stringify(profile))
        } catch (err) {
          // Token is expired or invalid
          setToken(null)
          setUser(null)
          localStorage.removeItem(TOKEN_KEY)
          localStorage.removeItem(USER_KEY)
        }
      }
      setLoading(false)
    }

    initAuth()
  }, [])

  const persistSession = (accessToken, userProfile) => {
    setToken(accessToken)
    setUser(userProfile)
    localStorage.setItem(TOKEN_KEY, accessToken)
    localStorage.setItem(USER_KEY, JSON.stringify(userProfile))
  }

  const login = async (email, password) => {
    const res = await api.login({ email, password })
    persistSession(res.access_token, res.user)
    return res.user
  }

  const register = async (email, password, fullName) => {
    const res = await api.register({ email, password, full_name: fullName })
    persistSession(res.access_token, res.user)
    return res.user
  }

  const demoLogin = async () => {
    const res = await api.demoLogin()
    persistSession(res.access_token, res.user)
    return res.user
  }

  const logout = () => {
    setToken(null)
    setUser(null)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  const value = {
    user,
    token,
    loading,
    isAuthenticated: Boolean(token && user),
    login,
    register,
    demoLogin,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
