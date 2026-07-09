import { useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { isAxiosError } from 'axios'
import { AlertTriangle, Camera, CheckCircle2, Keyboard, Mic, MicOff, Search } from 'lucide-react'
import { motion } from 'motion/react'
import { api, API_BASE } from '../api/client'
import type { SubmissionChannel, SubmissionResponse } from '../api/types'
import { Card } from './ui/Card'
import { Button } from './ui/Button'
import { PageHeader } from './ui/PageState'
import { springy } from '../lib/motion'

const LANGUAGES: { code: string; label: string; speechLang: string }[] = [
  { code: 'en', label: 'English', speechLang: 'en-IN' },
  { code: 'kn', label: 'ಕನ್ನಡ (Kannada)', speechLang: 'kn-IN' },
  { code: 'hi', label: 'हिन्दी (Hindi)', speechLang: 'hi-IN' },
  { code: 'mr', label: 'मराठी (Marathi)', speechLang: 'mr-IN' },
  { code: 'auto', label: 'Other / not sure', speechLang: 'en-IN' },
]

const MODES: { id: SubmissionChannel; label: string; hint: string; icon: typeof Keyboard }[] = [
  { id: 'text', label: 'Type', hint: 'Write your report in your own words.', icon: Keyboard },
  { id: 'voice', label: 'Speak', hint: 'Record your report; it is transcribed to text you can edit.', icon: Mic },
  { id: 'photo', label: 'Photo', hint: 'Attach a photo of the problem with a short caption.', icon: Camera },
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

export function SubmitReportForm() {
  const navigate = useNavigate()
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
    return (
      <SubmissionConfirmation
        result={mutation.data}
        onSubmitAnother={handleReset}
        onViewStatus={(id) => navigate(`/status/${id}`)}
      />
    )
  }

  const errorMessage = mutation.isError
    ? isAxiosError(mutation.error) && typeof mutation.error.response?.data?.detail === 'string'
      ? mutation.error.response.data.detail
      : 'Something went wrong sending your report. Please try again.'
    : null

  return (
    <div className="mx-auto max-w-lg px-4">
      <PageHeader
        title="Report a Development Issue"
        subtitle="Tell us about a water, road, school, health, electricity, or sanitation problem in your village. Every report is read and counted toward the constituency's ranked priorities."
      />

      <form onSubmit={handleSubmit}>
        <fieldset className="mb-5">
          <legend className="mb-2 text-sm font-medium text-stone-700 dark:text-stone-300">How would you like to report?</legend>
          <div role="radiogroup" aria-label="Report mode" className="grid grid-cols-3 gap-2">
            {MODES.map((m) => {
              const Icon = m.icon
              const active = mode === m.id
              return (
                <button
                  key={m.id}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => setMode(m.id)}
                  className={`relative flex flex-col items-center gap-1.5 rounded-md border px-3 py-2.5 text-sm font-medium transition-colors ${
                    active
                      ? 'border-accent-600 text-accent-800 dark:border-accent-400 dark:text-accent-200'
                      : 'border-stone-300 text-stone-600 hover:bg-stone-50 dark:border-stone-700 dark:text-stone-300 dark:hover:bg-stone-800'
                  }`}
                >
                  {active && (
                    <motion.span
                      layoutId="mode-active-bg"
                      className="absolute inset-0 -z-10 rounded-md bg-accent-50 dark:bg-accent-900/30"
                      transition={springy}
                    />
                  )}
                  <Icon size={17} aria-hidden="true" />
                  {m.label}
                </button>
              )
            })}
          </div>
          <p className="mt-1.5 text-xs text-stone-500 dark:text-stone-400">{MODES.find((m) => m.id === mode)?.hint}</p>
        </fieldset>

        <div className="mb-5">
          <label htmlFor="report-language" className="mb-1 block text-sm font-medium text-stone-700 dark:text-stone-300">
            Language
          </label>
          <select
            id="report-language"
            value={languageCode}
            onChange={(e) => setLanguageCode(e.target.value)}
            className="w-full rounded-md border border-stone-300 bg-stone-50 px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100"
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </div>

        {mode === 'photo' && (
          <div className="mb-5">
            <label htmlFor="report-photo" className="mb-1 block text-sm font-medium text-stone-700 dark:text-stone-300">
              Photo
            </label>
            <input
              id="report-photo"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => handlePhotoChange(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-stone-700 dark:text-stone-300"
            />
            {photoPreviewUrl && (
              <img src={photoPreviewUrl} alt="Selected photo preview" className="mt-2 h-32 w-32 rounded-md object-cover" />
            )}
          </div>
        )}

        <div className="mb-5">
          <div className="mb-1 flex items-center justify-between">
            <label htmlFor="report-text" className="text-sm font-medium text-stone-700 dark:text-stone-300">
              {mode === 'photo' ? 'Caption -- describe the problem' : 'Describe the problem'}
            </label>
            {mode === 'voice' && speechSupported && (
              <button
                type="button"
                onClick={handleToggleListening}
                aria-pressed={isListening}
                className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${
                  isListening
                    ? 'bg-critical/10 text-critical'
                    : 'bg-stone-100 text-stone-800 dark:bg-stone-800 dark:text-stone-100'
                }`}
              >
                {isListening ? <MicOff size={13} aria-hidden="true" /> : <Mic size={13} aria-hidden="true" />}
                {isListening ? 'Listening... tap to stop' : 'Tap to speak'}
              </button>
            )}
          </div>
          {mode === 'voice' && !speechSupported && (
            <p className="mb-1 flex items-center gap-1 text-xs text-warning">
              <AlertTriangle size={13} aria-hidden="true" />
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
            className="w-full rounded-md border border-stone-300 bg-stone-50 px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100"
          />
          <p className="mt-1 text-right text-xs tabular-nums text-stone-400">{rawText.length}/2000</p>
        </div>

        {errorMessage && (
          <div className="mb-5 flex items-start gap-2 rounded-md border border-critical/20 bg-critical/5 p-3 text-sm text-critical dark:bg-critical/10">
            <AlertTriangle size={15} className="mt-0.5 shrink-0" aria-hidden="true" />
            {errorMessage}
          </div>
        )}

        <Button type="submit" disabled={mutation.isPending || rawText.trim().length === 0} className="w-full">
          {mutation.isPending ? 'Submitting...' : 'Submit Report'}
        </Button>
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
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springy}
      className="mx-auto max-w-lg px-4"
    >
      <Card className="border-good/25 bg-good/5 p-5 dark:bg-good/10">
        <div className="mb-1 flex items-center gap-2">
          <CheckCircle2 size={18} className="text-good" aria-hidden="true" />
          <h2 className="font-display text-lg font-medium text-stone-900 dark:text-stone-50">Report received</h2>
        </div>
        <p className="text-sm text-stone-700 dark:text-stone-300">
          Thank you -- your report has been recorded and will be weighed alongside other citizen reports and
          infrastructure data when priorities are ranked.
        </p>

        <div className="mt-4 grid grid-cols-2 gap-3 border-t border-good/20 pt-4 text-sm">
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
          <p className="mt-3 flex items-start gap-1.5 text-xs text-warning">
            <AlertTriangle size={13} className="mt-0.5 shrink-0" aria-hidden="true" />
            We couldn't automatically identify the village from your text. Your report is still recorded -- an
            office reviewer can add it later.
          </p>
        )}

        <p className="mt-4 text-xs text-stone-500 dark:text-stone-400">Save your submission ID to check its status later.</p>
      </Card>

      <div className="mt-4 flex gap-2">
        <Button className="flex flex-1 items-center justify-center gap-1.5" onClick={() => onViewStatus(result.submission_id)}>
          <Search size={14} aria-hidden="true" />
          Check my report status
        </Button>
        <Button variant="secondary" className="flex-1" onClick={onSubmitAnother}>
          Submit another report
        </Button>
      </div>
    </motion.div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-stone-400">{label}</div>
      <div className="font-medium text-stone-900 dark:text-stone-100">{value}</div>
    </div>
  )
}
