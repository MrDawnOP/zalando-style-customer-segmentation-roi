# Zalando-Style Customer Segmentation and Marketing ROI Analysis

> **Portfolio project:** Fictional/simulated European fashion e-commerce analytics project inspired by a Zalando-style business model. This project does **not** use confidential Zalando data. All datasets are synthetic and reproducible using a fixed random seed.

## Business Problem
A European fashion e-commerce company wants to improve marketing profitability, customer retention and budget allocation. Leadership needs to understand which customer segments generate value, which campaigns waste spend, which channels deserve more budget and which customers are at risk of churn.

## Dataset Overview
| Dataset | Rows | Description |
|---|---:|---|
| `customers_raw.csv` | 10,000 | Customer profile, acquisition, device, region and category preference |
| `orders_raw.csv` | 50,000 | Order-level revenue, cost, profit, discount, returns and campaign attribution |
| `campaigns_raw.csv` | 120 | Campaign spend, impressions, clicks, conversions and attributed revenue |

**Countries:** Germany, UK, France, Italy, Spain, Netherlands, Poland  
**Channels:** Google Search, Meta Ads, TikTok Ads, Email, Affiliate, Organic Search, Display Ads  
**Categories:** Shoes, Dresses, Jackets, Sportswear, Accessories, Jeans, Beauty, Bags

## Tools Used
Python, Pandas, NumPy, Matplotlib, SQLite/SQL, Power BI/Tableau-ready CSV exports, Jupyter Notebook.

## Project Workflow
1. Generate or load synthetic e-commerce customer, order and campaign data.
2. Clean data, validate types, remove duplicates and derive metrics.
3. Build marketing, customer and business KPIs.
4. Perform exploratory analysis across month, channel, country, category, device and segment.
5. Apply RFM segmentation.
6. Create churn-risk labels.
7. Analyse ROI, ROAS, CPA, CPC, CTR and conversion rate.
8. Build budget reallocation recommendations.
9. Export BI-ready datasets and executive visuals.

## Key KPIs
Marketing KPIs include total spend, total revenue, ROI, ROAS, CTR, CPC, CPA, conversion rate, revenue per click, campaign profit and budget efficiency score.

Customer KPIs include CLV, AOV, purchase frequency, repeat purchase rate, churn-risk score, days since last purchase, discount dependency, return rate and high-value customer flag.

Business KPIs include revenue, profit, profit margin, orders, returns, net revenue after returns, category performance, country performance and device performance.

## Analysis Steps
### Data Cleaning and Preparation
Checked missing values and duplicate IDs, converted date fields, created derived metrics, joined customers/orders/campaigns and exported cleaned datasets.

### Exploratory Data Analysis
Built monthly revenue, category profit, spend by channel, revenue by country, segment distribution, return-rate and device-performance outputs.

### Marketing ROI Analysis
Compared ROI and ROAS across seven channels, identified high-spend low-conversion campaigns, ranked high-ROAS campaigns and recommended budget movements.

### Customer Segmentation
Used RFM segmentation with recency, frequency and monetary value to create Champions, Loyal Customers, Potential Loyalists, New Customers, At Risk, Hibernating, Discount Seekers and High-Value Customers.

### Churn-Risk Analysis
Created churn-risk labels from days since last purchase, purchase frequency, low engagement, discount dependency and return rate.

## Key Insights
- **Email generated the strongest ROAS** at approximately **13.62**.
- **Display Ads showed the weakest ROI** at approximately **-0.68**.
- **High-Value Customers generated the highest revenue** with approximately **€2,090,526**.
- **Dresses had the highest return rate** at approximately **19.3%**.
- **Germany was the top revenue market** with approximately **€1,004,139**.

## Recommendations
1. Increase budget for high-ROAS channels such as Email and Organic Search.
2. Reduce spend on campaigns with high CPA and low conversion.
3. Create retention campaigns for At-Risk and Potential Loyalist customers.
4. Use personalised offers for Champions and Loyal Customers.
5. Reduce excessive discounting for customers already likely to purchase.
6. Improve return-rate monitoring for low-margin or high-return categories.
7. Build a monthly marketing performance dashboard for leadership.

## Dashboard Screenshots Placeholder
| Dashboard Page | Screenshot Placeholder |
|---|---|
| Executive Overview | `dashboards/screenshots/page_1_executive_overview.png` |
| Marketing Performance | `dashboards/screenshots/page_2_marketing_performance.png` |
| Customer Segmentation | `dashboards/screenshots/page_3_customer_segmentation.png` |
| Business Recommendations | `dashboards/screenshots/page_4_business_recommendations.png` |

## How to Run the Project
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_project.py
```

## Folder Structure
```text
zalando_style_customer_segmentation_roi/
├── README.md
├── requirements.txt
├── business_requirements_document.md
├── executive_summary.md
├── kpi_dictionary.md
├── data/
│   ├── raw/
│   └── processed/
├── dashboards/
├── notebooks/
├── reports/
├── scripts/
├── sql/
└── visuals/
```

## CV Bullet Points
- Built an end-to-end e-commerce marketing analytics project using SQL, Python and BI-ready datasets to analyse campaign ROI, customer segmentation and revenue performance.
- Applied RFM segmentation to 10,000+ customers, identifying high-value, at-risk and discount-dependent customer groups for targeted marketing actions.
- Calculated marketing KPIs including ROAS, ROI, CPA, CPC, CTR and conversion rate across 100+ campaigns to recommend budget reallocation.
- Created executive-ready insights and dashboard wireframes to support marketing spend optimisation, customer retention and commercial decision-making.

## Interview Talking Points
### Business Analyst Role
I translated a broad commercial problem into KPI definitions, requirements, segment logic and a budget reallocation recommendation that leadership could act on.

### Data Analyst Role
I used Python, SQL and BI-ready datasets to clean data, calculate KPIs, segment customers, identify churn risk and create executive visuals.

### Marketing Analyst Role
I evaluated channel efficiency, campaign ROI, ROAS, CPA and conversion quality, then recommended budget shifts toward high-intent and retention channels.
