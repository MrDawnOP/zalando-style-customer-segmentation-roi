-- Customer segment revenue
SELECT customer_segment, COUNT(DISTINCT customer_id) AS customers, ROUND(SUM(total_spend), 2) AS revenue, ROUND(AVG(customer_lifetime_value), 2) AS avg_clv, ROUND(SUM(total_spend) * 1.0 / (SELECT SUM(total_spend) FROM customers), 4) AS revenue_share FROM customers GROUP BY customer_segment ORDER BY revenue DESC;
