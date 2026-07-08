from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.allocation import router as allocation_router
from app.api.backtest import router as backtest_router
from app.api.boundary import router as boundary_router
from app.api.citizen import router as citizen_router
from app.api.divergence import router as divergence_router
from app.api.issues import router as issues_router
from app.api.submissions import UPLOAD_DIR
from app.api.submissions import router as submissions_router
from app.api.transparency import router as transparency_router
from app.api.villages import router as villages_router
from app.api.works import router as works_router
from app.core.config import settings

app = FastAPI(title="People's Priorities API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # POST is scoped to /submissions alone in practice (every other route in app/api/*.py
    # is a @router.get) -- the sole live citizen-intake write path.
    allow_methods=["GET", "POST", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(villages_router)
app.include_router(issues_router)
app.include_router(works_router)
app.include_router(divergence_router)
app.include_router(backtest_router)
app.include_router(allocation_router)
app.include_router(boundary_router)
app.include_router(citizen_router)
app.include_router(transparency_router)
app.include_router(submissions_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "constituency": settings.constituency_name}
