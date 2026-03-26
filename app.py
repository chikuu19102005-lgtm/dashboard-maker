import html
import io
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st

from chart_ai import build_dashboard_charts
from dashboard_filters import apply_output_filters, detect_output_filter_config, sync_output_filter_state
from dataset_engine import analyze_dataset
from explanation_engine import (
    answer_analysis_question,
    explain_all_charts,
    generate_strategic_insights,
    generate_trend_insights,
    prepare_analysis_frame,
    summarize_all_charts,
)
from language_engine import (
    bilingual_list,
    bilingual_text,
    detect_input_language,
    translate_question_to_english,
)
from query_utils import (
    build_fallback_sql,
    detect_query_type,
    extract_sql,
    validate_question_columns,
)
from sql_engine import generate_sql, repair_sql
from sql_runner import SQLValidationError, run_sql


st.set_page_config(page_title="AI Business Dashboard", layout="wide")


DEFAULT_DATASET_PATH = Path(
    r"c:\Users\chiku\Downloads\5. Customer Behaviour Online vs Offline-20260307T060833Z-1-001\5. Customer Behaviour (Online vs Offline)\Customer Behaviour (Online vs Offline).csv"
)


def apply_ui_theme(theme_mode="Light"):
    is_dark = str(theme_mode).lower() == "dark"
    title_color = "#f8fafc" if is_dark else "#0b2a6b"
    text_color = "#f8fafc" if is_dark else "#0f172a"
    muted_color = "#94a3b8" if is_dark else "#64748b"
    body_text_color = "#e2e8f0" if is_dark else "#0f172a"
    sidebar_bg = (
        "linear-gradient(180deg, #0f172a 0%, #111827 100%)"
        if is_dark
        else "linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%)"
    )
    sidebar_text = "#e5e7eb" if is_dark else "#0f172a"
    sidebar_border = "rgba(255,255,255,0.10)" if is_dark else "rgba(15,23,42,0.12)"
    metric_bg = (
        "linear-gradient(160deg, rgba(15,23,42,0.96) 0%, rgba(30,41,59,0.94) 100%)"
        if is_dark
        else "linear-gradient(160deg, #ffffff 0%, #f7faff 100%)"
    )
    metric_border = "rgba(71,85,105,0.55)" if is_dark else "#cbd5e1"
    metric_label_text = "#94a3b8" if is_dark else "#64748b"
    metric_value_text = "#f8fafc" if is_dark else "#111827"
    input_label_text = "#cbd5e1" if is_dark else "#1f2937"
    surface_bg = "rgba(15,23,42,0.56)" if is_dark else "rgba(255, 255, 255, 0.98)"
    surface_border = "rgba(71,85,105,0.55)" if is_dark else "#cbd5e1"
    plot_bg = "rgba(15,23,42,0.48)" if is_dark else "rgba(255, 255, 255, 0.98)"
    plot_border = "rgba(71,85,105,0.55)" if is_dark else "#cbd5e1"
    process_card_bg = "rgba(15,23,42,0.44)" if is_dark else "rgba(255,255,255,0.68)"
    process_card_border = "rgba(71,85,105,0.38)" if is_dark else "rgba(148,163,184,0.22)"
    input_bg = (
        "linear-gradient(135deg, #1e293b 0%, #334155 50%, #475569 100%)"
        if is_dark
        else "linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)"
    )
    input_border = "rgba(148,163,184,0.55)" if is_dark else "rgba(15,23,42,0.18)"
    input_text = "#f8fafc" if is_dark else "#0f172a"
    input_placeholder = "rgba(226,232,240,0.85)" if is_dark else "rgba(15,23,42,0.52)"
    input_focus_border = "#93c5fd" if is_dark else "#1d4ed8"
    input_focus_shadow = (
        "0 0 0 3px rgba(147, 197, 253, 0.25), 0 10px 24px rgba(71, 85, 105, 0.30)"
        if is_dark
        else "0 0 0 3px rgba(29, 78, 216, 0.18), 0 10px 24px rgba(148, 163, 184, 0.25)"
    )
    profile_card_bg = "rgba(15,23,42,0.62)" if is_dark else "rgba(255,255,255,0.70)"
    profile_card_border = "rgba(148,163,184,0.34)" if is_dark else "rgba(148,163,184,0.24)"
    chip_bg = "rgba(30,41,59,0.72)" if is_dark else "rgba(255,255,255,0.72)"
    chip_border = "rgba(148,163,184,0.42)" if is_dark else "rgba(148,163,184,0.28)"
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
    glass_bg = "rgba(15,23,42,0.74)" if is_dark else "rgba(255,255,255,0.72)"
    glass_border = "rgba(148,163,184,0.34)" if is_dark else "rgba(203,213,225,0.88)"

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
            background: __SIDEBAR_BG__;
            border-right: 1px solid __SIDEBAR_BORDER__;
        }
        [data-testid="stSidebar"] * {
            color: __SIDEBAR_TEXT__ !important;
        }
        [data-testid="stSidebar"] .stAlert {
            background: rgba(255,255,255,0.08) !important;
        }
        h1, h2, h3 {
            letter-spacing: -0.02em;
            color: __TEXT_COLOR__ !important;
        }
        h4, h5, h6 {
            color: __TEXT_COLOR__ !important;
        }
        .main .block-container [data-testid="stMarkdownContainer"] h1,
        .main .block-container [data-testid="stMarkdownContainer"] h2,
        .main .block-container [data-testid="stMarkdownContainer"] h3,
        .main .block-container [data-testid="stMarkdownContainer"] h4,
        .main .block-container [data-testid="stMarkdownContainer"] h5,
        .main .block-container [data-testid="stMarkdownContainer"] h6,
        .main .block-container [data-testid="stHeadingWithActionElements"] h1,
        .main .block-container [data-testid="stHeadingWithActionElements"] h2,
        .main .block-container [data-testid="stHeadingWithActionElements"] h3,
        .main .block-container [data-testid="stHeadingWithActionElements"] h4,
        .main .block-container [data-testid="stHeadingWithActionElements"] h5,
        .main .block-container [data-testid="stHeadingWithActionElements"] h6 {
            color: __TEXT_COLOR__ !important;
        }
        .main .block-container,
        .main .block-container label,
        .main .block-container [data-testid="stMarkdownContainer"],
        .main .block-container [data-testid="stMarkdownContainer"] p,
        .main .block-container [data-testid="stMarkdownContainer"] li,
        .main .block-container [data-testid="stMarkdownContainer"] span,
        .main .block-container .stAlert,
        .main .block-container .stInfo,
        .main .block-container .stSuccess,
        .main .block-container .stWarning,
        .main .block-container .stError {
            color: __BODY_TEXT_COLOR__;
        }
        .hero-title {
            font-size: 3rem;
            line-height: 1.1;
            font-weight: 800;
            color: __TITLE_COLOR__ !important;
            letter-spacing: -0.02em;
            margin: 0 0 8px 0;
        }
        .main .block-container [data-testid="stMarkdownContainer"] p,
        .main .block-container [data-testid="stMarkdownContainer"] li,
        .main .block-container [data-testid="stMarkdownContainer"] * ,
        .main .block-container p,
        .main .block-container li,
        .main .block-container span,
        .main .block-container .process-copy,
        .main .block-container .profile-sub,
        .main .block-container .chip,
        .main .block-container .kpi-label {
            color: __BODY_TEXT_COLOR__ !important;
        }
        .main .block-container strong,
        .main .block-container b {
            color: __TEXT_COLOR__;
        }
        [data-testid="stMetric"] {
            background: __METRIC_BG__;
            border: 1.5px solid __METRIC_BORDER__;
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
            color: __METRIC_LABEL_TEXT__;
            font-weight: 700;
        }
        [data-testid="stMetricValue"] {
            color: __METRIC_VALUE_TEXT__;
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
            border: 1px solid __INPUT_BORDER__;
            background: __INPUT_BG__;
            color: __INPUT_TEXT__;
            font-weight: 600;
            padding-left: 12px;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.18);
        }
        .stTextInput > div > div > input::placeholder {
            color: __INPUT_PLACEHOLDER__;
        }
        .stTextInput > div > div > input:focus {
            border-color: __INPUT_FOCUS_BORDER__;
            box-shadow: __INPUT_FOCUS_SHADOW__;
        }
        [data-testid="stTextInput"] label p {
            color: __INPUT_LABEL_TEXT__;
            font-weight: 700;
        }
        .stDataFrame, .stCodeBlock {
            border: 1.5px solid __SURFACE_BORDER__;
            border-radius: 12px;
            overflow: hidden;
            background: __SURFACE_BG__;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
        }
        .section-panel {
            background: __GLASS_BG__;
            border: 1.5px solid __GLASS_BORDER__;
            border-radius: 22px;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            box-shadow: 0 18px 38px rgba(15, 23, 42, 0.12);
            padding: 18px 20px 12px 20px;
            margin-bottom: 18px;
            overflow: hidden;
            animation: riseIn .45s ease-out both;
        }
        .process-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            margin: 12px 0 4px 0;
        }
        .process-card {
            border-radius: 16px;
            border: 1px solid __PROCESS_CARD_BORDER__;
            background: __PROCESS_CARD_BG__;
            padding: 14px 16px;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.5);
        }
        .process-step {
            color: __MUTED_COLOR__;
            font-size: 0.78rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .08em;
        }
        .process-title {
            color: __TEXT_COLOR__;
            font-size: 1.05rem;
            font-weight: 800;
            margin-top: 6px;
        }
        .process-copy {
            color: __TEXT_COLOR__;
            font-size: 0.92rem;
            margin-top: 6px;
            opacity: .86;
        }
        .profile-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
            margin: 8px 0 12px 0;
        }
        .profile-card {
            border-radius: 16px;
            background: __PROFILE_CARD_BG__;
            border: 1px solid __PROFILE_CARD_BORDER__;
            padding: 14px 16px;
        }
        .profile-label {
            color: __MUTED_COLOR__;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: .08em;
            font-weight: 800;
        }
        .profile-value {
            color: __TEXT_COLOR__;
            font-size: 1.8rem;
            font-weight: 800;
            margin-top: 4px;
        }
        .profile-sub {
            color: __MUTED_COLOR__;
            font-size: 0.85rem;
            margin-top: 4px;
        }
        .chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 10px 0 4px 0;
        }
        .chip {
            display: inline-flex;
            align-items: center;
            padding: 8px 12px;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 700;
            color: __TEXT_COLOR__;
            background: __CHIP_BG__;
            border: 1px solid __CHIP_BORDER__;
        }
        @keyframes riseIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        [data-testid="stPlotlyChart"] {
            background: __PLOT_BG__;
            border: 1.5px solid __PLOT_BORDER__;
            border-radius: 14px;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
            padding: 6px 8px 2px 8px;
            overflow: hidden;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            align-self: stretch;
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
            color: __BODY_TEXT_COLOR__ !important;
            opacity: 0.9;
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
        @media (max-width: 1100px) {
            .main .block-container {
                max-width: 100%;
                padding-left: 1rem;
                padding-right: 1rem;
            }
            .hero-title {
                font-size: 2.35rem;
            }
            .section-panel {
                padding: 16px 16px 10px 16px;
            }
        }
        @media (max-width: 900px) {
            .hero-title {
                font-size: 2rem;
            }
            .hero-subtitle {
                font-size: 0.98rem;
            }
            .process-grid,
            .profile-grid {
                grid-template-columns: 1fr;
            }
            [data-testid="stHorizontalBlock"] {
                gap: 0.8rem !important;
                flex-wrap: wrap !important;
            }
            [data-testid="stHorizontalBlock"] > [data-testid="column"] {
                min-width: 100% !important;
                width: 100% !important;
                flex: 1 1 100% !important;
            }
            [data-testid="stPlotlyChart"] {
                padding: 4px 4px 2px 4px;
            }
            .stButton > button,
            .stDownloadButton > button {
                width: 100%;
            }
        }
        @media (max-width: 640px) {
            .main .block-container {
                padding-top: 1rem;
                padding-left: 0.75rem;
                padding-right: 0.75rem;
                padding-bottom: 1.5rem;
            }
            .hero-title {
                font-size: 1.75rem;
                line-height: 1.15;
            }
            h1, h2, h3 {
                line-height: 1.2;
            }
            .section-panel,
            .kpi-card {
                border-radius: 14px;
            }
            [data-testid="stDataFrame"],
            .stDataFrame,
            .stCodeBlock {
                overflow-x: auto;
            }
            [data-testid="stSidebar"] {
                min-width: 16rem;
            }
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
        .replace("__BODY_TEXT_COLOR__", body_text_color)
        .replace("__SIDEBAR_BG__", sidebar_bg)
        .replace("__SIDEBAR_TEXT__", sidebar_text)
        .replace("__SIDEBAR_BORDER__", sidebar_border)
        .replace("__GLASS_BG__", glass_bg)
        .replace("__GLASS_BORDER__", glass_border)
        .replace("__CODE_BG__", code_bg)
        .replace("__CODE_BORDER__", code_border)
        .replace("__METRIC_BG__", metric_bg)
        .replace("__METRIC_BORDER__", metric_border)
        .replace("__METRIC_LABEL_TEXT__", metric_label_text)
        .replace("__METRIC_VALUE_TEXT__", metric_value_text)
        .replace("__INPUT_LABEL_TEXT__", input_label_text)
        .replace("__SURFACE_BG__", surface_bg)
        .replace("__SURFACE_BORDER__", surface_border)
        .replace("__PLOT_BG__", plot_bg)
        .replace("__PLOT_BORDER__", plot_border)
        .replace("__PROCESS_CARD_BG__", process_card_bg)
        .replace("__PROCESS_CARD_BORDER__", process_card_border)
        .replace("__INPUT_BG__", input_bg)
        .replace("__INPUT_BORDER__", input_border)
        .replace("__INPUT_TEXT__", input_text)
        .replace("__INPUT_PLACEHOLDER__", input_placeholder)
        .replace("__INPUT_FOCUS_BORDER__", input_focus_border)
        .replace("__INPUT_FOCUS_SHADOW__", input_focus_shadow)
        .replace("__PROFILE_CARD_BG__", profile_card_bg)
        .replace("__PROFILE_CARD_BORDER__", profile_card_border)
        .replace("__CHIP_BG__", chip_bg)
        .replace("__CHIP_BORDER__", chip_border)
    )
    st.markdown(css, unsafe_allow_html=True)


def _profile_palette(profile_name):
    palettes = {
        "Sales Performance": {
            "primary": "#ef4444",
            "line": "#f97316",
            "pie": ["#ef4444", "#f97316", "#fb7185", "#fdba74", "#fca5a5"],
        },
        "Inventory Operations": {
            "primary": "#0ea5e9",
            "line": "#22c55e",
            "pie": ["#0ea5e9", "#22c55e", "#14b8a6", "#38bdf8", "#86efac"],
        },
        "Marketing Performance": {
            "primary": "#8b5cf6",
            "line": "#ec4899",
            "pie": ["#8b5cf6", "#ec4899", "#a78bfa", "#f472b6", "#c4b5fd"],
        },
        "Healthcare Operations": {
            "primary": "#2563eb",
            "line": "#06b6d4",
            "pie": ["#2563eb", "#06b6d4", "#60a5fa", "#67e8f9", "#93c5fd"],
        },
        "Finance Executive": {
            "primary": "#0f766e",
            "line": "#14b8a6",
            "pie": ["#0f766e", "#14b8a6", "#2dd4bf", "#5eead4", "#99f6e4"],
        },
        "General Executive": {
            "primary": "#f59e0b",
            "line": "#22c55e",
            "pie": ["#f59e0b", "#60a5fa", "#34d399", "#f472b6", "#a78bfa"],
        },
    }
    return palettes.get(profile_name, palettes["General Executive"])


def infer_dashboard_profile(df, schema):
    columns = [str(c).lower() for c in list(schema.get("columns", []))]
    col_blob = " ".join(columns)

    rules = [
        (
            "Sales Performance",
            ("sale", "sales", "revenue", "profit", "order", "quantity"),
            "Best for transaction/sales datasets with KPI-first layout and performance charts.",
        ),
        (
            "Inventory Operations",
            ("inventory", "stock", "supply", "warehouse", "replenishment", "product"),
            "Best for stock and fulfillment datasets with category and availability focus.",
        ),
        (
            "Marketing Performance",
            ("impression", "click", "ctr", "campaign", "seo", "traffic", "conversion"),
            "Best for campaign/channel datasets with funnel and trend sections.",
        ),
        (
            "Healthcare Operations",
            ("patient", "hospital", "department", "visit", "wait", "doctor"),
            "Best for operational healthcare datasets with service and throughput views.",
        ),
        (
            "Finance Executive",
            ("asset", "liability", "cogs", "expense", "margin", "balance", "cash"),
            "Best for financial statement datasets with margin and ratio dashboards.",
        ),
    ]

    for name, keys, reason in rules:
        if any(key in col_blob for key in keys):
            return name, reason

    return (
        "General Executive",
        "Best default for mixed datasets using KPIs, distribution, trend, and correlation charts.",
    )


def style_chart(fig, profile_name="General Executive"):
    if fig is None:
        return fig
    is_dark = str(st.session_state.get("theme_mode", "Light")).lower() == "dark"
    palette = _profile_palette(profile_name)
    fig.update_layout(
        template="plotly_dark" if is_dark else "plotly_white",
        paper_bgcolor="rgba(15,23,42,0.94)" if is_dark else "rgba(255,255,255,0.98)",
        plot_bgcolor="rgba(15,23,42,0.90)" if is_dark else "rgba(255,255,255,0.96)",
        font=dict(
            family="Manrope, sans-serif",
            color="#e5e7eb" if is_dark else "#0f172a",
            size=13,
        ),
        title=dict(font=dict(size=20, color="#f8fafc" if is_dark else "#0f172a")),
        margin=dict(l=20, r=20, t=56, b=24),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        transition=dict(duration=650, easing="cubic-in-out"),
        uirevision="dashboard-static",
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.16)" if is_dark else "rgba(15,23,42,0.08)",
        zeroline=False,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.16)" if is_dark else "rgba(15,23,42,0.08)",
        zeroline=False,
    )
    for trace in fig.data:
        t = getattr(trace, "type", "")
        if t == "pie":
            continue
        if hasattr(trace, "marker"):
            try:
                trace.marker.color = palette["primary"]
            except Exception:
                pass
    return fig


def why_this_graph(chart_key):
    reasons = {
        "bar": "Why this graph: compares categories or records to quickly see which values are highest or lowest.",
        "line": "Why this graph: shows change/trend patterns across records or grouped categories.",
        "pie": "Why this graph: highlights distribution share so you can see dominant segments.",
        "scatter": "Why this graph: reveals relationship/correlation between two numeric fields.",
    }
    return reasons.get(chart_key, "Why this graph: useful visual summary of the current result.")


def get_current_page():
    raw_page = st.query_params.get("page", "input")
    page = str(raw_page).strip().lower()
    mapping = {
        "input": "Input",
        "output": "Output",
        "download": "Download",
    }
    return mapping.get(page, "Input")


def set_current_page(page_name):
    page_key = str(page_name).strip().lower()
    st.query_params["page"] = page_key


def navigate_to_page(page_name):
    set_current_page(page_name)
    st.rerun()


def render_top_page_nav(current_page):
    spacer_left, input_col, output_col, download_col, spacer_right = st.columns(
        [1.4, 0.9, 0.9, 0.9, 1.4]
    )
    with input_col:
        if st.button(
            "Input",
            key=f"top_input_{current_page}",
            type="primary" if current_page == "Input" else "secondary",
        ):
            navigate_to_page("Input")
    with output_col:
        if st.button(
            "Output",
            key=f"top_output_{current_page}",
            type="primary" if current_page == "Output" else "secondary",
        ):
            navigate_to_page("Output")
    with download_col:
        if st.button(
            "Download",
            key=f"top_download_{current_page}",
            type="primary" if current_page == "Download" else "secondary",
        ):
            navigate_to_page("Download")


def sync_uploaded_datasets(uploaded_files):
    datasets = {}
    for item in uploaded_files or []:
        datasets[item.name] = item.getvalue()
    st.session_state.uploaded_datasets = datasets
    if datasets and st.session_state.active_dataset_name not in datasets:
        st.session_state.active_dataset_name = list(datasets.keys())[0]


def available_dataset_options():
    options = ["Default dataset"]
    options.extend(sorted(st.session_state.uploaded_datasets.keys()))
    return options


def current_dataset_payload():
    selected_name = st.session_state.active_dataset_name
    if selected_name and selected_name in st.session_state.uploaded_datasets:
        return (
            read_csv_bytes_with_fallback(st.session_state.uploaded_datasets[selected_name]),
            selected_name,
            True,
        )
    if DEFAULT_DATASET_PATH.exists():
        return (load_csv_from_path(DEFAULT_DATASET_PATH), DEFAULT_DATASET_PATH.name, False)
    return ((None, None, None), None, False)


def top_column_labels(schema):
    labels = []
    for item in schema.get("top_columns", [])[:5]:
        labels.append(
            f'{item["name"]} ({item["dtype"]}, {item["non_null_pct"]:.1f}% filled)'
        )
    return labels


def render_dataset_profile(schema):
    chips = "".join([f'<span class="chip">{html.escape(label)}</span>' for label in top_column_labels(schema)])
    st.markdown(
        f"""
        <div class="section-panel">
            <h3>Dataset Profiling</h3>
            <div class="profile-grid">
                <div class="profile-card">
                    <div class="profile-label">Rows</div>
                    <div class="profile-value">{schema.get("rows", 0):,}</div>
                    <div class="profile-sub">Records available for analysis</div>
                </div>
                <div class="profile-card">
                    <div class="profile-label">Columns</div>
                    <div class="profile-value">{schema.get("column_count", 0)}</div>
                    <div class="profile-sub">Fields currently loaded</div>
                </div>
                <div class="profile-card">
                    <div class="profile-label">Missing Values</div>
                    <div class="profile-value">{schema.get("missing_values", 0):,}</div>
                    <div class="profile-sub">Null cells across the active dataset</div>
                </div>
                <div class="profile-card">
                    <div class="profile-label">Top Columns</div>
                    <div class="profile-value">{len(schema.get("top_columns", []))}</div>
                    <div class="profile-sub">Most complete and informative fields</div>
                </div>
            </div>
            <div class="chip-row">{chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_nl_sql_panel():
    st.markdown(
        """
        <div class="section-panel">
            <h3>Natural Language SQL</h3>
            <div class="process-grid">
                <div class="process-card">
                    <div class="process-step">Step 1</div>
                    <div class="process-title">User types a business question</div>
                    <div class="process-copy"><code>top 10 customers by revenue</code></div>
                </div>
                <div class="process-card">
                    <div class="process-step">Step 2</div>
                    <div class="process-title">AI converts it to SQL</div>
                    <div class="process-copy">The app maps business language to dataset fields, generates SQL, and repairs it if needed.</div>
                </div>
                <div class="process-card">
                    <div class="process-step">Step 3</div>
                    <div class="process-title">Enterprise dashboard is built</div>
                    <div class="process-copy">KPIs, charts, explanations, and downloads are produced from the active result set.</div>
                </div>
            </div>
            <div class="process-copy">
                Supported input languages: English, Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, Punjabi, Kannada, Spanish, French, German, Chinese, Arabic, Japanese, and Malayalam.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_download_actions(dashboard_source, charts, prefix):
    left_col, right_col = st.columns(2)
    csv_bytes = dashboard_source.to_csv(index=False).encode("utf-8")
    with left_col:
        st.download_button(
            "Download Results",
            data=csv_bytes,
            file_name="dashboard_results.csv",
            mime="text/csv",
            type="primary",
            key=f"{prefix}_download_results",
        )
    with right_col:
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
            key=f"{prefix}_download_dashboard",
        )


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
st.markdown('<h1 class="hero-title">AI Business Dashboard</h1>', unsafe_allow_html=True)


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


@st.cache_data(show_spinner=False)
def _cached_read_csv_bytes_with_fallback(data):
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
        except pd.errors.ParserError:
            continue

    df = pd.read_csv(io.BytesIO(data), encoding="utf-8", encoding_errors="replace")
    return df, "utf-8 (replacement)", True


def read_csv_bytes_with_fallback(data):
    return _cached_read_csv_bytes_with_fallback(data)


def read_csv_with_fallback(uploaded_file):
    return read_csv_bytes_with_fallback(uploaded_file.getvalue())


@st.cache_data(show_spinner=False)
def _cached_load_csv_from_path(csv_path_str, modified_time_ns):
    del modified_time_ns
    with Path(csv_path_str).open("rb") as source_file:
        data = source_file.read()
    return read_csv_bytes_with_fallback(data)


def load_csv_from_path(csv_path):
    return _cached_load_csv_from_path(str(csv_path), csv_path.stat().st_mtime_ns)


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
            default=[],
            key=f"flt_cat_{col}",
        )
        if selected:
            filtered = filtered[filtered[col].isin(selected)]

    for col in numeric[:6]:
        min_val = float(filtered[col].min()) if len(filtered) else 0.0
        max_val = float(filtered[col].max()) if len(filtered) else 0.0
        if min_val == max_val:
            continue
        apply_range = st.checkbox(f"Apply {col} range filter", key=f"flt_num_enable_{col}")
        if apply_range:
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


def build_correlation_heatmap(df):
    numeric_cols = list(df.select_dtypes(include="number").columns)
    if len(numeric_cols) < 2:
        return None
    corr = df[numeric_cols].corr(numeric_only=True)
    if corr.empty:
        return None
    corr = corr.round(2)
    return px.imshow(
        corr,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="Heat Map (Correlation)",
    )


def build_confusing_metrics(df, max_rows=8):
    numeric_cols = list(df.select_dtypes(include="number").columns)
    if not numeric_cols:
        return pd.DataFrame()

    rows = []
    for col in numeric_cols:
        series = pd.to_numeric(df[col], errors="coerce")
        non_null = series.dropna()
        missing_pct = float(series.isna().mean() * 100) if len(series) else 0.0
        zero_pct = float((non_null == 0).mean() * 100) if len(non_null) else 0.0
        unique_pct = float(non_null.nunique() / len(non_null) * 100) if len(non_null) else 0.0
        avg_value = float(non_null.mean()) if len(non_null) else 0.0
        std_value = float(non_null.std()) if len(non_null) > 1 else 0.0
        confusion_score = (
            (missing_pct * 0.5)
            + (max(0.0, 40.0 - unique_pct) * 0.8)
            + (max(0.0, zero_pct - 30.0) * 0.6)
        )
        rows.append(
            {
                "Metric": col,
                "Missing %": round(missing_pct, 1),
                "Zero %": round(zero_pct, 1),
                "Unique %": round(unique_pct, 1),
                "Average": round(avg_value, 2),
                "Std Dev": round(std_value, 2),
                "Confusion Score": round(confusion_score, 1),
            }
        )

    metrics_df = pd.DataFrame(rows)
    if metrics_df.empty:
        return metrics_df
    return metrics_df.sort_values("Confusion Score", ascending=False).head(max_rows)


def render_fixed_dashboard_layout(
    dashboard_source,
    charts,
    output_profile,
    palette,
    translated_chart_summaries,
    translated_strategic_insights,
    is_invalid_query,
    style_chart,
):
    dashboard_title = str(st.session_state.get("last_user_query", "")).strip()
    if not dashboard_title:
        dashboard_title = f"{output_profile} Dashboard"
    is_dark = str(st.session_state.get("theme_mode", "Light")).lower() == "dark"
    heading_color = "#f8fafc" if is_dark else "#0f172a"
    subtitle_color = "#cbd5e1" if is_dark else "#334155"
    title_box_bg = (
        "linear-gradient(180deg, rgba(30,41,59,0.92) 0%, rgba(15,23,42,0.88) 100%)"
        if is_dark
        else "linear-gradient(180deg, rgba(255,255,255,0.88) 0%, rgba(255,255,255,0.68) 100%)"
    )

    st.markdown(
        f"""
        <div style="
            width: 100%;
            border: 1.5px solid rgba(148,163,184,0.42);
            border-radius: 18px;
            padding: 16px 24px;
            margin-bottom: 18px;
            text-align: center;
            background: {title_box_bg};
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.10);
        ">
            <div style="font-size: 1.45rem; font-weight: 800; color: {heading_color};">{html.escape(dashboard_title)}</div>
            <div style="font-size: 0.88rem; margin-top: 6px; opacity: 0.92; color: {subtitle_color};">Dashboard Name</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    row1_col1, row1_col2, row1_col3 = st.columns([1, 1, 0.9], gap="large")
    with row1_col1:
        st.markdown('<div class="section-panel">', unsafe_allow_html=True)
        st.subheader("Chart 1")
        if charts["bar"] is not None:
            st.plotly_chart(style_chart(charts["bar"], output_profile), use_container_width=True)
        else:
            st.info("Chart 1 is not available.")
        st.markdown("</div>", unsafe_allow_html=True)
    with row1_col2:
        st.markdown('<div class="section-panel">', unsafe_allow_html=True)
        st.subheader("Chart 2")
        if charts["line"] is not None:
            styled_line = style_chart(charts["line"], output_profile)
            styled_line.update_traces(line=dict(color=palette["line"], width=3))
            st.plotly_chart(styled_line, use_container_width=True)
        else:
            st.info("Chart 2 is not available.")
        st.markdown("</div>", unsafe_allow_html=True)
    with row1_col3:
        st.markdown('<div class="section-panel">', unsafe_allow_html=True)
        st.subheader("AI Summary (Short)")
        if is_invalid_query:
            st.warning("AI summary is blocked for invalid queries.")
        elif translated_chart_summaries:
            for item in translated_chart_summaries[:3]:
                st.markdown(f"- {item}")
        elif translated_strategic_insights:
            for item in translated_strategic_insights[:3]:
                st.markdown(f"- {item}")
        else:
            st.write("AI summary is unavailable right now.")
        st.markdown("</div>", unsafe_allow_html=True)

    row2_col1, row2_col2, row2_col3 = st.columns([1, 1, 0.9], gap="large")
    with row2_col1:
        st.markdown('<div class="section-panel">', unsafe_allow_html=True)
        st.subheader("Chart 3")
        if charts["pie"] is not None:
            styled_pie = style_chart(charts["pie"], output_profile)
            styled_pie.update_traces(marker=dict(colors=palette["pie"]))
            st.plotly_chart(styled_pie, use_container_width=True)
        else:
            st.info("Chart 3 is not available.")
        st.markdown("</div>", unsafe_allow_html=True)
    with row2_col2:
        st.markdown('<div class="section-panel">', unsafe_allow_html=True)
        st.subheader("Chart 4")
        if charts["scatter"] is not None:
            styled_scatter = style_chart(charts["scatter"], output_profile)
            styled_scatter.update_traces(
                marker=dict(color=palette["primary"], size=10, opacity=0.8)
            )
            st.plotly_chart(styled_scatter, use_container_width=True)
        else:
            st.info("Chart 4 is not available.")
        st.markdown("</div>", unsafe_allow_html=True)
    with row2_col3:
        st.markdown('<div class="section-panel">', unsafe_allow_html=True)
        st.subheader("Heat Map")
        heatmap = build_correlation_heatmap(dashboard_source)
        if heatmap is not None:
            st.plotly_chart(style_chart(heatmap, output_profile), use_container_width=True)
        else:
            st.info("Heat map is unavailable (need at least 2 numeric columns).")
        st.markdown("</div>", unsafe_allow_html=True)

    row3_col1, row3_col2 = st.columns([1.5, 0.95], gap="large")
    with row3_col1:
        st.markdown('<div class="section-panel">', unsafe_allow_html=True)
        st.subheader("Extracted Table")
        st.dataframe(dashboard_source.head(100), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with row3_col2:
        st.markdown('<div class="section-panel">', unsafe_allow_html=True)
        st.subheader("Confusing Metrics")
        confusing_metrics = build_confusing_metrics(dashboard_source)
        if confusing_metrics.empty:
            st.info("Confusing metrics are unavailable (no numeric columns found).")
        else:
            st.dataframe(confusing_metrics, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-panel">', unsafe_allow_html=True)
    st.subheader("AI Insights")
    if is_invalid_query:
        st.warning("AI insights are blocked for invalid queries.")
    elif translated_strategic_insights:
        for insight in translated_strategic_insights[:8]:
            st.markdown(f"- {insight}")
    else:
        st.write("AI insights are unavailable right now.")
    st.markdown("</div>", unsafe_allow_html=True)


def reset_analysis_chat(chat_key):
    if st.session_state.get("analysis_chat_key") != chat_key:
        st.session_state.analysis_chat_key = chat_key
        st.session_state.analysis_chat_history = []


def render_analysis_chatbot(
    df,
    chart_explanations,
    strategic_insights,
    chart_summaries,
    language_code,
    language_name,
):
    st.markdown('<div class="section-panel">', unsafe_allow_html=True)
    st.subheader("Chatbot")
    st.caption("Ask about trend, profit, segments, correlation, or the overall conclusion.")

    history = st.session_state.get("analysis_chat_history", [])
    if history:
        for item in history[-4:]:
            st.markdown(f"**You:** {item['question']}")
            st.write(item["answer"])
    else:
        st.write(
            bilingual_text(
                "I can answer questions from the current dashboard analysis.",
                language_code,
                language_name,
            )
        )

    with st.form("analysis_chat_form", clear_on_submit=True):
        chat_question = st.text_input(
            "Ask the chatbot",
            key="analysis_chat_input",
            placeholder="What is the profit outlook?",
        )
        ask_clicked = st.form_submit_button("Ask", type="primary")

    if ask_clicked and chat_question.strip():
        raw_answer = answer_analysis_question(
            chat_question.strip(),
            df,
            chart_explanations=chart_explanations,
            strategic_insights=strategic_insights,
            chart_summaries=chart_summaries,
        )
        localized_answer = bilingual_text(raw_answer, language_code, language_name)
        st.session_state.analysis_chat_history.append(
            {"question": chat_question.strip(), "answer": localized_answer}
        )
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def reset_filters():
    keys = [
        k
        for k in st.session_state.keys()
        if k.startswith("flt_cat_") or k.startswith("flt_num_") or k.startswith("flt_num_enable_")
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


def get_output_analysis_bundle(dashboard_source, sql):
    analysis_frame = prepare_analysis_frame(dashboard_source)
    cache_key = _result_signature(analysis_frame.head(200), sql)
    cached_bundle = st.session_state.get("output_analysis_cache", {})
    if cached_bundle.get("key") == cache_key:
        return cached_bundle

    chart_explanations = explain_all_charts(analysis_frame)
    chart_summaries = summarize_all_charts(chart_explanations)
    trend_insights = generate_trend_insights(analysis_frame)
    strategic_insights = generate_strategic_insights(analysis_frame)
    last_explanation = (
        " ".join(strategic_insights or trend_insights)
        if (strategic_insights or trend_insights)
        else "Explanation is unavailable right now."
    )
    bundle = {
        "key": cache_key,
        "chart_explanations": chart_explanations,
        "chart_summaries": chart_summaries,
        "trend_insights": trend_insights,
        "strategic_insights": strategic_insights,
        "last_explanation": last_explanation,
    }
    st.session_state.output_analysis_cache = bundle
    return bundle


def get_cached_dashboard_charts(dashboard_source, sql):
    cache_key = _result_signature(dashboard_source.head(200), sql)
    cached_bundle = st.session_state.get("dashboard_chart_cache", {})
    if cached_bundle.get("key") == cache_key:
        return cached_bundle.get("charts", {})

    charts = build_dashboard_charts(dashboard_source)
    st.session_state.dashboard_chart_cache = {"key": cache_key, "charts": charts}
    return charts


def get_cached_schema(df, rename_map, cache_name):
    cache_key = _result_signature(df.head(200), cache_name)
    schema_cache = st.session_state.get("schema_cache", {})
    if cache_name in schema_cache and schema_cache[cache_name].get("key") == cache_key:
        return schema_cache[cache_name].get("schema", {})

    schema = analyze_dataset(df, rename_map)
    schema_cache[cache_name] = {"key": cache_key, "schema": schema}
    st.session_state.schema_cache = schema_cache
    return schema


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


def render_user_prompt_panel(user_query):
    prompt_text = str(user_query or "").strip()
    if not prompt_text:
        return
    st.markdown('<div class="section-panel">', unsafe_allow_html=True)
    st.subheader("Input Prompt")
    st.caption("Original question used to generate this output")
    st.code(prompt_text)
    st.markdown("</div>", unsafe_allow_html=True)


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

if "last_query_invalid" not in st.session_state:
    st.session_state.last_query_invalid = False

if "last_invalid_message" not in st.session_state:
    st.session_state.last_invalid_message = ""

if "last_user_language_code" not in st.session_state:
    st.session_state.last_user_language_code = "en"

if "last_user_language_name" not in st.session_state:
    st.session_state.last_user_language_name = "English"

if "analysis_chat_history" not in st.session_state:
    st.session_state.analysis_chat_history = []

if "analysis_chat_key" not in st.session_state:
    st.session_state.analysis_chat_key = ""

if "page_notice" not in st.session_state:
    st.session_state.page_notice = ""

if "uploaded_datasets" not in st.session_state:
    st.session_state.uploaded_datasets = {}

if "active_dataset_name" not in st.session_state:
    st.session_state.active_dataset_name = "Default dataset"

if "output_analysis_cache" not in st.session_state:
    st.session_state.output_analysis_cache = {}

if "dashboard_chart_cache" not in st.session_state:
    st.session_state.dashboard_chart_cache = {}

if "schema_cache" not in st.session_state:
    st.session_state.schema_cache = {}

current_page = get_current_page()
uploaded_files = []
if current_page == "Input":
    uploaded_files = st.file_uploader(
        "Drag-drop dashboard builder: upload one or more datasets",
        key="dataset_uploader",
        accept_multiple_files=True,
    )
    if uploaded_files:
        sync_uploaded_datasets(uploaded_files)

df = None
encoding_used = None
had_replacements = False
dataset_label = None

(dataset_load, dataset_label, using_uploaded_dataset) = current_dataset_payload()
df, encoding_used, had_replacements = dataset_load

if df is not None:
    df, rename_map = normalize_columns(df)

    if current_page == "Input":
        st.markdown(
            '<p class="hero-subtitle">Automatic Dashboard Builder prompt: '
            '<code>Create a customer behavior dashboard</code></p>',
            unsafe_allow_html=True,
        )

        if using_uploaded_dataset:
            st.success(f"Using uploaded dataset: `{dataset_label}`")
        else:
            st.info(
                "No dataset uploaded. Running queries against the default dataset "
                f"`{dataset_label}`."
            )

    if had_replacements:
        st.warning("File contained invalid UTF-8 bytes. Loaded with replacement characters.")

    if any(str(k) != str(v) for k, v in rename_map.items()):
        with st.expander("Column mapping", expanded=False):
            mapping_df = pd.DataFrame(
                {
                    "original_column": [str(k) for k in rename_map.keys()],
                    "normalized_column": [str(v) for v in rename_map.values()],
                }
            )
            st.dataframe(mapping_df, use_container_width=True)

    filtered_df = df.copy()
    schema = get_cached_schema(filtered_df, rename_map, "input_page")
    profile_name, profile_reason = infer_dashboard_profile(filtered_df, schema)
    page_options = ["Input", "Output", "Download"]
    if st.session_state.get("page_nav_radio") != current_page:
        st.session_state.page_nav_radio = current_page

    with st.sidebar:
        st.subheader("Navigation")
        dataset_options = available_dataset_options()
        if st.session_state.active_dataset_name not in dataset_options:
            st.session_state.active_dataset_name = dataset_options[0]
        st.selectbox(
            "Active Dataset",
            options=dataset_options,
            key="active_dataset_name",
        )
        selected_page = st.radio(
            "Page",
            options=page_options,
            index=page_options.index(current_page) if current_page in page_options else 0,
            key="page_nav_radio",
        )
        if selected_page != current_page:
            set_current_page(selected_page)
            st.rerun()
        st.caption(f"Recommended layout: `{profile_name}`")
        st.caption(profile_reason)
        st.caption("Chat History")
        if not st.session_state.chat_history:
            st.info("No chat history yet.")
        else:
            for item in reversed(st.session_state.chat_history[-8:]):
                st.markdown(f"**Q:** {item['question']}")
                st.caption(f"{item['query_type']} | {item['source']}")

    render_top_page_nav(current_page)

    if current_page == "Input":
        if st.session_state.page_notice:
            st.warning(st.session_state.page_notice)
            st.session_state.page_notice = ""
        question = None

        st.markdown(
            f"""
            <div class="section-panel">
                <h3>Enterprise Workspace</h3>
                <div class="process-copy">Multi-dataset support is active. Pick an active dataset from the sidebar, then ask a business question to generate an executive dashboard.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
        schema = get_cached_schema(filtered_df, rename_map, "input_filters")
        profile_name, profile_reason = infer_dashboard_profile(filtered_df, schema)

        render_dataset_profile(schema)
        render_nl_sql_panel()

        st.markdown('<div class="section-panel">', unsafe_allow_html=True)
        st.subheader("Dataset Preview")
        st.caption(f"Best dashboard style for this data: `{profile_name}`")
        st.dataframe(filtered_df.head(8), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-panel">', unsafe_allow_html=True)
        st.subheader("Dashboard Generator")

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

        if run_clicked and st.session_state.input_question.strip():
            question = st.session_state.input_question.strip()

        dashboard_source = filtered_df.head(500)
        if question:
            st.session_state.last_user_query = question
            detected_lang_code, detected_lang_name = detect_input_language(question)
            st.session_state.last_user_language_code = detected_lang_code
            st.session_state.last_user_language_name = detected_lang_name
            processed_question = translate_question_to_english(
                question,
                detected_lang_code,
                detected_lang_name,
            ).strip() or question
            auto_dashboard = (
                "create" in processed_question.lower()
                and "dashboard" in processed_question.lower()
            )
            if not auto_dashboard:
                is_valid_query, invalid_message = validate_question_columns(
                    processed_question,
                    filtered_df,
                    schema.get("column_aliases", {}),
                    query_language="en",
                )
                if is_valid_query:
                    result, sql, q_type, q_source = run_query(
                        filtered_df,
                        schema,
                        processed_question,
                    )
                    st.session_state.last_result = result
                    st.session_state.last_sql = sql
                    st.session_state.last_query_type = q_type
                    st.session_state.last_query_source = q_source
                    st.session_state.last_query_invalid = False
                    st.session_state.last_invalid_message = ""
                else:
                    st.session_state.last_result = None
                    st.session_state.last_sql = "-- INVALID QUERY --"
                    st.session_state.last_query_type = "invalid"
                    st.session_state.last_query_source = "validation"
                    st.session_state.last_query_invalid = True
                    st.session_state.last_invalid_message = invalid_message
            else:
                st.session_state.last_result = dashboard_source
                st.session_state.last_sql = "SELECT * FROM dataframe LIMIT 500"
                st.session_state.last_query_type = "dashboard"
                st.session_state.last_query_source = "auto_dashboard"
                st.session_state.last_query_invalid = False
                st.session_state.last_invalid_message = ""

            st.session_state.chat_history.append(
                {
                    "question": question,
                    "query_type": st.session_state.last_query_type,
                    "source": st.session_state.last_query_source,
                }
            )
            set_current_page("Output")
            st.rerun()

        st.info("Enter a prompt and run query. App will auto-open the Output page.")

    elif current_page == "Output":
        dashboard_source = df.head(500)
        query_entered = bool(str(st.session_state.last_user_query).strip())
        if not query_entered:
            st.session_state.page_notice = "Run a prompt from Input first, then the app will open Output automatically."
            set_current_page("Input")
            st.rerun()
        else:
            if st.session_state.last_result is not None:
                dashboard_source = st.session_state.last_result
            output_filter_config = None
            if st.session_state.last_query_type == "dashboard":
                output_filter_config = detect_output_filter_config(dashboard_source)
                output_filter_context = _result_signature(
                    dashboard_source.head(200), st.session_state.last_sql
                )
                sync_output_filter_state(
                    st.session_state, output_filter_context, output_filter_config
                )
                dashboard_source = apply_output_filters(
                    dashboard_source, output_filter_config, st.session_state
                )

            output_schema = get_cached_schema(dashboard_source, rename_map, "output_page")
            output_profile, _ = infer_dashboard_profile(dashboard_source, output_schema)
            palette = _profile_palette(output_profile)

            if st.session_state.last_query_invalid:
                st.error(st.session_state.last_invalid_message or "Invalid query.")
                charts = {"bar": None, "line": None, "pie": None, "scatter": None}
            elif dashboard_source.empty:
                st.warning("No rows match the selected dashboard filters.")
                charts = {"bar": None, "line": None, "pie": None, "scatter": None}
            else:
                charts = get_cached_dashboard_charts(
                    dashboard_source, st.session_state.last_sql
                )
            if st.session_state.last_query_invalid:
                st.warning("AI insights are blocked for invalid queries.")
                st.session_state.last_explanation = "Invalid query: AI insights blocked."
                chart_explanations = {}
                chart_summaries = []
                trend_insights = []
                strategic_insights = []
                current_expl_key = _result_signature(dashboard_source.head(200), st.session_state.last_sql)
            elif dashboard_source.empty:
                chart_explanations = {}
                chart_summaries = []
                trend_insights = []
                strategic_insights = []
                st.session_state.last_explanation = "No rows match the selected dashboard filters."
                current_expl_key = _result_signature(dashboard_source.head(200), st.session_state.last_sql)
            else:
                analysis_bundle = get_output_analysis_bundle(
                    dashboard_source, st.session_state.last_sql
                )
                chart_explanations = analysis_bundle["chart_explanations"]
                chart_summaries = analysis_bundle["chart_summaries"]
                trend_insights = analysis_bundle["trend_insights"]
                strategic_insights = analysis_bundle["strategic_insights"]
                current_expl_key = analysis_bundle["key"]
                if st.session_state.last_explanation_key != current_expl_key:
                    st.session_state.last_explanation = analysis_bundle["last_explanation"]
                    st.session_state.last_explanation_key = current_expl_key
                elif not st.session_state.last_explanation:
                    st.session_state.last_explanation = analysis_bundle["last_explanation"]

            reset_analysis_chat(current_expl_key)
            translated_chart_summaries = bilingual_list(
                chart_summaries,
                st.session_state.last_user_language_code,
                st.session_state.last_user_language_name,
            )
            translated_strategic_insights = bilingual_list(
                strategic_insights or trend_insights,
                st.session_state.last_user_language_code,
                st.session_state.last_user_language_name,
            )

            render_user_prompt_panel(st.session_state.last_user_query)
            st.caption(f"Output style: `{output_profile}`")
            render_kpis(dashboard_source)
            render_fixed_dashboard_layout(
                dashboard_source=dashboard_source,
                charts=charts,
                output_profile=output_profile,
                palette=palette,
                translated_chart_summaries=translated_chart_summaries,
                translated_strategic_insights=translated_strategic_insights,
                is_invalid_query=st.session_state.last_query_invalid,
                style_chart=style_chart,
            )
            st.markdown('<div class="section-panel">', unsafe_allow_html=True)
            st.subheader("Download Output")
            render_download_actions(dashboard_source, charts, "output_bottom")
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        dashboard_source = df.head(500)
        query_entered = bool(str(st.session_state.last_user_query).strip())
        if not query_entered:
            st.session_state.page_notice = "Run a prompt from Input first to enable downloads."
            set_current_page("Input")
            st.rerun()
        else:
            if st.session_state.last_result is not None:
                dashboard_source = st.session_state.last_result
            if st.session_state.last_query_invalid:
                charts = {"bar": None, "line": None, "pie": None, "scatter": None}
            else:
                charts = get_cached_dashboard_charts(
                    dashboard_source, st.session_state.last_sql
                )
            st.subheader("Generated SQL")
            st.code(st.session_state.last_sql)
            st.subheader("Download Dashboard With Result")
            render_download_actions(dashboard_source, charts, "download_page")
            st.dataframe(dashboard_source.head(100), use_container_width=True)
else:
    st.warning(
        "Upload a dataset or place the default customer behaviour CSV at "
        f"`{DEFAULT_DATASET_PATH}` to run queries."
    )

