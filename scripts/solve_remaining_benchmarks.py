import duckdb
import os

data_dir = r"C:\Users\dadid\.gemini\antigravity\scratch\collections-ai\data\raw\maple_data\maple_collections_release"
os.chdir(data_dir)
con = duckdb.connect()

print("=== BQ-027: COST PER CONTACT BY CHANNEL IN SEPTEMBER 2026 ===")
q27 = con.execute("""
    SELECT channel, round(avg(unit_cost_cad), 2) AS avg_unit_cost, count(*) AS records
    FROM read_csv_auto('data/channel_capacity.csv')
    WHERE date >= DATE '2026-09-01' AND date <= DATE '2026-09-30'
    GROUP BY 1 ORDER BY 1
""").fetchall()
for r in q27:
    print(" ", r)

print("\n=== BQ-014: VULNERABLE CERTIFIED AGENTS CURE RATE IN PILOT ===")
con.execute("CREATE OR REPLACE VIEW collections_cases AS SELECT * FROM read_csv_auto('data/collections_cases.csv')")
con.execute("CREATE OR REPLACE VIEW agents AS SELECT * FROM read_csv_auto('data/agents.csv')")

q14 = """
SELECT a.vulnerable_customer_certified,
       round(100.0 * avg(CASE WHEN c.cure_flag AND c.days_to_cure <= 30 THEN 1 ELSE 0 END), 2) AS cure_rate_30d_pct,
       count(*) AS cases
FROM collections_cases c
JOIN agents a ON c.assigned_agent_id = a.agent_id
WHERE c.assignment_method = 'random' AND c.hardship_flag = TRUE
GROUP BY 1 ORDER BY 1
"""
print(con.execute(q14).fetchall())

print("\n=== BQ-015: CHARGE-OFFS BY PRODUCT IN 12 MONTHS TO 28-SEP-2026 ===")
con.execute("CREATE OR REPLACE VIEW card_accounts AS SELECT * FROM read_csv_auto('data/card_accounts.csv')")
con.execute("CREATE OR REPLACE VIEW loan_accounts AS SELECT * FROM read_csv_auto('data/loan_accounts.csv')")

# Check charge-off fields
print("Card columns with 'charge' or 'write':", [r[0] for r in con.execute("DESCRIBE card_accounts").fetchall() if 'charge' in r[0] or 'write' in r[0] or 'loss' in r[0]])
print("Loan columns with 'charge' or 'write':", [r[0] for r in con.execute("DESCRIBE loan_accounts").fetchall() if 'charge' in r[0] or 'write' in r[0] or 'loss' in r[0]])

q15_card = con.execute("""
    SELECT 'card' AS product, count(*) AS accounts, round(sum(charge_off_amount), 2) AS amount
    FROM card_accounts
    WHERE charge_off_date >= DATE '2025-09-28' AND charge_off_date <= DATE '2026-09-28'
""").fetchall()
print("Card charge-offs:", q15_card)

q15_loan = con.execute("""
    SELECT product_type AS product, count(*) AS accounts, round(sum(charge_off_amount), 2) AS amount
    FROM loan_accounts
    WHERE charge_off_date >= DATE '2025-09-28' AND charge_off_date <= DATE '2026-09-28'
    GROUP BY 1 ORDER BY 1
""").fetchall()
print("Loan charge-offs:", q15_loan)
