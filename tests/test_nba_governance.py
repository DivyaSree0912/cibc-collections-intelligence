"""
tests/test_nba_governance.py
CIBC Collections Intelligence — NBA & Governance Validation Test Suite

Validates:
  - REQ-L4-01: Working NBA model/agent
  - REQ-L4-02: Plain-English explanation per decision
  - REQ-L4-03: Human review / override point
  - REQ-GOV-01: Plain-English reason for every agent-facing decision
  - REQ-GOV-02: Human review for anything affecting a customer
  - REQ-GOV-03: No protected attributes in decisions
  - REQ-GOV-04: Hardship flags
  - REQ-GOV-05: Low-confidence matches are not silently merged
  - REQ-GOV-07: AI must not invent customer facts (grounded evidence)
"""

import duckdb
import pytest
import json
import importlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "maple_collections.duckdb"

_nba_mod = importlib.import_module("pipeline.08_nba.next_best_action")
run_nba = _nba_mod.run_nba
get_nba_for_customer = _nba_mod.get_nba_for_customer
evaluate_nba = _nba_mod.evaluate_nba
record_agent_decision = _nba_mod.record_agent_decision
get_agent_decision_history = _nba_mod.get_agent_decision_history
assert_no_protected_attributes = _nba_mod.assert_no_protected_attributes


@pytest.fixture(scope="module")
def db_con():
    assert DB_PATH.exists(), f"Database not found at {DB_PATH}"
    con = duckdb.connect(str(DB_PATH))
    yield con
    con.close()


# ─── REQ-L4-01: Working NBA Model / Agent ─────────────────────────────────────────

def test_nba_recommendations_coverage_and_validity(db_con):
    """Test that all active collections cases have a policy-constrained recommendation."""
    total_recs = db_con.execute("SELECT COUNT(*) FROM nba_recommendations").fetchone()[0]
    assert total_recs > 50000, f"Expected >50K recommendations, found {total_recs}"

    # Verify action values are strictly within policy vocabulary
    actions = [r[0] for r in db_con.execute(
        "SELECT DISTINCT recommended_action FROM nba_recommendations"
    ).fetchall()]
    assert set(actions).issubset({"HUMAN_REVIEW", "PAYMENT_PLAN", "REMINDER"}), (
        f"Invalid actions found: {actions}"
    )

    # Verify no nulls in required fields
    nulls = db_con.execute("""
        SELECT COUNT(*) FROM nba_recommendations
        WHERE golden_financial_id IS NULL
           OR recommended_action IS NULL
           OR policy_reference IS NULL
           OR explanation IS NULL
           OR evidence IS NULL
           OR confidence IS NULL
           OR requires_human_review IS NULL
           OR computed_at IS NULL
    """).fetchone()[0]
    assert nulls == 0, f"Found {nulls} records with missing required fields"


def test_online_nba_evaluation():
    """Test real-time evaluation function (evaluate_nba) produces valid decisions."""
    # Test early stage customer
    sample_features = {
        "max_dpd_across_portfolio": 15,
        "health_category": "GOOD",
        "dsr_category": "LOW",
        "hardship_flag": False,
        "vulnerability_flag": False,
        "can_support_arrangement": "YES",
        "total_overdue_balance": 450.0
    }
    decision = evaluate_nba(sample_features)
    assert decision["recommended_action"] == "REMINDER"
    assert decision["requires_human_review"] is False
    assert "Rule 5" in decision["policy_reference"]
    assert len(decision["explanation"]) > 20
    assert "dpd=15" in decision["evidence"]


# ─── REQ-L4-02 & REQ-GOV-01: Plain-English Explanations ───────────────────────────

def test_plain_english_explanations_exist(db_con):
    """Test REQ-L4-02 & REQ-GOV-01: 100% of decisions include meaningful plain-English explanations."""
    short_explanations = db_con.execute("""
        SELECT COUNT(*) FROM nba_recommendations
        WHERE explanation IS NULL OR LENGTH(TRIM(explanation)) < 25
    """).fetchone()[0]
    assert short_explanations == 0, f"Found {short_explanations} decisions with deficient explanations"

    # Verify policy references exist on all rows
    missing_policy = db_con.execute("""
        SELECT COUNT(*) FROM nba_recommendations
        WHERE policy_reference IS NULL OR LENGTH(TRIM(policy_reference)) < 5
    """).fetchone()[0]
    assert missing_policy == 0, f"Found {missing_policy} decisions missing policy references"


# ─── REQ-L4-03 & REQ-GOV-02: Human Review and Override Mechanism ──────────────────

def test_human_review_triggers(db_con):
    """Test REQ-GOV-02: Human review is mandatory for all high-risk, vulnerable, or payment-plan cases."""
    # Hardship / Vulnerability must require human review
    unflagged_hardship = db_con.execute("""
        SELECT COUNT(*) FROM nba_recommendations r
        JOIN customer_features f ON r.golden_financial_id = f.golden_financial_id
        WHERE (f.hardship_flag = TRUE OR f.vulnerability_flag = TRUE)
          AND r.requires_human_review = FALSE
    """).fetchone()[0]
    assert unflagged_hardship == 0, f"Found {unflagged_hardship} hardship/vulnerability cases bypassing human review"

    # DPD > 90 must require human review
    unflagged_dpd = db_con.execute("""
        SELECT COUNT(*) FROM nba_recommendations
        WHERE max_dpd_across_portfolio > 90 AND requires_human_review = FALSE
    """).fetchone()[0]
    assert unflagged_dpd == 0, f"Found {unflagged_dpd} DPD > 90 cases bypassing human review"

    # Payment plans must require agent review before presentation
    unflagged_plans = db_con.execute("""
        SELECT COUNT(*) FROM nba_recommendations
        WHERE recommended_action = 'PAYMENT_PLAN' AND requires_human_review = FALSE
    """).fetchone()[0]
    assert unflagged_plans == 0, f"Found {unflagged_plans} payment plans bypassing agent review"


def test_agent_decision_audit_trail(db_con):
    """Test REQ-L4-03: Accept, Modify, and Override actions are recorded in DuckDB and auditable."""
    test_gid = "GID-TEST-AUDIT-001"

    # 1. Test Accept
    rec_accept = record_agent_decision(
        golden_financial_id=test_gid,
        original_recommendation="PAYMENT_PLAN",
        agent_decision="ACCEPT",
        agent_id="AGENT-COL-999",
        con=db_con
    )
    assert rec_accept["agent_decision"] == "ACCEPT"
    assert rec_accept["audit_id"].startswith("AUD-")

    # 2. Test Modify
    rec_modify = record_agent_decision(
        golden_financial_id=test_gid,
        original_recommendation="PAYMENT_PLAN",
        agent_decision="MODIFY",
        modified_action="HUMAN_REVIEW",
        override_reason="Customer requested telephone interview",
        agent_id="AGENT-COL-999",
        con=db_con
    )
    assert rec_modify["agent_decision"] == "MODIFY"
    assert rec_modify["modified_action"] == "HUMAN_REVIEW"

    # 3. Test Override requires reason
    with pytest.raises(ValueError):
        record_agent_decision(
            golden_financial_id=test_gid,
            original_recommendation="REMINDER",
            agent_decision="OVERRIDE",
            override_reason="",  # empty reason should fail
            con=db_con
        )

    # 4. Test Valid Override
    rec_override = record_agent_decision(
        golden_financial_id=test_gid,
        original_recommendation="REMINDER",
        agent_decision="OVERRIDE",
        modified_action="DO_NOT_CONTACT",
        override_reason="Customer in bankruptcy proceedings",
        agent_id="AGENT-COL-999",
        con=db_con
    )
    assert rec_override["agent_decision"] == "OVERRIDE"
    assert rec_override["override_reason"] == "Customer in bankruptcy proceedings"

    # 5. Retrieve history
    history = get_agent_decision_history(test_gid, con=db_con)
    assert len(history) >= 3
    decisions = [h["agent_decision"] for h in history]
    assert "ACCEPT" in decisions
    assert "MODIFY" in decisions
    assert "OVERRIDE" in decisions


# ─── REQ-GOV-03: No Protected Attributes in Decisions ─────────────────────────────

def test_no_protected_attributes_in_nba(db_con):
    """Test REQ-GOV-03: Zero protected demographic or geographic attributes in NBA table or logic."""
    nba_cols = [r[0].lower() for r in db_con.execute("DESCRIBE nba_recommendations").fetchall()]
    prohibited = [
        "gender", "gender_code", "sex", "marital_status", "citizenship",
        "citizenship_status", "race", "ethnicity", "religion", "household",
        "newcomer", "accessibility", "accent", "customer_fsa", "fsa", "postal_code"
    ]
    for col in prohibited:
        assert col not in nba_cols, f"Protected attribute '{col}' leaked into nba_recommendations!"


# ─── REQ-GOV-04: Hardship Flags & Protective Routing ──────────────────────────────

def test_hardship_routing_rule_1(db_con):
    """Test REQ-GOV-04: Hardship is strictly protective — 100% routes to HUMAN_REVIEW, never adverse action."""
    hardship_non_review = db_con.execute("""
        SELECT COUNT(*) FROM nba_recommendations r
        JOIN customer_features f ON r.golden_financial_id = f.golden_financial_id
        WHERE f.hardship_flag = TRUE AND r.recommended_action != 'HUMAN_REVIEW'
    """).fetchone()[0]
    assert hardship_non_review == 0, (
        f"Rule 1 violation: {hardship_non_review} hardship cases did not route to HUMAN_REVIEW"
    )

    # Verify policy reference explicitly cites Hardship Protection
    hardship_cases = db_con.execute("""
        SELECT policy_reference FROM nba_recommendations r
        JOIN customer_features f ON r.golden_financial_id = f.golden_financial_id
        WHERE f.hardship_flag = TRUE
        LIMIT 5
    """).fetchall()
    for (pol,) in hardship_cases:
        assert "Rule 1 - Hardship Protection" in pol, f"Incorrect policy reference: {pol}"


# ─── REQ-GOV-05: Low-Confidence Matches Not Silently Merged ───────────────────────

def test_low_confidence_matches_not_silently_merged(db_con):
    """Test REQ-GOV-05: Ambiguous identity links are routed to identity_review_queue, not silently merged."""
    tables = [r[0] for r in db_con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()]
    assert "identity_review_queue" in tables, "Missing identity_review_queue table"

    queue_count = db_con.execute("SELECT COUNT(*) FROM identity_review_queue").fetchone()[0]
    assert queue_count > 0, "Identity review queue is empty; low confidence links were not trapped"

    # Verify all records in queue have review_required or confidence < 0.85
    unqualified = db_con.execute("""
        SELECT COUNT(*) FROM identity_review_queue
        WHERE match_confidence >= 0.85 AND status != 'PENDING_STEWARD_REVIEW'
    """).fetchone()[0]
    assert unqualified == 0, f"Found {unqualified} invalid entries in identity review queue"


# ─── REQ-GOV-07: AI Must Not Invent Customer Facts (Grounded Evidence) ────────────

def test_evidence_grounded_in_actual_features(db_con):
    """Test REQ-GOV-07: Decision evidence arrays are strictly grounded in verified customer data."""
    sample = db_con.execute("""
        SELECT 
            r.golden_financial_id,
            r.evidence,
            f.max_dpd_across_portfolio,
            f.health_category,
            f.dsr_category,
            f.hardship_flag
        FROM nba_recommendations r
        JOIN customer_features f ON r.golden_financial_id = f.golden_financial_id
        LIMIT 100
    """).fetchall()

    for gid, ev_str, dpd, health, dsr, hardship in sample:
        evidence = json.loads(ev_str) if isinstance(ev_str, str) else ev_str
        ev_dict = dict(item.split("=") for item in evidence if "=" in item)

        # Grounding checks
        assert int(ev_dict.get("dpd", -1)) == dpd, f"Mismatched DPD in evidence for {gid}"
        assert ev_dict.get("health") == health, f"Mismatched health in evidence for {gid}"
        assert ev_dict.get("dsr") == dsr, f"Mismatched DSR in evidence for {gid}"
        assert ev_dict.get("hardship") == str(hardship).lower(), f"Mismatched hardship in evidence for {gid}"


def test_deterministic_nba_decisions():
    """Test REQ-GOV-06: NBA decisions are completely deterministic (identical output for identical inputs)."""
    features = {
        "max_dpd_across_portfolio": 45,
        "health_category": "STRESSED",
        "dsr_category": "MODERATE",
        "hardship_flag": False,
        "vulnerability_flag": False,
        "can_support_arrangement": "MARGINAL",
        "total_overdue_balance": 1850.50
    }
    run1 = evaluate_nba(features)
    run2 = evaluate_nba(features)

    # Exclude timestamp for bit-level match
    del run1["computed_at"]
    del run2["computed_at"]
    assert run1 == run2, "NBA decision logic is non-deterministic!"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
