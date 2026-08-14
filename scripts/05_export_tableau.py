"""
05_export_tableau.py
---------------------
Writes a clean, denormalized extract for Tableau: one row per transaction
line item with all dimensions/measures joined and pre-labeled discount
bands, ready to drop into Tableau Desktop/Public as a data source.
"""

import pandas as pd

tx = pd.read_csv("data/transactions.csv", parse_dates=["order_date"])
products = pd.read_csv("data/products.csv")
stores = pd.read_csv("data/stores.csv")

bins = [-0.01, 0, 0.10, 0.20, 0.30, 1.0]
labels = ["0% (Full Price)", "1-10%", "11-20%", "21-30%", "31%+"]
tx["discount_band"] = pd.cut(tx.discount_pct, bins=bins, labels=labels)

df = tx.merge(stores[["store_id", "store_size"]], on="store_id", how="left")
df["order_month"] = df.order_date.dt.to_period("M").astype(str)
df["order_year"] = df.order_date.dt.year

out_cols = ["transaction_id", "order_date", "order_month", "order_year",
            "region", "store_id", "store_size", "customer_id", "customer_segment",
            "product_id", "category", "list_price", "unit_price", "discount_pct",
            "discount_band", "quantity", "revenue", "total_cost", "gross_profit",
            "gross_margin_pct"]

df[out_cols].to_csv("data/tableau_extract.csv", index=False)
print(f"Tableau extract written: data/tableau_extract.csv ({len(df):,} rows)")
