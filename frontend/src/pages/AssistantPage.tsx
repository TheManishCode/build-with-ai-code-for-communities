import { useRef, useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Send, Bot, User, Search } from 'lucide-react'
import { isAxiosError } from 'axios'
import { api } from '../api/client'
import type { ChatMessage } from '../api/types'
import { PageWrapper, PageHeader } from '../components/ui/PageWrapper'
import { Spinner } from '../components/ui/StateDisplays'

const EXAMPLE_QUESTIONS = [
  "Why wasn't my report funded?",
  "What's happening in Chikkur village?",
  'I want to report a broken hand pump.',
  'How much money has been spent in my constituency?',
]

const SOURCE_LABELS: Record<string, string> = {
  search_villages: 'Village search',
  get_village_detail: 'Village facts',
  get_ranked_works: 'Ranked works',
  get_work_detail: 'Work detail',
  get_citizen_status: 'Your report status',
  get_transparency_summary: 'Transparency summary',
  get_budget_justification: 'Budget evidence',
  file_grievance: 'Filed a new report',
}

interface DisplayMessage extends ChatMessage {
  sources?: string[]
  isError?: boolean
}

function extractErrorMessage(err: unknown): string {
  if (isAxiosError(err)) {
    if (err.response?.status === 429) return "I'm getting a lot of questions right now — please wait a minute and try again."
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
  }
  return "Something went wrong on my end. Please try again in a moment."
}

export function AssistantPage() {
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending])

  const send = async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || sending) return
    const next: DisplayMessage[] = [...messages, { role: 'user', content: trimmed }]
    setMessages(next)
    setInput('')
    setSending(true)
    try {
      const res = await api.chat(next.map((m) => ({ role: m.role, content: m.content })))
      setMessages([...next, { role: 'assistant', content: res.reply, sources: res.sources }])
    } catch (err) {
      setMessages([...next, { role: 'assistant', content: extractErrorMessage(err), isError: true }])
    } finally {
      setSending(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    send(input)
  }

  return (
    <PageWrapper>
      <PageHeader
        title="Ask for Help"
        subtitle="Ask about your report, a village, or the priority list — or describe a problem and I'll help you file it."
      />

      <div className="card card-flush" style={{ display: 'flex', flexDirection: 'column', height: 560, maxWidth: 680, margin: '0 auto' }}>
        <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-5)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {messages.length === 0 && (
            <div style={{ margin: 'auto', textAlign: 'center', maxWidth: 420 }}>
              <Bot size={28} style={{ color: 'var(--color-text-tertiary)', marginBottom: 'var(--space-3)' }} />
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-tertiary)', marginBottom: 'var(--space-4)' }}>
                Try asking:
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {EXAMPLE_QUESTIONS.map((q) => (
                  <button key={q} onClick={() => send(q)} className="btn btn-secondary btn-sm" style={{ justifyContent: 'flex-start' }}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              style={{ display: 'flex', flexDirection: 'column', alignItems: m.role === 'user' ? 'flex-end' : 'flex-start' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                {m.role === 'assistant' && <Bot size={13} style={{ color: 'var(--color-text-muted)' }} />}
                <span style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                  {m.role === 'user' ? 'You' : 'Assistant'}
                </span>
                {m.role === 'user' && <User size={13} style={{ color: 'var(--color-text-muted)' }} />}
              </div>
              <div
                style={{
                  maxWidth: '85%',
                  padding: 'var(--space-3) var(--space-4)',
                  borderRadius: 'var(--radius-lg)',
                  fontSize: 'var(--text-sm)',
                  lineHeight: 'var(--leading-relaxed)',
                  whiteSpace: 'pre-wrap',
                  background: m.role === 'user' ? 'var(--color-accent-dim)' : 'var(--color-bg-elevated)',
                  color: m.isError ? 'var(--status-critical)' : 'var(--color-text-primary)',
                }}
              >
                {m.content}
              </div>
              {m.sources && m.sources.length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 4, fontSize: '0.6875rem', color: 'var(--color-text-muted)' }}>
                  <Search size={11} />
                  Looked up: {m.sources.map((s) => SOURCE_LABELS[s] || s).join(', ')}
                </div>
              )}
            </motion.div>
          ))}

          {sending && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>
              <Bot size={13} /> <Spinner size={14} /> Thinking…
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 'var(--space-3)', padding: 'var(--space-4)', borderTop: '1px solid var(--color-border-default)' }}>
          <input
            className="input"
            placeholder="Type your question or describe a problem…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={sending}
            aria-label="Message"
          />
          <button type="submit" className="btn btn-primary" disabled={sending || !input.trim()} aria-label="Send">
            <Send size={16} />
          </button>
        </form>
      </div>
    </PageWrapper>
  )
}
