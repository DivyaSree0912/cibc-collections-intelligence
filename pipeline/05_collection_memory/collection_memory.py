"""
pipeline/05_collection_memory/collection_memory.py
CIBC Collections Intelligence — Phase 5: Collection Memory

Builds the longitudinal, time-aware Collection Memory for each customer.
Persists all interactions, contact attempts, agent notes, call transcripts,
and promises-to-pay chronologically.

The Five Golden Questions are derived from this table:
  1. What happened before?
  2. What is happening now?
  3. What has worked?
  4. What has NOT worked?
  5. What should I consider next?

Hardship keywords trigger PROTECTIVE routing (never adverse treatment).
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
log = logging.getLogger("collection_memory")

DB_PATH    = PROJECT_ROOT / CONFIG["database"]["db_path"]
GOLDEN_DIR = PROJECT_ROOT / CONFIG["paths"]["golden_data"]


def run_collection_memory() -> dict:
    run_ts = datetime.utcnow().isoformat()
    log.info("=== COLLECTION MEMORY BUILD START ===  run_ts=%s", run_ts)

    if not DB_PATH.exists():
        return {"status": "ERROR", "message": "Database not found."}

    con = duckdb.connect(str(DB_PATH))
    t0 = time.time()

    log.info("Creating consolidated collection_memory table...")

    # Load contact events, promises, notes, and transcripts into unified collection_memory
    con.execute(f"""
        CREATE OR REPLACE TABLE collection_memory AS
        -- 1. Contact History Events
        SELECT
            'EVT-' || ch.contact_id AS event_id,
            cl.golden_financial_id,
            ch.case_id,
            ch.account_id,
            'CONTACT_' || UPPER(COALESCE(ch.direction, 'OUTBOUND')) AS event_type,
            ch.contact_ts_local AS event_timestamp,
            COALESCE(ch.channel_v2, ch.channel) AS channel,
            ch.outcome_code AS outcome,
            ch.agent_id,
            NULL::DOUBLE AS promise_amount,
            NULL::DATE AS promise_date,
            NULL::BOOLEAN AS ptp_fulfilled,
            CASE WHEN ch.outcome_code IN ('hardship', 'vulnerable', 'dispute') THEN TRUE ELSE FALSE END AS hardship_flag,
            ch.outcome_desc AS note_text,
            FALSE AS has_transcript,
            'contact_history' AS source_table,
            '{run_ts}' AS created_at
        FROM contact_history ch
        JOIN crm_entity_clusters cl ON ch.crm_customer_id = cl.crm_customer_id

        UNION ALL

        -- 2. Promises to Pay
        SELECT
            'PTP-' || p.ptp_id AS event_id,
            cl.golden_financial_id,
            p.case_id,
            p.account_id,
            'PTP_' || UPPER(p.ptp_status) AS event_type,
            p.ptp_created_ts AS event_timestamp,
            p.ptp_channel AS channel,
            p.ptp_status AS outcome,
            p.agent_id,
            p.ptp_amount AS promise_amount,
            p.ptp_due_date AS promise_date,
            CASE WHEN p.ptp_status = 'kept' THEN TRUE WHEN p.ptp_status = 'broken' THEN FALSE ELSE NULL END AS ptp_fulfilled,
            FALSE AS hardship_flag,
            p.broken_reason_agent_coded AS note_text,
            FALSE AS has_transcript,
            'promises_to_pay' AS source_table,
            '{run_ts}' AS created_at
        FROM promises_to_pay p
        JOIN crm_entity_clusters cl ON p.crm_customer_id = cl.crm_customer_id

        UNION ALL

        -- 3. Agent Notes (with Keyword Hardship Detection)
        SELECT
            'NOTE-' || an.note_id AS event_id,
            cl.golden_financial_id,
            an.case_id,
            an.account_id,
            'AGENT_NOTE' AS event_type,
            an.note_ts AS event_timestamp,
            'internal' AS channel,
            an.note_type AS outcome,
            an.agent_id,
            NULL::DOUBLE AS promise_amount,
            NULL::DATE AS promise_date,
            NULL::BOOLEAN AS ptp_fulfilled,
            CASE WHEN lower(an.note_text) LIKE '%hardship%' 
                   OR lower(an.note_text) LIKE '%illness%' 
                   OR lower(an.note_text) LIKE '%medical%' 
                   OR lower(an.note_text) LIKE '%hospital%' 
                   OR lower(an.note_text) LIKE '%unemploy%' 
                   OR lower(an.note_text) LIKE '%lost job%' 
                   OR lower(an.note_text) LIKE '%layoff%' 
                   OR lower(an.note_text) LIKE '%hours cut%'
                 THEN TRUE ELSE FALSE END AS hardship_flag,
            an.note_text AS note_text,
            FALSE AS has_transcript,
            'agent_notes' AS source_table,
            '{run_ts}' AS created_at
        FROM agent_notes an
        JOIN crm_entity_clusters cl ON an.crm_customer_id = cl.crm_customer_id

        UNION ALL

        -- 4. Call Transcripts
        SELECT
            'TRN-' || ct.transcript_id AS event_id,
            cl.golden_financial_id,
            ct.case_id,
            NULL AS account_id,
            'CALL_TRANSCRIPT' AS event_type,
            ct.call_start_ts AS event_timestamp,
            'call' AS channel,
            'completed' AS outcome,
            ct.agent_id,
            NULL::DOUBLE AS promise_amount,
            NULL::DATE AS promise_date,
            NULL::BOOLEAN AS ptp_fulfilled,
            FALSE AS hardship_flag,
            'Transcript file: ' || ct.file_path AS note_text,
            TRUE AS has_transcript,
            'call_transcripts' AS source_table,
            '{run_ts}' AS created_at
        FROM call_transcripts ct
        JOIN crm_entity_clusters cl ON ct.crm_customer_id = cl.crm_customer_id;
    """)

    total_events = con.execute("SELECT COUNT(*) FROM collection_memory").fetchone()[0]
    hardship_events = con.execute("SELECT COUNT(*) FROM collection_memory WHERE hardship_flag = TRUE").fetchone()[0]

    log.info("Exporting collection_memory to Parquet...")
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    parquet_path = GOLDEN_DIR / "collection_memory.parquet"
    con.execute(f"COPY collection_memory TO '{parquet_path.as_posix()}' (FORMAT PARQUET)")

    elapsed = time.time() - t0
    log.info("=== COLLECTION MEMORY COMPLETE ===  total_events=%d  hardship_flagged=%d (%.2fs)",
             total_events, hardship_events, elapsed)

    con.close()

    return {
        "status": "OK",
        "run_ts": run_ts,
        "total_events": total_events,
        "hardship_flagged_events": hardship_events,
        "parquet_path": str(parquet_path),
        "elapsed_seconds": round(elapsed, 2)
    }


if __name__ == "__main__":
    result = run_collection_memory()
    print(json.dumps(result, indent=2))
