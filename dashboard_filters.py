import re

import pandas as pd


DATE_RANGE_KEY = "output_filter_date_range"
REGION_KEY = "output_filter_region"
PRODUCT_KEY = "output_filter_product"
CONTEXT_KEY = "output_filter_context"


def _candidate_columns(df, include):
    return list(df.select_dtypes(include=include).columns)


def _detect_date_column(df):
    for col in df.columns:
        col_name = str(col).lower()
        series = df[col]
        if pd.api.types.is_datetime64_any_dtype(series):
            return col
        if "date" in col_name or "time" in col_name:
            parsed = pd.to_datetime(series, errors="coerce")
            if parsed.notna().sum() >= max(3, int(len(series) * 0.4)):
                return col
        if "year" in col_name and pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()
            if not clean.empty and clean.between(1900, 2100).all():
                return col
    return None


def _detect_categorical_by_keywords(df, keywords, fallback=None):
    categorical = _candidate_columns(df, ["object", "category"])
    lowered = {str(col).lower(): col for col in categorical}
    for keyword in keywords:
        for name, col in lowered.items():
            if keyword in name:
                return col
    if fallback:
        for col in categorical:
            if col != fallback:
                return col
    return categorical[0] if categorical else None


def _select_options(series, all_label):
    values = (
        pd.Series(series)
        .dropna()
        .astype(str)
        .map(str.strip)
        .replace("", pd.NA)
        .dropna()
        .unique()
        .tolist()
    )
    values = sorted(values)
    return [all_label] + values[:50]


def build_date_options():
    options = ["All Dates", "Last 1 Day"]
    options.extend([f"Last {weeks} Week" if weeks == 1 else f"Last {weeks} Weeks" for weeks in range(1, 6)])
    options.extend([f"Last {months} Month" if months == 1 else f"Last {months} Months" for months in range(1, 13)])
    options.extend([f"Last {years} Year" if years == 1 else f"Last {years} Years" for years in range(1, 20)])
    deduped = []
    seen = set()
    for item in options:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def detect_output_filter_config(df):
    date_col = _detect_date_column(df)
    region_col = _detect_categorical_by_keywords(
        df,
        ["region", "country", "state", "city", "branch", "location", "area", "zone"],
    )
    product_col = _detect_categorical_by_keywords(
        df,
        ["product", "category", "segment", "shopping_preference", "preference", "type", "item"],
        fallback=region_col,
    )

    return {
        "date_column": date_col,
        "region_column": region_col,
        "product_column": product_col,
        "date_options": build_date_options() if date_col is not None else ["All Dates"],
        "region_options": _select_options(df[region_col], "All Regions") if region_col is not None else ["All Regions"],
        "product_options": _select_options(df[product_col], "All Categories") if product_col is not None else ["All Categories"],
    }


def sync_output_filter_state(state, context_key, filter_config):
    if state.get(CONTEXT_KEY) != context_key:
        state[CONTEXT_KEY] = context_key
        state[DATE_RANGE_KEY] = "All Dates"
        state[REGION_KEY] = "All Regions"
        state[PRODUCT_KEY] = "All Categories"

    if state.get(DATE_RANGE_KEY) not in filter_config["date_options"]:
        state[DATE_RANGE_KEY] = "All Dates"
    if state.get(REGION_KEY) not in filter_config["region_options"]:
        state[REGION_KEY] = "All Regions"
    if state.get(PRODUCT_KEY) not in filter_config["product_options"]:
        state[PRODUCT_KEY] = "All Categories"


def _coerce_datetime(series, column_name):
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")
    if "year" in str(column_name).lower() and pd.api.types.is_numeric_dtype(series):
        return pd.to_datetime(series.astype("Int64").astype(str), format="%Y", errors="coerce")
    return pd.to_datetime(series, errors="coerce")


def _apply_date_range(df, column_name, range_value):
    if not column_name or range_value == "All Dates":
        return df

    parsed = _coerce_datetime(df[column_name], column_name)
    if parsed.notna().sum() == 0:
        return df

    match = re.match(r"Last (\d+) (Day|Days|Week|Weeks|Month|Months|Year|Years)", str(range_value))
    if not match:
        return df

    count = int(match.group(1))
    unit = match.group(2).lower()
    max_date = parsed.max()
    if pd.isna(max_date):
        return df

    if "day" in unit:
        start = max_date - pd.Timedelta(days=count)
    elif "week" in unit:
        start = max_date - pd.Timedelta(weeks=count)
    elif "month" in unit:
        start = max_date - pd.DateOffset(months=count)
    else:
        start = max_date - pd.DateOffset(years=count)

    mask = parsed >= start
    return df.loc[mask.fillna(False)].copy()


def apply_output_filters(df, filter_config, state):
    filtered = df.copy()

    filtered = _apply_date_range(
        filtered,
        filter_config.get("date_column"),
        state.get(DATE_RANGE_KEY, "All Dates"),
    )

    region_col = filter_config.get("region_column")
    region_value = state.get(REGION_KEY, "All Regions")
    if region_col and region_value != "All Regions":
        filtered = filtered[filtered[region_col].astype(str) == str(region_value)]

    product_col = filter_config.get("product_column")
    product_value = state.get(PRODUCT_KEY, "All Categories")
    if product_col and product_value != "All Categories":
        filtered = filtered[filtered[product_col].astype(str) == str(product_value)]

    return filtered.copy()
