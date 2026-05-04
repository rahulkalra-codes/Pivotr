import type { Filters, Job, JobStatus, ResumeInfo, ScrapeResult, Stats } from './types'

const BASE = '/api'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, options)
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
}
