"""
data/generate.py
────────────────
Generates platform_transactions.csv and bank_settlements.csv
with 4 intentional gap types planted.

Gap types planted
─────────────────
  GAP-1  LATE_SETTLEMENT       — txn Jan-31, settles Feb-02
  GAP-2  ROUNDING_DIFFERENCE   — platform stores 333.335; bank rounds differently
  GAP-3  DUPLICATE_SETTLEMENT  — bank settles the same txn twice
  GAP-4  UNMATCHED_REFUND      — bank shows a refund for a txn that never existed

"""

import os
import random
import pandas as pd
from datetime import datetime, timedelta

random.seed(42)

# ── Helpers ────────────────────────────────────────────────────────────────────
def rand_id(prefix: str, n: int) -> str:
    return f"{prefix}-{random.randint(10_000, 99_999)}-{n:04d}"

def rand_date(start: datetime, max_days: int) -> datetime:
    return start + timedelta(days=random.randint(0, max_days))

# ── Config ─────────────────────────────────────────────────────────────────────
JAN_START  = datetime(2024, 1, 1)
CUSTOMERS  = [f"CUST-{i:04d}" for i in range(1, 21)]
METHODS    = ["card", "upi", "netbanking", "wallet"]

transactions: list = []
settlements:  list = []

# ── 40 clean transactions ──────────────────────────────────────────────────────
for i in range(1, 41):
    txn_id      = rand_id("TXN", i)
    amount      = round(random.uniform(100, 5_000), 2)
    txn_date    = rand_date(JAN_START, 28)
    settle_date = txn_date + timedelta(days=random.randint(1, 2))

    transactions.append({
        "transaction_id": txn_id,
        "customer_id":    random.choice(CUSTOMERS),
        "amount":         amount,
        "currency":       "INR",
        "txn_date":       txn_date.strftime("%Y-%m-%d"),
        "payment_method": random.choice(METHODS),
        "status":         "SUCCESS",
        "type":           "PAYMENT",
    })
    settlements.append({
        "settlement_id": rand_id("STL", i),
        "reference_id":  txn_id,
        "amount":        amount,
        "currency":      "INR",
        "settled_date":  settle_date.strftime("%Y-%m-%d"),
        "bank_ref":      rand_id("BANK", i),
        "status":        "SETTLED",
    })

# ══════════════════════════════════════════════════════════════════════════════
# GAP-1  LATE_SETTLEMENT  (Jan 31 txn → Feb 02 settlement)
# ══════════════════════════════════════════════════════════════════════════════
late_txn_id = rand_id("TXN", 91)
transactions.append({
    "transaction_id": late_txn_id,
    "customer_id":    "CUST-0001",
    "amount":         2_450.00,
    "currency":       "INR",
    "txn_date":       "2024-01-31",
    "payment_method": "card",
    "status":         "SUCCESS",
    "type":           "PAYMENT",
})
settlements.append({
    "settlement_id": rand_id("STL", 91),
    "reference_id":  late_txn_id,
    "amount":        2_450.00,
    "currency":      "INR",
    "settled_date":  "2024-02-02",       # ← crosses month boundary
    "bank_ref":      rand_id("BANK", 91),
    "status":        "SETTLED",
})

# ══════════════════════════════════════════════════════════════════════════════
# GAP-2  ROUNDING_DIFFERENCE  (platform: 333.335; bank rounds differently)
# ══════════════════════════════════════════════════════════════════════════════
rounding_pairs = [
    (92, 92, 333.34),
    (93, 93, 333.33),
    (94, 94, 333.33),
]
for txn_n, stl_n, bank_amt in rounding_pairs:
    rid = rand_id("TXN", txn_n)
    transactions.append({
        "transaction_id": rid,
        "customer_id":    "CUST-0002",
        "amount":         333.335,          # platform stores full precision
        "currency":       "INR",
        "txn_date":       "2024-01-15",
        "payment_method": "upi",
        "status":         "SUCCESS",
        "type":           "PAYMENT",
    })
    settlements.append({
        "settlement_id": rand_id("STL", stl_n),
        "reference_id":  rid,
        "amount":        bank_amt,          # bank truncates differently
        "currency":      "INR",
        "settled_date":  "2024-01-17",
        "bank_ref":      rand_id("BANK", stl_n),
        "status":        "SETTLED",
    })

# ══════════════════════════════════════════════════════════════════════════════
# GAP-3  DUPLICATE_SETTLEMENT  (bank settles same txn twice)
# ══════════════════════════════════════════════════════════════════════════════
dup_txn_id = rand_id("TXN", 95)
transactions.append({
    "transaction_id": dup_txn_id,
    "customer_id":    "CUST-0005",
    "amount":         875.00,
    "currency":       "INR",
    "txn_date":       "2024-01-20",
    "payment_method": "netbanking",
    "status":         "SUCCESS",
    "type":           "PAYMENT",
})
for stl_n in [96, 97]:                      # two settlements, same reference
    settlements.append({
        "settlement_id": rand_id("STL", stl_n),
        "reference_id":  dup_txn_id,
        "amount":        875.00,
        "currency":      "INR",
        "settled_date":  "2024-01-22",
        "bank_ref":      rand_id("BANK", stl_n),
        "status":        "SETTLED",
    })

# ══════════════════════════════════════════════════════════════════════════════
# GAP-4  UNMATCHED_REFUND  (bank refund, no matching platform txn)
# ══════════════════════════════════════════════════════════════════════════════
ghost_ref = rand_id("TXN", 98)              # this TXN-ID never appears on platform
settlements.append({
    "settlement_id": rand_id("STL", 98),
    "reference_id":  ghost_ref,
    "amount":        -1_200.00,             # negative = refund
    "currency":      "INR",
    "settled_date":  "2024-01-25",
    "bank_ref":      rand_id("BANK", 98),
    "status":        "REFUNDED",
})

# ── Save ───────────────────────────────────────────────────────────────────────
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(OUT_DIR, exist_ok=True)

df_txn = pd.DataFrame(transactions)
df_stl = pd.DataFrame(settlements)

df_txn.to_csv(os.path.join(OUT_DIR, "platform_transactions.csv"), index=False)
df_stl.to_csv(os.path.join(OUT_DIR, "bank_settlements.csv"), index=False)

print(f"✓ Transactions : {len(df_txn)} rows")
print(f"✓ Settlements  : {len(df_stl)} rows")
print()
print("Gaps planted:")
print(f"  [GAP-1] Late settlement     → TXN {late_txn_id}")
print(f"  [GAP-2] Rounding diff       → 3 TXNs (333.335 platform vs 333.34/33/33 bank)")
print(f"  [GAP-3] Duplicate settle    → TXN {dup_txn_id}")
print(f"  [GAP-4] Orphan refund       → REF {ghost_ref} (no platform txn)")