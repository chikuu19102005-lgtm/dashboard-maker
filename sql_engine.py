import requests
import os

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_CONNECT_TIMEOUT = float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "5"))
OLLAMA_READ_TIMEOUT = float(os.getenv("OLLAMA_READ_TIMEOUT", "120"))


def _ask_ollama(prompt):
    payload = {"model": "llama3", "prompt": prompt, "stream": False}
    try:
        r = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=(OLLAMA_CONNECT_TIMEOUT, OLLAMA_READ_TIMEOUT),
        )
        r.raise_for_status()
        return r.json()["response"].strip()
    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            f"Ollama request timed out after {OLLAMA_READ_TIMEOUT:.0f}s."
        ) from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc


def _schema_text(schema):
    if not isinstance(schema, dict):
        return "all_columns=[]\nnumeric_columns=[]\ncategorical_columns=[]\ncolumn_aliases={}"
    columns = schema.get("columns", [])
    numeric = schema.get("numeric", [])
    categorical = schema.get("categorical", [])
    column_aliases = schema.get("column_aliases", {})
    return (
        f"all_columns={columns}\n"
        f"numeric_columns={numeric}\n"
        f"categorical_columns={categorical}\n"
        f"column_aliases={column_aliases}"
    )


def generate_sql(question, schema):
    schema_block = _schema_text(schema)
    prompt = f"""
You convert natural language to DuckDB SQL.
Return SQL only.

Dataset structure:
{schema_block}

Rules:
- Table name is dataframe
- Use DuckDB syntax
- Use only exact column names from all_columns
- Users may refer to columns by their original names listed in column_aliases; map those to the exact normalized names in all_columns
- Never invent columns (for example: timestamp, date, datetime, created_at)
- Do not nest aggregates (for example: AVG(COUNT(*)))
- If user asks for this month/last month but no date-like column exists in all_columns, do not use EXTRACT or CURRENT_DATE; answer with available columns only

Question:
{question}
"""
    return _ask_ollama(prompt)


def repair_sql(question, schema, bad_sql, error_message):
    schema_block = _schema_text(schema)
    prompt = f"""
Fix this DuckDB SQL query. Return corrected SQL only.

Dataset structure:
{schema_block}

Question:
{question}

Broken SQL:
{bad_sql}

Error:
{error_message}

Rules:
- Table name is dataframe
- Use DuckDB syntax
- Use only exact column names from all_columns
- Users may refer to columns by their original names listed in column_aliases; map those to the exact normalized names in all_columns
- Never invent columns
- Do not nest aggregates
"""
    return _ask_ollama(prompt)
