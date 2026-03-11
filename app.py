import html
import io
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.io as pio
import streamlit as st

from chart_ai import build_dashboard_charts
from dataset_engine import analyze_dataset
from explanation_engine import explain_all_charts, generate_trend_insights, prepare_analysis_frame
from query_utils import build_fallback_sql, detect_query_type, extract_sql
from sql_engine import generate_sql, repair_sql
from sql_runner import SQLValidationError, run_sql


st.set_page_config(page_title="AI Buisness Dashboard", layout="wide")


DEFAULT_DATASET_PATH = Path(
    r"c:\Users\chiku\Downloads\5. Customer Behaviour Online vs Offline-20260307T060833Z-1-001\5. Customer Behaviour (Online vs Offline)\Customer Behaviour (Online vs Offline).csv"
)


def apply_ui_theme(theme_mode="Light"):
    is_dark = str(theme_mode).lower() == "dark"
    title_color = "#dbeafe" if is_dark else "#0b2a6b"
    text_color = "#e5e7eb" if is_dark else "#0f172a"
    muted_color = "#94a3b8" if is_dark else "#64748b"
    app_bg = (
        """
                radial-gradient(circle at 8% 10%, rgba(59, 130, 246, 0.30), transparent 20%),
                radial-gradient(circle at 22% 28%, rgba(99, 102, 241, 0.24), transparent 22%),
                radial-gradient(circle at 78% 16%, rgba(16, 185, 129, 0.25), transparent 24%),
                radial-gradient(circle at 92% 36%, rgba(37, 99, 235, 0.26), transparent 20%),
                radial-gradient(circle at 58% 72%, rgba(14, 165, 233, 0.24), transparent 26%),
                repeating-linear-gradient(
                    135deg,
                    rgba(255, 255, 255, 0.02) 0px,
                    rgba(255, 255, 255, 0.02) 8px,
                    rgba(30, 41, 59, 0.10) 8px,
                    rgba(30, 41, 59, 0.10) 16px
                ),
                linear-gradient(180deg, #0b1220 0%, #111827 100%);
        """
        if is_dark
        else
        """
                radial-gradient(circle at 8% 10%, rgba(255, 170, 70, 0.28), transparent 20%),
                radial-gradient(circle at 22% 28%, rgba(255, 209, 90, 0.22), transparent 22%),
                radial-gradient(circle at 78% 16%, rgba(98, 165, 255, 0.30), transparent 24%),
                radial-gradient(circle at 92% 36%, rgba(138, 191, 255, 0.22), transparent 20%),
                radial-gradient(circle at 58% 72%, rgba(126, 219, 189, 0.20), transparent 26%),
                repeating-linear-gradient(
                    135deg,
                    rgba(255, 255, 255, 0.15) 0px,
                    rgba(255, 255, 255, 0.15) 8px,
                    rgba(227, 236, 252, 0.16) 8px,
                    rgba(227, 236, 252, 0.16) 16px
                ),
                linear-gradient(180deg, #f2f5ff 0%, #e8eefb 100%);
        """
    )
    glass_bg = "rgba(15,23,42,0.45)" if is_dark else "rgba(255,255,255,0.72)"
    glass_border = "rgba(148,163,184,0.35)" if is_dark else "rgba(203,213,225,0.88)"

    css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: "Manrope", sans-serif;
        }
        .stApp {
            background: __APP_BG__;
        }
        .main .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2.2rem;
            max-width: 1320px;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
            border-right: 1px solid rgba(255,255,255,0.1);
        }
        [data-testid="stSidebar"] * {
            color: #e5e7eb !important;
        }
        [data-testid="stSidebar"] .stAlert {
            background: rgba(255,255,255,0.08) !important;
        }
        h1, h2, h3 {
            letter-spacing: -0.02em;
            color: __TEXT_COLOR__;
        }
        .hero-title {
            font-size: 3rem;
            line-height: 1.1;
            font-weight: 800;
            color: __TITLE_COLOR__;
            letter-spacing: -0.02em;
            margin: 0 0 8px 0;
        }
        [data-testid="stMetric"] {
            background: linear-gradient(160deg, #ffffff 0%, #f7faff 100%);
            border: 1.5px solid #cbd5e1;
            border-radius: 16px;
            padding: 12px 16px;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
        }
        .kpi-card {
            background: __GLASS_BG__;
            border: 1.5px solid __GLASS_BORDER__;
            border-radius: 16px;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
            padding: 12px 14px;
            transition: transform .2s ease, box-shadow .2s ease;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 16px 32px rgba(15, 23, 42, 0.18);
        }
        .kpi-label {
            color: __MUTED_COLOR__;
            font-weight: 700;
            font-size: .86rem;
        }
        .kpi-value {
            color: __TEXT_COLOR__;
            font-weight: 800;
            font-size: 2rem;
            line-height: 1.1;
            margin-top: 4px;
        }
        .kpi-icon {
            margin-right: 8px;
        }
        [data-testid="stMetricLabel"] p {
            color: #64748b;
            font-weight: 700;
        }
        [data-testid="stMetricValue"] {
            color: #111827;
            font-weight: 800;
        }
        .stButton > button[kind="primary"],
        .stDownloadButton > button[kind="primary"] {
            border-radius: 12px;
            border: 1px solid #7f1d1d;
            background: linear-gradient(135deg, #7f1d1d 0%, #991b1b 45%, #b91c1c 100%);
            color: #fff7ed;
            font-weight: 700;
            transition: all 0.2s ease;
            box-shadow: 0 6px 18px rgba(127, 29, 29, 0.35);
        }
        .stButton > button[kind="primary"]:hover,
        .stDownloadButton > button[kind="primary"]:hover {
            border-color: #450a0a;
            color: #ffffff;
            background: linear-gradient(135deg, #991b1b 0%, #b91c1c 50%, #dc2626 100%);
            transform: translateY(-1px);
            box-shadow: 0 10px 22px rgba(127, 29, 29, 0.45);
        }
        .stButton > button[kind="primary"]:focus,
        .stDownloadButton > button[kind="primary"]:focus {
            outline: none;
            box-shadow: 0 0 0 3px rgba(248, 113, 113, 0.35), 0 10px 22px rgba(127, 29, 29, 0.45);
        }
        .stTextInput > div > div > input {
            border-radius: 14px;
            border: 1px solid rgba(255, 255, 255, 0.35);
            background: linear-gradient(135deg, #3f3e8a 0%, #4a4fb3 45%, #5864d8 100%);
            color: #f8fafc;
            font-weight: 600;
            padding-left: 12px;
            box-shadow: 0 8px 22px rgba(58, 58, 150, 0.28);
        }
        .stTextInput > div > div > input::placeholder {
            color: rgba(241, 245, 249, 0.86);
        }
        .stTextInput > div > div > input:focus {
            border-color: #93c5fd;
            box-shadow: 0 0 0 3px rgba(147, 197, 253, 0.25), 0 10px 24px rgba(88, 100, 216, 0.35);
        }
        [data-testid="stTextInput"] label p {
            color: #1f2937;
            font-weight: 700;
        }
        .stDataFrame, .stCodeBlock {
            border: 1.5px solid #cbd5e1;
            border-radius: 12px;
            overflow: hidden;
            background: rgba(255, 255, 255, 0.98);
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
        }
        [data-testid="stPlotlyChart"] {
            background: rgba(255, 255, 255, 0.98);
            border: 1.5px solid #cbd5e1;
            border-radius: 14px;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
            padding: 6px 8px 2px 8px;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 12px 12px 0 0;
            padding: 13px 24px;
            min-height: 50px;
            background: linear-gradient(135deg, #102a63 0%, #1d3f8f 55%, #284ea6 100%);
            border: 1.5px solid #0f2f6f;
            color: #ffffff !important;
            font-size: 1.05rem;
            font-weight: 800;
            box-shadow: 0 8px 18px rgba(15, 47, 111, 0.28);
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #0b255a 0%, #143877 55%, #1f4d99 100%) !important;
            color: #ffffff !important;
            border-color: #0b255a !important;
            box-shadow: 0 10px 22px rgba(11, 37, 90, 0.38) !important;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background: linear-gradient(135deg, #13336f 0%, #1f4b98 55%, #2b5fb8 100%);
            color: #ffffff !important;
        }
        .stCaption {
            color: __MUTED_COLOR__ !important;
        }
        .hero-subtitle {
            font-size: 1.08rem;
            font-weight: 700;
            color: __TITLE_COLOR__;
            margin-top: -2px;
            margin-bottom: 8px;
        }
        .hero-subtitle code {
            color: __TITLE_COLOR__;
            background: __CODE_BG__;
            border: 1px solid __CODE_BORDER__;
            border-radius: 8px;
            padding: 2px 8px;
            font-size: 0.95rem;
            font-weight: 700;
        }
        [data-testid="stFileUploaderDropzone"] button {
            border-radius: 12px !important;
            border: 1px solid #7f1d1d !important;
            background: linear-gradient(135deg, #991b1b 0%, #b91c1c 45%, #dc2626 100%) !important;
            color: #fff7ed !important;
            font-weight: 700 !important;
            box-shadow: 0 8px 18px rgba(127, 29, 29, 0.35) !important;
        }
        [data-testid="stFileUploaderDropzone"] button:hover {
            border-color: #450a0a !important;
            background: linear-gradient(135deg, #b91c1c 0%, #dc2626 55%, #ef4444 100%) !important;
        }
        </style>
        """
    code_bg = "rgba(30,58,138,0.35)" if is_dark else "rgba(59, 130, 246, 0.14)"
    code_border = "rgba(147,197,253,0.35)" if is_dark else "rgba(37, 99, 235, 0.22)"
    css = (
        css.replace("__APP_BG__", app_bg.strip())
        .replace("__TEXT_COLOR__", text_color)
        .replace("__TITLE_COLOR__", title_color)
        .replace("__MUTED_COLOR__", muted_color)
        .replace("__GLASS_BG__", glass_bg)
        .replace("__GLASS_BORDER__", glass_border)
        .replace("__CODE_BG__", code_bg)
        .replace("__CODE_BORDER__", code_border)
    )
    st.markdown(css, unsafe_allow_html=True)


def style_chart(fig):
    if fig is None:
        return fig
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(255,255,255,0.98)",
        plot_bgcolor="rgba(255,255,255,0.96)",
        font=dict(family="Manrope, sans-serif", color="#0f172a", size=13),
        title=dict(font=dict(size=20, color="#0f172a")),
        margin=dict(l=20, r=20, t=56, b=24),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(15,23,42,0.08)", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(15,23,42,0.08)", zeroline=False)
    for trace in fig.data:
        t = getattr(trace, "type", "")
        if t == "pie":
            continue
        if hasattr(trace, "marker"):
            try:
                trace.marker.color = "#f59e0b"
            except Exception:
                pass
    return fig


if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Light"

with st.sidebar:
    st.subheader("Appearance")
    st.session_state.theme_mode = st.radio(
        "Mode",
        options=["Light", "Dark"],
        index=0 if st.session_state.theme_mode == "Light" else 1,
        horizontal=True,
        key="theme_mode_selector",
    )

apply_ui_theme(st.session_state.theme_mode)
st.markdown('<h1 class="hero-title">𝐀𝐈 𝐁𝐮𝐢𝐬𝐧𝐞𝐬𝐬 𝐃𝐚𝐬𝐡𝐛𝐨𝐚𝐫𝐝</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-subtitle">Automatic Dashboard Builder prompt: '
    '<code>Create a customer behavior dashboard</code></p>',
    unsafe_allow_html=True,
)


def sanitize_column_name(name):
    text = str(name).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = "col"
    if text[0].isdigit():
        text = f"c_{text}"
    return text


def normalize_columns(df):
    used = set()
    rename_map = {}
    for col in df.columns:
        base = sanitize_column_name(col)
        candidate = base
        i = 1
        while candidate in used:
            i += 1
            candidate = f"{base}_{i}"
        used.add(candidate)
        rename_map[col] = candidate
    return df.rename(columns=rename_map), rename_map


def read_csv_with_fallback(uploaded_file):
    data = uploaded_file.getvalue()
    decoded = data.decode("latin-1", errors="ignore")
    lower = decoded.lower()

    if "bplist00" in lower and "<pre" in lower:
        pre_start = lower.find("<pre")
        pre_open_end = decoded.find(">", pre_start)
        pre_end = lower.find("</pre>", pre_open_end)
        if pre_open_end != -1 and pre_end != -1:
            embedded_csv = html.unescape(decoded[pre_open_end + 1 : pre_end]).strip()
            try:
                df = pd.read_csv(io.StringIO(embedded_csv))
                return df, "embedded-csv-from-html", False
            except Exception:
                pass

    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
    for enc in encodings:
        try:
            df = pd.read_csv(io.BytesIO(data), encoding=enc)
            bad_columns = [str(c).lower() for c in df.columns]
            if len(df.columns) <= 1 or any("bplist00" in c for c in bad_columns):
                continue
            return df, enc, False
        except UnicodeDecodeError:
            continue

    df = pd.read_csv(io.BytesIO(data), encoding="utf-8", encoding_errors="replace")
    return df, "utf-8 (replacement)", True


def load_csv_from_path(csv_path):
    with csv_path.open("rb") as source_file:
        data = source_file.read()

    decoded = data.decode("latin-1", errors="ignore")
    lower = decoded.lower()
    if "bplist00" in lower and "<pre" in lower:
        pre_start = lower.find("<pre")
        pre_open_end = decoded.find(">", pre_start)
        pre_end = lower.find("</pre>", pre_open_end)
        if pre_open_end != -1 and pre_end != -1:
            embedded_csv = html.unescape(decoded[pre_open_end + 1 : pre_end]).strip()
            try:
                df = pd.read_csv(io.StringIO(embedded_csv))
                return df, "embedded-csv-from-html", False
            except Exception:
                pass

    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            df = pd.read_csv(io.BytesIO(data), encoding=enc)
            bad_columns = [str(c).lower() for c in df.columns]
            if len(df.columns) <= 1 or any("bplist00" in c for c in bad_columns):
                continue
            return df, enc, False
        except UnicodeDecodeError:
            continue
        except pd.errors.ParserError:
            continue

    df = pd.read_csv(io.BytesIO(data), encoding="utf-8", encoding_errors="replace")
    return df, "utf-8 (replacement)", True


def apply_filters(df):
    filtered = df.copy()
    categorical = list(filtered.select_dtypes(include=["object", "category"]).columns)
    numeric = list(filtered.select_dtypes(include="number").columns)

    for col in categorical[:6]:
        values = filtered[col].dropna().unique().tolist()
        if not values or len(values) > 30:
            continue
        selected = st.multiselect(
            f"{col}",
            options=values,
            default=values,
            key=f"flt_cat_{col}",
        )
        if selected:
            filtered = filtered[filtered[col].isin(selected)]

    for col in numeric[:6]:
        min_val = float(filtered[col].min()) if len(filtered) else 0.0
        max_val = float(filtered[col].max()) if len(filtered) else 0.0
        if min_val == max_val:
            continue
        chosen = st.slider(
            f"{col} range",
            min_value=min_val,
            max_value=max_val,
            value=(min_val, max_val),
            key=f"flt_num_{col}",
        )
        filtered = filtered[(filtered[col] >= chosen[0]) & (filtered[col] <= chosen[1])]

    return filtered


def _format_kpi_value(value):
    if value is None or pd.isna(value):
        return "N/A"
    value = float(value)
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def _build_kpi_cards(df):
    cards = [
        {"label": "Rows", "value": f"{len(df):,}", "icon": "Rows"},
        {"label": "Columns", "value": f"{len(df.columns)}", "icon": "Cols"},
    ]

    if "monthly_income" in df.columns:
        cards.append(
            {
                "label": "Avg Monthly Income",
                "value": _format_kpi_value(df["monthly_income"].mean()),
                "icon": "Income",
            }
        )
    else:
        cards.append(
            {
                "label": "Numeric Columns",
                "value": f"{len(df.select_dtypes(include='number').columns)}",
                "icon": "Nums",
            }
        )

    if {"avg_online_spend", "avg_store_spend"}.issubset(df.columns):
        online_avg = df["avg_online_spend"].mean()
        store_avg = df["avg_store_spend"].mean()
        cards.append(
            {
                "label": "Higher Spend Channel",
                "value": "Store" if store_avg > online_avg else "Online",
                "icon": "Spend",
            }
        )
    elif "shopping_preference" in df.columns:
        top_pref = df["shopping_preference"].fillna("Unknown").mode()
        cards.append(
            {
                "label": "Top Preference",
                "value": str(top_pref.iloc[0]) if not top_pref.empty else "N/A",
                "icon": "Pref",
            }
        )
    else:
        numeric_cols = list(df.select_dtypes(include="number").columns)
        metric = numeric_cols[0] if numeric_cols else None
        cards.append(
            {
                "label": metric.replace("_", " ").title() if metric else "Metric",
                "value": _format_kpi_value(df[metric].mean()) if metric else "N/A",
                "icon": "Stat",
            }
        )

    return cards[:4]


def render_kpis(df):
    st.subheader("KPI CARDS")
    for container, card in zip(st.columns(4), _build_kpi_cards(df)):
        container.markdown(
            f'<div class="kpi-card"><div class="kpi-label"><span class="kpi-icon">{card["icon"]}</span>{card["label"]}</div><div class="kpi-value">{card["value"]}</div></div>',
            unsafe_allow_html=True,
        )


def reset_filters():
    keys = [
        k
        for k in st.session_state.keys()
        if k.startswith("flt_cat_") or k.startswith("flt_num_")
    ]
    for k in keys:
        del st.session_state[k]


def run_query(df, schema, question):
    query_type = detect_query_type(question)
    query_source = "model"
    column_aliases = schema.get("column_aliases", {}) if isinstance(schema, dict) else {}
    try:
        raw_sql = generate_sql(question, schema)
        sql = extract_sql(raw_sql)
        if not sql.lower().startswith(("select", "with", "show", "describe")):
            sql = build_fallback_sql(question, df, column_aliases)
            query_source = "fallback"
    except Exception:
        sql = build_fallback_sql(question, df, column_aliases)
        query_source = "fallback"

    try:
        result = run_sql(df, sql)
        return result, sql, query_type, query_source
    except (SQLValidationError, Exception) as err:
        try:
            repaired_raw_sql = repair_sql(question, schema, sql, str(err))
            repaired_sql = extract_sql(repaired_raw_sql)
            if not repaired_sql.lower().startswith(("select", "with", "show", "describe")):
                repaired_sql = build_fallback_sql(question, df, column_aliases)
        except Exception:
            repaired_sql = build_fallback_sql(question, df, column_aliases)

        try:
            result = run_sql(df, repaired_sql)
            return result, repaired_sql, query_type, "repaired"
        except (SQLValidationError, Exception):
            fallback_sql = build_fallback_sql(question, df, column_aliases)
            result = run_sql(df, fallback_sql)
            return result, fallback_sql, query_type, "fallback"


def _result_signature(df, sql):
    if df is None or df.empty:
        return f"{sql}|empty"
    sample = df.head(200)
    sample_hash = int(pd.util.hash_pandas_object(sample, index=True).sum())
    return f"{sql}|{len(df)}|{sample_hash}"


def build_dashboard_html(
    charts, explanation, sql, query_type, query_source, data_preview, user_query=""
):
    def fig_html(fig, title):
        if fig is None:
            return f"<h3>{title}</h3><p>Chart not available.</p>"
        return f"<h3>{title}</h3>" + pio.to_html(
            fig, include_plotlyjs=False, full_html=False, config={"responsive": True}
        )

    rows_html = data_preview.head(50).to_html(index=False)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
<html>
<head>
<meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<title>Dashboard Report</title>
</head>
<body style="font-family:Arial, sans-serif; margin:20px;">
<h1>AI Business Intelligence Dashboard</h1>
<p><b>Generated:</b> {generated_at}</p>
<p><b>User Query:</b> {html.escape(user_query or "N/A")}</p>
<p><b>Query Type:</b> {query_type} | <b>SQL Source:</b> {query_source}</p>
<h2>Generated SQL</h2>
<pre>{html.escape(sql)}</pre>
<h2>Chart Row 1</h2>
{fig_html(charts.get("bar"), "Bar Chart")}
{fig_html(charts.get("line"), "Line Chart")}
<h2>Chart Row 2</h2>
{fig_html(charts.get("pie"), "Pie Chart")}
{fig_html(charts.get("scatter"), "Scatter Plot")}
<h2>AI Chart Explanation</h2>
<p>{html.escape(explanation or "")}</p>
<h2>Data Preview</h2>
{rows_html}
</body>
</html>
"""


if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "last_sql" not in st.session_state:
    st.session_state.last_sql = "SELECT * FROM dataframe LIMIT 500"

if "last_query_type" not in st.session_state:
    st.session_state.last_query_type = "dashboard"

if "last_query_source" not in st.session_state:
    st.session_state.last_query_source = "auto_dashboard"

if "last_explanation" not in st.session_state:
    st.session_state.last_explanation = ""

if "last_explanation_key" not in st.session_state:
    st.session_state.last_explanation_key = ""

if "input_question" not in st.session_state:
    st.session_state.input_question = ""

if "show_filters" not in st.session_state:
    st.session_state.show_filters = False

if "query_run_nonce" not in st.session_state:
    st.session_state.query_run_nonce = 0

if "last_user_query" not in st.session_state:
    st.session_state.last_user_query = ""


uploaded_file = st.file_uploader("Upload dataset")

df = None
encoding_used = None
had_replacements = False
dataset_label = None

if uploaded_file:
    df, encoding_used, had_replacements = read_csv_with_fallback(uploaded_file)
    dataset_label = uploaded_file.name
elif DEFAULT_DATASET_PATH.exists():
    df, encoding_used, had_replacements = load_csv_from_path(DEFAULT_DATASET_PATH)
    dataset_label = DEFAULT_DATASET_PATH.name

if df is not None:
    df, rename_map = normalize_columns(df)

    if uploaded_file:
        st.success(f"Using uploaded dataset: `{dataset_label}`")
    else:
        st.info(
            "No dataset uploaded. Running queries against the default dataset "
            f"`{dataset_label}`."
        )

    if had_replacements:
        st.warning("File contained invalid UTF-8 bytes. Loaded with replacement characters.")
    else:
        st.caption(f"Loaded with encoding: {encoding_used}")

    if any(str(k) != str(v) for k, v in rename_map.items()):
        with st.expander("Column mapping", expanded=False):
            mapping_df = pd.DataFrame(
                {
                    "original_column": [str(k) for k in rename_map.keys()],
                    "normalized_column": [str(v) for v in rename_map.values()],
                }
            )
            st.dataframe(mapping_df, use_container_width=True)

    with st.sidebar:
        st.subheader("Navigation")
        st.caption("Chat History")
        if not st.session_state.chat_history:
            st.info("No chat history yet.")
        else:
            for item in reversed(st.session_state.chat_history[-8:]):
                st.markdown(f"**Q:** {item['question']}")
                st.caption(f"{item['query_type']} | {item['source']}")

    dashboard_tab, download_tab = st.tabs(["Dashboard", "Download & Results"])

    question = None
    selected_question = None

    with dashboard_tab:
        filter_col1, filter_col2 = st.columns([1, 5])
        with filter_col1:
            filter_btn_label = "Hide Filters" if st.session_state.show_filters else "Show Filters"
            if st.button(filter_btn_label, key="toggle_filters_btn", type="primary"):
                st.session_state.show_filters = not st.session_state.show_filters
        with filter_col2:
            rf1, rf2 = st.columns([1, 5])
            with rf1:
                if st.button("Reset Filters", key="reset_filters_btn", type="primary"):
                    reset_filters()
                    st.rerun()
            with rf2:
                st.caption("Use filters when needed to keep dashboard clean.")

        if st.session_state.show_filters:
            with st.container(border=True):
                st.subheader("Filters (Very Important)")
                filtered_df = apply_filters(df)
        else:
            filtered_df = df.copy()

        schema = analyze_dataset(filtered_df, rename_map)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Dataset Summary Panel")
        st.write(
            f"Rows: `{len(filtered_df):,}` | Columns: `{len(filtered_df.columns)}` | "
            f"Numeric: `{len(schema['numeric'])}` | Categorical: `{len(schema['categorical'])}`"
        )
        st.dataframe(filtered_df.head(8), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Dashboard Generator")
        st.write("Use prompt like: `Create a customer behavior dashboard`")
        sample_questions = [
            "Create a customer behavior dashboard",
            "last month income",
            "this month income vs last month income",
            "average daily internet hours",
            "internet hours vs social media hours",
            "top 5 people by monthly income",
            "show monthly income and daily internet hours",
        ]

        b1, b2 = st.columns(2)
        for idx, prompt in enumerate(sample_questions):
            col = b1 if idx % 2 == 0 else b2
            if col.button(prompt, key=f"sample_{idx}", type="secondary"):
                selected_question = prompt
                st.session_state.input_question = prompt

        with st.form("query_form", clear_on_submit=False):
            st.text_input(
                "Ask a question about your data",
                key="input_question",
                placeholder="Type query and click Run Query",
            )
            run_clicked = st.form_submit_button("Run Query", type="primary")
        st.markdown("</div>", unsafe_allow_html=True)

        if run_clicked:
            st.session_state.query_run_nonce += 1

        if selected_question:
            question = selected_question
        elif run_clicked and st.session_state.input_question.strip():
            question = st.session_state.input_question.strip()

        dashboard_source = filtered_df.head(500)
        if question:
            st.session_state.last_user_query = question
            auto_dashboard = "create" in question.lower() and "dashboard" in question.lower()
            if not auto_dashboard:
                result, sql, q_type, q_source = run_query(filtered_df, schema, question)
                st.session_state.last_result = result
                st.session_state.last_sql = sql
                st.session_state.last_query_type = q_type
                st.session_state.last_query_source = q_source
            else:
                st.session_state.last_result = filtered_df.head(500)
                st.session_state.last_sql = "SELECT * FROM dataframe LIMIT 500"
                st.session_state.last_query_type = "dashboard"
                st.session_state.last_query_source = "auto_dashboard"

            st.session_state.chat_history.append(
                {
                    "question": question,
                    "query_type": st.session_state.last_query_type,
                    "source": st.session_state.last_query_source,
                }
            )

        if st.session_state.last_result is not None:
            dashboard_source = st.session_state.last_result

        charts = build_dashboard_charts(dashboard_source)

        render_kpis(dashboard_source)
        st.caption(
            f"Query type: `{st.session_state.last_query_type}` | "
            f"SQL source: `{st.session_state.last_query_source}`"
        )
        st.subheader("Generated SQL")
        st.code(st.session_state.last_sql)
        st.subheader("Charts")
        st.subheader("Chart Row 1")
        c1, c2 = st.columns(2)
        with c1:
            if charts["bar"] is not None:
                st.plotly_chart(style_chart(charts["bar"]), use_container_width=True)
            else:
                st.info("Bar chart not available.")
        with c2:
            if charts["line"] is not None:
                styled_line = style_chart(charts["line"])
                styled_line.update_traces(line=dict(color="#22c55e", width=3))
                st.plotly_chart(styled_line, use_container_width=True)
            else:
                st.info("Line chart not available.")

        st.subheader("Chart Row 2")
        c3, c4 = st.columns(2)
        with c3:
            if charts["pie"] is not None:
                styled_pie = style_chart(charts["pie"])
                styled_pie.update_traces(
                    marker=dict(
                        colors=["#f59e0b", "#60a5fa", "#34d399", "#f472b6", "#a78bfa"]
                    )
                )
                st.plotly_chart(styled_pie, use_container_width=True)
            else:
                st.info("Pie chart not available.")
        with c4:
            if charts["scatter"] is not None:
                styled_scatter = style_chart(charts["scatter"])
                styled_scatter.update_traces(
                    marker=dict(color="#f59e0b", size=10, opacity=0.8)
                )
                st.plotly_chart(styled_scatter, use_container_width=True)
            else:
                st.info("Scatter chart not available.")

        st.subheader("AI Chart Explanation")
        explanation_source = dashboard_source
        if explanation_source is None or explanation_source.empty:
            explanation_source = filtered_df
        analysis_frame = prepare_analysis_frame(explanation_source)
        chart_explanations = explain_all_charts(analysis_frame)
        trend_insights = generate_trend_insights(analysis_frame)
        current_expl_key = _result_signature(
            analysis_frame.head(200), st.session_state.last_sql
        )
        if st.session_state.last_explanation_key != current_expl_key:
            st.session_state.last_explanation = ""
            st.session_state.last_explanation_key = current_expl_key

        if not st.session_state.last_explanation:
            st.session_state.last_explanation = (
                " ".join(trend_insights)
                if trend_insights
                else "Explanation is unavailable right now."
            )
        st.caption("Explanation is generated from a fast sample of the current result and cached per query.")

        with st.expander("Open AI Explanation", expanded=True):
            chart_labels = {
                "bar": "Bar Chart",
                "line": "Line Chart",
                "pie": "Pie Chart",
                "scatter": "Scatter Chart",
            }
            for key in ("bar", "line", "pie", "scatter"):
                st.markdown(f"**{chart_labels[key]}:**")
                st.write(chart_explanations.get(key, "Explanation is unavailable right now."))

            st.markdown("**Trend Insights**")
            if trend_insights:
                for insight in trend_insights:
                    st.markdown(f"- {insight}")
            else:
                st.write("Trend insights are unavailable right now.")

            st.markdown("**Overall Summary**")
            st.write(st.session_state.last_explanation)

    with download_tab:
        dashboard_source = filtered_df.head(500)
        if st.session_state.last_result is not None:
            dashboard_source = st.session_state.last_result
        charts = build_dashboard_charts(dashboard_source)
        st.subheader("Generated SQL")
        st.code(st.session_state.last_sql)
        st.subheader("Download Dashboard With Result")
        csv_bytes = dashboard_source.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Results",
            data=csv_bytes,
            file_name="dashboard_results.csv",
            mime="text/csv",
            type="primary",
        )
        dashboard_html = build_dashboard_html(
            charts=charts,
            explanation=st.session_state.last_explanation,
            sql=st.session_state.last_sql,
            query_type=st.session_state.last_query_type,
            query_source=st.session_state.last_query_source,
            data_preview=dashboard_source,
            user_query=st.session_state.last_user_query,
        ).encode("utf-8")
        st.download_button(
            "Download Dashboard (HTML)",
            data=dashboard_html,
            file_name="dashboard_report.html",
            mime="text/html",
            type="primary",
        )
        st.dataframe(dashboard_source.head(100), use_container_width=True)
else:
    st.warning(
        "Upload a dataset or place the default customer behaviour CSV at "
        f"`{DEFAULT_DATASET_PATH}` to run queries."
    )
