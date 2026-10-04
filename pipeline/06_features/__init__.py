"""
pipeline/06_features
CIBC Collections Intelligence — Phase 6: Governed Feature Store
"""

from .feature_store import (
    FeatureStore,
    run_feature_store,
    compute_feature_vector,
    get_customer_features,
    assert_no_protected_attributes,
)

__all__ = [
    "FeatureStore",
    "run_feature_store",
    "compute_feature_vector",
    "get_customer_features",
    "assert_no_protected_attributes",
]
