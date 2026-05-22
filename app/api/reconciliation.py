"""
api/reconciliation.py
─────────────────────
All reconciliation & data endpoints.

GET  /api/summary              → full summary with totals & gap counts
GET  /api/gaps                 → all detected gaps
GET  /api/gaps/{gap_type}      → gaps filtered by type
GET  /api/transactions         → raw platform transactions
GET  /api/settlements          → raw bank settlements
POST /api/upload               → upload custom CSVs
DELETE /api/upload             → reset to default data
"""

import io
from typing import Callable, TypeVar

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.services.reconciliation_service import DataLoadError, run_reconciliation, load_data
from app.services.upload_service import store_uploads, reset_uploads
from app.services.validation_service import ValidationError
from app.schemas.response import (
    SummaryResponse,
    GapListResponse,
    GapTypeResponse,
    GapItem,
    UploadResponse,
    ResetResponse,
)
from app.utils.constants import ALL_GAP_TYPES
from app.utils.logger import get_logger

log = get_logger(__name__)
router = APIRouter()
ResponseT = TypeVar("ResponseT")


def _handle_data_errors(operation: Callable[[], ResponseT]) -> ResponseT:
    try:
        return operation()
    except DataLoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# ── Summary ────────────────────────────────────────────────────────────────────

@router.get(
    "/api/summary",
    response_model=SummaryResponse,
    summary="Full reconciliation summary",
    tags=["Reconciliation"],
)
def get_summary():
    """
    Returns aggregate totals, net difference, and gap counts broken down
    by type and severity.
    """
    return _handle_data_errors(lambda: run_reconciliation()[0])


# ── All Gaps ───────────────────────────────────────────────────────────────────

@router.get(
    "/api/gaps",
    response_model=GapListResponse,
    summary="All detected gaps",
    tags=["Reconciliation"],
)
def get_all_gaps():
    """Returns every gap found, with full detail for each."""
    gaps = _handle_data_errors(lambda: run_reconciliation()[1])
    return {"total": len(gaps), "gaps": gaps}


# ── Gaps by Type ───────────────────────────────────────────────────────────────

@router.get(
    "/api/gaps/{gap_type}",
    response_model=GapTypeResponse,
    summary="Gaps filtered by type",
    tags=["Reconciliation"],
)
def get_gaps_by_type(gap_type: str):
    """
    Filter gaps by type.

    Valid values: `LATE_SETTLEMENT` · `ROUNDING_DIFFERENCE` ·
    `DUPLICATE_SETTLEMENT` · `UNMATCHED_REFUND` · `UNSETTLED_TRANSACTION`
    """
    gap_type_upper = gap_type.upper()
    if gap_type_upper not in ALL_GAP_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown gap_type '{gap_type}'. Valid: {sorted(ALL_GAP_TYPES)}",
        )
    gaps = _handle_data_errors(lambda: run_reconciliation()[1])
    filtered = [g for g in gaps if g["gap_type"] == gap_type_upper]
    return {"gap_type": gap_type_upper, "total": len(filtered), "gaps": filtered}


# ── Raw Data ───────────────────────────────────────────────────────────────────

@router.get(
    "/api/transactions",
    summary="Raw platform transactions",
    tags=["Data"],
)
def get_transactions():
    """Returns all platform transaction records as a list of objects."""
    txn, _ = _handle_data_errors(load_data)
    return txn.to_dict(orient="records")


@router.get(
    "/api/settlements",
    summary="Raw bank settlements",
    tags=["Data"],
)
def get_settlements():
    """Returns all bank settlement records as a list of objects."""
    _, stl = _handle_data_errors(load_data)
    return stl.to_dict(orient="records")


# ── Upload ─────────────────────────────────────────────────────────────────────

@router.post(
    "/api/upload",
    response_model=UploadResponse,
    summary="Upload custom CSVs",
    tags=["Data"],
)
async def upload_data(
    transactions: UploadFile = File(..., description="Platform transactions CSV"),
    settlements:  UploadFile = File(..., description="Bank settlements CSV"),
):
    """
    Upload custom transaction and settlement CSVs to override the default
    generated dataset.  Both files are validated before being accepted.
    """
    try:
        txn_count, stl_count = await store_uploads(transactions, settlements)
        return {"status": "uploaded", "transactions": txn_count, "settlements": stl_count}
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.exception("Upload failed")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/api/upload",
    response_model=ResetResponse,
    summary="Reset to default data",
    tags=["Data"],
)
def reset_data():
    """Clears any uploaded CSVs and reverts to the default generated dataset."""
    reset_uploads()
    return {"status": "reset to default data"}