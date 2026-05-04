import { useState } from 'react'
import {
  Building2, MapPin, Briefcase, DollarSign,
  ExternalLink, ChevronDown, ChevronUp, Trash2, Star, Send
} from 'lucide-react'
import type { Job, JobStatus } from '../types'
import { ALL_STATUSES, SOURCE_LABELS, STATUS_COLORS, STATUS_DOT } from '../types'

interface Props {
  job: Job
  onStatusChange: (id: number, status: JobStatus) => void
  onNotesChange: (id: number, notes: string) => void
  onDelete: (id: number) => void
}

export default function JobCard({ job, onStatusChange, onNotesChange, onDelete }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [notes, setNotes] = useState(job.notes ?? '')
  const [savingNotes, setSavingNotes] = useState(false)

  const handleNotesSave = async () => {
    setSavingNotes(true)
    await onNotesChange(job.id, notes)
    setSavingNotes(false)
  }

  const score = job.relevance_score
  const scoreColor = score === undefined ? undefined
    : score >= 75 ? '#22c55e'
    : score >= 50 ? '#f59e0b'
    : '#ef4444'

  return (
    <div style={{
      background: '#fff',
      border: '1px solid #e2e8f0',
      borderRadius: '14px',
      overflow: 'hidden',
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
    }}>
      {/* Header */}
      <div style={{ padding: '16px 18px 12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '4px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#0f172a' }}>
                {job.url ? (
                  <a href={job.url} target="_blank" rel="noopener noreferrer"
                    style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                    onMouseEnter={e => (e.currentTarget.style.color = '#6366f1')}
                    onMouseLeave={e => (e.currentTarget.style.color = '#0f172a')}
                  >
                    {job.title}
                    <ExternalLink size={13} style={{ flexShrink: 0, opacity: 0.5 }} />
                  </a>
                ) : job.title}
              </h3>
              {score !== undefined && (
                <span style={{
                  fontSize: '11px', fontWeight: 700, padding: '2px 7px',
                  borderRadius: '10px', border: `1px solid ${scoreColor}`,
                  color: scoreColor, background: `${scoreColor}15`,
                }}>
                  <Star size={9} style={{ display: 'inline', marginRight: 3 }} />
                  {score}% match
                </span>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#475569', fontSize: '13px' }}>
              <Building2 size={13} />
              <span style={{ fontWeight: 500 }}>{job.company}</span>
            </div>
          </div>

          {/* Apply button */}
          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => {
                if (job.status === 'Wishlist') onStatusChange(job.id, 'Applied')
              }}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: '5px',
                padding: '6px 14px', borderRadius: '8px',
                background: '#6366f1', color: '#fff',
                fontSize: '13px', fontWeight: 600, flexShrink: 0,
                textDecoration: 'none', whiteSpace: 'nowrap',
              }}
            >
              <Send size={13} /> Apply
            </a>
          )}

          {/* Status badge + delete */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            <select
              value={job.status}
              onChange={e => onStatusChange(job.id, e.target.value as JobStatus)}
              style={{
                padding: '4px 24px 4px 10px',
                borderRadius: '20px',
                border: `1.5px solid`,
                fontSize: '12px',
                fontWeight: 600,
                appearance: 'none',
                cursor: 'pointer',
                outline: 'none',
                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E")`,
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'right 7px center',
              }}
              className={STATUS_COLORS[job.status]}
            >
              {ALL_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>

            <button
              onClick={() => onDelete(job.id)}
              style={{
                padding: '5px', border: 'none', background: 'transparent',
                color: '#cbd5e1', borderRadius: '6px',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = '#ef4444')}
              onMouseLeave={e => (e.currentTarget.style.color = '#cbd5e1')}
            >
              <Trash2 size={15} />
            </button>
          </div>
        </div>

        {/* Meta row */}
        <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', marginTop: '10px' }}>
          {job.location && <MetaChip icon={<MapPin size={12} />} label={job.location} />}
          {job.experience && <MetaChip icon={<Briefcase size={12} />} label={job.experience} />}
          {job.salary && <MetaChip icon={<DollarSign size={12} />} label={job.salary} />}
          <MetaChip
            label={SOURCE_LABELS[job.source] ?? job.source}
            style={{ background: '#f1f5f9', color: '#64748b' }}
          />
          {job.posted_date && (
            <MetaChip label={job.posted_date} style={{ color: '#94a3b8' }} />
          )}
        </div>
      </div>

      {/* Expand toggle */}
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          width: '100%', padding: '8px 18px',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px',
          border: 'none', borderTop: '1px solid #f1f5f9',
          background: '#fafafa', color: '#94a3b8', fontSize: '12px', cursor: 'pointer',
        }}
      >
        {expanded ? <><ChevronUp size={14} /> Hide details</> : <><ChevronDown size={14} /> Notes & details</>}
      </button>

      {/* Expanded area */}
      {expanded && (
        <div style={{ padding: '14px 18px 16px', borderTop: '1px solid #f1f5f9', background: '#fafafa' }}>
          {job.description && (
            <p style={{ fontSize: '13px', color: '#475569', marginBottom: '12px', lineHeight: 1.6 }}>
              {job.description}
            </p>
          )}
          <label style={{ fontSize: '12px', fontWeight: 600, color: '#64748b', display: 'block', marginBottom: '6px' }}>
            Notes
          </label>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Add notes about this job…"
            rows={3}
            style={{
              width: '100%', padding: '10px 12px',
              border: '1px solid #e2e8f0', borderRadius: '8px',
              fontSize: '13px', resize: 'vertical', background: '#fff',
              outline: 'none', color: '#0f172a',
            }}
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
            <button
              onClick={handleNotesSave}
              disabled={savingNotes}
              style={{
                padding: '7px 18px', background: '#6366f1', color: '#fff',
                border: 'none', borderRadius: '8px', fontSize: '13px',
                fontWeight: 500, opacity: savingNotes ? 0.6 : 1,
              }}
            >
              {savingNotes ? 'Saving…' : 'Save Notes'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function MetaChip({ icon, label, style }: {
  icon?: React.ReactNode
  label: string
  style?: React.CSSProperties
}) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '4px',
      fontSize: '12px', color: '#64748b', ...style,
    }}>
      {icon}{label}
    </span>
  )
}
