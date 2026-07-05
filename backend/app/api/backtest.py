from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.backtest import run_backtest

router = APIRouter(prefix="/backtest", tags=["backtest"])

CAVEATS = [
    "Ground truth is 17th Lok Sabha MPLADs works with completed_amount set, fuzzy-matched "
    "to an LGD village (~87% match rate) -- unmatched works are excluded, not counted as misses.",
    "Prediction uses ONLY the objective infrastructure-gap signal (village_fact), not citizen "
    "demand -- synthetic submissions have no real temporal relationship to 2019-2024 and "
    "including them would be a temporal-leakage bug, not a real validation.",
    "There is no true 'as of 2019' infrastructure snapshot available in this dataset -- "
    "census (2011) predates the 17th LS term, but PMGSY road/connectivity data reflects a "
    "more recent state and could in principle already reflect works the 17th LS itself "
    "funded. This is a real limitation of the available data, disclosed rather than hidden.",
]


@router.get("")
def get_backtest(db: Session = Depends(get_db)) -> dict:
    result = run_backtest(db)
    return {
        "total_villages": result.total_villages,
        "ground_truth_villages": result.ground_truth_villages,
        "cutoffs": [
            {
                "k": c.k,
                "true_positives": c.true_positives,
                "precision": round(c.precision, 4),
                "recall": round(c.recall, 4),
                "random_baseline_precision": round(c.random_baseline_precision, 4),
            }
            for c in result.cutoffs
        ],
        "never_addressed_high_gap_villages": result.never_addressed,
        "caveats": CAVEATS,
    }
