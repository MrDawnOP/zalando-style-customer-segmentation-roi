-- Total revenue, profit, orders and margin
SELECT ROUND(SUM(revenue), 2) AS total_revenue, ROUND(SUM(profit), 2) AS total_profit, COUNT(DISTINCT order_id) AS total_orders, ROUND(SUM(profit) * 1.0 / NULLIF(SUM(revenue), 0), 4) AS profit_margin FROM orders;
