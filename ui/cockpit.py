"""
ui/cockpit.py
CIBC Collections Intelligence — Agent Assist Cockpit

Streamlit application providing the Agent Assist interface.
Every agent-facing feature is driven by governed data from the pipeline.

Sections:
  1. Customer Identity & Golden Financial ID
  2. Financial Health Dashboard (traffic lights)
  3. Collection Memory — Five Golden Questions
  4. Next Best Action (policy-constrained, explainable)
  5. Smart Payment Plan (affordability-driven, human review required)
  6. NL Query Panel (evidence-grounded, SQL shown)

Governance panel: shows data freshness, lineage, and review status.
"""

import streamlit as st
import duckdb
import yaml
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

with open(PROJECT_ROOT / "config" / "pipeline_config.yaml") as f:
    CONFIG = yaml.safe_load(f)

DB_PATH = PROJECT_ROOT / CONFIG["database"]["db_path"]


# ── Page configuration ─────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Collections Intelligence — Agent Assist",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ─────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main-header { font-size: 1.8rem; font-weight: 700; color: #1E3A5F; margin-bottom: 0; }
    .sub-header  { font-size: 0.9rem; color: #6B7280; margin-top: 0; }
    .section-title { font-size: 1.1rem; font-weight: 600; color: #1E3A5F; 
                     border-bottom: 2px solid #2563EB; padding-bottom: 4px; margin-bottom: 12px; }
    .metric-card { background: #F0F9FF; border-radius: 8px; padding: 12px; margin: 4px; }
    .gid-badge   { background: #1E3A5F; color: white; padding: 4px 12px; 
                   border-radius: 20px; font-family: monospace; font-size: 0.9rem; }
    .traffic-green  { color: #16A34A; font-size: 1.3rem; font-weight: 700; }
    .traffic-amber  { color: #D97706; font-size: 1.3rem; font-weight: 700; }
    .traffic-red    { color: #DC2626; font-size: 1.3rem; font-weight: 700; }
    .human-review   { background: #FEF2F2; border: 2px solid #DC2626; border-radius: 8px; padding: 12px; }
    .nba-card       { background: #EFF6FF; border-left: 4px solid #2563EB; padding: 12px; border-radius: 4px; }
    .plan-option    { background: #F0FDF4; border-left: 4px solid #059669; padding: 12px; border-radius: 4px; margin: 6px 0; }
    .refusal-box    { background: #FEF9C3; border: 2px solid #CA8A04; border-radius: 8px; padding: 12px; }
    .governance-box { background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px; }
    .sql-display    { background: #1E293B; color: #93C5FD; padding: 12px; border-radius: 6px; 
                      font-family: monospace; font-size: 0.82rem; white-space: pre-wrap; }
    .evidence-tag   { background: #DBEAFE; color: #1E40AF; padding: 2px 8px; 
                      border-radius: 12px; font-size: 0.8rem; margin: 2px; display: inline-block; }
</style>
""", unsafe_allow_html=True)


# ── Database helpers ───────────────────────────────────────────────────────────

@st.cache_resource
def get_connection():
    if not DB_PATH.exists():
        return None
    return duckdb.connect(str(DB_PATH), read_only=True)


def get_table_list():
    con = get_connection()
    if not con:
        return []
    return [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()]


def get_customer_list():
    """Return list of GIDs in active collections for the dropdown."""
    con = get_connection()
    if not con:
        return []
    tables = get_table_list()
    if "nba_recommendations" in tables:
        rows = con.execute(
            "SELECT golden_financial_id FROM nba_recommendations LIMIT 1000"
        ).fetchall()
        return [r[0] for r in rows]
    elif "golden_customer_360" in tables:
        rows = con.execute(
            "SELECT golden_financial_id FROM golden_customer_360 LIMIT 1000"
        ).fetchall()
        return [r[0] for r in rows]
    return []


def get_c360(gid: str) -> dict | None:
    con = get_connection()
    if not con or "golden_customer_360" not in get_table_list():
        return None
    row = con.execute(
        "SELECT * FROM golden_customer_360 WHERE golden_financial_id = ? LIMIT 1", [gid]
    ).fetchone()
    if not row:
        return None
    cols = [d[0] for d in con.execute(
        "SELECT * FROM golden_customer_360 WHERE golden_financial_id = ? LIMIT 1", [gid]
    ).description]
    return dict(zip(cols, row))


def get_financial_health(gid: str) -> dict | None:
    con = get_connection()
    if not con or "financial_health_features" not in get_table_list():
        return None
    row = con.execute(
        "SELECT * FROM financial_health_features WHERE golden_financial_id = ? LIMIT 1", [gid]
    ).fetchone()
    if not row:
        return None
    cols = [d[0] for d in con.execute(
        "SELECT * FROM financial_health_features WHERE golden_financial_id = ? LIMIT 1", [gid]
    ).description]
    return dict(zip(cols, row))


def get_nba(gid: str) -> dict | None:
    con = get_connection()
    if not con or "nba_recommendations" not in get_table_list():
        return None
    row = con.execute(
        "SELECT * FROM nba_recommendations WHERE golden_financial_id = ? LIMIT 1", [gid]
    ).fetchone()
    if not row:
        return None
    cols = [d[0] for d in con.execute(
        "SELECT * FROM nba_recommendations WHERE golden_financial_id = ? LIMIT 1", [gid]
    ).description]
    return dict(zip(cols, row))


def get_collection_memory(gid: str) -> list:
    con = get_connection()
    if not con or "collection_memory" not in get_table_list():
        return []
    rows = con.execute("""
        SELECT event_type, event_timestamp, channel, outcome, hardship_flag,
               note_text, has_transcript
        FROM collection_memory
        WHERE golden_financial_id = ?
        ORDER BY event_timestamp DESC
        LIMIT 20
    """, [gid]).fetchall()
    return [
        {"type": r[0], "when": str(r[1]), "channel": r[2], "outcome": r[3],
         "hardship": r[4], "note": r[5], "has_transcript": r[6]}
        for r in rows
    ]


# ── Traffic light helper ───────────────────────────────────────────────────────

def traffic_light(label: str | None) -> str:
    label = (label or "TBC").upper()
    if label in ("GOOD", "LOW", "RELIABLE", "YES"):
        return f'<span class="traffic-green">● {label}</span>'
    elif label in ("FAIR", "MODERATE"):
        return f'<span class="traffic-amber">● {label}</span>'
    elif label in ("STRESSED", "STRESSED", "HIGH", "POOR", "MARGINAL"):
        return f'<span class="traffic-amber">● {label}</span>'
    elif label in ("CRITICAL", "SEVERE", "NO"):
        return f'<span class="traffic-red">● {label}</span>'
    else:
        return f'<span style="color:#6B7280">◌ {label}</span>'


# ── Main application ───────────────────────────────────────────────────────────

def main():
    # Header
    st.markdown('<p class="main-header">🏦 Collections Intelligence — Agent Assist</p>',
                unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Maple Bank Synthetic Dataset | '
                'All decisions require agent review | No protected attributes used</p>',
                unsafe_allow_html=True)

    # Check database
    if not DB_PATH.exists():
        st.error(
            "⚠️ Database not found. Run the pipeline first:\n"
            "`python scripts/run_pipeline.py`"
        )
        return

    tables = get_table_list()
    pipeline_complete = all(t in tables for t in [
        "golden_customer_360", "financial_health_features", "nba_recommendations"
    ])

    if not pipeline_complete:
        st.warning(
            f"Pipeline not fully run. Available tables: {tables}\n\n"
            "Run: `python scripts/run_pipeline.py`"
        )

    # ── Sidebar: Customer selector ─────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🔍 Customer Lookup")
        customers = get_customer_list()
        if customers:
            selected_gid = st.selectbox("Select Customer (GID)", customers)
        else:
            selected_gid = st.text_input("Enter Golden Financial ID", value="")
            st.caption("No customers loaded yet. Run pipeline first.")

        st.divider()
        st.markdown("### 📋 Governance")
        st.caption(f"DB: `{DB_PATH.name}`")
        st.caption(f"Tables: {len(tables)}")
        st.caption(f"Policy: MAPLE-NBA-POL-1.0")
        st.caption("Protected attributes: **EXCLUDED**")
        st.caption("Human review: **Required for material decisions**")

    if not selected_gid:
        st.info("Select a customer from the sidebar to begin.")
        return

    # Load data
    c360 = get_c360(selected_gid)
    fh   = get_financial_health(selected_gid)
    nba  = get_nba(selected_gid)
    mem  = get_collection_memory(selected_gid)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1: GOLDEN FINANCIAL ID & CUSTOMER PROFILE
    # ══════════════════════════════════════════════════════════════════════════

    st.markdown('<p class="section-title">1. Golden Financial ID & Customer Profile</p>',
                unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<span class="gid-badge">{selected_gid}</span>',
                    unsafe_allow_html=True)
        st.caption("Golden Financial ID")
    with col2:
        if c360:
            conf = c360.get("match_confidence", "TBC")
            color = "#16A34A" if conf == 1.0 else "#D97706" if conf and conf >= 0.92 else "#DC2626"
            st.metric("Match Confidence", f"{conf:.0%}" if isinstance(conf, float) else conf)
        else:
            st.metric("Match Confidence", "TBC")
    with col3:
        if c360:
            st.metric("Source Systems", c360.get("source_system_count", "TBC"))
        else:
            st.metric("Source Systems", "TBC")
    with col4:
        if c360:
            review = c360.get("any_record_needs_review", False)
            st.metric("Review Flag", "⚠️ YES" if review else "✅ No")
        else:
            st.metric("Review Flag", "TBC")

    if c360:
        st.caption(f"**Sources:** {c360.get('contributing_source_systems', 'TBC')} | "
                   f"**Last updated:** {c360.get('lineage_last_updated', 'TBC')}")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2: FINANCIAL HEALTH DASHBOARD
    # ══════════════════════════════════════════════════════════════════════════

    st.markdown('<p class="section-title">2. Financial Health Dashboard</p>',
                unsafe_allow_html=True)

    if fh:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"**Overall Health**<br>{traffic_light(fh.get('health_category'))}",
                        unsafe_allow_html=True)
        with col2:
            st.markdown(f"**DSR Category**<br>{traffic_light(fh.get('dsr_category'))}",
                        unsafe_allow_html=True)
            dsr = fh.get("dsr")
            if dsr:
                st.caption(f"DSR = {dsr:.1%}")
        with col3:
            st.markdown(f"**Cash-Flow Stress**<br>{traffic_light(fh.get('cashflow_stress_label'))}",
                        unsafe_allow_html=True)
        with col4:
            st.markdown(f"**Payment Behaviour**<br>{traffic_light(fh.get('payment_label'))}",
                        unsafe_allow_html=True)
            ptp = fh.get("ptp_fulfillment_rate")
            if ptp is not None:
                st.caption(f"PTP Rate: {ptp:.0%}")
        with col5:
            arrangement = fh.get("can_support_arrangement", "TBC")
            st.markdown(f"**Arrangement Fit**<br>{traffic_light(arrangement)}",
                        unsafe_allow_html=True)

        if fh.get("vulnerability_flag") or fh.get("hardship_flag"):
            st.markdown(
                '<div class="human-review">⚠️ <b>Hardship / Vulnerability signal detected.</b> '
                'This case requires human specialist review before any collection action. '
                'This is a protective measure.</div>',
                unsafe_allow_html=True
            )

        if fh.get("requires_human_review"):
            st.warning("**Human review required** for this case based on financial health assessment.")

        # Affordability detail
        surplus = fh.get("available_monthly_surplus")
        if surplus is not None:
            st.info(f"**Estimated available monthly surplus:** ${surplus:,.2f} | "
                    f"**Composite health score:** {fh.get('composite_health_score', 'TBC'):.3f}"
                    if isinstance(fh.get('composite_health_score'), float) else
                    f"**Estimated available monthly surplus:** ${surplus:,.2f}")
        st.caption(f"Formula version: {fh.get('formula_version', 'TBC')} | "
                   f"Data completeness: {fh.get('data_completeness_pct', 0):.0%}")
    else:
        st.info("Financial health data not available. Run the financial health engine.")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3: COLLECTION MEMORY — FIVE GOLDEN QUESTIONS
    # ══════════════════════════════════════════════════════════════════════════

    st.markdown('<p class="section-title">3. Collection Memory — Five Golden Questions</p>',
                unsafe_allow_html=True)

    if mem:
        q1, q2 = st.columns(2)
        with q1:
            st.markdown("**Q1: What happened before?**")
            for event in mem[:3]:
                hflag = "⚠️" if event.get("hardship") else ""
                st.markdown(
                    f"- {hflag} `{event['type']}` via **{event['channel']}** "
                    f"→ {event['outcome'] or 'no outcome recorded'} "
                    f"_{event['when']}_"
                )
        with q2:
            st.markdown("**Q2: What is happening now?**")
            if c360:
                dpd = c360.get("max_dpd_across_portfolio", "TBC")
                active = c360.get("active_collections_cases", "TBC")
                st.markdown(f"- Max DPD: **{dpd}** days")
                st.markdown(f"- Open cases: **{active}**")

        q3, q4 = st.columns(2)
        ptps_ok = sum(1 for e in mem if e["type"] == "PTP_FULFILLED")
        ptps_br = sum(1 for e in mem if e["type"] == "PTP_BROKEN")
        calls_m  = sum(1 for e in mem if e["type"] == "CALL_MISSED")
        with q3:
            st.markdown("**Q3: What has worked?**")
            st.markdown(f"- PTPs honoured: **{ptps_ok}**")
            effective = set(e["channel"] for e in mem if e.get("outcome") and
                            "success" in str(e.get("outcome","")).lower())
            if effective:
                st.markdown(f"- Effective channels: **{', '.join(effective)}**")
            else:
                st.markdown("- Effective channel data: TBC")
        with q4:
            st.markdown("**Q4: What has NOT worked?**")
            st.markdown(f"- PTPs broken: **{ptps_br}**")
            st.markdown(f"- Calls missed: **{calls_m}**")

        st.markdown("**Q5: What should I consider next?** → See NBA recommendation below")

        hardship_events = [e for e in mem if e.get("hardship")]
        if hardship_events:
            st.warning(f"⚠️ {len(hardship_events)} event(s) with hardship/vulnerability keywords detected.")
    else:
        st.info("Collection Memory not yet built. Run pipeline phase 5.")

    with st.expander("Full Collection Timeline (last 20 events)"):
        if mem:
            import pandas as pd
            df = pd.DataFrame(mem)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No events found.")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4: NEXT BEST ACTION
    # ══════════════════════════════════════════════════════════════════════════

    st.markdown('<p class="section-title">4. Next Best Action (Policy-Constrained)</p>',
                unsafe_allow_html=True)

    if nba:
        action = nba.get("recommended_action", "TBC")
        action_colors = {
            "REMINDER": "#059669",
            "PAYMENT_PLAN": "#2563EB",
            "HUMAN_REVIEW": "#DC2626",
        }
        color = action_colors.get(action, "#6B7280")

        st.markdown(
            f'<div class="nba-card">'
            f'<h3 style="color:{color};margin:0">▶ {action}</h3>'
            f'<p style="margin:8px 0 0 0">{nba.get("explanation", "")}</p>'
            f'</div>',
            unsafe_allow_html=True
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"**Policy:** {nba.get('policy_reference', 'TBC')}")
        with col2:
            st.caption(f"**Confidence:** {nba.get('confidence', 'TBC')}")
        with col3:
            review = nba.get("requires_human_review", False)
            st.caption(f"**Human review:** {'⚠️ Required' if review else '✅ Not required'}")

        # Evidence
        evidence = nba.get("evidence", "[]")
        if isinstance(evidence, str):
            evidence = json.loads(evidence) if evidence else []
        if evidence:
            st.markdown("**Evidence:**")
            st.markdown(" ".join(
                f'<span class="evidence-tag">{e}</span>' for e in evidence
            ), unsafe_allow_html=True)

        # Ineligible actions
        ineligible = nba.get("ineligible_actions", "[]")
        if isinstance(ineligible, str):
            ineligible = json.loads(ineligible) if ineligible else []
        if ineligible:
            with st.expander("Ineligible actions and reasons"):
                for ia in ineligible:
                    st.markdown(f"❌ **{ia['action']}** — {ia['reason']}")

        # Human review controls
        if nba.get("requires_human_review"):
            st.markdown('<div class="human-review">',  unsafe_allow_html=True)
            st.markdown("**⚠️ This recommendation requires human agent review and approval before any action.**")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ Accept", key="accept_nba"):
                    st.success("Action accepted. (Demo: logged to audit)")
            with col2:
                if st.button("✏️ Modify", key="modify_nba"):
                    st.info("Modification workflow would open here.")
            with col3:
                if st.button("❌ Override", key="override_nba"):
                    st.warning("Override recorded. Please provide reason.")
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("NBA recommendations not yet generated. Run pipeline phase 8.")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5: SMART PAYMENT PLAN
    # ══════════════════════════════════════════════════════════════════════════

    st.markdown('<p class="section-title">5. Smart Payment Plans (Agent Review Required)</p>',
                unsafe_allow_html=True)

    if nba and nba.get("recommended_action") == "PAYMENT_PLAN" and fh and c360:
        surplus   = fh.get("available_monthly_surplus")
        overdue   = c360.get("total_overdue_balance")

        if surplus and overdue and surplus > 0 and overdue > 0:
            st.caption("Plans generated from verified financial surplus. "
                       "Agent must review and approve before presenting to customer.")

            # Option A: 3-month step-up
            a1 = round(overdue * 0.30, 2)
            a2 = round(overdue * 0.35, 2)
            feasible_a = "✅ Feasible" if a1 <= surplus else "⚠️ Tight" if a1 <= surplus * 1.2 else "❌ Unaffordable"
            st.markdown(
                f'<div class="plan-option">'
                f'<b>Option A — 3-Month Step-Up Plan</b><br>'
                f'Month 1: ${a1:,.2f} | Month 2: ${a2:,.2f} | Month 3: ${a2:,.2f}<br>'
                f'Total: ${overdue:,.2f} | Affordability: {feasible_a} (surplus: ${surplus:,.2f})'
                f'</div>',
                unsafe_allow_html=True
            )

            # Option B: 6-month equal
            b = round(overdue / 6, 2)
            feasible_b = "✅ Feasible" if b <= surplus else "⚠️ Tight" if b <= surplus * 1.2 else "❌ Unaffordable"
            st.markdown(
                f'<div class="plan-option">'
                f'<b>Option B — 6-Month Equal Plan</b><br>'
                f'Monthly instalment: ${b:,.2f} x 6<br>'
                f'Total: ${overdue:,.2f} | Affordability: {feasible_b}'
                f'</div>',
                unsafe_allow_html=True
            )

            # Option C: Settlement
            settle = round(overdue * 0.90, 2)
            feasible_c = "✅ Possible (immediate)" if settle <= surplus * 3 else "⚠️ Review"
            st.markdown(
                f'<div class="plan-option">'
                f'<b>Option C — 90% Settlement (Late Fee Waiver)</b><br>'
                f'Immediate settlement: ${settle:,.2f} (waives remaining ${overdue - settle:,.2f})<br>'
                f'Affordability: {feasible_c} | Subject to policy approval'
                f'</div>',
                unsafe_allow_html=True
            )

            st.warning("**All payment plans require agent approval before presentation to customer.** "
                       "These are estimates based on available financial data.")
        else:
            st.info("Payment plan calculation requires overdue balance and income data (TBC for this customer).")
    elif nba and nba.get("recommended_action") != "PAYMENT_PLAN":
        st.info(f"Payment plan not the recommended action for this customer. "
                f"Current NBA: {nba.get('recommended_action', 'TBC')}")
    else:
        st.info("NBA and financial health data required for payment plan calculation.")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6: NL QUERY PANEL
    # ══════════════════════════════════════════════════════════════════════════

    st.markdown('<p class="section-title">6. Natural Language Query (SQL Shown)</p>',
                unsafe_allow_html=True)

    question = st.text_input(
        "Ask a question about this customer or the portfolio:",
        placeholder="e.g. Which customers have DPD above 60 days and a hardship flag?",
        key="nl_question"
    )

    example_questions = [
        "Which customers have DPD above 60 days?",
        "Show customers with DSR above 70%",
        "Who has a hardship or vulnerability flag?",
        "Show customers where the recommended action is PAYMENT_PLAN",
        "Which customers have a CRITICAL health category?",
    ]
    st.caption("Example questions: " + " | ".join(
        f"`{q}`" for q in example_questions[:3]
    ))

    if question:
        from nlp.nl_to_sql import execute_nl_query
        import os
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        result = execute_nl_query(question, api_key=api_key)

        if result["refused"]:
            st.markdown(
                f'<div class="refusal-box">🚫 <b>Question Refused</b><br>'
                f'{result["refusal_reason"]}</div>',
                unsafe_allow_html=True
            )
        elif result.get("error"):
            st.error(f"Error: {result['error']}")
        else:
            # Always show SQL
            st.markdown("**Generated SQL:**")
            st.markdown(
                f'<div class="sql-display">{result["sql"]}</div>',
                unsafe_allow_html=True
            )
            st.caption(f"Source: `{result['source_table']}` | "
                       f"Rows: {result['result_count']} | "
                       f"Time: {result['execution_time_ms']}ms")

            if result["results"]:
                import pandas as pd
                df = pd.DataFrame(result["results"])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No results found.")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # GOVERNANCE PANEL
    # ══════════════════════════════════════════════════════════════════════════

    with st.expander("🔒 Governance & Audit Information"):
        st.markdown('<div class="governance-box">', unsafe_allow_html=True)
        st.markdown("**Data Governance**")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            - ✅ Protected attributes: **EXCLUDED** from all calculations
            - ✅ Hardship flags: **Protective routing only**
            - ✅ Human review: **Required for material decisions**
            - ✅ AI: **Retrieval + explanation only** (not the calculator)
            """)
        with col2:
            st.markdown("""
            - ✅ Affordability: **Deterministic formula** (not LLM)
            - ✅ Every recommendation: **Policy referenced**
            - ✅ Every answer: **SQL evidence shown**
            - ✅ Identity resolution: **Confidence-gated**
            """)
        if c360:
            st.caption(f"Pipeline version: {c360.get('pipeline_version', 'TBC')} | "
                       f"Snapshot: {c360.get('snapshot_date', 'TBC')} | "
                       f"Lineage: {c360.get('lineage_last_updated', 'TBC')}")
        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
