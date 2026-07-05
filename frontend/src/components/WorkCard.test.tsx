import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { WorkCard } from './WorkCard'
import type { Work } from '../api/types'

function makeWork(overrides: Partial<Work> = {}): Work {
  return {
    work_id: 'issue-1',
    source: 'issue',
    theme: 'water',
    village_code: 598748,
    village_name: 'Adagal',
    corroboration_count: 3,
    demand_percentile: 0.81,
    gap_percentile: 0.62,
    population_affected: 4138,
    composite_score: 0.715,
    reasoning: '3 submission(s) about water in Adagal (recency-weighted demand percentile 81%).',
    source_quotes: [
      {
        submission_id: 12,
        village: 'Adagal',
        original_text: 'No drinking water for 3 days.',
        original_language: 'en',
        translated_text: 'No drinking water for 3 days.',
      },
    ],
    ...overrides,
  }
}

describe('WorkCard', () => {
  it('renders theme, village, score, and reasoning text', () => {
    render(<WorkCard work={makeWork()} onDraftLetter={vi.fn()} />)
    expect(screen.getByText('water')).toBeInTheDocument()
    expect(screen.getByText('Adagal')).toBeInTheDocument()
    expect(screen.getByText('72')).toBeInTheDocument() // Math.round(0.715 * 100)
    expect(screen.getByText(/3 submission\(s\) about water/)).toBeInTheDocument()
  })

  it('shows a "silent need" badge only for gap-sourced works', () => {
    const { rerender } = render(<WorkCard work={makeWork({ source: 'gap' })} onDraftLetter={vi.fn()} />)
    expect(screen.getByText('silent need')).toBeInTheDocument()

    rerender(<WorkCard work={makeWork({ source: 'issue' })} onDraftLetter={vi.fn()} />)
    expect(screen.queryByText('silent need')).not.toBeInTheDocument()
  })

  it('calls onDraftLetter with the work_id when the button is clicked', () => {
    const onDraftLetter = vi.fn()
    render(<WorkCard work={makeWork({ work_id: 'issue-42' })} onDraftLetter={onDraftLetter} />)
    fireEvent.click(screen.getByRole('button', { name: /generate draft letter/i }))
    expect(onDraftLetter).toHaveBeenCalledWith('issue-42')
  })

  it('does not render the "In their words" toggle when there are no source quotes', () => {
    render(<WorkCard work={makeWork({ source_quotes: [] })} onDraftLetter={vi.fn()} />)
    expect(screen.queryByText(/in their words/i)).not.toBeInTheDocument()
  })

  it('expands to show the original quote text when "In their words" is clicked', () => {
    render(<WorkCard work={makeWork()} onDraftLetter={vi.fn()} />)
    expect(screen.queryByText(/No drinking water for 3 days/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /in their words/i }))
    expect(screen.getByText(/No drinking water for 3 days/)).toBeInTheDocument()
  })
})
