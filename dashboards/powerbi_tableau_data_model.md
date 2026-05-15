# Power BI / Tableau Data Model

## Recommended Tables
Use `fact_orders_customer_campaign.csv` as the central fact table. Add `customers_clean.csv`, `orders_clean.csv`, `campaigns_clean.csv`, `marketing_kpis_by_channel.csv`, `segment_performance.csv`, `budget_reallocation.csv`, `category_performance.csv`, `country_performance.csv`, `device_performance.csv` and `monthly_revenue.csv`.

## Suggested Relationships
| From Table | Key | To Table | Key | Relationship |
|---|---|---|---|---|
| orders_clean | customer_id | customers_clean | customer_id | Many-to-one |
| orders_clean | campaign_id | campaigns_clean | campaign_id | Many-to-one |
| fact_orders_customer_campaign | customer_id | customers_clean | customer_id | Many-to-one |
| fact_orders_customer_campaign | campaign_id | campaigns_clean | campaign_id | Many-to-one |

## Suggested Measures
Revenue, Profit, Profit Margin, Orders, Return Rate, Net Revenue After Returns, ROAS, ROI, CPA, CPC, CTR and Conversion Rate.
