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

Output:
  - nba_recommendations table in DuckDB
  - nba_recommendations.parquet export
"""

import duckdb
import yaml
import logging
import json
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
with open(PROJECT_ROOT / "config" / "pipeline_config.yaml") as f:
    CONFIG = yaml.safe_load(f)

logging.basicConfig(level=CONFIG["logging"]["level"], format=CONFIG["logging"]["format"])
log = logging.getLogger("nba")

DB_PATH    = PROJECT_ROOT / CONFIG["database"]["db_path"]
GOLDEN_DIR = PROJECT_ROOT / CONFIG["paths"]["golden_data"]
POLICY_VER = "MAPLE-NBA-POL-1.0"


def run_nba() -> dict:
    run_ts = datetime.utcnow().isoformat()
    log.info("=== NBA ENGINE START ===  run_ts=%s", run_ts)

    if not DB_PATH.exists():
        return {"status": "ERROR", "message": "Database not found."}

    con = duckdb.connect(str(DB_PATH))
    t0 = time.time()

    log.info("Applying 5 policy rules to evaluate Next Best Action across collections customers...")

    con.execute(f"""
        CREATE OR REPLACE TABLE nba_recommendations AS
        WITH active_candidates AS (
            SELECT
                c.golden_financial_id,
                c.resolved_name,
                c.preferred_phone,
                c.max_dpd_across_portfolio,
                c.total_overdue_balance,
                c.active_collections_cases,
                c.current_queue,
                c.last_contact_channel,
                fh.health_category,
                fh.dsr_category,
                fh.composite_health_score,
                fh.can_support_arrangement,
                fh.available_monthly_surplus,
                fh.vulnerability_flag,
                fh.hardship_flag,
                fh.requires_human_review AS fh_review
            FROM golden_customer_360 c
            JOIN financial_health_features fh ON c.golden_financial_id = fh.golden_financial_id
            WHERE c.active_collections_cases > 0
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
                WHEN hardship_flag OR vulnerability_flag THEN '{POLICY_VER} / Rule 1 — Hardship Protection'
                WHEN max_dpd_across_portfolio > 90 THEN '{POLICY_VER} / Rule 2 — High DPD Escalation'
                WHEN can_support_arrangement = 'NO' THEN '{POLICY_VER} / Rule 3 — Sustainability Gate'
                WHEN can_support_arrangement = 'MARGINAL' OR health_category IN ('STRESSED', 'CRITICAL') THEN '{POLICY_VER} / Rule 4 — Affordability-Led Plan'
                WHEN max_dpd_across_portfolio <= 30 AND health_category IN ('GOOD', 'FAIR') THEN '{POLICY_VER} / Rule 5 — Early-Stage Reminder'
                ELSE '{POLICY_VER} / Rule 0 — Default Safety'
            END AS policy_reference,

            -- Human Review Flag
            CASE
                WHEN hardship_flag OR vulnerability_flag OR max_dpd_across_portfolio > 90 OR can_support_arrangement IN ('NO', 'REVIEW_REQUIRED') THEN TRUE
                WHEN can_support_arrangement = 'MARGINAL' THEN TRUE -- Agent review of proposed plan
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
                '"hardship=' || CAST(hardship_flag AS VARCHAR) || '"' ||
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


def get_nba_for_customer(golden_id: str) -> dict:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    row = con.execute("""
        SELECT recommended_action, policy_reference, requires_human_review, explanation, evidence, eligible_actions, confidence, computed_at
        FROM nba_recommendations
        WHERE golden_financial_id = ?
        LIMIT 1
    """, [golden_id]).fetchone()
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
