import { useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { api, API_BASE } from '../api/client'
import type { SubmissionChannel, SubmissionResponse } from '../api/types'

const LANGUAGES: { code: string; label: string; speechLang: string }[] = [
  { code: 'en', label: 'English', speechLang: 'en-IN' },
  { code: 'kn', label: 'ಕನ್ನಡ (Kannada)', speechLang: 'kn-IN' },
  { code: 'hi', label: 'हिन्दी (Hindi)', speechLang: 'hi-IN' },
  { code: 'mr', label: 'मराठी (Marathi)', speechLang: 'mr-IN' },
  { code: 'auto', label: 'Other / not sure', speechLang: 'en-IN' },
]

const MODES: { id: SubmissionChannel; label: string; hint: string }[] = [
  { id: 'text', label: 'Type', hint: 'Write your report in your own words.' },
  { id: 'voice', label: 'Speak', hint: 'Record your report; it is transcribed to text you can edit.' },
  { id: 'photo', label: 'Photo', hint: 'Attach a photo of the problem with a short caption.' },
]

// Minimal ambient typing for the non-standard (webkit-prefixed) SpeechRecognition API --
// not part of the DOM lib, so TypeScript has no built-in types for it.
interface SpeechRecognitionLike extends EventTarget {
  lang: string
  interimResults: boolean
  continuous: boolean
  start: () => void
  stop: () => void
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null
  onerror: ((event: Event) => void) | null
  onend: (() => void) | null
}

function getSpeechRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  const w = window as unknown as {
    SpeechRecognition?: new () => SpeechRecognitionLike
    webkitSpeechRecognition?: new () => SpeechRecognitionLike
  }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

export function SubmitReportForm({ onViewStatus }: { onViewStatus: (submissionId: number) => void }) {
  const [mode, setMode] = useState<SubmissionChannel>('text')
  const [languageCode, setLanguageCode] = useState('en')
  const [rawText, setRawText] = useState('')
  const [photo, setPhoto] = useState<File | null>(null)
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null)
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const speechSupported = getSpeechRecognitionCtor() !== null

  const language = LANGUAGES.find((l) => l.code === languageCode) ?? LANGUAGES[0]

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop()
      if (photoPreviewUrl) URL.revokeObjectURL(photoPreviewUrl)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const mutation = useMutation({
    mutationFn: (input: { channel: SubmissionChannel; rawText: string; language: string; photo: File | null }) =>
      api.submitReport(input),
  })

  const handleToggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop()
      return
    }
    const Ctor = getSpeechRecognitionCtor()
    if (!Ctor) return
    const recognition = new Ctor()
    recognition.lang = language.speechLang
    recognition.interimResults = false
    recognition.continuous = false
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript
      if (transcript) setRawText((prev) => (prev ? `${prev} ${transcript}` : transcript))
    }
    recognition.onerror = () => setIsListening(false)
    recognition.onend = () => setIsListening(false)
    recognitionRef.current = recognition
    recognition.start()
    setIsListening(true)
  }

  const handlePhotoChange = (file: File | null) => {
    if (photoPreviewUrl) URL.revokeObjectURL(photoPreviewUrl)
    setPhoto(file)
    setPhotoPreviewUrl(file ? URL.createObjectURL(file) : null)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate({ channel: mode, rawText, language: languageCode, photo })
  }

  const handleReset = () => {
    setRawText('')
    handlePhotoChange(null)
    mutation.reset()
  }

  if (mutation.isSuccess) {
    return <SubmissionConfirmation result={mutation.data} onSubmitAnother={handleReset} onViewStatus={onViewStatus} />
  }

  const errorMessage = mutation.isError
    ? isAxiosError(mutation.error) && typeof mutation.error.response?.data?.detail === 'string'
      ? mutation.error.response.data.detail
      : 'Something went wrong sending your report. Please try again.'
    : null

  return (
    <div className="mx-auto max-w-lg p-4">
      <h2 className="mb-1 text-lg font-semibold text-gray-900 dark:text-gray-100">Report a Development Issue</h2>
      <p className="mb-4 text-sm text-gray-500">
        Tell us about a water, road, school, health, electricity, or sanitation problem in your village. Every
        report is read and counted toward the constituency's ranked priorities.
      </p>

      <form onSubmit={handleSubmit}>
        <fieldset className="mb-4">
          <legend className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">How would you like to report?</legend>
          <div role="radiogroup" aria-label="Report mode" className="flex gap-2">
            {MODES.map((m) => (
              <button
                key={m.id}
                type="button"
                role="radio"
                aria-checked={mode === m.id}
                onClick={() => setMode(m.id)}
                className={`flex-1 rounded-md border px-3 py-2 text-sm font-medium ${
                  mode === m.id
                    ? 'border-gray-900 bg-gray-900 text-white dark:border-gray-100 dark:bg-gray-100 dark:text-gray-900'
                    : 'border-gray-300 text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
          <p className="mt-1 text-xs text-gray-500">{MODES.find((m) => m.id === mode)?.hint}</p>
        </fieldset>

        <div className="mb-4">
          <label htmlFor="report-language" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Language
          </label>
          <select
            id="report-language"
            value={languageCode}
            onChange={(e) => setLanguageCode(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </div>

        {mode === 'photo' && (
          <div className="mb-4">
            <label htmlFor="report-photo" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Photo
            </label>
            <input
              id="report-photo"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => handlePhotoChange(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-gray-700 dark:text-gray-300"
            />
            {photoPreviewUrl && (
              <img src={photoPreviewUrl} alt="Selected photo preview" className="mt-2 h-32 w-32 rounded-md object-cover" />
            )}
          </div>
        )}

        <div className="mb-4">
          <div className="mb-1 flex items-center justify-between">
            <label htmlFor="report-text" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {mode === 'photo' ? 'Caption -- describe the problem' : 'Describe the problem'}
            </label>
            {mode === 'voice' && speechSupported && (
              <button
                type="button"
                onClick={handleToggleListening}
                aria-pressed={isListening}
                className={`rounded-md px-2.5 py-1 text-xs font-medium ${
                  isListening
                    ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                    : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-100'
                }`}
              >
                {isListening ? '● Listening... tap to stop' : '🎤 Tap to speak'}
              </button>
            )}
          </div>
          {mode === 'voice' && !speechSupported && (
            <p className="mb-1 text-xs text-amber-600 dark:text-amber-400">
              Voice input isn't supported in this browser -- please type your report below instead.
            </p>
          )}
          <textarea
            id="report-text"
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            rows={5}
            maxLength={2000}
            placeholder="e.g. There has been no drinking water in our village for 3 days, the borewell motor is not working."
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          />
          <p className="mt-1 text-right text-xs text-gray-400">{rawText.length}/2000</p>
        </div>

        {errorMessage && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            {errorMessage}
          </div>
        )}

        <button
          type="submit"
          disabled={mutation.isPending || rawText.trim().length === 0}
          className="w-full rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-gray-100 dark:text-gray-900"
        >
          {mutation.isPending ? 'Submitting...' : 'Submit Report'}
        </button>
      </form>
    </div>
  )
}

function SubmissionConfirmation({
  result,
  onSubmitAnother,
  onViewStatus,
}: {
  result: SubmissionResponse
  onSubmitAnother: () => void
  onViewStatus: (submissionId: number) => void
}) {
  return (
    <div className="mx-auto max-w-lg p-4">
      <div className="rounded-lg border border-green-200 bg-green-50 p-5 dark:border-green-900 dark:bg-green-950">
        <h2 className="mb-1 text-lg font-semibold text-green-900 dark:text-green-200">Report received</h2>
        <p className="text-sm text-green-800 dark:text-green-300">
          Thank you -- your report has been recorded and will be weighed alongside other citizen reports and
          infrastructure data when priorities are ranked.
        </p>

        <div className="mt-4 grid grid-cols-2 gap-3 border-t border-green-200 pt-4 text-sm dark:border-green-800">
          <Field label="Submission ID" value={`#${result.submission_id}`} />
          <Field label="Category" value={result.theme} />
          <Field label="Village" value={result.village_name ?? 'Not automatically identified'} />
          <Field label="Language" value={result.language} />
        </div>

        {result.photo_url && (
          <img
            src={`${API_BASE}${result.photo_url}`}
            alt="Attached photo evidence"
            className="mt-4 h-32 w-32 rounded-md object-cover"
          />
        )}

        {!result.village_name && (
          <p className="mt-3 text-xs text-amber-700 dark:text-amber-400">
            We couldn't automatically identify the village from your text. Your report is still recorded -- an
            office reviewer can add it later.
          </p>
        )}

        <p className="mt-4 text-xs text-green-700 dark:text-green-400">
          Save your submission ID to check its status later.
        </p>
      </div>

      <div className="mt-4 flex gap-2">
        <button
          onClick={() => onViewStatus(result.submission_id)}
          className="flex-1 rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 dark:bg-gray-100 dark:text-gray-900"
        >
          Check my report status
        </button>
        <button
          onClick={onSubmitAnother}
          className="flex-1 rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
        >
          Submit another report
        </button>
      </div>
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-gray-400">{label}</div>
      <div className="font-medium text-gray-900 dark:text-gray-100">{value}</div>
    </div>
  )
}
