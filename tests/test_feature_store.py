"""
tests/test_feature_store.py
CIBC Collections Intelligence — Feature Store Test Suite (REQ-L3-01 & REQ-L3-03)

Verifies:
  - REQ-L3-01: Structured features (exposure, cashflow, payment behaviour, delinquency metrics).
  - REQ-L3-03: Single feature definition for training and live scoring (zero training-serving skew).
  - REQ-GOV-03: Zero protected attributes in feature registry, database table, or exported parquet.
  - REQ-GOV-06: Deterministic calculations (LLM is not calculator of record).
"""

import duckdb
import pytest
import yaml
from pathlib import Path
import importlib

_fs_mod = importlib.import_module("pipeline.06_features.feature_store")
FeatureStore = _fs_mod.FeatureStore
compute_feature_vector = _fs_mod.compute_feature_vector
get_customer_features = _fs_mod.get_customer_features
assert_no_protected_attributes = _fs_mod.assert_no_protected_attributes
PROTECTED_ATTRIBUTES = _fs_mod.PROTECTED_ATTRIBUTES

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "maple_collections.duckdb"
DEFINITIONS_PATH = PROJECT_ROOT / "data" / "features" / "feature_definitions.yaml"
FEATURE_STORE_PARQUET = PROJECT_ROOT / "data" / "features" / "feature_store.parquet"
TRAINING_PARQUET = PROJECT_ROOT / "data" / "features" / "training_features.parquet"


@pytest.fixture(scope="module")
def db_con():
    assert DB_PATH.exists(), f"Database not found at {DB_PATH}"
    con = duckdb.connect(str(DB_PATH), read_only=True)
    yield con
    con.close()


@pytest.fixture(scope="module")
def feature_store():
    return FeatureStore(db_path=DB_PATH)


def test_feature_definitions_yaml_validity(feature_store):
    """Test that feature_definitions.yaml exists, parses, and contains required lineage metadata."""
    assert DEFINITIONS_PATH.exists(), f"Missing {DEFINITIONS_PATH}"
    defs = feature_store.load_definitions()

    assert "metadata" in defs, "Missing metadata block in feature definitions"
    assert "governance" in defs, "Missing governance block in feature definitions"
    assert "features" in defs, "Missing features array in feature definitions"

    features = defs["features"]
    assert len(features) >= 25, f"Expected at least 25 governed features, got {len(features)}"

    domains = set()
    for feat in features:
        assert "name" in feat, "Feature missing name"
        assert "domain" in feat, f"Feature {feat['name']} missing domain"
        assert "data_type" in feat, f"Feature {feat['name']} missing data_type"
        assert "description" in feat, f"Feature {feat['name']} missing description"
        assert "source_table" in feat, f"Feature {feat['name']} missing source_table"
        assert "source_columns" in feat, f"Feature {feat['name']} missing source_columns"
        assert "is_protected_attribute" in feat, f"Feature {feat['name']} missing fairness flag"
        assert feat["is_protected_attribute"] is False, f"Feature {feat['name']} cannot be protected attribute"
        domains.add(feat["domain"])

    # Required domains for REQ-L3-01
    for req_domain in ["exposure", "cashflow", "payment_behaviour", "delinquency", "composite_health"]:
        assert req_domain in domains, f"Missing required domain: {req_domain}"


def test_governance_no_protected_attributes(db_con, feature_store):
    """Test strict governance compliance: NO protected attributes exist in features (REQ-GOV-03)."""
    defs = feature_store.load_definitions()
    feature_names = [f["name"] for f in defs["features"]]

    # 1. Assert helper passes on feature names
    assert_no_protected_attributes(feature_names)

    # 2. Assert helper raises on protected attributes
    for prohibited in ["gender", "gender_code", "marital_status", "citizenship", "race", "religion"]:
        with pytest.raises(ValueError):
            assert_no_protected_attributes([prohibited])

    # 3. Assert DuckDB customer_features table columns do not contain protected attributes
    table_cols = [
        r[0].lower() for r in db_con.execute("DESCRIBE customer_features").fetchall()
    ]
    for prohibited in ["gender_code", "marital_status", "citizenship_status", "race", "religion", "customer_fsa", "postal_code"]:
        assert prohibited not in table_cols, f"Protected attribute '{prohibited}' leaked into customer_features table!"


def test_feature_store_table_integrity(db_con):
    """Test that customer_features table has >= 1M rows and correct structured metrics (REQ-L3-01)."""
    cnt = db_con.execute("SELECT COUNT(*) FROM customer_features").fetchone()[0]
    assert cnt >= 1000000, f"Expected 1M+ rows in customer_features, got {cnt}"

    # Verify no nulls in critical score columns
    null_scores = db_con.execute("""
        SELECT COUNT(*) FROM customer_features
        WHERE exposure_score IS NULL
           OR payment_behaviour_score IS NULL
           OR cashflow_score IS NULL
           OR composite_health_score IS NULL
           OR health_category IS NULL
           OR can_support_arrangement IS NULL
    """).fetchone()[0]
    assert null_scores == 0, f"Found {null_scores} records with null health scores"

    # Verify delinquency buckets are populated
    buckets = [r[0] for r in db_con.execute("SELECT DISTINCT delinquency_bucket FROM customer_features").fetchall()]
    assert "CURRENT" in buckets
    assert "1-30" in buckets
    assert "31-60" in buckets
    assert "180+" in buckets


def test_feature_store_parquet_artifacts():
    """Test that feature_store.parquet and training_features.parquet are created and valid."""
    assert FEATURE_STORE_PARQUET.exists(), f"Missing {FEATURE_STORE_PARQUET}"
    assert FEATURE_STORE_PARQUET.stat().st_size > 1024 * 1024, "feature_store.parquet is unexpectedly small"

    assert TRAINING_PARQUET.exists(), f"Missing {TRAINING_PARQUET}"
    assert TRAINING_PARQUET.stat().st_size > 1024 * 1024, "training_features.parquet is unexpectedly small"

    # Verify training parquet has target label
    con = duckdb.connect()
    df_train = con.execute(f"SELECT * FROM '{TRAINING_PARQUET.as_posix()}' LIMIT 5").df()
    assert "target_nba_action" in df_train.columns, "training_features.parquet missing target_nba_action"
    con.close()


def test_training_serving_parity(feature_store, db_con):
    """
    Test REQ-L3-03: Single feature definition for training and live scoring.
    Verifies that real-time live calculated features match batch DuckDB features bit-for-bit with ZERO skew.
    """
    parity_result = feature_store.verify_training_serving_parity(sample_size=100, con=db_con)
    assert parity_result["parity_passed"] is True, f"Training-serving skew detected: {parity_result['mismatches']}"
    assert parity_result["mismatches_count"] == 0
    assert parity_result["tested_samples"] == 100


def test_deterministic_edge_cases():
    """Test deterministic calculation on edge cases (zero income, high DPD, hardship)."""
    # Case A: Pristine customer (zero debt, high income)
    row_pristine = {
        "golden_financial_id": "GID-TEST-001",
        "snapshot_date": "2026-09-28",
        "total_aggregate_exposure": 0.0,
        "total_overdue_balance": 0.0,
        "declared_annual_income": 120000,
        "estimated_monthly_inflow": 10000.0,
        "max_dpd_across_portfolio": 0,
        "active_collections_cases": 0,
        "ptp_count_24m": 0,
        "ptp_fulfilled_24m": 0,
        "ptp_fulfillment_rate": None,
        "hardship_flag": False,
        "vulnerability_flag": False,
    }
    feats_a = compute_feature_vector(row_pristine)
    assert feats_a["exposure_score"] == 0.0
    assert feats_a["exposure_label"] == "LOW"
    assert feats_a["delinquency_bucket"] == "CURRENT"
    assert feats_a["is_delinquent"] is False
    assert feats_a["dsr"] == 0.0
    assert feats_a["dsr_category"] == "LOW"
    assert feats_a["composite_health_score"] >= 0.75
    assert feats_a["health_category"] == "GOOD"
    assert feats_a["can_support_arrangement"] == "YES"
    assert feats_a["requires_human_review"] is False

    # Case B: Severe hardship customer
    row_hardship = {
        "golden_financial_id": "GID-TEST-002",
        "snapshot_date": "2026-09-28",
        "total_aggregate_exposure": 50000.0,
        "total_overdue_balance": 15000.0,
        "declared_annual_income": 30000,
        "estimated_monthly_inflow": 2500.0,
        "max_dpd_across_portfolio": 120,
        "active_collections_cases": 2,
        "ptp_count_24m": 3,
        "ptp_fulfilled_24m": 0,
        "ptp_fulfillment_rate": 0.0,
        "hardship_flag": True,
        "vulnerability_flag": False,
    }
    feats_b = compute_feature_vector(row_hardship)
    assert feats_b["exposure_score"] == 1.0
    assert feats_b["exposure_label"] == "SEVERE"
    assert feats_b["delinquency_bucket"] == "91-120"
    assert feats_b["is_delinquent"] is True
    assert feats_b["is_severe_delinquent"] is True
    assert feats_b["can_support_arrangement"] == "REVIEW_REQUIRED"
    assert feats_b["requires_human_review"] is True

    # Case C: Determinism — repeat calculation yields identical object
    feats_b_repeat = compute_feature_vector(row_hardship)
    assert feats_b == feats_b_repeat, "Non-deterministic feature computation detected"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
