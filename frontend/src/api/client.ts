import axios from 'axios'
import type {
  AllocationResponse,
  BacktestResponse,
  BoundaryResponse,
  CitizenStatusResponse,
  DivergenceRow,
  DraftLetterResponse,
  ExplanationResponse,
  Issue,
  SubmissionChannel,
  SubmissionResponse,
  TransparencySummaryResponse,
  Village,
  Work,
} from './types'

export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

const client = axios.create({ baseURL: API_BASE })

export const api = {
  works: (limit = 20) => client.get<Work[]>('/works', { params: { limit } }).then((r) => r.data),
  villages: () => client.get<Village[]>('/villages').then((r) => r.data),
  issues: () => client.get<Issue[]>('/issues').then((r) => r.data),
  divergence: () => client.get<DivergenceRow[]>('/divergence').then((r) => r.data),
  boundary: () => client.get<BoundaryResponse>('/boundary').then((r) => r.data),
  allocation: (budget?: number) =>
    client.get<AllocationResponse>('/allocation', { params: budget != null ? { budget } : {} }).then((r) => r.data),
  backtest: () => client.get<BacktestResponse>('/backtest').then((r) => r.data),
  draftLetter: (workId: string) => client.get<DraftLetterResponse>(`/works/${encodeURIComponent(workId)}/letter`).then((r) => r.data),
  explain: (workId: string, budget?: number) =>
    client
      .get<ExplanationResponse>(`/works/${encodeURIComponent(workId)}/explain`, { params: budget != null ? { budget } : {} })
      .then((r) => r.data),
  citizenStatus: (submissionId: number) =>
    client.get<CitizenStatusResponse>('/citizen/status', { params: { submission_id: submissionId } }).then((r) => r.data),
  transparencySummary: () => client.get<TransparencySummaryResponse>('/transparency/summary').then((r) => r.data),
  submitReport: (report: { channel: SubmissionChannel; rawText: string; language: string; photo?: File | null }) => {
    const form = new FormData()
    form.append('channel', report.channel)
    form.append('raw_text', report.rawText)
    form.append('language', report.language)
    if (report.photo) form.append('photo', report.photo)
    return client.post<SubmissionResponse>('/submissions', form).then((r) => r.data)
  },
}
