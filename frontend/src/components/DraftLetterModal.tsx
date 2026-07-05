import { useQuery } from '@tanstack/react-query'
import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'

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
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="draft-letter-title"
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 id="draft-letter-title" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Draft Letter
          </h3>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            aria-label="Close draft letter dialog"
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <span aria-hidden="true">✕</span>
          </button>
        </div>

        {isLoading && <div className="text-gray-500">Generating letter...</div>}
        {error && <div className="text-red-600">Failed to generate letter: {(error as Error).message}</div>}

        {data && (
          <>
            <div className="mb-2 text-sm text-gray-600 dark:text-gray-400">
              <span className="font-medium">To:</span> {data.to}
            </div>
            <div className="mb-3 text-sm text-gray-600 dark:text-gray-400">
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
              className="w-full rounded-md border border-gray-300 p-3 font-mono text-sm leading-relaxed dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
            />
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Editable before sending -- edit freely, this is a draft.</p>
            <div className="mt-4 flex gap-2">
              <button
                onClick={handleCopy}
                className="rounded-md bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-800 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-100"
              >
                Copy to clipboard
              </button>
              <button
                onClick={handleDownload}
                className="rounded-md bg-gray-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-700 dark:bg-gray-100 dark:text-gray-900"
              >
                Download as .txt
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
