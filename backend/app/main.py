from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.backtest import router as backtest_router
from app.api.divergence import router as divergence_router
from app.api.issues import router as issues_router
from app.api.villages import router as villages_router
from app.api.works import router as works_router
from app.core.config import settings

app = FastAPI(title="People's Priorities API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(villages_router)
app.include_router(issues_router)
app.include_router(works_router)
app.include_router(divergence_router)
app.include_router(backtest_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "constituency": settings.constituency_name}
