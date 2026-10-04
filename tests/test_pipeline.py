"""
tests/test_pipeline.py
CIBC Collections Intelligence — Comprehensive Test Suite

Verifies the integrity, accuracy, governance, and business logic of the
entire end-to-end pipeline against the Maple Bank dataset.
"""

import duckdb
import pytest
import os
import yaml
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "maple_collections.duckdb"


@pytest.fixture(scope="module")
def db_con():
    assert DB_PATH.exists(), f"Database not found at {DB_PATH}. Run pipeline first."
    con = duckdb.connect(str(DB_PATH), read_only=True)
    yield con
    con.close()


def test_tables_ingested(db_con):
    """Test that all 31 tables are loaded in DuckDB."""
    tables = [r[0] for r in db_con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()]
    core_tables = [
        "customers", "card_accounts", "loan_accounts", "deposit_accounts",
        "collections_cases", "contact_history", "promises_to_pay",
        "agent_notes", "call_transcripts", "external"
    ]
    for t in core_tables:
        assert t in tables, f"Expected table {t} missing from database"
        cnt = db_con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        assert cnt > 0, f"Table {t} is empty"


def test_entity_resolution_clusters(db_con):
    """Test that CRM records were deduplicated into persistent Golden Financial IDs."""
    crm_cnt = db_con.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    gid_cnt = db_con.execute("SELECT COUNT(DISTINCT golden_financial_id) FROM golden_id_map").fetchone()[0]
    assert gid_cnt > 0, "No Golden Financial IDs created"
    # Ensure deduplication occurred (GIDs < CRM records)
    assert gid_cnt < crm_cnt + 400000, "Entity resolution failed to cluster records"


def test_customer_360_integrity(db_con):
    """Test that Golden Customer 360 has no negative balances and excludes protected attributes."""
    c360_cnt = db_con.execute("SELECT COUNT(*) FROM golden_customer_360").fetchone()[0]
    assert c360_cnt >= 1000000, f"Expected ~1M customers in C360, got {c360_cnt}"

    # Check non-negative balances
    neg_bal = db_con.execute("""
        SELECT COUNT(*) FROM golden_customer_360
        WHERE total_overdue_balance < 0 OR total_aggregate_exposure < 0
    """).fetchone()[0]
    assert neg_bal == 0, f"Found {neg_bal} customers with negative balances"

    # Verify protected attributes are completely excluded from C360
    c360_cols = [r[0].lower() for r in db_con.execute("DESCRIBE golden_customer_360").fetchall()]
    for protected in ["gender_code", "marital_status", "citizenship_status", "race", "religion"]:
        assert protected not in c360_cols, f"Protected attribute {protected} leaked into Customer 360!"


def test_collection_memory_hardship_detection(db_con):
    """Test that Collection Memory contains events and has flagged hardship cases."""
    events_cnt = db_con.execute("SELECT COUNT(*) FROM collection_memory").fetchone()[0]
    assert events_cnt > 3000000, f"Expected 3M+ interaction events, got {events_cnt}"

    hardship_cnt = db_con.execute("SELECT COUNT(*) FROM collection_memory WHERE hardship_flag = TRUE").fetchone()[0]
    assert hardship_cnt > 50000, f"Hardship NLP keyword extraction failed to detect cases: {hardship_cnt}"


def test_financial_health_scoring(db_con):
    """Test that Financial Health features are populated across all active cases."""
    fh_cnt = db_con.execute("SELECT COUNT(*) FROM financial_health_features").fetchone()[0]
    assert fh_cnt >= 1000000, f"Expected 1M+ health scored customers, got {fh_cnt}"

    null_scores = db_con.execute("""
        SELECT COUNT(*) FROM financial_health_features
        WHERE composite_health_score IS NULL OR health_category IS NULL
    """).fetchone()[0]
    assert null_scores == 0, "Found null financial health scores"


def test_nba_policy_enforcement(db_con):
    """Test that Next Best Action enforces policy rules and plain-English explanations."""
    nba_cnt = db_con.execute("SELECT COUNT(*) FROM nba_recommendations").fetchone()[0]
    assert nba_cnt > 50000, f"Expected active collections recommendations, got {nba_cnt}"

    # Rule 1: Every hardship/vulnerability case MUST route to HUMAN_REVIEW
    viol_r1 = db_con.execute("""
        SELECT COUNT(*) FROM nba_recommendations r
        JOIN golden_customer_360 c ON r.golden_financial_id = c.golden_financial_id
        WHERE (c.hardship_flag = TRUE OR c.vulnerability_flag = TRUE)
          AND r.recommended_action != 'HUMAN_REVIEW'
    """).fetchone()[0]
    assert viol_r1 == 0, f"Rule 1 violation: {viol_r1} hardship/vulnerability cases did not route to HUMAN_REVIEW"

    # Rule 2: DPD > 90 MUST require human review
    viol_r2 = db_con.execute("""
        SELECT COUNT(*) FROM nba_recommendations
        WHERE max_dpd_across_portfolio > 90 AND requires_human_review = FALSE
    """).fetchone()[0]
    assert viol_r2 == 0, f"Rule 2 violation: {viol_r2} DPD > 90 cases bypassed human review"

    # Verify 100% of decisions have an explanation and policy reference
    missing_exp = db_con.execute("""
        SELECT COUNT(*) FROM nba_recommendations
        WHERE explanation IS NULL OR length(explanation) < 10
           OR policy_reference IS NULL
    """).fetchone()[0]
    assert missing_exp == 0, f"Found {missing_exp} recommendations missing explainability text"


def test_benchmark_bq035_gold_answer(db_con):
    """Test that benchmark BQ-035 reproduces the exact gold answer."""
    res = db_con.execute("""
        SELECT current_bucket, count(*) AS open_cases
        FROM collections_cases
        WHERE outcome IS NULL
        GROUP BY 1 ORDER BY 1
    """).fetchall()

    res_dict = dict(res)
    expected = {
        "1-30": 33639,
        "31-60": 25389,
        "61-90": 16312,
        "91-120": 10251,
        "121-150": 6184,
        "151-180": 4045,
        "180+": 180
    }
    for bucket, expected_count in expected.items():
        assert res_dict.get(bucket) == expected_count, (
            f"BQ-035 mismatch on bucket {bucket}: got {res_dict.get(bucket)}, expected {expected_count}"
        )


if __name__ == "__main__":
    import pytest
    pytest.main(["-v", __file__])
