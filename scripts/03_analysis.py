"""
03_analysis.py
---------------
Core analytical diagnostic:
  1. Revenue & margin decomposition by category / region / segment
  2. Discounting-vs-profitability relationship (price elasticity view)
  3. Product & segment-level opportunity sizing
  4. Scenario / sensitivity analysis for a proposed pricing action

Outputs:
  visuals/*.png          -- charts used in README and Tableau storyboard
  excel/pricing_diagnostic_summary.xlsx -- exec-ready workbook (see 04_build_excel.py)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

plt.rcParams["figure.dpi"] = 140
plt.rcParams["font.family"] = "DejaVu Sans"

tx = pd.read_csv("data/transactions.csv", parse_dates=["order_date"])
products = pd.read_csv("data/products.csv")

print("=" * 70)
print("RETAIL PROFITABILITY & PRICING DIAGNOSTIC")
print("=" * 70)

# ---------------------------------------------------------------------------
# 1. Headline metrics
# ---------------------------------------------------------------------------
total_rev = tx.revenue.sum()
total_profit = tx.gross_profit.sum()
blended_margin = total_profit / total_rev
print(f"\nTotal Revenue:        ${total_rev:,.0f}")
print(f"Total Gross Profit:   ${total_profit:,.0f}")
print(f"Blended Margin:       {blended_margin:.1%}")
print(f"Share of txns discounted: {(tx.discount_pct>0).mean():.1%}")

# ---------------------------------------------------------------------------
# 2. Category performance
# ---------------------------------------------------------------------------
cat = tx.groupby("category").agg(
    revenue=("revenue", "sum"),
    profit=("gross_profit", "sum"),
    avg_discount=("discount_pct", "mean"),
).reset_index()
cat["margin_pct"] = cat.profit / cat.revenue
cat = cat.sort_values("revenue", ascending=False)

fig, ax1 = plt.subplots(figsize=(9, 5))
ax2 = ax1.twinx()
ax1.bar(cat.category, cat.revenue / 1000, color="#2C5F8A", label="Revenue ($k)")
ax2.plot(cat.category, cat.margin_pct * 100, color="#E8743B", marker="o", linewidth=2.5, label="Margin %")
ax1.set_ylabel("Revenue ($ thousands)")
ax2.set_ylabel("Gross Margin (%)")
ax1.set_title("Revenue vs. Gross Margin by Category", fontsize=13, fontweight="bold")
plt.xticks(rotation=20, ha="right")
fig.tight_layout()
fig.savefig("visuals/01_revenue_margin_by_category.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# 3. Discount depth vs margin ("margin erosion curve") -- the key finding
# ---------------------------------------------------------------------------
bins = [-0.01, 0, 0.10, 0.20, 0.30, 1.0]
labels = ["0% (Full Price)", "1-10%", "11-20%", "21-30%", "31%+"]
tx["discount_band"] = pd.cut(tx.discount_pct, bins=bins, labels=labels)

erosion = tx.groupby("discount_band", observed=True).agg(
    revenue=("revenue", "sum"),
    profit=("gross_profit", "sum"),
    units=("quantity", "sum"),
).reset_index()
erosion["margin_pct"] = erosion.profit / erosion.revenue
erosion["profit_per_unit"] = erosion.profit / erosion.units

fig, ax = plt.subplots(figsize=(9, 5))
colors = ["#2C5F8A" if m >= 0 else "#C0392B" for m in erosion.margin_pct]
ax.bar(erosion.discount_band, erosion.margin_pct * 100, color=colors)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_ylabel("Gross Margin (%)")
ax.set_title("Margin Erosion Curve: Discount Depth vs. Realized Margin", fontsize=13, fontweight="bold")
for i, v in enumerate(erosion.margin_pct * 100):
    ax.text(i, v + (1.5 if v >= 0 else -3), f"{v:.1f}%", ha="center", fontweight="bold")
fig.tight_layout()
fig.savefig("visuals/02_margin_erosion_curve.png")
plt.close(fig)

print("\nKEY FINDING -- Margin Erosion Curve:")
print(erosion.to_string(index=False))
print("\n-> Discounts beyond ~30% turn gross-profit NEGATIVE on average: volume")
print("   lift no longer offsets the price concession at that depth.")

# ---------------------------------------------------------------------------
# 4. Region x Category profitability heatmap-style table
# ---------------------------------------------------------------------------
pivot = tx.pivot_table(index="region", columns="category", values="gross_profit", aggfunc="sum") / 1000

fig, ax = plt.subplots(figsize=(9, 5))
im = ax.imshow(pivot.values, cmap="RdYlGn", aspect="auto")
ax.set_xticks(range(len(pivot.columns)))
ax.set_xticklabels(pivot.columns, rotation=20, ha="right")
ax.set_yticks(range(len(pivot.index)))
ax.set_yticklabels(pivot.index)
for i in range(len(pivot.index)):
    for j in range(len(pivot.columns)):
        ax.text(j, i, f"{pivot.values[i,j]:.0f}k", ha="center", va="center", fontsize=8)
ax.set_title("Gross Profit ($k) by Region x Category", fontsize=13, fontweight="bold")
fig.colorbar(im, ax=ax, label="Gross Profit ($k)")
fig.tight_layout()
fig.savefig("visuals/03_region_category_heatmap.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# 5. Bottom-margin products -- repricing / delist candidates
# ---------------------------------------------------------------------------
prod_perf = tx.groupby("product_id").agg(
    revenue=("revenue", "sum"),
    profit=("gross_profit", "sum"),
    units=("quantity", "sum"),
    avg_discount=("discount_pct", "mean"),
).reset_index()
prod_perf = prod_perf.merge(products[["product_id", "category", "product_name", "list_price"]], on="product_id")
prod_perf["margin_pct"] = prod_perf.profit / prod_perf.revenue
material = prod_perf[prod_perf.revenue > 1000].sort_values("margin_pct")

bottom20 = material.head(20)
print(f"\nBottom-20 margin products (material revenue >$1,000): avg margin {bottom20.margin_pct.mean():.1%}")
print(f"Combined revenue exposure: ${bottom20.revenue.sum():,.0f} at risk of continued erosion")
bottom20.to_csv("data/bottom20_margin_products.csv", index=False)

# ---------------------------------------------------------------------------
# 6. Customer segment profitability
# ---------------------------------------------------------------------------
seg = tx.groupby("customer_segment").agg(
    revenue=("revenue", "sum"),
    profit=("gross_profit", "sum"),
    customers=("customer_id", "nunique"),
    avg_discount=("discount_pct", "mean"),
).reset_index()
seg["margin_pct"] = seg.profit / seg.revenue
seg["revenue_per_customer"] = seg.revenue / seg.customers
seg = seg.sort_values("profit", ascending=False)

fig, ax = plt.subplots(figsize=(9, 5))
sc = ax.scatter(seg.avg_discount * 100, seg.margin_pct * 100, s=seg.revenue / 3000,
                 c=range(len(seg)), cmap="viridis", alpha=0.85, edgecolors="black")
for _, r in seg.iterrows():
    ax.annotate(r.customer_segment, (r.avg_discount * 100, r.margin_pct * 100),
                textcoords="offset points", xytext=(8, 5), fontsize=9, fontweight="bold")
ax.set_xlabel("Avg. Discount Depth (%)")
ax.set_ylabel("Gross Margin (%)")
ax.set_title("Customer Segment: Discount Reliance vs. Margin\n(bubble size = revenue)",
              fontsize=12, fontweight="bold")
fig.tight_layout()
fig.savefig("visuals/04_segment_discount_vs_margin.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# 7. Scenario / sensitivity analysis
#    "What if we cap Grocery & Electronics discounts at 20% (down from
#    uncapped today) to protect margin on already-thin categories?"
# ---------------------------------------------------------------------------
capped_categories = ["Grocery", "Electronics"]
cap = 0.20

scenario = tx.copy()
mask = scenario.category.isin(capped_categories) & (scenario.discount_pct > cap)
# Assume capping discount reduces qty lift proportionally (elasticity-consistent)
# but simple, transparent approximation for the diagnostic:
scenario.loc[mask, "unit_price"] = scenario.loc[mask, "list_price"] * (1 - cap)
scenario.loc[mask, "discount_pct"] = cap
# apply a conservative 15% volume pull-back on formerly deep-discounted units
scenario.loc[mask, "quantity"] = (scenario.loc[mask, "quantity"] * 0.85).round().clip(lower=1)
scenario["revenue"] = scenario.unit_price * scenario.quantity
scenario["total_cost"] = scenario["unit_cost"] * scenario["quantity"]
scenario["gross_profit"] = scenario.revenue - scenario.total_cost

baseline_profit = tx.gross_profit.sum()
scenario_profit = scenario.gross_profit.sum()
baseline_rev = tx.revenue.sum()
scenario_rev = scenario.revenue.sum()

print("\n" + "=" * 70)
print("SCENARIO: Cap Grocery & Electronics discounts at 20%")
print("=" * 70)
print(f"Baseline revenue:      ${baseline_rev:,.0f}")
print(f"Scenario revenue:      ${scenario_rev:,.0f}  ({(scenario_rev/baseline_rev-1):+.1%})")
print(f"Baseline gross profit: ${baseline_profit:,.0f}")
print(f"Scenario gross profit: ${scenario_profit:,.0f}  ({(scenario_profit/baseline_profit-1):+.1%})")
print(f"Estimated annualized profit lift: ${(scenario_profit-baseline_profit):,.0f}")

scenario_summary = pd.DataFrame({
    "metric": ["Revenue", "Gross Profit", "Margin %"],
    "baseline": [baseline_rev, baseline_profit, baseline_profit/baseline_rev],
    "scenario": [scenario_rev, scenario_profit, scenario_profit/scenario_rev],
})
scenario_summary.to_csv("data/scenario_summary.csv", index=False)

fig, ax = plt.subplots(figsize=(7, 5))
x = np.arange(2)
width = 0.35
ax.bar(x - width/2, [baseline_rev/1000, baseline_profit/1000], width, label="Baseline", color="#95A5A6")
ax.bar(x + width/2, [scenario_rev/1000, scenario_profit/1000], width, label="Scenario (20% cap)", color="#2C5F8A")
ax.set_xticks(x)
ax.set_xticklabels(["Revenue ($k)", "Gross Profit ($k)"])
ax.set_title("Scenario Analysis: Discount Cap Impact", fontsize=13, fontweight="bold")
ax.legend()
fig.tight_layout()
fig.savefig("visuals/05_scenario_impact.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# 8. Save consolidated summary tables for the Excel workbook
# ---------------------------------------------------------------------------
cat.to_csv("data/summary_category.csv", index=False)
erosion.to_csv("data/summary_discount_bands.csv", index=False)
seg.to_csv("data/summary_segment.csv", index=False)
pivot.reset_index().to_csv("data/summary_region_category.csv", index=False)

print("\nAll analysis outputs written to /data and /visuals.")
