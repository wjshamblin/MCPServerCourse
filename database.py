"""Async database layer with SQL safety for the Financial MCP Server."""

import logging
import re
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

ALLOWED_TABLES = {"gl_transactions", "departments", "chart_of_accounts", "funds", "grants"}

DANGEROUS_PATTERNS = [
    re.compile(r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE|REPLACE)\b", re.IGNORECASE),
    re.compile(r"\b(ATTACH|DETACH)\b", re.IGNORECASE),
    re.compile(r"--"),
    re.compile(r"/\*"),
]


class DatabaseError(Exception):
    pass


class SQLValidationError(DatabaseError):
    pass


def validate_sql(sql: str) -> None:
    stripped = sql.strip().rstrip(";")
    upper = stripped.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        raise SQLValidationError("Only SELECT queries (and CTEs with WITH) are allowed.")
    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(stripped):
            raise SQLValidationError(f"Query contains disallowed pattern: {pattern.pattern}")


async def get_connection(db_path: Path) -> aiosqlite.Connection:
    if not db_path.exists():
        raise DatabaseError(f"Database not found: {db_path}")
    conn = await aiosqlite.connect(str(db_path))
    conn.row_factory = aiosqlite.Row
    return conn


async def execute_query(db_path: Path, sql: str, max_rows: int = 2000) -> tuple[list[dict], int]:
    validate_sql(sql)
    logger.info(f"Executing query: {sql[:200]}")
    conn = await get_connection(db_path)
    try:
        cursor = await conn.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        all_rows = await cursor.fetchall()
        total = len(all_rows)
        rows = [dict(zip(columns, row)) for row in all_rows[:max_rows]]
        return rows, total
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise DatabaseError(f"Query failed: {e}")
    finally:
        await conn.close()


async def get_table_info(db_path: Path) -> list[dict]:
    conn = await get_connection(db_path)
    try:
        cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = []
        for row in await cursor.fetchall():
            table_name = row[0]
            if table_name in ALLOWED_TABLES:
                count_cursor = await conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
                count = (await count_cursor.fetchone())[0]
                col_cursor = await conn.execute(f"PRAGMA table_info([{table_name}])")
                columns = [
                    {"name": col[1], "type": col[2], "nullable": not col[3]}
                    for col in await col_cursor.fetchall()
                ]
                tables.append({"table_name": table_name, "row_count": count, "columns": columns})
        return tables
    finally:
        await conn.close()


async def get_column_info(db_path: Path, table_name: str) -> dict:
    if table_name not in ALLOWED_TABLES:
        raise SQLValidationError(f"Table not allowed: {table_name}")
    conn = await get_connection(db_path)
    try:
        col_cursor = await conn.execute(f"PRAGMA table_info([{table_name}])")
        columns = []
        for col in await col_cursor.fetchall():
            columns.append({"name": col[1], "type": col[2], "nullable": not col[3], "primary_key": bool(col[5])})
        count_cursor = await conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        count = (await count_cursor.fetchone())[0]
        return {"table_name": table_name, "row_count": count, "columns": columns}
    finally:
        await conn.close()
