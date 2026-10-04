import duckdb
import os
import glob

data_dir = r"C:\Users\dadid\.gemini\antigravity\scratch\collections-ai\data\raw\maple_data\maple_collections_release"
os.chdir(data_dir)

con = duckdb.connect()
con.execute("CREATE OR REPLACE VIEW collections_cases AS SELECT * FROM read_csv_auto('data/collections_cases.csv')")
con.execute("CREATE OR REPLACE VIEW promises_to_pay AS SELECT * FROM read_csv_auto('data/promises_to_pay.csv')")
con.execute("CREATE OR REPLACE VIEW call_transcripts AS SELECT * FROM read_csv_auto('data/call_transcripts.csv')")
con.execute("CREATE OR REPLACE VIEW ops_events AS SELECT * FROM read_csv_auto('data/ops_events.csv')")
con.execute("CREATE OR REPLACE VIEW channel_capacity AS SELECT * FROM read_csv_auto('data/channel_capacity.csv')")
con.execute("CREATE OR REPLACE VIEW card_accounts AS SELECT * FROM read_csv_auto('data/card_accounts.csv')")
con.execute("CREATE OR REPLACE VIEW loan_accounts AS SELECT * FROM read_csv_auto('data/loan_accounts.csv')")

print("=== SOLVING TEST QUESTIONS ===")

# BQ-008: What share of cases opened in July 2026 cured within 30 days of opening?
print("\n--- BQ-008 ---")
q8 = """
SELECT round(100.0 * avg(CASE WHEN cure_flag AND days_to_cure <= 30 THEN 1 ELSE 0 END), 1) AS cure_rate_pct,
       count(*) AS cases
FROM collections_cases
WHERE case_open_date >= DATE '2026-07-01' AND case_open_date <= DATE '2026-07-31'
"""
print(con.execute(q8).fetchall())

# BQ-013: How much was paid against promises in September 2026?
print("\n--- BQ-013 ---")
q13 = """
SELECT round(sum(amount_paid_against), 2) AS total_paid
FROM promises_to_pay
WHERE paid_date >= DATE '2026-09-01' AND paid_date <= DATE '2026-09-30'
"""
print(con.execute(q13).fetchall())

# BQ-025: How many outbound contact attempts did open cases receive, on average, by current bucket?
print("\n--- BQ-025 ---")
q25 = """
SELECT current_bucket, round(avg(contact_attempts_total), 2) AS avg_attempts, count(*) AS cases
FROM collections_cases
WHERE outcome IS NULL
GROUP BY 1 ORDER BY 1
"""
print(con.execute(q25).fetchall())

# BQ-030: Why did outbound call volume drop on 23-24 September 2026?
print("\n--- BQ-030 (ops_events) ---")
q30 = "SELECT * FROM ops_events WHERE start_ts >= '2026-09-20' OR event_name ILIKE '%outage%' OR event_name ILIKE '%dialer%'"
print(con.execute(q30).fetchall())

# BQ-021: Summarise the most recent recorded call on case CS-2026-619801: what did the customer say and agree to?
print("\n--- BQ-021 (transcript for CS-2026-619801) ---")
q21 = "SELECT transcript_id, call_date, customer_stated_reason, file_path FROM call_transcripts WHERE case_id = 'CS-2026-619801' ORDER BY call_date DESC LIMIT 1"
print(con.execute(q21).fetchall())
