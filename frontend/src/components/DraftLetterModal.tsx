import { useQuery } from '@tanstack/react-query'
import { useState, useEffect, useRef } from 'react'
import { Copy, Download, X } from 'lucide-react'
import { motion } from 'motion/react'
import { api } from '../api/client'
import { Button } from './ui/Button'
import { springy } from '../lib/motion'

export function DraftLetterModal({ workId, onClose }: { workId: string; onClose: () => void }) {
  const { data, isLoading, error } = useQuery({ queryKey: ['letter', workId], queryFn: () => api.draftLetter(workId) })
  const [body, setBody] = useState('')
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (data) setBody(data.body)
  }, [data])

  // Accessibility: focus the close button on open, close on Escape (WCAG 2.1.2 -- a modal
  // must not trap keyboard/focus users without an escape route).
  useEffect(() => {
    closeButtonRef.current?.focus()
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  const handleCopy = () => {
    navigator.clipboard.writeText(body)
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
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/40 p-4"
      onClick={onClose}
      role="presentation"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.97, y: 6 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={springy}
        className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-md border border-stone-200 bg-stone-50 p-6 shadow-xl dark:border-stone-800 dark:bg-stone-900"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="draft-letter-title"
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 id="draft-letter-title" className="font-display text-lg font-medium text-stone-900 dark:text-stone-50">
            Draft Letter
          </h3>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            aria-label="Close draft letter dialog"
            className="rounded-full p-1 text-stone-500 hover:bg-stone-200 hover:text-stone-700 dark:text-stone-400 dark:hover:bg-stone-800 dark:hover:text-stone-200"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        {isLoading && <div className="text-stone-500">Generating letter...</div>}
        {error && <div className="text-critical">Failed to generate letter: {(error as Error).message}</div>}

        {data && (
          <>
            <div className="mb-2 text-sm text-stone-600 dark:text-stone-400">
              <span className="font-medium">To:</span> {data.to}
            </div>
            <div className="mb-3 text-sm text-stone-600 dark:text-stone-400">
              <span className="font-medium">Subject:</span> {data.subject}
            </div>
            <label htmlFor="draft-letter-body" className="sr-only">
              Draft letter body (editable)
            </label>
            <textarea
              id="draft-letter-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={20}
              className="w-full rounded-md border border-stone-300 p-3 font-mono text-sm leading-relaxed dark:border-stone-700 dark:bg-stone-950 dark:text-stone-100"
            />
            <p className="mt-2 text-xs text-stone-500 dark:text-stone-400">Editable before sending -- edit freely, this is a draft.</p>
            <div className="mt-4 flex gap-2">
              <Button variant="secondary" className="flex items-center gap-1.5" onClick={handleCopy}>
                <Copy size={14} aria-hidden="true" />
                Copy to clipboard
              </Button>
              <Button className="flex items-center gap-1.5" onClick={handleDownload}>
                <Download size={14} aria-hidden="true" />
                Download as .txt
              </Button>
            </div>
          </>
        )}
      </motion.div>
    </motion.div>
  )
}
