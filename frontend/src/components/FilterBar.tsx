import { Search, X } from 'lucide-react'
import type { Filters } from '../types'
import { ALL_STATUSES, ALL_CITIES, QUICK_LOCATIONS, SOURCE_LABELS } from '../types'

interface Props {
  filters: Filters
  onChange: (f: Partial<Filters>) => void
}

const ALL_SOURCES = Object.keys(SOURCE_LABELS)

export default function FilterBar({ filters, onChange }: Props) {
  const hasFilters = filters.status || filters.location || filters.source || filters.search

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>

      {/* Row 1: Search */}
      <div style={{ position: 'relative' }}>
        <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
        <input
          type="text"
          placeholder="Search jobs or companies…"
          value={filters.search}
          onChange={e => onChange({ search: e.target.value })}
          style={{
            width: '100%', padding: '9px 12px 9px 36px',
            border: '1px solid #e2e8f0', borderRadius: '10px',
            background: '#fff', fontSize: '14px', outline: 'none',
            boxSizing: 'border-box',
          }}
        />
      </div>

      {/* Row 2: Dropdowns */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
        <select value={filters.status} onChange={e => onChange({ status: e.target.value })} style={selectStyle}>
          <option value="">All Statuses</option>
          {ALL_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <select value={filters.source} onChange={e => onChange({ source: e.target.value })} style={selectStyle}>
          <option value="">All Sources</option>
          {ALL_SOURCES.map(s => <option key={s} value={s}>{SOURCE_LABELS[s]}</option>)}
        </select>

        <select
          value={ALL_CITIES.includes(filters.location) && !['Bangalore','Remote',''].includes(filters.location) ? filters.location : ''}
          onChange={e => onChange({ location: e.target.value })}
          style={selectStyle}
        >
          <option value="">All Cities</option>
          {ALL_CITIES.filter(c => c && c !== 'Bangalore' && c !== 'Remote').map(c => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>

        {hasFilters && (
          <button
            onClick={() => onChange({ status: '', location: '', source: '', search: '' })}
            style={{
              display: 'flex', alignItems: 'center', gap: '4px',
              padding: '7px 12px', border: '1px solid #fca5a5',
              borderRadius: '10px', background: '#fff5f5',
              color: '#ef4444', fontSize: '13px', fontWeight: 500,
            }}
          >
            <X size={13} /> Clear
          </button>
        )}
      </div>

      {/* Row 3: Quick location chips — Bangalore + Remote only */}
      <div style={{ display: 'flex', gap: '8px' }}>
        {QUICK_LOCATIONS.map(loc => {
          const active = filters.location === loc.value
          return (
            <button
              key={loc.value}
              onClick={() => onChange({ location: active ? '' : loc.value })}
              style={{
                padding: '5px 16px', borderRadius: '20px',
                border: `1.5px solid ${active ? '#6366f1' : '#e2e8f0'}`,
                background: active ? '#6366f1' : '#fff',
                color: active ? '#fff' : '#475569',
                fontSize: '13px', fontWeight: active ? 600 : 400,
                cursor: 'pointer', whiteSpace: 'nowrap',
              }}
            >
              {loc.label}
            </button>
          )
        })}
      </div>

    </div>
  )
}

const selectStyle: React.CSSProperties = {
  padding: '8px 28px 8px 12px',
  border: '1px solid #e2e8f0', borderRadius: '10px',
  background: '#fff', fontSize: '13px', color: '#0f172a',
  appearance: 'none',
  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E")`,
  backgroundRepeat: 'no-repeat', backgroundPosition: 'right 9px center',
  cursor: 'pointer', outline: 'none',
}
