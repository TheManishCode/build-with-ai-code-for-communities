# People's Priorities

An AI-assisted constituency development-planning platform, built for Bagalkot
(Karnataka). It turns scattered citizen development requests and public government
datasets into a single ranked, explainable list of high-priority development works an
MP's office can act on.

MPs receive development requests through many channels, while local development plans
contain dozens of competing proposals, with no objective way to consolidate feedback,
spot recurring needs, or weigh requests against real demographic and infrastructure
data. This project builds that missing layer: citizen reports are deduplicated into
issues, cross-referenced against real village-level demographic and infrastructure-gap
data, scored, ranked, and run through a budget allocator against the MP's actual
MPLADS limit — with every generated explanation checked against the underlying data
before it ships.

## What's built, and what isn't

The **analysis and recommendation pipeline is complete and real**: theme
classification, deduplication, demand/gap scoring, ranking, budget allocation, draft
letter generation, a rejection explainer, and backtesting against historical MPLADS
spending — all running against real Bagalkot data (Census 2011, LGD, PMGSY, MPLADS,
village amenities).

**Citizen intake is not live.** The data model anticipates voice/text/photo
submissions (see `Submission.channel`), but there is no submission endpoint, no
speech-to-text or image pipeline, and no messaging-app integration. All ~60
submissions in the system come from `backend/app/ingestion/seed_submissions.py`, a
synthetic generator standing in for real intake so the rest of the pipeline has data
to run against. Building a real intake channel is the natural next step.

## Architecture

```
Dataset/                    Real public datasets (Census, LGD, PMGSY, MPLADS, ...)
source code/
  backend/                  FastAPI + PostgreSQL/PostGIS
    app/
      models/               SQLAlchemy models (submissions, issues, LGD, village facts)
      ingestion/             One script per dataset -- parses raw files, resolves to
                             LGD village codes, writes to Postgres
      services/             Ranking, gap analysis, deduplication, budget allocation,
                             the rejection explainer, transparency summary
      api/                  FastAPI routers, one per resource
    alembic/                Schema migrations
    tests/                  56 tests against the live database (see Testing, below)
  frontend/                 React + Vite + TanStack Query + Tailwind + Leaflet
```

Citizen submissions are deduplicated into **issues** (same village + theme), scored on
two independent signals normalized to a constituency-wide percentile — **demand**
(citizen voice: corroboration count, recency-weighted) and **gap** (objective
infrastructure shortfall vs. the constituency, from Census/amenities data) — then
combined into a composite score. Villages with a high gap but no citizen reports still
surface as "silent need" candidates. A knapsack allocator selects the highest-value
combination of works that fits the MP's real MPLADS budget.

## Setup

**Prerequisites:** Python 3.11+, Node 20+, PostgreSQL 16+ with the PostGIS extension.

### 1. Database

```sql
CREATE DATABASE peoples_priorities;
\c peoples_priorities
CREATE EXTENSION postgis;
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

Create `backend/.env`:

```ini
DATABASE_URL=postgresql+psycopg://<user>:<password>@localhost:5432/peoples_priorities
DATASET_DIR=../../Dataset      # path to the Dataset/ folder described above
CONSTITUENCY_NAME=BAGALKOT
CONSTITUENCY_DISTRICT=Bagalkot

# Optional -- powers the rejection explainer's generated text (services/explain.py).
# Without either key, it falls back to a deterministic template automatically.
NVIDIA_NIM_API_KEY=
ANTHROPIC_API_KEY=
```

Run migrations, then ingest the datasets in order (each script fuzzy-matches its
source data to LGD village codes, so later scripts depend on earlier ones):

```bash
alembic upgrade head

python -m app.ingestion.lgd                    # district/subdistrict/village backbone
python -m app.ingestion.boundary               # parliamentary constituency shapefile
python -m app.ingestion.census_pca             # Census 2011 demographics
python -m app.ingestion.census_village_amenities
python -m app.ingestion.know_your_school
python -m app.ingestion.mplads                 # historical MPLADS allocations
python -m app.ingestion.pmgsy                  # rural road connectivity
python -m app.ingestion.build_village_fact     # aggregates the above into one fact table

python -m app.ingestion.seed_submissions       # synthetic citizen reports (see above)
python -m app.ingestion.build_issues           # deduplicates submissions into issues
```

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```ini
VITE_API_BASE=http://localhost:8000
```

```bash
npm run dev      # http://localhost:5173
```

## API reference

| Endpoint | Purpose |
|---|---|
| `GET /villages` | Village-level facts (demographics, infrastructure gaps) |
| `GET /issues` | Deduplicated citizen issues |
| `GET /works` | Ranked candidate development works, with source quotes |
| `GET /works/{id}/letter` | Draft letter to the relevant department for a work |
| `GET /works/{id}/explain` | Why a work was or wasn't funded, grounded in real scores |
| `GET /divergence` | Villages where need and citizen voice diverge ("silent need") |
| `GET /backtest` | Ranking precision/recall vs. historical MPLADS spending |
| `GET /allocation` | The budget allocator's result for a given MPLADS limit |
| `GET /boundary` | The constituency's parliamentary boundary (GeoJSON) |
| `GET /citizen/status` | A citizen's own report: dedup group, rank, funding status |
| `GET /transparency/summary` | A public rollup of the constituency's overall numbers |

Full interactive docs at `http://localhost:8000/docs` once the backend is running.

## Testing

```bash
# backend -- 56 tests against the live database (no mock DB; this is a deliberate
# choice for a dataset-driven project where the interesting bugs are in the data,
# not the plumbing)
cd backend && python -m pytest tests/

# lint
python -m ruff check app/ tests/

# frontend
cd frontend && npm test         # vitest
npm run lint                    # oxlint
npm run build                   # tsc + vite build
```

## Known limitations

- **No live citizen intake** (see above) — the single largest gap versus a full
  end-to-end deployment.
- **No authentication anywhere.** `GET /citizen/status` takes a plain sequential
  integer ID with no access control; the correct fix is an opaque per-submission
  token issued at intake time, which doesn't exist without a real intake endpoint.
- **No caching layer.** Every request recomputes the ranking from Postgres; fine at
  Bagalkot's current data volume, worth revisiting before scaling to more
  constituencies or a much larger submission volume.
- **Cost estimates are planning-grade, not engineering estimates** — `theme_cost_heuristic`
  in `backend/config/ranking_weights.yaml` is a flat per-theme figure used because no
  real per-work cost model exists yet.
