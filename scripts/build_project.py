"""
Zalando-Style Customer Segmentation and Marketing ROI Analysis

This script loads the included synthetic raw datasets, cleans the data, creates KPIs,
performs RFM segmentation and churn-risk analysis, exports BI-ready CSVs, creates
SQLite tables, and saves business-friendly Matplotlib visuals.

Data note: this is a fictional/simulated European fashion e-commerce project.
It does not use confidential Zalando data.
"""
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / 'data' / 'raw'
PROCESSED = BASE / 'data' / 'processed'
VISUALS = BASE / 'visuals'
ANALYSIS_DATE = pd.Timestamp('2026-01-01')

for folder in [PROCESSED, VISUALS]:
    folder.mkdir(parents=True, exist_ok=True)

# 1. Load data
customers = pd.read_csv(RAW / 'customers_raw.csv')
orders = pd.read_csv(RAW / 'orders_raw.csv')
campaigns = pd.read_csv(RAW / 'campaigns_raw.csv')

# 2. Clean data and validate types
customers = customers.drop_duplicates(subset=['customer_id']).copy()
orders = orders.drop_duplicates(subset=['order_id']).copy()
campaigns = campaigns.drop_duplicates(subset=['campaign_id']).copy()

customers['signup_date'] = pd.to_datetime(customers['signup_date'])
orders['order_date'] = pd.to_datetime(orders['order_date'])
campaigns['start_date'] = pd.to_datetime(campaigns['start_date'])
campaigns['end_date'] = pd.to_datetime(campaigns['end_date'])

# 3. Derived order KPIs
orders['net_revenue_after_returns'] = np.where(orders['return_flag'] == 1, 0, orders['revenue'])
orders['gross_margin_pct'] = np.where(orders['revenue'] > 0, orders['profit'] / orders['revenue'], 0)
orders['order_month'] = orders['order_date'].dt.to_period('M').astype(str)
orders['is_discounted_order'] = (orders['discount_amount'] > 0).astype(int)

# 4. Campaign KPIs
campaigns['roi'] = np.where(campaigns['spend'] > 0, (campaigns['revenue_attributed'] - campaigns['spend']) / campaigns['spend'], 0)
campaigns['roas'] = np.where(campaigns['spend'] > 0, campaigns['revenue_attributed'] / campaigns['spend'], 0)
campaigns['ctr'] = np.where(campaigns['impressions'] > 0, campaigns['clicks'] / campaigns['impressions'], 0)
campaigns['cpc'] = np.where(campaigns['clicks'] > 0, campaigns['spend'] / campaigns['clicks'], 0)
campaigns['cpa'] = np.where(campaigns['conversions'] > 0, campaigns['spend'] / campaigns['conversions'], np.nan)
campaigns['conversion_rate'] = np.where(campaigns['clicks'] > 0, campaigns['conversions'] / campaigns['clicks'], 0)
campaigns['revenue_per_click'] = np.where(campaigns['clicks'] > 0, campaigns['revenue_attributed'] / campaigns['clicks'], 0)
campaigns['campaign_profit'] = campaigns['revenue_attributed'] - campaigns['spend']

roas_norm = (campaigns['roas'] - campaigns['roas'].min()) / max((campaigns['roas'].max() - campaigns['roas'].min()), 1e-9)
roi_norm = (campaigns['roi'] - campaigns['roi'].min()) / max((campaigns['roi'].max() - campaigns['roi'].min()), 1e-9)
cpa_filled = campaigns['cpa'].fillna(campaigns['cpa'].max())
cpa_inv = 1 - ((cpa_filled - cpa_filled.min()) / max((cpa_filled.max() - cpa_filled.min()), 1e-9))
campaigns['budget_efficiency_score'] = (100 * (0.45 * roas_norm + 0.35 * roi_norm + 0.20 * cpa_inv)).round(1)

# 5. Customer KPIs
customer_agg = orders.groupby('customer_id').agg(
    last_purchase_date=('order_date', 'max'),
    first_purchase_date=('order_date', 'min'),
    number_of_orders=('order_id', 'count'),
    total_spend=('revenue', 'sum'),
    total_profit=('profit', 'sum'),
    net_revenue_after_returns=('net_revenue_after_returns', 'sum'),
    return_count=('return_flag', 'sum'),
    discounted_orders=('is_discounted_order', 'sum'),
    total_discount_amount=('discount_amount', 'sum')
).reset_index()

customer_agg['average_order_value'] = customer_agg['total_spend'] / customer_agg['number_of_orders']
customer_agg['days_since_last_purchase'] = (ANALYSIS_DATE - customer_agg['last_purchase_date']).dt.days
customer_agg['customer_lifetime_value'] = customer_agg['total_spend']
customer_agg['return_rate'] = customer_agg['return_count'] / customer_agg['number_of_orders']
customer_agg['discount_dependency'] = customer_agg['total_discount_amount'] / (customer_agg['total_spend'] + customer_agg['total_discount_amount'])
customer_agg['repeat_purchase_flag'] = (customer_agg['number_of_orders'] > 1).astype(int)
customer_agg['high_value_customer_flag'] = (customer_agg['total_spend'] >= customer_agg['total_spend'].quantile(0.85)).astype(int)

signup_lookup = customers.set_index('customer_id')['signup_date']
signup_aligned = pd.Series(pd.to_datetime(signup_lookup.loc[customer_agg['customer_id']]).to_numpy(), index=customer_agg.index)
tenure_years = ((ANALYSIS_DATE - signup_aligned).dt.days / 365.25).clip(lower=0.1)
customer_agg['purchase_frequency'] = customer_agg['number_of_orders'] / tenure_years
customers = customers.merge(customer_agg, on='customer_id', how='left')

# 6. RFM segmentation
customers['recency'] = customers['days_since_last_purchase']
customers['frequency'] = customers['number_of_orders']
customers['monetary'] = customers['total_spend']
customers['r_score'] = pd.qcut(customers['recency'].rank(method='first'), 5, labels=[5, 4, 3, 2, 1]).astype(int)
customers['f_score'] = pd.qcut(customers['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(int)
customers['m_score'] = pd.qcut(customers['monetary'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(int)
customers['rfm_score'] = customers['r_score'].astype(str) + customers['f_score'].astype(str) + customers['m_score'].astype(str)

def assign_segment(row):
    r, f, m = row['r_score'], row['f_score'], row['m_score']
    if m >= 5 and f >= 4:
        return 'High-Value Customers'
    if r >= 4 and f >= 4 and m >= 4:
        return 'Champions'
    if r >= 3 and f >= 4:
        return 'Loyal Customers'
    if r >= 4 and f <= 3:
        return 'Potential Loyalists'
    if r == 5 and f <= 2:
        return 'New Customers'
    if r <= 2 and f >= 3:
        return 'At Risk'
    if row['discount_dependency'] >= 0.20 and f >= 3:
        return 'Discount Seekers'
    if r <= 2 and f <= 2:
        return 'Hibernating'
    return 'Potential Loyalists'

customers['customer_segment'] = customers.apply(assign_segment, axis=1)
mask_discount = (customers['discount_dependency'] >= 0.24) & customers['customer_segment'].isin(['Potential Loyalists', 'Loyal Customers', 'At Risk'])
customers.loc[mask_discount, 'customer_segment'] = 'Discount Seekers'

# 7. Churn-risk labels
recency_component = np.select(
    [customers['days_since_last_purchase'] > 240, customers['days_since_last_purchase'] > 150, customers['days_since_last_purchase'] > 90],
    [45, 32, 18], default=5
)
frequency_component = np.select([customers['purchase_frequency'] < 1.2, customers['purchase_frequency'] < 2.2], [20, 10], default=0)
discount_component = np.select([customers['discount_dependency'] > 0.28, customers['discount_dependency'] > 0.20], [15, 8], default=0)
return_component = np.select([customers['return_rate'] > 0.22, customers['return_rate'] > 0.14], [15, 8], default=0)
engagement_component = np.where(customers['days_since_last_purchase'] > 120, 12, 0)
customers['churn_risk_score'] = np.clip(recency_component + frequency_component + discount_component + return_component + engagement_component, 0, 100)
customers['churn_risk_label'] = pd.cut(customers['churn_risk_score'], bins=[-1, 34, 64, 100], labels=['Low risk', 'Medium risk', 'High risk']).astype(str)

# 8. BI-ready joined fact table
fact_orders = orders.merge(
    customers[['customer_id', 'age_group', 'gender', 'customer_type', 'acquisition_channel', 'customer_segment', 'churn_risk_label', 'customer_lifetime_value', 'discount_dependency']],
    on='customer_id', how='left'
).merge(
    campaigns[['campaign_id', 'campaign_name', 'campaign_objective', 'spend', 'impressions', 'clicks', 'roas', 'roi', 'cpa', 'budget_efficiency_score']],
    on='campaign_id', how='left'
)

# 9. Aggregate outputs
monthly_revenue = orders.groupby('order_month').agg(revenue=('revenue', 'sum'), profit=('profit', 'sum'), orders=('order_id', 'count')).reset_index()
category_performance = orders.groupby('product_category').agg(revenue=('revenue', 'sum'), profit=('profit', 'sum'), orders=('order_id', 'count'), returns=('return_flag', 'sum'), net_revenue_after_returns=('net_revenue_after_returns', 'sum')).reset_index()
category_performance['profit_margin'] = category_performance['profit'] / category_performance['revenue']
category_performance['return_rate'] = category_performance['returns'] / category_performance['orders']
country_performance = orders.groupby('country').agg(revenue=('revenue', 'sum'), profit=('profit', 'sum'), orders=('order_id', 'count')).reset_index()
device_performance = orders.groupby('device_type').agg(revenue=('revenue', 'sum'), profit=('profit', 'sum'), orders=('order_id', 'count'), returns=('return_flag', 'sum')).reset_index()
device_performance['return_rate'] = device_performance['returns'] / device_performance['orders']
segment_performance = customers.groupby('customer_segment').agg(customers=('customer_id', 'count'), revenue=('total_spend', 'sum'), profit=('total_profit', 'sum'), avg_clv=('customer_lifetime_value', 'mean'), avg_orders=('number_of_orders', 'mean'), avg_discount_dependency=('discount_dependency', 'mean'), avg_return_rate=('return_rate', 'mean')).reset_index()
segment_performance['revenue_share'] = segment_performance['revenue'] / segment_performance['revenue'].sum()
channel_kpis = campaigns.groupby('channel').agg(total_spend=('spend', 'sum'), total_revenue=('revenue_attributed', 'sum'), impressions=('impressions', 'sum'), clicks=('clicks', 'sum'), conversions=('conversions', 'sum'), campaign_profit=('campaign_profit', 'sum'), avg_budget_efficiency_score=('budget_efficiency_score', 'mean')).reset_index()
channel_kpis['roi'] = (channel_kpis['total_revenue'] - channel_kpis['total_spend']) / channel_kpis['total_spend']
channel_kpis['roas'] = channel_kpis['total_revenue'] / channel_kpis['total_spend']
channel_kpis['ctr'] = channel_kpis['clicks'] / channel_kpis['impressions']
channel_kpis['cpc'] = channel_kpis['total_spend'] / channel_kpis['clicks']
channel_kpis['cpa'] = channel_kpis['total_spend'] / channel_kpis['conversions']
channel_kpis['conversion_rate'] = channel_kpis['conversions'] / channel_kpis['clicks']
channel_kpis['revenue_per_click'] = channel_kpis['total_revenue'] / channel_kpis['clicks']

# 10. Recommendation tables
realloc_rows = []
for _, row in channel_kpis.iterrows():
    channel = row['channel']; current = row['total_spend']
    if channel in ['Email', 'Organic Search']:
        mult = 1.22 if channel == 'Email' else 1.18
        reason = 'High ROAS and strong retention/intent efficiency; scale carefully due to audience ceiling.'
        impact = 'Expected to lift profitable repeat revenue and reduce blended CPA.'
    elif channel == 'Google Search':
        mult = 1.12; reason = 'Higher CPA than retention channels, but stronger purchase intent and healthy conversion quality.'; impact = 'Expected to capture high-intent demand and improve qualified acquisition.'
    elif channel == 'Affiliate':
        mult = 1.05; reason = 'Positive partner-led acquisition economics with moderate scalability.'; impact = 'Expected to add incremental orders while keeping CPA controlled.'
    elif channel == 'TikTok Ads':
        mult = 0.95; reason = 'Useful for new customer acquisition, but lower retention and weaker immediate ROAS.'; impact = 'Keep testing creatives while reducing inefficient prospecting pockets.'
    elif channel == 'Meta Ads':
        mult = 0.88; reason = 'High traffic volume but weaker conversion quality and lower ROI than high-intent channels.'; impact = 'Reduce wasted spend and reallocate to retention/high-intent demand.'
    else:
        mult = 0.72; reason = 'Lowest conversion efficiency and high spend relative to attributed revenue.'; impact = 'Lower awareness waste and protect margin.'
    realloc_rows.append({'channel': channel, 'current_spend': round(current, 2), 'recommended_spend': round(current * mult, 2), 'reason_for_change': reason, 'expected_business_impact': impact})
budget_reallocation = pd.DataFrame(realloc_rows)
scale = budget_reallocation['current_spend'].sum() / budget_reallocation['recommended_spend'].sum()
budget_reallocation['recommended_spend'] = (budget_reallocation['recommended_spend'] * scale).round(2)
budget_reallocation['increase_decrease_amount'] = (budget_reallocation['recommended_spend'] - budget_reallocation['current_spend']).round(2)

high_spend_low_conversion = campaigns[(campaigns['spend'] >= campaigns['spend'].quantile(0.70)) & (campaigns['conversion_rate'] <= campaigns['conversion_rate'].quantile(0.30))].sort_values(['spend', 'conversion_rate'], ascending=[False, True]).head(15)
top_roas = campaigns.sort_values('roas', ascending=False).head(15)
bottom_roi = campaigns.sort_values('roi').head(15)
churn_list = customers[customers['churn_risk_label'] == 'High risk'].sort_values(['churn_risk_score', 'customer_lifetime_value'], ascending=[False, False]).head(500)
executive_summary_table = pd.DataFrame([
    {'metric': 'Total revenue', 'value': orders['revenue'].sum()},
    {'metric': 'Total profit', 'value': orders['profit'].sum()},
    {'metric': 'Profit margin', 'value': orders['profit'].sum() / orders['revenue'].sum()},
    {'metric': 'Total orders', 'value': len(orders)},
    {'metric': 'Return rate', 'value': orders['return_flag'].mean()},
    {'metric': 'Net revenue after returns', 'value': orders['net_revenue_after_returns'].sum()},
    {'metric': 'Total marketing spend', 'value': campaigns['spend'].sum()},
    {'metric': 'Overall ROAS', 'value': campaigns['revenue_attributed'].sum() / campaigns['spend'].sum()},
    {'metric': 'Overall ROI', 'value': (campaigns['revenue_attributed'].sum() - campaigns['spend'].sum()) / campaigns['spend'].sum()},
    {'metric': 'Repeat purchase rate', 'value': customers['repeat_purchase_flag'].mean()},
    {'metric': 'High risk customers', 'value': (customers['churn_risk_label'] == 'High risk').sum()}
])

# 11. Export CSVs
exports = {
    'customers_clean.csv': customers,
    'orders_clean.csv': orders,
    'campaigns_clean.csv': campaigns,
    'fact_orders_customer_campaign.csv': fact_orders,
    'rfm_segments.csv': customers[['customer_id', 'recency', 'frequency', 'monetary', 'r_score', 'f_score', 'm_score', 'rfm_score', 'customer_segment', 'churn_risk_score', 'churn_risk_label']],
    'marketing_kpis_by_channel.csv': channel_kpis,
    'channel_kpis.csv': channel_kpis,
    'monthly_revenue.csv': monthly_revenue,
    'category_performance.csv': category_performance,
    'country_performance.csv': country_performance,
    'device_performance.csv': device_performance,
    'segment_performance.csv': segment_performance,
    'budget_reallocation.csv': budget_reallocation,
    'high_spend_low_conversion_campaigns.csv': high_spend_low_conversion,
    'top_roas_campaigns.csv': top_roas,
    'bottom_roi_campaigns.csv': bottom_roi,
    'churn_risk_customer_list.csv': churn_list,
    'executive_summary_table.csv': executive_summary_table,
}
for name, df in exports.items():
    df.to_csv(PROCESSED / name, index=False)

# 12. SQLite database
sqlite_path = PROCESSED / 'zalando_style_marketing_analytics.sqlite'
if sqlite_path.exists(): sqlite_path.unlink()
conn = sqlite3.connect(sqlite_path)
for table, df in [('customers', customers), ('orders', orders), ('campaigns', campaigns), ('channel_kpis', channel_kpis), ('budget_reallocation', budget_reallocation)]:
    df.to_sql(table, conn, index=False)
conn.close()

# 13. Visuals
plt.rcParams.update({'figure.figsize': (10, 6), 'axes.titlesize': 14, 'axes.labelsize': 11})
def money_fmt(ax, axis='y'):
    import matplotlib.ticker as mtick
    formatter = mtick.FuncFormatter(lambda x, pos: f'€{x/1000:,.0f}K')
    if axis == 'y': ax.yaxis.set_major_formatter(formatter)
    else: ax.xaxis.set_major_formatter(formatter)
def save(filename):
    plt.tight_layout(); plt.savefig(VISUALS / filename, dpi=160, bbox_inches='tight'); plt.close()

fig, ax = plt.subplots(); mr = monthly_revenue.sort_values('order_month'); ax.plot(mr['order_month'], mr['revenue'], marker='o'); ax.set_title('Monthly Revenue Trend'); ax.set_xlabel('Order Month'); ax.set_ylabel('Revenue'); ax.tick_params(axis='x', rotation=45); money_fmt(ax); save('01_monthly_revenue_trend.png')
fig, ax = plt.subplots(); ck = channel_kpis.sort_values('roas'); ax.barh(ck['channel'], ck['roas']); ax.set_title('ROAS by Marketing Channel'); ax.set_xlabel('ROAS'); ax.set_ylabel('Marketing Channel'); save('02_roas_by_channel.png')
fig, ax = plt.subplots(figsize=(11, 7)); roi_sample = pd.concat([campaigns.nlargest(8, 'roi'), campaigns.nsmallest(8, 'roi')]).sort_values('roi'); ax.barh(roi_sample['campaign_id'], roi_sample['roi']); ax.set_title('ROI by Campaign: Top and Bottom Campaigns'); ax.set_xlabel('ROI'); ax.set_ylabel('Campaign ID'); save('03_roi_by_campaign.png')
fig, ax = plt.subplots(); ck = channel_kpis.sort_values('cpa'); ax.barh(ck['channel'], ck['cpa']); ax.set_title('CPA by Marketing Channel'); ax.set_xlabel('Cost per Acquisition'); ax.set_ylabel('Marketing Channel'); money_fmt(ax, 'x'); save('04_cpa_by_channel.png')
fig, ax = plt.subplots(); sp = segment_performance.sort_values('revenue'); ax.barh(sp['customer_segment'], sp['revenue']); ax.set_title('Revenue by Customer Segment'); ax.set_xlabel('Revenue'); ax.set_ylabel('Customer Segment'); money_fmt(ax, 'x'); save('05_revenue_by_customer_segment.png')
fig, ax = plt.subplots(); sp = segment_performance.sort_values('avg_clv'); ax.barh(sp['customer_segment'], sp['avg_clv']); ax.set_title('Average CLV by Customer Segment'); ax.set_xlabel('Average Customer Lifetime Value'); ax.set_ylabel('Customer Segment'); money_fmt(ax, 'x'); save('06_clv_by_segment.png')
fig, ax = plt.subplots(); risks = customers['churn_risk_label'].value_counts().reindex(['Low risk', 'Medium risk', 'High risk']).fillna(0); ax.bar(risks.index, risks.values); ax.set_title('Churn Risk Distribution'); ax.set_xlabel('Churn Risk Label'); ax.set_ylabel('Number of Customers'); save('07_churn_risk_distribution.png')
fig, ax = plt.subplots(); ax.scatter(channel_kpis['total_spend'], channel_kpis['total_revenue'], s=90)
for _, row in channel_kpis.iterrows(): ax.annotate(row['channel'], (row['total_spend'], row['total_revenue']), xytext=(4, 4), textcoords='offset points', fontsize=8)
ax.set_title('Marketing Spend vs Attributed Revenue by Channel'); ax.set_xlabel('Total Spend'); ax.set_ylabel('Attributed Revenue'); money_fmt(ax, 'x'); money_fmt(ax, 'y'); save('08_marketing_spend_vs_revenue.png')
fig, ax = plt.subplots(); cp = category_performance.sort_values('profit'); ax.barh(cp['product_category'], cp['profit']); ax.set_title('Product Category Profit Performance'); ax.set_xlabel('Profit'); ax.set_ylabel('Product Category'); money_fmt(ax, 'x'); save('09_product_category_performance.png')
fig, ax = plt.subplots(); co = country_performance.sort_values('revenue'); ax.barh(co['country'], co['revenue']); ax.set_title('Country-Level Revenue'); ax.set_xlabel('Revenue'); ax.set_ylabel('Country'); money_fmt(ax, 'x'); save('10_country_level_revenue.png')

print('Project outputs rebuilt successfully.')
print(f'Customers: {len(customers):,} | Orders: {len(orders):,} | Campaigns: {len(campaigns):,}')
print(f'Processed exports: {len(exports)} | Visuals: {len(list(VISUALS.glob("*.png")))}')
