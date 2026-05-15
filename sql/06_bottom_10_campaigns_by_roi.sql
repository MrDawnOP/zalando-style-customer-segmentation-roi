-- Bottom 10 campaigns by ROI
SELECT campaign_id, campaign_name, channel, ROUND(spend, 2) AS spend, ROUND(revenue_attributed, 2) AS revenue_attributed, ROUND((revenue_attributed - spend) / NULLIF(spend, 0), 4) AS roi FROM campaigns ORDER BY roi ASC LIMIT 10;
