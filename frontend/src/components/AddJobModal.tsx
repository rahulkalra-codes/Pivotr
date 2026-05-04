import { useState } from 'react'
import { X } from 'lucide-react'
import type { Job } from '../types'
import { ALL_STATUSES } from '../types'

interface Props {
  onSave: (job: Partial<Job>) => Promise<void>
  onClose: () => void
}

const FIELD_LABELS: { key: keyof Partial<Job>; label: string; required?: boolean; type?: string }[] = [
  { key: 'title',    label: 'Job Title',  required: true },
  { key: 'company',  label: 'Company',    required: true },
  { key: 'location', label: 'Location' },
  { key: 'url',      label: 'Job URL',    type: 'url' },
  { key: 'salary',   label: 'Salary / CTC' },
  { key: 'experience', label: 'Experience required' },
  { key: 'posted_date', label: 'Posted date' },
]

export default function AddJobModal({ onSave, onClose }: Props) {
  const [form, setForm] = useState<Partial<Job>>({ status: 'Wishlist', location: 'Bangalore', source: 'manual' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const set = (key: keyof Job, val: string) => setForm(f => ({ ...f, [key]: val }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.title || !form.company) { setError('Title and Company are required.'); return }
    setSaving(true)
    setError('')
    try {
      await onSave(form)
      onClose()
    } catch (err) {
      setError(String(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.4)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000, padding: '16px',
    }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div style={{
        background: '#fff', borderRadius: '16px', width: '100%', maxWidth: '520px',
        maxHeight: '90vh', overflow: 'auto',
        boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
      }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '20px 24px 16px', borderBottom: '1px solid #f1f5f9',
        }}>
          <h2 style={{ fontSize: '17px', fontWeight: 700 }}>Add Job Manually</h2>
          <button onClick={onClose} style={{ border: 'none', background: 'none', color: '#94a3b8', padding: 4 }}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '20px 24px' }}>
          {FIELD_LABELS.map(({ key, label, required, type }) => (
            <div key={key} style={{ marginBottom: '14px' }}>
              <label style={{ fontSize: '13px', fontWeight: 500, color: '#374151', display: 'block', marginBottom: '5px' }}>
                {label}{required && <span style={{ color: '#ef4444' }}> *</span>}
              </label>
              <input
                type={type ?? 'text'}
                value={(form[key] as string) ?? ''}
                onChange={e => set(key as keyof Job, e.target.value)}
                style={inputStyle}
              />
            </div>
          ))}

          <div style={{ marginBottom: '14px' }}>
            <label style={{ fontSize: '13px', fontWeight: 500, color: '#374151', display: 'block', marginBottom: '5px' }}>
              Status
            </label>
            <select value={form.status} onChange={e => set('status', e.target.value)} style={inputStyle}>
              {ALL_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div style={{ marginBottom: '18px' }}>
            <label style={{ fontSize: '13px', fontWeight: 500, color: '#374151', display: 'block', marginBottom: '5px' }}>
              Notes
            </label>
            <textarea
              value={form.notes ?? ''}
              onChange={e => set('notes', e.target.value)}
              rows={3}
              style={{ ...inputStyle, resize: 'vertical' }}
            />
          </div>

          {error && <p style={{ color: '#ef4444', fontSize: '13px', marginBottom: '12px' }}>{error}</p>}

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
            <button type="button" onClick={onClose} style={cancelBtnStyle}>Cancel</button>
            <button type="submit" disabled={saving} style={saveBtnStyle}>
              {saving ? 'Saving…' : 'Add Job'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '9px 12px',
  border: '1px solid #e2e8f0', borderRadius: '8px',
  fontSize: '14px', outline: 'none', color: '#0f172a',
  background: '#fafafa',
}
const cancelBtnStyle: React.CSSProperties = {
  padding: '9px 20px', border: '1px solid #e2e8f0', borderRadius: '8px',
  background: '#fff', color: '#475569', fontSize: '14px', fontWeight: 500,
}
const saveBtnStyle: React.CSSProperties = {
  padding: '9px 24px', border: 'none', borderRadius: '8px',
  background: '#6366f1', color: '#fff', fontSize: '14px', fontWeight: 600,
}
