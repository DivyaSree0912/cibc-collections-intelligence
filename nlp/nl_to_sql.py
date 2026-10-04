"""
nlp/nl_to_sql.py
CIBC Collections Intelligence — Layer 2: NL-to-SQL Engine

Converts plain-English questions into SQL, executes against DuckDB,
and returns answers with source evidence.

Governance:
  - Out-of-scope and protected-attribute questions are REFUSED
  - SQL is ALWAYS shown with the answer
  - AI does NOT invent customer facts
  - All answers are grounded in retrieved data
"""

import duckdb
import yaml
import json
import re
import logging
import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
with open(PROJECT_ROOT / "config" / "pipeline_config.yaml") as f:
    CONFIG = yaml.safe_load(f)

logging.basicConfig(level=CONFIG["logging"]["level"], format=CONFIG["logging"]["format"])
log = logging.getLogger("nl_to_sql")

DB_PATH   = PROJECT_ROOT / CONFIG["database"]["db_path"]
LLM_MODEL = CONFIG["llm"]["model"]
PROTECTED = set(CONFIG["governance"]["protected_attributes"])

# ── Semantic map — human alias → column name mapping ─────────────────────────
# Updated from data_dictionary once dataset is inspected.
# TBC fields are marked.

SEMANTIC_MAP = {
    # Identity
    "customer id": "golden_financial_id",
    "golden id": "golden_financial_id",
    "gid": "golden_financial_id",
    "match confidence": "match_confidence",

    # Delinquency
    "days overdue": "max_dpd_across_portfolio",
    "dpd": "max_dpd_across_portfolio",
    "days past due": "max_dpd_across_portfolio",
    "overdue days": "max_dpd_across_portfolio",
    "overdue balance": "total_overdue_balance",
    "outstanding balance": "total_overdue_balance",

    # Exposure
    "loan outstanding": "total_loan_outstanding",
    "card outstanding": "total_card_outstanding",
    "total exposure": "total_aggregate_exposure",
    "total debt": "total_aggregate_exposure",

    # Income
    "monthly income": "estimated_monthly_inflow",
    "salary": "estimated_monthly_inflow",
    "monthly inflow": "estimated_monthly_inflow",

    # Health signals
    "debt service ratio": "dsr",
    "dsr": "dsr",
    "dsr category": "dsr_category",
    "health score": "composite_health_score",
    "financial health": "health_category",
    "health category": "health_category",
    "cash flow stress": "cashflow_stress_label",
    "cash-flow stress": "cashflow_stress_label",
    "cashflow stress": "cashflow_stress_label",
    "arrangement sustainability": "can_support_arrangement",

    # PTP / Payment behaviour
    "ptp rate": "ptp_fulfillment_rate",
    "promise to pay": "ptp_fulfillment_rate",
    "payment behaviour": "payment_label",

    # Hardship
    "hardship": "hardship_flag",
    "vulnerability": "vulnerability_flag",
    "vulnerable": "vulnerability_flag",

    # Contact
    "last contact": "last_contact_date",
    "last channel": "last_contact_channel",
    "last outcome": "last_contact_outcome",

    # NBA
    "recommended action": "recommended_action",
    "next best action": "recommended_action",
    "nba": "recommended_action",
    "human review": "requires_human_review",
}

# ── Schema context sent to LLM ────────────────────────────────────────────────

C360_SCHEMA_CONTEXT = """
Available tables in the database:

1. golden_customer_360 — Master customer table (one row per customer)
   Columns: golden_financial_id, match_confidence, resolved_name, preferred_phone,
   preferred_email, max_dpd_across_portfolio, total_overdue_balance, active_collections_cases,
   total_loan_outstanding, total_card_outstanding, total_aggregate_exposure, active_facility_count,
   estimated_monthly_inflow, salary_credit_lag_days, cashflow_stress_index,
   ptp_count_24m, ptp_fulfilled_24m, ptp_fulfillment_rate,
   last_contact_date, last_contact_channel, last_contact_outcome,
   vulnerability_flag, hardship_flag, lineage_last_updated, snapshot_date

2. financial_health_features — Financial health per customer
   Columns: golden_financial_id, exposure_score, exposure_label, cashflow_score,
   cashflow_stress_label, payment_behaviour_score, payment_label, dsr, dsr_category,
   composite_health_score, health_category, available_monthly_surplus, can_support_arrangement,
   vulnerability_flag, hardship_flag, requires_human_review, data_completeness_pct, computed_at

3. nba_recommendations — NBA recommendations per customer
   Columns: golden_financial_id, recommended_action, eligible_actions, explanation,
   evidence, policy_reference, requires_human_review, confidence, computed_at

4. collection_memory — Full event history per customer
   Columns: event_id, golden_financial_id, account_id, event_type, event_timestamp,
   event_date, channel, outcome, agent_id, promise_amount, promise_date,
   ptp_fulfilled, hardship_flag, source_table, note_text, has_transcript

NOTE: Protected attributes (gender, marital_status, citizenship, etc.) must NOT be 
      used in any query. Any question involving protected attributes must be refused.
"""

REFUSED_PATTERNS = [
    # Protected attributes
    r"\bgender\b", r"\bsex\b", r"\bmarital\b", r"\bcitizenship\b",
    r"\bnewcomer\b", r"\baccessibility\b", r"\baccent\b", r"\bhousehold\b",
    # Out-of-scope
    r"\bapprove.{0,20}loan\b", r"\bgrant.{0,20}credit\b",
    r"\brace\b", r"\bethnicity\b", r"\breligion\b",
    # Privacy violations
    r"\bpassword\b", r"\bssn\b", r"\bsin\b",
]


def check_refusal(question: str) -> tuple[bool, str]:
    """
    Check if a question should be refused.
    Returns (should_refuse, reason).
    """
    question_lower = question.lower()
    for pattern in REFUSED_PATTERNS:
        if re.search(pattern, question_lower):
            matched = re.search(pattern, question_lower).group()
            reason = (
                f"This question references '{matched}', which is either a protected attribute "
                "or is outside the permitted scope of this system. "
                "Protected attributes must not be used in any collection decision or query. "
                "Please rephrase the question using financial data only."
            )
            return True, reason
    return False, ""


def build_nl_to_sql_prompt(question: str) -> str:
    """Build the prompt for NL-to-SQL conversion."""
    return f"""You are a SQL expert for a collections intelligence database.
Your job is to convert a plain-English question into a valid DuckDB SQL query.

{C360_SCHEMA_CONTEXT}

Rules:
1. Return ONLY valid DuckDB SQL. No explanations, no markdown, no code blocks.
2. Never reference gender, marital_status, citizenship, household, newcomer, 
   accessibility, vulnerability, or accent columns.
3. If the question asks for personal PII (full name, address, phone), do not include it.
4. Use LIMIT 100 unless the user asks for all results.
5. Always include golden_financial_id in the result.
6. Use ILIKE for string comparisons.
7. For boolean flags, use TRUE/FALSE.

Question: {question}

SQL:"""


def execute_nl_query(question: str, api_key: str | None = None) -> dict:
    """
    Main NL-to-SQL execution function.

    Returns:
        {
          "question": str,
          "refused": bool,
          "refusal_reason": str | None,
          "sql": str | None,
          "results": list | None,
          "result_count": int,
          "columns": list | None,
          "source_table": str,
          "execution_time_ms": int,
          "error": str | None,
        }
    """
    result = {
        "question": question,
        "refused": False,
        "refusal_reason": None,
        "sql": None,
        "results": None,
        "result_count": 0,
        "columns": None,
        "source_table": "golden_customer_360",
        "execution_time_ms": 0,
        "error": None,
    }

    # Step 1: Check refusal
    should_refuse, reason = check_refusal(question)
    if should_refuse:
        result["refused"] = True
        result["refusal_reason"] = reason
        log.info("Question REFUSED: %s | Reason: %s", question[:80], reason[:80])
        return result

    # Step 2: Generate SQL via LLM
    try:
        import google.generativeai as genai
        key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not key:
            # Fallback: use simple rule-based SQL generation
            sql = _rule_based_sql(question)
            result["sql"] = sql
            result["source_table"] = "rule_based_fallback"
        else:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(LLM_MODEL)
            prompt = build_nl_to_sql_prompt(question)
            response = model.generate_content(prompt)
            sql = response.text.strip()
            # Clean up LLM output
            sql = re.sub(r"```sql\s*", "", sql)
            sql = re.sub(r"```\s*", "", sql)
            sql = sql.strip()
            result["sql"] = sql
            result["source_table"] = "llm_generated"
    except ImportError:
        sql = _rule_based_sql(question)
        result["sql"] = sql
        result["source_table"] = "rule_based_fallback"
    except Exception as e:
        result["error"] = f"LLM error: {e}"
        return result

    # Step 3: Execute SQL
    if not DB_PATH.exists():
        result["error"] = "Database not found. Run pipeline first."
        return result

    try:
        start = datetime.utcnow()
        con = duckdb.connect(str(DB_PATH), read_only=True)
        rel = con.execute(sql)
        rows = rel.fetchall()
        cols = [d[0] for d in rel.description] if rel.description else []
        con.close()
        elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

        result["results"] = [dict(zip(cols, row)) for row in rows]
        result["result_count"] = len(rows)
        result["columns"] = cols
        result["execution_time_ms"] = elapsed
        log.info("NL query executed: %d rows, %d ms", len(rows), elapsed)
    except Exception as e:
        result["error"] = f"SQL execution error: {e}"
        log.error("SQL execution failed: %s | SQL: %s", e, sql)

    return result


def _rule_based_sql(question: str) -> str:
    """
    Fallback rule-based SQL generator when LLM is unavailable.
    Handles common question patterns.
    """
    q = question.lower()
    base = "SELECT golden_financial_id, health_category, dsr_category, " \
           "max_dpd_across_portfolio, recommended_action FROM golden_customer_360 g " \
           "JOIN financial_health_features f USING (golden_financial_id) " \
           "JOIN nba_recommendations n USING (golden_financial_id)"

    if "hardship" in q or "vulnerable" in q:
        return f"{base} WHERE g.hardship_flag = TRUE OR g.vulnerability_flag = TRUE LIMIT 100"
    elif "dpd" in q and (">" in q or "above" in q or "over" in q):
        # Extract number
        nums = re.findall(r'\d+', q)
        threshold = int(nums[0]) if nums else 60
        return f"{base} WHERE g.max_dpd_across_portfolio > {threshold} LIMIT 100"
    elif "human review" in q or "review" in q:
        return f"{base} WHERE n.requires_human_review = TRUE LIMIT 100"
    elif "payment plan" in q:
        return f"{base} WHERE n.recommended_action = 'PAYMENT_PLAN' LIMIT 100"
    elif "critical" in q or "severe" in q:
        return f"{base} WHERE f.health_category IN ('CRITICAL', 'STRESSED') LIMIT 100"
    else:
        return f"SELECT * FROM golden_customer_360 LIMIT 100"
