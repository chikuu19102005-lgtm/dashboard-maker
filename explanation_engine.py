import os

import pandas as pd
import requests

from chart_ai import _best_scatter_pair, _pick_category_column, _rank_numeric_columns


OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_CONNECT_TIMEOUT = float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "1.5"))
OLLAMA_READ_TIMEOUT = float(os.getenv("OLLAMA_READ_TIMEOUT", "8"))
ENABLE_OLLAMA_EXPLANATION = os.getenv("ENABLE_OLLAMA_EXPLANATION", "0") == "1"


def _limit_words(text, max_words=70):
    words = (text or "").split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(".,;:") + "."


def _fmt_number(value):
    if pd.isna(value):
        return "N/A"
    if abs(float(value)) >= 1000:
        return f"{float(value):,.0f}"
    return f"{float(value):,.2f}"


def prepare_analysis_frame(df, limit=1000):
    if df is None or df.empty:
        return df
    if len(df) <= limit:
        return df.copy()
    return df.head(limit).copy()


def generate_trend_insights(df, max_items=4):
    insights = []
    if df is None or df.empty:
        return insights

    working_df = df.copy()
    numeric_cols = list(working_df.select_dtypes(include="number").columns)
    category_cols = list(working_df.select_dtypes(include=["object", "category"]).columns)

    if "shopping_preference" in working_df.columns:
        pref_counts = working_df["shopping_preference"].fillna("Unknown").value_counts()
        top_pref = pref_counts.index[0]
        top_share = pref_counts.iloc[0] / max(len(working_df), 1) * 100
        insights.append(
            f"{top_pref} is the dominant shopping preference, accounting for {top_share:.1f}% of records."
        )

    if {"avg_online_spend", "avg_store_spend"}.issubset(working_df.columns):
        online_avg = working_df["avg_online_spend"].mean()
        store_avg = working_df["avg_store_spend"].mean()
        stronger = "store" if store_avg > online_avg else "online"
        gap = abs(store_avg - online_avg)
        insights.append(
            f"Average {stronger} spend is higher by {_fmt_number(gap)} per customer "
            f"({_fmt_number(online_avg)} online vs {_fmt_number(store_avg)} in store)."
        )

    if {"monthly_online_orders", "monthly_store_visits"}.issubset(working_df.columns):
        avg_orders = working_df["monthly_online_orders"].mean()
        avg_visits = working_df["monthly_store_visits"].mean()
        insights.append(
            f"Customers average {_fmt_number(avg_orders)} online orders and {_fmt_number(avg_visits)} store visits each month."
        )

    if {"shopping_preference", "monthly_income"}.issubset(working_df.columns):
        income_by_pref = (
            working_df.groupby("shopping_preference")["monthly_income"]
            .mean()
            .sort_values(ascending=False)
        )
        if not income_by_pref.empty:
            top_segment = income_by_pref.index[0]
            top_income = income_by_pref.iloc[0]
            insights.append(
                f"{top_segment} shoppers have the highest average monthly income at {_fmt_number(top_income)}."
            )

    if len(numeric_cols) >= 2:
        corr = working_df[numeric_cols].corr(numeric_only=True)
        best_pair = None
        best_score = 0.0
        for i, left in enumerate(numeric_cols):
            for right in numeric_cols[i + 1 :]:
                score = corr.loc[left, right]
                if pd.isna(score):
                    continue
                if abs(score) > abs(best_score):
                    best_score = score
                    best_pair = (left, right)
        if best_pair and abs(best_score) >= 0.25:
            relation = "positive" if best_score > 0 else "negative"
            insights.append(
                f"The strongest {relation} relationship is between "
                f"{best_pair[0].replace('_', ' ')} and {best_pair[1].replace('_', ' ')} "
                f"(correlation {best_score:.2f})."
            )

    if not insights and category_cols:
        lead_col = category_cols[0]
        counts = working_df[lead_col].fillna("Unknown").value_counts()
        insights.append(
            f"{counts.index[0]} is the largest group in {lead_col.replace('_', ' ')}, with {counts.iloc[0]} records."
        )

    return insights[:max_items]


def _fallback_explanation(df):
    insights = generate_trend_insights(df, max_items=3)
    if not insights:
        return "The dataset loaded successfully, but there is not enough variation to generate a useful summary."
    return " ".join(insights)


def explain_all_charts(df):
    if df is None or df.empty:
        return {}

    working_df = prepare_analysis_frame(df)
    category_col = _pick_category_column(working_df)
    numeric_cols = _rank_numeric_columns(working_df)
    explanations = {}

    if category_col and numeric_cols:
        grouped = (
            working_df.groupby(category_col, dropna=False)[numeric_cols[0]]
            .mean()
            .sort_values(ascending=False)
        )
        if not grouped.empty:
            top_name = str(grouped.index[0])
            top_value = grouped.iloc[0]
            explanations["bar"] = (
                f"{top_name} has the highest average "
                f"{numeric_cols[0].replace('_', ' ')} at {_fmt_number(top_value)}."
            )
    elif numeric_cols:
        peak = working_df[numeric_cols[0]].max()
        explanations["bar"] = (
            f"The sampled records peak at {_fmt_number(peak)} for "
            f"{numeric_cols[0].replace('_', ' ')}."
        )
    else:
        explanations["bar"] = "Not enough numeric data to describe the bar chart."

    if category_col and len(numeric_cols) >= 2:
        grouped = (
            working_df.groupby(category_col, dropna=False)[numeric_cols[:2]]
            .mean()
            .sort_values(by=numeric_cols[0], ascending=False)
        )
        if not grouped.empty:
            lead_name = str(grouped.index[0])
            explanations["line"] = (
                f"{lead_name} leads on both "
                f"{numeric_cols[0].replace('_', ' ')} and {numeric_cols[1].replace('_', ' ')} "
                f"with averages of {_fmt_number(grouped.iloc[0][numeric_cols[0]])} and "
                f"{_fmt_number(grouped.iloc[0][numeric_cols[1]])}."
            )
    elif numeric_cols:
        explanations["line"] = (
            f"It shows how {numeric_cols[0].replace('_', ' ')} changes across the returned records."
        )
    else:
        explanations["line"] = "Not enough numeric data to describe the line chart."

    if category_col:
        counts = working_df[category_col].fillna("Unknown").astype(str).value_counts()
        if not counts.empty:
            share = counts.iloc[0] / max(len(working_df), 1) * 100
            explanations["pie"] = (
                f"{counts.index[0]} is the largest {category_col.replace('_', ' ')} segment "
                f"at {share:.1f}% of the result."
            )
    elif numeric_cols:
        explanations["pie"] = (
            f"It shows the distribution of {numeric_cols[0].replace('_', ' ')} across value ranges."
        )
    else:
        explanations["pie"] = "Not enough categorical or numeric data to describe the pie chart."

    scatter_pair = _best_scatter_pair(working_df, numeric_cols)
    if scatter_pair:
        left, right = scatter_pair
        corr = working_df[[left, right]].corr(numeric_only=True).iloc[0, 1]
        relation = "positive" if corr >= 0 else "negative"
        explanations["scatter"] = (
            f"{left.replace('_', ' ')} and {right.replace('_', ' ')} have a "
            f"{relation} relationship with correlation {corr:.2f}."
        )
    else:
        explanations["scatter"] = "Not enough numeric data to describe the scatter chart."

    return explanations


def explain_data(df):
    fallback_summary = _fallback_explanation(df)
    if not ENABLE_OLLAMA_EXPLANATION:
        return fallback_summary

    preview = df.head(10).to_string()

    prompt = f"""
You are a business analyst.

Explain the key insights from this data.

{preview}

Write exactly one short paragraph.
Keep it about 70 words.
Use simple language.
"""

    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=(OLLAMA_CONNECT_TIMEOUT, OLLAMA_READ_TIMEOUT),
        )
        response.raise_for_status()
        text = response.json().get("response", "").strip()
        if text:
            return _limit_words(text, max_words=70)
    except requests.exceptions.Timeout:
        pass
    except requests.RequestException:
        pass

    return fallback_summary
