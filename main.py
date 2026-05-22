"""
app/main.py
───────────
FastAPI application entry point.

Run:  uvicorn app.main:app --reload --port 8000
Docs: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.reconciliation import router as recon_router
from app.schemas.response import HealthResponse
from app.utils.logger import get_logger

log = get_logger(__name__)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Reconciliation Engine API",
    description=(
        "Detects gaps between platform transactions and bank settlements.\n\n"
        "**Gap types detected:**\n"
        "- `LATE_SETTLEMENT` — settled in a different calendar month\n"
        "- `ROUNDING_DIFFERENCE` — platform vs bank differ by ≤ ₹0.05\n"
        "- `DUPLICATE_SETTLEMENT` — same txn settled > 1 time\n"
        "- `UNMATCHED_REFUND` — bank refund with no platform txn\n"
        "- `UNSETTLED_TRANSACTION` — platform txn with no bank settlement\n"
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(recon_router)


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get(
    "/",
    response_model=HealthResponse,
    summary="Health check",
    tags=["Health"],
)
def health():
    return {"status": "ok", "service": "Reconciliation Engine", "version": "2.0.0"}


# ── Startup log ────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    log.info("Reconciliation Engine v2.0.0 started — docs at /docs")