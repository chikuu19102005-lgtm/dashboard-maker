import pandas as pd
import plotly.express as px


PREFERRED_CATEGORY_COLUMNS = [
    "shopping_preference",
    "city_tier",
    "gender",
]

PREFERRED_NUMERIC_COLUMNS = [
    "monthly_income",
    "avg_online_spend",
    "avg_store_spend",
    "daily_internet_hours",
    "social_media_hours",
    "monthly_online_orders",
    "monthly_store_visits",
    "online_payment_trust_score",
    "tech_savvy_score",
]


def _pick_category_column(df):
    category_cols = list(df.select_dtypes(include=["object", "category"]).columns)
    for col in PREFERRED_CATEGORY_COLUMNS:
        if col in category_cols and 2 <= df[col].nunique(dropna=True) <= 12:
            return col
    for col in category_cols:
        uniq = df[col].nunique(dropna=True)
        if 2 <= uniq <= 12:
            return col
    return None


def _rank_numeric_columns(df):
    numeric_cols = []
    for col in df.select_dtypes(include="number").columns:
        series = df[col].dropna()
        if series.empty or series.nunique() <= 1:
            continue
        score = 0
        if col in PREFERRED_NUMERIC_COLUMNS:
            score += 100 - PREFERRED_NUMERIC_COLUMNS.index(col)
        score += min(int(series.std()), 50)
        if series.nunique() < len(series) * 0.95:
            score += 10
        numeric_cols.append((score, col))
    numeric_cols.sort(reverse=True)
    return [col for _, col in numeric_cols]


def _top_categories(series, top_n=8):
    counts = series.fillna("Unknown").astype(str).value_counts().head(top_n).reset_index()
    counts.columns = ["category", "count"]
    return counts


def _grouped_mean(df, category_col, value_col, top_n=8):
    grouped = (
        df.groupby(category_col, dropna=False)[value_col]
        .mean()
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index()
    )
    grouped[category_col] = grouped[category_col].fillna("Unknown").astype(str)
    return grouped


def _grouped_multi_metric(df, category_col, value_cols, top_n=8):
    grouped = (
        df.groupby(category_col, dropna=False)[value_cols]
        .mean()
        .sort_values(by=value_cols[0], ascending=False)
        .head(top_n)
        .reset_index()
    )
    grouped[category_col] = grouped[category_col].fillna("Unknown").astype(str)
    return grouped


def _best_scatter_pair(df, numeric_cols):
    if len(numeric_cols) < 2:
        return None
    corr = df[numeric_cols].corr(numeric_only=True).abs()
    best_pair = None
    best_score = -1.0
    for i, left in enumerate(numeric_cols):
        for right in numeric_cols[i + 1 :]:
            score = corr.loc[left, right]
            if pd.isna(score):
                continue
            if score > best_score:
                best_score = score
                best_pair = (left, right)
    if best_pair:
        return best_pair
    return tuple(numeric_cols[:2])


def _fallback_numeric_columns(df):
    return list(df.select_dtypes(include="number").columns)


def create_charts(df, question="", chart_style="auto", query_type="table"):
    charts = []
    dashboard_charts = build_dashboard_charts(df)
    for key in ("bar", "line", "pie", "scatter"):
        fig = dashboard_charts.get(key)
        if fig is not None:
            charts.append(fig)
    return charts


def build_dashboard_charts(df):
    if df.empty:
        return {"bar": None, "line": None, "pie": None, "scatter": None}

    data = df.copy().reset_index(drop=True)
    category_col = _pick_category_column(data)
    numeric_cols = _rank_numeric_columns(data)
    all_numeric_cols = _fallback_numeric_columns(data)
    if not numeric_cols and all_numeric_cols:
        numeric_cols = all_numeric_cols[:]

    bar_fig = None
    if category_col and numeric_cols:
        grouped_bar = _grouped_mean(data, category_col, numeric_cols[0])
        bar_fig = px.bar(
            grouped_bar,
            x=category_col,
            y=numeric_cols[0],
            color=category_col,
            title=f"Average {numeric_cols[0].replace('_', ' ')} by {category_col.replace('_', ' ')}",
        )
    elif category_col:
        counts = _top_categories(data[category_col])
        bar_fig = px.bar(
            counts,
            x="category",
            y="count",
            color="category",
            title=f"{category_col.replace('_', ' ')} counts",
        )
    elif numeric_cols:
        top_values = data[numeric_cols[0]].dropna().head(25).reset_index(drop=True)
        bar_df = top_values.reset_index()
        bar_df.columns = ["row_id", numeric_cols[0]]
        bar_fig = px.bar(
            bar_df,
            x="row_id",
            y=numeric_cols[0],
            title=f"{numeric_cols[0].replace('_', ' ')} sample values",
        )

    line_fig = None
    if category_col and len(numeric_cols) >= 2:
        line_df = _grouped_multi_metric(data, category_col, numeric_cols[:2])
        melted = line_df.melt(
            id_vars=category_col, var_name="metric", value_name="value"
        )
        line_fig = px.line(
            melted,
            x=category_col,
            y="value",
            color="metric",
            markers=True,
            title=f"{numeric_cols[0].replace('_', ' ')} vs {numeric_cols[1].replace('_', ' ')} by {category_col.replace('_', ' ')}",
        )
    elif category_col and numeric_cols:
        line_df = _grouped_mean(data, category_col, numeric_cols[0])
        line_fig = px.line(
            line_df,
            x=category_col,
            y=numeric_cols[0],
            markers=True,
            title=f"{numeric_cols[0].replace('_', ' ')} by {category_col.replace('_', ' ')}",
        )
    elif category_col:
        counts = _top_categories(data[category_col])
        line_fig = px.line(
            counts,
            x="category",
            y="count",
            markers=True,
            title=f"{category_col.replace('_', ' ')} counts",
        )
    elif numeric_cols:
        line_df = data[numeric_cols[:1]].dropna().head(150).copy()
        line_df["row_id"] = range(1, len(line_df) + 1)
        line_fig = px.line(
            line_df,
            x="row_id",
            y=numeric_cols[0],
            title=f"{numeric_cols[0].replace('_', ' ')} trend across records",
        )

    pie_fig = None
    if category_col:
        counts = _top_categories(data[category_col])
        pie_fig = px.pie(
            counts,
            names="category",
            values="count",
            title=f"{category_col.replace('_', ' ')} distribution",
        )
    elif numeric_cols:
        series = data[numeric_cols[0]].dropna()
        if len(series) >= 2 and series.nunique() > 1:
            bucketed = pd.cut(series, bins=5, duplicates="drop").astype(str)
            counts = bucketed.value_counts().reset_index()
            counts.columns = ["category", "count"]
        else:
            value = float(series.iloc[0]) if len(series) else 0.0
            counts = pd.DataFrame(
                {
                    "category": [numeric_cols[0].replace("_", " ")],
                    "count": [value if value > 0 else 1.0],
                }
            )
        pie_fig = px.pie(
            counts,
            names="category",
            values="count",
            title=f"{numeric_cols[0].replace('_', ' ')} distribution",
        )

    scatter_fig = None
    scatter_pair = _best_scatter_pair(data, numeric_cols)
    if scatter_pair:
        left, right = scatter_pair
        scatter_kwargs = {
            "x": left,
            "y": right,
            "title": f"{left.replace('_', ' ')} vs {right.replace('_', ' ')}",
        }
        if category_col:
            scatter_kwargs["color"] = category_col
        scatter_fig = px.scatter(data, **scatter_kwargs)
    elif numeric_cols:
        scatter_df = data[[numeric_cols[0]]].dropna().head(150).copy()
        scatter_df["row_id"] = range(1, len(scatter_df) + 1)
        scatter_fig = px.scatter(
            scatter_df,
            x="row_id",
            y=numeric_cols[0],
            title=f"{numeric_cols[0].replace('_', ' ')} across records",
        )
    elif category_col:
        counts = _top_categories(data[category_col])
        counts["row_id"] = range(1, len(counts) + 1)
        scatter_fig = px.scatter(
            counts,
            x="row_id",
            y="count",
            color="category",
            title=f"{category_col.replace('_', ' ')} counts",
        )

    return {"bar": bar_fig, "line": line_fig, "pie": pie_fig, "scatter": scatter_fig}
