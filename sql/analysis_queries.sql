-- ============================================================================
-- Retail Profitability & Pricing Diagnostic — Analysis Queries
-- Target dialect: ANSI SQL / SQLite (validated via scripts/02_run_sql.py)
-- Tables: transactions, products, stores, customers
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Revenue, margin, and discount penetration by category
-- ----------------------------------------------------------------------------
SELECT
    category,
    COUNT(DISTINCT transaction_id)            AS transactions,
    SUM(revenue)                               AS total_revenue,
    SUM(gross_profit)                          AS total_gross_profit,
    ROUND(SUM(gross_profit) * 1.0 / SUM(revenue), 4)          AS blended_margin_pct,
    ROUND(AVG(discount_pct), 4)                                AS avg_discount_pct,
    ROUND(SUM(CASE WHEN discount_pct > 0 THEN 1 ELSE 0 END) * 1.0
          / COUNT(*), 4)                                       AS pct_txns_discounted
FROM transactions
GROUP BY category
ORDER BY total_revenue DESC;

-- ----------------------------------------------------------------------------
-- 2. Margin erosion curve: discount depth vs. realized margin
--    (identifies the tipping point where discounting stops paying for itself)
-- ----------------------------------------------------------------------------
SELECT
    CASE
        WHEN discount_pct = 0        THEN '0% (Full Price)'
        WHEN discount_pct <= 0.10    THEN '1-10%'
        WHEN discount_pct <= 0.20    THEN '11-20%'
        WHEN discount_pct <= 0.30    THEN '21-30%'
        ELSE '31%+'
    END                                             AS discount_band,
    COUNT(*)                                        AS transactions,
    SUM(quantity)                                   AS units_sold,
    SUM(revenue)                                    AS total_revenue,
    ROUND(SUM(gross_profit) * 1.0 / SUM(revenue), 4) AS margin_pct,
    ROUND(SUM(gross_profit) * 1.0 / SUM(quantity), 2) AS profit_per_unit
FROM transactions
GROUP BY discount_band
ORDER BY MIN(discount_pct);

-- ----------------------------------------------------------------------------
-- 3. Region x Category profitability matrix
-- ----------------------------------------------------------------------------
SELECT
    region,
    category,
    SUM(revenue)                                     AS revenue,
    SUM(gross_profit)                                AS gross_profit,
    ROUND(SUM(gross_profit) * 1.0 / SUM(revenue), 4)  AS margin_pct
FROM transactions
GROUP BY region, category
ORDER BY region, gross_profit DESC;

-- ----------------------------------------------------------------------------
-- 4. Bottom-margin products (candidates for repricing or delist)
-- ----------------------------------------------------------------------------
SELECT
    t.product_id,
    p.category,
    p.product_name,
    p.list_price,
    SUM(t.quantity)                                    AS units_sold,
    SUM(t.revenue)                                     AS revenue,
    SUM(t.gross_profit)                                AS gross_profit,
    ROUND(SUM(t.gross_profit) * 1.0 / SUM(t.revenue), 4) AS margin_pct,
    ROUND(AVG(t.discount_pct), 4)                        AS avg_discount_pct
FROM transactions t
JOIN products p ON p.product_id = t.product_id
GROUP BY t.product_id, p.category, p.product_name, p.list_price
HAVING SUM(t.revenue) > 1000
ORDER BY margin_pct ASC
LIMIT 20;

-- ----------------------------------------------------------------------------
-- 5. Customer segment profitability & discount reliance
-- ----------------------------------------------------------------------------
SELECT
    customer_segment,
    COUNT(DISTINCT customer_id)                          AS customers,
    SUM(revenue)                                          AS revenue,
    SUM(gross_profit)                                     AS gross_profit,
    ROUND(SUM(gross_profit) * 1.0 / SUM(revenue), 4)      AS margin_pct,
    ROUND(SUM(revenue) * 1.0 / COUNT(DISTINCT customer_id), 2) AS revenue_per_customer,
    ROUND(AVG(discount_pct), 4)                           AS avg_discount_pct
FROM transactions
GROUP BY customer_segment
ORDER BY gross_profit DESC;

-- ----------------------------------------------------------------------------
-- 6. Monthly revenue & margin trend (for seasonality / trend line in Tableau)
-- ----------------------------------------------------------------------------
SELECT
    strftime('%Y-%m', order_date)                        AS year_month,
    SUM(revenue)                                          AS revenue,
    SUM(gross_profit)                                     AS gross_profit,
    ROUND(SUM(gross_profit) * 1.0 / SUM(revenue), 4)      AS margin_pct
FROM transactions
GROUP BY year_month
ORDER BY year_month;

-- ----------------------------------------------------------------------------
-- 7. Store-size performance (assortment / footprint opportunity)
-- ----------------------------------------------------------------------------
SELECT
    s.store_size,
    COUNT(DISTINCT t.store_id)                            AS stores,
    SUM(t.revenue)                                        AS revenue,
    ROUND(SUM(t.revenue) * 1.0 / COUNT(DISTINCT t.store_id), 2) AS revenue_per_store,
    ROUND(SUM(t.gross_profit) * 1.0 / SUM(t.revenue), 4)  AS margin_pct
FROM transactions t
JOIN stores s ON s.store_id = t.store_id
GROUP BY s.store_size
ORDER BY revenue DESC;
