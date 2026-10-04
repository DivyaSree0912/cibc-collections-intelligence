import duckdb
import os

data_dir = r"C:\Users\dadid\.gemini\antigravity\scratch\collections-ai\data\raw\maple_data\maple_collections_release"
os.chdir(data_dir)

con = duckdb.connect()

tables = [
    "customers",
    "card_accounts",
    "loan_accounts",
    "deposit_accounts",
    "collections_cases",
    "promises_to_pay",
    "contact_history",
    "agent_notes",
    "external"
]

print("=== INSPECTING COLUMNS ===")
for t in tables:
    con.execute(f"CREATE OR REPLACE VIEW {t} AS SELECT * FROM read_csv_auto('data/{t}.csv')")
    cols = [r[0] for r in con.execute(f"DESCRIBE {t}").fetchall()]
    print(f"\n[{t}] ({len(cols)} columns):")
    print(", ".join(cols[:25]))
    if len(cols) > 25:
        print("  ... and " + ", ".join(cols[25:50]))
