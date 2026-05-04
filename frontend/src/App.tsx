import { useCallback, useEffect, useRef, useState } from 'react'
import { RefreshCw, Plus, Loader2, Zap, Clock } from 'lucide-react'
import { api } from './api'
import type { Filters, Job, JobStatus, ResumeInfo, Stats } from './types'
import FilterBar from './components/FilterBar'
import JobCard from './components/JobCard'
import StatsBar from './components/StatsBar'
import AddJobModal from './components/AddJobModal'
import ResumeUpload from './components/ResumeUpload'
import LinkedInCookieSettings from './components/LinkedInCookieSettings'

const AUTO_REFRESH_MS = 30 * 60 * 1000 // 30 min

export default function App() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [resume, setResume] = useState<ResumeInfo | null>(null)
  const [filters, setFilters] = useState<Filters>({ status: '', location: '', source: '', search: '' })
  const [loading, setLoading] = useState(true)
  const [scraping, setScraping] = useState(false)
  const [scrapeMsg, setScrapeMsg] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [sortBy, setSortBy] = useState<'date' | 'match'>('date')
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null)
  const [nextRefreshIn, setNextRefreshIn] = useState(AUTO_REFRESH_MS / 1000)

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchAll = useCallback(async () => {
    try {
      const [jobsData, statsData] = await Promise.all([
        api.jobs.list(filters),
        api.stats(),
      ])
      setJobs(jobsData)
      setStats(statsData)
      setLastRefreshed(new Date())
      setNextRefreshIn(AUTO_REFRESH_MS / 1000)
    } catch (err) {
      console.error('Fetch error', err)
    } finally {
      setLoading(false)
    }
  }, [filters])

  // initial load + filter changes
  useEffect(() => {
    setLoading(true)
    fetchAll()
  }, [fetchAll])

  // auto-refresh every 30 min
  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(fetchAll, AUTO_REFRESH_MS)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [fetchAll])

  // countdown ticker
  useEffect(() => {
    if (countdownRef.current) clearInterval(countdownRef.current)
    countdownRef.current = setInterval(() => {
      setNextRefreshIn(n => (n <= 1 ? AUTO_REFRESH_MS / 1000 : n - 1))
    }, 1000)
    return () => { if (countdownRef.current) clearInterval(countdownRef.current) }
  }, [])

  // load resume info on mount
  useEffect(() => {
    api.resume.get().then(setResume).catch(() => {})
  }, [])

  const handleScrape = async () => {
    setScraping(true)
    setScrapeMsg('Scraping in background across all platforms…')
    try {
      await api.scrape()
      // Poll until done
      const poll = setInterval(async () => {
        const { running, last_result } = await api.scrapeStatus()
        if (!running) {
          clearInterval(poll)
          setScraping(false)
          if (last_result) setScrapeMsg(last_result.message)
          fetchAll()
        }
      }, 3000)
    } catch (err) {
      setScrapeMsg(`Error: ${err}`)
      setScraping(false)
    }
  }

  const handleStatusChange = async (id: number, status: JobStatus) => {
    const updated = await api.jobs.updateStatus(id, status)
    setJobs(prev => prev.map(j => j.id === id ? { ...j, ...updated } : j))
    api.stats().then(setStats)
  }

  const handleNotesChange = async (id: number, notes: string) => {
    await api.jobs.update(id, { notes })
    setJobs(prev => prev.map(j => j.id === id ? { ...j, notes } : j))
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this job?')) return
    await api.jobs.delete(id)
    setJobs(prev => prev.filter(j => j.id !== id))
    api.stats().then(setStats)
  }

  const handleAddJob = async (data: Partial<Job>) => {
    const newJob = await api.jobs.create(data)
    setJobs(prev => [newJob, ...prev])
    api.stats().then(setStats)
  }

  const fmtCountdown = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return `${m}:${String(s).padStart(2, '0')}`
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc' }}>
      {/* Header */}
      <header style={{
        background: '#fff', borderBottom: '1px solid #e2e8f0',
        padding: '0 24px', position: 'sticky', top: 0, zIndex: 100,
      }}>
        <div style={{
          maxWidth: 1200, margin: '0 auto',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          height: '60px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: 32, height: 32, background: '#6366f1', borderRadius: '8px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Zap size={18} color="#fff" />
            </div>
            <div>
              <h1 style={{ fontSize: '16px', fontWeight: 700, lineHeight: 1 }}>Pivotr</h1>
              <div style={{ fontSize: '11px', color: '#94a3b8', lineHeight: 1.4 }}>
                <div>Stop juggling tabs. Start landing jobs.</div>
                <div>Hunt smarter, not harder.</div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px', color: '#94a3b8' }}>
              <Clock size={13} />
              <span>Refreshes in {fmtCountdown(nextRefreshIn)}</span>
            </div>

            <button
              onClick={fetchAll}
              style={{
                display: 'flex', alignItems: 'center', gap: '5px',
                padding: '7px 14px', border: '1px solid #e2e8f0',
                borderRadius: '8px', background: '#fff', color: '#475569',
                fontSize: '13px', fontWeight: 500,
              }}
            >
              <RefreshCw size={14} /> Refresh
            </button>

            <button
              onClick={handleScrape}
              disabled={scraping}
              style={{
                display: 'flex', alignItems: 'center', gap: '5px',
                padding: '7px 14px', border: 'none',
                borderRadius: '8px', background: scraping ? '#a5b4fc' : '#6366f1',
                color: '#fff', fontSize: '13px', fontWeight: 600,
              }}
            >
              {scraping ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Zap size={14} />}
              {scraping ? 'Scraping…' : 'Scrape Now'}
            </button>

            <button
              onClick={() => setShowAdd(true)}
              style={{
                display: 'flex', alignItems: 'center', gap: '5px',
                padding: '7px 14px', border: '1px solid #e2e8f0',
                borderRadius: '8px', background: '#fff', color: '#475569',
                fontSize: '13px', fontWeight: 500,
              }}
            >
              <Plus size={14} /> Add Job
            </button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main style={{ maxWidth: 1200, margin: '0 auto', padding: '28px 24px' }}>

        {scrapeMsg && (
          <div style={{
            marginBottom: '16px', padding: '12px 16px',
            background: '#f0fdf4', border: '1px solid #86efac',
            borderRadius: '10px', fontSize: '13px', color: '#166534',
          }}>
            {scrapeMsg}
          </div>
        )}

        <StatsBar stats={stats} />

        <ResumeUpload
          resume={resume}
          onUpdate={r => { setResume(r); fetchAll() }}
        />

        <LinkedInCookieSettings />

        <FilterBar
          filters={filters}
          onChange={partial => setFilters(f => ({ ...f, ...partial }))}
        />

        {lastRefreshed && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <p style={{ fontSize: '12px', color: '#94a3b8', margin: 0 }}>
              Last refreshed: {lastRefreshed.toLocaleTimeString()} · {jobs.length} job{jobs.length !== 1 ? 's' : ''} shown
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '12px', color: '#94a3b8' }}>Sort:</span>
              <button
                onClick={() => setSortBy('date')}
                style={{
                  padding: '4px 10px', borderRadius: '6px', fontSize: '12px', fontWeight: 500,
                  border: `1px solid ${sortBy === 'date' ? '#6366f1' : '#e2e8f0'}`,
                  background: sortBy === 'date' ? '#6366f1' : '#fff',
                  color: sortBy === 'date' ? '#fff' : '#475569', cursor: 'pointer',
                }}
              >Latest</button>
              <button
                onClick={() => setSortBy('match')}
                style={{
                  padding: '4px 10px', borderRadius: '6px', fontSize: '12px', fontWeight: 500,
                  border: `1px solid ${sortBy === 'match' ? '#6366f1' : '#e2e8f0'}`,
                  background: sortBy === 'match' ? '#6366f1' : '#fff',
                  color: sortBy === 'match' ? '#fff' : '#475569', cursor: 'pointer',
                }}
              >% Match</button>
            </div>
          </div>
        )}

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '60px', color: '#94a3b8' }}>
            <Loader2 size={32} style={{ animation: 'spin 1s linear infinite' }} />
          </div>
        ) : jobs.length === 0 ? (
          <div style={{
            textAlign: 'center', padding: '80px 24px',
            background: '#fff', border: '1px solid #e2e8f0', borderRadius: '16px',
          }}>
            <p style={{ fontSize: '16px', fontWeight: 600, color: '#374151', marginBottom: '8px' }}>No jobs found</p>
            <p style={{ fontSize: '14px', color: '#94a3b8' }}>
              Try adjusting filters or click "Scrape Now" to fetch fresh listings.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {[...jobs].sort((a, b) =>
              sortBy === 'match'
                ? (b.relevance_score ?? 0) - (a.relevance_score ?? 0)
                : 0
            ).map(job => (
              <JobCard
                key={job.id}
                job={job}
                onStatusChange={handleStatusChange}
                onNotesChange={handleNotesChange}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </main>

      {showAdd && (
        <AddJobModal
          onSave={handleAddJob}
          onClose={() => setShowAdd(false)}
        />
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes tagline1 { 0%,40% { opacity:1 } 50%,90% { opacity:0 } 100% { opacity:1 } }
        @keyframes tagline2 { 0%,40% { opacity:0 } 50%,90% { opacity:1 } 100% { opacity:0 } }
        .bg-slate-100 { background: #f1f5f9; }
        .text-slate-700 { color: #334155; }
        .border-slate-200 { border-color: #e2e8f0; }
        .bg-slate-400 { background: #94a3b8; }
        .bg-blue-100 { background: #dbeafe; }
        .text-blue-700 { color: #1d4ed8; }
        .border-blue-200 { border-color: #bfdbfe; }
        .bg-blue-500 { background: #3b82f6; }
        .bg-amber-100 { background: #fef3c7; }
        .text-amber-700 { color: #b45309; }
        .border-amber-200 { border-color: #fde68a; }
        .bg-amber-500 { background: #f59e0b; }
        .bg-green-100 { background: #dcfce7; }
        .text-green-700 { color: #15803d; }
        .border-green-200 { border-color: #bbf7d0; }
        .bg-green-500 { background: #22c55e; }
        .bg-red-100 { background: #fee2e2; }
        .text-red-600 { color: #dc2626; }
        .border-red-200 { border-color: #fecaca; }
        .bg-red-500 { background: #ef4444; }
      `}</style>
    </div>
  )
}
