import { useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Camera, CheckCircle2, Loader2, Send, X } from 'lucide-react'
import { isAxiosError } from 'axios'
import { api } from '../api/client'
import type { SubmissionResponse } from '../api/types'
import { PageWrapper, PageHeader } from '../components/ui/PageWrapper'

const MAX_TEXT_LENGTH = 2000
const MAX_PHOTO_BYTES = 8 * 1024 * 1024

const THEME_LABELS: Record<string, string> = {
  water: 'Water', road: 'Roads', school: 'Education',
  health: 'Health', electricity: 'Electricity', sanitation: 'Sanitation', other: 'Other',
}

function extractErrorMessage(err: unknown): string {
  if (isAxiosError(err)) {
    if (err.response?.status === 429) return "You've reported a few times in quick succession — please wait a minute and try again."
    if (err.response?.status === 503) return 'Photo uploads are temporarily unavailable. You can still send your report without a photo.'
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
  }
  return "Something went wrong sending your report. Please try again in a moment."
}

export function ReportIssuePage() {
  const [text, setText] = useState('')
  const [language, setLanguage] = useState('en')
  const [photo, setPhoto] = useState<File | null>(null)
  const [photoError, setPhotoError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<SubmissionResponse | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handlePhotoChange = (file: File | null) => {
    setPhotoError(null)
    if (!file) { setPhoto(null); return }
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setPhotoError('Photos must be JPEG, PNG, or WebP.')
      return
    }
    if (file.size > MAX_PHOTO_BYTES) {
      setPhotoError('Photo must be smaller than 8MB.')
      return
    }
    setPhoto(file)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await api.submitReport({
        channel: photo ? 'photo' : 'text',
        rawText: trimmed,
        language,
        photo,
      })
      setResult(res)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const reset = () => {
    setResult(null)
    setText('')
    setPhoto(null)
    setError(null)
  }

  return (
    <PageWrapper>
      <PageHeader
        title="Report an Issue"
        subtitle="Tell us what's happening in your area, in your own words. Every report helps decide what gets fixed next."
      />

      <AnimatePresence mode="wait">
        {result ? (
          <motion.div
            key="success"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="card"
            style={{ maxWidth: 560, margin: '0 auto' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
              <CheckCircle2 size={22} style={{ color: 'var(--status-good)' }} />
              <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 650, color: 'var(--color-text-primary)' }}>
                Report #{result.submission_id} received
              </h3>
            </div>

            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 'var(--leading-relaxed)', marginBottom: 'var(--space-4)' }}>
              We've logged this as a <strong style={{ color: 'var(--color-text-primary)' }}>{THEME_LABELS[result.theme] || result.theme}</strong> report
              {result.village_name
                ? <> for <strong style={{ color: 'var(--color-text-primary)' }}>{result.village_name}</strong>.</>
                : <>. We couldn't pinpoint a specific village from your description — if you'd like, submit another report mentioning the village by name so it's tracked accurately.</>
              }
              {result.issue_id != null && ' It has been grouped with other reports about the same issue, so it counts toward the constituency priority ranking.'}
            </p>

            {result.photo_url && (
              <img src={result.photo_url} alt="Submitted evidence" style={{ width: '100%', maxHeight: 220, objectFit: 'cover', borderRadius: 'var(--radius-md)', marginBottom: 'var(--space-4)' }} />
            )}

            <div className="callout callout-info" style={{ marginBottom: 'var(--space-4)' }}>
              <span>
                Save this ID — <strong>#{result.submission_id}</strong> — and check its status anytime on the{' '}
                <a href="/status" style={{ textDecoration: 'underline', fontWeight: 600 }}>Check My Report</a> page.
              </span>
            </div>

            <button onClick={reset} className="btn btn-secondary btn-sm">
              Report another issue
            </button>
          </motion.div>
        ) : (
          <motion.form
            key="form"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            onSubmit={handleSubmit}
            className="card"
            style={{ maxWidth: 560, margin: '0 auto' }}
          >
            <label htmlFor="report-text" style={{ display: 'block', fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 'var(--space-2)' }}>
              What's the problem?
            </label>
            <textarea
              id="report-text"
              className="input"
              rows={5}
              maxLength={MAX_TEXT_LENGTH}
              placeholder="e.g. The hand pump near the Chikkur village school has been broken for two weeks and there's no other water source nearby."
              value={text}
              onChange={(e) => setText(e.target.value)}
              style={{ resize: 'vertical', lineHeight: 'var(--leading-relaxed)' }}
              required
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 'var(--space-1)', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
              <span>Mention the village by name — it helps us route your report accurately.</span>
              <span className="tabular-nums">{text.length}/{MAX_TEXT_LENGTH}</span>
            </div>

            <div style={{ display: 'flex', gap: 'var(--space-4)', marginTop: 'var(--space-5)', flexWrap: 'wrap' }}>
              <div style={{ flex: '1 1 160px' }}>
                <label htmlFor="report-language" style={{ display: 'block', fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 'var(--space-2)' }}>
                  Language
                </label>
                <select
                  id="report-language"
                  className="input select"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  <option value="en">English</option>
                  <option value="kn">ಕನ್ನಡ (Kannada)</option>
                </select>
              </div>

              <div style={{ flex: '1 1 200px' }}>
                <span style={{ display: 'block', fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 'var(--space-2)' }}>
                  Photo (optional)
                </span>
                {photo ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', padding: 'var(--space-2) var(--space-3)', background: 'var(--color-bg-elevated)', borderRadius: 'var(--radius-md)', fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
                    <Camera size={14} />
                    <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{photo.name}</span>
                    <button type="button" onClick={() => handlePhotoChange(null)} className="btn btn-ghost btn-sm" aria-label="Remove photo" style={{ padding: 2 }}>
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <button type="button" onClick={() => fileInputRef.current?.click()} className="btn btn-secondary btn-sm" style={{ width: '100%' }}>
                    <Camera size={14} /> Add a photo
                  </button>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(e) => handlePhotoChange(e.target.files?.[0] ?? null)}
                  style={{ display: 'none' }}
                />
                {photoError && <div style={{ fontSize: 'var(--text-xs)', color: 'var(--status-critical)', marginTop: 4 }}>{photoError}</div>}
              </div>
            </div>

            {error && <div className="error-banner" style={{ marginTop: 'var(--space-5)' }}>{error}</div>}

            <button type="submit" className="btn btn-primary" disabled={submitting || !text.trim()} style={{ marginTop: 'var(--space-5)', width: '100%' }}>
              {submitting ? <Loader2 size={16} className="spin" /> : <Send size={15} />}
              {submitting ? 'Sending…' : 'Send report'}
            </button>
            <p style={{ marginTop: 'var(--space-3)', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', textAlign: 'center' }}>
              No account needed. Your report is reviewed alongside every other citizen report and objective infrastructure data.
            </p>
          </motion.form>
        )}
      </AnimatePresence>
    </PageWrapper>
  )
}
