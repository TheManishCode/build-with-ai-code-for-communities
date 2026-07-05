"""MPLADs backtest validation.

Question: if the ranking model's OBJECTIVE GAP signal (not citizen demand -- see caveat
below) had been used to prioritize villages, would it have surfaced the villages where
17th Lok Sabha MPLADs money actually went, or flagged unmet gaps that were never
addressed?

METHODOLOGY AND CAVEATS (disclosed, not hidden):
  - Ground truth: villages with at least one COMPLETED 17th-LS MPLADs work (fuzzy-matched
    village linkage from app.ingestion.mplads, ~87% match rate -- the ~13% of works that
    couldn't be linked to a village are excluded from ground truth, not counted as misses).
  - Prediction: village overall_gap_percentile from app.services.gap, using ONLY the
    objective infrastructure signal -- the demand/citizen-submission signal is
    intentionally EXCLUDED from this backtest, because our synthetic submissions have no
    real temporal relationship to 2019-2024 (the 17th LS term) and including them would be
    a temporal-leakage bug dressed up as a validation.
  - We do NOT have a true "as of 2019" infrastructure snapshot -- the census (2011) predates
    the 17th LS term, which is good, but PMGSY connectivity/road data reflects a more recent
    state and could in principle already reflect works funded BY the 17th LS itself (a
    circularity risk). This is disclosed as a real limitation of the available data, not
    swept under the rug -- the backtest is a genuine, if imperfect, validation signal, not
    a certified causal claim.
  - Precision/recall are reported at multiple top-K cutoffs, alongside the random-chance
    baseline (K/627 villages would be expected to overlap ground truth by chance), so the
    reader can judge whether the model beats chance -- not just report a bare number.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.ranking_config import RankingConfig, ranking_config
from app.services.gap import compute_village_gaps

TOP_K_CUTOFFS = (10, 25, 50, 100, 157)  # 157 ~= top quartile of 627 villages


@dataclass
class BacktestCutoffResult:
    k: int
    predicted_villages: int
    true_positives: int
    precision: float
    recall: float
    random_baseline_precision: float


@dataclass
class BacktestResult:
    total_villages: int
    ground_truth_villages: int
    cutoffs: list[BacktestCutoffResult]
    never_addressed: list[dict]  # high-gap villages with ZERO completed MPLADs work, either term


def _ground_truth_villages(db: Session, lok_sabha_term: str) -> set[int]:
    rows = db.execute(
        text(
            """
            SELECT DISTINCT matched_lgd_village_code
            FROM mplads_work
            WHERE lok_sabha_term = :term
              AND completed_amount IS NOT NULL
              AND matched_lgd_village_code IS NOT NULL
            """
        ),
        {"term": lok_sabha_term},
    ).all()
    return {r.matched_lgd_village_code for r in rows}


def _any_term_funded_villages(db: Session) -> set[int]:
    rows = db.execute(
        text(
            """
            SELECT DISTINCT matched_lgd_village_code
            FROM mplads_work
            WHERE completed_amount IS NOT NULL AND matched_lgd_village_code IS NOT NULL
            """
        )
    ).all()
    return {r.matched_lgd_village_code for r in rows}


def run_backtest(db: Session, config: RankingConfig = ranking_config, lok_sabha_term: str = "17th") -> BacktestResult:
    gaps = compute_village_gaps(db, config.gap_sub_weights)
    ranked = sorted(
        (g for g in gaps.values() if g.overall_gap_percentile is not None),
        key=lambda g: g.overall_gap_percentile,
        reverse=True,
    )
    total_villages = len(gaps)

    ground_truth = _ground_truth_villages(db, lok_sabha_term)
    n_truth = len(ground_truth)

    cutoffs = []
    for k in TOP_K_CUTOFFS:
        if k > len(ranked):
            continue
        predicted = {g.village_code for g in ranked[:k]}
        tp = len(predicted & ground_truth)
        precision = tp / k if k else 0.0
        recall = tp / n_truth if n_truth else 0.0
        random_baseline = n_truth / total_villages if total_villages else 0.0
        cutoffs.append(
            BacktestCutoffResult(
                k=k, predicted_villages=k, true_positives=tp,
                precision=precision, recall=recall, random_baseline_precision=random_baseline,
            )
        )

    funded_any_term = _any_term_funded_villages(db)
    never_addressed = []
    for g in ranked:
        if g.overall_gap_percentile is None or g.overall_gap_percentile < config.silent_need_gap_percentile:
            continue
        if g.village_code in funded_any_term:
            continue
        if not g.total_population:
            # Data artifact guard -- see app/services/ranking.py's matching comment:
            # a handful of villages show population==0 despite being LGD "Inhabitant",
            # likely a hamlet/main-village census split, not a genuinely empty settlement.
            continue
        never_addressed.append(
            {
                "village_code": g.village_code,
                "village_name": g.village_name,
                "overall_gap_percentile": g.overall_gap_percentile,
                "total_population": g.total_population,
            }
        )

    return BacktestResult(
        total_villages=total_villages,
        ground_truth_villages=n_truth,
        cutoffs=cutoffs,
        never_addressed=never_addressed,
    )
