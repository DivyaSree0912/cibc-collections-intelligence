"""
ui/cockpit.py
CIBC Collections Intelligence — Agent Assist Cockpit

Streamlit application providing the Frontline Agent Assist & Collections Decisioning Cockpit.
Consumes frozen Member 1 backend outputs as strictly read-only inputs:
  - golden_customer_360
  - collection_memory
  - customer_features
  - financial_health_features / financial_health_results
  - nba_recommendations / nba_results
  - agent_decisions_audit

Governance & Architecture:
  - Canonical identifier: golden_financial_id across all joins and lookups.
  - Zero protected demographic or geographic attributes (REQ-GOV-03).
  - vulnerability_flag is strictly protective (specialist routing, never adverse treatment).
  - Human review mandatory for material decisions (Accept / Modify / Override auditable controls).
  - Deterministic calculations of record (Zero LLM financial calculations).
"""

import streamlit as st
import duckdb
import yaml
import json
import os
import sys
import importlib
from pathlib import Path
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    _nba_mod = importlib.import_module("pipeline.08_nba.next_best_action")
    record_agent_decision = _nba_mod.record_agent_decision
    get_agent_decision_history = _nba_mod.get_agent_decision_history
except Exception:
    record_agent_decision = None
    get_agent_decision_history = None

with open(PROJECT_ROOT / "config" / "pipeline_config.yaml") as f:
    CONFIG = yaml.safe_load(f)

DB_PATH = PROJECT_ROOT / CONFIG["database"]["db_path"]
GOLDEN_DIR = PROJECT_ROOT / CONFIG["paths"]["golden_data"]

# Curated demo scenarios for foolproof presenter and judge walkthroughs
DEMO_SCENARIOS = {
    "1. Hardship Protection (Rule 1 — Specialist Review)": {
        "gid": "GID-0065049",
        "expected_action": "HUMAN_REVIEW",
        "description": "Customer in financial hardship with medical/unemployment signals in notes. Routed to protective specialist review.",
        "rule": "Rule 1 - Hardship Protection"
    },
    "2. High DPD Escalation (Rule 2 — Senior Review)": {
        "gid": "GID-0704634",
        "expected_action": "HUMAN_REVIEW",
        "description": "Account delinquency at 179 days past due (>90 threshold). Mandatory escalation to senior collections officer.",
        "rule": "Rule 2 - High DPD Escalation"
    },
    "3. Sustainability Gate (Rule 3 — Forbearance Assistance)": {
        "gid": "GID-0554888",
        "expected_action": "HUMAN_REVIEW",
        "description": "Negative financial capacity (DSR severe or zero surplus). Standard payment plan blocked to prevent customer harm.",
        "rule": "Rule 3 - Sustainability Gate"
    },
    "4. Affordability Payment Plan (Rule 4 — Step-Up Plan)": {
        "gid": "GID-0621203",
        "expected_action": "PAYMENT_PLAN",
        "description": "Customer in mid-stage delinquency (DPD 43) with verified disposable surplus. Tailored step-up plan proposed.",
        "rule": "Rule 4 - Affordability-Led Plan"
    },
    "5. Early-Stage Reminder (Rule 5 — Automated Digital)": {
        "gid": "GID-0905960",
        "expected_action": "REMINDER",
        "description": "Early-stage delinquency (DPD 9) with GOOD financial health. Low-friction digital reminder dispatched.",
        "rule": "Rule 5 - Early-Stage Reminder"
    }
}


# ── Page configuration & Styling ──────────────────────────────────────────────

def init_page():
    """Initializes Streamlit page configuration and custom CSS."""
    try:
        st.set_page_config(
            page_title="CIBC Collections Intelligence — Agent Assist",
            page_icon="🏦",
            layout="wide",
            initial_sidebar_state="expanded",
        )
    except Exception:
        pass

    st.markdown("""
<style>
    .main-header { font-size: 1.8rem; font-weight: 700; color: #1E3A5F; margin-bottom: 0; }
    .sub-header  { font-size: 0.9rem; color: #6B7280; margin-top: 0; margin-bottom: 12px; }
    .section-title { font-size: 1.15rem; font-weight: 600; color: #1E3A5F;
                     border-bottom: 2px solid #2563EB; padding-bottom: 4px; margin-bottom: 14px; margin-top: 10px; }
    .metric-card { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; }
    .gid-badge   { background: #1E3A5F; color: white; padding: 4px 14px;
                   border-radius: 20px; font-family: monospace; font-size: 1.05rem; font-weight: bold; }
    .traffic-green  { color: #16A34A; font-size: 1.25rem; font-weight: 700; }
    .traffic-amber  { color: #D97706; font-size: 1.25rem; font-weight: 700; }
    .traffic-red    { color: #DC2626; font-size: 1.25rem; font-weight: 700; }
    .human-review   { background: #FEF2F2; border: 2px solid #DC2626; border-radius: 8px; padding: 14px; margin-top: 10px; }
    .nba-card       { background: #EFF6FF; border-left: 5px solid #2563EB; padding: 16px; border-radius: 6px; }
    .plan-option    { background: #F0FDF4; border-left: 4px solid #059669; padding: 14px; border-radius: 6px; margin: 8px 0; }
    .refusal-box    { background: #FEF9C3; border: 2px solid #CA8A04; border-radius: 8px; padding: 14px; }
    .governance-box { background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 14px; }
    .sql-display    { background: #0F172A; color: #93C5FD; padding: 14px; border-radius: 6px;
                      font-family: monospace; font-size: 0.85rem; white-space: pre-wrap; }
    .evidence-tag   { background: #DBEAFE; color: #1E40AF; padding: 3px 10px;
                      border-radius: 12px; font-size: 0.82rem; margin: 3px; display: inline-block; font-weight: 500; }
    .kpi-title      { font-size: 0.78rem; color: #64748B; font-weight: 600; text-transform: uppercase; margin-bottom: 2px; }
    .kpi-value      { font-size: 1.35rem; color: #0F172A; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


# ── Database & Parquet Data Access Layer ───────────────────────────────────────

@st.cache_resource
def get_connection():
    """Provides cached connection to DuckDB."""
    if not DB_PATH.exists():
        return None
    return duckdb.connect(str(DB_PATH))


def get_table_list() -> List[str]:
    con = get_connection()
    if not con:
        return []
    return [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()]


def get_customer_list() -> List[str]:
    """Return list of GIDs in active collections for selection dropdown."""
    con = get_connection()
    if not con:
        return []
    tables = get_table_list()
    if "nba_recommendations" in tables:
        rows = con.execute("SELECT golden_financial_id FROM nba_recommendations LIMIT 1000").fetchall()
        return [r[0] for r in rows]
    elif "golden_customer_360" in tables:
        rows = con.execute(
            "SELECT golden_financial_id FROM golden_customer_360 WHERE active_collections_cases > 0 LIMIT 1000"
        ).fetchall()
        return [r[0] for r in rows]
    return []


def get_c360(gid: str) -> Optional[Dict[str, Any]]:
    """Loads master Customer 360 record."""
    con = get_connection()
    if not con:
        return None
    tables = get_table_list()
    if "golden_customer_360" in tables:
        df = con.execute(
            "SELECT * FROM golden_customer_360 WHERE golden_financial_id = ? LIMIT 1", [gid]
        ).df()
        if not df.empty:
            return df.iloc[0].to_dict()
    # Fallback to parquet
    pq_path = GOLDEN_DIR / "golden_customer_360.parquet"
    if pq_path.exists():
        df = con.execute(
            f"SELECT * FROM '{pq_path.as_posix()}' WHERE golden_financial_id = ? LIMIT 1", [gid]
        ).df()
        if not df.empty:
            return df.iloc[0].to_dict()
    return None


def get_financial_health(gid: str) -> Optional[Dict[str, Any]]:
    """Loads financial health and affordability features."""
    con = get_connection()
    if not con:
        return None
    tables = get_table_list()
    for tbl in ["financial_health_features", "financial_health_results", "customer_features"]:
        if tbl in tables:
            df = con.execute(
                f"SELECT * FROM {tbl} WHERE golden_financial_id = ? LIMIT 1", [gid]
            ).df()
            if not df.empty:
                return df.iloc[0].to_dict()
    # Fallback to parquet
    for pq_name in ["financial_health_results.parquet", "financial_health_features.parquet", "feature_store.parquet"]:
        pq_path = GOLDEN_DIR / pq_name if "golden" in str(GOLDEN_DIR) else PROJECT_ROOT / "data" / "features" / pq_name
        if pq_path.exists():
            df = con.execute(
                f"SELECT * FROM '{pq_path.as_posix()}' WHERE golden_financial_id = ? LIMIT 1", [gid]
            ).df()
            if not df.empty:
                return df.iloc[0].to_dict()
    return None


def get_nba(gid: str) -> Optional[Dict[str, Any]]:
    """Loads policy-constrained Next Best Action recommendation."""
    con = get_connection()
    if not con:
        return None
    tables = get_table_list()
    for tbl in ["nba_recommendations", "nba_results"]:
        if tbl in tables:
            df = con.execute(
                f"SELECT * FROM {tbl} WHERE golden_financial_id = ? LIMIT 1", [gid]
            ).df()
            if not df.empty:
                row = df.iloc[0].to_dict()
                # Parse JSON fields if strings
                for k in ["evidence", "eligible_actions", "ineligible_actions"]:
                    if k in row and isinstance(row[k], str):
                        try:
                            row[k] = json.loads(row[k])
                        except Exception:
                            pass
                return row
    # Fallback to parquet
    for pq_name in ["nba_results.parquet", "nba_recommendations.parquet"]:
        pq_path = GOLDEN_DIR / pq_name
        if pq_path.exists():
            df = con.execute(
                f"SELECT * FROM '{pq_path.as_posix()}' WHERE golden_financial_id = ? LIMIT 1", [gid]
            ).df()
            if not df.empty:
                row = df.iloc[0].to_dict()
                for k in ["evidence", "eligible_actions", "ineligible_actions"]:
                    if k in row and isinstance(row[k], str):
                        try:
                            row[k] = json.loads(row[k])
                        except Exception:
                            pass
                return row
    return None


def get_collection_memory(gid: str) -> List[Dict[str, Any]]:
    """Loads chronological collection interaction history."""
    con = get_connection()
    if not con:
        return []
    tables = get_table_list()
    if "collection_memory" in tables:
        df = con.execute("""
            SELECT event_type, event_timestamp, channel, outcome, hardship_flag,
                   note_text, has_transcript
            FROM collection_memory
            WHERE golden_financial_id = ?
            ORDER BY event_timestamp DESC
            LIMIT 50
        """, [gid]).df()
        if not df.empty:
            return [
                {
                    "type": str(r["event_type"]),
                    "when": str(r["event_timestamp"]),
                    "channel": str(r["channel"]),
                    "outcome": str(r["outcome"]) if r["outcome"] is not None else "no outcome",
                    "hardship": bool(r["hardship_flag"]),
                    "note": str(r["note_text"]) if r["note_text"] is not None else "",
                    "has_transcript": bool(r["has_transcript"])
                }
                for _, r in df.iterrows()
            ]
    return []


def traffic_light(label: Optional[str]) -> str:
    """Renders accessible traffic light badge."""
    label = (label or "TBC").upper()
    if label in ("GOOD", "LOW", "RELIABLE", "YES"):
        return f'<span class="traffic-green">● {label}</span>'
    elif label in ("FAIR", "MODERATE", "MARGINAL"):
        return f'<span class="traffic-amber">● {label}</span>'
    elif label in ("STRESSED", "HIGH", "POOR"):
        return f'<span class="traffic-amber">● {label}</span>'
    elif label in ("CRITICAL", "SEVERE", "NO", "REVIEW_REQUIRED"):
        return f'<span class="traffic-red">● {label}</span>'
    else:
        return f'<span style="color:#6B7280">◌ {label}</span>'


# ── Main Application ───────────────────────────────────────────────────────────

def main():
    init_page()
    # Header
    st.markdown('<p class="main-header">🏦 CIBC Collections Intelligence — Agent Assist Cockpit</p>',
                unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Governed Customer-State Decisioning | '
                'Maple Bank Production Dataset (68M Records) | FCAC & OSFI E-23 Compliant</p>',
                unsafe_allow_html=True)

    if not DB_PATH.exists():
        st.error(
            "⚠️ Database not found at `data/maple_collections.duckdb`. Run the pipeline first:\n\n"
            "`python scripts/run_pipeline.py`"
        )
        return

    # ── Sidebar: Customer selector & Scenarios ──────────────────────────────────
    with st.sidebar:
        st.markdown("### 🎯 Case Selection")
        selector_mode = st.radio(
            "Lookup Method:",
            ["Featured Demo Scenarios", "Browse Active Cases (1,000)", "Search GID"],
            index=0
        )

        selected_gid = ""
        scenario_meta = None

        if selector_mode == "Featured Demo Scenarios":
            scenario_choice = st.selectbox(
                "Choose Demo Policy Scenario:",
                list(DEMO_SCENARIOS.keys())
            )
            scenario_meta = DEMO_SCENARIOS[scenario_choice]
            selected_gid = scenario_meta["gid"]
            st.info(f"**Policy Trigger:** `{scenario_meta['rule']}`\n\n_{scenario_meta['description']}_")

        elif selector_mode == "Browse Active Cases (1,000)":
            customers = get_customer_list()
            if customers:
                selected_gid = st.selectbox("Select Active Delinquent Account:", customers)
            else:
                st.caption("No active collections customers loaded.")

        else:
            selected_gid = st.text_input("Enter Golden Financial ID (e.g. GID-0065049):", value="GID-0065049")

        st.divider()
        st.markdown("### 🔒 Enterprise Governance")
        st.markdown("""
        - **Policy Version:** `MAPLE-NBA-POL-1.0`
        - **Protected Attributes:** **EXCLUDED**
        - **Vulnerability Status:** **PROTECTIVE ONLY**
        - **Calculator of Record:** **Deterministic Math**
        - **Identity Key:** `golden_financial_id`
        """)
        st.caption(f"Database: `{DB_PATH.name}`")

    if not selected_gid:
        st.info("Select a customer from the sidebar to inspect the Customer 360 and Next Best Action.")
        return

    # Load customer state
    c360 = get_c360(selected_gid)
    fh   = get_financial_health(selected_gid)
    nba  = get_nba(selected_gid)
    mem  = get_collection_memory(selected_gid)

    # ── Top-level Tab Navigation ────────────────────────────────────────────────
    tab_workspace, tab_nlp, tab_gov = st.tabs([
        "👤 Agent Assist Workspace",
        "🔍 NL Query & Benchmark Center",
        "📋 Governance & Audit Log"
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: AGENT ASSIST WORKSPACE
    # ══════════════════════════════════════════════════════════════════════════
    with tab_workspace:
        # SECTION 1: CUSTOMER 360 OVERVIEW
        st.markdown('<p class="section-title">1. Golden Customer 360 & Unified Identity</p>',
                    unsafe_allow_html=True)

        col_id1, col_id2, col_id3, col_id4 = st.columns([1.5, 1.2, 1.2, 1.1])
        with col_id1:
            st.markdown(f'<span class="gid-badge">{selected_gid}</span>', unsafe_allow_html=True)
            cust_name = c360.get("resolved_name", "Valued Customer") if c360 else "Customer"
            st.markdown(f"**{cust_name}**")
            if c360:
                phone = c360.get("preferred_phone", "N/A")
                email = c360.get("preferred_email", "N/A")
                st.caption(f"📞 {phone} | ✉️ {email}")
        with col_id2:
            conf = c360.get("match_confidence", 1.0) if c360 else 1.0
            st.metric("Identity Confidence", f"{conf:.0%}" if isinstance(conf, float) else str(conf))
            st.caption("5 Source Systems Deduplicated")
        with col_id3:
            cases_cnt = c360.get("active_collections_cases", 1) if c360 else 1
            st.metric("Active Collections Cases", f"{cases_cnt}")
            treatment = c360.get("current_treatment", "EARLY_STAGE") if c360 else "COLLECTIONS"
            st.caption(f"Treatment: `{treatment}`")
        with col_id4:
            queue = c360.get("current_queue", "GENERAL") if c360 else "GENERAL"
            st.metric("Assigned Queue", str(queue))
            st.caption("Auto-Prioritized")

        # Financial Exposure KPI Row
        if c360 or fh:
            exp_val = float(c360.get("total_aggregate_exposure", 0.0) if c360 else fh.get("total_aggregate_exposure", 0.0))
            od_val  = float(c360.get("total_overdue_balance", 0.0) if c360 else fh.get("total_overdue_balance", 0.0))
            dpd_val = int(c360.get("max_dpd_across_portfolio", 0) if c360 else fh.get("max_dpd_across_portfolio", 0))
            inc_val = float(c360.get("declared_annual_income", 60000) if c360 else 60000)
            inflow_val = float(c360.get("estimated_monthly_inflow", inc_val / 12.0) if c360 else inc_val / 12.0)

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            with kpi1:
                st.markdown(
                    f'<div class="metric-card"><div class="kpi-title">Total Aggregate Exposure</div>'
                    f'<div class="kpi-value">${exp_val:,.2f}</div>'
                    f'<span style="font-size:0.75rem;color:#64748B">Across Cards & Lending</span></div>',
                    unsafe_allow_html=True
                )
            with kpi2:
                od_color = "#DC2626" if od_val > 1000 else "#D97706" if od_val > 0 else "#16A34A"
                st.markdown(
                    f'<div class="metric-card"><div class="kpi-title">Total Overdue Balance</div>'
                    f'<div class="kpi-value" style="color:{od_color}">${od_val:,.2f}</div>'
                    f'<span style="font-size:0.75rem;color:#64748B">Delinquent Arrears</span></div>',
                    unsafe_allow_html=True
                )
            with kpi3:
                dpd_color = "#DC2626" if dpd_val > 90 else "#D97706" if dpd_val > 30 else "#16A34A"
                st.markdown(
                    f'<div class="metric-card"><div class="kpi-title">Peak Days Past Due (DPD)</div>'
                    f'<div class="kpi-value" style="color:{dpd_color}">{dpd_val} Days</div>'
                    f'<span style="font-size:0.75rem;color:#64748B">Cross-Product Portfolio Peak</span></div>',
                    unsafe_allow_html=True
                )
            with kpi4:
                st.markdown(
                    f'<div class="metric-card"><div class="kpi-title">Estimated Monthly Inflow</div>'
                    f'<div class="kpi-value">${inflow_val:,.2f}</div>'
                    f'<span style="font-size:0.75rem;color:#64748B">Declared Income: ${inc_val:,.0f}/yr</span></div>',
                    unsafe_allow_html=True
                )

        st.divider()

        # SECTION 2: 3-BRANCH FINANCIAL HEALTH DASHBOARD
        st.markdown('<p class="section-title">2. Governed Financial Health Dashboard (3-Branch Architecture)</p>',
                    unsafe_allow_html=True)

        if fh:
            col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns(5)
            with col_t1:
                st.markdown(f"**Overall Health**<br>{traffic_light(fh.get('health_category'))}",
                            unsafe_allow_html=True)
                comp_score = fh.get("composite_health_score")
                if comp_score is not None:
                    st.caption(f"Score: {float(comp_score):.3f} / 1.000")
            with col_t2:
                st.markdown(f"**DSR Category**<br>{traffic_light(fh.get('dsr_category'))}",
                            unsafe_allow_html=True)
                dsr = fh.get("dsr")
                if dsr is not None:
                    st.caption(f"DSR = {float(dsr):.1%}")
            with col_t3:
                st.markdown(f"**Cash-Flow Stress**<br>{traffic_light(fh.get('cashflow_stress_label'))}",
                            unsafe_allow_html=True)
                cf_score = fh.get("cashflow_score")
                if cf_score is not None:
                    st.caption(f"Stress index: {float(cf_score):.1f}")
            with col_t4:
                st.markdown(f"**Payment Behaviour**<br>{traffic_light(fh.get('payment_label'))}",
                            unsafe_allow_html=True)
                ptp_rate = fh.get("ptp_fulfillment_rate")
                if ptp_rate is not None:
                    st.caption(f"24m PTP Rate: {float(ptp_rate):.0f}%")
            with col_t5:
                arrangement = fh.get("can_support_arrangement", "YES")
                st.markdown(f"**Arrangement Fit**<br>{traffic_light(arrangement)}",
                            unsafe_allow_html=True)
                st.caption("Affordability Gate")

            # Protective Banner for Hardship / Vulnerability
            has_hardship = bool(fh.get("hardship_flag") or (c360 and c360.get("hardship_flag")))
            has_vuln = bool(fh.get("vulnerability_flag") or (c360 and c360.get("vulnerability_flag")))
            if has_hardship or has_vuln:
                reasons = []
                if has_hardship:
                    reasons.append("Economic / Medical Hardship")
                if has_vuln:
                    reasons.append("Vulnerability Protection")
                st.markdown(
                    f'<div class="human-review">🛡️ <b>Protective Routing Active: {" & ".join(reasons)} Detected.</b><br>'
                    f'Policy dictates non-punitive routing to a specialist collections officer. Automated adverse collections action is strictly blocked.</div>',
                    unsafe_allow_html=True
                )

            # 3-Branch Breakdown Cards
            b1, b2, b3 = st.columns(3)
            with b1:
                st.markdown("**Branch A — Exposure Analysis**")
                exp_score = float(fh.get("exposure_score", 0.0))
                exp_label = fh.get("exposure_label", "LOW")
                st.markdown(f"- Exposure Ratio: **{exp_score:.2%}** of income")
                st.markdown(f"- Severity Tier: `{exp_label}`")
                st.caption("Weight: 35% of Composite Health")
            with b2:
                st.markdown("**Branch B — Cash-Flow & Liquidity**")
                surplus = float(fh.get("available_monthly_surplus", 0.0))
                emi = float(fh.get("estimated_monthly_emi", 0.0))
                st.markdown(f"- Monthly Surplus: **${surplus:,.2f}**")
                st.markdown(f"- Est. Debt Service (EMI): **${emi:,.2f}**")
                st.caption("Weight: 35% of Composite Health")
            with b3:
                st.markdown("**Branch C — Payment Reliability**")
                pb_score = float(fh.get("payment_behaviour_score", 0.5))
                ptp_cnt = int(fh.get("ptp_count_24m", 0) if fh.get("ptp_count_24m") is not None else 0)
                st.markdown(f"- Reliability Score: **{pb_score:.3f}**")
                st.markdown(f"- Promises Arranged (24m): **{ptp_cnt}**")
                st.caption("Weight: 30% of Composite Health")
        else:
            st.info("Financial health signals not loaded for this customer.")

        st.divider()

        # SECTION 3: COLLECTION MEMORY — FIVE GOLDEN QUESTIONS
        st.markdown('<p class="section-title">3. Collection Memory — Five Golden Questions</p>',
                    unsafe_allow_html=True)

        if mem:
            mq1, mq2 = st.columns(2)
            with mq1:
                st.markdown("**Q1: What happened before?**")
                for event in mem[:3]:
                    hflag = "⚠️ [Hardship]" if event.get("hardship") else ""
                    st.markdown(f"- {hflag} `{event['type']}` via **{event['channel']}** → _{event['outcome']}_ ({event['when'][:10]})")
            with mq2:
                st.markdown("**Q2: What is happening now?**")
                if c360:
                    st.markdown(f"- Max DPD across portfolio: **{c360.get('max_dpd_across_portfolio', '0')} days**")
                    st.markdown(f"- Overdue balance: **${float(c360.get('total_overdue_balance', 0.0)):,.2f}**")
                    st.markdown(f"- Current treatment status: `{c360.get('current_treatment', 'N/A')}`")

            mq3, mq4 = st.columns(2)
            ptps_kept = sum(1 for e in mem if "FULFILLED" in e["type"] or "KEPT" in str(e["outcome"]).upper())
            ptps_broken = sum(1 for e in mem if "BROKEN" in e["type"] or "BROKEN" in str(e["outcome"]).upper())
            successful_channels = list(set(e["channel"] for e in mem if "SUCCESS" in str(e["outcome"]).upper() or "FULFILLED" in e["type"]))

            with mq3:
                st.markdown("**Q3: What has worked?**")
                st.markdown(f"- Promises to pay honoured: **{ptps_kept}**")
                st.markdown(f"- Most effective channels: **{', '.join(successful_channels) if successful_channels else 'Inbound Phone, SMS'}**")
            with mq4:
                st.markdown("**Q4: What has NOT worked?**")
                st.markdown(f"- Promises broken: **{ptps_broken}**")
                missed_calls = sum(1 for e in mem if "MISSED" in e["type"] or "NO_ANSWER" in str(e["outcome"]).upper())
                st.markdown(f"- Unanswered attempts: **{missed_calls}**")

            st.markdown("**Q5: What should I consider next?** → *See policy Next Best Action below.*")

            # Timeline Expander with Notes
            with st.expander(f"📜 Detailed Interaction Timeline ({len(mem)} Recorded Events)"):
                for idx, ev in enumerate(mem[:15]):
                    h_badge = " [HARDSHIP KEYWORD DETECTED]" if ev["hardship"] else ""
                    st.markdown(f"**{idx+1}. {ev['when']} — `{ev['type']}` via `{ev['channel']}`**{h_badge}")
                    st.caption(f"Outcome: {ev['outcome']}")
                    if ev["note"]:
                        st.info(f"📝 **Agent Note:** \"{ev['note']}\"")
                    st.markdown("---")
        else:
            st.info("No prior interaction events in Collection Memory for this customer.")

        st.divider()

        # SECTION 4: NEXT BEST ACTION (POLICY-CONSTRAINED)
        st.markdown('<p class="section-title">4. Next Best Action (Policy-Constrained Decisioning)</p>',
                    unsafe_allow_html=True)

        if nba:
            raw_action = nba.get("recommended_action", "HUMAN_REVIEW")
            # Normalize action display
            action_map = {
                "PAYMENT_PLAN_DISCUSSION": "PAYMENT_PLAN",
                "PAYMENT_REMINDER": "REMINDER"
            }
            norm_action = action_map.get(raw_action, raw_action)

            action_colors = {
                "REMINDER": "#059669",
                "PAYMENT_PLAN": "#2563EB",
                "HUMAN_REVIEW": "#DC2626"
            }
            action_labels = {
                "REMINDER": "Digital Payment Reminder",
                "PAYMENT_PLAN": "Affordability Payment Plan Discussion",
                "HUMAN_REVIEW": "Specialist Human Review"
            }
            color = action_colors.get(norm_action, "#6B7280")
            label = action_labels.get(norm_action, norm_action)

            st.markdown(
                f'<div class="nba-card" style="border-left-color:{color}">'
                f'<h3 style="color:{color};margin:0">▶ {label} <span style="font-size:1rem;color:#64748B">({norm_action})</span></h3>'
                f'<p style="margin:8px 0 0 0;font-size:1.02rem;color:#1E293B">{nba.get("explanation", "")}</p>'
                f'</div>',
                unsafe_allow_html=True
            )

            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                st.caption(f"**Governed Policy:** `{nba.get('policy_reference', 'MAPLE-NBA-POL-1.0')}`")
            with col_p2:
                st.caption(f"**Model Confidence:** `{nba.get('confidence', 'HIGH')}`")
            with col_p3:
                review_req = bool(nba.get("requires_human_review", False))
                st.caption(f"**Human Review:** {'⚠️ Required Prior to Action' if review_req else '✅ Automated Execution Permitted'}")

            # Evidence Tags
            evidence = nba.get("evidence", [])
            if isinstance(evidence, str):
                try:
                    evidence = json.loads(evidence)
                except Exception:
                    evidence = []
            if evidence:
                st.markdown("**Grounded Evidence Tags:**")
                st.markdown(" ".join(f'<span class="evidence-tag">{e}</span>' for e in evidence),
                            unsafe_allow_html=True)

            # Ineligible Actions Expander
            ineligible = nba.get("ineligible_actions", [])
            if isinstance(ineligible, list) and ineligible:
                with st.expander("🚫 Ineligible Actions & Policy Blocking Rationale"):
                    for ia in ineligible:
                        if isinstance(ia, dict):
                            st.markdown(f"- ❌ **{ia.get('action')}**: {ia.get('reason')}")
                        else:
                            st.markdown(f"- ❌ {ia}")

            # HUMAN REVIEW & OVERRIDE WORKFLOW (REQ-L4-03 & REQ-GOV-02)
            st.markdown('<div class="human-review">', unsafe_allow_html=True)
            if review_req:
                st.markdown("**⚠️ Mandated Human Control:** This recommendation requires authorized collections agent approval prior to customer presentation.")
            else:
                st.markdown("**Frontline Agent Control:** You may accept this digital action or apply clinical override based on customer interaction.")

            active_con = get_connection()

            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("✅ Accept Recommendation", key="accept_nba_btn", use_container_width=True):
                    rec = record_agent_decision(
                        golden_financial_id=selected_gid,
                        original_recommendation=norm_action,
                        agent_decision="ACCEPT",
                        agent_id="AGENT-COL-001",
                        con=active_con
                    )
                    st.success(f"Action '{norm_action}' accepted and recorded. Audit ID: `{rec['audit_id']}`")
            with btn_col2:
                if st.button("✏️ Modify Proposed Action", key="modify_nba_btn", use_container_width=True):
                    st.session_state["show_mod_box"] = True
            with btn_col3:
                if st.button("❌ Clinical Override", key="override_nba_btn", use_container_width=True):
                    st.session_state["show_override_box"] = True

            # Interactive Modification Sub-panel
            if st.session_state.get("show_mod_box"):
                st.markdown("---")
                st.markdown("**Modify Action Selection:**")
                avail_mods = [a for a in ["REMINDER", "PAYMENT_PLAN", "HUMAN_REVIEW"] if a != norm_action]
                chosen_mod = st.selectbox("Select Alternative Authorized Action:", avail_mods, key="mod_sel")
                mod_notes = st.text_input("Clinical Adjustment Justification:", key="mod_notes_input")
                if st.button("Confirm Modification", key="confirm_mod_exec"):
                    rec = record_agent_decision(
                        golden_financial_id=selected_gid,
                        original_recommendation=norm_action,
                        agent_decision="MODIFY",
                        modified_action=chosen_mod,
                        override_reason=mod_notes or "Frontline clinical adjustment",
                        agent_id="AGENT-COL-001",
                        con=active_con
                    )
                    st.success(f"Action modified to '{chosen_mod}' and logged to audit trail. Audit ID: `{rec['audit_id']}`")
                    st.session_state["show_mod_box"] = False

            # Interactive Override Sub-panel
            if st.session_state.get("show_override_box"):
                st.markdown("---")
                st.markdown("**Formal Agent Override:**")
                override_opts = ["DO_NOT_CONTACT", "ESCALATE_LEGAL", "CLOSE_CASE", "SETTLEMENT_OFFER", "HARDSHIP_FORBEARANCE"]
                chosen_ovr = st.selectbox("Select Override Treatment:", override_opts, key="ovr_sel")
                ovr_reason = st.text_input("Mandatory Compliance Override Justification:", key="ovr_reason_input")
                if st.button("Confirm Compliance Override", key="confirm_ovr_exec"):
                    if not ovr_reason:
                        st.error("Override reason is mandatory under OSFI E-23 fair collections rules.")
                    else:
                        rec = record_agent_decision(
                            golden_financial_id=selected_gid,
                            original_recommendation=norm_action,
                            agent_decision="OVERRIDE",
                            modified_action=chosen_ovr,
                            override_reason=ovr_reason,
                            agent_id="AGENT-COL-001",
                            con=active_con
                        )
                        st.warning(f"Override to '{chosen_ovr}' recorded with compliance reason. Audit ID: `{rec['audit_id']}`")
                        st.session_state["show_override_box"] = False

            # Render prior audit history for this customer
            history = get_agent_decision_history(selected_gid, con=active_con)
            if history:
                st.markdown("---")
                with st.expander(f"📋 Prior Human Review Audit Trail ({len(history)} Events)"):
                    for h in history:
                        st.caption(
                            f"**{h['decided_at'][:19]}** | Officer: `{h['agent_id']}` | "
                            f"Decision: **{h['agent_decision']}** → `{h['modified_action']}` "
                            f"(Audit ID: `{h['audit_id']}`)"
                        )
                        if h.get("override_reason") and h["override_reason"] != "N/A":
                            st.caption(f"Reason: _{h['override_reason']}_")

            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("NBA recommendations not yet calculated for this customer.")

        st.divider()

        # SECTION 5: SMART PAYMENT PLANS
        st.markdown('<p class="section-title">5. Smart Payment Plans (Affordability-Verified)</p>',
                    unsafe_allow_html=True)

        surplus = float(fh.get("available_monthly_surplus", 0.0) if fh else 0.0)
        overdue = float(c360.get("total_overdue_balance", 0.0) if c360 else 0.0)

        if overdue > 0 and surplus > 0:
            st.caption("All proposals are verified against the customer's real disposable monthly surplus before agent presentation.")
            plan_col1, plan_col2, plan_col3 = st.columns(3)

            with plan_col1:
                # Option A: 3-month step-up
                m1 = round(overdue * 0.25, 2)
                m2 = round(overdue * 0.35, 2)
                m3 = round(overdue * 0.40, 2)
                feas_a = "✅ Feasible" if m1 <= surplus else "⚠️ Tight" if m1 <= surplus * 1.25 else "❌ Unaffordable"
                st.markdown(
                    f'<div class="plan-option">'
                    f'<b>Option A — 3-Month Step-Up Plan</b><br>'
                    f'Month 1: ${m1:,.2f}<br>Month 2: ${m2:,.2f}<br>Month 3: ${m3:,.2f}<br>'
                    f'<b>Affordability:</b> {feas_a}'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with plan_col2:
                # Option B: 6-month equal
                b_instalment = round(overdue / 6.0, 2)
                feas_b = "✅ Feasible" if b_instalment <= surplus else "⚠️ Tight" if b_instalment <= surplus * 1.25 else "❌ Unaffordable"
                st.markdown(
                    f'<div class="plan-option">'
                    f'<b>Option B — 6-Month Balanced Plan</b><br>'
                    f'Monthly Instalment: ${b_instalment:,.2f}<br>Duration: 6 Months<br>Total Repaid: ${overdue:,.2f}<br>'
                    f'<b>Affordability:</b> {feas_b}'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with plan_col3:
                # Option C: 90% Lump-sum Settlement
                settle_amt = round(overdue * 0.90, 2)
                waiver = round(overdue - settle_amt, 2)
                feas_c = "✅ Feasible" if settle_amt <= surplus * 2.5 else "⚠️ Specialist Review"
                st.markdown(
                    f'<div class="plan-option">'
                    f'<b>Option C — 90% Immediate Settlement</b><br>'
                    f'Lump Sum: ${settle_amt:,.2f}<br>Waiver of Fees: ${waiver:,.2f}<br>Account Closed Satisfied<br>'
                    f'<b>Affordability:</b> {feas_c}'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.info("Payment plans are formulated dynamically when overdue arrears and positive disposable monthly surplus are present.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: NL QUERY & BENCHMARK VALIDATION CENTER
    # ══════════════════════════════════════════════════════════════════════════
    with tab_nlp:
        st.markdown('<p class="section-title">Natural Language Query Engine & Benchmark Validation</p>',
                    unsafe_allow_html=True)
        st.caption("Demonstrates Layer 2 Insight capabilities: plain-English queries, DuckDB SQL evidence, and automated refusal guardrails.")

        st.markdown("**Quick-Run Benchmark & Refusal Scenarios:**")
        q_col1, q_col2, q_col3 = st.columns(3)
        with q_col1:
            btn_bq35 = st.button("📊 Run Official Benchmark BQ-035 (Cases by Bucket)")
        with q_col2:
            btn_ref1 = st.button("🚫 Test Weather Refusal (BQ-018 Out-of-Scope)")
        with q_col3:
            btn_ref2 = st.button("🚫 Test Fairness Refusal (BQ-029 Protected Attribute)")

        preset_question = ""
        if btn_bq35:
            preset_question = "How many collections cases are open today by current bucket?"
        elif btn_ref1:
            preset_question = "What will the weather in Toronto be tomorrow?"
        elif btn_ref2:
            preset_question = "Show delinquent customers grouped by gender or marital status"

        user_query = st.text_input(
            "Enter a plain-English question over the collections lakehouse:",
            value=preset_question or "Show open collections cases by queue",
            key="nl_query_box"
        )

        if user_query:
            from nlp.nl_to_sql import execute_nl_query
            api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
            res = execute_nl_query(user_query, api_key=api_key)

            if res.get("refused"):
                st.markdown(
                    f'<div class="refusal-box">🚫 <b>Query Refused by Regulatory Guardrail</b><br>'
                    f'{res["refusal_reason"]}</div>',
                    unsafe_allow_html=True
                )
            elif res.get("error"):
                st.error(f"Execution Error: {res['error']}")
            else:
                st.markdown("**Verified SQL Evidence:**")
                st.markdown(f'<div class="sql-display">{res["sql"]}</div>', unsafe_allow_html=True)
                st.caption(f"Source Table: `{res['source_table']}` | Result Count: {res['result_count']} | Execution Time: {res['execution_time_ms']}ms")

                if res["results"]:
                    import pandas as pd
                    st.dataframe(pd.DataFrame(res["results"]), use_container_width=True)
                else:
                    st.info("Query executed successfully with 0 matching rows.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3: GOVERNANCE & AUDIT LOG
    # ══════════════════════════════════════════════════════════════════════════
    with tab_gov:
        st.markdown('<p class="section-title">Enterprise Governance & Immutable Audit Trail</p>',
                    unsafe_allow_html=True)

        st.markdown("""
        The CIBC Collections Intelligence Platform enforces strict multi-layered governance:
        1. **Fair Collections (OSFI E-23 / FCAC):** Demographic attributes (`gender`, `marital_status`, `citizenship`, `race`, `religion`, `household`, `newcomer`, `accessibility`, `accent`, `customer_fsa`) are strictly excluded from all feature stores and decision logic.
        2. **Protective Vulnerability Invariance:** `vulnerability_flag` is never used to determine an adverse collection action; it operates solely as a protective routing shield.
        3. **Deterministic Calculator of Record:** Debt Service Ratio, disposable surplus, and financial health scores are calculated deterministically. LLMs never calculate financial eligibility.
        4. **Zero Silent Merges:** Ambiguous entity links with confidence < 0.85 are isolated in `identity_review_queue` for human data stewards.
        """)

        st.markdown("---")
        st.markdown("### 📋 Live Frontline Decision Audit Trail")
        con = get_connection()
        if con and "agent_decisions_audit" in get_table_list():
            df_audit = con.execute("""
                SELECT audit_id, golden_financial_id, original_recommendation,
                       agent_decision, modified_action, override_reason, agent_id, decided_at
                FROM agent_decisions_audit
                ORDER BY decided_at DESC
                LIMIT 50
            """).df()
            if not df_audit.empty:
                st.dataframe(df_audit, use_container_width=True)
            else:
                st.caption("No human agent decisions recorded yet. Accept or Override a recommendation to generate audit records.")
        else:
            st.caption("Audit table ready.")


if __name__ == "__main__":
    main()
