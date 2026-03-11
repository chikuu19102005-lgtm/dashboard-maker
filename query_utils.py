import re


SQL_STARTERS = ("select", "with", "show", "describe")


def extract_sql(text):
    sql = (text or "").strip()
    if "```" in sql:
        parts = sql.split("```")
        for part in parts:
            p = part.strip()
            if not p:
                continue
            if p.lower().startswith("sql"):
                p = p[3:].strip()
            if p.lower().startswith(SQL_STARTERS):
                sql = p
                break
    if ";" in sql:
        sql = sql.split(";", 1)[0].strip()
    return sql


def detect_query_type(question):
    q = (question or "").lower()
    if any(k in q for k in [" vs ", "versus", "compare"]):
        return "compare"
    if re.search(r"\btop\s+\d+\b", q) or "top " in q:
        return "top"
    if any(k in q for k in ["average", "avg", "mean"]):
        return "average"
    if any(k in q for k in ["trend", "over time"]):
        return "trend"
    return "table"


def _question_tokens(question):
    return set(re.findall(r"[a-z0-9]+", (question or "").lower()))


def _column_score(col, q_tokens, q_lower, aliases=None):
    aliases = aliases or {}
    candidates = [str(col).lower()]
    alias = aliases.get(str(col))
    if alias:
        candidates.append(str(alias).lower())

    if any(candidate in q_lower for candidate in candidates):
        return 100
    score = 0
    for candidate in candidates:
        parts = [p for p in re.split(r"[_\W]+", candidate) if len(p) >= 3]
        score += sum(1 for p in parts if p in q_tokens)
    return score


def _extract_top_n(question, default=5):
    q = (question or "").lower()
    m = re.search(r"\btop\s+(\d+)\b", q)
    if m:
        return int(m.group(1))
    if "top" in q:
        return default
    return None


def build_fallback_sql(question, df, column_aliases=None):
    q = (question or "").lower()
    q_tokens = _question_tokens(question)
    query_type = detect_query_type(question)
    column_aliases = column_aliases or {}

    columns = list(df.columns)
    numeric_cols = list(df.select_dtypes(include="number").columns)
    category_cols = [c for c in columns if c not in numeric_cols]

    ranked = sorted(
        columns,
        key=lambda c: _column_score(c, q_tokens, q, column_aliases),
        reverse=True,
    )
    matched = [c for c in ranked if _column_score(c, q_tokens, q, column_aliases) > 0]
    matched_numeric = [c for c in matched if c in numeric_cols]
    matched_category = [c for c in matched if c in category_cols]

    top_n = _extract_top_n(question)
    if query_type == "top" and top_n is not None:
        metric = matched_numeric[0] if matched_numeric else (numeric_cols[0] if numeric_cols else None)
        group_col = matched_category[0] if matched_category else (category_cols[0] if category_cols else None)
        if metric and group_col:
            return f'SELECT "{group_col}", "{metric}" FROM dataframe ORDER BY "{metric}" DESC LIMIT {top_n}'
        if metric:
            return f'SELECT "{metric}" FROM dataframe ORDER BY "{metric}" DESC LIMIT {top_n}'

    if query_type == "average" and (matched_numeric or numeric_cols):
        metric = matched_numeric[0] if matched_numeric else numeric_cols[0]
        if matched_category and any(k in q for k in ["by", "per", "each"]):
            group_col = matched_category[0]
            return (
                f'SELECT "{group_col}", AVG("{metric}") AS avg_{metric} '
                f'FROM dataframe GROUP BY "{group_col}" ORDER BY avg_{metric} DESC LIMIT 20'
            )
        return f'SELECT AVG("{metric}") AS avg_{metric} FROM dataframe'

    if query_type == "compare":
        compare_cols = matched_numeric[:2]
        if len(compare_cols) < 2:
            compare_cols = numeric_cols[:2]
        if len(compare_cols) >= 2:
            return f'SELECT "{compare_cols[0]}", "{compare_cols[1]}" FROM dataframe LIMIT 200'

    selected = matched[:4]
    if not selected:
        return "SELECT * FROM dataframe LIMIT 20"
    select_list = ", ".join([f'"{c}"' for c in selected])
    if query_type == "trend":
        return f"SELECT {select_list} FROM dataframe LIMIT 300"
    return f"SELECT {select_list} FROM dataframe LIMIT 100"
