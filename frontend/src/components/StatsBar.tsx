import type { Stats } from '../types'
import { ALL_STATUSES, STATUS_DOT } from '../types'

interface Props {
  stats: Stats | null
}

export default function StatsBar({ stats }: Props) {
  if (!stats) return null

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
      gap: '12px',
      marginBottom: '24px',
    }}>
      <StatCard label="Total Jobs" value={stats.total} color="#6366f1" />
      {ALL_STATUSES.map(s => (
        <StatCard
          key={s}
          label={s}
          value={stats.by_status[s] ?? 0}
          dot={STATUS_DOT[s]}
        />
      ))}
    </div>
  )
}

function StatCard({ label, value, color, dot }: {
  label: string
  value: number
  color?: string
  dot?: string
}) {
  return (
    <div style={{
      background: '#fff',
      border: '1px solid #e2e8f0',
      borderRadius: '12px',
      padding: '16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '4px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        {dot && (
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: dot.replace('bg-', '').replace('-', ' '),
            // use inline color via className mapping
            display: 'inline-block',
          }} className={dot} />
        )}
        <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 500 }}>{label}</span>
      </div>
      <span style={{ fontSize: '28px', fontWeight: 700, color: color ?? '#0f172a' }}>
        {value}
      </span>
    </div>
  )
}
