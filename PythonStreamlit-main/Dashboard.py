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
                            tickfont=dict(size=8, family="Inter", color="#1f2937")
                        ),
                        yaxis=dict(
                            title='Promotional Events',
                            titlefont=dict(size=8, family="Inter", color='#3b82f6'),
                            tickfont=dict(size=8, family="Inter", color='#3b82f6'),
                            side='left'
                        ),
                        yaxis2=dict(
                            title='Revenue ($)',
                            titlefont=dict(size=8, family="Inter", color='#1e3a8a'),
                            tickfont=dict(size=8, family="Inter", color='#1e3a8a'),
                            side='right',
                            overlaying='y'
                        ),
                        margin=dict(t=10, b=10, r=10, l=10),
                        height=140,
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
                            font=dict(size=7)
                        ),
                        hoverlabel=dict(bgcolor="white", font_size=8, font_family="Inter")
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
