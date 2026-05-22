"""
Reconciliation Dashboard — Streamlit Frontend
Talks to the FastAPI backend.

Run:
    streamlit run app/dashboard.py
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv,find_dotenv
load_dotenv(find_dotenv())

DEFAULT_API_BASE = os.getenv("RECON_API_URL", "http://127.0.0.1:8000")
GAP_INFO = {
    "LATE_SETTLEMENT": (
        "Cross-Month Settlement",
        "Transaction settled in a different calendar month.",
        "HIGH",
    ),
    "ROUNDING_DIFFERENCE": (
        "Rounding Difference",
        "Platform and bank amounts differ by at most Rs 0.05.",
        "LOW",
    ),
    "DUPLICATE_SETTLEMENT": (
        "Duplicate Settlement",
        "The same transaction was settled more than once by the bank.",
        "CRITICAL",
    ),
    "UNMATCHED_REFUND": (
        "Unmatched Refund",
        "A bank refund exists without a matching platform transaction.",
        "CRITICAL",
    ),
    "UNSETTLED_TRANSACTION": (
        "Unsettled Transaction",
        "A platform transaction has no bank settlement.",
        "HIGH",
    ),
}
SEVERITY_CLASS = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "LOW": "low",
}


st.set_page_config(
    page_title="Reconciliation Control Room",
    page_icon="::",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;600&display=swap');

:root {
    --bg: #f3efe5;
    --panel: rgba(255, 252, 247, 0.86);
    --panel-strong: #fffdf9;
    --line: #d8c8ad;
    --ink: #24180c;
    --muted: #6d5a47;
    --blue: #0f7b6c;
    --orange: #d36b2d;
    --red: #b63f2e;
    --gold: #b2861e;
}

.stApp {
    background:
        radial-gradient(circle at top left, rgba(15, 123, 108, 0.18), transparent 28%),
        radial-gradient(circle at top right, rgba(211, 107, 45, 0.16), transparent 24%),
        linear-gradient(180deg, #faf6ee 0%, var(--bg) 100%);
    color: var(--ink);
}

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    color: var(--ink);
}

h1, h2, h3, h4 {
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: -0.02em;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f8f2e9 0%, #efe2cf 100%);
    border-right: 1px solid rgba(120, 90, 60, 0.18);
}

.hero {
    background: linear-gradient(135deg, rgba(255,255,255,0.8), rgba(251, 242, 226, 0.94));
    border: 1px solid rgba(117, 92, 62, 0.18);
    border-radius: 24px;
    padding: 26px 28px;
    box-shadow: 0 18px 40px rgba(70, 44, 17, 0.08);
}

.hero-kicker {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--blue);
}

.hero-title {
    font-size: 2.6rem;
    line-height: 1;
    margin: 10px 0 4px 0;
}

.hero-subtitle {
    font-size: 1rem;
    color: var(--muted);
    max-width: 56rem;
}

.metric-card {
    background: var(--panel);
    border: 1px solid rgba(118, 92, 64, 0.16);
    border-radius: 20px;
    padding: 20px 18px;
    min-height: 132px;
    box-shadow: 0 12px 26px rgba(88, 62, 35, 0.06);
}

.metric-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--muted);
}

.metric-value {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.1;
    margin-top: 14px;
}

.metric-foot {
    color: var(--muted);
    font-size: 0.88rem;
    margin-top: 8px;
}

.section-card {
    background: var(--panel);
    border: 1px solid rgba(118, 92, 64, 0.16);
    border-radius: 20px;
    padding: 18px 20px;
    box-shadow: 0 10px 22px rgba(88, 62, 35, 0.05);
}

.gap-card {
    background: var(--panel-strong);
    border: 1px solid rgba(118, 92, 64, 0.16);
    border-left: 6px solid var(--gold);
    border-radius: 18px;
    padding: 16px 18px;
    margin-bottom: 14px;
    box-shadow: 0 8px 18px rgba(88, 62, 35, 0.05);
}

.gap-card.critical { border-left-color: var(--red); }
.gap-card.high { border-left-color: var(--orange); }
.gap-card.low { border-left-color: var(--blue); }

.chip {
    display: inline-block;
    border-radius: 999px;
    padding: 4px 10px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.chip.critical { background: #fae1dc; color: #7c2217; }
.chip.high { background: #fce7d7; color: #8c4414; }
.chip.low { background: #dbf0ec; color: #0a5c50; }

.status-ok {
    color: #0b6f4f;
    font-weight: 700;
}

.status-alert {
    color: #9a2d1f;
    font-weight: 700;
}

.small-note {
    color: var(--muted);
    font-size: 0.9rem;
}

div[data-testid="stDataFrame"] {
    background: rgba(255, 255, 255, 0.45);
    border-radius: 18px;
}

.stButton > button {
    border-radius: 999px;
    border: 1px solid rgba(36, 24, 12, 0.08);
    background: linear-gradient(135deg, #0f7b6c, #1f5f8b);
    color: #fffefb;
    font-family: 'IBM Plex Mono', monospace;
    padding: 0.6rem 1rem;
}

.stDownloadButton > button,
.stFormSubmitButton > button {
    border-radius: 999px;
    font-family: 'IBM Plex Mono', monospace;
}
</style>
""",
    unsafe_allow_html=True,
)


def api_base() -> str:
    return st.session_state.get("api_base", DEFAULT_API_BASE).rstrip("/")


@st.cache_data(ttl=5, show_spinner=False)
def fetch_json(base_url: str, endpoint: str) -> dict[str, Any] | list[dict[str, Any]]:
    response = requests.get(f"{base_url}{endpoint}", timeout=8)
    response.raise_for_status()
    return response.json()


def clear_cache() -> None:
    st.cache_data.clear()


def render_api_error(endpoint: str, exc: requests.RequestException) -> None:
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            payload = response.json()
            detail = payload.get("detail", response.text)
        except ValueError:
            detail = response.text
        st.error(f"{endpoint} failed with {response.status_code}: {detail}")
        return
    st.error(f"Cannot reach backend at {api_base()}: {exc}")


def load_resource(endpoint: str) -> Any | None:
    try:
        return fetch_json(api_base(), endpoint)
    except requests.RequestException as exc:
        render_api_error(endpoint, exc)
        return None


def severity_class(severity: str) -> str:
    return SEVERITY_CLASS.get(severity.upper(), "low")


def severity_chip(severity: str) -> str:
    level = severity.upper()
    css = severity_class(level)
    return f'<span class="chip {css}">{level}</span>'


def format_currency(value: float | int) -> str:
    return f"Rs {value:,.2f}"


def render_metric(column: st.delta_generator.DeltaGenerator, label: str, value: str, foot: str, accent: str) -> None:
    with column:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color:{accent};">{value}</div>
                <div class="metric-foot">{foot}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def upload_files(api_url: str, transactions, settlements) -> tuple[bool, str]:
    response = requests.post(
        f"{api_url}/api/upload",
        files={
            "transactions": (transactions.name, transactions.getvalue(), "text/csv"),
            "settlements": (settlements.name, settlements.getvalue(), "text/csv"),
        },
        timeout=20,
    )
    if response.ok:
        payload = response.json()
        return True, (
            f"Uploaded {payload['transactions']} transactions and "
            f"{payload['settlements']} settlements."
        )

    try:
        payload = response.json()
        message = payload.get("detail", response.text)
    except ValueError:
        message = response.text
    return False, message


def clear_uploaded_data(api_url: str) -> tuple[bool, str]:
    response = requests.delete(f"{api_url}/api/upload", timeout=10)
    if response.ok:
        payload = response.json()
        return True, payload.get("status", "Data reset completed.")

    try:
        payload = response.json()
        message = payload.get("detail", response.text)
    except ValueError:
        message = response.text
    return False, message


with st.sidebar:
    st.markdown("### Control Room")
    st.caption("FastAPI-backed reconciliation dashboard")
    api_input = st.text_input("Backend URL", value=api_base())
    st.session_state["api_base"] = api_input.rstrip("/")

    page = st.radio(
        "Mode",
        ["Overview", "Gap Explorer", "Raw Data", "Upload Data"],
        label_visibility="collapsed",
    )

    if st.button("Refresh API Data", use_container_width=True):
        clear_cache()
        st.rerun()

    st.markdown("---")
    health = load_resource("/")
    if health:
        st.markdown(f"**Service**: {health['service']}")
        st.markdown(f"**Version**: {health['version']}")
        st.markdown("<span class='status-ok'>Backend reachable</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='status-alert'>Backend unavailable</span>", unsafe_allow_html=True)


summary = load_resource("/api/summary")

st.markdown(
    """
    <div class="hero">
        <div class="hero-kicker">Reconciliation Control Room</div>
        <div class="hero-title">Track settlement drift before it becomes a finance incident.</div>
        <div class="hero-subtitle">
            This Streamlit frontend reads the FastAPI reconciliation routes, surfaces detected gaps,
            and lets you upload alternate transaction and settlement CSVs without leaving the dashboard.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("")


if page == "Overview":
    if not summary:
        st.info("Summary data is unavailable. Check the backend status or upload valid CSV files.")
        st.stop()

    metric_cols = st.columns(5)
    render_metric(metric_cols[0], "Transactions", str(summary["total_transactions"]), "Rows in platform file", "#0f7b6c")
    render_metric(metric_cols[1], "Settlements", str(summary["total_settlements"]), "Rows in bank file", "#1f5f8b")
    render_metric(metric_cols[2], "Platform Total", format_currency(summary["platform_total_inr"]), "Booked platform amount", "#a15c1d")
    render_metric(metric_cols[3], "Bank Total", format_currency(summary["bank_total_inr"]), "Settled bank amount", "#7f3f98")
    render_metric(metric_cols[4], "Gaps Found", str(summary["total_gaps_found"]), "Detected reconciliation anomalies", "#b63f2e")

    st.markdown("")

    diff = float(summary["net_difference_inr"])
    if abs(diff) < 0.005:
        st.success("Platform and bank totals are currently aligned.")
    else:
        st.warning(f"Net difference detected: {format_currency(diff)}")

    left, right = st.columns([1.1, 0.9])

    with left:
        st.markdown("#### Gap volume by type")
        gaps_by_type = pd.DataFrame(
            list(summary["gaps_by_type"].items()),
            columns=["Gap Type", "Count"],
        )
        st.bar_chart(gaps_by_type.set_index("Gap Type"), color="#0f7b6c")

    with right:
        st.markdown("#### Gap volume by severity")
        gaps_by_severity = pd.DataFrame(
            list(summary["gaps_by_severity"].items()),
            columns=["Severity", "Count"],
        )
        st.bar_chart(gaps_by_severity.set_index("Severity"), color="#d36b2d")

    rows = []
    for gap_type, count in summary["gaps_by_type"].items():
        label, description, severity = GAP_INFO.get(gap_type, (gap_type, "", "LOW"))
        rows.append(
            {
                "Gap Type": label,
                "Count": count,
                "Severity": severity,
                "Description": description,
            }
        )

    st.markdown("#### Gap catalog")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


elif page == "Gap Explorer":
    gap_data = load_resource("/api/gaps")
    if not gap_data:
        st.info("Gap data is unavailable. Check the backend status or upload valid CSV files.")
        st.stop()

    gaps = gap_data["gaps"]
    st.markdown(f"#### {len(gaps)} active gaps")

    filter_cols = st.columns(3)
    with filter_cols[0]:
        types = sorted({gap["gap_type"] for gap in gaps})
        selected_types = st.multiselect("Gap type", types, default=types)
    with filter_cols[1]:
        severities = ["CRITICAL", "HIGH", "LOW"]
        selected_severities = st.multiselect("Severity", severities, default=severities)
    with filter_cols[2]:
        text_filter = st.text_input("Search transaction or description")

    query = text_filter.strip().lower()
    filtered = [
        gap for gap in gaps
        if gap["gap_type"] in selected_types
        and gap.get("severity", "LOW") in selected_severities
        and (
            not query
            or query in str(gap.get("transaction_id", "")).lower()
            or query in str(gap.get("description", "")).lower()
        )
    ]

    st.caption(f"Showing {len(filtered)} of {len(gaps)} gaps")

    for gap in filtered:
        severity = gap.get("severity", "LOW")
        details = []
        if gap.get("platform_amount") is not None:
            details.append(f"Platform: {gap['platform_amount']}")
        if gap.get("bank_amount") is not None:
            details.append(f"Bank: {gap['bank_amount']}")
        if gap.get("difference") is not None:
            details.append(f"Difference: {gap['difference']}")
        if gap.get("overcharge") is not None:
            details.append(f"Overcharge: {gap['overcharge']}")
        if gap.get("settlement_count") is not None:
            details.append(f"Settlement count: {gap['settlement_count']}")
        if gap.get("txn_date"):
            details.append(f"Txn date: {gap['txn_date']}")
        if gap.get("settled_date"):
            details.append(f"Settled date: {gap['settled_date']}")

        st.markdown(
            f"""
            <div class="gap-card {severity_class(severity)}">
                <div style="display:flex; justify-content:space-between; gap:12px; align-items:center; flex-wrap:wrap;">
                    <div style="font-family:'IBM Plex Mono', monospace; font-size:0.8rem; color:#6d5a47;">{gap['transaction_id']}</div>
                    <div>{severity_chip(severity)}</div>
                    <div style="font-family:'IBM Plex Mono', monospace; font-size:0.76rem; color:#0f7b6c;">{gap['gap_type']}</div>
                </div>
                <div style="margin-top:10px; font-size:1rem;">{gap['description']}</div>
                <div class="small-note" style="margin-top:8px;">{' | '.join(details) if details else 'No extra fields for this record.'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


elif page == "Raw Data":
    st.markdown("#### Uploaded source data")
    tab_txn, tab_stl = st.tabs(["Transactions", "Settlements"])

    with tab_txn:
        transactions = load_resource("/api/transactions")
        if transactions:
            txn_df = pd.DataFrame(transactions)
            st.caption(f"{len(txn_df)} transaction rows")
            st.dataframe(txn_df, use_container_width=True, hide_index=True)

    with tab_stl:
        settlements = load_resource("/api/settlements")
        if settlements:
            stl_df = pd.DataFrame(settlements)
            st.caption(f"{len(stl_df)} settlement rows")
            st.dataframe(stl_df, use_container_width=True, hide_index=True)


else:
    st.markdown("#### Upload transaction sources")
    st.markdown(
        "Upload both CSV files to replace the in-memory dataset used by the FastAPI reconciliation routes."
    )

    st.markdown(
        """
        | transactions CSV | settlements CSV |
        |---|---|
        | transaction_id, customer_id, amount, currency, txn_date, payment_method, status, type | settlement_id, reference_id, amount, currency, settled_date, bank_ref, status |
        """
    )

    with st.form("upload_form"):
        transactions_file = st.file_uploader("Transactions CSV", type="csv")
        settlements_file = st.file_uploader("Settlements CSV", type="csv")
        submitted = st.form_submit_button("Upload to FastAPI")

    if submitted:
        if not transactions_file or not settlements_file:
            st.error("Select both CSV files before uploading.")
        else:
            success, message = upload_files(api_base(), transactions_file, settlements_file)
            if success:
                clear_cache()
                st.success(message)
            else:
                st.error(message)

    if st.button("Clear uploaded data"):
        success, message = clear_uploaded_data(api_base())
        clear_cache()
        if success:
            st.success(message)
        else:
            st.error(message)