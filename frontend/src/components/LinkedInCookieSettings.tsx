import { useEffect, useState } from 'react'
import { Key, Trash2, Check } from 'lucide-react'
import { api } from '../api'

export default function LinkedInCookieSettings() {
  const [cookieSet, setCookieSet] = useState(false)
  const [preview, setPreview] = useState('')
  const [input, setInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [showInput, setShowInput] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.linkedin.getCookie().then(r => {
      setCookieSet(r.set)
      setPreview(r.preview)
    }).catch(() => {})
  }, [])

  const handleSave = async () => {
    if (!input.trim()) return
    setSaving(true)
    try {
      await api.linkedin.setCookie(input.trim())
      setCookieSet(true)
      setPreview(input.trim().slice(0, 12) + '...')
      setInput('')
      setShowInput(false)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    await api.linkedin.deleteCookie()
    setCookieSet(false)
    setPreview('')
    setShowInput(false)
  }

  return (
    <div style={{
      background: '#fff', border: '1px solid #e2e8f0',
      borderRadius: '14px', padding: '20px', marginBottom: '24px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <Key size={16} color="#0a66c2" />
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#0f172a' }}>LinkedIn — Authenticated Scraping</h3>
            {cookieSet && (
              <span style={{
                fontSize: '11px', fontWeight: 600, color: '#15803d',
                background: '#dcfce7', padding: '2px 8px', borderRadius: '20px',
              }}>Active</span>
            )}
          </div>
          <p style={{ fontSize: '12px', color: '#64748b' }}>
            {cookieSet
              ? `Cookie set (${preview}) — scraper will run as your LinkedIn account for full results.`
              : 'Add your li_at cookie to unlock full LinkedIn results (Stripe, Amazon, Intuit, PayPal, etc.)'}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          {cookieSet && (
            <button onClick={handleDelete} style={{
              display: 'flex', alignItems: 'center', gap: '5px',
              padding: '7px 12px', border: '1px solid #fca5a5',
              borderRadius: '8px', background: '#fff5f5', color: '#ef4444',
              fontSize: '13px', fontWeight: 500,
            }}>
              <Trash2 size={13} /> Remove
            </button>
          )}
          {!showInput && (
            <button onClick={() => setShowInput(true)} style={{
              display: 'flex', alignItems: 'center', gap: '5px',
              padding: '7px 14px', border: 'none',
              borderRadius: '8px', background: '#6366f1', color: '#fff',
              fontSize: '13px', fontWeight: 600,
            }}>
              <Key size={14} /> {cookieSet ? 'Update Cookie' : 'Set Cookie'}
            </button>
          )}
        </div>
      </div>

      {saved && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          marginTop: '12px', padding: '10px 14px',
          background: '#f0fdf4', border: '1px solid #86efac',
          borderRadius: '8px', fontSize: '13px', color: '#166534',
        }}>
          <Check size={14} /> Cookie saved — next scrape will use your LinkedIn session.
        </div>
      )}

      {showInput && (
        <div style={{ marginTop: '14px' }}>
          <div style={{
            padding: '12px 14px', background: '#fffbeb', border: '1px solid #fde68a',
            borderRadius: '10px', fontSize: '12px', color: '#92400e', marginBottom: '10px', lineHeight: 1.6,
          }}>
            <strong>How to get your full LinkedIn cookie string:</strong><br />
            1. Open <strong>linkedin.com</strong> in Chrome while logged in<br />
            2. Press <strong>F12</strong> → <strong>Network</strong> tab → refresh the page<br />
            3. Click any request to <strong>linkedin.com</strong> in the list<br />
            4. In <strong>Request Headers</strong>, find the <strong>cookie:</strong> line<br />
            5. Copy the entire value (it's long — starts with things like <code>bcookie=</code> or <code>li_at=</code>)
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              type="password"
              placeholder="Paste li_at cookie value here…"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSave()}
              style={{
                flex: 1, padding: '9px 12px',
                border: '1px solid #e2e8f0', borderRadius: '8px',
                fontSize: '13px', outline: 'none', fontFamily: 'monospace',
              }}
            />
            <button
              onClick={handleSave}
              disabled={saving || !input.trim()}
              style={{
                padding: '9px 18px', border: 'none',
                borderRadius: '8px', background: saving ? '#93c5fd' : '#0a66c2',
                color: '#fff', fontSize: '13px', fontWeight: 600,
                opacity: !input.trim() ? 0.5 : 1,
              }}
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button
              onClick={() => { setShowInput(false); setInput('') }}
              style={{
                padding: '9px 14px', border: '1px solid #e2e8f0',
                borderRadius: '8px', background: '#fff', color: '#64748b',
                fontSize: '13px',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
