import duckdb
import pandas as pd
import os

data_dir = r"C:\Users\dadid\.gemini\antigravity\scratch\collections-ai\data\raw\maple_data\maple_collections_release"
os.chdir(data_dir)

bq = pd.read_csv("data/benchmark_questions.csv")
dev = pd.read_csv("labels/benchmark_dev_answers.csv")

print(f"Total benchmark questions: {len(bq)}")
print(f"Dev questions with gold answers: {len(dev)}")

merged = bq.merge(dev, on="question_id", how="left")
for idx, r in merged.iterrows():
    split = r['split']
    has_gold = "GOLD" if pd.notna(r['gold_answer']) else "TEST"
    print(f"[{r['question_id']}] ({split}, {has_gold}): {r['question_text']}")
    if pd.notna(r['gold_answer']):
        print(f"   -> Gold Answer: {str(r['gold_answer'])[:100]}...")
        if pd.notna(r['gold_sql_reference']):
            print(f"   -> Gold SQL: {str(r['gold_sql_reference'])[:100]}...")
        if pd.notna(r['gold_sources']):
            print(f"   -> Gold Sources: {r['gold_sources']}")
