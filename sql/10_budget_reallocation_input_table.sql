-- Budget reallocation input table
SELECT channel, ROUND(total_spend, 2) AS current_spend, ROUND(total_revenue, 2) AS attributed_revenue, ROUND(roas, 4) AS roas, ROUND(roi, 4) AS roi, ROUND(cpa, 2) AS cpa, ROUND(conversion_rate, 4) AS conversion_rate, ROUND(avg_budget_efficiency_score, 1) AS budget_efficiency_score FROM channel_kpis ORDER BY budget_efficiency_score DESC;
