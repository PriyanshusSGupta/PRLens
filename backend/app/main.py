from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.api import webhooks, prs, dashboard, evaluations, review, auth, repos, ai
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_engine
import app.models.user
import app.models.user_token
import app.models.user_ai_config
import app.models.otp_code
import app.models.pull_request
import app.models.review_run
import app.models.finding
import app.models.evaluation
import app.models.repository
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        eng = get_engine()
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.warning("Database not available, skipping auto-migration: %s", e)
    yield
    try:
        await eng.dispose()
    except Exception:
        pass


app = FastAPI(title="PRLens", version="0.1.0", lifespan=lifespan)

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(ai.router)
app.include_router(repos.router)
app.include_router(webhooks.router)
app.include_router(prs.router)
app.include_router(dashboard.router)
app.include_router(evaluations.router)
app.include_router(review.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
