import duckdb
import os

data_dir = r"C:\Users\dadid\.gemini\antigravity\scratch\collections-ai\data\raw\maple_data\maple_collections_release"
os.chdir(data_dir)
con = duckdb.connect()

print("=== COLLECTIONS CASES ACCOUNTS LINK ===")
# How do collections cases link to accounts?
cases = con.execute("""
    SELECT case_id, coll_customer_ref, primary_account_id, primary_product, account_ids 
    FROM read_csv_auto('data/collections_cases.csv') 
    LIMIT 10
""").fetchall()
for r in cases:
    print(" ", r)

print("\n=== LOOKING UP PRIMARY ACCOUNT IN CARD ACCOUNTS ===")
card_acc = cases[0][2]
print(f"Looking up primary_account_id: {card_acc}")
res = con.execute("""
    SELECT card_account_id, src_customer_ref, cardholder_name_raw, cardholder_phone_raw
    FROM read_csv_auto('data/card_accounts.csv')
    WHERE card_account_id = ?
""", [card_acc]).fetchall()
print(" Found in card_accounts:", res)

print("\n=== LOOKING UP CUSTOMER IN CUSTOMERS ===")
crm_cust = cases[0][1]
print(f"Looking up coll_customer_ref: {crm_cust}")
res_c = con.execute("""
    SELECT crm_customer_id, full_name_raw, date_of_birth, primary_phone_raw, primary_phone_e164
    FROM read_csv_auto('data/customers.csv')
    WHERE crm_customer_id = ?
""", [crm_cust]).fetchall()
print(" Found in customers:", res_c)
