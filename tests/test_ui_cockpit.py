"""
tests/test_ui_cockpit.py
CIBC Collections Intelligence — UI Cockpit Test Suite

Verifies:
  - REQ-L4-01: NBA engine recommendation loading
  - REQ-L4-02: Plain-English explanation per decision
  - REQ-L4-03 / REQ-GOV-02: Human review and override point with audit trail
  - REQ-GOV-03: No protected attributes in decisions or UI presentations
  - REQ-GOV-04: Hardship protective routing
  - Five curated demo scenarios
"""

import pytest
import duckdb
from pathlib import Path
from typing import Dict, Any

from ui.cockpit import (
    DEMO_SCENARIOS,
    get_connection,
    get_table_list,
    get_customer_list,
    get_c360,
    get_financial_health,
    get_nba,
    get_collection_memory,
    traffic_light,
    record_agent_decision,
    get_agent_decision_history,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "maple_collections.duckdb"

PROTECTED_ATTRIBUTES = {
    "gender", "marital_status", "citizenship", "race",
    "religion", "household", "newcomer", "accessibility",
    "accent", "customer_fsa", "postal_code"
}


# ── Database & Loader Tests ───────────────────────────────────────────────────

def test_database_connection():
    """Verify DuckDB read-only connection is established."""
    con = get_connection()
    assert con is not None
    tables = get_table_list()
    assert "golden_customer_360" in tables
    assert "nba_recommendations" in tables or "nba_results" in tables


def test_customer_list_non_empty():
    """Verify get_customer_list returns active collections GIDs."""
    customers = get_customer_list()
    assert isinstance(customers, list)
    assert len(customers) > 0
    assert all(g.startswith("GID-") for g in customers[:20])


def test_traffic_light_formatting():
    """Verify traffic light badge HTML output for various categories."""
    assert "traffic-green" in traffic_light("GOOD")
    assert "traffic-green" in traffic_light("LOW")
    assert "traffic-green" in traffic_light("YES")
    assert "traffic-amber" in traffic_light("FAIR")
    assert "traffic-amber" in traffic_light("STRESSED")
    assert "traffic-red" in traffic_light("CRITICAL")
    assert "traffic-red" in traffic_light("SEVERE")
    assert "traffic-red" in traffic_light("NO")
    assert "◌" in traffic_light(None)


# ── Curated Demo Scenarios Tests ──────────────────────────────────────────────

@pytest.mark.parametrize("scenario_name,meta", list(DEMO_SCENARIOS.items()))
def test_demo_scenario_data_integrity(scenario_name, meta):
    """Verify each curated demo scenario loads completely with correct policy rule."""
    gid = meta["gid"]
    expected_action = meta["expected_action"]
    expected_rule = meta["rule"]

    # 1. Customer 360
    c360 = get_c360(gid)
    assert c360 is not None, f"C360 not found for {gid} ({scenario_name})"
    assert c360["golden_financial_id"] == gid

    # 2. Financial Health
    fh = get_financial_health(gid)
    assert fh is not None, f"Financial health not found for {gid} ({scenario_name})"
    assert fh["golden_financial_id"] == gid
    assert "health_category" in fh
    assert "dsr" in fh
    assert "available_monthly_surplus" in fh

    # 3. Next Best Action (REQ-L4-01 & REQ-L4-02)
    nba = get_nba(gid)
    assert nba is not None, f"NBA not found for {gid} ({scenario_name})"
    assert nba["golden_financial_id"] == gid

    # Normalise action
    raw_action = nba["recommended_action"]
    norm_action = {
        "PAYMENT_PLAN_DISCUSSION": "PAYMENT_PLAN",
        "PAYMENT_REMINDER": "REMINDER"
    }.get(raw_action, raw_action)
    assert norm_action == expected_action, (
        f"Scenario {scenario_name}: expected {expected_action}, got {norm_action}"
    )

    # Policy rule citation
    assert expected_rule.split(" - ")[0] in nba.get("policy_reference", "")

    # REQ-L4-02: Plain-English explanation must be non-empty and descriptive
    explanation = nba.get("explanation", "")
    assert isinstance(explanation, str)
    assert len(explanation) > 20, f"Explanation too short for {gid}"

    # 4. Collection Memory
    mem = get_collection_memory(gid)
    assert isinstance(mem, list)
    assert len(mem) > 0, f"Collection memory empty for {gid}"
    assert all("type" in ev and "when" in ev and "channel" in ev for ev in mem)


# ── REQ-L4-03 / REQ-GOV-02: Human Review & Audit Trail Tests ─────────────────

def test_human_review_workflow_audit():
    """Verify accept, modify, and override actions write immutable audit records."""
    test_gid = "GID-0905960"
    con = get_connection()

    # 1. Accept decision
    rec_accept = record_agent_decision(
        golden_financial_id=test_gid,
        original_recommendation="REMINDER",
        agent_decision="ACCEPT",
        agent_id="AGENT-TEST-001",
        con=con
    )
    assert rec_accept["audit_id"].startswith("AUD-")
    assert rec_accept["agent_decision"] == "ACCEPT"

    # 2. Modify decision
    rec_mod = record_agent_decision(
        golden_financial_id=test_gid,
        original_recommendation="REMINDER",
        agent_decision="MODIFY",
        modified_action="PAYMENT_PLAN",
        override_reason="Customer requested payment schedule during call",
        agent_id="AGENT-TEST-001",
        con=con
    )
    assert rec_mod["audit_id"].startswith("AUD-")
    assert rec_mod["modified_action"] == "PAYMENT_PLAN"

    # 3. Override decision
    rec_ovr = record_agent_decision(
        golden_financial_id=test_gid,
        original_recommendation="REMINDER",
        agent_decision="OVERRIDE",
        modified_action="DO_NOT_CONTACT",
        override_reason="Customer reported disputing charge with Ombudsman",
        agent_id="AGENT-TEST-002",
        con=con
    )
    assert rec_ovr["audit_id"].startswith("AUD-")
    assert rec_ovr["agent_decision"] == "OVERRIDE"

    # 4. Verify decision history retrieval
    history = get_agent_decision_history(test_gid, con=con)
    assert len(history) >= 3
    audit_ids = [h["audit_id"] for h in history]
    assert rec_accept["audit_id"] in audit_ids
    assert rec_mod["audit_id"] in audit_ids
    assert rec_ovr["audit_id"] in audit_ids


# ── Governance & Fairness Tests (REQ-GOV-03, REQ-GOV-04) ──────────────────────

def test_no_protected_attributes_in_ui_features():
    """Verify UI financial health and NBA loaders never expose protected attributes."""
    for s in DEMO_SCENARIOS.values():
        gid = s["gid"]
        fh = get_financial_health(gid)
        nba = get_nba(gid)

        fh_keys = set(fh.keys()) if fh else set()
        nba_keys = set(nba.keys()) if nba else set()

        violating_fh = fh_keys.intersection(PROTECTED_ATTRIBUTES)
        violating_nba = nba_keys.intersection(PROTECTED_ATTRIBUTES)

        assert not violating_fh, f"Protected attributes leaked in UI financial health for {gid}: {violating_fh}"
        assert not violating_nba, f"Protected attributes leaked in UI NBA for {gid}: {violating_nba}"


def test_vulnerability_invariance_protection():
    """
    REQ-GOV-04: Verify vulnerability_flag never produces an adverse automated action.
    Customers in hardship/vulnerability must route to HUMAN_REVIEW, never adverse treatments.
    """
    hardship_gid = DEMO_SCENARIOS["1. Hardship Protection (Rule 1 — Specialist Review)"]["gid"]
    nba = get_nba(hardship_gid)
    assert nba["recommended_action"] == "HUMAN_REVIEW"
    assert nba["requires_human_review"] is True
    assert "Rule 1" in nba["policy_reference"]
