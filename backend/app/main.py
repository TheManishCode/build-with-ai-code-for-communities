from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.villages import router as villages_router
from app.core.config import settings

app = FastAPI(title="People's Priorities API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(villages_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "constituency": settings.constituency_name}
