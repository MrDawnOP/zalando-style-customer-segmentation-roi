from pathlib import Path
import json
import sqlite3
import textwrap
import zipfile
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

SEED = 42
rng = np.random.default_rng(SEED)
BASE = Path(__file__).resolve().parents[1]
ANALYSIS_DATE = pd.Timestamp('2026-01-01')

# ---------------------------
# Folders
# ---------------------------
folders = [
    'data/raw', 'data/processed', 'notebooks', 'sql', 'reports',
    'dashboards', 'visuals', 'scripts'
]
for f in folders:
    (BASE / f).mkdir(parents=True, exist_ok=True)

# ---------------------------
# Reference dimensions
# ---------------------------
countries = ['Germany', 'UK', 'France', 'Italy', 'Spain', 'Netherlands', 'Poland']
country_probs = np.array([0.24, 0.18, 0.17, 0.13, 0.12, 0.08, 0.08])
channels = ['Google Search', 'Meta Ads', 'TikTok Ads', 'Email', 'Affiliate', 'Organic Search', 'Display Ads']
product_categories = ['Shoes', 'Dresses', 'Jackets', 'Sportswear', 'Accessories', 'Jeans', 'Beauty', 'Bags']
devices = ['Mobile', 'Desktop', 'Tablet']
age_groups = ['18-24', '25-34', '35-44', '45-54', '55+']
genders = ['Female', 'Male', 'Non-binary/Other']
latent_segments = ['Champions', 'Loyal Customers', 'Potential Loyalists', 'New Customers', 'At Risk', 'Hibernating', 'Discount Seekers', 'High-Value Customers']

category_params = {
    'Shoes': {'base_price': 82, 'margin': 0.42, 'return_rate': 0.10},
    'Dresses': {'base_price': 76, 'margin': 0.45, 'return_rate': 0.18},
    'Jackets': {'base_price': 125, 'margin': 0.40, 'return_rate': 0.16},
    'Sportswear': {'base_price': 64, 'margin': 0.43, 'return_rate': 0.09},
    'Accessories': {'base_price': 36, 'margin': 0.55, 'return_rate': 0.05},
    'Jeans': {'base_price': 70, 'margin': 0.38, 'return_rate': 0.13},
    'Beauty': {'base_price': 30, 'margin': 0.58, 'return_rate': 0.03},
    'Bags': {'base_price': 96, 'margin': 0.47, 'return_rate': 0.08},
}

channel_profiles = {
    'Google Search': {'spend_low': 18000, 'spend_high': 65000, 'ctr': 0.045, 'cpc': 1.35, 'conv_rate': 0.060, 'objective': 'High-intent acquisition'},
    'Meta Ads': {'spend_low': 22000, 'spend_high': 82000, 'ctr': 0.036, 'cpc': 0.85, 'conv_rate': 0.026, 'objective': 'Prospecting and retargeting'},
    'TikTok Ads': {'spend_low': 12000, 'spend_high': 52000, 'ctr': 0.050, 'cpc': 0.65, 'conv_rate': 0.022, 'objective': 'New customer acquisition'},
    'Email': {'spend_low': 1200, 'spend_high': 8500, 'ctr': 0.080, 'cpc': 0.12, 'conv_rate': 0.125, 'objective': 'Retention and lifecycle marketing'},
    'Affiliate': {'spend_low': 9000, 'spend_high': 36000, 'ctr': 0.038, 'cpc': 0.72, 'conv_rate': 0.045, 'objective': 'Partner-led acquisition'},
    'Organic Search': {'spend_low': 2500, 'spend_high': 11000, 'ctr': 0.060, 'cpc': 0.18, 'conv_rate': 0.072, 'objective': 'SEO-led acquisition'},
    'Display Ads': {'spend_low': 20000, 'spend_high': 76000, 'ctr': 0.012, 'cpc': 0.55, 'conv_rate': 0.014, 'objective': 'Awareness and remarketing'},
}

# ---------------------------
# Generate campaigns
# ---------------------------
num_campaigns = 120
campaign_rows = []
start_min = pd.Timestamp('2024-01-01')
start_max = pd.Timestamp('2025-10-15')
channel_cycle = np.repeat(channels, repeats=int(np.ceil(num_campaigns / len(channels))))[:num_campaigns]
rng.shuffle(channel_cycle)

for i in range(num_campaigns):
    channel = channel_cycle[i]
    prof = channel_profiles[channel]
    start_date = start_min + pd.Timedelta(days=int(rng.integers(0, (start_max - start_min).days)))
    duration = int(rng.integers(21, 91))
    end_date = min(start_date + pd.Timedelta(days=duration), pd.Timestamp('2025-12-31'))
    spend = float(rng.uniform(prof['spend_low'], prof['spend_high']))
    cpc = max(0.05, rng.normal(prof['cpc'], prof['cpc'] * 0.18))
    ctr = min(max(rng.normal(prof['ctr'], prof['ctr'] * 0.18), 0.002), 0.18)
    clicks = int(max(100, spend / cpc))
    impressions = int(max(clicks / ctr, clicks * 20))
    conv_rate = min(max(rng.normal(prof['conv_rate'], prof['conv_rate'] * 0.22), 0.004), 0.20)
    conversions = int(max(1, clicks * conv_rate))
    campaign_rows.append({
        'campaign_id': f'CMP-{i+1:03d}',
        'campaign_name': f"{channel} | {rng.choice(['Spring Edit','Summer Sale','Back to Work','Holiday Drop','Premium Basics','Sneaker Week','Beauty Boost','VIP Retention'])} | {i+1:03d}",
        'channel': channel,
        'campaign_objective': prof['objective'],
        'start_date': start_date.date().isoformat(),
        'end_date': end_date.date().isoformat(),
        'spend': round(spend, 2),
        'impressions': impressions,
        'clicks': clicks,
        'conversions': conversions,  # updated later to actual order attribution
        'revenue_attributed': 0.0,   # updated later
        'target_audience': rng.choice(['New shoppers', 'Returning customers', 'VIP customers', 'Discount-sensitive customers', 'Young fashion buyers', 'Premium shoppers']),
        'country': rng.choice(countries, p=country_probs),
        'device_type': rng.choice(devices, p=[0.65, 0.28, 0.07])
    })

campaigns = pd.DataFrame(campaign_rows)

# ---------------------------
# Generate customers
# ---------------------------
num_customers = 10_000
segment_probs = np.array([0.10, 0.17, 0.15, 0.16, 0.13, 0.12, 0.12, 0.05])
latent = rng.choice(latent_segments, size=num_customers, p=segment_probs)

def random_signup(seg):
    if seg == 'New Customers':
        start, end = pd.Timestamp('2025-06-01'), pd.Timestamp('2025-12-15')
    elif seg in ['Champions', 'Loyal Customers', 'High-Value Customers']:
        start, end = pd.Timestamp('2023-01-01'), pd.Timestamp('2025-03-31')
    elif seg in ['At Risk', 'Hibernating']:
        start, end = pd.Timestamp('2023-01-01'), pd.Timestamp('2024-12-31')
    else:
        start, end = pd.Timestamp('2023-06-01'), pd.Timestamp('2025-08-31')
    return start + pd.Timedelta(days=int(rng.integers(0, max(1, (end-start).days))))

category_by_segment = {
    'Champions': ['Shoes', 'Jackets', 'Bags', 'Sportswear'],
    'Loyal Customers': ['Shoes', 'Dresses', 'Jeans', 'Accessories'],
    'Potential Loyalists': ['Sportswear', 'Shoes', 'Beauty', 'Accessories'],
    'New Customers': ['Beauty', 'Accessories', 'Shoes', 'Sportswear'],
    'At Risk': ['Jeans', 'Dresses', 'Shoes', 'Bags'],
    'Hibernating': ['Accessories', 'Jeans', 'Beauty', 'Shoes'],
    'Discount Seekers': ['Dresses', 'Jeans', 'Shoes', 'Sportswear'],
    'High-Value Customers': ['Jackets', 'Bags', 'Shoes', 'Dresses']
}

customers_rows = []
for i in range(num_customers):
    seg = latent[i]
    signup = random_signup(seg)
    if seg in ['New Customers', 'Potential Loyalists']:
        acq_probs = [0.30, 0.25, 0.18, 0.02, 0.08, 0.13, 0.04]
    elif seg in ['Discount Seekers']:
        acq_probs = [0.18, 0.28, 0.12, 0.18, 0.10, 0.09, 0.05]
    elif seg in ['Champions', 'Loyal Customers', 'High-Value Customers']:
        acq_probs = [0.22, 0.18, 0.06, 0.22, 0.08, 0.21, 0.03]
    else:
        acq_probs = [0.20, 0.22, 0.10, 0.12, 0.10, 0.18, 0.08]

    customers_rows.append({
        'customer_id': f'CUS-{i+1:05d}',
        'age_group': rng.choice(age_groups, p=[0.18, 0.34, 0.24, 0.15, 0.09]),
        'gender': rng.choice(genders, p=[0.58, 0.39, 0.03]),
        'country': rng.choice(countries, p=country_probs),
        'customer_type': 'New' if seg == 'New Customers' else 'Returning',
        'acquisition_channel': rng.choice(channels, p=acq_probs),
        'signup_date': signup.date().isoformat(),
        'product_category_preference': rng.choice(category_by_segment[seg]),
        'device_type': rng.choice(devices, p=[0.66, 0.27, 0.07]),
        'latent_business_profile': seg
    })
customers = pd.DataFrame(customers_rows)
customers['signup_date'] = pd.to_datetime(customers['signup_date'])

# ---------------------------
# Generate exactly 50,000 orders
# ---------------------------
base_weights = {
    'Champions': 9.0, 'Loyal Customers': 6.2, 'Potential Loyalists': 3.7, 'New Customers': 1.8,
    'At Risk': 2.5, 'Hibernating': 1.0, 'Discount Seekers': 5.3, 'High-Value Customers': 7.5
}
weights = customers['latent_business_profile'].map(base_weights).to_numpy(dtype=float)
weights = weights * rng.lognormal(mean=0, sigma=0.35, size=num_customers)
# guarantee at least 1 order per customer; allocate remaining by multinomial
initial_counts = np.ones(num_customers, dtype=int)
remaining = 50_000 - num_customers
extra_counts = rng.multinomial(remaining, weights / weights.sum())
order_counts = initial_counts + extra_counts
customers['planned_order_count'] = order_counts

campaign_lookup = campaigns.copy()
# convenience for campaign sampling by channel, country, device
camp_groups = {}
for (channel, country, device), df in campaign_lookup.groupby(['channel', 'country', 'device_type']):
    camp_groups[(channel, country, device)] = df
camp_channel_country = {}
for (channel, country), df in campaign_lookup.groupby(['channel', 'country']):
    camp_channel_country[(channel, country)] = df
camp_channel = {channel: df for channel, df in campaign_lookup.groupby('channel')}

# Desired channel mix creates realistic business story
retention_probs = np.array([0.15, 0.14, 0.06, 0.30, 0.09, 0.22, 0.04])
new_probs = np.array([0.31, 0.25, 0.16, 0.02, 0.08, 0.13, 0.05])
discount_probs = np.array([0.13, 0.24, 0.11, 0.25, 0.11, 0.10, 0.06])
at_risk_probs = np.array([0.14, 0.16, 0.07, 0.28, 0.10, 0.18, 0.07])

def channel_for_order(seg, order_idx):
    if order_idx == 0 and seg in ['New Customers', 'Potential Loyalists']:
        probs = new_probs
    elif seg == 'Discount Seekers':
        probs = discount_probs
    elif seg in ['At Risk', 'Hibernating']:
        probs = at_risk_probs
    else:
        probs = retention_probs
    return rng.choice(channels, p=probs)

def sample_campaign(channel, country, device):
    df = camp_groups.get((channel, country, device))
    if df is None or df.empty:
        df = camp_channel_country.get((channel, country))
    if df is None or df.empty:
        df = camp_channel[channel]
    # higher expected conversions get slightly higher probability
    vals = df['conversions'].to_numpy(dtype=float)
    probs = vals / vals.sum()
    row = df.iloc[int(rng.choice(np.arange(len(df)), p=probs))]
    return row['campaign_id']

def dates_for_customer(signup, seg, n):
    signup = pd.Timestamp(signup)
    if seg == 'New Customers':
        latest = ANALYSIS_DATE - pd.Timedelta(days=int(rng.integers(1, 45)))
        earliest = max(signup, pd.Timestamp('2025-06-01'))
    elif seg in ['Champions', 'Loyal Customers', 'High-Value Customers', 'Discount Seekers', 'Potential Loyalists']:
        latest = ANALYSIS_DATE - pd.Timedelta(days=int(rng.integers(2, 75 if seg != 'Potential Loyalists' else 105)))
        earliest = signup
    elif seg == 'At Risk':
        latest = ANALYSIS_DATE - pd.Timedelta(days=int(rng.integers(110, 235)))
        earliest = signup
    else:
        latest = ANALYSIS_DATE - pd.Timedelta(days=int(rng.integers(260, 620)))
        earliest = signup
    if latest <= earliest:
        latest = earliest + pd.Timedelta(days=1)
    # beta distribution gives more recent activity for active segments
    if seg in ['Champions', 'Loyal Customers', 'High-Value Customers', 'Discount Seekers']:
        vals = rng.beta(2.3, 1.2, n)
    elif seg in ['At Risk', 'Hibernating']:
        vals = rng.beta(1.2, 2.8, n)
    else:
        vals = rng.random(n)
    days = ((latest - earliest).days * vals).astype(int)
    return sorted([earliest + pd.Timedelta(days=int(d)) for d in days])

order_rows = []
order_num = 1
for idx, cust in customers.iterrows():
    n = int(cust['planned_order_count'])
    seg = cust['latent_business_profile']
    cust_dates = dates_for_customer(cust['signup_date'], seg, n)
    for j, odt in enumerate(cust_dates):
        channel = channel_for_order(seg, j)
        campaign_id = sample_campaign(channel, cust['country'], cust['device_type'])
        # Product category preference with some exploration
        if rng.random() < 0.62:
            cat = cust['product_category_preference']
        else:
            cat = rng.choice(product_categories)
        params = category_params[cat]
        qty = int(rng.choice([1, 1, 1, 2, 2, 3], p=[0.36, 0.22, 0.14, 0.16, 0.08, 0.04]))
        price_noise = rng.lognormal(mean=0, sigma=0.22)
        gross = params['base_price'] * price_noise * qty
        # segment-specific discounting
        discount_rate = {
            'Discount Seekers': rng.uniform(0.14, 0.36),
            'New Customers': rng.uniform(0.05, 0.22),
            'Potential Loyalists': rng.uniform(0.05, 0.20),
            'At Risk': rng.uniform(0.06, 0.25),
            'Hibernating': rng.uniform(0.07, 0.28),
            'Champions': rng.uniform(0.00, 0.12),
            'Loyal Customers': rng.uniform(0.00, 0.16),
            'High-Value Customers': rng.uniform(0.00, 0.08),
        }[seg]
        discount_amount = gross * discount_rate
        revenue = max(5.0, gross - discount_amount)
        cost = gross * (1 - params['margin'])
        # higher returns for discount seekers and high-return categories
        return_prob = params['return_rate']
        if seg == 'Discount Seekers':
            return_prob += 0.035
        if channel in ['Meta Ads', 'TikTok Ads', 'Display Ads']:
            return_prob += 0.012
        return_flag = int(rng.random() < min(return_prob, 0.35))
        # Profit excludes returned revenue impact in separate net revenue, but includes handling penalty for returned order
        return_penalty = return_flag * rng.uniform(2.5, 8.5)
        profit = revenue - cost - return_penalty
        order_rows.append({
            'order_id': f'ORD-{order_num:06d}',
            'customer_id': cust['customer_id'],
            'order_date': odt.date().isoformat(),
            'product_category': cat,
            'revenue': round(revenue, 2),
            'cost': round(cost, 2),
            'profit': round(profit, 2),
            'discount_amount': round(discount_amount, 2),
            'quantity': qty,
            'return_flag': return_flag,
            'campaign_id': campaign_id,
            'channel': channel,
            'device_type': cust['device_type'],
            'country': cust['country']
        })
        order_num += 1
orders = pd.DataFrame(order_rows)
assert len(orders) == 50_000
orders['order_date'] = pd.to_datetime(orders['order_date'])

# Update campaign conversions/revenue attributed from actual orders
camp_actual = orders.groupby('campaign_id').agg(
    conversions=('order_id', 'count'),
    revenue_attributed=('revenue', 'sum')
).reset_index()
campaigns = campaigns.drop(columns=['conversions', 'revenue_attributed']).merge(camp_actual, on='campaign_id', how='left')
campaigns['conversions'] = campaigns['conversions'].fillna(0).astype(int)
campaigns['revenue_attributed'] = campaigns['revenue_attributed'].fillna(0).round(2)

# Save raw files before processing
customers_raw = customers.drop(columns=['planned_order_count'])
customers_raw.to_csv(BASE / 'data/raw/customers_raw.csv', index=False)
orders.to_csv(BASE / 'data/raw/orders_raw.csv', index=False)
campaigns.to_csv(BASE / 'data/raw/campaigns_raw.csv', index=False)

# ---------------------------
# Data cleaning and KPI prep
# ---------------------------
customers_clean = customers_raw.copy()
orders_clean = orders.copy()
campaigns_clean = campaigns.copy()

# Validate types and add derived metrics
orders_clean['order_date'] = pd.to_datetime(orders_clean['order_date'])
customers_clean['signup_date'] = pd.to_datetime(customers_clean['signup_date'])
campaigns_clean['start_date'] = pd.to_datetime(campaigns_clean['start_date'])
campaigns_clean['end_date'] = pd.to_datetime(campaigns_clean['end_date'])

orders_clean = orders_clean.drop_duplicates(subset=['order_id']).copy()
customers_clean = customers_clean.drop_duplicates(subset=['customer_id']).copy()
campaigns_clean = campaigns_clean.drop_duplicates(subset=['campaign_id']).copy()

orders_clean['net_revenue_after_returns'] = np.where(orders_clean['return_flag'] == 1, 0, orders_clean['revenue'])
orders_clean['gross_margin_pct'] = np.where(orders_clean['revenue'] > 0, orders_clean['profit'] / orders_clean['revenue'], 0)
orders_clean['order_month'] = orders_clean['order_date'].dt.to_period('M').astype(str)
orders_clean['is_discounted_order'] = (orders_clean['discount_amount'] > 0).astype(int)

# Campaign KPIs
campaigns_clean['roi'] = np.where(campaigns_clean['spend'] > 0, (campaigns_clean['revenue_attributed'] - campaigns_clean['spend']) / campaigns_clean['spend'], 0)
campaigns_clean['roas'] = np.where(campaigns_clean['spend'] > 0, campaigns_clean['revenue_attributed'] / campaigns_clean['spend'], 0)
campaigns_clean['ctr'] = np.where(campaigns_clean['impressions'] > 0, campaigns_clean['clicks'] / campaigns_clean['impressions'], 0)
campaigns_clean['cpc'] = np.where(campaigns_clean['clicks'] > 0, campaigns_clean['spend'] / campaigns_clean['clicks'], 0)
campaigns_clean['cpa'] = np.where(campaigns_clean['conversions'] > 0, campaigns_clean['spend'] / campaigns_clean['conversions'], np.nan)
campaigns_clean['conversion_rate'] = np.where(campaigns_clean['clicks'] > 0, campaigns_clean['conversions'] / campaigns_clean['clicks'], 0)
campaigns_clean['revenue_per_click'] = np.where(campaigns_clean['clicks'] > 0, campaigns_clean['revenue_attributed'] / campaigns_clean['clicks'], 0)
campaigns_clean['campaign_profit'] = campaigns_clean['revenue_attributed'] - campaigns_clean['spend']
# Budget efficiency score, normalized blend of ROAS, ROI, and CPA inverse
roas_norm = (campaigns_clean['roas'] - campaigns_clean['roas'].min()) / (campaigns_clean['roas'].max() - campaigns_clean['roas'].min())
roi_norm = (campaigns_clean['roi'] - campaigns_clean['roi'].min()) / (campaigns_clean['roi'].max() - campaigns_clean['roi'].min())
cpa_filled = campaigns_clean['cpa'].fillna(campaigns_clean['cpa'].max())
cpa_inv = 1 - ((cpa_filled - cpa_filled.min()) / (cpa_filled.max() - cpa_filled.min()))
campaigns_clean['budget_efficiency_score'] = (100 * (0.45 * roas_norm + 0.35 * roi_norm + 0.20 * cpa_inv)).round(1)

# Customer KPIs and RFM
customer_order_agg = orders_clean.groupby('customer_id').agg(
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
customer_order_agg['average_order_value'] = customer_order_agg['total_spend'] / customer_order_agg['number_of_orders']
customer_order_agg['days_since_last_purchase'] = (ANALYSIS_DATE - customer_order_agg['last_purchase_date']).dt.days
customer_order_agg['customer_lifetime_value'] = customer_order_agg['total_spend']
signup_aligned = pd.Series(pd.to_datetime(customers_clean.set_index('customer_id').loc[customer_order_agg['customer_id'], 'signup_date']).to_numpy(), index=customer_order_agg.index)
customer_tenure_years = ((ANALYSIS_DATE - signup_aligned).dt.days / 365.25).clip(lower=0.1)
customer_order_agg['purchase_frequency'] = customer_order_agg['number_of_orders'] / customer_tenure_years
customer_order_agg['return_rate'] = customer_order_agg['return_count'] / customer_order_agg['number_of_orders']
customer_order_agg['discount_dependency'] = customer_order_agg['total_discount_amount'] / (customer_order_agg['total_spend'] + customer_order_agg['total_discount_amount'])
customer_order_agg['repeat_purchase_flag'] = (customer_order_agg['number_of_orders'] > 1).astype(int)
customer_order_agg['high_value_customer_flag'] = (customer_order_agg['total_spend'] >= customer_order_agg['total_spend'].quantile(0.85)).astype(int)

customers_clean = customers_clean.merge(customer_order_agg, on='customer_id', how='left')

# RFM scoring: recency lower is better, frequency and monetary higher are better
customers_clean['recency'] = customers_clean['days_since_last_purchase']
customers_clean['frequency'] = customers_clean['number_of_orders']
customers_clean['monetary'] = customers_clean['total_spend']
customers_clean['r_score'] = pd.qcut(customers_clean['recency'].rank(method='first'), 5, labels=[5,4,3,2,1]).astype(int)
customers_clean['f_score'] = pd.qcut(customers_clean['frequency'].rank(method='first'), 5, labels=[1,2,3,4,5]).astype(int)
customers_clean['m_score'] = pd.qcut(customers_clean['monetary'].rank(method='first'), 5, labels=[1,2,3,4,5]).astype(int)
customers_clean['rfm_score'] = customers_clean['r_score'].astype(str) + customers_clean['f_score'].astype(str) + customers_clean['m_score'].astype(str)

def assign_rfm(row):
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

customers_clean['customer_segment'] = customers_clean.apply(assign_rfm, axis=1)
# Make Discount Seekers visible even where monetary/frequency high, except Champions/high-value priority
mask_discount = (customers_clean['discount_dependency'] >= 0.24) & (customers_clean['customer_segment'].isin(['Potential Loyalists', 'Loyal Customers', 'At Risk']))
customers_clean.loc[mask_discount, 'customer_segment'] = 'Discount Seekers'

# Churn risk score logic
recency_component = np.select(
    [customers_clean['days_since_last_purchase'] > 240, customers_clean['days_since_last_purchase'] > 150, customers_clean['days_since_last_purchase'] > 90],
    [45, 32, 18], default=5
)
frequency_component = np.select(
    [customers_clean['purchase_frequency'] < 1.2, customers_clean['purchase_frequency'] < 2.2],
    [20, 10], default=0
)
discount_component = np.select(
    [customers_clean['discount_dependency'] > 0.28, customers_clean['discount_dependency'] > 0.20],
    [15, 8], default=0
)
return_component = np.select(
    [customers_clean['return_rate'] > 0.22, customers_clean['return_rate'] > 0.14],
    [15, 8], default=0
)
# low recent engagement proxy: no order in last 120 days
engagement_component = np.where(customers_clean['days_since_last_purchase'] > 120, 12, 0)
customers_clean['churn_risk_score'] = np.clip(recency_component + frequency_component + discount_component + return_component + engagement_component, 0, 100)
customers_clean['churn_risk_label'] = pd.cut(customers_clean['churn_risk_score'], bins=[-1, 34, 64, 100], labels=['Low risk', 'Medium risk', 'High risk']).astype(str)

# Join customer, order, campaign data
fact_orders = orders_clean.merge(customers_clean[['customer_id', 'age_group', 'gender', 'customer_type', 'acquisition_channel', 'customer_segment', 'churn_risk_label', 'customer_lifetime_value', 'discount_dependency']], on='customer_id', how='left') \
                         .merge(campaigns_clean[['campaign_id', 'campaign_name', 'campaign_objective', 'spend', 'impressions', 'clicks', 'roas', 'roi', 'cpa', 'budget_efficiency_score']], on='campaign_id', how='left')

# Aggregate outputs
monthly_revenue = orders_clean.groupby('order_month').agg(revenue=('revenue', 'sum'), profit=('profit', 'sum'), orders=('order_id', 'count')).reset_index()
category_performance = orders_clean.groupby('product_category').agg(revenue=('revenue', 'sum'), profit=('profit', 'sum'), orders=('order_id', 'count'), returns=('return_flag', 'sum'), net_revenue_after_returns=('net_revenue_after_returns', 'sum')).reset_index()
category_performance['profit_margin'] = category_performance['profit'] / category_performance['revenue']
category_performance['return_rate'] = category_performance['returns'] / category_performance['orders']
country_performance = orders_clean.groupby('country').agg(revenue=('revenue', 'sum'), profit=('profit', 'sum'), orders=('order_id', 'count')).reset_index()
device_performance = orders_clean.groupby('device_type').agg(revenue=('revenue', 'sum'), profit=('profit', 'sum'), orders=('order_id', 'count'), returns=('return_flag', 'sum')).reset_index()
device_performance['return_rate'] = device_performance['returns'] / device_performance['orders']
segment_performance = customers_clean.groupby('customer_segment').agg(customers=('customer_id', 'count'), revenue=('total_spend', 'sum'), profit=('total_profit', 'sum'), avg_clv=('customer_lifetime_value', 'mean'), avg_orders=('number_of_orders', 'mean'), avg_discount_dependency=('discount_dependency', 'mean'), avg_return_rate=('return_rate', 'mean')).reset_index()
segment_performance['revenue_share'] = segment_performance['revenue'] / segment_performance['revenue'].sum()
channel_kpis = campaigns_clean.groupby('channel').agg(total_spend=('spend','sum'), total_revenue=('revenue_attributed','sum'), impressions=('impressions','sum'), clicks=('clicks','sum'), conversions=('conversions','sum'), campaign_profit=('campaign_profit','sum'), avg_budget_efficiency_score=('budget_efficiency_score','mean')).reset_index()
channel_kpis['roi'] = (channel_kpis['total_revenue'] - channel_kpis['total_spend']) / channel_kpis['total_spend']
channel_kpis['roas'] = channel_kpis['total_revenue'] / channel_kpis['total_spend']
channel_kpis['ctr'] = channel_kpis['clicks'] / channel_kpis['impressions']
channel_kpis['cpc'] = channel_kpis['total_spend'] / channel_kpis['clicks']
channel_kpis['cpa'] = channel_kpis['total_spend'] / channel_kpis['conversions']
channel_kpis['conversion_rate'] = channel_kpis['conversions'] / channel_kpis['clicks']
channel_kpis['revenue_per_click'] = channel_kpis['total_revenue'] / channel_kpis['clicks']

# Budget reallocation recommendations
channel_median_roas = channel_kpis['roas'].median()
channel_median_cpa = channel_kpis['cpa'].median()
realloc_rows = []
for _, row in channel_kpis.iterrows():
    channel = row['channel']
    current = row['total_spend']
    if channel in ['Email', 'Organic Search']:
        multiplier = 1.22 if channel == 'Email' else 1.18
        reason = 'High ROAS and strong retention/intent efficiency; scale carefully due to audience ceiling.'
        impact = 'Expected to lift profitable repeat revenue and reduce blended CPA.'
    elif channel == 'Google Search':
        multiplier = 1.12
        reason = 'Higher CPA than retention channels, but stronger purchase intent and healthy conversion quality.'
        impact = 'Expected to capture high-intent demand and improve qualified acquisition.'
    elif channel == 'Affiliate':
        multiplier = 1.05
        reason = 'Positive partner-led acquisition economics with moderate scalability.'
        impact = 'Expected to add incremental orders while keeping CPA controlled.'
    elif channel == 'TikTok Ads':
        multiplier = 0.95
        reason = 'Useful for new customer acquisition, but lower retention and weaker immediate ROAS.'
        impact = 'Keep testing creatives while reducing inefficient prospecting pockets.'
    elif channel == 'Meta Ads':
        multiplier = 0.88
        reason = 'High traffic volume but weaker conversion quality and lower ROI than high-intent channels.'
        impact = 'Reduce wasted spend and reallocate to retention/high-intent demand.'
    else:  # Display Ads
        multiplier = 0.72
        reason = 'Lowest conversion efficiency and high spend relative to attributed revenue.'
        impact = 'Lower awareness waste and protect margin.'
    recommended = current * multiplier
    realloc_rows.append({
        'channel': channel,
        'current_spend': round(current, 2),
        'recommended_spend': round(recommended, 2),
        'increase_decrease_amount': round(recommended - current, 2),
        'reason_for_change': reason,
        'expected_business_impact': impact
    })
budget_reallocation = pd.DataFrame(realloc_rows)
# Preserve total budget by scaling recommended spend back to current total
scale = budget_reallocation['current_spend'].sum() / budget_reallocation['recommended_spend'].sum()
budget_reallocation['recommended_spend'] = (budget_reallocation['recommended_spend'] * scale).round(2)
budget_reallocation['increase_decrease_amount'] = (budget_reallocation['recommended_spend'] - budget_reallocation['current_spend']).round(2)

high_spend_low_conversion = campaigns_clean[(campaigns_clean['spend'] >= campaigns_clean['spend'].quantile(0.70)) & (campaigns_clean['conversion_rate'] <= campaigns_clean['conversion_rate'].quantile(0.30))].sort_values(['spend','conversion_rate'], ascending=[False, True]).head(15)
high_roas_campaigns = campaigns_clean.sort_values('roas', ascending=False).head(15)
low_roi_campaigns = campaigns_clean.sort_values('roi', ascending=True).head(15)
churn_customer_list = customers_clean[customers_clean['churn_risk_label']=='High risk'].sort_values(['churn_risk_score', 'customer_lifetime_value'], ascending=[False, False]).head(500)

# Executive summary table
summary_metrics = {
    'Total revenue': orders_clean['revenue'].sum(),
    'Total profit': orders_clean['profit'].sum(),
    'Profit margin': orders_clean['profit'].sum() / orders_clean['revenue'].sum(),
    'Total orders': len(orders_clean),
    'Return rate': orders_clean['return_flag'].mean(),
    'Net revenue after returns': orders_clean['net_revenue_after_returns'].sum(),
    'Total marketing spend': campaigns_clean['spend'].sum(),
    'Overall ROAS': campaigns_clean['revenue_attributed'].sum() / campaigns_clean['spend'].sum(),
    'Overall ROI': (campaigns_clean['revenue_attributed'].sum() - campaigns_clean['spend'].sum()) / campaigns_clean['spend'].sum(),
    'Repeat purchase rate': customers_clean['repeat_purchase_flag'].mean(),
    'High risk customers': (customers_clean['churn_risk_label'] == 'High risk').sum()
}
executive_summary_table = pd.DataFrame([{'metric': k, 'value': v} for k, v in summary_metrics.items()])

# Processed exports
processed_exports = {
    'customers_clean.csv': customers_clean,
    'orders_clean.csv': orders_clean,
    'campaigns_clean.csv': campaigns_clean,
    'fact_orders_customer_campaign.csv': fact_orders,
    'rfm_segments.csv': customers_clean[['customer_id','recency','frequency','monetary','r_score','f_score','m_score','rfm_score','customer_segment','churn_risk_score','churn_risk_label']],
    'marketing_kpis_by_channel.csv': channel_kpis,
    'monthly_revenue.csv': monthly_revenue,
    'category_performance.csv': category_performance,
    'country_performance.csv': country_performance,
    'device_performance.csv': device_performance,
    'segment_performance.csv': segment_performance,
    'budget_reallocation.csv': budget_reallocation,
    'high_spend_low_conversion_campaigns.csv': high_spend_low_conversion,
    'top_roas_campaigns.csv': high_roas_campaigns,
    'bottom_roi_campaigns.csv': low_roi_campaigns,
    'churn_risk_customer_list.csv': churn_customer_list,
    'executive_summary_table.csv': executive_summary_table,
}
for name, df in processed_exports.items():
    df.to_csv(BASE / 'data/processed' / name, index=False)

# SQLite database for SQL practice
sqlite_path = BASE / 'data/processed/zalando_style_marketing_analytics.sqlite'
if sqlite_path.exists():
    sqlite_path.unlink()
conn = sqlite3.connect(sqlite_path)
customers_clean.to_sql('customers', conn, index=False)
orders_clean.to_sql('orders', conn, index=False)
campaigns_clean.to_sql('campaigns', conn, index=False)
channel_kpis.to_sql('channel_kpis', conn, index=False)
budget_reallocation.to_sql('budget_reallocation', conn, index=False)
conn.close()

# ---------------------------
# Visuals
# ---------------------------
plt.rcParams.update({'figure.figsize': (10, 6), 'axes.titlesize': 14, 'axes.labelsize': 11})

def money_fmt(ax, axis='y'):
    import matplotlib.ticker as mtick
    formatter = mtick.FuncFormatter(lambda x, pos: f'€{x/1000:,.0f}K')
    if axis == 'y':
        ax.yaxis.set_major_formatter(formatter)
    else:
        ax.xaxis.set_major_formatter(formatter)

def save_fig(filename):
    plt.tight_layout()
    plt.savefig(BASE / 'visuals' / filename, dpi=160, bbox_inches='tight')
    plt.close()

# 1 Monthly revenue trend
fig, ax = plt.subplots()
mr = monthly_revenue.sort_values('order_month')
ax.plot(mr['order_month'], mr['revenue'], marker='o')
ax.set_title('Monthly Revenue Trend')
ax.set_xlabel('Order Month')
ax.set_ylabel('Revenue')
ax.tick_params(axis='x', rotation=45)
money_fmt(ax)
save_fig('01_monthly_revenue_trend.png')

# 2 ROAS by marketing channel
fig, ax = plt.subplots()
ck = channel_kpis.sort_values('roas', ascending=True)
ax.barh(ck['channel'], ck['roas'])
ax.set_title('ROAS by Marketing Channel')
ax.set_xlabel('ROAS')
ax.set_ylabel('Marketing Channel')
save_fig('02_roas_by_channel.png')

# 3 ROI by campaign top/bottom sample
fig, ax = plt.subplots(figsize=(11, 7))
roi_sample = pd.concat([campaigns_clean.nlargest(8, 'roi'), campaigns_clean.nsmallest(8, 'roi')]).sort_values('roi')
ax.barh(roi_sample['campaign_id'], roi_sample['roi'])
ax.set_title('ROI by Campaign: Top and Bottom Campaigns')
ax.set_xlabel('ROI')
ax.set_ylabel('Campaign ID')
save_fig('03_roi_by_campaign.png')

# 4 CPA by channel
fig, ax = plt.subplots()
ck = channel_kpis.sort_values('cpa', ascending=True)
ax.barh(ck['channel'], ck['cpa'])
ax.set_title('CPA by Marketing Channel')
ax.set_xlabel('Cost per Acquisition')
ax.set_ylabel('Marketing Channel')
money_fmt(ax, axis='x')
save_fig('04_cpa_by_channel.png')

# 5 Revenue by customer segment
fig, ax = plt.subplots()
sp = segment_performance.sort_values('revenue', ascending=True)
ax.barh(sp['customer_segment'], sp['revenue'])
ax.set_title('Revenue by Customer Segment')
ax.set_xlabel('Revenue')
ax.set_ylabel('Customer Segment')
money_fmt(ax, axis='x')
save_fig('05_revenue_by_customer_segment.png')

# 6 CLV by segment
fig, ax = plt.subplots()
sp = segment_performance.sort_values('avg_clv', ascending=True)
ax.barh(sp['customer_segment'], sp['avg_clv'])
ax.set_title('Average CLV by Customer Segment')
ax.set_xlabel('Average Customer Lifetime Value')
ax.set_ylabel('Customer Segment')
money_fmt(ax, axis='x')
save_fig('06_clv_by_segment.png')

# 7 Churn risk distribution
fig, ax = plt.subplots()
risk_counts = customers_clean['churn_risk_label'].value_counts().reindex(['Low risk','Medium risk','High risk']).fillna(0)
ax.bar(risk_counts.index, risk_counts.values)
ax.set_title('Churn Risk Distribution')
ax.set_xlabel('Churn Risk Label')
ax.set_ylabel('Number of Customers')
save_fig('07_churn_risk_distribution.png')

# 8 Marketing spend vs revenue
fig, ax = plt.subplots()
ax.scatter(channel_kpis['total_spend'], channel_kpis['total_revenue'], s=90)
for _, row in channel_kpis.iterrows():
    ax.annotate(row['channel'], (row['total_spend'], row['total_revenue']), xytext=(4, 4), textcoords='offset points', fontsize=8)
ax.set_title('Marketing Spend vs Attributed Revenue by Channel')
ax.set_xlabel('Total Spend')
ax.set_ylabel('Attributed Revenue')
money_fmt(ax, axis='x')
money_fmt(ax, axis='y')
save_fig('08_marketing_spend_vs_revenue.png')

# 9 Product category performance
fig, ax = plt.subplots()
cp = category_performance.sort_values('profit', ascending=True)
ax.barh(cp['product_category'], cp['profit'])
ax.set_title('Product Category Profit Performance')
ax.set_xlabel('Profit')
ax.set_ylabel('Product Category')
money_fmt(ax, axis='x')
save_fig('09_product_category_performance.png')

# 10 Country-level revenue
fig, ax = plt.subplots()
co = country_performance.sort_values('revenue', ascending=True)
ax.barh(co['country'], co['revenue'])
ax.set_title('Country-Level Revenue')
ax.set_xlabel('Revenue')
ax.set_ylabel('Country')
money_fmt(ax, axis='x')
save_fig('10_country_level_revenue.png')

# ---------------------------
# SQL scripts
# ---------------------------
sql_scripts = {
'01_total_revenue_profit_orders_margin.sql': """
-- Total revenue, profit, orders and margin
SELECT
    ROUND(SUM(revenue), 2) AS total_revenue,
    ROUND(SUM(profit), 2) AS total_profit,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(profit) * 1.0 / NULLIF(SUM(revenue), 0), 4) AS profit_margin
FROM orders;
""",
'02_monthly_revenue_trend.sql': """
-- Monthly revenue trend
SELECT
    strftime('%Y-%m', order_date) AS order_month,
    ROUND(SUM(revenue), 2) AS revenue,
    ROUND(SUM(profit), 2) AS profit,
    COUNT(order_id) AS orders
FROM orders
GROUP BY 1
ORDER BY 1;
""",
'03_campaign_roi_roas.sql': """
-- Campaign ROI and ROAS
SELECT
    campaign_id,
    campaign_name,
    channel,
    ROUND(spend, 2) AS spend,
    ROUND(revenue_attributed, 2) AS revenue_attributed,
    ROUND((revenue_attributed - spend) / NULLIF(spend, 0), 4) AS roi,
    ROUND(revenue_attributed / NULLIF(spend, 0), 4) AS roas,
    conversions
FROM campaigns
ORDER BY roas DESC;
""",
'04_channel_cpa_cpc_ctr_conversion.sql': """
-- Channel-level CPA, CPC, CTR and conversion rate
SELECT
    channel,
    ROUND(SUM(spend), 2) AS total_spend,
    SUM(impressions) AS impressions,
    SUM(clicks) AS clicks,
    SUM(conversions) AS conversions,
    ROUND(SUM(spend) / NULLIF(SUM(conversions), 0), 2) AS cpa,
    ROUND(SUM(spend) / NULLIF(SUM(clicks), 0), 2) AS cpc,
    ROUND(SUM(clicks) * 1.0 / NULLIF(SUM(impressions), 0), 4) AS ctr,
    ROUND(SUM(conversions) * 1.0 / NULLIF(SUM(clicks), 0), 4) AS conversion_rate
FROM campaigns
GROUP BY channel
ORDER BY cpa ASC;
""",
'05_top_10_campaigns_by_roas.sql': """
-- Top 10 campaigns by ROAS
SELECT
    campaign_id,
    campaign_name,
    channel,
    ROUND(spend, 2) AS spend,
    ROUND(revenue_attributed, 2) AS revenue_attributed,
    ROUND(revenue_attributed / NULLIF(spend, 0), 4) AS roas
FROM campaigns
ORDER BY roas DESC
LIMIT 10;
""",
'06_bottom_10_campaigns_by_roi.sql': """
-- Bottom 10 campaigns by ROI
SELECT
    campaign_id,
    campaign_name,
    channel,
    ROUND(spend, 2) AS spend,
    ROUND(revenue_attributed, 2) AS revenue_attributed,
    ROUND((revenue_attributed - spend) / NULLIF(spend, 0), 4) AS roi
FROM campaigns
ORDER BY roi ASC
LIMIT 10;
""",
'07_customer_rfm_table.sql': """
-- Customer RFM table
WITH customer_orders AS (
    SELECT
        customer_id,
        MAX(order_date) AS last_purchase_date,
        COUNT(order_id) AS frequency,
        ROUND(SUM(revenue), 2) AS monetary
    FROM orders
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    c.country,
    c.age_group,
    c.gender,
    CAST(julianday('2026-01-01') - julianday(co.last_purchase_date) AS INTEGER) AS recency,
    co.frequency,
    co.monetary,
    c.customer_segment,
    c.rfm_score
FROM customers c
JOIN customer_orders co ON c.customer_id = co.customer_id
ORDER BY monetary DESC;
""",
'08_customer_segment_revenue.sql': """
-- Customer segment revenue
SELECT
    customer_segment,
    COUNT(DISTINCT customer_id) AS customers,
    ROUND(SUM(total_spend), 2) AS revenue,
    ROUND(AVG(customer_lifetime_value), 2) AS avg_clv,
    ROUND(SUM(total_spend) * 1.0 / (SELECT SUM(total_spend) FROM customers), 4) AS revenue_share
FROM customers
GROUP BY customer_segment
ORDER BY revenue DESC;
""",
'09_churn_risk_customer_list.sql': """
-- Churn-risk customer list
SELECT
    customer_id,
    country,
    customer_segment,
    days_since_last_purchase,
    number_of_orders,
    ROUND(total_spend, 2) AS total_spend,
    ROUND(discount_dependency, 4) AS discount_dependency,
    ROUND(return_rate, 4) AS return_rate,
    churn_risk_score,
    churn_risk_label
FROM customers
WHERE churn_risk_label = 'High risk'
ORDER BY churn_risk_score DESC, total_spend DESC;
""",
'10_budget_reallocation_input_table.sql': """
-- Budget reallocation input table
SELECT
    channel,
    ROUND(total_spend, 2) AS current_spend,
    ROUND(total_revenue, 2) AS attributed_revenue,
    ROUND(roas, 4) AS roas,
    ROUND(roi, 4) AS roi,
    ROUND(cpa, 2) AS cpa,
    ROUND(conversion_rate, 4) AS conversion_rate,
    ROUND(avg_budget_efficiency_score, 1) AS budget_efficiency_score
FROM channel_kpis
ORDER BY budget_efficiency_score DESC;
"""
}
for fname, sql in sql_scripts.items():
    (BASE / 'sql' / fname).write_text(textwrap.dedent(sql).strip() + '\n')

# ---------------------------
# Markdown documents
# ---------------------------
# derived insight values for reports
top_channel = channel_kpis.sort_values('roas', ascending=False).iloc[0]
low_channel = channel_kpis.sort_values('roi', ascending=True).iloc[0]
top_segment = segment_performance.sort_values('revenue', ascending=False).iloc[0]
top_country = country_performance.sort_values('revenue', ascending=False).iloc[0]
high_return_cat = category_performance.sort_values('return_rate', ascending=False).iloc[0]

folder_tree = """zalando_style_customer_segmentation_roi/
├── README.md
├── requirements.txt
├── business_requirements_document.md
├── executive_summary.md
├── kpi_dictionary.md
├── data/
│   ├── raw/
│   │   ├── campaigns_raw.csv
│   │   ├── customers_raw.csv
│   │   └── orders_raw.csv
│   └── processed/
│       ├── budget_reallocation.csv
│       ├── campaigns_clean.csv
│       ├── category_performance.csv
│       ├── channel_kpis.csv
│       ├── churn_risk_customer_list.csv
│       ├── country_performance.csv
│       ├── customers_clean.csv
│       ├── device_performance.csv
│       ├── executive_summary_table.csv
│       ├── fact_orders_customer_campaign.csv
│       ├── high_spend_low_conversion_campaigns.csv
│       ├── marketing_kpis_by_channel.csv
│       ├── monthly_revenue.csv
│       ├── orders_clean.csv
│       ├── rfm_segments.csv
│       ├── segment_performance.csv
│       ├── top_roas_campaigns.csv
│       └── zalando_style_marketing_analytics.sqlite
├── dashboards/
│   ├── dashboard_blueprint.md
│   └── powerbi_tableau_data_model.md
├── notebooks/
│   └── 01_zalando_style_analysis.ipynb
├── reports/
│   ├── analysis_report.md
│   ├── data_cleaning_report.md
│   └── marketing_recommendations.md
├── scripts/
│   └── build_project.py
├── sql/
│   ├── 01_total_revenue_profit_orders_margin.sql
│   ├── 02_monthly_revenue_trend.sql
│   ├── 03_campaign_roi_roas.sql
│   ├── 04_channel_cpa_cpc_ctr_conversion.sql
│   ├── 05_top_10_campaigns_by_roas.sql
│   ├── 06_bottom_10_campaigns_by_roi.sql
│   ├── 07_customer_rfm_table.sql
│   ├── 08_customer_segment_revenue.sql
│   ├── 09_churn_risk_customer_list.sql
│   └── 10_budget_reallocation_input_table.sql
└── visuals/
    ├── 01_monthly_revenue_trend.png
    ├── 02_roas_by_channel.png
    ├── 03_roi_by_campaign.png
    ├── 04_cpa_by_channel.png
    ├── 05_revenue_by_customer_segment.png
    ├── 06_clv_by_segment.png
    ├── 07_churn_risk_distribution.png
    ├── 08_marketing_spend_vs_revenue.png
    ├── 09_product_category_performance.png
    └── 10_country_level_revenue.png"""

readme = f"""
# Zalando-Style Customer Segmentation and Marketing ROI Analysis

> **Portfolio project:** Fictional/simulated European fashion e-commerce analytics project inspired by a Zalando-style business model. This project does **not** use confidential Zalando data. All datasets are synthetic and reproducible using a fixed random seed.

## 1. Business Problem

A European fashion e-commerce company wants to improve marketing profitability, customer retention and budget allocation. Leadership needs to understand:

1. Which customer segments generate the highest revenue and profit?
2. Which marketing channels produce the best ROI and ROAS?
3. Which campaigns have high spend but poor conversion?
4. Which customer groups should receive more marketing budget?
5. Which customer groups are at risk of churn?
6. How should marketing spend be reallocated across channels?

## 2. Dataset Overview

The project uses reproducible synthetic data representing a European fashion e-commerce business.

| Dataset | Rows | Description |
|---|---:|---|
| `customers_raw.csv` | 10,000 | Customer profile, acquisition, device, region and category preference |
| `orders_raw.csv` | 50,000 | Order-level revenue, cost, profit, discount, returns and campaign attribution |
| `campaigns_raw.csv` | 120 | Campaign spend, impressions, clicks, conversions and revenue attribution |

### Business Dimensions

- **Countries:** Germany, UK, France, Italy, Spain, Netherlands, Poland
- **Channels:** Google Search, Meta Ads, TikTok Ads, Email, Affiliate, Organic Search, Display Ads
- **Product categories:** Shoes, Dresses, Jackets, Sportswear, Accessories, Jeans, Beauty, Bags
- **Devices:** Mobile, Desktop, Tablet

## 3. Tools Used

- Python
- Pandas
- NumPy
- Matplotlib
- SQLite / SQL
- Power BI or Tableau-ready CSV exports
- Optional Jupyter Notebook workflow

## 4. Project Workflow

1. Generate synthetic e-commerce customer, order and campaign data.
2. Clean missing values, remove duplicates and validate data types.
3. Create derived marketing, customer and business KPIs.
4. Perform exploratory analysis across time, channel, customer, product, country and device dimensions.
5. Apply RFM segmentation to identify customer groups.
6. Create churn-risk labels using recency, frequency, discount and return behaviour.
7. Analyse marketing ROI, ROAS, CPA, CPC, CTR and conversion rate.
8. Build a budget reallocation recommendation table.
9. Export BI-ready datasets for Power BI or Tableau.
10. Create executive-ready visuals and written recommendations.

## 5. Key KPIs

### Marketing KPIs

- Total spend
- Total revenue
- ROI
- ROAS
- CTR
- CPC
- CPA
- Conversion rate
- Revenue per click
- Cost per acquisition
- Campaign profit
- Budget efficiency score

### Customer KPIs

- Customer lifetime value
- Average order value
- Purchase frequency
- Repeat purchase rate
- Churn-risk score
- Days since last purchase
- Discount dependency
- Return rate
- High-value customer flag

### Business KPIs

- Revenue
- Profit
- Profit margin
- Orders
- Returns
- Net revenue after returns
- Category performance
- Country performance
- Device performance

## 6. Analysis Steps

### Data Cleaning and Preparation

- Checked duplicate customer, order and campaign IDs.
- Converted date fields into datetime format.
- Created order month, net revenue after returns, margin and discount flags.
- Joined customer, order and campaign data into a BI-ready fact table.
- Exported cleaned datasets into `data/processed/`.

### Exploratory Data Analysis

- Monthly revenue trend
- Profit by product category
- Marketing spend by channel
- Revenue by country
- Customer distribution by RFM segment
- Return rate by category
- Device-level performance

### Marketing ROI Analysis

- Compared ROI and ROAS across seven channels.
- Identified high-spend, low-conversion campaigns.
- Identified highest-ROAS campaigns.
- Compared CPA and conversion rate by channel.
- Built budget reallocation recommendations.

### Customer Segmentation

RFM segmentation was calculated using:

- **Recency:** days since last purchase
- **Frequency:** number of customer orders
- **Monetary:** total customer spend

Segments created:

- Champions
- Loyal Customers
- Potential Loyalists
- New Customers
- At Risk
- Hibernating
- Discount Seekers
- High-Value Customers

### Churn-Risk Analysis

A simple churn-risk score was created using:

- Days since last purchase
- Purchase frequency
- Low recent engagement proxy
- Discount dependency
- Return rate

Customers are classified into:

- Low risk
- Medium risk
- High risk

## 7. Key Insights

- **{top_channel['channel']} generated the strongest ROAS** at approximately **{top_channel['roas']:.2f}**, showing that retention or high-intent channels can outperform broader paid media.
- **{low_channel['channel']} showed the weakest ROI** at approximately **{low_channel['roi']:.2f}**, indicating spend should be reduced or tightly tested.
- **{top_segment['customer_segment']} generated the highest revenue** with approximately **€{top_segment['revenue']:,.0f}**, proving that customer value is concentrated in a small number of high-quality groups.
- **{high_return_cat['product_category']} had the highest return rate** at approximately **{high_return_cat['return_rate']:.1%}**, reducing category profitability.
- **{top_country['country']} was the top revenue market** with approximately **€{top_country['revenue']:,.0f}** in sales.

## 8. Recommendations

1. Increase budget for high-ROAS channels such as Email and Organic Search while respecting audience scale limits.
2. Reduce spend on campaigns with high CPA, low conversion rate and weak ROI.
3. Create retention campaigns for At-Risk and Potential Loyalist customers.
4. Use personalised offers for Champions and Loyal Customers.
5. Reduce excessive discounting for customers already likely to purchase.
6. Improve return-rate monitoring for lower-margin or high-return categories.
7. Build a monthly marketing performance dashboard for leadership.

## 9. Dashboard Screenshots Placeholder

Add screenshots here after building the dashboard in Power BI or Tableau.

| Dashboard Page | Screenshot Placeholder |
|---|---|
| Executive Overview | `dashboards/screenshots/page_1_executive_overview.png` |
| Marketing Performance | `dashboards/screenshots/page_2_marketing_performance.png` |
| Customer Segmentation | `dashboards/screenshots/page_3_customer_segmentation.png` |
| Business Recommendations | `dashboards/screenshots/page_4_business_recommendations.png` |

## 10. How to Run the Project

```bash
# 1. Clone the repository
# git clone <your-repo-url>
# cd zalando-style-customer-segmentation-roi

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\\Scripts\\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Regenerate data, outputs and visuals
python scripts/build_project.py
```

## 11. Folder Structure

```text
{folder_tree}
```

## 12. CV Bullet Points

- Built an end-to-end e-commerce marketing analytics project using SQL, Python and BI-ready datasets to analyse campaign ROI, customer segmentation and revenue performance.
- Applied RFM segmentation to 10,000+ customers, identifying high-value, at-risk and discount-dependent customer groups for targeted marketing actions.
- Calculated marketing KPIs including ROAS, ROI, CPA, CPC, CTR and conversion rate across 100+ campaigns to recommend budget reallocation.
- Created executive-ready insights and dashboard wireframes to support marketing spend optimisation, customer retention and commercial decision-making.

## 13. Interview Talking Points

### Business Analyst Role

I would describe this as a commercial decision-support project. I translated a broad business problem into clear requirements, defined KPIs, segmented customers, prioritised risks and produced a budget reallocation recommendation that leadership could act on.

### Data Analyst Role

I would focus on the technical workflow: synthetic data generation, cleaning, SQL analysis, Python-based KPI creation, RFM segmentation, churn-risk labelling, visualisation and CSV outputs for BI tools.

### Marketing Analyst Role

I would explain how the project evaluates channel efficiency, campaign ROI, ROAS, CPA and conversion quality. I would highlight how the analysis shifts budget toward high-intent and retention channels while reducing spend on inefficient acquisition campaigns.
"""
(BASE / 'README.md').write_text(textwrap.dedent(readme).strip() + '\n')

requirements = """
pandas>=2.0
numpy>=1.24
matplotlib>=3.7
jupyter>=1.0
notebook>=7.0
ipykernel>=6.0
"""
(BASE / 'requirements.txt').write_text(textwrap.dedent(requirements).strip() + '\n')

executive_summary_md = f"""
# Executive Summary

## Project Context

This project analyses a fictional European fashion e-commerce company similar to Zalando. The goal is to help leadership improve marketing ROI, customer retention and budget allocation using customer, order and campaign data.

## Commercial Performance Snapshot

| Metric | Value |
|---|---:|
| Total revenue | €{orders_clean['revenue'].sum():,.0f} |
| Total profit | €{orders_clean['profit'].sum():,.0f} |
| Profit margin | {orders_clean['profit'].sum() / orders_clean['revenue'].sum():.1%} |
| Orders | {len(orders_clean):,} |
| Return rate | {orders_clean['return_flag'].mean():.1%} |
| Net revenue after returns | €{orders_clean['net_revenue_after_returns'].sum():,.0f} |
| Marketing spend | €{campaigns_clean['spend'].sum():,.0f} |
| Overall ROAS | {campaigns_clean['revenue_attributed'].sum() / campaigns_clean['spend'].sum():.2f} |
| Overall ROI | {(campaigns_clean['revenue_attributed'].sum() - campaigns_clean['spend'].sum()) / campaigns_clean['spend'].sum():.2f} |

## Key Findings

1. **Retention and high-intent channels outperform broad acquisition.** {top_channel['channel']} delivered the strongest ROAS, while {low_channel['channel']} showed the weakest ROI.
2. **Customer value is concentrated.** {top_segment['customer_segment']} generated the largest share of revenue, making it a priority for retention and premium personalisation.
3. **Returns are a material profitability risk.** {high_return_cat['product_category']} had the highest return rate, creating pressure on margin and net revenue.
4. **Paid social requires tighter governance.** Meta Ads and TikTok Ads can support discovery and new customer acquisition, but their conversion quality and retention impact must be monitored.
5. **Budget should move toward profitable retention and high-intent acquisition.** Email, Organic Search and selected Google Search campaigns deserve incremental investment, while inefficient Display and low-ROI paid social campaigns should be reduced.

## Recommended Actions

| Priority | Recommendation | Expected Impact |
|---|---|---|
| 1 | Increase spend in high-ROAS lifecycle and high-intent channels | Higher profitable revenue and lower blended CPA |
| 2 | Reduce high-spend low-conversion campaigns | Protect marketing budget from waste |
| 3 | Launch retention journeys for At-Risk customers | Improve repeat purchase and reduce churn |
| 4 | Personalise offers for Champions and Loyal Customers | Increase CLV without excessive discounting |
| 5 | Monitor return-heavy categories weekly | Improve margin and reduce net revenue leakage |
| 6 | Build a monthly executive dashboard | Improve decision speed and marketing accountability |

## Risks

- Synthetic data is designed for portfolio demonstration and should not be treated as real Zalando data.
- Attribution is simplified to campaign-level attribution and does not model multi-touch journeys.
- Churn-risk scoring is rules-based; a production version should test predictive modelling.

## Next Steps

1. Build the Power BI or Tableau dashboard using processed CSV files.
2. Add screenshots to the README.
3. Create a short LinkedIn post and GitHub repository description.
4. Extend the project with cohort analysis, multi-touch attribution or predictive churn modelling.
"""
(BASE / 'executive_summary.md').write_text(textwrap.dedent(executive_summary_md).strip() + '\n')

kpi_dictionary_md = """
# KPI Dictionary

## Marketing KPIs

| KPI | Formula | Business Meaning |
|---|---|---|
| Total Spend | Sum of campaign spend | Total marketing investment |
| Total Revenue | Sum of attributed campaign revenue | Revenue linked to campaigns |
| ROI | (Revenue - Spend) / Spend | Profitability of marketing investment before product cost allocation |
| ROAS | Revenue / Spend | Revenue generated for each euro spent |
| CTR | Clicks / Impressions | Ad engagement rate |
| CPC | Spend / Clicks | Average cost of generating a click |
| CPA | Spend / Conversions | Average cost of acquiring an order/conversion |
| Conversion Rate | Conversions / Clicks | Share of clicks that converted |
| Revenue per Click | Revenue / Clicks | Monetisation value of traffic |
| Campaign Profit | Revenue Attributed - Spend | Campaign-level contribution before fulfilment and operating costs |
| Budget Efficiency Score | Weighted score using ROAS, ROI and inverse CPA | Ranking metric for budget allocation |

## Customer KPIs

| KPI | Formula | Business Meaning |
|---|---|---|
| Customer Lifetime Value | Total customer spend | Historical customer value |
| Average Order Value | Total Spend / Number of Orders | Average revenue per order |
| Purchase Frequency | Number of Orders / Customer Tenure in Years | How often a customer buys |
| Repeat Purchase Rate | Customers with >1 order / Total Customers | Retention strength |
| Churn-Risk Score | Rules-based score from recency, frequency, discounting and returns | Likelihood of customer becoming inactive |
| Days Since Last Purchase | Analysis Date - Last Purchase Date | Recency of engagement |
| Discount Dependency | Discount Amount / Gross Order Value | Reliance on promotions |
| Return Rate | Returned Orders / Total Orders | Product/customer profitability risk |
| High-Value Customer Flag | Customer spend >= 85th percentile | Identifies top spenders |

## Business KPIs

| KPI | Formula | Business Meaning |
|---|---|---|
| Revenue | Sum of order revenue | Sales generated |
| Profit | Revenue - Cost - Return Handling Penalty | Order-level profit |
| Profit Margin | Profit / Revenue | Commercial efficiency |
| Orders | Count of order IDs | Transaction volume |
| Returns | Count of return flags | Returned order volume |
| Net Revenue After Returns | Revenue excluding returned orders | Revenue retained after returns |
| Category Performance | Revenue, profit, return rate by category | Product portfolio health |
| Country Performance | Revenue, profit, orders by country | Regional performance |
| Device Performance | Revenue, profit, returns by device | Digital experience performance |
"""
(BASE / 'kpi_dictionary.md').write_text(textwrap.dedent(kpi_dictionary_md).strip() + '\n')

brd_md = """
# Business Requirements Document

## Project Name

Zalando-Style Customer Segmentation and Marketing ROI Analysis

## Business Objective

Improve marketing budget allocation, customer targeting and retention strategy for a fictional European fashion e-commerce business.

## Stakeholders

| Stakeholder | Requirement |
|---|---|
| Marketing Director | Understand channel ROI, ROAS, CPA and budget efficiency |
| CRM Manager | Identify customer segments for retention and lifecycle campaigns |
| E-commerce Director | Understand revenue, profit, returns and category performance |
| Finance Partner | Review spend efficiency and recommended budget reallocation |
| BI / Analytics Team | Provide clean datasets and dashboard-ready KPI definitions |

## Business Questions

1. Which customer segments generate the highest revenue and profit?
2. Which channels have the highest ROI and ROAS?
3. Which campaigns have high spend but weak conversion?
4. Which customers are most at risk of churn?
5. Which channels should receive more or less budget?
6. Which categories and regions are most profitable?

## Scope

### In Scope

- Synthetic customer, order and campaign data generation
- Data cleaning and preparation
- Marketing KPI analysis
- RFM customer segmentation
- Churn-risk classification
- Budget reallocation recommendation
- BI-ready CSV outputs
- Dashboard blueprint
- SQL scripts
- Executive summary

### Out of Scope

- Real Zalando data
- Confidential commercial information
- Multi-touch attribution modelling
- Machine learning churn prediction
- Live Power BI or Tableau file creation

## Data Requirements

| Entity | Required Fields |
|---|---|
| Customers | Customer ID, age group, gender, country, acquisition channel, signup date, device type, category preference |
| Orders | Order ID, customer ID, order date, revenue, cost, profit, discount, return flag, campaign ID, channel, device, country |
| Campaigns | Campaign ID, channel, objective, spend, impressions, clicks, conversions, attributed revenue, country, device |

## Success Criteria

- At least 10,000 customers, 50,000 orders and 100 campaigns.
- All required KPIs calculated and documented.
- SQL scripts support common business questions.
- Clean CSV files are ready for Power BI or Tableau.
- Executive summary provides clear recommendations.
- Project is suitable for GitHub, LinkedIn, CV and interview discussion.
"""
(BASE / 'business_requirements_document.md').write_text(textwrap.dedent(brd_md).strip() + '\n')

analysis_report_md = f"""
# Analysis Report

## 1. Data Cleaning and Preparation

The project generated three raw datasets: customers, orders and campaigns. The cleaning workflow removed duplicate IDs, converted date fields, created derived metrics and joined all data into `fact_orders_customer_campaign.csv`.

### Cleaning Checks

| Check | Result |
|---|---|
| Customer rows | {len(customers_clean):,} |
| Order rows | {len(orders_clean):,} |
| Campaign rows | {len(campaigns_clean):,} |
| Duplicate customer IDs | {customers_clean['customer_id'].duplicated().sum()} |
| Duplicate order IDs | {orders_clean['order_id'].duplicated().sum()} |
| Duplicate campaign IDs | {campaigns_clean['campaign_id'].duplicated().sum()} |

## 2. Exploratory Data Analysis

### Revenue Trend

Revenue is tracked monthly in `monthly_revenue.csv` and visualised in `visuals/01_monthly_revenue_trend.png`.

### Product Category Performance

`{category_performance.sort_values('profit', ascending=False).iloc[0]['product_category']}` generated the highest category profit. `{high_return_cat['product_category']}` had the highest return rate, which reduces net revenue after returns.

### Country Performance

`{top_country['country']}` was the highest revenue country, followed by `{country_performance.sort_values('revenue', ascending=False).iloc[1]['country']}`.

### Device Performance

Mobile is the dominant device for order volume, reflecting typical fashion e-commerce browsing and buying behaviour.

## 3. Marketing ROI Analysis

| Top Channel by ROAS | ROAS | ROI |
|---|---:|---:|
| {top_channel['channel']} | {top_channel['roas']:.2f} | {top_channel['roi']:.2f} |

Key marketing findings:

- Email has high ROAS but limited scale.
- Organic Search delivers efficient revenue with low paid media cost.
- Google Search has higher CPA but captures strong purchase intent.
- Meta Ads generates traffic volume but weaker conversion quality.
- TikTok Ads supports new customer acquisition but needs retention follow-up.
- Display Ads has weaker direct-response efficiency and should be tightly capped.

## 4. Customer Segmentation

RFM segmentation identifies customer quality based on recency, frequency and monetary value.

| Segment | Customers | Revenue | Avg CLV |
|---|---:|---:|---:|
"""
for _, r in segment_performance.sort_values('revenue', ascending=False).iterrows():
    analysis_report_md += f"| {r['customer_segment']} | {int(r['customers']):,} | €{r['revenue']:,.0f} | €{r['avg_clv']:,.0f} |\n"
analysis_report_md += """

## 5. Churn-Risk Analysis

Churn risk is classified using days since last purchase, purchase frequency, discount dependency and return rate. High-risk customers are exported to `churn_risk_customer_list.csv` for retention targeting.

## 6. Budget Reallocation Recommendation

The budget table recommends shifting spend away from low-ROI campaigns and toward channels with stronger retention, intent and conversion quality.

"""
for _, r in budget_reallocation.iterrows():
    analysis_report_md += f"- **{r['channel']}**: current €{r['current_spend']:,.0f}, recommended €{r['recommended_spend']:,.0f}, change €{r['increase_decrease_amount']:,.0f}. {r['reason_for_change']}\n"
(BASE / 'reports/analysis_report.md').write_text(textwrap.dedent(analysis_report_md).strip() + '\n')

data_cleaning_md = """
# Data Cleaning Report

## Cleaning Steps Completed

1. Loaded customer, order and campaign datasets.
2. Checked missing values and duplicate IDs.
3. Converted date fields to datetime format.
4. Created derived order fields:
   - `order_month`
   - `net_revenue_after_returns`
   - `gross_margin_pct`
   - `is_discounted_order`
5. Created campaign KPI fields:
   - ROI
   - ROAS
   - CTR
   - CPC
   - CPA
   - Conversion rate
   - Revenue per click
   - Campaign profit
   - Budget efficiency score
6. Created customer KPI fields:
   - CLV
   - AOV
   - Purchase frequency
   - Days since last purchase
   - Discount dependency
   - Return rate
   - High-value customer flag
7. Created RFM scores and customer segments.
8. Created churn-risk score and churn-risk label.
9. Exported clean CSVs and SQLite database.

## Important Notes

- Synthetic data uses a fixed seed for reproducibility.
- Revenue is simulated as post-discount order revenue.
- Net revenue after returns excludes returned orders.
- Churn scoring is rules-based for business explainability.
"""
(BASE / 'reports/data_cleaning_report.md').write_text(textwrap.dedent(data_cleaning_md).strip() + '\n')

recommendations_md = """
# Marketing Recommendations

## 1. Increase Budget for High-ROAS Channels

Email and Organic Search should receive more investment because they generate efficient revenue with lower acquisition cost. Email should be scaled carefully because audience size can limit growth.

## 2. Reduce Spend on High-CPA, Low-Conversion Campaigns

Campaigns with high spend and low conversion should be paused, reworked or moved into a test budget. This protects margin and improves marketing accountability.

## 3. Create Retention Campaigns for At-Risk Customers

At-Risk customers should receive win-back journeys with personalised product recommendations, limited-time offers and reminders based on previous category preference.

## 4. Personalise Offers for Champions and Loyal Customers

High-value customers should receive early access, premium edits, loyalty benefits and personalised recommendations instead of blanket discounts.

## 5. Reduce Excessive Discounting

Discount Seekers have high purchase activity but weaker margin. The company should test non-discount incentives such as bundles, loyalty points and free delivery thresholds.

## 6. Monitor Return-Heavy Categories

Categories with high return rates should be monitored weekly. Recommended actions include better size guidance, product detail improvements and return reason analysis.

## 7. Build a Monthly Executive Dashboard

Leadership should review revenue, profit, ROAS, CPA, customer segment performance, churn risk and recommended budget shifts every month.
"""
(BASE / 'reports/marketing_recommendations.md').write_text(textwrap.dedent(recommendations_md).strip() + '\n')

dashboard_blueprint = """
# Power BI / Tableau Dashboard Blueprint

## Page 1: Executive Overview

### Purpose
Show leadership the commercial health of the e-commerce business at a glance.

### KPI Cards

- Revenue
- Profit
- ROAS
- ROI
- Orders
- Conversion rate
- Top channel
- Top customer segment

### Visuals

- Monthly revenue trend
- Revenue and profit by country
- Revenue by customer segment
- Marketing spend vs attributed revenue

### Filters

- Date range
- Country
- Channel
- Device type
- Product category

## Page 2: Marketing Performance

### Purpose
Help marketing teams evaluate spend efficiency and campaign quality.

### Visuals

- Spend by channel
- ROAS by channel
- CPA by channel
- Campaign performance table
- High-spend low-return campaign table

### Table Columns

- Campaign ID
- Campaign name
- Channel
- Spend
- Revenue attributed
- ROI
- ROAS
- CPA
- CTR
- Conversion rate
- Budget efficiency score

## Page 3: Customer Segmentation

### Purpose
Show which customer groups generate value and which groups require retention action.

### Visuals

- RFM segment distribution
- Revenue by segment
- CLV by segment
- Churn risk by segment
- Discount dependency by segment

### Recommended Actions by Segment

| Segment | Action |
|---|---|
| Champions | VIP access, early product drops, loyalty benefits |
| Loyal Customers | Personalised recommendations and cross-sell journeys |
| Potential Loyalists | Nurture with second-purchase incentives |
| New Customers | Welcome journey and category education |
| At Risk | Win-back emails and personalised offers |
| Hibernating | Low-cost reactivation testing |
| Discount Seekers | Reduce blanket discounts and test bundles |
| High-Value Customers | Premium retention and concierge-style messaging |

## Page 4: Business Recommendations

### Purpose
Turn analysis into decisions.

### Visuals

- Budget reallocation table
- Recommended spend by channel
- Top growth opportunities
- Retention recommendation matrix
- Segment targeting strategy

### Output Table

- Channel
- Current spend
- Recommended spend
- Increase/decrease amount
- Reason for change
- Expected business impact
"""
(BASE / 'dashboards/dashboard_blueprint.md').write_text(textwrap.dedent(dashboard_blueprint).strip() + '\n')

data_model_md = """
# Power BI / Tableau Data Model

## Recommended Tables

### Fact Table

`fact_orders_customer_campaign.csv`

Use this as the central fact table for most dashboard visuals.

### Dimension / Summary Tables

- `customers_clean.csv`
- `orders_clean.csv`
- `campaigns_clean.csv`
- `marketing_kpis_by_channel.csv`
- `segment_performance.csv`
- `budget_reallocation.csv`
- `category_performance.csv`
- `country_performance.csv`
- `device_performance.csv`
- `monthly_revenue.csv`

## Suggested Relationships

| From Table | Key | To Table | Key | Relationship |
|---|---|---|---|---|
| orders_clean | customer_id | customers_clean | customer_id | Many-to-one |
| orders_clean | campaign_id | campaigns_clean | campaign_id | Many-to-one |
| fact_orders_customer_campaign | customer_id | customers_clean | customer_id | Many-to-one |
| fact_orders_customer_campaign | campaign_id | campaigns_clean | campaign_id | Many-to-one |

## Suggested Measures

- Revenue = SUM(orders_clean[revenue])
- Profit = SUM(orders_clean[profit])
- Profit Margin = DIVIDE([Profit], [Revenue])
- Orders = DISTINCTCOUNT(orders_clean[order_id])
- Return Rate = AVERAGE(orders_clean[return_flag])
- Net Revenue After Returns = SUM(orders_clean[net_revenue_after_returns])
- ROAS = DIVIDE(SUM(campaigns_clean[revenue_attributed]), SUM(campaigns_clean[spend]))
- ROI = DIVIDE(SUM(campaigns_clean[revenue_attributed]) - SUM(campaigns_clean[spend]), SUM(campaigns_clean[spend]))
- CPA = DIVIDE(SUM(campaigns_clean[spend]), SUM(campaigns_clean[conversions]))
- CPC = DIVIDE(SUM(campaigns_clean[spend]), SUM(campaigns_clean[clicks]))
- CTR = DIVIDE(SUM(campaigns_clean[clicks]), SUM(campaigns_clean[impressions]))
- Conversion Rate = DIVIDE(SUM(campaigns_clean[conversions]), SUM(campaigns_clean[clicks]))
"""
(BASE / 'dashboards/powerbi_tableau_data_model.md').write_text(textwrap.dedent(data_model_md).strip() + '\n')

# Write runnable script by copying this generator into project scripts with path adjusted
script_text = Path(__file__).read_text()
script_text = script_text.replace("BASE = Path(__file__).resolve().parents[1]", "BASE = Path(__file__).resolve().parents[1]")
(BASE / 'scripts/build_project.py').write_text(script_text)

# Create notebook with concise executable cells
notebook = {
    "cells": [
        {"cell_type": "markdown", "metadata": {}, "source": ["# Zalando-Style Customer Segmentation and Marketing ROI Analysis\n", "\n", "This notebook provides a recruiter-friendly walkthrough of the generated project outputs. Run `scripts/build_project.py` to regenerate all data, visuals and reports.\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["from pathlib import Path\n", "import pandas as pd\n", "import matplotlib.pyplot as plt\n", "\n", "BASE = Path('..')\n", "processed = BASE / 'data' / 'processed'\n", "customers = pd.read_csv(processed / 'customers_clean.csv')\n", "orders = pd.read_csv(processed / 'orders_clean.csv')\n", "campaigns = pd.read_csv(processed / 'campaigns_clean.csv')\n", "channel_kpis = pd.read_csv(processed / 'marketing_kpis_by_channel.csv')\n", "segment_performance = pd.read_csv(processed / 'segment_performance.csv')\n", "customers.head()\n"]},
        {"cell_type": "markdown", "metadata": {}, "source": ["## Executive KPI Snapshot\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["summary = pd.read_csv(processed / 'executive_summary_table.csv')\n", "summary\n"]},
        {"cell_type": "markdown", "metadata": {}, "source": ["## Channel Performance\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["channel_kpis.sort_values('roas', ascending=False)[['channel','total_spend','total_revenue','roas','roi','cpa','conversion_rate']]\n"]},
        {"cell_type": "markdown", "metadata": {}, "source": ["## Customer Segment Performance\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["segment_performance.sort_values('revenue', ascending=False)\n"]},
        {"cell_type": "markdown", "metadata": {}, "source": ["## Budget Reallocation\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["pd.read_csv(processed / 'budget_reallocation.csv')\n"]},
        {"cell_type": "markdown", "metadata": {}, "source": ["## Visual Example\n"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["monthly = pd.read_csv(processed / 'monthly_revenue.csv')\n", "ax = monthly.plot(x='order_month', y='revenue', marker='o', legend=False)\n", "ax.set_title('Monthly Revenue Trend')\n", "ax.set_xlabel('Order Month')\n", "ax.set_ylabel('Revenue')\n", "plt.xticks(rotation=45)\n", "plt.tight_layout()\n"]}
    ],
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"}
    },
    "nbformat": 4,
    "nbformat_minor": 5
}
(BASE / 'notebooks/01_zalando_style_analysis.ipynb').write_text(json.dumps(notebook, indent=2))

# small json manifest
manifest = {
    'project_title': 'Zalando-Style Customer Segmentation and Marketing ROI Analysis',
    'seed': SEED,
    'analysis_date': str(ANALYSIS_DATE.date()),
    'customers': int(len(customers_clean)),
    'orders': int(len(orders_clean)),
    'campaigns': int(len(campaigns_clean)),
    'countries': countries,
    'channels': channels,
    'product_categories': product_categories,
    'generated_at': datetime.utcnow().isoformat() + 'Z'
}
(BASE / 'reports/project_manifest.json').write_text(json.dumps(manifest, indent=2))

# Duplicate expected channel_kpis filename if user scans names
channel_kpis.to_csv(BASE / 'data/processed/channel_kpis.csv', index=False)

# Zip entire project
zip_path = Path('/mnt/data/zalando_style_customer_segmentation_roi_project.zip')
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for path in BASE.rglob('*'):
        if path.is_file():
            zf.write(path, arcname=path.relative_to(BASE.parent))

print(json.dumps({
    'base': str(BASE),
    'zip': str(zip_path),
    'customers': len(customers_clean),
    'orders': len(orders_clean),
    'campaigns': len(campaigns_clean),
    'total_revenue': round(float(orders_clean['revenue'].sum()), 2),
    'total_profit': round(float(orders_clean['profit'].sum()), 2),
    'overall_roas': round(float(campaigns_clean['revenue_attributed'].sum()/campaigns_clean['spend'].sum()), 3),
    'top_channel_by_roas': top_channel['channel'],
    'top_segment_by_revenue': top_segment['customer_segment'],
    'files': len([p for p in BASE.rglob('*') if p.is_file()])
}, indent=2))
