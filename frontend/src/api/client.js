import axios from 'axios'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, code = 'unknown_error', detail = null, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.detail = detail
    this.status = status
  }
}

// Axios instance with JWT interceptors
export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: attach Authorization header
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('datapilot_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: redirect to /login on 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('datapilot_token')
      localStorage.removeItem('datapilot_user')
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

function normalizeError(error, defaultMsg = 'Request failed') {
  if (error.response) {
    const data = error.response.data
    return new ApiError(
      data?.detail || data?.message || defaultMsg,
      data?.code || 'http_error',
      data?.detail || null,
      error.response.status
    )
  }
  return new ApiError(
    'Cannot reach the PaperPilot server. Check that the backend is running on ' + BASE_URL + '.',
    'network_error',
    error.message
  )
}

export const api = {
  baseUrl: BASE_URL,
  client: apiClient,

  // --- Auth endpoints ---
  async register({ email, password, full_name }) {
    try {
      const res = await apiClient.post('/auth/register', { email, password, full_name })
      return res.data
    } catch (err) {
      throw normalizeError(err, 'Registration failed')
    }
  },

  async login({ email, password }) {
    try {
      const res = await apiClient.post('/auth/login', { email, password })
      return res.data
    } catch (err) {
      throw normalizeError(err, 'Login failed')
    }
  },

  async demoLogin() {
    try {
      const res = await apiClient.post('/auth/demo')
      return res.data
    } catch (err) {
      throw normalizeError(err, 'Guest login failed')
    }
  },

  async getMe() {
    try {
      const res = await apiClient.get('/auth/me')
      return res.data
    } catch (err) {
      throw normalizeError(err, 'Failed to fetch user profile')
    }
  },

  // --- Core Application endpoints ---
  async health() {
    try {
      const res = await apiClient.get('/api/health')
      return res.data
    } catch (err) {
      throw normalizeError(err, 'Health check failed')
    }
  },

  async listDocuments() {
    try {
      const res = await apiClient.get('/api/documents')
      return res.data
    } catch (err) {
      throw normalizeError(err, 'Failed to load documents')
    }
  },

  async limits() {
    try {
      const res = await apiClient.get('/api/documents/limits')
      return res.data
    } catch (err) {
      throw normalizeError(err, 'Failed to load limits')
    }
  },

  async deleteDocument(id) {
    try {
      const res = await apiClient.delete(`/api/documents/${id}`)
      return res.data
    } catch (err) {
      throw normalizeError(err, 'Failed to delete document')
    }
  },

  async getSettings() {
    try {
      const res = await apiClient.get('/api/settings')
      return res.data
    } catch (err) {
      throw normalizeError(err, 'Failed to load settings')
    }
  },

  async updateSettings(data) {
    try {
      const res = await apiClient.post('/api/settings', data)
      return res.data
    } catch (err) {
      throw normalizeError(err, 'Failed to update settings')
    }
  },

  async ask({ question, mode, documentIds, history }) {
    try {
      const res = await apiClient.post('/api/chat/ask', {
        question,
        mode,
        document_ids: documentIds && documentIds.length ? documentIds : null,
        history: (history || []).map((turn) => ({ role: turn.role, content: turn.content })),
      })
      return res.data
    } catch (err) {
      throw normalizeError(err, 'Question answering failed')
    }
  },

  /**
   * Upload using Axios with progress tracking and Authorization header
   */
  async uploadDocuments(files, onProgress) {
    const form = new FormData()
    files.forEach((file) => form.append('files', file))

    try {
      const res = await apiClient.post('/api/documents/upload', form, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total && onProgress) {
            onProgress(Math.round((progressEvent.loaded / progressEvent.total) * 100))
          }
        },
      })
      return res.data
    } catch (err) {
      throw normalizeError(err, 'Upload failed')
    }
  },
}
