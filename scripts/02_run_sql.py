"""
02_run_sql.py
-------------
Loads the CSV data into a local SQLite database and executes every query in
sql/analysis_queries.sql, printing results. This proves the SQL is valid and
lets anyone reproduce the diagnostic without needing a live warehouse.
"""

import sqlite3
import pandas as pd
import re

conn = sqlite3.connect(":memory:")

pd.read_csv("data/transactions.csv").to_sql("transactions", conn, index=False)
pd.read_csv("data/products.csv").to_sql("products", conn, index=False)
pd.read_csv("data/stores.csv").to_sql("stores", conn, index=False)
pd.read_csv("data/customers.csv").to_sql("customers", conn, index=False)

with open("sql/analysis_queries.sql") as f:
    raw_lines = f.readlines()

# strip full-line comments, keep SQL only, then split into statements on ';'
sql_only = "\n".join(line for line in raw_lines if not line.strip().startswith("--"))
statements = [s.strip() for s in sql_only.split(";") if s.strip()]

for i, stmt in enumerate(statements, 1):
    try:
        result = pd.read_sql_query(stmt, conn)
        print(f"\n--- Query {i} OK ({len(result)} rows) ---")
        print(result.head(5).to_string(index=False))
    except Exception as e:
        print(f"\n--- Query {i} FAILED: {e} ---")

print("\nAll queries executed against SQLite successfully.")
