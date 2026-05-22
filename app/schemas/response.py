from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

# ── Individual Gap ─────────────────────────────────────────────────────────────
class GapItem(BaseModel):
    gap_type:        str
    transaction_id:  str
    description:     str
    severity:        str
    platform_amount: Optional[float] = None
    bank_amount:     Optional[float] = None
    difference:      Optional[float] = None
    overcharge:      Optional[float] = None
    settlement_count: Optional[int]  = None
    total_settled:   Optional[float] = None
    expected_amount: Optional[float] = None
    txn_date:        Optional[str]   = None
    settled_date:    Optional[str]   = None

# ── Gap list response ──────────────────────────────────────────────────────────
class GapListResponse(BaseModel):
    total: int
    gaps:  List[GapItem]

# ── Filtered by type ───────────────────────────────────────────────────────────
class GapTypeResponse(BaseModel):
    gap_type: str
    total:    int
    gaps:     List[GapItem]

# ── Summary ────────────────────────────────────────────────────────────────────
class GapsByType(BaseModel):
    LATE_SETTLEMENT:       int = 0
    ROUNDING_DIFFERENCE:   int = 0
    DUPLICATE_SETTLEMENT:  int = 0
    UNMATCHED_REFUND:      int = 0
    UNSETTLED_TRANSACTION: int = 0

class GapsBySeverity(BaseModel):
    CRITICAL: int = 0
    HIGH:     int = 0
    LOW:      int = 0

class SummaryResponse(BaseModel):
    total_transactions:   int
    total_settlements:    int
    platform_total_inr:   float
    bank_total_inr:       float
    net_difference_inr:   float
    total_gaps_found:     int
    gaps_by_type:         GapsByType
    gaps_by_severity:     GapsBySeverity

# ── Upload / Reset ─────────────────────────────────────────────────────────────
class UploadResponse(BaseModel):
    status:       str
    transactions: int
    settlements:  int

class ResetResponse(BaseModel):
    status: str

# ── Health ─────────────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status:  str
    service: str
    version: str