-- Top 10 campaigns by ROAS
SELECT campaign_id, campaign_name, channel, ROUND(spend, 2) AS spend, ROUND(revenue_attributed, 2) AS revenue_attributed, ROUND(revenue_attributed / NULLIF(spend, 0), 4) AS roas FROM campaigns ORDER BY roas DESC LIMIT 10;
