# Backend

FastAPI + SQLAlchemy + PostgreSQL/PostGIS. See the [project README](../README.md) for
full setup, the ingestion pipeline order, and the API reference.

Quick reference:

```bash
uvicorn app.main:app --reload --port 8000   # run
python -m pytest tests/                     # test (56 tests, live DB)
python -m ruff check app/ tests/            # lint
alembic revision --autogenerate -m "..."    # new migration
alembic upgrade head                        # apply migrations
```

`app/ingestion/` scripts are each independently runnable via `python -m
app.ingestion.<name>`. The real-dataset scripts (`lgd`, `census_pca`,
`census_village_amenities`, `know_your_school`, `mplads`, `pmgsy`, `boundary`,
`build_village_fact`) upsert on a natural key and are safe to re-run. `seed_submissions`
and `build_issues` are not — they generate/cluster data rather than ingesting a fixed
source, so re-running them on a non-empty database will create duplicates; only run
them once against a fresh database.
