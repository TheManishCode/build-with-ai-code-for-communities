export interface SourceQuote {
  submission_id: number
  village: string | null
  original_text: string
  original_language: string
  translated_text: string | null
}

export interface Work {
  work_id: string
  source: 'issue' | 'gap'
  theme: string
  village_code: number | null
  village_name: string | null
  corroboration_count: number
  demand_percentile: number
  gap_percentile: number | null
  population_affected: number | null
  composite_score: number
  reasoning: string
  source_quotes: SourceQuote[]
}

export interface Village {
  village_code: number
  village_name: string
  subdistrict_name: string | null
  gram_panchayat_name: string | null
  total_population: number | null
  literacy_rate: number | null
  has_safe_water_source: boolean | null
  has_all_weather_road: boolean | null
  pmgsy_connected: boolean | null
  census_school_count: number | null
  kys_school_count: number | null
}

export interface DivergenceRow {
  village_code: number
  village_name: string
  gap_percentile: number | null
  voice_percentile: number
  divergence: number | null
  silent_need: boolean
}

export interface BoundaryResponse {
  constituency: { type: 'Feature'; geometry: GeoJSON.Geometry; properties: Record<string, unknown> } | null
  villages: GeoJSON.FeatureCollection
  village_coverage_note: string
}

export interface AllocationResponse {
  budget: number
  is_default_budget: boolean
  total_cost: number
  budget_used_pct: number
  total_value: number
  n_works_selected: number
  n_candidates_considered: number
  cost_heuristic_note: string
  theme_cost_heuristic: Record<string, number>
  selected_works: Array<{
    work_id: string
    source: string
    theme: string
    village_code: number | null
    village_name: string | null
    cost: number
    composite_score: number
    reasoning: string
  }>
}

export interface BacktestCutoff {
  k: number
  true_positives: number
  precision: number
  recall: number
  random_baseline_precision: number
}

export interface BacktestResponse {
  total_villages: number
  ground_truth_villages: number
  cutoffs: BacktestCutoff[]
  never_addressed_high_gap_villages: Array<{
    village_code: number
    village_name: string
    overall_gap_percentile: number
    total_population: number | null
  }>
  caveats: string[]
}

export interface DraftLetterResponse {
  work_id: string
  to: string
  subject: string
  body: string
  generated_at: string
}

export interface ExplanationResponse {
  work_id: string
  is_funded: boolean
  theme?: string
  village_name?: string | null
  composite_score?: number
  demand_percentile?: number
  gap_percentile?: number | null
  cost?: number | null
  cutoff_score?: number
  cutoff_caveat?: string
  compared_against?: Array<{ village_name: string | null; theme: string; composite_score: number; cost: number }>
  mp_explanation?: string
  citizen_message?: string
  generation_source?: 'nvidia' | 'claude' | 'template'
  fallback_reason?: string | null
}

export interface TransparencySummaryResponse {
  total_submissions: number
  total_issues: number
  dedup_rate: number
  theme_breakdown: Record<string, number>
  total_villages: number
  villages_with_submissions: number
  voice_coverage_pct: number
  silent_need_village_count: number
  total_candidate_works: number
  issue_based_works: number
  gap_only_works: number
  budget: number
  works_funded: number
  budget_used_pct: number
  backtest_ground_truth_villages: number
  backtest_precision_at_100: number | null
  backtest_never_addressed_count: number
}

export interface CitizenStatusResponse {
  submission_id: number
  village: string | null
  taluk: string | null
  theme: string | null
  dedup_group_id: number | null
  corroboration_count: number | null
  current_rank: number | null
  total_works_ranked: number | null
  is_funded_this_cycle: boolean | null
  funding_tier: string
  status_message: string
}

export interface Issue {
  id: number
  theme: string
  village_code: number | null
  representative_text: string
  corroboration_count: number
}
