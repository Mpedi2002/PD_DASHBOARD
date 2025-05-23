import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, time, timedelta
import pycountry
import random
import string
import os


# --- Configuration & Styles ---
st.set_page_config(page_title="AI Solutions Dashboard", page_icon="📊", layout="wide")
st.markdown(
    """
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #1e3a8a;
            --secondary-color: #3b82f6;
            --text-color: #1f2937;
            --bg-color: #f9fafb;
            --green: #22c55e;
            --amber: #f59e0b;
            --red: #ef4444;
        }
        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Inter', sans-serif;
        }
        .block-container {
            padding: 0.5rem;
            max-width: 1400px;
        }
        #MainMenu, footer {visibility: hidden;}
        header {visibility: hidden;}
        section[data-testid="stSidebar"] {
            width: 250px !important;
            background-color: #ffffff;
            border-right: 1px solid #e5e7eb;
        }
        .metric-card {
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            padding: 0.4rem;
            background: #ffffff;
            width: 100%;
            height: 80px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-2px);
        }
        .metric-card.green {
            border-left: 4px solid var(--green);
        }
        .metric-card.amber {
            border-left: 4px solid var(--amber);
        }
        .metric-card.red {
            border-left: 4px solid var(--red);
        }
        .metrics-container {
            display: flex;
            flex-direction: row;
            gap: 0.4rem;
            margin-bottom: 0.4rem;
        }
        .visual-container {
            border: 1px solid #e5e7eb;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            background: #ffffff;
            padding: 0.3rem;
            margin: 0.3rem 0;
            transition: transform 0.2s;
        }
        .visual-container:hover {
            transform: scale(1.02);
        }
        .legend-container {
            display: flex;
            gap: 1rem;
            justify-content: center;
            margin-top: 0.3rem;
            font-size: 0.7rem;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 0.3rem;
        }
        .legend-color {
            width: 12px;
            height: 12px;
            border-radius: 2px;
        }
        .progress-bar {
            height: 10px;
            background-color: #e5e7eb;
            border-radius: 5px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            transition: width 0.3s ease-in-out;
        }
        .stButton>button {
            background-color: var(--secondary-color);
            color: white;
            border: none;
            border-radius: 4px;
            padding: 0.3rem 0.6rem;
            font-size: 0.7rem;
        }
        .stButton>button:hover {
            background-color: var(--primary-color);
        }
        .plotly-chart-container {
            margin: 0.2rem 0 !important;
            padding: 0.2rem !important;
        }
        .stPlotlyChart {
            height: 140px !important;
        }
        .compact-table {
            font-size: 0.7rem;
            max-height: 160px;
            overflow-y: auto;
        }
        .stSelectbox {
            margin-bottom: 0.4rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Initialize Session State ---
if "export_id" not in st.session_state:
    st.session_state.export_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=32))
if "user_role" not in st.session_state:
    st.session_state.user_role = "Sales Manager"
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0
if "active_subtab" not in st.session_state:
    st.session_state.active_subtab = 0

# --- Configuration ---
PRODUCTS = ["AI Assistant", "Smart Prototype", "Analytics Suite"]
YEARLY_TARGET = 120000  # Per salesperson
TEAM_YEARLY_TARGET = YEARLY_TARGET * 5  # For 5 salespeople
DATA_CSV_PATH = os.path.join(os.path.dirname(__file__), "combined_data.csv")



# --- Data Processing Functions ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv(DATA_CSV_PATH, parse_dates=["timestamp"], encoding='utf-8')
        # Ensure numeric types
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
        df['unit_cost'] = pd.to_numeric(df['unit_cost'], errors='coerce').fillna(0)
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        # Compute P&L
        df['revenue'] = df['price'] * df['quantity']
        df['cost'] = df['unit_cost'] * df['quantity']
        df['profit'] = df['revenue'] - df['cost']
        df['profit_margin'] = df['profit'] / df['revenue'].replace({0: 1})
        # Optimize with index
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

def filter_df(data, start_date, end_date, countries, product=None):
    try:
        filtered = data.copy()
        if start_date:
            start_date = pd.to_datetime(start_date, errors='coerce')
            if pd.isna(start_date):
                return pd.DataFrame()
            filtered = filtered[filtered.index >= start_date]
        if end_date:
            end_date = pd.to_datetime(end_date, errors='coerce')
            if pd.isna(end_date):
                return pd.DataFrame()
            filtered = filtered[filtered.index <= end_date]
        if countries:
            filtered = filtered[filtered['country'].isin(countries)]
        if product:
            filtered = filtered[filtered['product'] == product]
        return filtered
    except Exception as e:
        st.error(f"Error filtering data: {e}")
        return pd.DataFrame()

def get_countries(df):
    try:
        return sorted(df['country'].dropna().unique().tolist())
    except Exception:
        return []

def get_sales(df, start_date, end_date, countries):
    try:
        sales_df = df[df['event_type'] == 'sale']
        filtered = filter_df(sales_df, start_date, end_date, countries)
        if filtered.empty:
            return []
        grouped = (
            filtered
            .reset_index()
            .groupby(['country', 'product'])
            .agg(
                sales_count=('quantity', 'sum'),
                revenue=('revenue', 'sum'),
                profit=('profit', 'sum')
            )
            .reset_index()
        )
        return grouped.to_dict(orient='records')
    except Exception:
        return []

def get_web_events(df, start_date, end_date, countries):
    try:
        web_df = df[df['event_type'] == 'web']
        filtered = filter_df(web_df, start_date, end_date, countries)
        if filtered.empty:
            return []
        target_urls = ['/request-demo', '/promotional-event', '/ai-assistant']
        events = filtered[filtered['url'].isin(target_urls)]
        grouped = events.reset_index().groupby(['country', 'url']).size().reset_index(name='count')
        return grouped.to_dict(orient='records')
    except Exception:
        return []

def get_metrics(df, start_date, end_date, countries):
    try:
        filtered = filter_df(df, start_date, end_date, countries)
        if filtered.empty:
            return {
                "total_sales": 0,
                "total_revenue": 0.0,
                "total_profit": 0.0,
                "demo_requests": 0,
                "promo_requests": 0,
                "ai_requests": 0
            }
        sales = filtered[filtered['event_type'] == 'sale']
        web = filtered[filtered['event_type'] == 'web']
        return {
            "total_sales": int(sales.shape[0]),
            "total_revenue": float(sales['revenue'].sum()),
            "total_profit": float(sales['profit'].sum()),
            "demo_requests": int(web[web['url'] == '/request-demo'].shape[0]),
            "promo_requests": int(web[web['url'] == '/promotional-event'].shape[0]),
            "ai_requests": int(web[web['url'] == '/ai-assistant'].shape[0])
        }
    except Exception:
        return {
            "total_sales": 0,
            "total_revenue": 0.0,
            "total_profit": 0.0,
            "demo_requests": 0,
            "promo_requests": 0,
            "ai_requests": 0
        }

def get_stats(df, start_date, end_date, countries):
    try:
        filtered = filter_df(df, start_date, end_date, countries)
        if filtered.empty:
            return []
        stats = (
            filtered
            .reset_index()
            .groupby('event_type')
            .agg(
                mean_price=('price', 'mean'),
                std_price=('price', 'std'),
                mean_quantity=('quantity', 'mean'),
                std_quantity=('quantity', 'std')
            )
            .round(2)
            .reset_index()
        )
        return stats.to_dict(orient='records')
    except Exception:
        return []

def get_software_sales(df, start_date, end_date, countries):
    try:
        products = ["AI Assistant", "Smart Prototype", "Analytics Suite"]
        sales_df = df[(df['event_type'] == 'sale') & df['product'].isin(products)]
        filtered = filter_df(sales_df, start_date, end_date, countries)
        if filtered.empty:
            return {"software_sales_count": 0, "software_revenue": 0.0}
        return {
            "software_sales_count": int(filtered.shape[0]),
            "software_revenue": float(filtered['revenue'].sum())
        }
    except Exception:
        return {"software_sales_count": 0, "software_revenue": 0.0}

def get_conversion_funnel(df, start_date, end_date, countries):
    try:
        filtered = filter_df(df, start_date, end_date, countries)
        if filtered.empty:
            return {"web_visits": 0, "demo_requests": 0, "sales": 0, "conversion_rate": 0.0}
        visits = filtered[filtered['event_type'] == 'web']
        demos = visits[visits['url'] == '/request-demo']
        sales = filtered[filtered['event_type'] == 'sale']
        web_count = int(visits.shape[0])
        sales_count = int(sales.shape[0])
        return {
            "web_visits": web_count,
            "demo_requests": int(demos.shape[0]),
            "sales": sales_count,
            "conversion_rate": float(sales_count / web_count * 100) if web_count > 0 else 0
        }
    except Exception:
        return {"web_visits": 0, "demo_requests": 0, "sales": 0, "conversion_rate": 0.0}

def get_trends(df, start_date, end_date, countries):
    try:
        sales_df = df[df['event_type'] == 'sale']
        filtered = filter_df(sales_df, start_date, end_date, countries)
        if filtered.empty:
            return []
        grouped = (
            filtered
            .resample('M')
            .agg(
                revenue=('revenue', 'sum'),
                profit=('profit', 'sum')
            )
            .fillna(0)
            .reset_index()
        )
        return grouped.to_dict(orient='records')
    except Exception:
        return []

def get_sales_by_channel(df, start_date, end_date, countries):
    try:
        sales_df = df[df['event_type'] == 'sale']
        filtered = filter_df(sales_df, start_date, end_date, countries)
        if filtered.empty:
            return []
        grouped = (
            filtered
            .reset_index()
            .groupby(['product', 'channel'])
            .agg(
                sales_count=('quantity', 'sum'),
                revenue=('revenue', 'sum')
            )
            .reset_index()
        )
        return grouped.to_dict(orient='records')
    except Exception:
        return []

def get_profit_margin(df, start_date, end_date, countries):
    try:
        sales_df = df[df['event_type'] == 'sale']
        filtered = filter_df(sales_df, start_date, end_date, countries)
        if filtered.empty:
            return []
        grouped = (
            filtered
            .reset_index()
            .groupby(['country', 'product'])
            .agg(
                profit_margin=('profit_margin', 'mean')
            )
            .reset_index()
        )
        return grouped.to_dict(orient='records')
    except Exception:
        return []

def get_top_customers(df, start_date, end_date, countries):
    try:
        sales_df = df[df['event_type'] == 'sale']
        filtered = filter_df(sales_df, start_date, end_date, countries)
        if filtered.empty:
            return []
        grouped = (
            filtered
            .reset_index()
            .groupby(['customer_id', 'country'])
            .agg(
                sales_count=('quantity', 'sum'),
                revenue=('revenue', 'sum')
            )
            .reset_index()
            .nlargest(5, 'revenue')
        )
        return grouped.to_dict(orient='records')
    except Exception:
        return []

def get_web_trends(df, start_date, end_date, countries):
    try:
        web_df = df[df['event_type'] == 'web']
        filtered = filter_df(web_df, start_date, end_date, countries)
        if filtered.empty:
            return []
        target_urls = ['/request-demo', '/promotional-event', '/ai-assistant']
        events = filtered[filtered['url'].isin(target_urls)]
        if events.empty:
            return []
        date_range = pd.date_range(
            start=start_date or filtered.index.min(),
            end=end_date or filtered.index.max(),
            freq='W'
        )
        grouped = (
            events
            .groupby([pd.Grouper(freq='W'), 'url'])
            .size()
            .unstack(fill_value=0)
            .reindex(date_range, fill_value=0)
            .reset_index()
            .rename(columns={'index': 'timestamp'})
        )
        for url in target_urls:
            col_name = url
            if col_name not in grouped.columns:
                grouped[col_name] = 0
        grouped = grouped.rename(columns={
            '/request-demo': 'request_demo',
            '/promotional-event': 'promotional_event',
            '/ai-assistant': 'ai_assistant'
        })
        return grouped.to_dict(orient='records')
    except Exception:
        return []

def get_sales_stats(df, start_date, end_date, countries):
    try:
        sales_df = df[df['event_type'] == 'sale'].copy()
        filtered = filter_df(sales_df, start_date, end_date, countries)
        if filtered.empty:
            return []
        filtered['job_type'] = filtered.get('job_type', 'Unknown').fillna('Unknown')
        stats = (
            filtered
            .reset_index()
            .groupby(['country', 'product', 'job_type'])
            .agg(
                mean_sales_count=('quantity', lambda x: x.mean() if len(x) > 0 else 0),
                std_sales_count=('quantity', lambda x: x.std() if len(x) > 1 else 0),
                mean_revenue=('revenue', lambda x: x.mean() if len(x) > 0 else 0),
                std_revenue=('revenue', lambda x: x.std() if len(x) > 1 else 0),
                mean_profit=('profit', lambda x: x.mean() if len(x) > 0 else 0),
                std_profit=('profit', lambda x: x.std() if len(x) > 1 else 0)
            )
            .round(2)
            .reset_index()
        )
        return stats.to_dict(orient='records')
    except Exception:
        return []

def get_salesperson_performance(df, start_date, end_date, countries):
    try:
        sales_df = df[df['event_type'] == 'sale']
        filtered = filter_df(sales_df, start_date, end_date, countries)
        if filtered.empty:
            return []
        YEARLY_TARGET = 120000
        MONTHLY_TARGET = YEARLY_TARGET / 12
        grouped = (
            filtered
            .reset_index()
            .groupby(['salesperson_id', 'salesperson_name', 'country'])
            .agg(
                sales_count=('quantity', 'sum'),
                revenue=('revenue', 'sum'),
                profit=('profit', 'sum')
            )
            .reset_index()
        )
        grouped['yearly_target_achieved'] = (grouped['revenue'] / YEARLY_TARGET * 100).round(2)
        filtered['month'] = filtered.index.to_period('M')
        monthly = (
            filtered
            .reset_index()
            .groupby(['salesperson_id', 'salesperson_name', 'month'])
            .agg(
                monthly_sales_count=('quantity', 'sum'),
                monthly_revenue=('revenue', 'sum')
            )
            .reset_index()
        )
        monthly['monthly_target_achieved'] = (monthly['monthly_revenue'] / MONTHLY_TARGET * 100).round(2)
        monthly_stats = (
            monthly
            .groupby(['salesperson_id', 'salesperson_name'])
            .agg(
                mean_monthly_sales=('monthly_sales_count', 'mean'),
                std_monthly_sales=('monthly_sales_count', 'std'),
                mean_monthly_revenue=('monthly_revenue', 'mean'),
                std_monthly_revenue=('monthly_revenue', 'std')
            )
            .round(2)
            .reset_index()
        )
        latest_month = monthly.groupby('salesperson_id')['month'].max().reset_index()
        monthly_latest = monthly.merge(latest_month, on=['salesperson_id', 'month'])
        grouped = grouped.merge(
            monthly_latest[['salesperson_id', 'monthly_target_achieved']],
            on='salesperson_id',
            how='left'
        ).merge(
            monthly_stats[['salesperson_id', 'mean_monthly_sales', 'std_monthly_sales',
                          'mean_monthly_revenue', 'std_monthly_revenue']],
            on='salesperson_id',
            how='left'
        ).fillna({
            'monthly_target_achieved': 0,
            'mean_monthly_sales': 0,
            'std_monthly_sales': 0,
            'mean_monthly_revenue': 0,
            'std_monthly_revenue': 0
        })
        return grouped.to_dict(orient='records')
    except Exception:
        return []

def get_salesperson_comparison(df, start_date, end_date, countries):
    try:
        sales_df = df[df['event_type'] == 'sale']
        filtered = filter_df(sales_df, start_date, end_date, countries)
        if filtered.empty:
            return {"individuals": [], "team": [], "team_stats": []}
        YEARLY_TARGET = 120000
        TEAM_YEARLY_TARGET = YEARLY_TARGET * 10
        filtered['year'] = filtered.index.year
        individual = (
            filtered
            .reset_index()
            .groupby(['year', 'salesperson_id', 'salesperson_name', 'country'])
            .agg(
                sales_count=('quantity', 'sum'),
                revenue=('revenue', 'sum'),
                profit=('profit', 'sum')
            )
            .reset_index()
        )
        individual['yearly_target_achieved'] = (individual['revenue'] / YEARLY_TARGET * 100).round(2)
        team = (
            filtered
            .reset_index()
            .groupby('year')
            .agg(
                team_sales_count=('quantity', 'sum'),
                team_revenue=('revenue', 'sum'),
                team_profit=('profit', 'sum')
            )
            .reset_index()
        )
        team['team_target_achieved'] = (team['team_revenue'] / TEAM_YEARLY_TARGET * 100).round(2)
        team_stats = (
            filtered
            .reset_index()
            .groupby(['year', 'salesperson_id'])
            .agg(
                sales_count=('quantity', 'sum'),
                revenue=('revenue', 'sum')
            )
            .reset_index()
            .groupby('year')
            .agg(
                mean_team_sales=('sales_count', 'mean'),
                std_team_sales=('sales_count', 'std'),
                mean_team_revenue=('revenue', 'mean'),
                std_team_revenue=('revenue', 'std')
            )
            .round(2)
            .reset_index()
        )
        return {
            "individuals": individual.to_dict(orient='records'),
            "team": team.to_dict(orient='records'),
            "team_stats": team_stats.to_dict(orient='records')
        }
    except Exception:
        return {"individuals": [], "team": [], "team_stats": []}

# --- Helpers ---
def country_to_iso3(name):
    try:
        return pycountry.countries.lookup(name).alpha_3
    except:
        return None

def get_country_full_name(code):
    try:
        return pycountry.countries.lookup(code).name
    except:
        return code

def style_fig(fig, height=140):
    fig.update_layout(
        xaxis=dict(showticklabels=True),
        margin=dict(t=10, b=10, r=10, l=10),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=8, color="#1f2937"),
        legend=dict(
            title="",
            orientation="v",
            x=1,
            xanchor="left",
            y=0.5,
            yanchor="middle",
            bgcolor="rgba(255,255,255,0.8)",
            font=dict(size=7),
        ),
        hoverlabel=dict(bgcolor="white", font_size=8, font_family="Inter"),
    )
    return fig

def get_kpi_color(value, good_threshold=80, avg_threshold=50):
    if value >= good_threshold:
        return "green", "fa-check-circle"
    elif value >= avg_threshold:
        return "amber", "fa-exclamation-circle"
    else:
        return "red", "fa-times-circle"

def create_gauge_chart(value, title, max_value=100):
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': title, 'font': {'size': 10}},
            gauge={
                'axis': {'range': [0, max_value], 'tickwidth': 1, 'tickcolor': "black", 'tickfont': {'size': 8}},
                'bar': {'color': "#3b82f6"},
                'steps': [
                    {'range': [0, max_value * 0.5], 'color': "#ef4444"},
                    {'range': [max_value * 0.5, max_value * 0.8], 'color': "#f59e0b"},
                    {'range': [max_value * 0.8, max_value], 'color': "#22c55e"},
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 2},
                    'thickness': 0.75,
                    'value': max_value
                }
            }
        )
    )
    fig.update_layout(
        margin=dict(t=15, b=15, r=15, l=15),
        height=140,
        font=dict(family="Inter", size=8, color="#1f2937"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def create_progress_bar(value, max_value=100):
    percentage = min(value / max_value * 100, 100)
    color = "#22c55e" if percentage >= 80 else "#f59e0b" if percentage >= 50 else "#ef4444"
    return f"""
        <div class="progress-bar">
            <div class="progress-fill" style="width: {percentage}%; background-color: {color};"></div>
        </div>
    """

# --- Load Data ---
df = load_data()
if df.empty:
    st.error("No data available. Please ensure 'combined_data.csv' is present and correctly formatted.")
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.header("Dashboard Controls")
    st.session_state.user_role = st.selectbox(
        "Select Role",
        ["Sales Manager", "Regional Sales Rep", "Marketing Analyst"],
        index=["Sales Manager", "Regional Sales Rep", "Marketing Analyst"].index(st.session_state.user_role)
    )

    st.header("Dashboard Filters")
    preset = st.selectbox(
        "Date Range Preset", ["Custom", "Last 7 Days", "Last 30 Days", "This Year"]
    )
    today = datetime.today()
    if preset == "Last 7 Days":
        sd, ed = today - timedelta(days=7), today
    elif preset == "Last 30 Days":
        sd, ed = today - timedelta(days=30), today
    elif preset == "This Year":
        sd, ed = datetime(today.year, 1, 1), today
    else:
        sd, ed = datetime(2023, 1, 1), today

    sd = st.date_input("Start Date", sd)
    ed = st.date_input("End Date", ed)
    if sd > ed:
        st.error("Start date cannot be after end date.")
        sd, ed = ed, sd
    start_iso = datetime.combine(sd, time.min)
    end_iso = datetime.combine(ed, time.max)

    codes = get_countries(df)
    names = [get_country_full_name(c) for c in codes]
    sel_countries = st.multiselect("Countries", names, default=names[:3] if names else [])
    sel_products = st.multiselect("Products", PRODUCTS, default=PRODUCTS[:3])

    params = {
        "countries": [c for c in codes if get_country_full_name(c) in sel_countries],
        "start_date": start_iso,
        "end_date": end_iso,
    }

# --- Data Loading ---
sales = get_sales(df, params["start_date"], params["end_date"], params["countries"]) or []
df_sales = pd.DataFrame(sales)
if not df_sales.empty:
    df_sales = df_sales[df_sales["product"].isin(sel_products)]

web = get_web_events(df, params["start_date"], params["end_date"], params["countries"]) or []
df_web = pd.DataFrame(web)

metrics = get_metrics(df, params["start_date"], params["end_date"], params["countries"]) or {}
stats_data = get_stats(df, params["start_date"], params["end_date"], params["countries"]) or []
software_sales = get_software_sales(df, params["start_date"], params["end_date"], params["countries"]) or {}
funnel = get_conversion_funnel(df, params["start_date"], params["end_date"], params["countries"]) or {}
trends = get_trends(df, params["start_date"], params["end_date"], params["countries"]) or []
sales_by_channel = get_sales_by_channel(df, params["start_date"], params["end_date"], params["countries"]) or []
profit_margin = get_profit_margin(df, params["start_date"], params["end_date"], params["countries"]) or []
top_customers = get_top_customers(df, params["start_date"], params["end_date"], params["countries"]) or []
web_trends = get_web_trends(df, params["start_date"], params["end_date"], params["countries"]) or []
sales_stats = get_sales_stats(df, params["start_date"], params["end_date"], params["countries"]) or []
salesperson_performance = get_salesperson_performance(df, params["start_date"], params["end_date"], params["countries"]) or []
salesperson_comparison = get_salesperson_comparison(df, params["start_date"], params["end_date"], params["countries"]) or {}

# --- Main App ---
st.title(f"AI Solutions Analytics Dashboard - {st.session_state.user_role}")

# --- Instructions ---
with st.expander("How to Use the Dashboard", expanded=False):
    st.markdown(
        """
        ### Dashboard User Guide
        Welcome to the AI Solutions Analytics Dashboard! Follow these steps to make the most of its features:

        1. **Select Your Role**:
           - In the sidebar, choose your role (Sales Manager, Regional Sales Rep, or Marketing Analyst) from the "Select Role" dropdown.
           - Each role provides tailored tabs and metrics relevant to your responsibilities.

        2. **Apply Filters**:
           - Under "Dashboard Filters" in the sidebar, customize your data view:
             - **Date Range**: Use the preset options (e.g., Last 7 Days) or set a custom start and end date.
             - **Countries**: Select one or more countries to filter data geographically.
             - **Products**: Choose specific products (AI Assistant, Smart Prototype, Analytics Suite) to analyze.
           - Ensure the start date is not after the end date to avoid errors.

        3. **Navigate Tabs**:
           - Use the tabs at the top to explore different analytics views (e.g., Overview, Trends, Sales Team Analysis).
           - For Sales Manager and Regional Sales Rep roles, the "Sales Team Analysis" tab includes subtabs for deeper insights.
           - For Marketing Analyst, tabs for Promotional Correlation and Product Metrics provide insights into promotional impacts and product performance.
           - Interact with charts by hovering for details or selecting options (e.g., team or salesperson) where available.

        4. **Interpret KPIs**:
           - In the Overview tab, metric cards are displayed side by side with visualizations:
             - **Left Column**: Metric cards in a horizontal line, color-coded:
               - **Green**: Performance ≥ 80% of target (✔).
               - **Amber**: Performance between 50% and 80% of target (⚠).
               - **Red**: Performance < 50% of target (✖).
             - **Right Column**: Gauge chart, progress bar, and trend chart show performance metrics like sales or conversion targets.

        5. **Export Data**:
           - In tabs with exportable data, click the "Export" button to generate a CSV file.
           - Use the "Download CSV" button to save data locally, named uniquely with a session ID.

        6. **Interpret Visuals**:
           - **Metric Cards**: Show key metrics with color-coded borders and status icons.
           - **Gauge Chart**: Displays progress toward sales or conversion targets.
           - **Progress Bar**: Visualizes target achievement.
           - **Trend Chart**: Shows revenue trends over time.
           - **Correlation Charts**: Show relationships between promotional events and sales (Marketing Analyst).
           - **Product Metrics**: Display average sales, growth rates, and YoY comparisons (Marketing Analyst).

        7. **Troubleshooting**:
           - If data is missing, check filters (e.g., date range, countries) for alignment with available data.
           - Ensure 'combined_data.csv' is present in the application directory.

        For further assistance, contact the dashboard administrator.
        """
    )

# --- Role-Based Dashboard ---
if st.session_state.user_role == "Sales Manager":
    tab_labels = ["Overview", "Trends", "Sales Channels", "Profitability", "Sales Team Analysis"]
    tabs = st.tabs(tab_labels)
    st.session_state.active_tab = min(st.session_state.active_tab, len(tab_labels) - 1)

    with tabs[0]:
        st.subheader("Key Metrics")
        total_revenue = df_sales['revenue'].sum() if not df_sales.empty else 0
        target_achievement = (total_revenue / TEAM_YEARLY_TARGET * 100) if TEAM_YEARLY_TARGET > 0 else 0
        sales_count = int(df_sales['sales_count'].sum()) if not df_sales.empty else 0
        expected_sales = 1000
        revenue = df_sales['revenue'].sum() if not df_sales.empty else 0
        profit = df_sales['profit'].sum() if not df_sales.empty else 0
        conversion_rate = funnel.get('conversion_rate', 0) if funnel else 0
        metrics = [
            ("Sales", "fas fa-shopping-cart", f"{sales_count:,}", sales_count / expected_sales * 100),
            ("Revenue", "fas fa-dollar-sign", f"${revenue:,.0f}", target_achievement),
            ("Profit", "fas fa-chart-line", f"${profit:,.0f}", profit / revenue * 100 if revenue > 0 else 0),
            ("Conversion Rate", "fas fa-percentage", f"{conversion_rate:.1f}%", conversion_rate, 10, 5),
            ("Target Achievement", "fas fa-bullseye", f"{target_achievement:.1f}%", target_achievement),
        ]
        col_metrics, col_visuals = st.columns([3, 2])
        with col_metrics:
            st.markdown('<div class="visual-container">', unsafe_allow_html=True)
            st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
            for lbl, icon, val, value, *thresholds in metrics:
                color, status_icon = get_kpi_color(value, *thresholds)
                st.markdown(
                    f"""
                    <div class="metric-card {color}">
                        <div style="display: flex; justify-content: space-between;">
                            <i class="{icon}" style="font-size:0.9rem;color:var(--secondary-color)"></i>
                            <i class="fas {status_icon}" style="font-size:0.9rem;color:{color}"></i>
                        </div>
                        <div style="font-weight:600;font-size:0.7rem">{lbl}</div>
                        <div style="font-size:0.8rem;font-weight:700">{val}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(
                """
                <div class="legend-container">
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: var(--green);"></div>
                        <span>Good (≥80%) ✔</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: var(--amber);"></div>
                        <span>Average (50–80%) ⚠</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: var(--red);"></div>
                        <span>Poor (<50%) ✖</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)
        with col_visuals:
            st.markdown('<div class="visual-container">', unsafe_allow_html=True)
            st.plotly_chart(create_gauge_chart(target_achievement, "Team Sales Target", 100), use_container_width=True)
            st.markdown(create_progress_bar(target_achievement), unsafe_allow_html=True)
            if trends:
                df_trends = pd.DataFrame(trends)
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=df_trends["timestamp"],
                        y=df_trends["revenue"],
                        name="Revenue",
                        line=dict(color="#3b82f6"),
                    )
                )
                st.plotly_chart(style_fig(fig), use_container_width=True)
            else:
                st.info("No trend data available.")
            st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        st.subheader("Revenue and Profit Trends")
        if trends:
            df_trends = pd.DataFrame(trends)
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df_trends["timestamp"],
                    y=df_trends["revenue"],
                    name="Revenue",
                    line=dict(color="#3b82f6"),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df_trends["timestamp"],
                    y=df_trends["profit"],
                    name="Profit",
                    line=dict(color="#1e3a8a"),
                )
            )
            st.markdown('<div class="visual-container">', unsafe_allow_html=True)
            st.plotly_chart(style_fig(fig), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("Export Trends Data", key="export_trends"):
                export_data = df_trends.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=export_data,
                    file_name=f"trends_data_{st.session_state.export_id}.csv",
                    mime="text/csv",
                )
        else:
            st.info("No trends data available for the selected filters.")

    with tabs[2]:
        st.subheader("Sales by Product and Channel")
        if sales_by_channel:
            df_channel = pd.DataFrame(sales_by_channel)
            fig = px.bar(
                df_channel,
                x="product",
                y="sales_count",
                color="channel",
                barmode="stack",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            st.markdown('<div class="visual-container">', unsafe_allow_html=True)
            st.plotly_chart(style_fig(fig), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("Export Sales by Channel Data", key="export_channel"):
                export_data = df_channel.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=export_data,
                    file_name=f"sales_channel_data_{st.session_state.export_id}.csv",
                    mime="text/csv",
                )
        else:
            st.info("No sales by channel data available for the selected filters.")

    with tabs[3]:
        st.subheader("Profit Margin by Country and Product")
        if profit_margin:
            df_margin = pd.DataFrame(profit_margin)
            df_margin["country"] = df_margin["country"].apply(get_country_full_name)
            fig = px.density_heatmap(
                df_margin,
                x="country",
                y="product",
                z="profit_margin",
                color_continuous_scale="Blues",
            )
            st.markdown('<div class="visual-container">', unsafe_allow_html=True)
            st.plotly_chart(style_fig(fig), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("Export Profit Margin Data", key="export_margin"):
                export_data = df_margin.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=export_data,
                    file_name=f"profit_margin_data_{st.session_state.export_id}.csv",
                    mime="text/csv",
                )
        else:
            st.info("No profit margin data available for the selected filters.")

    with tabs[4]:  # Sales Team Analysis (Sales Manager)
        st.subheader("Sales Team Analysis")
        if salesperson_comparison.get("individuals") and salesperson_comparison.get("team"):
            df_individual = pd.DataFrame(salesperson_comparison["individuals"])
            df_individual["country"] = df_individual["country"].apply(get_country_full_name)
            top_salespeople = df_individual.groupby("salesperson_name")["revenue"].sum().nlargest(5).index
            df_individual = df_individual[df_individual["salesperson_name"].isin(top_salespeople)]
            df_team = pd.DataFrame(salesperson_comparison["team"])
            
            subtab_labels = ["Team & Individual", "Statistics & Comparison"]
            st.session_state.active_subtab = subtab_labels.index(st.selectbox(
                "Select Subtab",
                subtab_labels,
                index=st.session_state.active_subtab,
                key="subtab_select_mgr"
            ))

            if st.session_state.active_subtab == 0:
                st.markdown("#### Team & Individual Performance (2023-2025)")
                options = ["Team"] + sorted(df_individual["salesperson_name"].unique().tolist())
                selected = st.selectbox("Select Team or Salesperson", options, key="select_team_ind_mgr")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    if selected == "Team":
                        fig = go.Figure()
                        fig.add_trace(
                            go.Scatter(
                                x=df_team["year"],
                                y=df_team["team_revenue"],
                                name="Team Revenue",
                                line=dict(color="#3b82f6"),
                            )
                        )
                        fig.add_hline(y=TEAM_YEARLY_TARGET, line_dash="dash", line_color="red", annotation_text="Team Target")
                    else:
                        df_person = df_individual[df_individual["salesperson_name"] == selected]
                        fig = go.Figure()
                        fig.add_trace(
                            go.Scatter(
                                x=df_person["year"],
                                y=df_person["revenue"],
                                name="Revenue",
                                line=dict(color="#3b82f6"),
                            )
                        )
                        fig.add_hline(y=YEARLY_TARGET, line_dash="dash", line_color="red", annotation_text="Yearly Target")
                    st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                    st.plotly_chart(style_fig(fig), use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                    st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
                    if selected == "Team":
                        total_revenue = df_team["team_revenue"].sum()
                        latest_target = df_team[df_team["year"] == df_team["year"].max()]["team_target_achieved"].iloc[0] if not df_team.empty else 0
                    else:
                        df_person = df_individual[df_individual["salesperson_name"] == selected]
                        total_revenue = df_person["revenue"].sum()
                        latest_target = df_person[df_person["year"] == df_person["year"].max()]["yearly_target_achieved"].iloc[0] if not df_person.empty else 0
                    color, status_icon = get_kpi_color(total_revenue / TEAM_YEARLY_TARGET * 100 if selected == 'Team' else total_revenue / YEARLY_TARGET * 100)
                    st.markdown(
                        f"""
                        <div class="metric-card {color}">
                            <div style="display: flex; justify-content: space-between;">
                                <i class="fas fa-dollar-sign" style="font-size:0.9rem;color:var(--secondary-color)"></i>
                                <i class="fas {status_icon}" style="font-size:0.9rem;color:{color}"></i>
                            </div>
                            <div style="font-weight:600;font-size:0.7rem">Total Revenue</div>
                            <div style="font-size:0.8rem;font-weight:700">${total_revenue:,.0f}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    color, status_icon = get_kpi_color(latest_target)
                    st.markdown(
                        f"""
                        <div class="metric-card {color}">
                            <div style="display: flex; justify-content: space-between;">
                                <i class="fas fa-bullseye" style="font-size:0.9rem;color:var(--secondary-color)"></i>
                                <i class="fas {status_icon}" style="font-size:0.9rem;color:{color}"></i>
                            </div>
                            <div style="font-weight:600;font-size:0.7rem">Target Achieved</div>
                            <div style="font-size:0.8rem;font-weight:700">{latest_target:.0f}%</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

            elif st.session_state.active_subtab == 1:
                st.markdown("#### Statistics & Comparison (2023-2025)")
                col1, col2 = st.columns([1, 1])
                with col1:
                    if sales_stats:
                        df_sales_stats = pd.DataFrame(sales_stats)
                        df_sales_stats["country"] = df_sales_stats["country"].apply(get_country_full_name)
                        fig_heatmap = px.density_heatmap(
                            df_sales_stats,
                            x="country",
                            y="product",
                            z="mean_sales_count",
                            color_continuous_scale="Blues",
                            text_auto=".1f",
                            hover_data={
                                "std_sales_count": ":,.1f",
                                "mean_revenue": ":$,.0f",
                                "std_revenue": ":$,.0f",
                                "job_type": True
                            },
                            title="Mean Sales by Country/Product",
                        )
                        st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                        st.plotly_chart(style_fig(fig_heatmap), use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                with col2:
                    fig_compare = px.bar(
                        df_individual,
                        x="salesperson_name",
                        y="revenue",
                        color="year",
                        barmode="group",
                        color_discrete_sequence=px.colors.qualitative.Pastel,
                        title="Revenue Comparison",
                    )
                    fig_compare.add_hline(y=YEARLY_TARGET, line_dash="dash", line_color="red", annotation_text="Yearly Target")
                    st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                    st.plotly_chart(style_fig(fig_compare), use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                with st.expander("View Basic Statistics"):
                    if sales_stats:
                        st.dataframe(
                            df_sales_stats[[
                                "country", "product", "job_type",
                                "mean_sales_count", "std_sales_count",
                                "mean_revenue", "std_revenue"
                            ]],
                            column_config={
                                "country": "Country",
                                "product": "Product",
                                "job_type": "Job Type",
                                "mean_sales_count": st.column_config.NumberColumn("Mean Sales", format="%.1f"),
                                "std_sales_count": st.column_config.NumberColumn("Std Sales", format="%.1f"),
                                "mean_revenue": st.column_config.NumberColumn("Mean Revenue", format="$%.0f"),
                                "std_revenue": st.column_config.NumberColumn("Std Revenue", format="$%.0f"),
                            },
                            use_container_width=True,
                        )
                st.markdown('</div>', unsafe_allow_html=True)

            if st.button("Export Sales Team Analysis Data", key="export_sales_team"):
                export_data = {
                    "individuals": df_individual.to_csv(index=False),
                    "team": df_team.to_csv(index=False),
                    "sales_stats": df_sales_stats.to_csv(index=False) if sales_stats else ""
                }
                export_csv = (
                    "Individual Performance:\n" + export_data["individuals"] +
                    "\nTeam Performance:\n" + export_data["team"] +
                    "\nSales Statistics:\n" + export_data["sales_stats"]
                )
                st.download_button(
                    label="Download CSV",
                    data=export_csv,
                    file_name=f"sales_team_analysis_{st.session_state.export_id}.csv",
                    mime="text/csv",
                )
        else:
            st.info("No sales team analysis data available for the selected filters.")
elif st.session_state.user_role == "Regional Sales Rep":
    tab_labels = ["Overview", "Regional Sales", "Top Customers", "Sales Team Analysis"]
    tabs = st.tabs(tab_labels)
    st.session_state.active_tab = min(st.session_state.active_tab, len(tab_labels) - 1)

    with tabs[0]:
        st.subheader("Regional Metrics")
        total_revenue = df_sales['revenue'].sum() if not df_sales.empty else 0
        target_achievement = (total_revenue / YEARLY_TARGET * 100) if YEARLY_TARGET > 0 else 0
        sales_count = int(df_sales['sales_count'].sum()) if not df_sales.empty else 0
        expected_sales = 500
        demo_requests = df_web[df_web['url'] == '/request-demo']['count'].sum() if not df_web.empty else 0
        expected_demos = 200
        ai_requests = df_web[df_web['url'] == '/ai-assistant']['count'].sum() if not df_web.empty else 0
        expected_ai = 150
        metrics = [
            ("Sales", "fas fa-shopping-cart", f"{sales_count:,}", sales_count / expected_sales * 100),
            ("Demo Requests", "fas fa-user-check", f"{demo_requests:,}", demo_requests / expected_demos * 100),
            ("AI Requests", "fas fa-robot", f"{ai_requests:,}", ai_requests / expected_ai * 100),
            ("Target Achievement", "fas fa-bullseye", f"{target_achievement:.1f}%", target_achievement),
        ]
        col_metrics, col_visuals = st.columns([3, 2])
        with col_metrics:
            st.markdown('<div class="visual-container">', unsafe_allow_html=True)
            st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
            for lbl, icon, val, value in metrics:
                color, status_icon = get_kpi_color(value)
                st.markdown(
                    f"""
                    <div class="metric-card {color}">
                        <div style="display: flex; justify-content: space-between;">
                            <i class="{icon}" style="font-size:0.9rem;color:var(--secondary-color)"></i>
                            <i class="fas {status_icon}" style="font-size:0.9rem;color:{color}"></i>
                        </div>
                        <div style="font-weight:600;font-size:0.7rem">{lbl}</div>
                        <div style="font-size:0.8rem;font-weight:700">{val}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(
                """
                <div class="legend-container">
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: var(--green);"></div>
                        <span>Good (≥80%) ✔</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: var(--amber);"></div>
                        <span>Average (50–80%) ⚠</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: var(--red);"></div>
                        <span>Poor (<50%) ✖</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)
        with col_visuals:
            st.markdown('<div class="visual-container">', unsafe_allow_html=True)
            st.plotly_chart(create_gauge_chart(target_achievement, "Sales Target", 100), use_container_width=True)
            st.markdown(create_progress_bar(target_achievement), unsafe_allow_html=True)
            if trends:
                df_trends = pd.DataFrame(trends)
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=df_trends["timestamp"],
                        y=df_trends["revenue"],
                        name="Revenue",
                        line=dict(color="#3b82f6"),
                    )
                )
                st.plotly_chart(style_fig(fig), use_container_width=True)
            else:
                st.info("No trend data available.")
            st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        st.subheader("Regional Sales Analysis")
        if not df_web.empty:
            dfj = df_web.copy()
            dfj["job_type"] = dfj["url"].str.strip("/").str.replace("-", " ").str.title()
            dfj["country"] = dfj["country"].apply(get_country_full_name)
            dfj["iso"] = dfj["country"].apply(country_to_iso3)

            col1, col2 = st.columns(2)
            with col1:
                bar_chart = px.bar(
                    dfj,
                    x="job_type",
                    y="count",
                    color="country",
                    barmode="group",
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                st.plotly_chart(style_fig(bar_chart), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with col2:
                pie_chart = px.pie(
                    dfj,
                    names="job_type",
                    values="count",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                st.plotly_chart(style_fig(pie_chart), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            map_chart = px.choropleth(
                dfj,
                locations="iso",
                color="count",
                hover_name="country",
                color_continuous_scale=px.colors.sequential.Blues,
            )
            st.markdown('<div class="visual-container">', unsafe_allow_html=True)
            st.plotly_chart(style_fig(map_chart), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("Export Regional Sales Data", key="export_regional"):
                export_data = dfj.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=export_data,
                    file_name=f"regional_sales_data_{st.session_state.export_id}.csv",
                    mime="text/csv",
                )
        else:
            st.info("No regional sales data available for the selected filters.")

    with tabs[2]:
        st.subheader("Top Customers")
        if top_customers:
            df_customers = pd.DataFrame(top_customers)
            df_customers["country"] = df_customers["country"].apply(get_country_full_name)
            st.markdown('<div class="visual-container">', unsafe_allow_html=True)
            st.dataframe(
                df_customers[["customer_id", "country", "sales_count", "revenue"]],
                column_config={
                    "customer_id": "Customer ID",
                    "country": "Country",
                    "sales_count": "Sales Count",
                    "revenue": st.column_config.NumberColumn("Revenue", format="$%.2f"),
                },
                use_container_width=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("Export Top Customers Data", key="export_customers"):
                export_data = df_customers.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=export_data,
                    file_name=f"top_customers_data_{st.session_state.export_id}.csv",
                    mime="text/csv",
                )
        else:
            st.info("No top customers data available for the selected filters.")

    with tabs[3]:
        st.subheader("Sales Team Analysis")
        if salesperson_comparison.get("individuals") and salesperson_comparison.get("team"):
            df_individual = pd.DataFrame(salesperson_comparison["individuals"])
            df_individual["country"] = df_individual["country"].apply(get_country_full_name)
            top_salespeople = df_individual.groupby("salesperson_name")["revenue"].sum().nlargest(5).index
            df_individual = df_individual[df_individual["salesperson_name"].isin(top_salespeople)]
            df_team = pd.DataFrame(salesperson_comparison["team"])
            
            subtab_labels = ["Team & Individual", "Statistics & Comparison"]
            st.session_state.active_subtab = subtab_labels.index(st.selectbox(
                "Select Subtab",
                subtab_labels,
                index=st.session_state.active_subtab,
                key="subtab_select_rep"
            ))

            if st.session_state.active_subtab == 0:
                st.markdown("#### Team & Individual Performance (2023-2025)")
                options = ["Team"] + sorted(df_individual["salesperson_name"].unique().tolist())
                selected = st.selectbox("Select Team or Salesperson", options, key="select_team_ind_rep")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    if selected == "Team":
                        fig = go.Figure()
                        fig.add_trace(
                            go.Scatter(
                                x=df_team["year"],
                                y=df_team["team_revenue"],
                                name="Team Revenue",
                                line=dict(color="#3b82f6"),
                            )
                        )
                        fig.add_hline(y=TEAM_YEARLY_TARGET, line_dash="dash", line_color="red", annotation_text="Team Target")
                    else:
                        df_person = df_individual[df_individual["salesperson_name"] == selected]
                        fig = go.Figure()
                        fig.add_trace(
                            go.Scatter(
                                x=df_person["year"],
                                y=df_person["revenue"],
                                name="Revenue",
                                line=dict(color="#3b82f6"),
                            )
                        )
                        fig.add_hline(y=YEARLY_TARGET, line_dash="dash", line_color="red", annotation_text="Yearly Target")
                    st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                    st.plotly_chart(style_fig(fig), use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                    st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
                    if selected == "Team":
                        total_revenue = df_team["team_revenue"].sum()
                        latest_target = df_team[df_team["year"] == df_team["year"].max()]["team_target_achieved"].iloc[0] if not df_team.empty else 0
                    else:
                        df_person = df_individual[df_individual["salesperson_name"] == selected]
                        total_revenue = df_person["revenue"].sum()
                        latest_target = df_person[df_person["year"] == df_person["year"].max()]["yearly_target_achieved"].iloc[0] if not df_person.empty else 0
                    color, status_icon = get_kpi_color(total_revenue / TEAM_YEARLY_TARGET * 100 if selected == 'Team' else total_revenue / YEARLY_TARGET * 100)
                    st.markdown(
                        f"""
                        <div class="metric-card {color}">
                            <div style="display: flex; justify-content: space-between;">
                                <i class="fas fa-dollar-sign" style="font-size:0.9rem;color:var(--secondary-color)"></i>
                                <i class="fas {status_icon}" style="font-size:0.9rem;color:{color}"></i>
                            </div>
                            <div style="font-weight:600;font-size:0.7rem">Total Revenue</div>
                            <div style="font-size:0.8rem;font-weight:700">${total_revenue:,.0f}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    color, status_icon = get_kpi_color(latest_target)
                    st.markdown(
                        f"""
                        <div class="metric-card {color}">
                            <div style="display: flex; justify-content: space-between;">
                                <i class="fas fa-bullseye" style="font-size:0.9rem;color:var(--secondary-color)"></i>
                                <i class="fas {status_icon}" style="font-size:0.9rem;color:{color}"></i>
                            </div>
                            <div style="font-weight:600;font-size:0.7rem">Target Achieved</div>
                            <div style="font-size:0.8rem;font-weight:700">{latest_target:.0f}%</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

            elif st.session_state.active_subtab == 1:
                st.markdown("#### Statistics & Comparison (2023-2025)")
                col1, col2 = st.columns([1, 1])
                with col1:
                    if sales_stats:
                        df_sales_stats = pd.DataFrame(sales_stats)
                        df_sales_stats["country"] = df_sales_stats["country"].apply(get_country_full_name)
                        fig_heatmap = px.density_heatmap(
                            df_sales_stats,
                            x="country",
                            y="product",
                            z="mean_sales_count",
                            color_continuous_scale="Blues",
                            text_auto=".1f",
                            hover_data={
                                "std_sales_count": ":,.1f",
                                "mean_revenue": ":$,.0f",
                                "std_revenue": ":$,.0f",
                                "job_type": True
                            },
                            title="Mean Sales by Country/Product",
                        )
                        st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                        st.plotly_chart(style_fig(fig_heatmap), use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                with col2:
                    fig_compare = px.bar(
                        df_individual,
                        x="salesperson_name",
                        y="revenue",
                        color="year",
                        barmode="group",
                        color_discrete_sequence=px.colors.qualitative.Pastel,
                        title="Revenue Comparison",
                    )
                    fig_compare.add_hline(y=YEARLY_TARGET, line_dash="dash", line_color="red", annotation_text="Yearly Target")
                    st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                    st.plotly_chart(style_fig(fig_compare), use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                with st.expander("View Basic Statistics"):
                    if sales_stats:
                        st.dataframe(
                            df_sales_stats[[
                                "country", "product", "job_type",
                                "mean_sales_count", "std_sales_count",
                                "mean_revenue", "std_revenue"
                            ]],
                            column_config={
                                "country": "Country",
                                "product": "Product",
                                "job_type": "Job Type",
                                "mean_sales_count": st.column_config.NumberColumn("Mean Sales", format="%.1f"),
                                "std_sales_count": st.column_config.NumberColumn("Std Sales", format="%.1f"),
                                "mean_revenue": st.column_config.NumberColumn("Mean Revenue", format="$%.0f"),
                                "std_revenue": st.column_config.NumberColumn("Std Revenue", format="$%.0f"),
                            },
                            use_container_width=True,
                        )
                st.markdown('</div>', unsafe_allow_html=True)

            if st.button("Export Sales Team Analysis Data", key="export_sales_team_regional"):
                export_data = {
                    "individuals": df_individual.to_csv(index=False),
                    "team": df_team.to_csv(index=False),
                    "sales_stats": df_sales_stats.to_csv(index=False) if sales_stats else ""
                }
                export_csv = (
                    "Individual Performance:\n" + export_data["individuals"] +
                    "\nTeam Performance:\n" + export_data["team"] +
                    "\nSales Statistics:\n" + export_data["sales_stats"]
                )
                st.download_button(
                    label="Download CSV",
                    data=export_csv,
                    file_name=f"sales_team_analysis_{st.session_state.export_id}.csv",
                    mime="text/csv",
                )
        else:
            st.info("No sales team analysis data available for the selected filters.")

elif st.session_state.user_role == "Marketing Analyst":
    tab_labels = ["Overview", "Conversion Funnel", "Web Trends", "Campaign Performance", "Promotional Correlation", "Product Metrics"]
    tabs = st.tabs(tab_labels)
    st.session_state.active_tab = min(st.session_state.active_tab, len(tab_labels) - 1)

    with tabs[0]:
        st.subheader("Marketing Metrics")
        total_visits = df_web["count"].sum() if not df_web.empty else 0
        demo_requests = df_web[df_web["url"] == "/request-demo"]["count"].sum() if not df_web.empty else 0
        ai_requests = df_web[df_web["url"] == "/ai-assistant"]["count"].sum() if not df_web.empty else 0
        lead_conversion = (demo_requests / total_visits * 100) if total_visits > 0 else 0
        ctr = (ai_requests / total_visits * 100) if total_visits > 0 else 0
        impressions = total_visits * 2 if total_visits > 0 else 0
        expected_visits = 10000
        expected_impressions = 20000
        metrics = [
            ("Website Visits", "fas fa-globe", f"{total_visits:,}", total_visits / expected_visits * 100),
            ("Lead Conversion", "fas fa-funnel-dollar", f"{lead_conversion:.1f}%", lead_conversion, 10, 5),
            ("Campaign Impressions", "fas fa-eye", f"{impressions:,}", impressions / expected_impressions * 100),
            ("Click-Through Rate", "fas fa-mouse-pointer", f"{ctr:.1f}%", ctr, 5, 2),
            ("Conversion Achievement", "fas fa-bullseye", f"{lead_conversion:.1f}%", lead_conversion, 10, 5),
        ]
        col_metrics, col_visuals = st.columns([3, 2])
        with col_metrics:
            st.markdown('<div class="visual-container">', unsafe_allow_html=True)
            st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
            for lbl, icon, val, value, *thresholds in metrics:
                color, status_icon = get_kpi_color(value, *thresholds)
                st.markdown(
                    f"""
                    <div class="metric-card {color}">
                        <div style="display: flex; justify-content: space-between;">
                            <i class="{icon}" style="font-size:0.9rem;color:var(--secondary-color)"></i>
                            <i class="fas {status_icon}" style="font-size:0.9rem;color:{color}"></i>
                        </div>
                        <div style="font-weight:600;font-size:0.7rem">{lbl}</div>
                        <div style="font-size:0.8rem;font-weight:700">{val}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(
                """
                <div class="legend-container">
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: var(--green);"></div>
                        <span>Good (≥80%) ✔</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: var(--amber);"></div>
                        <span>Average (50–80%) ⚠</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: var(--red);"></div>
                        <span>Poor (<50%) ✖</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)
        with col_visuals:
            st.markdown('<div class="visual-container">', unsafe_allow_html=True)
            st.plotly_chart(create_gauge_chart(lead_conversion, "Lead Conversion", 20), use_container_width=True)
            st.markdown(create_progress_bar(lead_conversion, 20), unsafe_allow_html=True)
            if web_trends:
                df_web_trends = pd.DataFrame(web_trends)
                fig = go.Figure()
                if 'request_demo' in df_web_trends.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df_web_trends["timestamp"],
                            y=df_web_trends["request_demo"],
                            name="Demo Requests",
                            line=dict(color="#3b82f6"),
                        )
                    )
                st.plotly_chart(style_fig(fig), use_container_width=True)
            else:
                st.info("No trend data available.")
            st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        st.subheader("Conversion Funnel")
        if funnel and any(funnel.get(k, 0) > 0 for k in ["web_visits", "demo_requests", "sales"]):
            fig = go.Figure(
                go.Funnel(
                    y=["Web Visits", "Demo Requests", "Sales"],
                    x=[
                        funnel.get("web_visits", 0),
                        funnel.get("demo_requests", 0),
                        funnel.get("sales", 0)
                    ],
                    textinfo="value+percent initial",
                    marker=dict(color=["#3b82f6", "#1e3a8a", "#60a5fa"]),
                )
            )
            st.markdown('<div class="visual-container">', unsafe_allow_html=True)
            st.plotly_chart(style_fig(fig), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("Export Funnel Data", key="export_funnel"):
                export_data = pd.DataFrame([funnel]).to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=export_data,
                    file_name=f"funnel_data_{st.session_state.export_id}.csv",
                    mime="text/csv",
                )
        else:
            st.info("No conversion funnel data available for the selected filters.")

    with tabs[2]:
        st.subheader("Web Event Trends")
        if web_trends:
            df_web_trends = pd.DataFrame(web_trends)
            fig = go.Figure()
            for url, label in [
                ("request_demo", "Request Demo"),
                ("promotional_event", "Promotional Event"),
                ("ai_assistant", "AI Assistant"),
            ]:
                if url in df_web_trends.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df_web_trends["timestamp"],
                            y=df_web_trends[url],
                            name=label,
                            stackgroup="one",
                            line=dict(width=0),
                        )
                    )
            if fig.data:
                st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                st.plotly_chart(style_fig(fig), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                if st.button("Export Web Trends Data", key="export_web_trends"):
                    export_data = df_web_trends.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=export_data,
                        file_name=f"web_trends_data_{st.session_state.export_id}.csv",
                        mime="text/csv",
                    )
            else:
                st.info("No web trends data available for the selected filters.")
        else:
            st.info("No web trends data available for the selected filters.")

    with tabs[3]:
        st.subheader("Campaign Performance")
        if funnel is not None and df_web is not None and not df_web.empty:
            df_conversion = df_web.copy()
            df_conversion["country"] = df_conversion["country"].apply(get_country_full_name)
            df_conversion["impressions"] = df_conversion["count"] * 2
            df_conversion["conversion_rate"] = df_conversion["count"] / df_conversion["impressions"] * 100
            fig = px.scatter(
                df_conversion,
                x="impressions",
                y="conversion_rate",
                color="country",
                size="count",
                hover_name="country",
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            st.markdown('<div class="visual-container">', unsafe_allow_html=True)
            st.plotly_chart(style_fig(fig), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("Export Campaign Data", key="export_campaign"):
                export_data = df_conversion.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=export_data,
                    file_name=f"campaign_data_{st.session_state.export_id}.csv",
                    mime="text/csv",
                )
        else:
            st.info("No campaign performance data available for the selected filters.")

    with tabs[4]:
        st.subheader("Promotional Event Trends with Sales")
        if web_trends and trends:
            df_web_trends = pd.DataFrame(web_trends)
            df_trends = pd.DataFrame(trends)
            if 'promotional_event' in df_web_trends.columns:
                # Prepare data: align timestamps to monthly periods
                df_promo = df_web_trends[['timestamp', 'promotional_event']].copy()
                df_promo['timestamp'] = pd.to_datetime(df_promo['timestamp']).dt.to_period('M').dt.to_timestamp()
                df_trends['timestamp'] = pd.to_datetime(df_trends['timestamp']).dt.to_period('M').dt.to_timestamp()
                df_merged = pd.merge(df_promo, df_trends, on='timestamp', how='inner')
                
                if not df_merged.empty:
                    # Create dual-axis plot
                    fig = go.Figure()
                    # Plot promotional events (left y-axis)
                    fig.add_trace(
                        go.Scatter(
                            x=df_merged['timestamp'],
                            y=df_merged['promotional_event'],
                            name='Promotional Events',
                            line=dict(color='#3b82f6'),
                        )
                    )
                    # Plot revenue (right y-axis)
                    fig.add_trace(
                        go.Scatter(
                            x=df_merged['timestamp'],
                            y=df_merged['revenue'],
                            name='Revenue',
                            line=dict(color='#1e3a8a'),
                            yaxis='y2'
                        )
                    )
                    # Update layout for dual y-axes
                    fig.update_layout(
                        xaxis=dict(
                            showticklabels=True,
                            tickfont=dict(size=8, family="Arial", color="#1f2937")
                        ),
                        yaxis=dict(
                            title=dict(
                                text='Promotional Events',
                                font=dict(size=8, family="Arial", color='#3b82f6')
                            ),
                            tickfont=dict(size=8, family="Arial", color='#3b82f6'),
                            side='left'
                        ),
                        yaxis2=dict(
                            title=dict(
                                text='Revenue ($)',
                                font=dict(size=8, family="Arial", color='#1e3a8a')
                            ),
                            tickfont=dict(size=8, family="Arial", color='#1e3a8a'),
                            side='right',
                            overlaying='y'
                        ),
                        margin=dict(t=10, b=10, r=10, l=10),
                        height=140,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Arial", size=8, color="#1f2937"),
                        legend=dict(
                            orientation="v",
                            x=1,
                            xanchor="left",
                            y=0.5,
                            yanchor="middle",
                            bgcolor="rgba(255,255,255,0.8)",
                            font=dict(size=7, family="Arial")
                        ),
                        hoverlabel=dict(bgcolor="white", font_size=8, font_family="Arial")
                    )
                    st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    if st.button("Export Promotional Trends Data", key="export_promo_trends"):
                        export_data = df_merged.to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=export_data,
                            file_name=f"promo_trends_data_{st.session_state.export_id}.csv",
                            mime="text/csv"
                        )
                else:
                    st.info("No overlapping promotional event and sales data available for the selected filters.")
            else:
                st.info("No promotional event data available for the selected filters.")
        else:
            st.info("No promotional trends or sales data available for the selected filters.")

    with tabs[5]:
        st.subheader("Product Metrics")
        if sales:
            df_sales_metrics = pd.DataFrame(sales)
            df_sales_metrics["country"] = df_sales_metrics["country"].apply(get_country_full_name)
            # Calculate YoY growth (assuming data spans multiple years)
            df_sales_metrics['year'] = pd.to_datetime(df_trends['timestamp']).dt.year if trends else 2023
            df_yoy = df_sales_metrics.groupby(['product', 'year']).agg({
                'revenue': 'sum',
                'sales_count': 'sum'
            }).reset_index()
            df_yoy = df_yoy.sort_values(['product', 'year'])
            df_yoy['revenue_growth'] = df_yoy.groupby('product')['revenue'].pct_change() * 100
            df_yoy['sales_growth'] = df_yoy.groupby('product')['sales_count'].pct_change() * 100
            df_yoy = df_yoy.dropna()

            col1, col2 = st.columns(2)
            with col1:
                # Bar chart for average revenue by product
                fig_avg = px.bar(
                    df_sales_metrics,
                    x="product",
                    y="revenue",
                    color="country",
                    barmode="group",
                    title="Average Revenue by Product",
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                st.plotly_chart(style_fig(fig_avg), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with col2:
                # Line chart for YoY revenue growth
                if not df_yoy.empty:
                    fig_yoy = px.line(
                        df_yoy,
                        x="year",
                        y="revenue_growth",
                        color="product",
                        title="YoY Revenue Growth (%)",
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                    st.plotly_chart(style_fig(fig_yoy), use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("Insufficient data for YoY growth analysis.")

            # Display metrics table
            st.markdown('<div class="visual-container">', unsafe_allow_html=True)
            with st.expander("View Product Metrics"):
                st.dataframe(
                    df_sales_metrics.groupby('product').agg({
                        'sales_count': 'sum',
                        'revenue': 'mean',
                        'profit': 'mean'
                    }).reset_index(),
                    column_config={
                        'product': 'Product',
                        'sales_count': st.column_config.NumberColumn('Total Sales', format='%d'),
                        'revenue': st.column_config.NumberColumn('Avg. Revenue', format='$%.2f'),
                        'profit': st.column_config.NumberColumn('Avg. Profit', format='$%.2f')
                    },
                    use_container_width=True
                )
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("Export Product Metrics Data", key="export_product_metrics"):
                export_data = df_sales_metrics.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=export_data,
                    file_name=f"product_metrics_data_{st.session_state.export_id}.csv",
                    mime="text/csv"
                )
        else:
            st.info("No product metrics data available for the selected filters.")
