# Step 05: Natural Language to SQL

This step adds an NL-to-SQL capability so users can ask questions in plain English. An LLM generates a SQL query, the server validates it with the same safety checks as `query_sql`, and executes it.

## How It Works

1. **Question** — User asks a natural language question via the `ask` tool
2. **LLM generates SQL** — The question is sent to an LLM (Anthropic or OpenAI) along with the full database DDL as context
3. **Validation** — The generated SQL passes through the same safety checks as manual queries (SELECT-only, dangerous keyword blocking)
4. **Execution** — The validated query runs against the database and results are returned as JSON

## DDL-Based Context

Rather than using few-shot examples or retrieval, the NL-to-SQL pipeline sends the complete database DDL (CREATE TABLE statements with column comments) to the LLM. This gives the model full knowledge of:

- All table and column names
- Data types and constraints
- Inline comments explaining codes, ranges, and relationships
- Query generation hints (e.g., fiscal year conventions, entry type filters)

## New Tool

| Tool | Description |
|------|-------------|
| `ask(question)` | Ask a natural language question about university financial data. Converts to SQL, validates, executes, and returns results. |

## Prompts

Prompts are reusable templates that help clients construct common financial analysis requests.

| Prompt | Parameters | Description |
|--------|------------|-------------|
| `budget_analysis` | `department`, `fiscal_year` (default 2025) | Budget vs actual analysis for a department |
| `grant_status` | `status` (default "active") | Grant status report filtered by status |
| `department_spending` | `fiscal_year` (default 2025) | Department spending comparison with subcategory breakdown |

## Configuration

Set `LLM_PROVIDER` in `.env` to choose the LLM backend:

```bash
# Anthropic (default)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5

# OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# OpenAI-compatible proxy
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://your-proxy.example.com/v1
```

## Architecture

| File | Purpose |
|------|---------|
| `nl2sql.py` | NL-to-SQL pipeline — schema context, LLM calls, SQL extraction |
| `server.py` | MCP server — `ask` tool, prompt templates |
| `config.py` | LLM provider settings (API keys, model names, base URLs) |
