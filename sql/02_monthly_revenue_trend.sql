-- Monthly revenue trend
SELECT strftime('%Y-%m', order_date) AS order_month, ROUND(SUM(revenue), 2) AS revenue, ROUND(SUM(profit), 2) AS profit, COUNT(order_id) AS orders FROM orders GROUP BY 1 ORDER BY 1;
