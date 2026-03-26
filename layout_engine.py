import html

import pandas as pd
import streamlit as st


def _safe_text(value, fallback="N/A"):
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _format_metric(value):
    if value is None:
        return "N/A"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _safe_text(value)
    if abs(number) >= 1000:
        return f"{number:,.0f}"
    return f"{number:,.2f}"


def _find_numeric_column(df, keywords):
    numeric_cols = list(df.select_dtypes(include="number").columns)
    lowered = {str(col).lower(): col for col in numeric_cols}
    for keyword in keywords:
        for name, original in lowered.items():
            if keyword in name:
                return original
    return None


def _estimate_profit_series(df):
    profit_col = _find_numeric_column(df, ["profit"])
    if profit_col:
        return df[profit_col].dropna(), profit_col
    sales_col = _find_numeric_column(df, ["revenue", "sales", "income", "amount"])
    cost_col = _find_numeric_column(df, ["cost", "expense", "spend", "cogs"])
    if sales_col and cost_col:
        return (df[sales_col] - df[cost_col]).dropna(), f"{sales_col}_minus_{cost_col}"
    return pd.Series(dtype=float), None


def _sales_growth(series):
    clean = pd.Series(series).dropna().reset_index(drop=True)
    if len(clean) < 2:
        return None
    first = float(clean.iloc[0])
    last = float(clean.iloc[-1])
    if abs(first) < 1e-9:
        return None
    return ((last - first) / abs(first)) * 100.0


def _sparkline_svg(values, line_color, fill_color=None):
    clean = [float(v) for v in pd.Series(values).dropna().tolist()]
    if len(clean) < 2:
        return ""
    width = 220
    height = 62
    padding = 6
    min_val = min(clean)
    max_val = max(clean)
    spread = max(max_val - min_val, 1e-9)
    points = []
    for idx, value in enumerate(clean):
        x = padding + (idx / max(len(clean) - 1, 1)) * (width - padding * 2)
        normalized = (value - min_val) / spread
        y = height - padding - normalized * (height - padding * 2)
        points.append((x, y))
    line_points = " ".join([f"{x:.1f},{y:.1f}" for x, y in points])
    svg = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="72" preserveAspectRatio="none">'
    ]
    if fill_color:
        area_points = f"{padding},{height-padding} " + line_points + f" {width-padding},{height-padding}"
        svg.append(
            f'<polygon points="{area_points}" fill="{fill_color}" opacity="0.28"></polygon>'
        )
    svg.append(
        f'<polyline points="{line_points}" fill="none" stroke="{line_color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></polyline>'
    )
    svg.append("</svg>")
    return "".join(svg)


def _resolve_dashboard_metrics(df):
    numeric_cols = list(df.select_dtypes(include="number").columns)
    sales_col = _find_numeric_column(df, ["revenue", "sales", "income", "amount"])
    orders_col = _find_numeric_column(df, ["orders", "order", "transaction", "qty", "quantity"])
    profit_series, _profit_name = _estimate_profit_series(df)

    if sales_col is None and numeric_cols:
        sales_col = numeric_cols[0]
    sales_series = df[sales_col].dropna() if sales_col else pd.Series(dtype=float)
    orders_series = df[orders_col].dropna() if orders_col else pd.Series(dtype=float)
    if orders_col is None and len(df.index) > 0:
        orders_total = len(df.index)
    else:
        orders_total = orders_series.sum() if not orders_series.empty else None

    return {
        "sales_total": sales_series.sum() if not sales_series.empty else None,
        "orders_total": orders_total,
        "profit_total": profit_series.sum() if not profit_series.empty else None,
        "profit_series": profit_series,
        "sales_growth": _sales_growth(sales_series),
        "sales_series": sales_series,
    }


def _filter_summary(schema):
    top_columns = schema.get("top_columns", [])[:3]
    items = []
    for item in top_columns:
        items.append(
            (
                item["name"].replace("_", " ").title(),
                f'{item["dtype"]} | {item["non_null_pct"]:.1f}% filled',
            )
        )
    return items


def _translated_lines(lines, bilingual_list, language_code, language_name):
    if not lines:
        return []
    return bilingual_list(lines, language_code, language_name)


def _panel_header(title):
    return f"""
        <div style="
            background: linear-gradient(180deg, rgba(30,41,59,0.98) 0%, rgba(15,23,42,0.98) 100%);
            border: 1px solid rgba(148,163,184,0.18);
            border-radius: 18px;
            box-shadow: 0 16px 38px rgba(2,6,23,0.34);
            padding: 18px 18px 8px 18px;
            margin-bottom: 12px;
        ">
            <div style="font-size:1.1rem; font-weight:800; color:#f8fafc;">{html.escape(title)}</div>
        </div>
    """


def _prepare_panel_chart(fig, style_chart, output_profile, height):
    styled = style_chart(fig, output_profile)
    styled.update_layout(
        title=None,
        height=height,
        paper_bgcolor="rgba(15,23,42,0.95)",
        plot_bgcolor="rgba(15,23,42,0.95)",
        font=dict(color="#e2e8f0", size=11),
        margin=dict(t=20, r=18, b=30, l=18),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    styled.update_xaxes(automargin=True, tickangle=0)
    styled.update_yaxes(automargin=True)
    return styled


def _render_metric_card(title, value, subtitle="", accent_text="", accent_color="#95e06c"):
    accent_html = (
        f'<span style="color:{accent_color}; font-weight:800; margin-left:10px; font-size:0.92em;">{html.escape(accent_text)}</span>'
        if accent_text
        else ""
    )
    subtitle_html = (
        f'<div style="color:#93c5fd; font-size:0.82rem; margin-top:10px;">{html.escape(subtitle)}</div>'
        if subtitle
        else ""
    )
    return f"""
        <div style="
            background: linear-gradient(180deg, rgba(17,24,39,0.98) 0%, rgba(30,41,59,0.96) 100%);
            border: 1px solid rgba(148,163,184,0.20);
            border-radius: 18px;
            box-shadow: 0 18px 40px rgba(2,6,23,0.36);
            padding: 18px 18px 14px 18px;
            min-height: 128px;
        ">
            <div style="color:#e2e8f0; font-size:0.95rem; font-weight:700;">{html.escape(title)}</div>
            <div style="color:#f8fafc; font-size:2.25rem; font-weight:800; margin-top:12px;">{html.escape(value)}{accent_html}</div>
            {subtitle_html}
        </div>
    """


def _render_spark_card(title, value, sparkline_html, accent_text):
    return f"""
        <div style="
            background: linear-gradient(180deg, rgba(17,24,39,0.98) 0%, rgba(30,41,59,0.96) 100%);
            border: 1px solid rgba(148,163,184,0.20);
            border-radius: 18px;
            box-shadow: 0 18px 40px rgba(2,6,23,0.36);
            padding: 18px 18px 10px 18px;
            min-height: 128px;
        ">
            <div style="color:#e2e8f0; font-size:0.95rem; font-weight:700;">{html.escape(title)}</div>
            <div style="color:#f8fafc; font-size:2.05rem; font-weight:800; margin-top:10px;">{html.escape(value)}</div>
            <div style="color:#93c5fd; font-size:0.82rem; margin-top:4px;">{html.escape(accent_text)}</div>
            <div style="margin-top:8px;">{sparkline_html}</div>
        </div>
    """


def render_sales_architecture_dashboard(
    dashboard_source,
    charts,
    output_profile,
    output_schema,
    output_filter_config,
    chart_explanations,
    chart_summaries,
    strategic_insights,
    language_code,
    language_name,
    bilingual_list,
    bilingual_text,
    style_chart,
    render_download_actions,
):
    palette = {
        "line": "#72c6ff",
        "accent": "#4f8cff",
        "positive": "#95e06c",
        "surface_top": "rgba(17,24,39,0.96)",
        "surface_bottom": "rgba(30,41,59,0.94)",
        "panel_border": "rgba(148,163,184,0.20)",
        "panel_shadow": "0 18px 40px rgba(2,6,23,0.36)",
    }
    translated_chart_summaries = _translated_lines(
        chart_summaries, bilingual_list, language_code, language_name
    )
    translated_insights = _translated_lines(
        strategic_insights, bilingual_list, language_code, language_name
    )
    metrics = _resolve_dashboard_metrics(dashboard_source)

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(180deg, rgba(30,41,59,0.98) 0%, rgba(30,41,59,0.90) 100%);
            border: 1px solid rgba(148,163,184,0.16);
            border-radius: 18px;
            box-shadow: 0 20px 52px rgba(2,6,23,0.42);
            padding: 18px 28px 16px 28px;
            margin-bottom: 22px;
        ">
            <div style="display:flex; align-items:center; justify-content:center; gap:14px;">
                <div style="font-size:2.1rem;">📊</div>
                <div>
                    <div style="font-size:2.35rem; font-weight:800; color:#f8fafc; text-shadow:0 0 22px rgba(148,197,255,0.18);">Sales Analytics Dashboard</div>
                    <div style="font-size:0.95rem; color:#cbd5e1; text-align:center;">Structured executive architecture inspired by enterprise BI layouts. Profile: {_safe_text(output_profile)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(5)
    metric_cols[0].markdown(
        _render_metric_card(
            "Total Sales",
            f"${_format_metric(metrics['sales_total'])}" if metrics["sales_total"] is not None else "N/A",
            subtitle="Overall sales value",
            accent_text=(f"{metrics['sales_growth']:.1f}%" if metrics["sales_growth"] is not None else ""),
            accent_color=palette["positive"] if (metrics["sales_growth"] or 0) >= 0 else "#f87171",
        ),
        unsafe_allow_html=True,
    )
    metric_cols[1].markdown(
        _render_metric_card(
            "Total Orders",
            _format_metric(metrics["orders_total"]),
            subtitle="Order volume",
        ),
        unsafe_allow_html=True,
    )
    metric_cols[2].markdown(
        _render_metric_card(
            "Total Profit",
            f"${_format_metric(metrics['profit_total'])}" if metrics["profit_total"] is not None else "N/A",
            subtitle="Net estimated profit",
        ),
        unsafe_allow_html=True,
    )
    metric_cols[3].markdown(
        _render_spark_card(
            "Total Profit",
            f"${_format_metric(metrics['profit_total'])}" if metrics["profit_total"] is not None else "N/A",
            _sparkline_svg(metrics["profit_series"], "#9ae6b4", "rgba(154,230,180,0.80)")
            or '<div style="color:#93c5fd; padding-top:18px;">Profit graph unavailable</div>',
            "Profit graph",
        ),
        unsafe_allow_html=True,
    )
    metric_cols[4].markdown(
        _render_spark_card(
            "Sales Growth",
            f"{metrics['sales_growth']:.1f}%" if metrics["sales_growth"] is not None else "N/A",
            _sparkline_svg(metrics["sales_series"], "#72c6ff", "rgba(114,198,255,0.65)")
            or '<div style="color:#93c5fd; padding-top:18px;">Growth graph unavailable</div>',
            "Growth signal",
        ),
        unsafe_allow_html=True,
    )

    outer_left, outer_center, outer_right = st.columns([1.15, 2.4, 1.8], gap="large")

    with outer_left:
        st.markdown(_panel_header("Filters"), unsafe_allow_html=True)
        output_filter_config = output_filter_config or {}
        st.selectbox(
            "Select Date Range",
            options=output_filter_config.get("date_options", ["All Dates"]),
            key="output_filter_date_range",
            disabled=not output_filter_config.get("date_column"),
        )
        st.selectbox(
            "Region",
            options=output_filter_config.get("region_options", ["All Regions"]),
            key="output_filter_region",
            disabled=not output_filter_config.get("region_column"),
        )
        st.selectbox(
            "Product Category",
            options=output_filter_config.get("product_options", ["All Categories"]),
            key="output_filter_product",
            disabled=not output_filter_config.get("product_column"),
        )
        for name, detail in _filter_summary(output_schema):
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(180deg, rgba(30,41,59,0.98) 0%, rgba(15,23,42,0.98) 100%);
                    border: 1px solid rgba(148,163,184,0.18);
                    border-radius: 14px;
                    padding: 12px 14px;
                    margin-top: 10px;
                ">
                    <div style="font-size:0.85rem; color:#93c5fd; font-weight:700;">{html.escape(name)}</div>
                    <div style="font-size:1rem; color:#f8fafc; font-weight:700; margin-top:4px;">{html.escape(detail)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
                border-radius: 14px;
                padding: 14px 16px;
                margin-top: 14px;
                color:#eff6ff;
                font-weight:800;
                text-align:center;
                box-shadow: 0 10px 24px rgba(37,99,235,0.30);
            ">
                Apply Filters
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Filters apply to KPI cards, charts, and the table.")

    with outer_center:
        st.markdown(_panel_header("Sales Trend"), unsafe_allow_html=True)
        if charts.get("line") is not None:
            styled_line = _prepare_panel_chart(
                charts["line"], style_chart, output_profile, height=320
            )
            styled_line.update_traces(line=dict(color=palette["line"], width=3))
            st.plotly_chart(styled_line, use_container_width=True)
        else:
            st.info("Sales trend chart not available.")

    with outer_right:
        st.markdown(_panel_header("Sales by Region"), unsafe_allow_html=True)
        if charts.get("bar") is not None:
            styled_bar = _prepare_panel_chart(
                charts["bar"], style_chart, output_profile, height=320
            )
            st.plotly_chart(styled_bar, use_container_width=True)
        else:
            st.info("Sales by region chart not available.")

    lower_left, lower_right = st.columns([1.35, 1.65], gap="large")

    with lower_left:
        st.markdown(_panel_header("Top Products"), unsafe_allow_html=True)
        if charts.get("pie") is not None:
            styled_pie = _prepare_panel_chart(
                charts["pie"], style_chart, output_profile, height=290
            )
            st.plotly_chart(styled_pie, use_container_width=True)
        else:
            st.info("Top products chart not available.")

    with lower_right:
        st.markdown(_panel_header("Detailed Sales Data"), unsafe_allow_html=True)
        preview = dashboard_source.head(6).copy()
        st.dataframe(preview, use_container_width=True, hide_index=True)

    insight_col, summary_col = st.columns([1.7, 1.3], gap="large")
    with insight_col:
        st.markdown(_panel_header("AI Insights"), unsafe_allow_html=True)
        if translated_insights:
            for item in translated_insights[:5]:
                st.markdown(f"- {item}")
        else:
            st.write("Insights are unavailable right now.")

    with summary_col:
        st.markdown(_panel_header("AI Summary"), unsafe_allow_html=True)
        if translated_chart_summaries:
            for item in translated_chart_summaries[:4]:
                st.markdown(f"- {item}")
        else:
            st.write(
                bilingual_text(
                    "Summary is unavailable right now.",
                    language_code,
                    language_name,
                )
            )

    st.markdown(_panel_header("Download"), unsafe_allow_html=True)
    render_download_actions(dashboard_source, charts, "sales_architecture")
