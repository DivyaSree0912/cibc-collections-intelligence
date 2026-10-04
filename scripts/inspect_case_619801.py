import duckdb
import json
import os

data_dir = r"C:\Users\dadid\.gemini\antigravity\scratch\collections-ai\data\raw\maple_data\maple_collections_release"
os.chdir(data_dir)
con = duckdb.connect()

print("=== LOOKING UP CALL TRANSCRIPTS FOR CS-2026-619801 ===")
res = con.execute("""
    SELECT transcript_id, call_date, customer_stated_reason, file_path, call_duration_sec, agent_id
    FROM read_csv_auto('data/call_transcripts.csv')
    WHERE case_id = 'CS-2026-619801'
    ORDER BY call_date DESC
""").fetchall()

for r in res:
    print(r)
    file_path = r[3]
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("Transcript file loaded:", file_path)
        print("Turns count:", len(data.get('turns', [])))
        for t in data.get('turns', [])[:15]:
            print(f"  {t.get('speaker')}: {t.get('text')}")
    else:
        print("File path does not exist:", file_path)
