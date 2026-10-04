"""
scripts/run_pipeline.py
CIBC Collections Intelligence — Master Pipeline Runner

Runs all pipeline phases in order.
Each phase is independently logged and can be re-run.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Create logs dir
(PROJECT_ROOT / "logs").mkdir(exist_ok=True)

logging.basicConfig(
    level="INFO",
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(PROJECT_ROOT / "logs" / "pipeline.log")),
    ]
)
log = logging.getLogger("run_pipeline")


def run_phase(name: str, module_path: str, fn_name: str) -> dict:
    """Import and run a pipeline phase, return result dict."""
    log.info("=" * 60)
    log.info("PHASE: %s", name)
    log.info("=" * 60)
    try:
        import importlib
        mod = importlib.import_module(module_path)
        fn  = getattr(mod, fn_name)
        result = fn()
        status = result.get("status", "OK")
        log.info("Phase %s: %s", name, status)
        return result
    except Exception as e:
        log.error("Phase %s FAILED: %s", name, e, exc_info=True)
        return {"status": "ERROR", "phase": name, "error": str(e)}


def main():
    start = datetime.utcnow()
    log.info("CIBC Collections Intelligence Platform — Full Pipeline Start")
    log.info("Timestamp: %s", start.isoformat())

    results = {}

    # Phase 1: Ingestion
    results["P1_ingest"] = run_phase(
        "P1 — Ingestion",
        "pipeline.01_ingest.ingest",
        "run_ingestion"
    )
    if results["P1_ingest"].get("status") == "ERROR":
        log.error("Ingestion failed. Cannot continue.")
        return results

    # Phase 2: Data Quality
    results["P2_quality"] = run_phase(
        "P2 — Data Quality",
        "pipeline.02_quality.data_quality",
        "run_quality_checks"
    )

    # Phase 3: Entity Resolution → Golden Financial ID
    results["P3_identity"] = run_phase(
        "P3 — Entity Resolution",
        "pipeline.03_identity.entity_resolution",
        "run_entity_resolution"
    )

    # Phase 4: Customer 360
    results["P4_c360"] = run_phase(
        "P4 — Customer 360",
        "pipeline.04_c360.build_c360",
        "run_build_c360"
    )

    # Phase 5: Collection Memory
    results["P5_memory"] = run_phase(
        "P5 — Collection Memory",
        "pipeline.05_collection_memory.collection_memory",
        "run_collection_memory"
    )

    # Phase 7: Financial Health Engine
    results["P7_health"] = run_phase(
        "P7 — Financial Health",
        "pipeline.07_financial_health.financial_health",
        "run_financial_health"
    )

    # Phase 8: Next Best Action
    results["P8_nba"] = run_phase(
        "P8 — Next Best Action",
        "pipeline.08_nba.next_best_action",
        "run_nba"
    )

    elapsed = (datetime.utcnow() - start).total_seconds()
    log.info("Pipeline complete in %.1f seconds", elapsed)

    # Save pipeline run summary
    summary = {
        "run_timestamp": start.isoformat(),
        "elapsed_seconds": elapsed,
        "phases": results,
        "overall_status": "OK" if all(
            v.get("status") in ("OK", "PARTIAL") for v in results.values()
        ) else "ERROR"
    }
    with open(PROJECT_ROOT / "logs" / "pipeline_run_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    log.info("Pipeline summary saved to logs/pipeline_run_summary.json")
    print(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    main()
