export interface User {
  id: number
  email: string
}

export type JobStatus = 'Wishlist' | 'Applied' | 'Interviewing' | 'Offer' | 'Rejected'

export interface Job {
  id: number
  title: string
  company: string
  location: string
  source: string
  url?: string
  description?: string
  salary?: string
  experience?: string
  status: JobStatus
  notes?: string
  posted_date?: string
  scraped_at?: string
  updated_at?: string
  external_id?: string
  relevance_score?: number
}

export interface Stats {
  total: number
  by_status: Record<JobStatus, number>
  sources: Record<string, number>
}

export interface ResumeInfo {
  uploaded: boolean
  years_experience?: number | null
  skills?: string[]
  current_title?: string
}

export interface ScrapeResult {
  added: number
  skipped: number
  errors: number
  message: string
}

export interface Filters {
  status: string
  location: string
  source: string
  search: string
}

export const STATUS_COLORS: Record<JobStatus, string> = {
  Wishlist:     'bg-slate-100 text-slate-700 border-slate-200',
  Applied:      'bg-blue-100 text-blue-700 border-blue-200',
  Interviewing: 'bg-amber-100 text-amber-700 border-amber-200',
  Offer:        'bg-green-100 text-green-700 border-green-200',
  Rejected:     'bg-red-100 text-red-600 border-red-200',
}

export const STATUS_DOT: Record<JobStatus, string> = {
  Wishlist:     'bg-slate-400',
  Applied:      'bg-blue-500',
  Interviewing: 'bg-amber-500',
  Offer:        'bg-green-500',
  Rejected:     'bg-red-500',
}

export const ALL_STATUSES: JobStatus[] = ['Wishlist', 'Applied', 'Interviewing', 'Offer', 'Rejected']

export const SOURCE_LABELS: Record<string, string> = {
  linkedin:        'LinkedIn',
  indeed:          'Indeed',
  google_careers:  'Google Careers',
  manual:          'Manual',
}

export const QUICK_LOCATIONS = [
  { label: 'All', value: '' },
  { label: 'Bangalore', value: 'Bangalore' },
  { label: 'Remote', value: 'Remote' },
]

export const ALL_CITIES = [
  '', 'Bangalore', 'Mumbai', 'Delhi', 'Hyderabad', 'Pune', 'Remote', 'Rest of India',
]
