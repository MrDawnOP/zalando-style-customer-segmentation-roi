-- Churn-risk customer list
SELECT customer_id, country, customer_segment, days_since_last_purchase, number_of_orders, ROUND(total_spend, 2) AS total_spend, ROUND(discount_dependency, 4) AS discount_dependency, ROUND(return_rate, 4) AS return_rate, churn_risk_score, churn_risk_label FROM customers WHERE churn_risk_label = 'High risk' ORDER BY churn_risk_score DESC, total_spend DESC;
