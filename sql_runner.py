import duckdb
import re


class SQLValidationError(ValueError):
    pass


FORBIDDEN_KEYWORDS = {
    "drop",
    "delete",
    "update",
    "insert",
    "alter",
    "create",
    "copy",
    "attach",
    "detach",
    "pragma",
    "call",
}

ALLOWED_FUNCTIONS = {
    "abs",
    "avg",
    "cast",
    "coalesce",
    "count",
    "date_trunc",
    "extract",
    "greatest",
    "ifnull",
    "least",
    "lower",
    "max",
    "min",
    "nullif",
    "round",
    "strftime",
    "sum",
    "upper",
}

SQL_STARTERS = ("select", "with", "show", "describe")
RESERVED_TOKENS = {
    "select",
    "from",
    "where",
    "group",
    "order",
    "by",
    "limit",
    "having",
    "and",
    "or",
    "not",
    "as",
    "on",
    "join",
    "left",
    "right",
    "inner",
    "outer",
    "full",
    "cross",
    "distinct",
    "case",
    "when",
    "then",
    "else",
    "end",
    "with",
    "over",
    "partition",
    "desc",
    "asc",
    "current_date",
    "date",
}


def validate_sql(sql, df_columns):
    normalized = (sql or "").strip()
    if not normalized:
        raise SQLValidationError("Empty SQL query.")
    lower_sql = normalized.lower()
    if not lower_sql.startswith(SQL_STARTERS):
        raise SQLValidationError("Only SELECT/WITH/SHOW/DESCRIBE queries are allowed.")
    if ";" in normalized:
        raise SQLValidationError("Multiple SQL statements are not allowed.")

    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", lower_sql):
            raise SQLValidationError(f"Forbidden SQL keyword: {kw}")

    known_columns = {str(c).lower() for c in df_columns}

    quoted_identifiers = re.findall(r'"([^"]+)"', normalized)
    for ident in quoted_identifiers:
        ident_lower = ident.lower()
        if ident_lower in {"dataframe", "*"}:
            continue
        if ident_lower not in known_columns:
            raise SQLValidationError(f"Unknown column referenced: {ident}")

    func_candidates = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", normalized)
    for func in func_candidates:
        f = func.lower()
        if f in RESERVED_TOKENS:
            continue
        if f in known_columns:
            continue
        if f not in ALLOWED_FUNCTIONS:
            raise SQLValidationError(f"Unknown or disallowed SQL function: {func}")

def run_sql(df, sql):
    validate_sql(sql, df.columns)

    con = duckdb.connect()

    con.register("dataframe", df)

    result = con.execute(sql).df()

    return result
