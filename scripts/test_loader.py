import duckdb
import os
import time

data_dir = r"C:\Users\dadid\.gemini\antigravity\scratch\collections-ai\data\raw\maple_data\maple_collections_release"
os.chdir(data_dir)

t0 = time.time()
con = duckdb.connect()

# Create views for key tables using standard auto-detection
views = [
    ("customers", "data/customers.csv"),
    ("card_accounts", "data/card_accounts.csv"),
    ("loan_accounts", "data/loan_accounts.csv"),
    ("deposit_accounts", "data/deposit_accounts.csv"),
    ("collections_cases", "data/collections_cases.csv"),
    ("contact_history", "data/contact_history.csv"),
    ("promises_to_pay", "data/promises_to_pay.csv"),
    ("agent_notes", "data/agent_notes.csv"),
    ("call_transcripts", "data/call_transcripts.csv"),
    ("external", "data/external.csv"),
    ("benchmark_questions", "data/benchmark_questions.csv"),
    ("reference_documents", "data/reference_documents.csv"),
    ("hardship_programs", "data/hardship_programs.csv"),
    ("qa_checklist", "data/qa_checklist.csv"),
    ("agents", "data/agents.csv"),
    ("ops_events", "data/ops_events.csv")
]

for name, path in views:
    query = f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_csv_auto('{path}')"
    con.execute(query)

print(f"Created {len(views)} views in {time.time()-t0:.2f} seconds!")

# Test query on collections_cases
res = con.execute("SELECT count(*) FROM collections_cases").fetchone()
print(f"Total collections cases: {res[0]:,}")

# Test query from gold answers BQ-035:
query_bq35 = "SELECT current_bucket, count(*) AS open_cases FROM collections_cases WHERE outcome IS NULL GROUP BY 1 ORDER BY 1"
res_bq35 = con.execute(query_bq35).fetchall()
print("\nBQ-035 result (Open cases by bucket):")
for r in res_bq35:
    print(f"  {r[0]}: {r[1]:,}")

# Compare with gold answer:
# 1-30: 33639
# 31-60: 25389
# 61-90: 16312
# 91-120: 10251
# 121-150: 6184
# 151-180: 4045
# 180+: 180
