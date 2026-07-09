import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ReportIssuePage } from './ReportIssuePage'
import { api } from '../api/client'
import type { SubmissionResponse } from '../api/types'

vi.mock('../api/client', () => ({
  api: { submitReport: vi.fn() },
}))

function makeResponse(overrides: Partial<SubmissionResponse> = {}): SubmissionResponse {
  return {
    submission_id: 101,
    channel: 'text',
    language: 'en',
    translated_text: 'The hand pump near Chikkur village school is broken.',
    theme: 'water',
    resolved_village_code: 598748,
    village_name: 'Chikkur',
    place_match_score: 92,
    photo_url: null,
    issue_id: 12,
    created_at: '2026-07-09T00:00:00Z',
    ...overrides,
  }
}

describe('ReportIssuePage', () => {
  beforeEach(() => {
    vi.mocked(api.submitReport).mockReset()
  })

  it('disables submit until a description is entered', () => {
    render(<ReportIssuePage />)
    expect(screen.getByRole('button', { name: /send report/i })).toBeDisabled()
    fireEvent.change(screen.getByLabelText(/what's the problem/i), { target: { value: 'Broken hand pump' } })
    expect(screen.getByRole('button', { name: /send report/i })).not.toBeDisabled()
  })

  it('submits as channel=text when no photo is attached and shows the confirmation', async () => {
    vi.mocked(api.submitReport).mockResolvedValue(makeResponse())
    render(<ReportIssuePage />)

    fireEvent.change(screen.getByLabelText(/what's the problem/i), {
      target: { value: 'The hand pump near Chikkur village school is broken.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send report/i }))

    await waitFor(() => expect(screen.getByText(/report #101 received/i)).toBeInTheDocument())
    expect(api.submitReport).toHaveBeenCalledWith({
      channel: 'text',
      rawText: 'The hand pump near Chikkur village school is broken.',
      language: 'en',
      photo: null,
    })
    expect(screen.getByText('Chikkur')).toBeInTheDocument()
  })

  it('shows a friendly message when the village could not be resolved', async () => {
    vi.mocked(api.submitReport).mockResolvedValue(makeResponse({ village_name: null, resolved_village_code: null }))
    render(<ReportIssuePage />)

    fireEvent.change(screen.getByLabelText(/what's the problem/i), { target: { value: 'Streetlights are out at night.' } })
    fireEvent.click(screen.getByRole('button', { name: /send report/i }))

    await waitFor(() => expect(screen.getByText(/couldn't pinpoint a specific village/i)).toBeInTheDocument())
  })

  it('shows a rate-limit-specific message on a 429 response', async () => {
    vi.mocked(api.submitReport).mockRejectedValue({
      isAxiosError: true,
      response: { status: 429, data: {} },
    })
    render(<ReportIssuePage />)

    fireEvent.change(screen.getByLabelText(/what's the problem/i), { target: { value: 'Another report.' } })
    fireEvent.click(screen.getByRole('button', { name: /send report/i }))

    await waitFor(() => expect(screen.getByText(/wait a minute and try again/i)).toBeInTheDocument())
  })

  it('lets the citizen file a second report after a successful submission', async () => {
    vi.mocked(api.submitReport).mockResolvedValue(makeResponse())
    render(<ReportIssuePage />)

    fireEvent.change(screen.getByLabelText(/what's the problem/i), { target: { value: 'First report text.' } })
    fireEvent.click(screen.getByRole('button', { name: /send report/i }))
    await waitFor(() => expect(screen.getByText(/report #101 received/i)).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /report another issue/i }))
    expect(screen.getByLabelText(/what's the problem/i)).toHaveValue('')
  })
})
