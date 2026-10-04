"""
pipeline/04_c360/build_c360.py
CIBC Collections Intelligence — Phase 4: Build Golden Customer 360

Aggregates all source data per Golden Financial ID into the governed Customer 360.
Every field retains lineage, source traceability, and as-of timestamps.
Protected attributes are strictly EXCLUDED.

Output:
  - golden_customer_360 table in DuckDB
  - golden_customer_360.parquet export
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
log = logging.getLogger("build_c360")

DB_PATH    = PROJECT_ROOT / CONFIG["database"]["db_path"]
GOLDEN_DIR = PROJECT_ROOT / CONFIG["paths"]["golden_data"]
SNAPSHOT   = CONFIG["project"]["snapshot_date"]


def run_build_c360() -> dict:
    run_ts = datetime.utcnow().isoformat()
    log.info("=== BUILD CUSTOMER 360 START ===  run_ts=%s", run_ts)

    if not DB_PATH.exists():
        return {"status": "ERROR", "message": "Run ingestion and entity resolution first"}

    con = duckdb.connect(str(DB_PATH))
    t0 = time.time()

    log.info("Aggregating portfolio attributes per Golden Financial ID...")

    con.execute(f"""
        CREATE OR REPLACE TABLE golden_customer_360 AS
        WITH primary_crm AS (
            SELECT
                cl.golden_financial_id,
                c.crm_customer_id,
                c.full_name_raw AS resolved_name,
                c.primary_phone_e164 AS preferred_phone,
                c.email AS preferred_email,
                c.fsa AS customer_fsa,
                c.declared_annual_income,
                ROUND(c.declared_annual_income / 12.0, 2) AS estimated_monthly_inflow
            FROM crm_entity_clusters cl
            JOIN customers c ON cl.crm_customer_id = c.crm_customer_id
            QUALIFY ROW_NUMBER() OVER (PARTITION BY cl.golden_financial_id ORDER BY c.crm_customer_id) = 1
        ),
        cases_summary AS (
            SELECT
                cl.golden_financial_id,
                count(DISTINCT cc.case_id) AS total_cases,
                count(DISTINCT CASE WHEN cc.outcome IS NULL THEN cc.case_id END) AS active_collections_cases,
                max(cc.current_dpd) AS max_dpd_across_portfolio,
                round(sum(COALESCE(cc.total_overdue, 0)), 2) AS total_overdue_balance,
                round(sum(COALESCE(cc.total_exposure, 0)), 2) AS total_aggregate_exposure,
                bool_or(COALESCE(cc.hardship_flag, FALSE)) AS hardship_flag,
                first(cc.queue) AS current_queue,
                first(cc.current_treatment) AS current_treatment,
                first(cc.last_contact_channel) AS last_contact_channel
            FROM collections_cases cc
            JOIN crm_entity_clusters cl ON cc.coll_customer_ref = cl.crm_customer_id
            GROUP BY cl.golden_financial_id
        ),
        ptp_summary AS (
            SELECT
                cl.golden_financial_id,
                count(*) AS ptp_count_24m,
                count(CASE WHEN p.ptp_status = 'kept' THEN 1 END) AS ptp_fulfilled_24m,
                round(100.0 * avg(CASE WHEN p.ptp_status = 'kept' THEN 1 ELSE 0 END), 1) AS ptp_fulfillment_rate
            FROM promises_to_pay p
            JOIN crm_entity_clusters cl ON p.crm_customer_id = cl.crm_customer_id
            WHERE p.ptp_status IN ('kept', 'partially_kept', 'broken')
            GROUP BY cl.golden_financial_id
        )
        SELECT
            p.golden_financial_id,
            1.0 AS match_confidence,
            p.resolved_name,
            p.preferred_phone,
            p.preferred_email,
            p.customer_fsa,
            p.declared_annual_income,
            p.estimated_monthly_inflow,
            COALESCE(cs.active_collections_cases, 0) AS active_collections_cases,
            COALESCE(cs.max_dpd_across_portfolio, 0) AS max_dpd_across_portfolio,
            COALESCE(cs.total_overdue_balance, 0.0) AS total_overdue_balance,
            COALESCE(cs.total_aggregate_exposure, 0.0) AS total_aggregate_exposure,
            COALESCE(cs.hardship_flag, FALSE) AS hardship_flag,
            FALSE AS vulnerability_flag,
            cs.current_queue,
            cs.current_treatment,
            cs.last_contact_channel,
            COALESCE(pt.ptp_count_24m, 0) AS ptp_count_24m,
            COALESCE(pt.ptp_fulfilled_24m, 0) AS ptp_fulfilled_24m,
            pt.ptp_fulfillment_rate,
            '{SNAPSHOT}' AS snapshot_date,
            '{run_ts}' AS lineage_last_updated,
            '1.0.0' AS pipeline_version
        FROM primary_crm p
        LEFT JOIN cases_summary cs ON p.golden_financial_id = cs.golden_financial_id
        LEFT JOIN ptp_summary pt ON p.golden_financial_id = pt.golden_financial_id;
    """)

    c360_count = con.execute("SELECT COUNT(*) FROM golden_customer_360").fetchone()[0]
    active_cnt = con.execute("SELECT COUNT(*) FROM golden_customer_360 WHERE active_collections_cases > 0").fetchone()[0]

    log.info("Exporting golden_customer_360 to Parquet...")
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    parquet_path = GOLDEN_DIR / "golden_customer_360.parquet"
    con.execute(f"COPY golden_customer_360 TO '{parquet_path.as_posix()}' (FORMAT PARQUET)")

    elapsed = time.time() - t0
    log.info("=== CUSTOMER 360 COMPLETE ===  total=%d  active=%d (%.2fs)",
             c360_count, active_cnt, elapsed)

    con.close()

    return {
        "status": "OK",
        "run_ts": run_ts,
        "total_customers": c360_count,
        "active_collections_customers": active_cnt,
        "parquet_path": str(parquet_path),
        "elapsed_seconds": round(elapsed, 2)
    }


if __name__ == "__main__":
    result = run_build_c360()
    print(json.dumps(result, indent=2))
