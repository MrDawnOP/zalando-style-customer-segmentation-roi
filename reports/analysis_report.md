# Analysis Report

## 1. Data Cleaning and Preparation
The project generated three raw datasets: customers, orders and campaigns. The workflow removed duplicate IDs, converted date fields, created derived metrics and joined all data into `fact_orders_customer_campaign.csv`.

| Check | Result |
|---|---:|
| Customer rows | 10,000 |
| Order rows | 50,000 |
| Campaign rows | 120 |
| Duplicate customer IDs | 0 |
| Duplicate order IDs | 0 |
| Duplicate campaign IDs | 0 |

## 2. Exploratory Data Analysis
Revenue trend, category profit, marketing spend, country revenue, customer segments, returns and device performance are exported in `data/processed/` and visualised in `visuals/`.

## 3. Marketing ROI Analysis
- Email has high ROAS but limited scale.
- Organic Search is efficient because spend is low and intent is strong.
- Google Search has higher CPA but strong purchase intent.
- Meta Ads generates traffic but weaker conversion quality.
- TikTok Ads supports new acquisition but needs retention follow-up.
- Display Ads has weaker direct-response performance and should be capped.

## 4. Customer Segmentation
| Segment | Customers | Revenue | Avg CLV |
|---|---:|---:|---:|
| High-Value Customers | 1,960 | €2,090,526 | €1,067 |
| Potential Loyalists | 2,555 | €584,166 | €229 |
| At Risk | 1,290 | €491,673 | €381 |
| Hibernating | 2,396 | €361,929 | €151 |
| Champions | 671 | €355,310 | €530 |
| Loyal Customers | 698 | €290,234 | €416 |
| Discount Seekers | 430 | €138,956 | €323 |


## 5. Churn-Risk Analysis
High-risk customers are exported to `churn_risk_customer_list.csv` for retention targeting.

## 6. Budget Reallocation Recommendation
- **Affiliate**: current €440,880, recommended €484,510, change €43,630. Positive partner-led acquisition economics with moderate scalability.
- **Display Ads**: current €616,427, recommended €464,523, change €-151,904. Lowest conversion efficiency and high spend relative to attributed revenue.
- **Email**: current €88,662, recommended €113,211, change €24,549. High ROAS and strong retention/intent efficiency; scale carefully due to audience ceiling.
- **Google Search**: current €714,440, recommended €837,484, change €123,044. Higher CPA than retention channels, but stronger purchase intent and healthy conversion quality.
- **Meta Ads**: current €836,226, recommended €770,192, change €-66,034. High traffic volume but weaker conversion quality and lower ROI than high-intent channels.
- **Organic Search**: current €128,241, recommended €158,380, change €30,139. High ROAS and strong retention/intent efficiency; scale carefully due to audience ceiling.
- **TikTok Ads**: current €600,597, recommended €597,172, change €-3,425. Useful for new customer acquisition, but lower retention and weaker immediate ROAS.
