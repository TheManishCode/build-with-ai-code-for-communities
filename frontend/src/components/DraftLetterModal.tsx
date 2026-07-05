import { useQuery } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { api } from '../api/client'

export function DraftLetterModal({ workId, onClose }: { workId: string; onClose: () => void }) {
  const { data, isLoading, error } = useQuery({ queryKey: ['letter', workId], queryFn: () => api.draftLetter(workId) })
  const [body, setBody] = useState('')

  useEffect(() => {
    if (data) setBody(data.body)
  }, [data])

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Draft Letter</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
            ✕
          </button>
        </div>

        {isLoading && <div className="text-gray-500">Generating letter...</div>}
        {error && <div className="text-red-600">Failed to generate letter: {(error as Error).message}</div>}

        {data && (
          <>
            <div className="mb-2 text-sm text-gray-500">
              <span className="font-medium">To:</span> {data.to}
            </div>
            <div className="mb-3 text-sm text-gray-500">
              <span className="font-medium">Subject:</span> {data.subject}
            </div>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={20}
              className="w-full rounded-md border border-gray-300 p-3 font-mono text-sm leading-relaxed dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
            />
            <p className="mt-2 text-xs text-gray-400">Editable before sending -- edit freely, this is a draft.</p>
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
