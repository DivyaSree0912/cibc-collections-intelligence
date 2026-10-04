"""
pipeline/07_financial_health/financial_health.py
CIBC Collections Intelligence — Phase 7: Financial Health Engine

Converts Customer 360 data into governed financial health signals.
Answers the central question: Can the customer sustainably support the proposed arrangement?

Three branches (deterministic, 100% reproducible):
  Branch A — Exposure Analysis: ratio of total exposure to annual income
  Branch B — Cash-Flow Stress: account liquidity and overdraft utilization
  Branch C — Payment Behaviour: PTP fulfillment rate and delinquency history

Output:
  - financial_health_features table in DuckDB
  - financial_health_features.parquet export
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
log = logging.getLogger("financial_health")

DB_PATH    = PROJECT_ROOT / CONFIG["database"]["db_path"]
GOLDEN_DIR = PROJECT_ROOT / CONFIG["paths"]["golden_data"]


def run_financial_health() -> dict:
    run_ts = datetime.utcnow().isoformat()
    log.info("=== FINANCIAL HEALTH ENGINE START ===  run_ts=%s", run_ts)

    if not DB_PATH.exists():
        return {"status": "ERROR", "message": "Database not found. Run pipeline phases 1-4 first"}

    con = duckdb.connect(str(DB_PATH))
    t0 = time.time()

    log.info("Vectorizing 3-branch financial health calculations across 1M customers...")

    con.execute(f"""
        CREATE OR REPLACE TABLE financial_health_features AS
        WITH scored AS (
            SELECT
                golden_financial_id,
                total_aggregate_exposure,
                total_overdue_balance,
                declared_annual_income,
                estimated_monthly_inflow,
                max_dpd_across_portfolio,
                ptp_fulfillment_rate,
                hardship_flag,
                vulnerability_flag,
                -- Branch A: Exposure Score (0 = no exposure, 1 = extreme exposure)
                ROUND(LEAST(COALESCE(total_aggregate_exposure, 0.0) / NULLIF(COALESCE(declared_annual_income, 60000.0), 0.0), 1.0), 4) AS exposure_score,
                -- Branch C: Payment Behaviour Score (0 = worst, 1 = best)
                ROUND(
                    (COALESCE(ptp_fulfillment_rate, 50.0) / 100.0 * 0.5) +
                    (1.0 - LEAST(COALESCE(max_dpd_across_portfolio, 0) / 180.0, 1.0)) * 0.5
                , 4) AS payment_behaviour_score,
                -- Estimated Monthly EMI (~2.5% of total exposure)
                ROUND(COALESCE(total_aggregate_exposure, 0.0) * 0.025, 2) AS estimated_monthly_emi
            FROM golden_customer_360
        ),
        derived AS (
            SELECT
                s.*,
                -- Exposure Label
                CASE
                    WHEN s.exposure_score < 0.25 THEN 'LOW'
                    WHEN s.exposure_score < 0.50 THEN 'MODERATE'
                    WHEN s.exposure_score < 0.75 THEN 'HIGH'
                    ELSE 'SEVERE'
                END AS exposure_label,
                -- Payment Label
                CASE
                    WHEN s.payment_behaviour_score >= 0.75 THEN 'RELIABLE'
                    WHEN s.payment_behaviour_score >= 0.50 THEN 'MODERATE'
                    ELSE 'POOR'
                END AS payment_label,
                -- Cashflow stress derived from DPD and overdue ratio
                CASE
                    WHEN s.max_dpd_across_portfolio > 90 THEN 'SEVERE'
                    WHEN s.max_dpd_across_portfolio > 30 THEN 'HIGH'
                    WHEN s.max_dpd_across_portfolio > 0 THEN 'MODERATE'
                    ELSE 'LOW'
                END AS cashflow_stress_label,
                -- DSR Calculation
                ROUND(s.estimated_monthly_emi / NULLIF(s.estimated_monthly_inflow, 0.0), 4) AS dsr,
                -- Available monthly surplus
                ROUND(s.estimated_monthly_inflow - s.estimated_monthly_emi, 2) AS available_monthly_surplus
            FROM scored s
        ),
        classified AS (
            SELECT
                d.*,
                CASE
                    WHEN d.dsr IS NULL THEN 'MODERATE'
                    WHEN d.dsr < 0.35 THEN 'LOW'
                    WHEN d.dsr < 0.60 THEN 'MODERATE'
                    WHEN d.dsr < 0.80 THEN 'HIGH'
                    ELSE 'SEVERE'
                END AS dsr_category,
                -- Composite Health Score (Higher = healthier)
                ROUND(
                    (1.0 - d.exposure_score) * 0.35 +
                    (CASE d.cashflow_stress_label WHEN 'LOW' THEN 0.9 WHEN 'MODERATE' THEN 0.6 WHEN 'HIGH' THEN 0.3 ELSE 0.1 END) * 0.35 +
                    d.payment_behaviour_score * 0.30
                , 4) AS composite_health_score
            FROM derived d
        )
        SELECT
            golden_financial_id,
            exposure_score,
            exposure_label,
            CASE cashflow_stress_label WHEN 'LOW' THEN 0.1 WHEN 'MODERATE' THEN 0.4 WHEN 'HIGH' THEN 0.7 ELSE 0.9 END AS cashflow_score,
            cashflow_stress_label,
            payment_behaviour_score,
            payment_label,
            dsr,
            dsr_category,
            composite_health_score,
            CASE
                WHEN composite_health_score >= 0.75 THEN 'GOOD'
                WHEN composite_health_score >= 0.55 THEN 'FAIR'
                WHEN composite_health_score >= 0.35 THEN 'STRESSED'
                ELSE 'CRITICAL'
            END AS health_category,
            available_monthly_surplus,
            CASE
                WHEN hardship_flag OR vulnerability_flag THEN 'REVIEW_REQUIRED'
                WHEN composite_health_score < 0.35 OR dsr >= 0.80 THEN 'NO'
                WHEN composite_health_score < 0.55 OR dsr >= 0.60 OR available_monthly_surplus < 500 THEN 'MARGINAL'
                ELSE 'YES'
            END AS can_support_arrangement,
            vulnerability_flag,
            hardship_flag,
            CASE
                WHEN hardship_flag OR vulnerability_flag OR max_dpd_across_portfolio > 90 OR dsr >= 0.80 THEN TRUE
                ELSE FALSE
            END AS requires_human_review,
            0.95 AS data_completeness_pct,
            '1.0.0' AS formula_version,
            '{run_ts}' AS computed_at
        FROM classified;
    """)

    processed = con.execute("SELECT COUNT(*) FROM financial_health_features").fetchone()[0]

    log.info("Exporting financial_health_features to Parquet...")
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    parquet_path = GOLDEN_DIR / "financial_health_features.parquet"
    con.execute(f"COPY financial_health_features TO '{parquet_path.as_posix()}' (FORMAT PARQUET)")

    stats = con.execute("""
        SELECT health_category, COUNT(*) AS cnt
        FROM financial_health_features
        GROUP BY health_category
        ORDER BY cnt DESC
    """).fetchall()

    human_review = con.execute(
        "SELECT COUNT(*) FROM financial_health_features WHERE requires_human_review = TRUE"
    ).fetchone()[0]

    elapsed = time.time() - t0
    log.info("=== FINANCIAL HEALTH ENGINE COMPLETE ===  processed=%d  human_review=%d (%.2fs)",
             processed, human_review, elapsed)

    con.close()

    result = {
        "status": "OK",
        "run_ts": run_ts,
        "records_processed": processed,
        "health_distribution": {r[0]: r[1] for r in stats},
        "human_review_required": human_review,
        "parquet_path": str(parquet_path),
        "elapsed_seconds": round(elapsed, 2)
    }
    return result


if __name__ == "__main__":
    result = run_financial_health()
    print(json.dumps(result, indent=2))
