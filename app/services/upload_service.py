import io
import pandas as pd
from typing import Optional, Tuple
from fastapi import UploadFile

from app.services.validation_service import validate_transactions, validate_settlements
from app.utils.logger import get_logger

log = get_logger(__name__)

# ── In-memory override store ───────────────────────────────────────────────────
_custom_txn: Optional[pd.DataFrame] = None
_custom_stl: Optional[pd.DataFrame] = None


async def store_uploads(
    transactions: UploadFile,
    settlements: UploadFile,
) -> Tuple[int, int]:
    """Parse, validate, and cache uploaded CSVs.  Returns (txn_count, stl_count)."""
    global _custom_txn, _custom_stl

    txn_bytes = await transactions.read()
    stl_bytes = await settlements.read()

    txn_df = pd.read_csv(io.StringIO(txn_bytes.decode()))
    stl_df = pd.read_csv(io.StringIO(stl_bytes.decode()))

    # validate before accepting
    validate_transactions(txn_df)
    validate_settlements(stl_df)

    _custom_txn = txn_df
    _custom_stl = stl_df

    log.info("Custom data loaded — txn:%d  stl:%d", len(txn_df), len(stl_df))
    return len(txn_df), len(stl_df)


def reset_uploads() -> None:
    """Revert to default generated CSVs."""
    global _custom_txn, _custom_stl
    _custom_txn = None
    _custom_stl = None
    log.info("Upload store cleared — reverting to default data.")


def get_custom_data() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Return cached custom DataFrames (or None if defaults should be used)."""
    return _custom_txn, _custom_stl