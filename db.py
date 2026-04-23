"""
Database layer for the financial dashboard — schema, seed, and queries.

SQLite via stdlib ``sqlite3``. One connection per call, opened lazily. The
schema and seed data are adapted from a TypeScript prototype so the demo
feels like a real research-admin dashboard: funds, personnel, effort
allocations, transactions, and grant-renewal projections.

Seed data is deterministic — same numbers every run, so the dashboard
screenshots match what the lecture demo will show.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "data" / "fin.db"


# === Connection management ================================================


@contextmanager
def _conn():
    """Open a SQLite connection with dict-shaped rows and FK enforcement."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _rows_to_dicts(rows) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


def db_exists() -> bool:
    """Return True if the database file exists and has our schema."""
    if not DB_PATH.exists():
        return False
    with _conn() as con:
        row = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='funds'"
        ).fetchone()
        return row is not None


# === Schema ==============================================================


def create_schema() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS funds (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                sponsor TEXT,
                project_start TEXT,
                project_end TEXT,
                budget_period TEXT,
                grant_life_years INTEGER,
                plan_itd REAL,
                actual_itd REAL,
                available_balance REAL NOT NULL,
                projected_available REAL,
                fa_rate REAL,
                is_plan INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS personnel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                title TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS effort_allocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                personnel_id INTEGER NOT NULL REFERENCES personnel(id),
                fund_id TEXT NOT NULL REFERENCES funds(id),
                effort_pct REAL NOT NULL,
                fringe_rate REAL NOT NULL,
                projected_total REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                fund_id TEXT NOT NULL REFERENCES funds(id),
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS additional_funding (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_id TEXT NOT NULL REFERENCES funds(id),
                period TEXT NOT NULL,
                amount REAL NOT NULL
            );
        """)


# === Seed ================================================================


def seed_database(force: bool = False) -> None:
    """Populate the database with deterministic demo data.

    If the funds table already has rows and ``force`` is False, skip
    (so the server start-up doesn't re-seed on every restart).
    """
    create_schema()
    with _conn() as con:
        count = con.execute("SELECT COUNT(*) AS c FROM funds").fetchone()["c"]
        if count > 0 and not force:
            return

        # Clear in dependency order
        for t in ("additional_funding", "transactions", "effort_allocations",
                  "personnel", "funds"):
            con.execute(f"DELETE FROM {t}")

        # --- Funds ------------------------------------------------------
        con.executemany(
            """INSERT INTO funds
                 (id, name, type, sponsor, project_start, project_end,
                  budget_period, grant_life_years, plan_itd, actual_itd,
                  available_balance, projected_available, fa_rate, is_plan)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                ("501002345", "R01 Neural Circuits", "Sponsored",
                 "DHHS, PHS, NIH, NINDS", "2024-03-01", "2029-02-28",
                 "Year 02", 5, 845000, 712500, 145200, 71800, 0.61, 1),
                ("3827541", "Chen Lab Discretionary", "Non-Sponsored",
                 "Non-Governmental - Not Re", "2020-07-01", "2047-06-30",
                 "Year 00", 0, None, None, 21750, 21750, None, 0),
                ("4623189", "Chen Startup Fund", "Non-Sponsored",
                 None, "2019-07-01", None, None,
                 None, None, None, 63400, 63400, None, 0),
                ("4298756", "Chen Departmental Commitment", "Dept Commitment",
                 None, None, None, None,
                 None, None, None, 27900, None, None, 0),
            ],
        )

        # --- Personnel --------------------------------------------------
        con.executemany(
            "INSERT INTO personnel (id, name, title) VALUES (?,?,?)",
            [
                (1, "Jordan Chen",   "Professor (Tenure)"),
                (2, "Maria Santos",  "Lab Research Analyst II"),
                (3, "Alex Kim",      "Research Technician I"),
                (4, "Priya Patel",   "Postdoctoral Associate"),
            ],
        )

        # --- Effort allocations ----------------------------------------
        con.executemany(
            """INSERT INTO effort_allocations
                 (personnel_id, fund_id, effort_pct, fringe_rate, projected_total)
               VALUES (?,?,?,?,?)""",
            [
                (1, "501002345", 0.358, 0.271, 92400),
                (2, "501002345", 1.0,   0.271, 85600),
                (3, "501002345", 0.10,  0.239,  8750),
                (4, "501002345", 0.90,  0.249, 82300),
                (4, "4623189",   0.10,  0.249,  9150),
            ],
        )

        # --- Additional funding (future grant years) -------------------
        con.executemany(
            "INSERT INTO additional_funding (fund_id, period, amount) VALUES (?,?,?)",
            [
                ("501002345", "3/1/26-2/28/27", 270000),
                ("501002345", "3/1/27-2/28/28", 270000),
            ],
        )

        # --- Transactions ----------------------------------------------
        txns = [
            # Chen Departmental Commitment (4298756)
            ("2025-06-17", "4298756", "LAB SUPPLIES AND MATERIALS",                 "FISHER SCIENTIFIC INC",         1425),
            ("2025-06-17", "4298756", "LAB SUPPLIES AND MATERIALS",                 "FISHER SCIENTIFIC INC",          210),
            ("2025-06-17", "4298756", "LAB SUPPLIES AND MATERIALS",                 "SIGMA ALDRICH INC",              134),
            ("2025-06-30", "4298756", "LMCF",                                       "LMCF",                           385),
            ("2025-07-11", "4298756", "GASES (OTHER THAN FOR COOKING OR HEATING)",  "AIRGAS INC",                      73),
            ("2025-07-11", "4298756", "LAB SUPPLIES AND MATERIALS",                 "VWR INTERNATIONAL INC",           42),
            ("2025-07-24", "4298756", "M&R-MACHINERY AND EQUIPMENT",                "BARLOW SCIENTIFIC INC",          295),
            ("2025-07-29", "4298756", "LIFE SCIENCE FACILITY",                      "LIFE SCIENCE FACILITY",          158),
            ("2025-07-31", "4298756", "FLOW CYTOMETRY",                             "FLOW CYTOMETRY",                  92),
            ("2025-07-31", "4298756", "LMCF",                                       "LMCF",                            67),
            ("2025-08-31", "4298756", "FLOW CYTOMETRY",                             "FLOW CYTOMETRY",                  51),
            ("2025-09-04", "4298756", "GASES (OTHER THAN FOR COOKING OR HEATING)",  "AIRGAS INC",                      73),
            ("2025-09-19", "4298756", "LAB SUPPLIES AND MATERIALS",                 "GOLD BIOTECHNOLOGY INC",         248),
            ("2025-09-23", "4298756", "LIFE SCIENCE FACILITY",                      "LIFE SCIENCE FACILITY",          310),
            ("2025-09-30", "4298756", "FLOW CYTOMETRY",                             "FLOW CYTOMETRY",                 137),
            ("2025-10-15", "4298756", "LAB SUPPLIES AND MATERIALS",                 "GENESEE SCIENTIFIC CORP",         78),
            ("2025-10-15", "4298756", "LAB SUPPLIES AND MATERIALS",                 "VWR INTERNATIONAL INC",           65),
            ("2025-10-20", "4298756", "LAB SUPPLIES AND MATERIALS",                 "WORTHINGTON BIOCHEMICAL CORP",   125),
            ("2025-10-28", "4298756", "LIFE SCIENCE FACILITY",                      "LIFE SCIENCE FACILITY",          362),
            ("2025-10-31", "4298756", "FLOW CYTOMETRY",                             "FLOW CYTOMETRY",                  48),
            ("2025-11-03", "4298756", "SERVICES PURCHASED (NOT UNDER CONTRACT)",    "ETON BIOSCIENCE INC",             88),
            ("2025-11-04", "4298756", "GASES (OTHER THAN FOR COOKING OR HEATING)",  "AIRGAS INC",                      73),
            ("2025-11-30", "4298756", "FLOW CYTOMETRY",                             "FLOW CYTOMETRY",                  41),
            ("2025-12-14", "4298756", "LAB SUPPLIES AND MATERIALS",                 "VWR INTERNATIONAL INC",           11),
            ("2025-12-15", "4298756", "SERVICES PURCHASED (NOT UNDER CONTRACT)",    "ETON BIOSCIENCE INC",             57),
            ("2025-12-15", "4298756", "SERVICES PURCHASED (NOT UNDER CONTRACT)",    "ETON BIOSCIENCE INC",             39),
            ("2025-12-20", "4298756", "LAB SUPPLIES AND MATERIALS",                 "VWR INTERNATIONAL INC",           22),
            ("2025-12-20", "4298756", "LAB SUPPLIES AND MATERIALS",                 "VWR INTERNATIONAL INC",           16),
            ("2025-12-31", "4298756", "FLOW CYTOMETRY",                             "FLOW CYTOMETRY",                 108),
            ("2026-01-12", "4298756", "SERVICES PURCHASED (NOT UNDER CONTRACT)",    "ETON BIOSCIENCE INC",             95),
            ("2026-01-15", "4298756", "LAB SUPPLIES AND MATERIALS",                 "GENESEE SCIENTIFIC CORP",        252),
            ("2026-01-15", "4298756", "LAB SUPPLIES AND MATERIALS",                 "VWR INTERNATIONAL INC",           83),
            ("2026-01-20", "4298756", "LAB SUPPLIES AND MATERIALS",                 "GENESEE SCIENTIFIC CORP",         47),
            ("2026-01-21", "4298756", "SERVICES PURCHASED (NOT UNDER CONTRACT)",    "ETON BIOSCIENCE INC",             23),
            ("2026-01-25", "4298756", "SERVICES PURCHASED (NOT UNDER CONTRACT)",    "ETON BIOSCIENCE INC",             15),
            ("2026-01-31", "4298756", "FLOW CYTOMETRY",                             "FLOW CYTOMETRY",                  76),
            # Chen Lab Discretionary (3827541)
            ("2026-01-26", "3827541", "OIT RESEARCH SUPPORT & STORAGE SERVICES",    "OIT DUKE EDU INVOICES 172615",   118),
            ("2026-01-26", "3827541", "INTERDEPARTMENTAL SERVICES EXPENSE",         "OIT DUKE EDU INVOICES 172318",    24),
            ("2026-01-25", "3827541", "COMPUTER SOFTWARE",                          "OIT DUKE EDU INVOICES 174744",    16),
            ("2026-01-31", "3827541", "DEPT GENL & ADMIN APPROPRIATIONS",           "",                                28),
            # Chen Startup Fund (4623189)
            ("2026-01-31", "4623189", "DEPT GENL & ADMIN APPROPRIATIONS",           "",                               105),
            # Orphan transaction pre-seeding current period
            ("2025-05-17", "4298756", "LAB SUPPLIES AND MATERIALS",                 "NEW ENGLAND BIOLABS INC",        102),
            # R01 Neural Circuits (501002345)
            ("2025-08-15", "501002345", "LAB SUPPLIES AND MATERIALS",               "FISHER SCIENTIFIC INC",          345),
            ("2025-09-10", "501002345", "LAB SUPPLIES AND MATERIALS",               "SIGMA ALDRICH INC",              189),
            ("2025-10-05", "501002345", "COMPUTER SOFTWARE",                        "GRAPHPAD SOFTWARE INC",          215),
            ("2025-10-22", "501002345", "SERVICES PURCHASED (NOT UNDER CONTRACT)",  "GENEWIZ INC",                    475),
            ("2025-11-14", "501002345", "LAB SUPPLIES AND MATERIALS",               "THERMO FISHER SCIENTIFIC",       562),
            ("2025-12-03", "501002345", "LAB SUPPLIES AND MATERIALS",               "VWR INTERNATIONAL INC",          128),
            ("2025-12-18", "501002345", "LIFE SCIENCE FACILITY",                    "LIFE SCIENCE FACILITY",          225),
            ("2026-01-08", "501002345", "LAB SUPPLIES AND MATERIALS",               "NEW ENGLAND BIOLABS INC",        310),
            ("2026-01-22", "501002345", "SERVICES PURCHASED (NOT UNDER CONTRACT)",  "ETON BIOSCIENCE INC",            165),
            ("2026-01-31", "501002345", "FLOW CYTOMETRY",                           "FLOW CYTOMETRY",                  94),
        ]
        con.executemany(
            "INSERT INTO transactions (date, fund_id, category, description, amount) VALUES (?,?,?,?,?)",
            txns,
        )


# === Queries =============================================================


def get_all_funds() -> list[dict[str, Any]]:
    with _conn() as con:
        return _rows_to_dicts(con.execute("SELECT * FROM funds").fetchall())


def get_fund_by_id(fund_id: str) -> dict[str, Any] | None:
    with _conn() as con:
        row = con.execute("SELECT * FROM funds WHERE id = ?", (fund_id,)).fetchone()
        return dict(row) if row else None


def get_all_personnel() -> list[dict[str, Any]]:
    with _conn() as con:
        return _rows_to_dicts(con.execute("SELECT * FROM personnel").fetchall())


def get_effort_allocations() -> list[dict[str, Any]]:
    with _conn() as con:
        return _rows_to_dicts(con.execute("SELECT * FROM effort_allocations").fetchall())


def get_effort_allocations_by_fund(fund_id: str) -> list[dict[str, Any]]:
    with _conn() as con:
        return _rows_to_dicts(
            con.execute(
                "SELECT * FROM effort_allocations WHERE fund_id = ?", (fund_id,)
            ).fetchall()
        )


def get_additional_funding(fund_id: str) -> list[dict[str, Any]]:
    with _conn() as con:
        return _rows_to_dicts(
            con.execute(
                "SELECT * FROM additional_funding WHERE fund_id = ?", (fund_id,)
            ).fetchall()
        )


_TXN_SORT_COLS = {"date", "fund_id", "category", "description", "amount"}


def get_transactions(
    *,
    fund_id: str | None = None,
    category: str | None = None,
    sort_by: str = "date",
    sort_order: str = "desc",
) -> list[dict[str, Any]]:
    """Return filtered/sorted transactions. Column and order are validated."""
    sort_col = sort_by if sort_by in _TXN_SORT_COLS else "date"
    sort_dir = "ASC" if sort_order.lower() == "asc" else "DESC"

    sql = "SELECT * FROM transactions WHERE 1=1"
    params: list[Any] = []
    if fund_id:
        sql += " AND fund_id = ?"
        params.append(fund_id)
    if category:
        sql += " AND category = ?"
        params.append(category)
    # sort_col/sort_dir are both from hard-coded sets above — safe to interpolate.
    sql += f" ORDER BY {sort_col} {sort_dir}"

    with _conn() as con:
        return _rows_to_dicts(con.execute(sql, params).fetchall())


def get_monthly_spending(months: int = 6) -> list[dict[str, Any]]:
    """Monthly totals for the last N months, split personnel vs non-personnel."""
    sql = """
        SELECT
            strftime('%Y-%m', date) AS month,
            SUM(CASE WHEN category IN ('PERSONNEL','SALARY','FRINGE') THEN amount ELSE 0 END) AS personnel,
            SUM(CASE WHEN category NOT IN ('PERSONNEL','SALARY','FRINGE') THEN amount ELSE 0 END) AS non_personnel
        FROM transactions
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month DESC
        LIMIT ?
    """
    with _conn() as con:
        rows = _rows_to_dicts(con.execute(sql, (months,)).fetchall())
    rows.reverse()
    return rows


def get_spending_summary() -> dict[str, float]:
    """Compute the aggregate projections shown on the Overview cards.

    - total_available:          sum of available balances across all funds
    - total_projected_expenses: projected 12-month personnel + non-personnel
    - projected_incoming:       roughly 1/2 of the additional_funding total
                                (next year's portion of the grant renewal)
    - surplus_deficit:          available + incoming - projected expenses
    """
    with _conn() as con:
        total_available = con.execute(
            "SELECT COALESCE(SUM(available_balance), 0) AS t FROM funds"
        ).fetchone()["t"]

        personnel_cost = con.execute(
            "SELECT COALESCE(SUM(projected_total), 0) AS t FROM effort_allocations"
        ).fetchone()["t"]

        non_personnel_total = con.execute(
            "SELECT COALESCE(SUM(amount), 0) AS t FROM transactions"
        ).fetchone()["t"]

        addl = con.execute(
            "SELECT COALESCE(SUM(amount), 0) AS t FROM additional_funding"
        ).fetchone()["t"]

    # Transactions span ~8 months (May 2025 → Jan 2026); annualize then
    # project forward 12 months, matching the TS prototype's heuristic.
    monthly_non_personnel = non_personnel_total / 8.0
    projected_non_personnel = monthly_non_personnel * 12.0

    total_projected_expenses = personnel_cost + projected_non_personnel
    projected_incoming = addl / 2.0
    surplus_deficit = total_available + projected_incoming - total_projected_expenses

    return {
        "total_available": round(total_available, 2),
        "total_projected_expenses": round(total_projected_expenses, 2),
        "projected_incoming": round(projected_incoming, 2),
        "surplus_deficit": round(surplus_deficit, 2),
    }


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    seed_database(force=force)
    print(f"Database seeded at {DB_PATH}")
