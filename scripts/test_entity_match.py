import duckdb
import os
import time

data_dir = r"C:\Users\dadid\.gemini\antigravity\scratch\collections-ai\data\raw\maple_data\maple_collections_release"
os.chdir(data_dir)

con = duckdb.connect()

print("Setting up views...")
con.execute("CREATE OR REPLACE VIEW customers AS SELECT * FROM read_csv_auto('data/customers.csv')")
con.execute("CREATE OR REPLACE VIEW card_accounts AS SELECT * FROM read_csv_auto('data/card_accounts.csv')")
con.execute("CREATE OR REPLACE VIEW loan_accounts AS SELECT * FROM read_csv_auto('data/loan_accounts.csv')")
con.execute("CREATE OR REPLACE VIEW deposit_accounts AS SELECT * FROM read_csv_auto('data/deposit_accounts.csv')")
con.execute("CREATE OR REPLACE VIEW collections_cases AS SELECT * FROM read_csv_auto('data/collections_cases.csv')")

# Check matches between collections_cases and customers (direct CRM key)
res = con.execute("""
    SELECT count(DISTINCT coll_customer_ref) AS unique_case_custs,
           count(DISTINCT c.crm_customer_id) AS matched_crm_custs
    FROM collections_cases cc
    LEFT JOIN customers c ON cc.coll_customer_ref = c.crm_customer_id
""").fetchone()
print(f"Collections cases to Customers: {res[0]:,} unique case customers -> {res[1]:,} matched in CRM!")

# Check matching between customers and card_accounts using phone / DOB / postal
# cardholder_phone_raw vs primary_phone_raw / primary_phone_e164
print("\nTesting phone match on Card Accounts...")
res_cards = con.execute("""
    SELECT count(DISTINCT ca.card_account_id) AS total_cards,
           count(DISTINCT CASE WHEN c.crm_customer_id IS NOT NULL THEN ca.card_account_id END) AS cards_matched_by_phone
    FROM (SELECT card_account_id, regexp_replace(cardholder_phone_raw, '[^0-9]', '', 'g') AS clean_phone FROM card_accounts LIMIT 50000) ca
    LEFT JOIN (SELECT crm_customer_id, regexp_replace(primary_phone_e164, '[^0-9]', '', 'g') AS clean_phone FROM customers) c
      ON ca.clean_phone = c.clean_phone
""").fetchone()
print(f"Sample 50k Cards: {res_cards[0]:,} cards -> {res_cards[1]:,} matched to CRM by phone!")

# Check matching between customers and loan_accounts
print("\nTesting phone match on Loan Accounts...")
res_loans = con.execute("""
    SELECT count(DISTINCT la.loan_id) AS total_loans,
           count(DISTINCT CASE WHEN c.crm_customer_id IS NOT NULL THEN la.loan_id END) AS loans_matched_by_phone
    FROM (SELECT loan_id, regexp_replace(borrower_phone_raw, '[^0-9]', '', 'g') AS clean_phone FROM loan_accounts LIMIT 50000) la
    LEFT JOIN (SELECT crm_customer_id, regexp_replace(primary_phone_e164, '[^0-9]', '', 'g') AS clean_phone FROM customers) c
      ON la.clean_phone = c.clean_phone
""").fetchone()
print(f"Sample 50k Loans: {res_loans[0]:,} loans -> {res_loans[1]:,} matched to CRM by phone!")
