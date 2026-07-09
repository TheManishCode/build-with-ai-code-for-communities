import { useQuery } from '@tanstack/react-query'
import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { X, Copy, Download, Check } from 'lucide-react'
import { api } from '../api/client'
import { Spinner } from './ui/StateDisplays'

export function DraftLetterModal({ workId, onClose }: { workId: string; onClose: () => void }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['letter', workId],
    queryFn: () => api.draftLetter(workId),
  })
  const [body, setBody] = useState('')
  const [copied, setCopied] = useState(false)
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (data) setBody(data.body)
  }, [data])

  useEffect(() => {
    closeButtonRef.current?.focus()
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  const handleCopy = async () => {
    await navigator.clipboard.writeText(body)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const blob = new Blob([body], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `draft-letter-${workId}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <motion.div
      className="modal-backdrop"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      role="presentation"
    >
      <motion.div
        className="modal-content"
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="draft-letter-title"
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 'var(--space-5)',
        }}>
          <h3
            id="draft-letter-title"
            style={{
              fontSize: 'var(--text-lg)',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
            }}
          >
            Draft Letter
          </h3>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            aria-label="Close draft letter dialog"
            className="btn btn-ghost btn-sm"
          >
            <X size={18} />
          </button>
        </div>

        {isLoading && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--space-10)' }}>
            <Spinner size={28} />
          </div>
        )}

        {error && (
          <div className="error-banner">
            Failed to generate letter: {(error as Error).message}
          </div>
        )}

        {data && (
          <>
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-2)',
              marginBottom: 'var(--space-4)',
              fontSize: 'var(--text-sm)',
              color: 'var(--color-text-secondary)',
            }}>
              <div>
                <span style={{ fontWeight: 600, color: 'var(--color-text-tertiary)' }}>To: </span>
                {data.to}
              </div>
              <div>
                <span style={{ fontWeight: 600, color: 'var(--color-text-tertiary)' }}>Subject: </span>
                {data.subject}
              </div>
            </div>

            <label htmlFor="draft-letter-body" className="sr-only">
              Draft letter body (editable)
            </label>
            <textarea
              id="draft-letter-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={16}
              className="input"
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 'var(--text-xs)',
                lineHeight: 'var(--leading-relaxed)',
                resize: 'vertical',
                minHeight: 200,
              }}
            />
            <p style={{
              marginTop: 'var(--space-2)',
              fontSize: 'var(--text-xs)',
              color: 'var(--color-text-muted)',
            }}>
              Editable before sending — edit freely, this is a draft.
            </p>

            <div style={{
              display: 'flex',
              gap: 'var(--space-3)',
              marginTop: 'var(--space-5)',
            }}>
              <button onClick={handleCopy} className="btn btn-secondary btn-sm">
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? 'Copied!' : 'Copy to clipboard'}
              </button>
              <button onClick={handleDownload} className="btn btn-primary btn-sm">
                <Download size={14} />
                Download as .txt
              </button>
            </div>
          </>
        )}
      </motion.div>
    </motion.div>
  )
}
