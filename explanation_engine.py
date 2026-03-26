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


def _nice_name(name):
    return str(name).replace("_", " ")


def _primary_numeric_metric(df):
    if df is None or df.empty:
        return None
    preferred = [
        "profit",
        "revenue",
        "sales",
        "income",
        "spend",
        "balance",
        "amount",
        "orders",
    ]
    numeric_cols = list(df.select_dtypes(include="number").columns)
    lowered = {str(col).lower(): col for col in numeric_cols}
    for token in preferred:
        for lower_name, original in lowered.items():
            if token in lower_name:
                return original
    return numeric_cols[0] if numeric_cols else None


def _trend_signal(series):
    values = pd.Series(series).dropna().reset_index(drop=True)
    if len(values) < 3:
        return None
    window = max(1, len(values) // 3)
    start_avg = values.head(window).mean()
    end_avg = values.tail(window).mean()
    delta = end_avg - start_avg
    if abs(float(delta)) < 1e-9:
        return "stable", delta
    return ("up" if delta > 0 else "down"), delta


def _estimate_profit_series(df):
    if df is None or df.empty:
        return None, None
    numeric_cols = list(df.select_dtypes(include="number").columns)
    if not numeric_cols:
        return None, None

    revenue_col = next((c for c in numeric_cols if any(k in str(c).lower() for k in ["revenue", "sales", "income"])), None)
    cost_col = next((c for c in numeric_cols if any(k in str(c).lower() for k in ["cost", "expense", "spend", "cogs"])), None)
    profit_col = next((c for c in numeric_cols if "profit" in str(c).lower()), None)

    if profit_col:
        return df[profit_col], profit_col
    if revenue_col and cost_col:
        return df[revenue_col] - df[cost_col], f"{revenue_col}_minus_{cost_col}"
    return None, None


def _grounded_profit_answer(df):
    profit_series, profit_name = _estimate_profit_series(df)
    if profit_series is None or profit_series.dropna().empty:
        return (
            "Profit cannot be calculated from the current result because there is no "
            "profit column and no revenue-cost combination available to estimate it."
        )

    clean_profit = profit_series.dropna()
    source_text = (
        "from the profit field"
        if profit_name and "_minus_" not in str(profit_name)
        else "estimated from revenue minus cost"
    )
    answer = (
        f"Based on the current result, average profit is {_fmt_number(clean_profit.mean())} "
        f"{source_text}."
    )
    profit_signal = _trend_signal(clean_profit)
    if profit_signal:
        direction, delta = profit_signal
        if direction == "up":
            answer += f" The recent sample is trending up by about {_fmt_number(delta)}."
        elif direction == "down":
            answer += f" The recent sample is trending down by about {_fmt_number(abs(delta))}."
        else:
            answer += " The recent sample looks stable."
    return answer


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


def summarize_all_charts(chart_explanations):
    if not chart_explanations:
        return []
    labels = {
        "bar": "Bar chart",
        "line": "Trend chart",
        "pie": "Distribution chart",
        "scatter": "Correlation chart",
    }
    summaries = []
    for key in ("bar", "line", "pie", "scatter"):
        text = chart_explanations.get(key)
        if text:
            summaries.append(f"{labels[key]}: {text}")
    return summaries


def answer_analysis_question(
    question,
    df,
    chart_explanations=None,
    strategic_insights=None,
    chart_summaries=None,
):
    prompt = (question or "").strip()
    if not prompt:
        return "Ask about trend, profit, segments, correlation, or the overall conclusion."

    chart_explanations = chart_explanations or {}
    strategic_insights = strategic_insights or []
    chart_summaries = chart_summaries or []
    lower = prompt.lower()

    if any(token in lower for token in ["overall", "summary", "conclusion", "overview"]):
        if strategic_insights:
            return strategic_insights[0]
        return _fallback_explanation(df)

    if any(token in lower for token in ["profit", "loss", "margin"]):
        return _grounded_profit_answer(df)

    if any(token in lower for token in ["trend", "growth", "future"]):
        trend_line = next((item for item in strategic_insights if "future trend" in item.lower()), None)
        if trend_line:
            return trend_line
        if chart_explanations.get("line"):
            return chart_explanations["line"]

    if any(token in lower for token in ["distribution", "segment", "category", "region", "share"]):
        if chart_explanations.get("pie"):
            return chart_explanations["pie"]
        if chart_explanations.get("bar"):
            return chart_explanations["bar"]

    if any(token in lower for token in ["correlation", "relationship", "compare", "vs"]):
        if chart_explanations.get("scatter"):
            return chart_explanations["scatter"]

    if any(token in lower for token in ["chart", "graph", "visual"]):
        why_line = next((item for item in strategic_insights if "why these charts:" in item.lower()), None)
        if why_line:
            return why_line

    response_parts = []
    if strategic_insights:
        response_parts.append(strategic_insights[0])
    if chart_summaries:
        response_parts.append(chart_summaries[0])
    if not response_parts and chart_explanations:
        response_parts.append(next(iter(chart_explanations.values())))
    if not response_parts:
        response_parts.append(_fallback_explanation(df))
    return " ".join(response_parts[:2])


def generate_strategic_insights(df):
    insights = []
    if df is None or df.empty:
        return insights

    metric = _primary_numeric_metric(df)
    category_cols = list(df.select_dtypes(include=["object", "category"]).columns)
    numeric_cols = list(df.select_dtypes(include="number").columns)

    if metric:
        metric_series = df[metric]
        signal = _trend_signal(metric_series)
        avg_metric = metric_series.dropna().mean() if not metric_series.dropna().empty else None
        if avg_metric is not None:
            insights.append(
                f"Overall conclusion: {_nice_name(metric).title()} is averaging {_fmt_number(avg_metric)} across the current result set."
            )
        if signal:
            direction, delta = signal
            if direction == "up":
                insights.append(
                    f"Future trend: recent values suggest {_nice_name(metric)} is gaining momentum, up by about {_fmt_number(delta)} versus the earlier portion of the sample."
                )
            elif direction == "down":
                insights.append(
                    f"Future trend: recent values suggest {_nice_name(metric)} is weakening, down by about {_fmt_number(abs(delta))} versus the earlier portion of the sample."
                )
            else:
                insights.append(
                    f"Future trend: {_nice_name(metric)} is currently stable with no strong directional signal in the sample."
                )

    profit_series, profit_name = _estimate_profit_series(df)
    if profit_series is not None:
        avg_profit = profit_series.dropna().mean() if not profit_series.dropna().empty else None
        profit_signal = _trend_signal(profit_series)
        if avg_profit is not None:
            direction_word = "profit" if avg_profit >= 0 else "loss"
            insights.append(
                f"Profit view: the current estimated {direction_word} level is {_fmt_number(avg_profit)}."
            )
        if profit_signal:
            direction, delta = profit_signal
            if direction == "up":
                insights.append(
                    f"Profit trend: the recent sample points to improving profit, up by about {_fmt_number(delta)}."
                )
            elif direction == "down":
                insights.append(
                    f"Profit trend: the recent sample points to weaker profit, down by about {_fmt_number(abs(delta))}."
                )
            else:
                insights.append(
                    "Profit trend: the current sample suggests a flat profit pattern."
                )
    elif numeric_cols:
        insights.append(
            "Profit view: profit cannot be calculated from the current result because no profit field or revenue-cost combination is available."
        )

    why_parts = []
    if category_cols:
        why_parts.append("distribution charts show segment mix")
    if metric:
        why_parts.append(f"trend charts track {_nice_name(metric)} movement")
    if len(numeric_cols) >= 2:
        why_parts.append("correlation charts reveal linked business drivers")
    if why_parts:
        insights.append(f"Why these charts: {'; '.join(why_parts)}.")

    return insights[:5]


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
