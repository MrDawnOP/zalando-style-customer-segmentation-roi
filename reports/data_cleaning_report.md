# Data Cleaning Report

## Cleaning Steps Completed
1. Loaded customer, order and campaign datasets.
2. Checked missing values and duplicate IDs.
3. Converted date fields to datetime format.
4. Created `order_month`, `net_revenue_after_returns`, `gross_margin_pct` and `is_discounted_order`.
5. Created campaign KPIs: ROI, ROAS, CTR, CPC, CPA, conversion rate, revenue per click, campaign profit and budget efficiency score.
6. Created customer KPIs: CLV, AOV, purchase frequency, days since last purchase, discount dependency, return rate and high-value flag.
7. Created RFM scores and customer segments.
8. Created churn-risk score and churn-risk label.
9. Exported clean CSVs and SQLite database.

## Notes
Synthetic data uses a fixed seed and is designed for portfolio demonstration. Net revenue after returns excludes returned orders. Churn scoring is rules-based for business explainability.
