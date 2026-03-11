def analyze_dataset(df, rename_map=None):
    info = {}

    info["rows"] = len(df)
    info["columns"] = list(df.columns)
    info["numeric"] = list(df.select_dtypes(include="number").columns)
    info["categorical"] = list(df.select_dtypes(include=["object", "category"]).columns)

    column_aliases = {}
    if rename_map:
        for original, normalized in rename_map.items():
            column_aliases[str(normalized)] = str(original)

    info["column_aliases"] = column_aliases
    return info
