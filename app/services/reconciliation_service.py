"""
reconciliation_service.py
─────────────────────────
Core reconciliation engine.  Detects five gap types:

  GAP-1  LATE_SETTLEMENT       – transaction & settlement in different months
  GAP-2  ROUNDING_DIFFERENCE   – |platform − bank| ≤ 0.05
  GAP-3  DUPLICATE_SETTLEMENT  – same reference_id appears > 1 time in bank
  GAP-4  UNMATCHED_REFUND      – negative bank entry with no platform txn
  GAP-5  UNSETTLED_TRANSACTION – platform txn has zero bank settlements

Assumptions
-----------
* "Late" means the calendar month of settled_date ≠ calendar month of txn_date.
  A 2-day lag that stays inside the same month is normal and not flagged.
* Rounding is any absolute difference ≤ ₹0.05.  Larger discrepancies are not
  automatically classified (they surface as UNSETTLED or amount mismatches).
* A negative bank amount signals a refund; the engine looks for a matching
  platform transaction by reference_id.
* Duplicate detection is purely based on reference_id frequency in bank data.
"""

import pandas as pd
from typing import List, Dict, Any, Tuple

from app.utils.constants import (
    ROUNDING_THRESHOLD,
    GAP_LATE_SETTLEMENT, GAP_ROUNDING_DIFFERENCE,
    GAP_DUPLICATE_SETTLEMENT, GAP_UNMATCHED_REFUND,
    GAP_UNSETTLED_TRANSACTION,
    SEV_CRITICAL, SEV_HIGH, SEV_LOW,
    GAP_META,
    TXN_PATH, STL_PATH,
)
from app.services.upload_service import get_custom_data
from app.utils.logger import get_logger

log = get_logger(__name__)


class DataLoadError(RuntimeError):
    """Raised when the reconciliation dataset cannot be loaded."""


# ── Data Loading ───────────────────────────────────────────────────────────────

def load_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    custom_txn, custom_stl = get_custom_data()
    try:
        txn = custom_txn if custom_txn is not None else pd.read_csv(TXN_PATH)
        stl = custom_stl if custom_stl is not None else pd.read_csv(STL_PATH)
    except FileNotFoundError as exc:
        missing_path = exc.filename or "required reconciliation data file"
        log.exception("Default reconciliation data is unavailable: %s", missing_path)
        raise DataLoadError(
            f"Default reconciliation data is unavailable. Missing file: {missing_path}"
        ) from exc

    txn["txn_date"]     = pd.to_datetime(txn["txn_date"])
    stl["settled_date"] = pd.to_datetime(stl["settled_date"])
    return txn, stl


# ── Gap Detectors ──────────────────────────────────────────────────────────────

def _detect_late_settlements(merged: pd.DataFrame) -> List[Dict[str, Any]]:
    """GAP-1: settled_date in a different month than txn_date."""
    both = merged.dropna(subset=["transaction_id", "reference_id"])
    late = both[both["settled_date"].dt.month != both["txn_date"].dt.month]
    gaps = []
    for _, row in late.iterrows():
        gaps.append({
            "gap_type":        GAP_LATE_SETTLEMENT,
            "transaction_id":  row["transaction_id"],
            "description": (
                f"Transaction on {row['txn_date'].date()} "
                f"settled on {row['settled_date'].date()} — crosses month boundary."
            ),
            "platform_amount": round(float(row["amount_txn"]), 2),
            "bank_amount":     round(float(row["amount_stl"]), 2),
            "txn_date":        str(row["txn_date"].date()),
            "settled_date":    str(row["settled_date"].date()),
            "severity":        SEV_HIGH,
        })
    log.info("GAP-1 LATE_SETTLEMENT: %d found", len(gaps))
    return gaps


def _detect_rounding_differences(merged: pd.DataFrame) -> List[Dict[str, Any]]:
    """GAP-2: |platform_amount − bank_amount| > 0 and ≤ ROUNDING_THRESHOLD."""
    both = merged.dropna(subset=["transaction_id", "reference_id"]).copy()
    both["amount_diff"] = abs(both["amount_txn"] - both["amount_stl"])
    rounding = both[
        (both["amount_diff"] > 0) & (both["amount_diff"] <= ROUNDING_THRESHOLD)
    ]
    gaps = []
    for _, row in rounding.iterrows():
        gaps.append({
            "gap_type":        GAP_ROUNDING_DIFFERENCE,
            "transaction_id":  row["transaction_id"],
            "description": (
                f"Platform recorded ₹{row['amount_txn']:.4f}, "
                f"bank settled ₹{row['amount_stl']:.2f}. "
                f"Difference: ₹{row['amount_diff']:.4f}"
            ),
            "platform_amount": round(float(row["amount_txn"]), 4),
            "bank_amount":     round(float(row["amount_stl"]), 2),
            "difference":      round(float(row["amount_diff"]), 4),
            "txn_date":        str(row["txn_date"].date()),
            "settled_date":    str(row["settled_date"].date()),
            "severity":        SEV_LOW,
        })
    log.info("GAP-2 ROUNDING_DIFFERENCE: %d found", len(gaps))
    return gaps


def _detect_duplicate_settlements(stl: pd.DataFrame) -> List[Dict[str, Any]]:
    """GAP-3: same reference_id appears more than once in bank settlements."""
    dup_counts = stl.groupby("reference_id").size()
    duplicates = dup_counts[dup_counts > 1]
    gaps = []
    for ref_id, count in duplicates.items():
        dup_rows    = stl[stl["reference_id"] == ref_id]
        total_amt   = float(dup_rows["amount"].sum())
        expected    = float(dup_rows["amount"].iloc[0])
        overcharge  = total_amt - expected
        gaps.append({
            "gap_type":         GAP_DUPLICATE_SETTLEMENT,
            "transaction_id":   str(ref_id),
            "description": (
                f"reference_id {ref_id} appears {count}× in bank settlements. "
                f"Total settled: ₹{total_amt:,.2f} vs expected ₹{expected:,.2f}. "
                f"Overcharged: ₹{overcharge:,.2f}."
            ),
            "settlement_count": int(count),
            "total_settled":    round(total_amt, 2),
            "expected_amount":  round(expected, 2),
            "overcharge":       round(overcharge, 2),
            "severity":         SEV_CRITICAL,
        })
    log.info("GAP-3 DUPLICATE_SETTLEMENT: %d found", len(gaps))
    return gaps


def _detect_unmatched_refunds(merged: pd.DataFrame) -> List[Dict[str, Any]]:
    """GAP-4: bank settlements with negative amount and no platform transaction."""
    unmatched_stl = merged[merged["transaction_id"].isna()]
    orphans = unmatched_stl[unmatched_stl["amount_stl"] < 0]
    gaps = []
    for _, row in orphans.iterrows():
        gaps.append({
            "gap_type":       GAP_UNMATCHED_REFUND,
            "transaction_id": str(row["reference_id"]),
            "description": (
                f"Bank shows refund of ₹{abs(row['amount_stl']):,.2f} "
                f"on {row['settled_date'].date()} "
                f"but no matching original transaction found on platform."
            ),
            "bank_amount":  round(float(row["amount_stl"]), 2),
            "settled_date": str(row["settled_date"].date()),
            "severity":     SEV_CRITICAL,
        })
    log.info("GAP-4 UNMATCHED_REFUND: %d found", len(gaps))
    return gaps


def _detect_unsettled_transactions(merged: pd.DataFrame) -> List[Dict[str, Any]]:
    """GAP-5: platform transactions with no matching bank settlement."""
    unmatched_txn = merged[merged["reference_id"].isna()]
    gaps = []
    for _, row in unmatched_txn.iterrows():
        gaps.append({
            "gap_type":        GAP_UNSETTLED_TRANSACTION,
            "transaction_id":  str(row["transaction_id"]),
            "description": (
                f"Transaction {row['transaction_id']} "
                f"of ₹{row['amount_txn']:,.2f} "
                f"on {row['txn_date'].date()} has no bank settlement."
            ),
            "platform_amount": round(float(row["amount_txn"]), 2),
            "txn_date":        str(row["txn_date"].date()),
            "severity":        SEV_HIGH,
        })
    log.info("GAP-5 UNSETTLED_TRANSACTION: %d found", len(gaps))
    return gaps


# ── Summary Builder ────────────────────────────────────────────────────────────

def _build_summary(
    txn: pd.DataFrame,
    stl: pd.DataFrame,
    gaps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    platform_total = float(txn["amount"].sum())
    bank_total     = float(stl["amount"].sum())

    def count_type(t):
        return sum(1 for g in gaps if g["gap_type"] == t)

    def count_sev(s):
        return sum(1 for g in gaps if g.get("severity") == s)

    return {
        "total_transactions":   len(txn),
        "total_settlements":    len(stl),
        "platform_total_inr":   round(platform_total, 2),
        "bank_total_inr":       round(bank_total, 2),
        "net_difference_inr":   round(platform_total - bank_total, 2),
        "total_gaps_found":     len(gaps),
        "gaps_by_type": {
            GAP_LATE_SETTLEMENT:       count_type(GAP_LATE_SETTLEMENT),
            GAP_ROUNDING_DIFFERENCE:   count_type(GAP_ROUNDING_DIFFERENCE),
            GAP_DUPLICATE_SETTLEMENT:  count_type(GAP_DUPLICATE_SETTLEMENT),
            GAP_UNMATCHED_REFUND:      count_type(GAP_UNMATCHED_REFUND),
            GAP_UNSETTLED_TRANSACTION: count_type(GAP_UNSETTLED_TRANSACTION),
        },
        "gaps_by_severity": {
            "CRITICAL": count_sev("CRITICAL"),
            "HIGH":     count_sev("HIGH"),
            "LOW":      count_sev("LOW"),
        },
    }


# ── Public Entry Point ─────────────────────────────────────────────────────────

def run_reconciliation() -> Tuple[
    Dict[str, Any],
    List[Dict[str, Any]],
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Run the full reconciliation pipeline.

    Returns (summary_dict, gaps_list, txn_df, stl_df).
    """
    txn, stl = load_data()
    log.info("Loaded %d transactions, %d settlements", len(txn), len(stl))

    # outer-merge: transaction_id (platform) ↔ reference_id (bank)
    merged = pd.merge(
        txn, stl,
        left_on="transaction_id",
        right_on="reference_id",
        how="outer",
        suffixes=("_txn", "_stl"),
    )

    gaps: List[Dict[str, Any]] = []
    gaps += _detect_late_settlements(merged)
    gaps += _detect_rounding_differences(merged)
    gaps += _detect_duplicate_settlements(stl)
    gaps += _detect_unmatched_refunds(merged)
    gaps += _detect_unsettled_transactions(merged)

    summary = _build_summary(txn, stl, gaps)
    log.info("Reconciliation complete — %d gaps found", len(gaps))
    return summary, gaps, txn, stl