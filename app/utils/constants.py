import os

# ── File Paths ────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR   = os.path.join(BASE_DIR, "data")
TXN_PATH   = os.path.join(DATA_DIR, "platform_transactions.csv")
STL_PATH   = os.path.join(DATA_DIR, "bank_settlements.csv")

# ── Gap Types ─────────────────────────────────────────────────────────────────
GAP_LATE_SETTLEMENT       = "LATE_SETTLEMENT"
GAP_ROUNDING_DIFFERENCE   = "ROUNDING_DIFFERENCE"
GAP_DUPLICATE_SETTLEMENT  = "DUPLICATE_SETTLEMENT"
GAP_UNMATCHED_REFUND      = "UNMATCHED_REFUND"
GAP_UNSETTLED_TRANSACTION = "UNSETTLED_TRANSACTION"

ALL_GAP_TYPES = {
    GAP_LATE_SETTLEMENT,
    GAP_ROUNDING_DIFFERENCE,
    GAP_DUPLICATE_SETTLEMENT,
    GAP_UNMATCHED_REFUND,
    GAP_UNSETTLED_TRANSACTION,
}

# ── Severity Levels ───────────────────────────────────────────────────────────
SEV_CRITICAL = "CRITICAL"
SEV_HIGH     = "HIGH"
SEV_LOW      = "LOW"

# ── Thresholds ────────────────────────────────────────────────────────────────
ROUNDING_THRESHOLD = 0.05          # diff ≤ 0.05 → rounding gap
SETTLEMENT_LAG_DAYS = 2            # normal settlement lag (informational)

# ── Gap Metadata: human-readable labels for each gap type ────────────────────
GAP_META = {
    GAP_LATE_SETTLEMENT: {
        "label":       "Cross-Month Settlement",
        "description": "Transaction settled in a different calendar month",
        "severity":    SEV_HIGH,
    },
    GAP_ROUNDING_DIFFERENCE: {
        "label":       "Rounding Difference",
        "description": "Platform vs bank amount mismatch ≤ ₹0.05",
        "severity":    SEV_LOW,
    },
    GAP_DUPLICATE_SETTLEMENT: {
        "label":       "Duplicate Settlement",
        "description": "Same transaction settled more than once by bank",
        "severity":    SEV_CRITICAL,
    },
    GAP_UNMATCHED_REFUND: {
        "label":       "Unmatched Refund",
        "description": "Bank refund with no matching platform transaction",
        "severity":    SEV_CRITICAL,
    },
    GAP_UNSETTLED_TRANSACTION: {
        "label":       "Unsettled Transaction",
        "description": "Platform transaction with no bank settlement",
        "severity":    SEV_HIGH,
    },
}