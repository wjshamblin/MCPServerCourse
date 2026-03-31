"""
Natural Language to SQL pipeline for the Financial MCP Server.

Takes a plain English question about university finances,
generates a SQL query using an LLM, validates and executes it.
"""

import logging

from config import Settings

logger = logging.getLogger(__name__)

SCHEMA_CONTEXT = """
-- University General Ledger Database Schema
-- Each row in gl_transactions is one financial transaction

CREATE TABLE gl_transactions (
    transaction_id TEXT PRIMARY KEY,
    fiscal_year INTEGER NOT NULL,          -- 2022, 2023, 2024, 2025
    fiscal_period INTEGER NOT NULL,        -- 1-12 (1=July, 12=June, fiscal year July-June)
    transaction_date TEXT NOT NULL,         -- ISO date (YYYY-MM-DD)
    posting_date TEXT NOT NULL,            -- ISO date
    department_code TEXT NOT NULL,          -- e.g., 'COMPSCI', 'CHEM', 'ATHLET'
    department_name TEXT NOT NULL,          -- e.g., 'Computer Science'
    fund_code TEXT NOT NULL,               -- '10'=Operating, '20'=Grants, '30'=Endowment, '40'=Auxiliary, '50'=Agency
    fund_name TEXT NOT NULL,               -- e.g., 'General Operating'
    fund_type TEXT NOT NULL,               -- 'unrestricted', 'restricted', 'endowment', 'auxiliary', 'agency'
    account_code TEXT NOT NULL,            -- GL account code (4xxx=revenue, 5xxx=salary, 6xxx=expense)
    account_name TEXT NOT NULL,            -- e.g., 'Faculty Salaries', 'Lab Supplies'
    account_category TEXT NOT NULL,        -- 'revenue', 'expense', 'asset', 'liability', 'equity'
    account_subcategory TEXT NOT NULL,     -- e.g., 'salaries', 'supplies', 'travel', 'equipment'
    amount REAL NOT NULL,                  -- Transaction amount (0 for budget/encumbrance-only entries)
    budget_amount REAL,                    -- Budgeted amount (NULL for non-budget entries)
    encumbrance_amount REAL,              -- Committed but not yet spent
    encumbrance_type TEXT,                -- 'purchase_order', 'contract', 'salary_commitment'
    vendor_name TEXT,                      -- Vendor for expense transactions
    description TEXT NOT NULL,             -- Transaction description
    grant_id TEXT,                         -- Grant ID for restricted fund transactions
    grant_name TEXT,                       -- e.g., 'NSF Award #2345678'
    grant_pi TEXT,                         -- Principal investigator name
    grant_start_date TEXT,                -- Grant start (ISO date)
    grant_end_date TEXT,                  -- Grant end (ISO date)
    grant_total_budget REAL,              -- Total grant budget
    source_system TEXT NOT NULL,           -- 'SAP', 'Concur', 'Workday', 'Manual'
    entry_type TEXT NOT NULL,             -- 'actual', 'budget', 'encumbrance'
    is_adjustment INTEGER NOT NULL        -- 0 or 1
);

CREATE TABLE departments (
    department_code TEXT PRIMARY KEY,
    department_name TEXT NOT NULL,
    division TEXT NOT NULL,
    school TEXT NOT NULL                   -- 'Arts & Sciences', 'Engineering', 'Medicine', etc.
);

CREATE TABLE chart_of_accounts (
    account_code TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    account_category TEXT NOT NULL,
    account_subcategory TEXT NOT NULL,
    normal_balance TEXT NOT NULL           -- 'debit' or 'credit'
);

CREATE TABLE funds (
    fund_code TEXT PRIMARY KEY,
    fund_name TEXT NOT NULL,
    fund_type TEXT NOT NULL,
    description TEXT
);

CREATE TABLE grants (
    grant_id TEXT PRIMARY KEY,
    grant_name TEXT NOT NULL,
    grant_pi TEXT NOT NULL,
    sponsor TEXT NOT NULL,
    department_code TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    total_budget REAL NOT NULL,
    remaining_budget REAL NOT NULL,
    status TEXT NOT NULL                   -- 'active', 'closed', 'pending'
);

-- IMPORTANT NOTES FOR QUERY GENERATION:
-- 1. Fiscal year runs July 1 - June 30 (fiscal_period 1=July, 12=June)
-- 2. entry_type: 'actual' = real spending, 'budget' = planned, 'encumbrance' = committed
-- 3. For actual spending queries, filter: entry_type = 'actual' AND amount > 0
-- 4. For budget vs actual: compare budget_amount (entry_type='budget') vs amount (entry_type='actual')
-- 5. fund_type 'restricted' transactions usually have grant_id populated
-- 6. Use SUM(amount) for totals, not COUNT(*) — each row is one transaction
-- 7. Department codes: COMPSCI, CHEM, PHYS, MATH, ECE, BME, LAW, etc.
"""


def extract_sql_from_response(text: str) -> str:
    """Extract SQL query from LLM response, handling markdown code blocks."""
    if "```sql" in text:
        start = text.index("```sql") + 6
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    lines = text.strip().split("\n")
    sql_lines = []
    in_sql = False
    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("SELECT"):
            in_sql = True
        if in_sql:
            sql_lines.append(stripped)
            if stripped.endswith(";"):
                break
    if sql_lines:
        return " ".join(sql_lines).rstrip(";")
    return text.strip()


async def generate_sql_anthropic(question: str, config: Settings) -> str:
    """Generate SQL using Anthropic's Claude."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)
    response = await client.messages.create(
        model=config.anthropic_model,
        max_tokens=1024,
        system=(
            "You are a SQL expert. Given a question about university financial data, "
            "generate a single SQLite SELECT query to answer it. Return ONLY the SQL "
            "query in a ```sql code block. No explanations."
        ),
        messages=[{"role": "user", "content": f"Database schema:\n{SCHEMA_CONTEXT}\n\nQuestion: {question}"}],
    )
    block = response.content[0]
    return extract_sql_from_response(getattr(block, "text", str(block)))


async def generate_sql_openai(question: str, config: Settings) -> str:
    """Generate SQL using OpenAI."""
    import openai

    client_kwargs = {"api_key": config.openai_api_key}
    if config.openai_base_url:
        client_kwargs["base_url"] = config.openai_base_url

    client = openai.AsyncOpenAI(**client_kwargs)
    response = await client.chat.completions.create(
        model=config.openai_model,
        max_tokens=1024,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a SQL expert. Given a question about university financial data, "
                    "generate a single SQLite SELECT query to answer it. Return ONLY the SQL "
                    "query in a ```sql code block. No explanations."
                ),
            },
            {"role": "user", "content": f"Database schema:\n{SCHEMA_CONTEXT}\n\nQuestion: {question}"},
        ],
    )
    content = response.choices[0].message.content or ""
    return extract_sql_from_response(content)


async def nl_to_sql(question: str, config: Settings) -> str:
    """Convert a natural language question to SQL."""
    logger.info(f"NL2SQL question: {question}")
    if config.llm_provider == "anthropic" and config.anthropic_api_key:
        sql = await generate_sql_anthropic(question, config)
    elif config.openai_api_key:
        sql = await generate_sql_openai(question, config)
    else:
        raise ValueError("No LLM API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env")
    logger.info(f"Generated SQL: {sql}")
    return sql
