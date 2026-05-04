import type { Filters, Job, JobStatus, ResumeInfo, ScrapeResult, Stats } from './types'

const BASE = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api'

const TOKEN_KEY = 'pivotr_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(t: string): void {
  localStorage.setItem(TOKEN_KEY, t)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken()
  const authHeaders: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {}

  // Merge caller headers with auth headers (caller headers take precedence for everything except Authorization)
  const mergedHeaders: Record<string, string> = {
    ...authHeaders,
    ...(options?.headers as Record<string, string> | undefined),
  }

  const res = await fetch(BASE + path, { ...options, headers: mergedHeaders })

  if (res.status === 401) {
    clearToken()
    window.dispatchEvent(new Event('auth:logout'))
    throw new Error('401: Unauthorized')
  }

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  jobs: {
    list: (filters: Partial<Filters> = {}): Promise<Job[]> => {
      const params = new URLSearchParams()
      if (filters.status)   params.set('status', filters.status)
      if (filters.location) params.set('location', filters.location)
      if (filters.source)   params.set('source', filters.source)
      if (filters.search)   params.set('search', filters.search)
      const qs = params.toString()
      return req(`/jobs${qs ? `?${qs}` : ''}`)
    },

    create: (data: Partial<Job>): Promise<Job> =>
      req('/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),

    update: (id: number, data: Partial<Job>): Promise<Job> =>
      req(`/jobs/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),

    updateStatus: (id: number, status: JobStatus): Promise<Job> =>
      req(`/jobs/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      }),

    delete: (id: number): Promise<void> =>
      req(`/jobs/${id}`, { method: 'DELETE' }),
  },

  stats: (): Promise<Stats> => req('/stats'),

  scrape: (): Promise<{ status: string; message: string }> => req('/scrape', { method: 'POST' }),
  scrapeStatus: (): Promise<{ running: boolean; last_result: ScrapeResult | null }> => req('/scrape/status'),

  resume: {
    get: (): Promise<ResumeInfo> => req('/resume'),
    upload: (file: File): Promise<ResumeInfo & { message: string; skills_found: number }> => {
      const form = new FormData()
      form.append('file', file)
      return req('/resume', { method: 'POST', body: form })
    },
    delete: (): Promise<void> => req('/resume', { method: 'DELETE' }),
  },

  linkedin: {
    getCookie: (): Promise<{ set: boolean; preview: string }> =>
      req('/settings/linkedin-cookie'),
    setCookie: (cookie: string): Promise<{ status: string; set: boolean }> =>
      req('/settings/linkedin-cookie', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cookie }),
      }),
    deleteCookie: (): Promise<void> =>
      req('/settings/linkedin-cookie', { method: 'DELETE' }),
  },

  auth: {
    register: (email: string, password: string) =>
      req('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      }),
    login: (email: string, password: string) =>
      req('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      }),
    me: () => req('/auth/me'),
    logout: () => { clearToken() },
  },
}
