"""SQLite Database Inspector and Query Plugin for locaLLM."""

import os
from pathlib import Path
import sqlite3
from typing import Any, Dict


def _resolve_db(path_str: str) -> Path:
    """Resolve database path defensively."""
    clean = path_str.strip().strip("'\"")
    p = Path(os.path.expanduser(os.path.expandvars(clean)))
    return p.resolve()


def sqlite_query(db_path: str, query: str) -> str:
    """Execute a SQL query on a local SQLite database and return formatted results."""
    target_path = _resolve_db(db_path)
    if not target_path.exists():
        return f"Error: SQLite database file '{target_path}' does not exist."

    clean_query = query.strip()
    if not clean_query:
        return "Error: Empty SQL query provided."

    try:
        conn = sqlite3.connect(str(target_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(clean_query)

        if cursor.description is None:
            # Non-SELECT statement
            conn.commit()
            rows_affected = cursor.rowcount
            conn.close()
            return f"Query executed successfully. Rows affected: {rows_affected}"

        col_names = [col[0] for col in cursor.description]
        rows = cursor.fetchmany(50)
        conn.close()

        if not rows:
            return f"Query executed successfully. Columns: {col_names}. (0 rows returned)"

        # Format output as neat text table
        lines = [" | ".join(col_names)]
        lines.append("-" * len(lines[0]))
        for row in rows:
            lines.append(" | ".join(str(val) for val in row))

        total_note = f"\n(Returned {len(rows)} rows"
        if len(rows) == 50:
            total_note += " [capped at 50 max]"
        total_note += ")"

        return "\n".join(lines) + total_note

    except Exception as exc:
        return f"SQLite Error: {exc}"


def sqlite_schema(db_path: str) -> str:
    """Inspect all tables and their column definitions in a local SQLite database."""
    target_path = _resolve_db(db_path)
    if not target_path.exists():
        return f"Error: SQLite database file '{target_path}' does not exist."

    try:
        conn = sqlite3.connect(str(target_path), timeout=5.0)
        cursor = conn.cursor()
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
        tables = cursor.fetchall()
        conn.close()

        if not tables:
            return f"Database '{target_path.name}' is valid but contains no user tables."

        reports = [f"=== SQLite Schema for '{target_path.name}' ({len(tables)} tables) ==="]
        for tbl_name, tbl_sql in tables:
            reports.append(f"\n--- Table: {tbl_name} ---\n{tbl_sql or '(No CREATE definition found)'}")

        return "\n".join(reports)

    except Exception as exc:
        return f"SQLite Error inspecting schema: {exc}"
