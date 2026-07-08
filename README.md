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

**Citizen intake is live.** `POST /submissions` (`backend/app/api/submissions.py`)
accepts a real report — text, or voice transcribed to text client-side via the
browser's Web Speech API, or a photo with a caption — runs it through the same NLP
pipeline used to seed demo data (translate → classify theme → extract and fuzzy-match
the place name to an LGD village → geocode → embed), stores it, and rebuilds issue
clusters synchronously so the new report is reflected in the ranking immediately. The
frontend's "Report an Issue" tab (`frontend/src/components/SubmitReportForm.tsx`) is
the citizen-facing form; the 58 seeded submissions from
`backend/app/ingestion/seed_submissions.py` still provide baseline demo volume
alongside whatever comes in live. **Not built**: a WhatsApp/Telegram/SMS gateway (the
API is channel-agnostic and could sit behind one, but no bot integration exists), and
photo submissions are stored and displayed as evidence rather than analyzed by a
vision model.

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
    tests/                  64 tests against the live database (see Testing, below)
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

Generated files are intentionally kept out of version control: Python virtualenvs and
bytecode, pytest and lint caches, Node dependencies, frontend build output, local
`.env` files, and editor state.

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
| `POST /submissions` | Live citizen intake -- text, browser-transcribed voice, or a photo + caption |
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
# backend -- 64 tests against the live database (no mock DB; this is a deliberate
# choice for a dataset-driven project where the interesting bugs are in the data,
# not the plumbing). Tests that POST to /submissions clean up the rows they create
# (and rebuild issue clusters) so the shared seed dataset stays pristine.
cd backend && python -m pytest tests/

# lint
python -m ruff check app/ tests/

# frontend
cd frontend && npm test         # vitest
npm run lint                    # oxlint
npm run build                   # tsc + vite build
```

## Known limitations

- **No messaging-app gateway.** Citizens can report via the web form (text, browser
  speech-to-text, or photo+caption), but there is no WhatsApp/Telegram/SMS bot -- the
  API is channel-agnostic and could sit behind one, but that integration doesn't exist.
- **Photos are stored as evidence, not analyzed.** A submitted photo is saved and
  displayed alongside the report; there is no vision model extracting information from
  the image itself (e.g. reading a meter, assessing road damage severity).
- **No authentication anywhere.** `POST /submissions` is unauthenticated and rate-limit-
  free (anyone can submit; fine for a demo, not for a public deployment), and
  `GET /citizen/status` takes a plain sequential integer ID with no access control --
  the correct fix is an opaque per-submission token issued at intake time.
- **Issue re-clustering on every submission is a full rebuild**, not an incremental
  update (`app.services.intake` calls `app.ingestion.build_issues.run()`). Cheap at
  Bagalkot's current data volume since embeddings are precomputed and stored -- no
  model calls happen during the rebuild -- but it's O(total submissions) per new
  report, worth revisiting before a much larger submission volume.
- **No caching layer.** Every request recomputes the ranking from Postgres; fine at
  Bagalkot's current data volume, worth revisiting before scaling to more
  constituencies or a much larger submission volume.
- **Cost estimates are planning-grade, not engineering estimates** — `theme_cost_heuristic`
  in `backend/config/ranking_weights.yaml` is a flat per-theme figure used because no
  real per-work cost model exists yet.
