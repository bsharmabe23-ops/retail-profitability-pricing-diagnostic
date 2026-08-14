"""
01_generate_data.py
--------------------
Generates a realistic synthetic transaction-level retail dataset used
throughout this project. In a real engagement this script would be replaced
by a data-extraction step (SQL pull from a POS / ERP system). It is included
here so the full pipeline is reproducible end-to-end from a single command.

Output: data/transactions.csv  (~45,000 line-item transactions)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)

# ---------------------------------------------------------------------------
# 1. Reference dimensions
# ---------------------------------------------------------------------------
regions = ["Northeast", "Midwest", "South", "West"]
region_weights = [0.28, 0.22, 0.30, 0.20]

customer_segments = ["Value Shopper", "Mainstream", "Premium", "Occasional"]
segment_weights = [0.30, 0.35, 0.15, 0.20]

categories = {
    "Grocery":        {"n_products": 40, "base_price": (2, 15),  "base_cost_pct": 0.78, "elasticity": -1.6},
    "Apparel":        {"n_products": 35, "base_price": (15, 90), "base_cost_pct": 0.48, "elasticity": -2.2},
    "Electronics":    {"n_products": 25, "base_price": (30, 400),"base_cost_pct": 0.72, "elasticity": -1.1},
    "Home & Kitchen":  {"n_products": 30, "base_price": (10, 120),"base_cost_pct": 0.55, "elasticity": -1.8},
    "Health & Beauty": {"n_products": 30, "base_price": (5, 45),  "base_cost_pct": 0.42, "elasticity": -1.4},
}

stores_per_region = 6
n_customers = 6000
start_date = datetime(2024, 1, 1)
end_date = datetime(2025, 12, 31)
n_days = (end_date - start_date).days

# ---------------------------------------------------------------------------
# 2. Build product catalog
# ---------------------------------------------------------------------------
products = []
pid = 1000
for cat, cfg in categories.items():
    for i in range(cfg["n_products"]):
        base_price = np.round(np.random.uniform(*cfg["base_price"]), 2)
        cost_pct = np.clip(np.random.normal(cfg["base_cost_pct"], 0.06), 0.25, 0.9)
        products.append({
            "product_id": f"P{pid}",
            "category": cat,
            "product_name": f"{cat.split()[0]} Item {i+1}",
            "list_price": base_price,
            "unit_cost": np.round(base_price * cost_pct, 2),
            "elasticity": cfg["elasticity"],
        })
        pid += 1
products = pd.DataFrame(products)
products.to_csv("data/products.csv", index=False)

# ---------------------------------------------------------------------------
# 3. Build store list
# ---------------------------------------------------------------------------
stores = []
sid = 1
for r in regions:
    for s in range(stores_per_region):
        stores.append({"store_id": f"S{sid:03d}", "region": r,
                        "store_size": np.random.choice(["Small", "Medium", "Large"], p=[0.3, 0.5, 0.2])})
        sid += 1
stores = pd.DataFrame(stores)
stores.to_csv("data/stores.csv", index=False)

# ---------------------------------------------------------------------------
# 4. Build customer list
# ---------------------------------------------------------------------------
customers = pd.DataFrame({
    "customer_id": [f"C{100000+i}" for i in range(n_customers)],
    "segment": np.random.choice(customer_segments, size=n_customers, p=segment_weights),
    "region": np.random.choice(regions, size=n_customers, p=region_weights),
    "signup_date": [start_date + timedelta(days=int(np.random.uniform(-400, n_days*0.6))) for _ in range(n_customers)],
})
customers.to_csv("data/customers.csv", index=False)

# ---------------------------------------------------------------------------
# 5. Simulate transactions
# Discount behavior varies by segment; discounting drives incremental units
# via a simple elasticity model, but at the cost of margin -- this is the
# core dynamic the analysis is designed to uncover.
# ---------------------------------------------------------------------------
segment_discount_affinity = {
    "Value Shopper": 0.65,   # heavily driven by promotions
    "Mainstream": 0.35,
    "Premium": 0.12,         # buys mostly at full price
    "Occasional": 0.30,
}

n_transactions = 45000
rows = []
cust_sample = customers.sample(n_transactions, replace=True, random_state=1).reset_index(drop=True)
prod_sample = products.sample(n_transactions, replace=True, random_state=2).reset_index(drop=True)

for i in range(n_transactions):
    cust = cust_sample.loc[i]
    prod = prod_sample.loc[i]
    store_region_pool = stores[stores.region == cust.region]
    store = store_region_pool.sample(1, random_state=i % 97).iloc[0]

    order_date = start_date + timedelta(days=int(np.random.uniform(0, n_days)))

    # discount probability & depth depend on segment + category seasonality
    affinity = segment_discount_affinity[cust.segment]
    is_discounted = np.random.rand() < affinity
    discount_pct = 0.0
    if is_discounted:
        discount_pct = np.round(np.random.choice([0.10, 0.15, 0.20, 0.25, 0.30, 0.40],
                                                   p=[0.30, 0.25, 0.20, 0.12, 0.09, 0.04]), 2)

    unit_price = np.round(prod.list_price * (1 - discount_pct), 2)

    # elasticity-driven quantity: deeper discount -> more units, dampened
    base_qty_lambda = 1.6
    qty_lift = 1 + (discount_pct * abs(prod.elasticity) * 0.9)
    quantity = max(1, np.random.poisson(base_qty_lambda * qty_lift))

    revenue = np.round(unit_price * quantity, 2)
    cost = np.round(prod.unit_cost * quantity, 2)
    profit = np.round(revenue - cost, 2)

    rows.append({
        "transaction_id": f"T{1000000+i}",
        "order_date": order_date.date(),
        "customer_id": cust.customer_id,
        "customer_segment": cust.segment,
        "store_id": store.store_id,
        "region": store.region,
        "product_id": prod.product_id,
        "category": prod.category,
        "list_price": prod.list_price,
        "unit_price": unit_price,
        "discount_pct": discount_pct,
        "quantity": quantity,
        "revenue": revenue,
        "unit_cost": prod.unit_cost,
        "total_cost": cost,
        "gross_profit": profit,
        "gross_margin_pct": np.round(profit / revenue, 4) if revenue > 0 else 0,
    })

df = pd.DataFrame(rows)
df.to_csv("data/transactions.csv", index=False)

print(f"Generated {len(df):,} transactions")
print(f"Total revenue: ${df.revenue.sum():,.0f}")
print(f"Total gross profit: ${df.gross_profit.sum():,.0f}")
print(f"Blended gross margin: {df.gross_profit.sum()/df.revenue.sum():.1%}")
print(f"% of transactions discounted: {(df.discount_pct>0).mean():.1%}")
