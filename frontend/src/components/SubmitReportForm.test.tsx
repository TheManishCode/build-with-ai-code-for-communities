import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactElement } from 'react'
import { SubmitReportForm } from './SubmitReportForm'
import { api } from '../api/client'
import type { SubmissionResponse } from '../api/types'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    api: { ...actual.api, submitReport: vi.fn() },
  }
})

function renderWithClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

const mockResponse: SubmissionResponse = {
  submission_id: 101,
  channel: 'text',
  language: 'en',
  translated_text: 'No water in the village.',
  theme: 'water',
  resolved_village_code: 12345,
  village_name: 'Kaladgi',
  place_match_score: 100,
  photo_url: null,
  issue_id: 7,
  created_at: '2026-07-08T00:00:00Z',
}

describe('SubmitReportForm', () => {
  beforeEach(() => {
    vi.mocked(api.submitReport).mockReset()
  })

  it('disables submit until report text is entered', () => {
    renderWithClient(<SubmitReportForm onViewStatus={vi.fn()} />)
    expect(screen.getByRole('button', { name: /submit report/i })).toBeDisabled()
    fireEvent.change(screen.getByLabelText(/describe the problem/i), { target: { value: 'No water for 3 days.' } })
    expect(screen.getByRole('button', { name: /submit report/i })).not.toBeDisabled()
  })

  it('submits the typed report with the selected language and shows a confirmation', async () => {
    vi.mocked(api.submitReport).mockResolvedValue(mockResponse)
    renderWithClient(<SubmitReportForm onViewStatus={vi.fn()} />)

    fireEvent.change(screen.getByLabelText(/describe the problem/i), { target: { value: 'No water for 3 days.' } })
    fireEvent.click(screen.getByRole('button', { name: /submit report/i }))

    await waitFor(() => expect(screen.getByText('Report received')).toBeInTheDocument())
    expect(api.submitReport).toHaveBeenCalledWith({
      channel: 'text',
      rawText: 'No water for 3 days.',
      language: 'en',
      photo: null,
    })
    expect(screen.getByText('#101')).toBeInTheDocument()
    expect(screen.getByText('Kaladgi')).toBeInTheDocument()
  })

  it('calls onViewStatus with the new submission id when "Check my report status" is clicked', async () => {
    vi.mocked(api.submitReport).mockResolvedValue(mockResponse)
    const onViewStatus = vi.fn()
    renderWithClient(<SubmitReportForm onViewStatus={onViewStatus} />)

    fireEvent.change(screen.getByLabelText(/describe the problem/i), { target: { value: 'No water for 3 days.' } })
    fireEvent.click(screen.getByRole('button', { name: /submit report/i }))
    await waitFor(() => expect(screen.getByText('Report received')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /check my report status/i }))
    expect(onViewStatus).toHaveBeenCalledWith(101)
  })

  it('shows the server-provided error message on failure', async () => {
    vi.mocked(api.submitReport).mockRejectedValue({
      isAxiosError: true,
      response: { data: { detail: 'raw_text must be at most 2000 characters' } },
    })
    renderWithClient(<SubmitReportForm onViewStatus={vi.fn()} />)

    fireEvent.change(screen.getByLabelText(/describe the problem/i), { target: { value: 'x'.repeat(50) } })
    fireEvent.click(screen.getByRole('button', { name: /submit report/i }))

    await waitFor(() => expect(screen.getByText('raw_text must be at most 2000 characters')).toBeInTheDocument())
  })

  it('switches to photo mode and shows a caption label', () => {
    renderWithClient(<SubmitReportForm onViewStatus={vi.fn()} />)
    fireEvent.click(screen.getByRole('radio', { name: 'Photo' }))
    expect(screen.getByLabelText(/caption/i)).toBeInTheDocument()
  })
})
