"""Read-only, parameterized SQL tool. Agents pass a SELECT; this blocks anything else."""
import re
import duckdb
from config import DB_PATH

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|copy|pragma|call|grant|exec)\b",
    re.IGNORECASE,
)
MAX_ROWS = 200


def sql_query_tool(sql: str, params: list = None):
    """Run a read-only SELECT against the warehouse. Returns rows as a list of dicts.
    Raises ValueError if the query is not a single SELECT or contains a forbidden keyword."""
    clean = sql.strip().rstrip(";")
    if not clean.lower().startswith("select"):
        raise ValueError("Only SELECT statements are allowed.")
    if ";" in clean:
        raise ValueError("Only a single statement is allowed.")
    if _FORBIDDEN.search(clean):
        raise ValueError("Query contains a forbidden keyword.")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        df = con.execute(clean, params or []).df()
    finally:
        con.close()

    truncated = len(df) > MAX_ROWS
    if truncated:
        df = df.head(MAX_ROWS)
    return {"rows": df.to_dict(orient="records"), "row_count": len(df), "truncated": truncated}