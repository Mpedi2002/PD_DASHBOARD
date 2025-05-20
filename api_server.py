from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
import pandas as pd
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
DATA_CSV_PATH = "combined_data.csv"

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load and preprocess data once on startup
df: pd.DataFrame

@app.on_event("startup")
def load_data():
    global df
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
        logger.info("Data loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load data: {str(e)}")

# Utility: filter by date range and countries
def filter_df(
    data: pd.DataFrame,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    countries: Optional[List[str]],
    product: Optional[str] = None
) -> pd.DataFrame:
    try:
        filtered = data.copy()
        if start_date:
            start_date = pd.to_datetime(start_date, errors='coerce')
            if pd.isna(start_date):
                raise ValueError("Invalid start_date format")
            filtered = filtered[filtered.index >= start_date]
        if end_date:
            end_date = pd.to_datetime(end_date, errors='coerce')
            if pd.isna(end_date):
                raise ValueError("Invalid end_date format")
            filtered = filtered[filtered.index <= end_date]
        if countries:
            filtered = filtered[filtered['country'].isin(countries)]
        if product:
            filtered = filtered[filtered['product'] == product]
        return filtered
    except Exception as e:
        logger.error(f"Error filtering data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error filtering data: {str(e)}")

@app.get("/api/countries")
def get_countries() -> List[str]:
    try:
        return sorted(df['country'].dropna().unique().tolist())
    except Exception as e:
        logger.error(f"Error fetching countries: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching countries: {str(e)}")

@app.get("/api/sales")
def get_sales(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    country: Optional[List[str]] = Query(None)
):
    try:
        sales_df = df[df['event_type'] == 'sale']
        filtered = filter_df(sales_df, start_date, end_date, country)
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
    except Exception as e:
        logger.error(f"Error in sales endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing sales data: {str(e)}")

@app.get("/api/web_events")
def get_web_events(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    country: Optional[List[str]] = Query(None)
):
    try:
        web_df = df[df['event_type'] == 'web']
        filtered = filter_df(web_df, start_date, end_date, country)
        if filtered.empty:
            return []
        target_urls = ['/request-demo', '/promotional-event', '/ai-assistant']
        events = filtered[filtered['url'].isin(target_urls)]
        grouped = events.reset_index().groupby(['country', 'url']).size().reset_index(name='count')
        return grouped.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error in web_events endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing web events: {str(e)}")

@app.get("/api/metrics")
def get_metrics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    country: Optional[List[str]] = Query(None)
):
    try:
        filtered = filter_df(df, start_date, end_date, country)
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
    except Exception as e:
        logger.error(f"Error in metrics endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing metrics: {str(e)}")

@app.get("/api/stats")
def get_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    country: Optional[List[str]] = Query(None)
):
    try:
        filtered = filter_df(df, start_date, end_date, country)
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
    except Exception as e:
        logger.error(f"Error in stats endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing stats: {str(e)}")

@app.get("/api/software_sales")
def get_software_sales(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    country: Optional[List[str]] = Query(None)
):
    try:
        products = ["AI Assistant", "Smart Prototype", "Analytics Suite"]
        sales_df = df[(df['event_type'] == 'sale') & df['product'].isin(products)]
        filtered = filter_df(sales_df, start_date, end_date, country)
        if filtered.empty:
            return {"software_sales_count": 0, "software_revenue": 0.0}
        return {
            "software_sales_count": int(filtered.shape[0]),
            "software_revenue": float(filtered['revenue'].sum())
        }
    except Exception as e:
        logger.error(f"Error in software_sales endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing software sales: {str(e)}")

@app.get("/api/conversion_funnel")
def get_conversion_funnel(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    country: Optional[List[str]] = Query(None)
):
    try:
        filtered = filter_df(df, start_date, end_date, country)
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
    except Exception as e:
        logger.error(f"Error in conversion_funnel endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing conversion funnel: {str(e)}")

@app.get("/api/trends")
def get_trends(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    country: Optional[List[str]] = Query(None)
):
    try:
        sales_df = df[df['event_type'] == 'sale']
        filtered = filter_df(sales_df, start_date, end_date, country)
        if filtered.empty:
            logger.info("No sales data found for the specified filters")
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
    except Exception as e:
        logger.error(f"Error in trends endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing trends: {str(e)}")

@app.get("/api/sales_by_channel")
def get_sales_by_channel(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    country: Optional[List[str]] = Query(None)
):
    try:
        sales_df = df[df['event_type'] == 'sale']
        filtered = filter_df(sales_df, start_date, end_date, country)
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
    except Exception as e:
        logger.error(f"Error in sales_by_channel endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing sales by channel: {str(e)}")

@app.get("/api/profit_margin")
def get_profit_margin(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    country: Optional[List[str]] = Query(None)
):
    try:
        sales_df = df[df['event_type'] == 'sale']
        filtered = filter_df(sales_df, start_date, end_date, country)
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
    except Exception as e:
        logger.error(f"Error in profit_margin endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing profit margin: {str(e)}")

@app.get("/api/top_customers")
def get_top_customers(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    country: Optional[List[str]] = Query(None)
):
    try:
        sales_df = df[df['event_type'] == 'sale']
        filtered = filter_df(sales_df, start_date, end_date, country)
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
    except Exception as e:
        logger.error(f"Error in top_customers endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing top customers: {str(e)}")

@app.get("/api/web_trends")
def get_web_trends(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    country: Optional[List[str]] = Query(None)
):
    try:
        web_df = df[df['event_type'] == 'web']
        filtered = filter_df(web_df, start_date, end_date, country)
        if filtered.empty:
            logger.info("No web events found for the specified filters")
            return []
        target_urls = ['/request-demo', '/promotional-event', '/ai-assistant']
        events = filtered[filtered['url'].isin(target_urls)]
        if events.empty:
            logger.info("No target web events found for the specified filters")
            return []
        # Resample and create a standardized output
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
        # Ensure all target URLs are present
        for url in target_urls:
            col_name = url
            if col_name not in grouped.columns:
                grouped[col_name] = 0
        # Standardize column names
        grouped = grouped.rename(columns={
            '/request-demo': 'request_demo',
            '/promotional-event': 'promotional_event',
            '/ai-assistant': 'ai_assistant'
        })
        return grouped.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error in web_trends endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing web trends: {str(e)}")

@app.get("/api/sales_stats")
def get_sales_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    country: Optional[List[str]] = Query(None)
):
    try:
        sales_df = df[df['event_type'] == 'sale'].copy()
        filtered = filter_df(sales_df, start_date, end_date, country)
        if filtered.empty:
            logger.info("No sales data found for the specified filters in sales_stats")
            return []
        # Ensure job_type exists and handle missing values
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
    except Exception as e:
        logger.error(f"Error in sales_stats endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing sales stats: {str(e)}")

@app.get("/api/salesperson_performance")
def get_salesperson_performance(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    country: Optional[List[str]] = Query(None)
):
    try:
        sales_df = df[df['event_type'] == 'sale']
        filtered = filter_df(sales_df, start_date, end_date, country)
        if filtered.empty:
            return []
        # Define targets
        YEARLY_TARGET = 120000  # $120,000 per salesperson per year
        MONTHLY_TARGET = YEARLY_TARGET / 12  # Approx $10,000 per month
        # Aggregate by salesperson
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
        # Calculate yearly target achievement
        grouped['yearly_target_achieved'] = (grouped['revenue'] / YEARLY_TARGET * 100).round(2)
        # Calculate monthly statistics
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
        # Compute mean and std for monthly sales
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
        # Merge monthly data (latest month for target, stats for mean/std)
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
    except Exception as e:
        logger.error(f"Error in salesperson_performance endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing salesperson performance: {str(e)}")

@app.get("/api/salesperson_comparison")
def get_salesperson_comparison(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    country: Optional[List[str]] = Query(None)
):
    try:
        sales_df = df[df['event_type'] == 'sale']
        filtered = filter_df(sales_df, start_date, end_date, country)
        if filtered.empty:
            return {"individuals": [], "team": [], "team_stats": []}
        # Define targets
        YEARLY_TARGET = 120000  # $120,000 per salesperson per year
        TEAM_YEARLY_TARGET = YEARLY_TARGET * 10  # 10 salespersons
        # Group by year and salesperson
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
        # Team performance
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
        # Team statistics (mean and std per year)
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
    except Exception as e:
        logger.error(f"Error in salesperson_comparison endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing salesperson comparison: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)