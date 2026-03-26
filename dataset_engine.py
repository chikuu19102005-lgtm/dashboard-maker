def analyze_dataset(df, rename_map=None):
    info = {}

    info["rows"] = len(df)
    info["column_count"] = len(df.columns)
    info["columns"] = list(df.columns)
    info["numeric"] = list(df.select_dtypes(include="number").columns)
    info["categorical"] = list(df.select_dtypes(include=["object", "category"]).columns)
    info["missing_values"] = int(df.isna().sum().sum())

    top_columns = []
    row_count = max(len(df), 1)
    for col in df.columns:
        non_null = int(df[col].notna().sum())
        missing = int(df[col].isna().sum())
        top_columns.append(
            {
                "name": str(col),
                "dtype": str(df[col].dtype),
                "non_null_pct": round(non_null / row_count * 100, 1),
                "missing": missing,
                "unique": int(df[col].nunique(dropna=True)),
            }
        )
    top_columns.sort(key=lambda item: (-item["non_null_pct"], -item["unique"], item["name"]))
    info["top_columns"] = top_columns[:5]

    column_aliases = {}
    if rename_map:
        for original, normalized in rename_map.items():
            column_aliases[str(normalized)] = str(original)

    info["column_aliases"] = column_aliases
    return info
