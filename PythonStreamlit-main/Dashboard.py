import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, time, timedelta
import pycountry
import uuid
import json

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
        }
        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Inter', sans-serif;
        }
        .block-container {
            padding: 0.7rem;
            max-width: 1400px;
        }
        #MainMenu, footer {visibility: hidden;}
        header {visibility: hidden;}
        section[data-testid="stSidebar"] {
            width: 280px !important;
            background-color: #ffffff;
            border-right: 1px solid #e5e7eb;
        }
        .metric-card {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05);
            padding: 0.6rem;
            background: #ffffff;
            width: 160px;
            transition: transform 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-2px);
        }
        .metrics-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 0.6rem;
            margin-bottom: 0.6rem;
            padding: 0.3rem;
        }
        .visual-container {
            border: 1px solid #e5e7eb;
            border-radius: 5px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05);
            background: #ffffff;
            padding: 0.4rem;
            margin: 0.4rem 0;
            transition: transform 0.2s;
        }
        .visual-container:hover {
            transform: scale(1.02);
        }
        .tab-pane {
            padding: 0.15rem;
            background: #ffffff;
            border-radius: 5px;
            max-height: 380px;
        }
        .table-wrapper {
            border-radius: 5px;
            overflow-x: auto;
            background: #ffffff;
            padding: 0.3rem;
            max-height: 180px;
            overflow-y: auto;
        }
        .stButton>button {
            background-color: var(--secondary-color);
            color: white;
            border: none;
            border-radius: 4px;
            padding: 0.3rem 0.6rem;
            font-size: 0.8rem;
        }
        .stButton>button:hover {
            background-color: var(--primary-color);
        }
        .plotly-chart-container {
            margin: 0.3rem 0 !important;
            padding: 0.3rem !important;
        }
        .stPlotlyChart {
            height: 180px !important;
        }
        .compact-table {
            font-size: 0.8rem;
            max-height: 180px;
            overflow-y: auto;
        }
        .stSelectbox {
            margin-bottom: 0.5rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Initialize Session State ---
if "export_id" not in st.session_state:
    st.session_state.export_id = str(uuid.uuid4())
if "user_role" not in st.session_state:
    st.session_state.user_role = "Sales Manager"
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0
if "active_subtab" not in st.session_state:
    st.session_state.active_subtab = 0

# --- API Configuration ---
api_url = "http://localhost:8000/api"
PRODUCTS = ["AI Assistant", "Smart Prototype", "Analytics Suite"]
YEARLY_TARGET = 120000  # Per salesperson
TEAM_YEARLY_TARGET = YEARLY_TARGET * 5  # For 5 salespeople

# --- Data Fetch Utility ---
@st.cache_data(ttl=300)
def get_data(endpoint, params=None):
    with st.spinner(f"Fetching {endpoint} data..."):
        try:
            r = requests.get(f"{api_url}/{endpoint}", params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            if not data:
                st.info(f"No data available for {endpoint} with the selected filters.")
                return []
            return data
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                st.warning("Invalid API parameters. Please check your filters.")
                return []
            st.error(f"API Error: {e}")
            return []
        except Exception as e:
            st.error(f"Failed to fetch data: {e}")
            return []

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

def style_fig(fig):
    fig.update_layout(
        xaxis=dict(showticklabels=True),
        margin=dict(t=10, b=10, r=10, l=10),
        height=180,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=9, color="#1f2937"),
        legend=dict(
            title="",
            orientation="v",
            x=1,
            xanchor="left",
            y=0.5,
            yanchor="middle",
            bgcolor="rgba(255,255,255,0.8)",
            font=dict(size=8),
        ),
        hoverlabel=dict(bgcolor="white", font_size=9, font_family="Inter"),
    )
    return fig

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
    start_iso = datetime.combine(sd, time.min).isoformat()
    end_iso = datetime.combine(ed, time.max).isoformat()

    codes = get_data("countries") or []
    names = [get_country_full_name(c) for c in codes]
    sel_countries = st.multiselect("Countries", names, default=names[:3])
    sel_products = st.multiselect("Products", PRODUCTS, default=PRODUCTS[:3])

    params = {
        "country": [c for c in codes if get_country_full_name(c) in sel_countries],
        "start_date": start_iso,
        "end_date": end_iso,
    }

# --- Data Loading ---
sales = get_data("sales", params) or []
df_sales = pd.DataFrame(sales)
if not df_sales.empty:
    df_sales = df_sales[df_sales["product"].isin(sel_products)]

web = get_data("web_events", params) or []
df_web = pd.DataFrame(web)

stats = get_data("stats", params) or []
funnel = get_data("conversion_funnel", params) or {}
trends = get_data("trends", params) or []
sales_by_channel = get_data("sales_by_channel", params) or []
profit_margin = get_data("profit_margin", params) or []
top_customers = get_data("top_customers", params) or []
web_trends = get_data("web_trends", params) or []
salesperson_performance = get_data("salesperson_performance", params) or []
salesperson_comparison = get_data("salesperson_comparison", params) or {}
sales_stats = get_data("sales_stats", params) or []

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
           - For Sales Manager and Regional Sales Rep roles, the "Sales Team Analysis" tab includes subtabs ("Team & Individual" and "Statistics & Comparison") for deeper insights.
           - Interact with charts by hovering for details or selecting options (e.g., team or salesperson) where available.

        4. **Export Data**:
           - In tabs with exportable data (e.g., Trends, Sales by Channel), click the "Export" button to generate a CSV file.
           - Use the "Download CSV" button that appears to save the data locally.
           - Each export is uniquely named using a session ID to avoid overwriting files.

        5. **Interpret Visuals**:
           - **Metric Cards**: Display key metrics like sales, revenue, or conversion rates.
           - **Charts**: Include bar, line, heatmap, and funnel charts to visualize trends, comparisons, and distributions.
           - **Tables**: Provide detailed data, often expandable for basic statistics.

        6. **Troubleshooting**:
           - If data is missing, check your filters (e.g., date range or selected countries) and ensure they align with available data.
           - Error messages will appear if API requests fail or filters are invalid.

        For further assistance, contact the dashboard administrator.
        """
    )

if st.session_state.user_role == "Sales Manager":
    tab_labels = ["Overview", "Trends", "Sales Channels", "Profitability", "Sales Team Analysis"]
    tabs = st.tabs(tab_labels)
    st.session_state.active_tab = min(st.session_state.active_tab, len(tab_labels) - 1)

    with tabs[0]:
        st.subheader("Key Metrics")
        col1, col2, col3, col4 = st.columns(4)
        metrics = [
            (
                "Sales",
                "fas fa-shopping-cart",
                f"{int(df_sales['sales_count'].sum()):,}" if not df_sales.empty else "0",
            ),
            (
                "Revenue",
                "fas fa-dollar-sign",
                f"${df_sales['revenue'].sum():,.0f}" if not df_sales.empty else "$0",
            ),
            (
                "Profit",
                "fas fa-chart-line",
                f"${df_sales['profit'].sum():,.0f}" if not df_sales.empty else "$0",
            ),
            (
                "Conversion Rate",
                "fas fa-percentage",
                f"{funnel.get('conversion_rate', 0):.1f}%" if funnel else "0%",
            ),
        ]
        st.markdown('<div class="visual-container">', unsafe_allow_html=True)
        for col, (lbl, icon, val) in zip([col1, col2, col3, col4], metrics):
            with col:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <i class="{icon}" style="font-size:1rem;color:var(--secondary-color)"></i>
                        <div style="margin-top:0.3rem;font-weight:600;font-size:0.8rem">{lbl}</div>
                        <div style="font-size:0.9rem;font-weight:700">{val}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
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

    with tabs[4]:
        st.subheader("Sales Team Analysis")
        if salesperson_comparison.get("individuals") and salesperson_comparison.get("team"):
            # Filter to top 5 salespeople by total revenue
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
                # Dropdown for selection
                options = ["Team"] + sorted(df_individual["salesperson_name"].unique().tolist())
                selected = st.selectbox("Select Team or Salesperson", options, key="select_team_ind_mgr")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    if selected == "Team":
                        # Team Line Chart
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
                        # Individual Line Chart
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
                    # Metric Cards
                    st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                    st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
                    if selected == "Team":
                        total_revenue = df_team["team_revenue"].sum()
                        latest_target = df_team[df_team["year"] == df_team["year"].max()]["team_target_achieved"].iloc[0] if not df_team.empty else 0
                    else:
                        df_person = df_individual[df_individual["salesperson_name"] == selected]
                        total_revenue = df_person["revenue"].sum()
                        latest_target = df_person[df_person["year"] == df_person["year"].max()]["yearly_target_achieved"].iloc[0] if not df_person.empty else 0
                    st.markdown(
                        f"""
                        <div class="metric-card">
                            <i class="fas fa-dollar-sign" style="font-size:1rem;color:var(--secondary-color)"></i>
                            <div style="margin-top:0.3rem;font-weight:600;font-size:0.8rem">Total Revenue</div>
                            <div style="font-size:0.9rem;font-weight:700">${total_revenue:,.0f}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"""
                        <div class="metric-card">
                            <i class="fas fa-bullseye" style="font-size:1rem;color:var(--secondary-color)"></i>
                            <div style="margin-top:0.3rem;font-weight:600;font-size:0.8rem">Target Achieved</div>
                            <div style="font-size:0.9rem;font-weight:700">{latest_target:.0f}%</div>
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
                    # Heatmap for Basic Stats
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
                    # Comparison Bar Chart
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
                
                # Basic Stats Table in Expander
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

            # Export Data
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
        col1, col2, col3 = st.columns(3)
        sales_count = f"{int(df_sales['sales_count'].sum()):,}" if not df_sales.empty else "0"
        demo_requests = f"{df_web[df_web['url']=='/request-demo']['count'].sum():,}" if not df_web.empty else "0"
        ai_requests = f"{df_web[df_web['url']=='/ai-assistant']['count'].sum():,}" if not df_web.empty else "0"
        metrics = [
            ("Sales", "fas fa-shopping-cart", sales_count),
            ("Demo Requests", "fas fa-user-check", demo_requests),
            ("AI Requests", "fas fa-robot", ai_requests),
        ]
        st.markdown('<div class="visual-container">', unsafe_allow_html=True)
        for col, (lbl, icon, val) in zip([col1, col2, col3], metrics):
            with col:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <i class="{icon}" style="font-size:1rem;color:var(--secondary-color)"></i>
                        <div style="margin-top:0.3rem;font-weight:600;font-size:0.8rem">{lbl}</div>
                        <div style="font-size:0.9rem;font-weight:700">{val}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        st.subheader("Regional Sales Analysis")
        if not df_web.empty:
            dfj = df_web.copy()
            dfj["job_type"] = (
                dfj["url"].str.strip("/").str.replace("-", " ").str.title()
            )
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
            df_customers["country"] = df_customers["country"].apply(
                get_country_full_name
            )
            st.markdown('<div class="visual-container">', unsafe_allow_html=True)
            st.dataframe(
                df_customers[["customer_id", "country", "sales_count", "revenue"]],
                column_config={
                    "customer_id": "Customer ID",
                    "country": "Country",
                    "sales_count": "Sales Count",
                    "revenue": st.column_config.NumberColumn(
                        "Revenue", format="$%.2f"
                    ),
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
            # Filter to top 5 salespeople by total revenue
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
                # Dropdown for selection
                options = ["Team"] + sorted(df_individual["salesperson_name"].unique().tolist())
                selected = st.selectbox("Select Team or Salesperson", options, key="select_team_ind_rep")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    if selected == "Team":
                        # Team Line Chart
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
                        # Individual Line Chart
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
                    # Metric Cards
                    st.markdown('<div class="visual-container">', unsafe_allow_html=True)
                    st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
                    if selected == "Team":
                        total_revenue = df_team["team_revenue"].sum()
                        latest_target = df_team[df_team["year"] == df_team["year"].max()]["team_target_achieved"].iloc[0] if not df_team.empty else 0
                    else:
                        df_person = df_individual[df_individual["salesperson_name"] == selected]
                        total_revenue = df_person["revenue"].sum()
                        latest_target = df_person[df_person["year"] == df_person["year"].max()]["yearly_target_achieved"].iloc[0] if not df_person.empty else 0
                    st.markdown(
                        f"""
                        <div class="metric-card">
                            <i class="fas fa-dollar-sign" style="font-size:1rem;color:var(--secondary-color)"></i>
                            <div style="margin-top:0.3rem;font-weight:600;font-size:0.8rem">Total Revenue</div>
                            <div style="font-size:0.9rem;font-weight:700">${total_revenue:,.0f}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"""
                        <div class="metric-card">
                            <i class="fas fa-bullseye" style="font-size:1rem;color:var(--secondary-color)"></i>
                            <div style="margin-top:0.3rem;font-weight:600;font-size:0.8rem">Target Achieved</div>
                            <div style="font-size:0.9rem;font-weight:700">{latest_target:.0f}%</div>
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
                    # Heatmap for Basic Stats
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
                    # Comparison Bar Chart
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
                
                # Basic Stats Table in Expander
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

            # Export Data
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
    tab_labels = ["Overview", "Conversion Funnel", "Web Trends", "Campaign Performance"]
    tabs = st.tabs(tab_labels)
    st.session_state.active_tab = min(st.session_state.active_tab, len(tab_labels) - 1)

    with tabs[0]:
        st.subheader("Marketing Metrics")
        total_visits = df_web["count"].sum() if not df_web.empty else 0
        demo_requests = (
            df_web[df_web["url"] == "/request-demo"]["count"].sum()
            if not df_web.empty
            else 0
        )
        ai_requests = (
            df_web[df_web["url"] == "/ai-assistant"]["count"].sum()
            if not df_web.empty
            else 0
        )
        lead_conversion = (
            (demo_requests / total_visits * 100) if total_visits > 0 else 0
        )
        ctr = (ai_requests / total_visits * 100) if total_visits > 0 else 0
        impressions = total_visits * 2 if total_visits > 0 else 0

        metrics = [
            ("Website Visits", "fas fa-globe", f"{total_visits:,}"),
            ("Lead Conversion", "fas fa-funnel-dollar", f"{lead_conversion:.1f}%"),
            ("Campaign Impressions", "fas fa-eye", f"{impressions:,}"),
            ("Click-Through Rate", "fas fa-mouse-pointer", f"{ctr:.1f}%"),
        ]
        st.markdown('<div class="visual-container">', unsafe_allow_html=True)
        st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
        for lbl, icon, val in metrics:
            st.markdown(
                f"""
                <div class="metric-card">
                    <i class="{icon}" style="font-size:1rem;color:var(--secondary-color)"></i>
                    <div style="margin-top:0.3rem;font-weight:600;font-size:0.8rem">{lbl}</div>
                    <div style="font-size:0.9rem;font-weight:700">{val}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[1]:
        st.subheader("Conversion Funnel")
        if funnel and any(
            funnel.get(k, 0) > 0 for k in ["web_visits", "demo_requests", "sales"]
        ):
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
            df_conversion["country"] = df_conversion["country"].apply(
                get_country_full_name
            )
            df_conversion["impressions"] = df_conversion["count"] * 2
            df_conversion["conversion_rate"] = (
                df_conversion["count"] / df_conversion["impressions"] * 100
            )
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
            st.info(
                "No campaign performance data available for the selected filters."
            )

# --- Sidebar Footer ---
with st.sidebar:
    st.markdown("---")
    st.markdown(
        """
        <div style='padding: 0.7rem;'>
            <small>AI Solutions Dashboard v3.3<br>
            Built with Streamlit & Plotly<br>
            Data updated: {}</small>
        </div>
        """.format(
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ),
        unsafe_allow_html=True,
    )