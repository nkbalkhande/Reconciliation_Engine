import pandas as pd
from app.utils.logger import get_logger

log = get_logger(__name__)

REQUIRED_TXN_COLS = {
    "transaction_id", "customer_id", "amount",
    "currency", "txn_date", "payment_method", "status", "type",
}

REQUIRED_STL_COLS = {
    "settlement_id", "reference_id", "amount",
    "currency", "settled_date", "bank_ref", "status",
}


class ValidationError(Exception):
    """Raised when a DataFrame fails schema validation."""


def validate_transactions(df: pd.DataFrame) -> None:
    """Raise ValidationError if the transactions DataFrame is malformed."""
    missing = REQUIRED_TXN_COLS - set(df.columns)
    if missing:
        raise ValidationError(
            f"Transactions CSV missing columns: {sorted(missing)}"
        )
    if df["transaction_id"].isnull().any():
        raise ValidationError("transactions: transaction_id cannot be null.")
    if df["amount"].isnull().any() or (df["amount"] < 0).any():
        raise ValidationError("transactions: amount must be non-negative and non-null.")
    log.info("Transactions validated: %d rows", len(df))


def validate_settlements(df: pd.DataFrame) -> None:
    """Raise ValidationError if the settlements DataFrame is malformed."""
    missing = REQUIRED_STL_COLS - set(df.columns)
    if missing:
        raise ValidationError(
            f"Settlements CSV missing columns: {sorted(missing)}"
        )
    if df["reference_id"].isnull().any():
        raise ValidationError("settlements: reference_id cannot be null.")
    log.info("Settlements validated: %d rows", len(df))