from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.allocation import router as allocation_router
from app.api.backtest import router as backtest_router
from app.api.boundary import router as boundary_router
from app.api.chat import router as chat_router
from app.api.citizen import router as citizen_router
from app.api.divergence import router as divergence_router
from app.api.issues import router as issues_router
from app.api.submissions import UPLOAD_DIR, UPLOAD_DIR_AVAILABLE
from app.api.submissions import router as submissions_router
from app.api.transparency import router as transparency_router
from app.api.villages import router as villages_router
from app.api.works import router as works_router
from app.core.config import settings
from app.core.rate_limit import limiter

# Defense-in-depth ahead of our own per-field size checks (app/api/submissions.py) -- a
# client could otherwise send an oversized body that gets read into memory before those
# checks ever run. 12MB gives headroom above the 8MB photo limit + 2000-char text + normal
# multipart framing overhead.
MAX_REQUEST_BODY_BYTES = 12 * 1024 * 1024


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > MAX_REQUEST_BODY_BYTES:
            return JSONResponse(status_code=413, content={"detail": "Request body too large."})
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app = FastAPI(title="People's Priorities API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MaxBodySizeMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # POST is used by /submissions (citizen intake) and /chat (the assistant) -- every
    # other route in app/api/*.py is a @router.get.
    allow_methods=["GET", "POST", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

if UPLOAD_DIR_AVAILABLE:
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
app.include_router(chat_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "constituency": settings.constituency_name}
