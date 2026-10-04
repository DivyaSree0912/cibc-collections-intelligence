"""
pipeline/08_nba/next_best_action.py
CIBC Collections Intelligence — Phase 8: Policy-Constrained Next Best Action

Determines the policy-compliant recommended action for each customer in collections.
Enforces the 5 non-negotiable policy rules:
  Rule 1: Hardship / Vulnerability always routes to specialist review (Protection, not adverse treatment)
  Rule 2: DPD > 90 days requires senior escalation / human review
  Rule 3: Unsustainable financial position (cannot support payment) routes to human review
  Rule 4: Marginal financial position routes to tailored payment plan discussion
  Rule 5: Early stage (DPD <= 30) with GOOD/FAIR health receives digital reminder

Governance & Features:
  - Reuses the governed Feature Store (customer_features) as the source of features.
  - Zero protected demographic or geographic attributes (REQ-GOV-03).
  - Deterministic calculations of record (REQ-GOV-06).
  - Auditable human review tracking for Accept, Modify, and Override actions (REQ-L4-03, REQ-GOV-02).

Outputs:
  - DuckDB table: nba_recommendations
  - DuckDB table: agent_decisions_audit
  - Parquet export: data/golden/nba_recommendations.parquet
"""

import duckdb
import yaml
import logging
import json
import time
import uuid
import importlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
with open(PROJECT_ROOT / "config" / "pipeline_config.yaml") as f:
    CONFIG = yaml.safe_load(f)

logging.basicConfig(level=CONFIG["logging"]["level"], format=CONFIG["logging"]["format"])
log = logging.getLogger("nba")

DB_PATH = PROJECT_ROOT / CONFIG["database"]["db_path"]
GOLDEN_DIR = PROJECT_ROOT / CONFIG["paths"]["golden_data"]
AUDIT_LOG_FILE = PROJECT_ROOT / "logs" / "agent_decisions_audit.jsonl"
POLICY_VER = "MAPLE-NBA-POL-1.0"

_fs_mod = importlib.import_module("pipeline.06_features.feature_store")
assert_no_protected_attributes = _fs_mod.assert_no_protected_attributes


def init_audit_table(con: duckdb.DuckDBPyConnection) -> None:
    """Initializes the persistent agent decisions audit table in DuckDB."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS agent_decisions_audit (
            audit_id VARCHAR PRIMARY KEY,
            golden_financial_id VARCHAR,
            original_recommendation VARCHAR,
            agent_decision VARCHAR,
            modified_action VARCHAR,
            override_reason VARCHAR,
            agent_id VARCHAR,
            decided_at VARCHAR
        )
    """)


def record_agent_decision(
    golden_financial_id: str,
    original_recommendation: str,
    agent_decision: str,
    modified_action: Optional[str] = None,
    override_reason: Optional[str] = None,
    agent_id: str = "AGENT-COL-001",
    con: Optional[duckdb.DuckDBPyConnection] = None
) -> Dict[str, Any]:
    """
    Auditable Human Review & Override Recording (REQ-L4-03 & REQ-GOV-02).
    Records agent actions (ACCEPT, MODIFY, OVERRIDE) to both DuckDB and JSONL audit trail.
    """
    close_on_exit = False
    if con is None:
        con = duckdb.connect(str(DB_PATH))
        close_on_exit = True

    init_audit_table(con)

    audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
    ts = datetime.now(timezone.utc).isoformat()
    norm_decision = agent_decision.upper().strip()

    if norm_decision not in ("ACCEPT", "MODIFY", "OVERRIDE"):
        raise ValueError(f"Invalid agent decision '{agent_decision}'. Must be ACCEPT, MODIFY, or OVERRIDE.")

    if norm_decision == "OVERRIDE" and not override_reason:
        raise ValueError("Override reason is mandatory when overriding a policy-constrained recommendation.")

    con.execute("""
        INSERT INTO agent_decisions_audit VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        audit_id,
        golden_financial_id,
        original_recommendation,
        norm_decision,
        modified_action or original_recommendation,
        override_reason or "N/A",
        agent_id,
        ts
    ])

    record = {
        "audit_id": audit_id,
        "golden_financial_id": golden_financial_id,
        "original_recommendation": original_recommendation,
        "agent_decision": norm_decision,
        "modified_action": modified_action or original_recommendation,
        "override_reason": override_reason,
        "agent_id": agent_id,
        "decided_at": ts
    }

    # Write to append-only JSONL audit log
    AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    log.info("Agent decision recorded: %s on %s by %s (Audit ID: %s)",
             norm_decision, golden_financial_id, agent_id, audit_id)

    if close_on_exit:
        con.close()
    return record


def get_agent_decision_history(
    golden_financial_id: str,
    con: Optional[duckdb.DuckDBPyConnection] = None
) -> List[Dict[str, Any]]:
    """Retrieves all historical human review actions for a customer."""
    close_on_exit = False
    if con is None:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        close_on_exit = True

    try:
        rows = con.execute("""
            SELECT audit_id, golden_financial_id, original_recommendation,
                   agent_decision, modified_action, override_reason, agent_id, decided_at
            FROM agent_decisions_audit
            WHERE golden_financial_id = ?
            ORDER BY decided_at DESC
        """, [golden_financial_id]).fetchall()
    except Exception:
        rows = []

    cols = [
        "audit_id", "golden_financial_id", "original_recommendation",
        "agent_decision", "modified_action", "override_reason", "agent_id", "decided_at"
    ]
    history = [dict(zip(cols, r)) for r in rows]

    if close_on_exit:
        con.close()
    return history


def evaluate_nba(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Online evaluation engine for Next Best Action (REQ-L4-01).
    Evaluates policy rules over a single customer's governed feature vector.
    """
    hardship = bool(features.get("hardship_flag") or False)
    vuln = bool(features.get("vulnerability_flag") or False)
    max_dpd = int(features.get("max_dpd_across_portfolio") or 0)
    can_support = str(features.get("can_support_arrangement") or "YES")
    health = str(features.get("health_category") or "GOOD")
    dsr_cat = str(features.get("dsr_category") or "LOW")
    overdue = float(features.get("total_overdue_balance") or 0.0)

    # 5 Non-Negotiable Policy Rules
    if hardship or vuln:
        action = "HUMAN_REVIEW"
        policy = f"{POLICY_VER} / Rule 1 - Hardship Protection"
        explanation = (
            "Hardship or vulnerability signal detected. Policy requires protective routing "
            "to specialist review prior to any collections treatment."
        )
        requires_review = True
        eligible = ["HUMAN_REVIEW"]
    elif max_dpd > 90:
        action = "HUMAN_REVIEW"
        policy = f"{POLICY_VER} / Rule 2 - High DPD Escalation"
        explanation = (
            "Account delinquency exceeds the 90-day threshold. Requires specialist agent "
            "evaluation and formal review."
        )
        requires_review = True
        eligible = ["HUMAN_REVIEW"]
    elif can_support == "NO":
        action = "HUMAN_REVIEW"
        policy = f"{POLICY_VER} / Rule 3 - Sustainability Gate"
        explanation = (
            "Customer financial capacity indicates inability to support standard repayment. "
            "Routed to specialist for forbearance or hardship assistance."
        )
        requires_review = True
        eligible = ["HUMAN_REVIEW", "PAYMENT_PLAN"]
    elif can_support == "MARGINAL" or health in ("STRESSED", "CRITICAL"):
        action = "PAYMENT_PLAN"
        policy = f"{POLICY_VER} / Rule 4 - Affordability-Led Plan"
        explanation = (
            "Customer capacity is tight or stressed. Recommend structured, affordable "
            "step-up payment plan verified against monthly surplus."
        )
        requires_review = True
        eligible = ["PAYMENT_PLAN", "HUMAN_REVIEW"]
    elif max_dpd <= 30 and health in ("GOOD", "FAIR"):
        action = "REMINDER"
        policy = f"{POLICY_VER} / Rule 5 - Early-Stage Reminder"
        explanation = (
            "Early-stage delinquency with positive financial health profile. Automated digital "
            "reminder is least intrusive and appropriate."
        )
        requires_review = False
        eligible = ["REMINDER", "PAYMENT_PLAN", "HUMAN_REVIEW"]
    else:
        action = "HUMAN_REVIEW"
        policy = f"{POLICY_VER} / Rule 0 - Default Safety"
        explanation = "Default safety rule applied: specialist review recommended."
        requires_review = True
        eligible = ["HUMAN_REVIEW"]

    evidence = [
        f"dpd={max_dpd}",
        f"health={health}",
        f"dsr={dsr_cat}",
        f"hardship={str(hardship).lower()}",
        f"overdue={round(overdue, 2)}"
    ]

    return {
        "recommended_action": action,
        "policy_reference": policy,
        "requires_human_review": requires_review,
        "explanation": explanation,
        "evidence": evidence,
        "eligible_actions": eligible,
        "confidence": "HIGH",
        "policy_version": POLICY_VER,
        "computed_at": datetime.now(timezone.utc).isoformat()
    }


def run_nba() -> dict:
    """
    Executes Phase 8: Policy-Constrained Next Best Action engine.
    Joins golden_customer_360 with the governed customer_features table.
    """
    run_ts = datetime.now(timezone.utc).isoformat()
    log.info("=== NBA ENGINE START ===  run_ts=%s", run_ts)

    if not DB_PATH.exists():
        return {"status": "ERROR", "message": "Database not found."}

    con = duckdb.connect(str(DB_PATH))
    t0 = time.time()

    # Initialize audit infrastructure
    init_audit_table(con)

    # Validate that no protected attributes are used in NBA logic
    nba_candidate_cols = [
        "golden_financial_id", "resolved_name", "preferred_phone",
        "max_dpd_across_portfolio", "total_overdue_balance", "active_collections_cases",
        "current_queue", "last_contact_channel", "health_category", "dsr_category",
        "composite_health_score", "can_support_arrangement", "available_monthly_surplus",
        "vulnerability_flag", "hardship_flag"
    ]
    assert_no_protected_attributes(nba_candidate_cols)
    log.info("Governance verified: zero protected attributes in NBA candidate features.")

    log.info("Applying 5 policy rules using governed Feature Store across collections customers...")

    con.execute(f"""
        CREATE OR REPLACE TABLE nba_recommendations AS
        WITH active_candidates AS (
            SELECT
                c.golden_financial_id,
                c.resolved_name,
                c.preferred_phone,
                f.max_dpd_across_portfolio,
                f.total_overdue_balance,
                f.active_collections_cases,
                c.current_queue,
                c.last_contact_channel,
                f.health_category,
                f.dsr_category,
                f.composite_health_score,
                f.can_support_arrangement,
                f.available_monthly_surplus,
                f.vulnerability_flag,
                f.hardship_flag,
                f.requires_human_review AS feature_review
            FROM golden_customer_360 c
            JOIN customer_features f ON c.golden_financial_id = f.golden_financial_id
            WHERE f.active_collections_cases > 0
        )
        SELECT
            golden_financial_id,
            resolved_name,
            preferred_phone,
            max_dpd_across_portfolio,
            total_overdue_balance,
            health_category,
            dsr_category,
            can_support_arrangement,
            -- Recommended Action
            CASE
                -- Rule 1: Hardship / Vulnerability
                WHEN hardship_flag OR vulnerability_flag THEN 'HUMAN_REVIEW'
                -- Rule 2: High DPD (>90)
                WHEN max_dpd_across_portfolio > 90 THEN 'HUMAN_REVIEW'
                -- Rule 3: Cannot support arrangement
                WHEN can_support_arrangement = 'NO' THEN 'HUMAN_REVIEW'
                -- Rule 4: Marginal / Stressed capacity
                WHEN can_support_arrangement = 'MARGINAL' OR health_category IN ('STRESSED', 'CRITICAL') THEN 'PAYMENT_PLAN'
                -- Rule 5: Early stage + healthy
                WHEN max_dpd_across_portfolio <= 30 AND health_category IN ('GOOD', 'FAIR') THEN 'REMINDER'
                ELSE 'HUMAN_REVIEW'
            END AS recommended_action,

            -- Policy Reference
            CASE
                WHEN hardship_flag OR vulnerability_flag THEN '{POLICY_VER} / Rule 1 - Hardship Protection'
                WHEN max_dpd_across_portfolio > 90 THEN '{POLICY_VER} / Rule 2 - High DPD Escalation'
                WHEN can_support_arrangement = 'NO' THEN '{POLICY_VER} / Rule 3 - Sustainability Gate'
                WHEN can_support_arrangement = 'MARGINAL' OR health_category IN ('STRESSED', 'CRITICAL') THEN '{POLICY_VER} / Rule 4 - Affordability-Led Plan'
                WHEN max_dpd_across_portfolio <= 30 AND health_category IN ('GOOD', 'FAIR') THEN '{POLICY_VER} / Rule 5 - Early-Stage Reminder'
                ELSE '{POLICY_VER} / Rule 0 - Default Safety'
            END AS policy_reference,

            -- Human Review Flag
            CASE
                WHEN hardship_flag OR vulnerability_flag OR max_dpd_across_portfolio > 90 OR can_support_arrangement IN ('NO', 'REVIEW_REQUIRED') THEN TRUE
                WHEN can_support_arrangement = 'MARGINAL' THEN TRUE
                ELSE FALSE
            END AS requires_human_review,

            -- Plain-English Explanation
            CASE
                WHEN hardship_flag OR vulnerability_flag THEN
                    'Hardship or vulnerability signal detected. Policy requires protective routing to specialist review prior to any collections treatment.'
                WHEN max_dpd_across_portfolio > 90 THEN
                    'Account delinquency exceeds the 90-day threshold. Requires specialist agent evaluation and formal review.'
                WHEN can_support_arrangement = 'NO' THEN
                    'Customer financial capacity indicates inability to support standard repayment. Routed to specialist for forbearance or hardship assistance.'
                WHEN can_support_arrangement = 'MARGINAL' OR health_category IN ('STRESSED', 'CRITICAL') THEN
                    'Customer capacity is tight or stressed. Recommend structured, affordable step-up payment plan verified against monthly surplus.'
                WHEN max_dpd_across_portfolio <= 30 AND health_category IN ('GOOD', 'FAIR') THEN
                    'Early-stage delinquency with positive financial health profile. Automated digital reminder is least intrusive and appropriate.'
                ELSE 'Default safety rule applied: specialist review recommended.'
            END AS explanation,

            -- Evidence JSON Array
            '[' ||
                '"dpd=' || CAST(max_dpd_across_portfolio AS VARCHAR) || '", ' ||
                '"health=' || health_category || '", ' ||
                '"dsr=' || dsr_category || '", ' ||
                '"hardship=' || LOWER(CAST(hardship_flag AS VARCHAR)) || '", ' ||
                '"overdue=' || CAST(ROUND(total_overdue_balance, 2) AS VARCHAR) || '"' ||
            ']' AS evidence,

            -- Eligible Actions JSON
            CASE
                WHEN hardship_flag OR vulnerability_flag THEN '["HUMAN_REVIEW"]'
                WHEN max_dpd_across_portfolio > 90 THEN '["HUMAN_REVIEW"]'
                WHEN can_support_arrangement = 'NO' THEN '["HUMAN_REVIEW", "PAYMENT_PLAN"]'
                WHEN can_support_arrangement = 'MARGINAL' THEN '["PAYMENT_PLAN", "HUMAN_REVIEW"]'
                ELSE '["REMINDER", "PAYMENT_PLAN", "HUMAN_REVIEW"]'
            END AS eligible_actions,

            'HIGH' AS confidence,
            '{POLICY_VER}' AS policy_version,
            '{run_ts}' AS computed_at
        FROM active_candidates;
    """)

    total_nba = con.execute("SELECT COUNT(*) FROM nba_recommendations").fetchone()[0]

    log.info("Exporting nba_recommendations to Parquet...")
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    parquet_path = GOLDEN_DIR / "nba_recommendations.parquet"
    con.execute(f"COPY nba_recommendations TO '{parquet_path.as_posix()}' (FORMAT PARQUET)")

    dist = con.execute("""
        SELECT recommended_action, COUNT(*) AS cnt
        FROM nba_recommendations
        GROUP BY recommended_action
        ORDER BY cnt DESC
    """).fetchall()

    human_reviews = con.execute("SELECT COUNT(*) FROM nba_recommendations WHERE requires_human_review = TRUE").fetchone()[0]

    elapsed = time.time() - t0
    log.info("=== NBA ENGINE COMPLETE ===  total=%d  human_reviews=%d (%.2fs)",
             total_nba, human_reviews, elapsed)

    con.close()

    result = {
        "status": "OK",
        "run_ts": run_ts,
        "total_recommendations": total_nba,
        "action_distribution": {r[0]: r[1] for r in dist},
        "human_review_required": human_reviews,
        "parquet_path": str(parquet_path),
        "elapsed_seconds": round(elapsed, 2)
    }
    return result


def get_nba_for_customer(golden_id: str, con: Optional[duckdb.DuckDBPyConnection] = None) -> dict:
    """Retrieves the full NBA recommendation for a customer."""
    close_on_exit = False
    if con is None:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        close_on_exit = True

    row = con.execute("""
        SELECT recommended_action, policy_reference, requires_human_review,
               explanation, evidence, eligible_actions, confidence, computed_at
        FROM nba_recommendations
        WHERE golden_financial_id = ?
        LIMIT 1
    """, [golden_id]).fetchone()

    if close_on_exit:
        con.close()

    if not row:
        return {"error": f"No recommendation found for {golden_id}"}

    return {
        "golden_financial_id": golden_id,
        "recommended_action": row[0],
        "policy_reference": row[1],
        "requires_human_review": row[2],
        "explanation": row[3],
        "evidence": json.loads(row[4]) if row[4] else [],
        "eligible_actions": json.loads(row[5]) if row[5] else [],
        "confidence": row[6],
        "computed_at": row[7]
    }


if __name__ == "__main__":
    result = run_nba()
    print(json.dumps(result, indent=2))
