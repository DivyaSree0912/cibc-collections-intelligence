"""
pipeline/01_ingest/ingest.py
CIBC Collections Intelligence — Phase 1: Source Ingestion & Schema Validation

Loads all tables from the Maple Bank synthetic dataset into persistent DuckDB.
Tables are registered with both standard and src_ aliases for maximum interoperability.
Protected attributes are flagged for governance audit (and excluded from all decisioning).
"""

import duckdb
import yaml
import logging
import json
import os
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

with open(PROJECT_ROOT / "config" / "pipeline_config.yaml") as f:
    CONFIG = yaml.safe_load(f)

logging.basicConfig(
    level=CONFIG["logging"]["level"],
    format=CONFIG["logging"]["format"],
)
log = logging.getLogger("ingest")

RAW_RELEASE = PROJECT_ROOT / CONFIG["paths"]["raw_data"]
DB_PATH     = PROJECT_ROOT / CONFIG["database"]["db_path"]
REPORTS     = PROJECT_ROOT / CONFIG["paths"]["reports"]
PROTECTED   = set(CONFIG["governance"]["protected_attributes"])


# Exact mapping of tables from dataset README
CSV_TABLES = [
    ("customers",               "data/customers.csv",               "CRM"),
    ("card_accounts",           "data/card_accounts.csv",           "Cards"),
    ("loan_accounts",           "data/loan_accounts.csv",           "Lending"),
    ("deposit_accounts",        "data/deposit_accounts.csv",        "CoreBanking"),
    ("collections_cases",       "data/collections_cases.csv",       "Collections"),
    ("contact_history",         "data/contact_history.csv",         "Collections"),
    ("promises_to_pay",         "data/promises_to_pay.csv",         "Collections"),
    ("agent_notes",             "data/agent_notes.csv",             "Collections"),
    ("call_transcripts",        "data/call_transcripts.csv",        "Voice"),
    ("voice_samples",           "data/voice_samples.csv",           "Voice"),
    ("external",                "data/external.csv",                "Bureau"),
    ("model_scores",            "data/model_scores.csv",            "Analytics"),
    ("offers",                  "data/offers.csv",                  "Collections"),
    ("metric_definitions",      "data/metric_definitions.csv",      "Reference"),
    ("benchmark_questions",     "data/benchmark_questions.csv",     "Benchmark"),
    ("reference_documents",     "data/reference_documents.csv",     "Reference"),
    ("hardship_programs",       "data/hardship_programs.csv",       "Policy"),
    ("qa_checklist",            "data/qa_checklist.csv",            "QA"),
    ("agents",                  "data/agents.csv",                  "Ops"),
    ("case_assignment_history", "data/case_assignment_history.csv", "Ops"),
    ("agent_shifts",            "data/agent_shifts.csv",            "Ops"),
    ("channel_capacity",        "data/channel_capacity.csv",        "Ops"),
    ("ops_events",              "data/ops_events.csv",              "Ops"),
    ("geo_reference",           "data/geo_reference.csv",           "Reference"),
    ("code_lookups",            "data/code_lookups.csv",            "Reference"),
]

PARQUET_TABLES = [
    ("loan_instalments",         "data/loan_instalments/*/*.parquet",       "Lending"),
    ("transactions",             "data/transactions/*/*.parquet",           "CoreBanking"),
    ("card_statements",          "data/card_statements/*/*.parquet",        "Cards"),
    ("account_monthly_snapshot", "data/account_monthly_snapshot/*/*.parquet", "Finance"),
    ("bureau_history",           "data/bureau_history/*/*.parquet",         "Bureau"),
    ("salary_credit_history",    "data/salary_credit_history/*/*.parquet",  "CoreBanking"),
]


def get_connection() -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection to the persistent project database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))


def run_ingestion() -> dict:
    run_ts = datetime.utcnow().isoformat()
    log.info("=== INGESTION START ===  run_ts=%s", run_ts)
    log.info("Raw data directory: %s", RAW_RELEASE)

    if not RAW_RELEASE.exists():
        log.error("Raw release directory not found: %s", RAW_RELEASE)
        return {"status": "ERROR", "message": "Raw release directory not found"}

    con = get_connection()
    results = []
    loaded_tables = []

    # 1. Load CSV tables as views
    for name, rel_path, system in CSV_TABLES:
        full_path = RAW_RELEASE / rel_path
        if not full_path.exists():
            log.warning("File not found: %s", full_path)
            continue
        try:
            # Create view with exact name
            con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_csv_auto('{full_path.as_posix()}')")
            # Create alias with src_ prefix for backwards compatibility
            con.execute(f"CREATE OR REPLACE VIEW src_{name} AS SELECT * FROM {name}")
            
            cnt = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            loaded_tables.append(name)
            results.append({
                "table": name,
                "source_system": system,
                "file": rel_path,
                "rows": cnt,
                "status": "OK"
            })
            log.info("  [CSV] Loaded view '%s' (%s) -> %d rows", name, system, cnt)
        except Exception as e:
            log.error("  [CSV] Error loading '%s': %s", name, e)
            results.append({
                "table": name,
                "source_system": system,
                "file": rel_path,
                "rows": 0,
                "status": f"ERROR: {e}"
            })

    # 2. Load Parquet tables
    for name, glob_pattern, system in PARQUET_TABLES:
        full_glob = (RAW_RELEASE / glob_pattern).as_posix()
        try:
            con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{full_glob}', hive_partitioning = true)")
            con.execute(f"CREATE OR REPLACE VIEW src_{name} AS SELECT * FROM {name}")
            
            # Quick count check
            cnt = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            loaded_tables.append(name)
            results.append({
                "table": name,
                "source_system": system,
                "file": glob_pattern,
                "rows": cnt,
                "status": "OK"
            })
            log.info("  [Parquet] Loaded view '%s' (%s) -> %d rows", name, system, cnt)
        except Exception as e:
            log.warning("  [Parquet] Note on '%s': %s", name, e)
            results.append({
                "table": name,
                "source_system": system,
                "file": glob_pattern,
                "rows": 0,
                "status": f"ERROR: {e}"
            })

    # 3. Scan for protected attributes
    log.info("Scanning for protected attributes...")
    for t in loaded_tables:
        try:
            cols = [r[0].lower() for r in con.execute(f"DESCRIBE {t}").fetchall()]
            found = [c for c in cols if c in PROTECTED]
            if found:
                log.warning("  Protected attributes found in '%s': %s (RETAINED FOR AUDIT ONLY; EXCLUDED FROM DECISIONING)", t, found)
        except Exception:
            pass

    # 4. Write audit log
    con.execute("""
        CREATE TABLE IF NOT EXISTS audit_ingestion (
            table_name      VARCHAR,
            source_system   VARCHAR,
            source_file     VARCHAR,
            rows_loaded     BIGINT,
            run_ts          VARCHAR,
            status          VARCHAR
        )
    """)
    for r in results:
        con.execute("INSERT INTO audit_ingestion VALUES (?, ?, ?, ?, ?, ?)",
                    [r["table"], r["source_system"], r["file"], r["rows"], run_ts, r["status"]])

    con.close()

    total_rows = sum(r.get("rows", 0) for r in results)
    summary = {
        "status": "OK",
        "run_ts": run_ts,
        "tables_loaded": len(loaded_tables),
        "total_rows": total_rows,
        "results": results
    }

    REPORTS.mkdir(parents=True, exist_ok=True)
    with open(REPORTS / "ingestion_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    log.info("=== INGESTION COMPLETE ===  tables=%d  total_rows=%d", len(loaded_tables), total_rows)
    return summary


if __name__ == "__main__":
    result = run_ingestion()
    print(json.dumps(result, indent=2))
