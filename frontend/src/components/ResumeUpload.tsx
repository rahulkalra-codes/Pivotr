import { useRef, useState } from 'react'
import { Upload, FileText, Trash2, Star, CheckCircle } from 'lucide-react'
import type { ResumeInfo } from '../types'
import { api } from '../api'

interface Props {
  resume: ResumeInfo | null
  onUpdate: (r: ResumeInfo | null) => void
}

export default function ResumeUpload({ resume, onUpdate }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  const handleFile = async (file: File) => {
    setUploading(true)
    setError('')
    try {
      const result = await api.resume.upload(file)
      onUpdate(result)
    } catch (e) {
      setError(String(e))
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async () => {
    await api.resume.delete()
    onUpdate(null)
  }

  return (
    <div style={{
      background: '#fff', border: '1px solid #e2e8f0',
      borderRadius: '14px', padding: '20px', marginBottom: '24px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <FileText size={16} color="#6366f1" />
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#0f172a' }}>Resume — Smart Matching</h3>
          </div>
          <p style={{ fontSize: '12px', color: '#64748b' }}>
            Upload your resume (PDF or TXT) to see a relevance % score on each job card.
          </p>
        </div>

        {resume?.uploaded ? (
          <button onClick={handleDelete} style={{
            display: 'flex', alignItems: 'center', gap: '5px',
            padding: '7px 12px', border: '1px solid #fca5a5',
            borderRadius: '8px', background: '#fff5f5', color: '#ef4444',
            fontSize: '13px', fontWeight: 500,
          }}>
            <Trash2 size={13} /> Remove
          </button>
        ) : (
          <>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.txt"
              style={{ display: 'none' }}
              onChange={e => { if (e.target.files?.[0]) handleFile(e.target.files[0]) }}
            />
            <button
              onClick={() => inputRef.current?.click()}
              disabled={uploading}
              style={{
                display: 'flex', alignItems: 'center', gap: '5px',
                padding: '8px 16px', border: 'none',
                borderRadius: '8px', background: '#6366f1', color: '#fff',
                fontSize: '13px', fontWeight: 600,
                opacity: uploading ? 0.6 : 1,
              }}
            >
              <Upload size={14} /> {uploading ? 'Parsing…' : 'Upload Resume'}
            </button>
          </>
        )}
      </div>

      {resume?.uploaded && (
        <div style={{
          display: 'flex', gap: '16px', flexWrap: 'wrap', marginTop: '14px',
          padding: '12px 14px', background: '#f8faff', borderRadius: '10px',
          border: '1px solid #e0e7ff',
        }}>
          <Badge icon={<CheckCircle size={13} color="#22c55e" />}
            label={`${resume.years_experience != null ? resume.years_experience + ' yrs exp' : 'Exp detected'}`} />
          {resume.current_title && (
            <Badge icon={<Star size={13} color="#f59e0b" />} label={resume.current_title} />
          )}
          {resume.skills && resume.skills.length > 0 && (
            <Badge icon={<span style={{ fontSize: 13 }}>🎯</span>}
              label={`${resume.skills.length} skills matched`} />
          )}
        </div>
      )}

      {error && <p style={{ color: '#ef4444', fontSize: '13px', marginTop: '8px' }}>{error}</p>}
    </div>
  )
}

function Badge({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px',
      fontSize: '13px', color: '#374151', fontWeight: 500,
    }}>
      {icon}{label}
    </span>
  )
}
