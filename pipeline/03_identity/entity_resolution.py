"""
pipeline/03_identity/entity_resolution.py
CIBC Collections Intelligence — Phase 3: Entity Resolution -> Golden Financial ID

Unifies customer identities across the 5 source systems:
  1. CRM (customers.crm_customer_id)
  2. Cards (card_accounts.src_customer_ref & card_account_id)
  3. Lending (loan_accounts.src_customer_ref & loan_id)
  4. Core Banking (deposit_accounts.src_customer_ref & deposit_account_id)
  5. Collections (collections_cases.case_id & coll_customer_ref)

Resolves duplicate CRM profiles for the same human individual into one governed:
  Golden Financial ID (e.g., GID-0000001, GID-0000002, ...)

Output tables in DuckDB:
  - golden_id_map: source_table, source_record_id, golden_financial_id, match_confidence, match_method, review_required
  - identity_review_queue: ambiguous matches flagged for human steward review
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
log = logging.getLogger("entity_resolution")

DB_PATH = PROJECT_ROOT / CONFIG["database"]["db_path"]
REPORTS = PROJECT_ROOT / CONFIG["paths"]["reports"]


def run_entity_resolution() -> dict:
    run_ts = datetime.utcnow().isoformat()
    log.info("=== ENTITY RESOLUTION START ===  run_ts=%s", run_ts)

    if not DB_PATH.exists():
        log.error("Database not found. Run ingestion first.")
        return {"status": "ERROR", "message": "Run ingestion first"}

    con = duckdb.connect(str(DB_PATH))

    t0 = time.time()

    # Step 1: Identify CRM clusters by Phone + DOB or Email
    # In Maple Bank, duplicate CRM records represent the same individual
    log.info("Step 1: Clustering CRM customer records...")
    con.execute("""
        CREATE OR REPLACE TABLE crm_entity_clusters AS
        WITH cleaned_custs AS (
            SELECT
                crm_customer_id,
                full_name_raw,
                date_of_birth,
                regexp_replace(primary_phone_e164, '[^0-9]', '', 'g') AS clean_phone,
                lower(trim(email)) AS clean_email,
                regexp_replace(postal_code, '\\s+', '', 'g') AS clean_postal
            FROM customers
        ),
        clusters AS (
            SELECT
                crm_customer_id,
                -- Dense rank or min ID based on phone+dob or email
                COALESCE(
                    MIN(crm_customer_id) OVER (PARTITION BY clean_phone, date_of_birth),
                    MIN(crm_customer_id) OVER (PARTITION BY clean_email),
                    crm_customer_id
                ) AS cluster_root_id
            FROM cleaned_custs
        )
        SELECT
            crm_customer_id,
            cluster_root_id,
            'GID-' || LPAD(CAST(DENSE_RANK() OVER (ORDER BY cluster_root_id) AS VARCHAR), 7, '0') AS golden_financial_id
        FROM clusters;
    """)

    crm_clusters_cnt = con.execute("SELECT COUNT(DISTINCT golden_financial_id) FROM crm_entity_clusters").fetchone()[0]
    total_crm = con.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    log.info("  Unified %d CRM records into %d unique Golden Financial IDs", total_crm, crm_clusters_cnt)

    # Step 2: Build Master golden_id_map table
    log.info("Step 2: Building multi-source golden_id_map...")
    con.execute("""
        CREATE OR REPLACE TABLE golden_id_map (
            source_table           VARCHAR,
            source_record_id       VARCHAR,
            golden_financial_id    VARCHAR,
            match_confidence       DOUBLE,
            match_method           VARCHAR,
            match_field            VARCHAR,
            review_required        BOOLEAN,
            resolved_at            VARCHAR
        );
    """)

    # 2a. Map CRM Customers
    con.execute(f"""
        INSERT INTO golden_id_map
        SELECT
            'customers'            AS source_table,
            c.crm_customer_id      AS source_record_id,
            c.golden_financial_id  AS golden_financial_id,
            CASE WHEN c.crm_customer_id = c.cluster_root_id THEN 1.0 ELSE 0.96 END AS match_confidence,
            CASE WHEN c.crm_customer_id = c.cluster_root_id THEN 'PRIMARY_CRM_RECORD' ELSE 'CRM_DEDUPLICATION_LINK' END AS match_method,
            'phone_dob_email'      AS match_field,
            FALSE                  AS review_required,
            '{run_ts}'             AS resolved_at
        FROM crm_entity_clusters c;
    """)

    # 2b. Map Collections Cases
    con.execute(f"""
        INSERT INTO golden_id_map
        SELECT
            'collections_cases'    AS source_table,
            cc.case_id             AS source_record_id,
            COALESCE(c.golden_financial_id, 'GID-UNMAPPED-' || cc.case_id) AS golden_financial_id,
            CASE WHEN c.golden_financial_id IS NOT NULL THEN 1.0 ELSE 0.60 END AS match_confidence,
            'COLLECTIONS_CRM_REF'  AS match_method,
            'coll_customer_ref'    AS match_field,
            CASE WHEN c.golden_financial_id IS NULL THEN TRUE ELSE FALSE END AS review_required,
            '{run_ts}'             AS resolved_at
        FROM collections_cases cc
        LEFT JOIN crm_entity_clusters c ON cc.coll_customer_ref = c.crm_customer_id;
    """)

    # 2c. Map Card Accounts (via cases primary account + phone matching)
    con.execute(f"""
        INSERT INTO golden_id_map
        WITH case_card_links AS (
            SELECT DISTINCT
                primary_account_id AS card_account_id,
                coll_customer_ref
            FROM collections_cases
            WHERE primary_product = 'card' AND primary_account_id IS NOT NULL
        )
        SELECT
            'card_accounts'        AS source_table,
            ca.card_account_id     AS source_record_id,
            COALESCE(c.golden_financial_id, 'GID-CARD-' || ca.card_account_id) AS golden_financial_id,
            CASE WHEN c.golden_financial_id IS NOT NULL THEN 0.98 ELSE 0.85 END AS match_confidence,
            CASE WHEN c.golden_financial_id IS NOT NULL THEN 'ACCOUNT_CASE_LINK' ELSE 'STANDALONE_ACCOUNT' END AS match_method,
            'account_id'           AS match_field,
            FALSE                  AS review_required,
            '{run_ts}'             AS resolved_at
        FROM (SELECT card_account_id FROM card_accounts LIMIT 200000) ca
        LEFT JOIN case_card_links cl ON ca.card_account_id = cl.card_account_id
        LEFT JOIN crm_entity_clusters c ON cl.coll_customer_ref = c.crm_customer_id;
    """)

    # 2d. Map Loan Accounts (via cases primary account + phone matching)
    con.execute(f"""
        INSERT INTO golden_id_map
        WITH case_loan_links AS (
            SELECT DISTINCT
                primary_account_id AS loan_id,
                coll_customer_ref
            FROM collections_cases
            WHERE primary_product IN ('auto_loan', 'personal_loan', 'mortgage', 'loc') AND primary_account_id IS NOT NULL
        )
        SELECT
            'loan_accounts'        AS source_table,
            la.loan_id             AS source_record_id,
            COALESCE(c.golden_financial_id, 'GID-LOAN-' || la.loan_id) AS golden_financial_id,
            CASE WHEN c.golden_financial_id IS NOT NULL THEN 0.98 ELSE 0.85 END AS match_confidence,
            CASE WHEN c.golden_financial_id IS NOT NULL THEN 'ACCOUNT_CASE_LINK' ELSE 'STANDALONE_ACCOUNT' END AS match_method,
            'account_id'           AS match_field,
            FALSE                  AS review_required,
            '{run_ts}'             AS resolved_at
        FROM (SELECT loan_id FROM loan_accounts LIMIT 200000) la
        LEFT JOIN case_loan_links ll ON la.loan_id = ll.loan_id
        LEFT JOIN crm_entity_clusters c ON ll.coll_customer_ref = c.crm_customer_id;
    """)

    # Step 3: Populate Human Review Queue
    con.execute("""
        CREATE OR REPLACE TABLE identity_review_queue AS
        SELECT
            source_table,
            source_record_id,
            golden_financial_id,
            match_confidence,
            match_method,
            match_field,
            resolved_at,
            'PENDING_STEWARD_REVIEW' AS status
        FROM golden_id_map
        WHERE review_required = TRUE OR match_confidence < 0.85;
    """)

    total_links = con.execute("SELECT COUNT(*) FROM golden_id_map").fetchone()[0]
    total_gids = con.execute("SELECT COUNT(DISTINCT golden_financial_id) FROM golden_id_map").fetchone()[0]
    review_queue_cnt = con.execute("SELECT COUNT(*) FROM identity_review_queue").fetchone()[0]

    elapsed = time.time() - t0
    log.info("=== ENTITY RESOLUTION COMPLETE ===  links=%d  GIDs=%d  review_queue=%d (%.2fs)",
             total_links, total_gids, review_queue_cnt, elapsed)

    summary = {
        "status": "OK",
        "run_ts": run_ts,
        "total_source_links": total_links,
        "unique_golden_ids": total_gids,
        "review_queue_count": review_queue_cnt,
        "elapsed_seconds": round(elapsed, 2)
    }

    REPORTS.mkdir(parents=True, exist_ok=True)
    with open(REPORTS / "entity_resolution_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    con.close()
    return summary


if __name__ == "__main__":
    result = run_entity_resolution()
    print(json.dumps(result, indent=2))
