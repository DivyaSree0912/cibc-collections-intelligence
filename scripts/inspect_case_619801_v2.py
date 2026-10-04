import duckdb
import os

os.chdir(r"C:\Users\dadid\.gemini\antigravity\scratch\collections-ai\data\raw\maple_data\maple_collections_release")
con = duckdb.connect()

cols = [r[0] for r in con.execute("DESCRIBE SELECT * FROM read_csv_auto('data/call_transcripts.csv')").fetchall()]
print("call_transcripts columns:")
print(cols)

rows = con.execute("SELECT * FROM read_csv_auto('data/call_transcripts.csv') WHERE case_id = 'CS-2026-619801'").fetchall()
print("\nRows for CS-2026-619801:")
for r in rows:
    print(dict(zip(cols, r)))
