import { useRef, useState, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { MessageCircle, X, Send, Bot, User, Search } from 'lucide-react'
import { isAxiosError } from 'axios'
import { api } from '../api/client'
import type { ChatMessage } from '../api/types'
import { Spinner } from './ui/StateDisplays'

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

export function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending, open])

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
    <>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
            role="dialog"
            aria-label="Assistant"
            style={{
              position: 'fixed',
              bottom: 92,
              right: 24,
              width: 'min(380px, calc(100vw - 32px))',
              height: 'min(560px, calc(100vh - 140px))',
              background: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border-default)',
              borderRadius: 'var(--radius-xl)',
              boxShadow: '0 24px 64px rgba(0, 0, 0, 0.45)',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              zIndex: 70,
            }}
          >
            <div style={{
              padding: 'var(--space-4) var(--space-5)',
              borderBottom: '1px solid var(--color-border-default)',
            }}>
              <div style={{ fontSize: 'var(--text-sm)', fontWeight: 650, color: 'var(--color-text-primary)' }}>
                Assistant
              </div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-tertiary)', marginTop: 2 }}>
                Ask about a report, a village, or describe a problem to file one
              </div>
            </div>

            <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {messages.length === 0 && (
                <div style={{ margin: 'auto', textAlign: 'center', maxWidth: 300, padding: 'var(--space-4)' }}>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)', marginBottom: 'var(--space-3)' }}>
                    Try asking:
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                    {EXAMPLE_QUESTIONS.map((q) => (
                      <button key={q} onClick={() => send(q)} className="btn btn-secondary btn-sm" style={{ justifyContent: 'flex-start', textAlign: 'left' }}>
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((m, i) => (
                <div
                  key={i}
                  style={{ display: 'flex', flexDirection: 'column', alignItems: m.role === 'user' ? 'flex-end' : 'flex-start' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                    {m.role === 'assistant' && <Bot size={12} style={{ color: 'var(--color-text-muted)' }} />}
                    <span style={{ fontSize: '0.625rem', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                      {m.role === 'user' ? 'You' : 'Assistant'}
                    </span>
                    {m.role === 'user' && <User size={12} style={{ color: 'var(--color-text-muted)' }} />}
                  </div>
                  <div
                    style={{
                      maxWidth: '92%',
                      padding: 'var(--space-2) var(--space-3)',
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
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 4, fontSize: '0.625rem', color: 'var(--color-text-muted)' }}>
                      <Search size={10} />
                      {m.sources.map((s) => SOURCE_LABELS[s] || s).join(', ')}
                    </div>
                  )}
                </div>
              ))}

              {sending && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>
                  <Bot size={13} /> <Spinner size={14} /> Thinking…
                </div>
              )}
            </div>

            <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 'var(--space-2)', padding: 'var(--space-3)', borderTop: '1px solid var(--color-border-default)' }}>
              <input
                className="input"
                placeholder="Type a message…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={sending}
                aria-label="Message"
              />
              <button type="submit" className="btn btn-primary" disabled={sending || !input.trim()} aria-label="Send">
                <Send size={15} />
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? 'Close assistant' : 'Open assistant'}
        aria-expanded={open}
        style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          width: 52,
          height: 52,
          borderRadius: 'var(--radius-full)',
          background: 'var(--color-accent)',
          color: '#17130a',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.35)',
          zIndex: 71,
          transition: 'transform var(--duration-fast) var(--ease-out-expo)',
        }}
      >
        {open ? <X size={22} /> : <MessageCircle size={22} />}
      </button>
    </>
  )
}
