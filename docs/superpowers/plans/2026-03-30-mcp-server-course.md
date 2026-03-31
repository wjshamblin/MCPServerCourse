# MCP Server Course Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 10-branch progressive course teaching FastMCP server development from hello world through NL2SQL to Azure OAuth + OBO flow.

**Architecture:** Each branch (`step-01` through `step-10`) is created from the previous branch. Each branch contains working code and a README explaining concepts. The dataset generator (step-04) is independent and can be built in parallel with steps 01-03.

**Tech Stack:** Python 3.11+, FastMCP (latest), SQLite/aiosqlite, Pydantic Settings, httpx, Faker

---

## Task 1: step-01 — Hello World MCP Server

**Branch:** `step-01` (from `main`)

**Files:**
- Create: `server.py`
- Create: `requirements.txt`
- Create: `README.md`
- Create: `.gitignore`

- [ ] **Step 1: Create branch**

```bash
git checkout main
git checkout -b step-01
```

- [ ] **Step 2: Create .gitignore**

Create `.gitignore`:

```
__pycache__/
*.pyc
*.pyo
.env
*.db
data/
.venv/
venv/
.idea/
.vscode/
*.egg-info/
dist/
build/
logs/
```

- [ ] **Step 3: Create requirements.txt**

Create `requirements.txt`:

```
fastmcp>=2.14.0
uvicorn>=0.34.0
```

- [ ] **Step 4: Create server.py**

Create `server.py`:

```python
"""
Step 01: Hello World MCP Server

A minimal MCP server demonstrating the basics:
- Creating a FastMCP server instance
- Defining tools with @mcp.tool
- Type annotations for automatic schema generation
- Running with HTTP streamable transport
"""

from fastmcp import FastMCP

# Create the server instance.
# 'instructions' tells LLM clients what this server does.
mcp = FastMCP(
    "HelloWorld",
    instructions="A simple demo MCP server. Use the echo tool to echo messages and the add tool to add numbers.",
)


@mcp.tool
def echo(message: str) -> str:
    """Echo a message back to the caller."""
    return f"Echo: {message}"


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers together and return the result."""
    return a + b


@mcp.tool
def greet(name: str, greeting: str = "Hello") -> str:
    """Greet someone by name. Optionally customize the greeting."""
    return f"{greeting}, {name}! Welcome to MCP."


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
```

- [ ] **Step 5: Create README.md**

Create `README.md`:

```markdown
# MCP Server Course

A progressive course teaching MCP (Model Context Protocol) server development with FastMCP in Python.

## What is MCP?

The Model Context Protocol (MCP) is an open standard that lets AI assistants connect to external tools and data sources. An MCP server exposes **tools**, **resources**, and **prompts** that LLM clients can discover and use.

## Step 01: Hello World

This is the simplest possible MCP server. It demonstrates:

1. **Creating a server** — `FastMCP("HelloWorld")` creates a named server instance
2. **Defining tools** — `@mcp.tool` decorates a Python function to expose it as an MCP tool
3. **Type annotations** — FastMCP uses your type hints to auto-generate the tool's JSON schema
4. **Default parameters** — Optional parameters with defaults (like `greeting` in `greet`) become optional in the schema
5. **HTTP transport** — `mcp.run(transport="http")` starts an HTTP streamable endpoint at `/mcp/`

### Running the server

```bash
pip install -r requirements.txt
python server.py
```

The server starts at `http://localhost:8000/mcp/`.

### Connecting a client

In Claude Desktop or any MCP client, add this server configuration:

```json
{
  "mcpServers": {
    "hello-world": {
      "url": "http://localhost:8000/mcp/"
    }
  }
}
```

### Key concepts

- **Tools** are functions the LLM can call. They take typed inputs and return results.
- **Transport** is how the client communicates with the server. HTTP streamable is recommended for network deployments.
- **Schema generation** happens automatically from your Python function signature — the function name becomes the tool name, the docstring becomes the description, and type annotations define the input schema.
```

- [ ] **Step 6: Test the server starts**

```bash
cd /Users/wjs/Programming/MCPServerCourse
pip install -r requirements.txt
timeout 5 python server.py || true
```

Expected: Server starts on port 8000 (times out after 5s, which is fine).

- [ ] **Step 7: Commit**

```bash
git add .gitignore requirements.txt server.py README.md
git commit -m "feat: step-01 hello world MCP server

Minimal FastMCP server with echo, add, and greet tools.
HTTP streamable transport on port 8000."
```

---

## Task 2: step-02 — Resources and Prompts

**Branch:** `step-02` (from `step-01`)

**Files:**
- Modify: `server.py`
- Modify: `README.md`

- [ ] **Step 1: Create branch**

```bash
git checkout step-01
git checkout -b step-02
```

- [ ] **Step 2: Update server.py with resources and prompts**

Add to `server.py` after the existing tools:

```python
"""
Step 02: Resources and Prompts

Building on the hello world server, we add:
- Resources: read-only data the LLM can access (static and dynamic)
- Resource templates: parameterized URIs for dynamic content
- Prompts: reusable message templates for common interactions
"""

import json
from datetime import datetime, timezone
from fastmcp import FastMCP
from fastmcp.prompts import Message

mcp = FastMCP(
    "HelloWorld",
    instructions=(
        "A demo MCP server with tools, resources, and prompts. "
        "Read the 'about' resource first to understand what's available."
    ),
)


# === Tools (from step-01) ===


@mcp.tool
def echo(message: str) -> str:
    """Echo a message back to the caller."""
    return f"Echo: {message}"


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers together and return the result."""
    return a + b


@mcp.tool
def greet(name: str, greeting: str = "Hello") -> str:
    """Greet someone by name. Optionally customize the greeting."""
    return f"{greeting}, {name}! Welcome to MCP."


# === Resources ===


@mcp.resource("resource://about", mime_type="text/plain")
def get_about() -> str:
    """Static information about this server."""
    return (
        "HelloWorld MCP Server v0.2\n"
        "A demo server for learning MCP concepts.\n"
        "Available: tools (echo, add, greet), resources, and prompts."
    )


@mcp.resource("resource://server-time", mime_type="application/json")
def get_server_time() -> str:
    """Dynamic resource that returns the current server time."""
    now = datetime.now(timezone.utc)
    return json.dumps({
        "utc": now.isoformat(),
        "unix_timestamp": int(now.timestamp()),
    })


@mcp.resource("resource://greeting/{name}", mime_type="text/plain")
def get_greeting_resource(name: str) -> str:
    """Resource template — generates a personalized greeting for any name."""
    return f"Hello, {name}! This greeting was generated from a resource template."


@mcp.resource(
    "data://server-config",
    mime_type="application/json",
    description="Server configuration and capabilities (read-only)",
)
def get_server_config() -> str:
    """Exposes server metadata as structured JSON."""
    return json.dumps({
        "server_name": "HelloWorld",
        "version": "0.2",
        "transport": "http-streamable",
        "capabilities": ["tools", "resources", "prompts"],
    })


# === Prompts ===


@mcp.prompt
def code_review(language: str, code: str) -> list[Message]:
    """Generate a code review request for the given code."""
    return [
        Message(
            f"Please review the following {language} code for bugs, style issues, "
            f"and potential improvements:\n\n```{language}\n{code}\n```"
        ),
    ]


@mcp.prompt
def summarize(text: str, style: str = "concise") -> str:
    """Generate a summarization request with a specified style."""
    return f"Please provide a {style} summary of the following text:\n\n{text}"


@mcp.prompt
def explain_concept(concept: str, audience: str = "beginner") -> list[Message]:
    """Generate a request to explain a concept for a specific audience."""
    return [
        Message(
            f"You are an expert teacher. Explain '{concept}' to a {audience} audience. "
            f"Use analogies and examples where helpful."
        ),
        Message("I'll explain this step by step.", role="assistant"),
    ]


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
```

- [ ] **Step 3: Update README.md**

Append to `README.md`:

```markdown
## Step 02: Resources and Prompts

Building on the hello world server, this step introduces two more MCP primitives:

### Resources

Resources provide **read-only data** that LLM clients can retrieve. Unlike tools (which perform actions), resources just return data.

| Type | Example | When to use |
|------|---------|-------------|
| Static resource | `resource://about` | Fixed content like docs, config |
| Dynamic resource | `resource://server-time` | Content that changes per request |
| Resource template | `resource://greeting/{name}` | Parameterized content |

**Key differences from tools:**
- Resources are read-only (no side effects)
- Resources use URI addressing (`resource://about`)
- Resource templates use RFC 6570 URI templates

### Prompts

Prompts are **reusable message templates** that help LLMs generate structured responses. They're not the same as "system prompts" — they're templates a client can request and fill in with parameters.

- `code_review(language, code)` — generates a code review request
- `summarize(text, style)` — generates a summarization request
- `explain_concept(concept, audience)` — generates a teaching request with assistant preamble

### New concepts in this step

- `@mcp.resource(uri)` — register a function as a resource
- `@mcp.prompt` — register a function as a prompt template
- `mime_type` — tell clients what format the resource returns
- `Message(content, role)` — structured messages for multi-turn prompts
- Resource templates with `{parameter}` in the URI
```

- [ ] **Step 4: Commit**

```bash
git add server.py README.md
git commit -m "feat: step-02 add resources and prompts

Static/dynamic resources, resource templates with URI parameters,
and reusable prompt templates (code_review, summarize, explain_concept)."
```

---

## Task 3: step-03 — Context, Logging, and Elicitation

**Branch:** `step-03` (from `step-02`)

**Files:**
- Modify: `server.py`
- Modify: `README.md`

- [ ] **Step 1: Create branch**

```bash
git checkout step-02
git checkout -b step-03
```

- [ ] **Step 2: Update server.py with Context features**

Replace `server.py` with the full version that adds Context-based tools. Add these new tools after the existing ones:

```python
# Add these imports at the top:
import asyncio
from fastmcp import Context

# Add these tools after the existing tools section:

# === Context-Aware Tools ===


@mcp.tool
async def analyze_text(text: str, ctx: Context) -> str:
    """Analyze text with progress reporting and context logging.

    Demonstrates:
    - Context injection (ctx parameter is auto-injected, hidden from schema)
    - Logging to the client via ctx.info(), ctx.warning()
    - Progress reporting via ctx.report_progress()
    """
    await ctx.info("Starting text analysis...")

    # Step 1: Basic stats
    await ctx.report_progress(progress=1, total=4)
    words = text.split()
    word_count = len(words)
    char_count = len(text)
    await ctx.info(f"Counted {word_count} words, {char_count} characters")

    # Step 2: Word frequency
    await ctx.report_progress(progress=2, total=4)
    freq: dict[str, int] = {}
    for word in words:
        w = word.lower().strip(".,!?;:")
        freq[w] = freq.get(w, 0) + 1
    top_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]

    # Step 3: Sentence count
    await ctx.report_progress(progress=3, total=4)
    sentences = len([s for s in text.split(".") if s.strip()])

    if word_count > 1000:
        await ctx.warning("Large text detected — analysis may be approximate")

    # Step 4: Done
    await ctx.report_progress(progress=4, total=4)
    await ctx.info("Analysis complete")

    return json.dumps({
        "word_count": word_count,
        "character_count": char_count,
        "sentence_count": sentences,
        "top_words": [{"word": w, "count": c} for w, c in top_words],
    })


@mcp.tool
async def delete_records(table: str, confirm: bool = False, ctx: Context = None) -> str:
    """Simulate deleting records with elicitation for confirmation.

    Demonstrates ctx.elicit() — requesting structured input from the user
    during tool execution. The LLM client will prompt the user for confirmation.
    """
    if not confirm:
        # Use elicitation to ask the user for confirmation
        result = await ctx.elicit(
            message=f"Are you sure you want to delete all records from '{table}'? This cannot be undone.",
            response_type=bool,
        )

        if result.action != "accept" or not result.data:
            await ctx.info("Delete cancelled by user")
            return "Operation cancelled."

    await ctx.warning(f"Simulating delete of all records from '{table}'")
    # In a real server, you'd actually delete records here
    await asyncio.sleep(0.5)  # Simulate work
    return f"(Simulated) Deleted all records from '{table}'."


@mcp.tool
async def process_items(items: list[str], ctx: Context) -> str:
    """Process a list of items with detailed progress reporting.

    Demonstrates progress reporting for batch operations where
    total is known upfront and progress increments per item.
    """
    results = []
    total = len(items)
    await ctx.info(f"Processing {total} items...")

    for i, item in enumerate(items):
        await ctx.report_progress(progress=i + 1, total=total)
        await ctx.info(f"Processing: {item}")
        await asyncio.sleep(0.2)  # Simulate work
        results.append(f"Processed: {item.upper()}")

    await ctx.info("All items processed")
    return json.dumps(results)
```

- [ ] **Step 3: Update README.md**

Append to `README.md`:

```markdown
## Step 03: Context, Logging, and Elicitation

This step introduces the **Context** object — your tools' connection back to the MCP client.

### Context injection

Add a `ctx: Context` parameter to any tool function. FastMCP injects it automatically — it does NOT appear in the tool's schema (LLMs never see it).

```python
@mcp.tool
async def my_tool(query: str, ctx: Context) -> str:
    await ctx.info("Working on it...")
    return "done"
```

### What Context provides

| Method | Purpose |
|--------|---------|
| `ctx.info(msg)` | Log info message to client |
| `ctx.warning(msg)` | Log warning to client |
| `ctx.error(msg)` | Log error to client |
| `ctx.debug(msg)` | Log debug message to client |
| `ctx.report_progress(progress, total)` | Update progress bar |
| `ctx.elicit(message, response_type)` | Ask user for input during execution |
| `ctx.read_resource(uri)` | Read another resource from within a tool |
| `ctx.sample(prompt)` | Ask the client's LLM to generate text |

### Elicitation

Elicitation pauses tool execution and asks the user a question. The response has an `action` field:
- `"accept"` — user provided data (available in `result.data`)
- `"decline"` — user chose not to answer
- `"cancel"` — user cancelled the operation

This is powerful for confirmations, multi-step workflows, and gathering missing information.

### New concepts in this step

- `Context` — auto-injected gateway to MCP features
- Logging levels (`info`, `warning`, `error`, `debug`)
- Progress reporting for long operations
- Elicitation for interactive user input during tool execution
- `async def` tools — required when using Context methods (they're all async)
```

- [ ] **Step 4: Commit**

```bash
git add server.py README.md
git commit -m "feat: step-03 context, logging, and elicitation

Context-aware tools with progress reporting, client logging,
and elicitation for interactive user confirmation."
```

---

## Task 4: step-04 — Financial Dataset Generator

**Branch:** `step-04` (from `step-03`)

**Files:**
- Create: `generate_data.py`
- Modify: `requirements.txt`
- Modify: `README.md`

This task is large. The generator must produce ~500K+ realistic university GL transactions.

- [ ] **Step 1: Create branch**

```bash
git checkout step-03
git checkout -b step-04
```

- [ ] **Step 2: Update requirements.txt**

Add to `requirements.txt`:

```
fastmcp>=2.14.0
uvicorn>=0.34.0
faker>=33.0.0
```

- [ ] **Step 3: Create generate_data.py**

Create `generate_data.py` — the full dataset generator. This is a standalone script.

```python
#!/usr/bin/env python
"""
Step 04: University General Ledger Dataset Generator

Generates ~500K+ synthetic financial transactions modeled on a large
university's general ledger. Includes fund accounting concepts:
- Multiple fund types (operating, restricted grants, endowment, auxiliary, agency)
- Chart of accounts with natural GL account codes
- Encumbrances (commitments not yet spent)
- Budget entries alongside actuals
- Grant tracking with PIs, sponsors, and budgets
- Seasonal spending patterns
- 50+ departments across multiple schools

Usage:
    python generate_data.py [--output data/university_gl.db] [--transactions 500000]
"""

import argparse
import random
import sqlite3
import uuid
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

# =============================================================================
# Reference Data
# =============================================================================

SCHOOLS = {
    "Arts & Sciences": [
        ("COMPSCI", "Computer Science"),
        ("MATH", "Mathematics"),
        ("PHYS", "Physics"),
        ("CHEM", "Chemistry"),
        ("BIO", "Biology"),
        ("ENGLISH", "English"),
        ("HISTORY", "History"),
        ("POLISCI", "Political Science"),
        ("ECON", "Economics"),
        ("PSYCH", "Psychology"),
        ("SOCIOL", "Sociology"),
        ("PHILO", "Philosophy"),
        ("ROMANCE", "Romance Studies"),
        ("STATS", "Statistical Science"),
        ("NEURO", "Neuroscience"),
    ],
    "Engineering": [
        ("ECE", "Electrical & Computer Engineering"),
        ("MECHENG", "Mechanical Engineering"),
        ("CIVENG", "Civil & Environmental Engineering"),
        ("BME", "Biomedical Engineering"),
        ("MATSCI", "Materials Science"),
    ],
    "Medicine": [
        ("MEDSCHOOL", "School of Medicine"),
        ("PATHOL", "Pathology"),
        ("PEDS", "Pediatrics"),
        ("SURG", "Surgery"),
        ("NEUROMD", "Neurology"),
        ("CARDIO", "Cardiology"),
        ("ONCOL", "Oncology"),
        ("RADIOL", "Radiology"),
    ],
    "Law": [
        ("LAW", "School of Law"),
        ("LAWCLIN", "Law Clinical Programs"),
    ],
    "Business": [
        ("BUSINESS", "School of Business"),
        ("FINANCE", "Finance Department"),
        ("MKTG", "Marketing"),
    ],
    "Public Policy": [
        ("PUBPOL", "Public Policy"),
        ("ENVIRON", "Environmental Policy"),
    ],
    "Nursing": [
        ("NURSING", "School of Nursing"),
    ],
    "Divinity": [
        ("DIVINITY", "Divinity School"),
    ],
    "Graduate School": [
        ("GRADSCH", "Graduate School Administration"),
    ],
    "Central Administration": [
        ("PROVOST", "Provost Office"),
        ("FINAID", "Financial Aid"),
        ("REGIST", "Registrar"),
        ("ITDEPT", "Information Technology"),
        ("FACMGMT", "Facilities Management"),
        ("HR", "Human Resources"),
        ("LIBR", "University Libraries"),
        ("ATHLET", "Athletics"),
        ("ALUMNI", "Alumni Affairs"),
        ("RESADM", "Research Administration"),
    ],
}

FUNDS = [
    ("10", "General Operating", "unrestricted", "Primary university operating fund"),
    ("20", "Restricted Grants", "restricted", "Sponsored research and grants"),
    ("25", "Restricted Gifts", "restricted", "Donor-restricted gifts and endowment income"),
    ("30", "Endowment", "endowment", "Endowment principal and investment returns"),
    ("40", "Auxiliary Enterprises", "auxiliary", "Self-supporting operations (housing, dining, parking)"),
    ("50", "Agency Funds", "agency", "Funds held on behalf of others (student organizations)"),
    ("60", "Plant Funds", "unrestricted", "Capital projects and equipment"),
    ("70", "Loan Funds", "restricted", "Student loan programs"),
]

CHART_OF_ACCOUNTS = [
    # Revenue accounts (4xxx)
    ("4100", "Tuition Revenue", "revenue", "tuition_revenue", "credit"),
    ("4110", "Graduate Tuition", "revenue", "tuition_revenue", "credit"),
    ("4120", "Professional Tuition", "revenue", "tuition_revenue", "credit"),
    ("4200", "State Appropriations", "revenue", "state_funding", "credit"),
    ("4300", "Federal Grants Revenue", "revenue", "grant_revenue", "credit"),
    ("4310", "State Grants Revenue", "revenue", "grant_revenue", "credit"),
    ("4320", "Private Grants Revenue", "revenue", "grant_revenue", "credit"),
    ("4400", "Gift Revenue", "revenue", "gift_revenue", "credit"),
    ("4500", "Investment Income", "revenue", "investment_income", "credit"),
    ("4600", "Auxiliary Revenue", "revenue", "auxiliary_revenue", "credit"),
    ("4610", "Housing Revenue", "revenue", "auxiliary_revenue", "credit"),
    ("4620", "Dining Revenue", "revenue", "auxiliary_revenue", "credit"),
    ("4630", "Parking Revenue", "revenue", "auxiliary_revenue", "credit"),
    ("4700", "Clinical Revenue", "revenue", "clinical_revenue", "credit"),
    ("4800", "Indirect Cost Recovery", "revenue", "idc_revenue", "credit"),
    ("4900", "Other Revenue", "revenue", "other_revenue", "credit"),
    # Expense accounts (5xxx-7xxx)
    ("5110", "Faculty Salaries", "expense", "salaries", "debit"),
    ("5120", "Staff Salaries", "expense", "salaries", "debit"),
    ("5130", "Graduate Student Stipends", "expense", "salaries", "debit"),
    ("5140", "Temporary/Hourly Wages", "expense", "salaries", "debit"),
    ("5200", "Employee Benefits", "expense", "benefits", "debit"),
    ("5210", "Health Insurance", "expense", "benefits", "debit"),
    ("5220", "Retirement Contributions", "expense", "benefits", "debit"),
    ("5230", "Tuition Remission", "expense", "benefits", "debit"),
    ("6100", "Office Supplies", "expense", "supplies", "debit"),
    ("6110", "Lab Supplies", "expense", "supplies", "debit"),
    ("6120", "Computer Supplies", "expense", "supplies", "debit"),
    ("6130", "Medical Supplies", "expense", "supplies", "debit"),
    ("6200", "Travel - Domestic", "expense", "travel", "debit"),
    ("6210", "Travel - International", "expense", "travel", "debit"),
    ("6220", "Conference Registration", "expense", "travel", "debit"),
    ("6300", "Equipment Purchases", "expense", "equipment", "debit"),
    ("6310", "Computer Equipment", "expense", "equipment", "debit"),
    ("6320", "Lab Equipment", "expense", "equipment", "debit"),
    ("6330", "Furniture", "expense", "equipment", "debit"),
    ("6400", "Telecommunications", "expense", "services", "debit"),
    ("6410", "Software Licenses", "expense", "services", "debit"),
    ("6420", "Cloud Computing", "expense", "services", "debit"),
    ("6430", "Consulting Services", "expense", "services", "debit"),
    ("6440", "Maintenance Contracts", "expense", "services", "debit"),
    ("6500", "Utilities", "expense", "facilities", "debit"),
    ("6510", "Rent", "expense", "facilities", "debit"),
    ("6520", "Building Maintenance", "expense", "facilities", "debit"),
    ("6600", "Scholarships & Fellowships", "expense", "financial_aid", "debit"),
    ("6610", "Graduate Fellowships", "expense", "financial_aid", "debit"),
    ("6620", "Undergraduate Scholarships", "expense", "financial_aid", "debit"),
    ("6700", "Subcontracts", "expense", "subcontracts", "debit"),
    ("6800", "Printing & Publications", "expense", "other_expense", "debit"),
    ("6810", "Postage & Shipping", "expense", "other_expense", "debit"),
    ("6820", "Memberships & Dues", "expense", "other_expense", "debit"),
    ("6830", "Insurance", "expense", "other_expense", "debit"),
    ("6900", "Depreciation", "expense", "depreciation", "debit"),
    ("7000", "Internal Transfers", "expense", "transfers", "debit"),
    ("7100", "Debt Service", "expense", "debt_service", "debit"),
    # Asset accounts (1xxx)
    ("1100", "Cash & Equivalents", "asset", "cash", "debit"),
    ("1200", "Accounts Receivable", "asset", "receivables", "debit"),
    ("1210", "Grants Receivable", "asset", "receivables", "debit"),
    ("1300", "Prepaid Expenses", "asset", "prepaid", "debit"),
    ("1400", "Investments", "asset", "investments", "debit"),
    ("1500", "Land", "asset", "fixed_assets", "debit"),
    ("1510", "Buildings", "asset", "fixed_assets", "debit"),
    ("1520", "Equipment (Capital)", "asset", "fixed_assets", "debit"),
    ("1530", "Accumulated Depreciation", "asset", "contra_asset", "credit"),
    # Liability accounts (2xxx)
    ("2100", "Accounts Payable", "liability", "payables", "credit"),
    ("2200", "Accrued Salaries", "liability", "accrued", "credit"),
    ("2210", "Accrued Benefits", "liability", "accrued", "credit"),
    ("2300", "Deferred Revenue", "liability", "deferred", "credit"),
    ("2310", "Deferred Tuition", "liability", "deferred", "credit"),
    ("2400", "Bonds Payable", "liability", "long_term_debt", "credit"),
    # Equity / Net Assets (3xxx)
    ("3100", "Unrestricted Net Assets", "equity", "net_assets", "credit"),
    ("3200", "Temporarily Restricted", "equity", "net_assets", "credit"),
    ("3300", "Permanently Restricted", "equity", "net_assets", "credit"),
]

GRANT_SPONSORS = [
    "National Science Foundation",
    "National Institutes of Health",
    "Department of Defense",
    "Department of Energy",
    "NASA",
    "DARPA",
    "Howard Hughes Medical Institute",
    "Bill & Melinda Gates Foundation",
    "Andrew W. Mellon Foundation",
    "Ford Foundation",
    "Alfred P. Sloan Foundation",
    "National Endowment for the Humanities",
    "American Heart Association",
    "American Cancer Society",
    "Simons Foundation",
]

VENDORS = {
    "supplies": [
        "Fisher Scientific", "VWR International", "Sigma-Aldrich", "Staples Business",
        "Amazon Business", "CDW Government", "Grainger", "Thomas Scientific",
        "Carolina Biological", "Office Depot Business",
    ],
    "equipment": [
        "Dell Technologies", "Apple Inc.", "Lenovo", "HP Enterprise",
        "Thermo Fisher Scientific", "Agilent Technologies", "Bio-Rad Laboratories",
        "Herman Miller", "Steelcase",
    ],
    "services": [
        "Microsoft Corporation", "Adobe Systems", "Amazon Web Services",
        "Google Cloud", "Deloitte Consulting", "McKinsey & Company",
        "KPMG", "Oracle Corporation", "Salesforce", "ServiceNow",
    ],
    "travel": [
        "American Airlines", "Delta Air Lines", "United Airlines",
        "Marriott International", "Hilton Hotels", "Enterprise Rent-A-Car",
    ],
    "facilities": [
        "Duke Power", "Piedmont Natural Gas", "CBRE Group",
        "Johnson Controls", "Siemens Building Technologies",
    ],
}

SOURCE_SYSTEMS = ["SAP", "Concur", "Workday", "Manual"]


def generate_departments(conn: sqlite3.Connection) -> list[tuple[str, str, str]]:
    """Create departments table and return list of (code, name, school)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            department_code TEXT PRIMARY KEY,
            department_name TEXT NOT NULL,
            division TEXT NOT NULL,
            school TEXT NOT NULL
        )
    """)

    departments = []
    for school, depts in SCHOOLS.items():
        division = school
        for code, name in depts:
            departments.append((code, name, division, school))

    conn.executemany(
        "INSERT INTO departments VALUES (?, ?, ?, ?)",
        departments,
    )
    conn.commit()
    return [(d[0], d[1], d[3]) for d in departments]


def generate_chart_of_accounts(conn: sqlite3.Connection) -> None:
    """Create chart_of_accounts table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chart_of_accounts (
            account_code TEXT PRIMARY KEY,
            account_name TEXT NOT NULL,
            account_category TEXT NOT NULL,
            account_subcategory TEXT NOT NULL,
            normal_balance TEXT NOT NULL
        )
    """)
    conn.executemany(
        "INSERT INTO chart_of_accounts VALUES (?, ?, ?, ?, ?)",
        CHART_OF_ACCOUNTS,
    )
    conn.commit()


def generate_funds(conn: sqlite3.Connection) -> None:
    """Create funds table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS funds (
            fund_code TEXT PRIMARY KEY,
            fund_name TEXT NOT NULL,
            fund_type TEXT NOT NULL,
            description TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO funds VALUES (?, ?, ?, ?)",
        FUNDS,
    )
    conn.commit()


def generate_grants(
    conn: sqlite3.Connection, departments: list[tuple[str, str, str]], count: int = 200
) -> list[dict]:
    """Create grants table and generate grant records."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS grants (
            grant_id TEXT PRIMARY KEY,
            grant_name TEXT NOT NULL,
            grant_pi TEXT NOT NULL,
            sponsor TEXT NOT NULL,
            department_code TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            total_budget REAL NOT NULL,
            remaining_budget REAL NOT NULL,
            status TEXT NOT NULL
        )
    """)

    # Filter to research-active departments
    research_depts = [
        d for d in departments
        if d[2] in ("Arts & Sciences", "Engineering", "Medicine", "Public Policy")
    ]

    grants = []
    for i in range(count):
        dept = random.choice(research_depts)
        sponsor = random.choice(GRANT_SPONSORS)
        pi_name = f"{fake.first_name()} {fake.last_name()}"

        # Grant spans 2-5 years
        start = date(random.randint(2020, 2024), random.randint(1, 12), 1)
        duration_years = random.randint(2, 5)
        end = start.replace(year=start.year + duration_years)

        total_budget = round(random.uniform(50_000, 5_000_000), 2)
        # Spending progress based on how far into the grant period
        today = date(2025, 6, 30)
        if end <= today:
            spent_pct = random.uniform(0.85, 1.0)
            status = "closed"
        elif start > today:
            spent_pct = 0.0
            status = "pending"
        else:
            elapsed = (today - start).days
            total_days = (end - start).days
            spent_pct = min(0.95, (elapsed / total_days) * random.uniform(0.7, 1.3))
            status = "active"

        remaining = round(total_budget * (1 - spent_pct), 2)

        sponsor_prefix = {
            "National Science Foundation": "NSF",
            "National Institutes of Health": "NIH",
            "Department of Defense": "DOD",
            "Department of Energy": "DOE",
        }.get(sponsor, sponsor[:3].upper())

        grant_id = f"{sponsor_prefix}-{random.randint(1000000, 9999999)}"
        grant_name = f"{sponsor_prefix} Award #{random.randint(1000000, 9999999)}: {fake.catch_phrase()}"

        grants.append({
            "grant_id": grant_id,
            "grant_name": grant_name,
            "grant_pi": pi_name,
            "sponsor": sponsor,
            "department_code": dept[0],
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "total_budget": total_budget,
            "remaining_budget": max(0, remaining),
            "status": status,
        })

    conn.executemany(
        "INSERT INTO grants VALUES (:grant_id, :grant_name, :grant_pi, :sponsor, "
        ":department_code, :start_date, :end_date, :total_budget, :remaining_budget, :status)",
        grants,
    )
    conn.commit()
    return grants


def create_transactions_table(conn: sqlite3.Connection) -> None:
    """Create the main gl_transactions table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gl_transactions (
            transaction_id TEXT PRIMARY KEY,
            fiscal_year INTEGER NOT NULL,
            fiscal_period INTEGER NOT NULL,
            transaction_date TEXT NOT NULL,
            posting_date TEXT NOT NULL,
            department_code TEXT NOT NULL,
            department_name TEXT NOT NULL,
            fund_code TEXT NOT NULL,
            fund_name TEXT NOT NULL,
            fund_type TEXT NOT NULL,
            account_code TEXT NOT NULL,
            account_name TEXT NOT NULL,
            account_category TEXT NOT NULL,
            account_subcategory TEXT NOT NULL,
            amount REAL NOT NULL,
            budget_amount REAL,
            encumbrance_amount REAL,
            encumbrance_type TEXT,
            vendor_name TEXT,
            description TEXT NOT NULL,
            grant_id TEXT,
            grant_name TEXT,
            grant_pi TEXT,
            grant_start_date TEXT,
            grant_end_date TEXT,
            grant_total_budget REAL,
            source_system TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            is_adjustment INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()


def fiscal_period_for_date(d: date) -> tuple[int, int]:
    """Convert a calendar date to fiscal year and period.

    Higher-ed fiscal year: July 1 - June 30.
    Period 1 = July, Period 12 = June.
    """
    if d.month >= 7:
        fy = d.year + 1
        period = d.month - 6
    else:
        fy = d.year
        period = d.month + 6
    return fy, period


def seasonal_weight(period: int) -> float:
    """Spending weight by fiscal period. Higher in Q1 (Jul-Sep) and Q4 (Apr-Jun)."""
    weights = {
        1: 1.3, 2: 1.2, 3: 1.1,    # Jul-Sep: startup spending
        4: 0.9, 5: 0.8, 6: 0.7,    # Oct-Dec: slower
        7: 0.8, 8: 0.9, 9: 1.0,    # Jan-Mar: ramps up
        10: 1.1, 11: 1.2, 12: 1.4, # Apr-Jun: year-end spending
    }
    return weights.get(period, 1.0)


def generate_transactions(
    conn: sqlite3.Connection,
    departments: list[tuple[str, str, str]],
    grants: list[dict],
    target_count: int = 500_000,
) -> int:
    """Generate GL transactions in batches."""
    expense_accounts = [a for a in CHART_OF_ACCOUNTS if a[2] == "expense"]
    revenue_accounts = [a for a in CHART_OF_ACCOUNTS if a[2] == "revenue"]
    active_grants = [g for g in grants if g["status"] in ("active", "closed")]

    # Fund weights: 70% operating, 15% grants, 5% endowment, 7% auxiliary, 3% agency
    fund_weights = [
        (FUNDS[0], 0.55),   # General Operating
        (FUNDS[1], 0.15),   # Restricted Grants
        (FUNDS[2], 0.03),   # Restricted Gifts
        (FUNDS[3], 0.05),   # Endowment
        (FUNDS[4], 0.07),   # Auxiliary
        (FUNDS[5], 0.03),   # Agency
        (FUNDS[6], 0.07),   # Plant
        (FUNDS[7], 0.05),   # Loan
    ]
    fund_items = [f[0] for f in fund_weights]
    fund_probs = [f[1] for f in fund_weights]

    # Date range: FY2022 (Jul 2021) through FY2025 (Jun 2025)
    start_date = date(2021, 7, 1)
    end_date = date(2025, 6, 30)
    total_days = (end_date - start_date).days

    batch_size = 10_000
    batch = []
    count = 0

    print(f"Generating {target_count:,} transactions...")

    while count < target_count:
        # Random date with seasonal weighting
        d = start_date + timedelta(days=random.randint(0, total_days))
        fy, period = fiscal_period_for_date(d)

        # Skip some based on seasonal weight (rejection sampling)
        if random.random() > seasonal_weight(period) / 1.4:
            continue

        dept_code, dept_name, school = random.choice(departments)
        fund = random.choices(fund_items, weights=fund_probs, k=1)[0]
        fund_code, fund_name, fund_type, fund_desc = fund

        # Determine entry type: 85% actual, 10% budget, 5% encumbrance
        entry_roll = random.random()
        if entry_roll < 0.85:
            entry_type = "actual"
        elif entry_roll < 0.95:
            entry_type = "budget"
        else:
            entry_type = "encumbrance"

        # Pick account based on entry type
        if entry_type == "budget" and random.random() < 0.3:
            acct = random.choice(revenue_accounts)
        else:
            acct = random.choice(expense_accounts)

        acct_code, acct_name, acct_cat, acct_subcat, normal_bal = acct

        # Amount generation based on account type
        amount_ranges = {
            "salaries": (2_000, 25_000),
            "benefits": (500, 8_000),
            "supplies": (10, 5_000),
            "travel": (100, 8_000),
            "equipment": (500, 150_000),
            "services": (100, 50_000),
            "facilities": (500, 30_000),
            "financial_aid": (1_000, 50_000),
            "subcontracts": (5_000, 200_000),
            "other_expense": (50, 10_000),
            "depreciation": (100, 20_000),
            "transfers": (1_000, 100_000),
            "debt_service": (5_000, 50_000),
            "tuition_revenue": (5_000, 50_000),
            "grant_revenue": (10_000, 500_000),
            "gift_revenue": (100, 100_000),
            "investment_income": (1_000, 200_000),
            "auxiliary_revenue": (500, 25_000),
            "clinical_revenue": (1_000, 50_000),
            "idc_revenue": (1_000, 100_000),
            "state_funding": (50_000, 500_000),
            "other_revenue": (100, 20_000),
        }
        lo, hi = amount_ranges.get(acct_subcat, (100, 10_000))
        amount = round(random.uniform(lo, hi), 2)

        # Grant info for restricted fund transactions
        grant_id = grant_name = grant_pi = None
        grant_start = grant_end = None
        grant_budget = None
        if fund_type == "restricted" and active_grants:
            g = random.choice(active_grants)
            grant_id = g["grant_id"]
            grant_name = g["grant_name"]
            grant_pi = g["grant_pi"]
            grant_start = g["start_date"]
            grant_end = g["end_date"]
            grant_budget = g["total_budget"]

        # Vendor for expense actuals
        vendor = None
        if acct_cat == "expense" and entry_type == "actual":
            vendor_cat = acct_subcat if acct_subcat in VENDORS else "supplies"
            vendor = random.choice(VENDORS.get(vendor_cat, VENDORS["supplies"]))

        # Budget and encumbrance amounts
        budget_amt = None
        enc_amt = None
        enc_type = None
        if entry_type == "budget":
            budget_amt = amount
            amount = 0
        elif entry_type == "encumbrance":
            enc_amt = amount
            enc_type = random.choice(["purchase_order", "contract", "salary_commitment"])
            amount = 0
        elif entry_type == "actual" and random.random() < 0.15:
            enc_amt = round(amount * random.uniform(0.8, 1.2), 2)
            enc_type = random.choice(["purchase_order", "contract", "salary_commitment"])

        is_adj = 1 if random.random() < 0.03 else 0

        # Description
        if entry_type == "budget":
            desc = f"FY{fy} Budget - {acct_name} - {dept_name}"
        elif entry_type == "encumbrance":
            desc = f"Encumbrance: {enc_type.replace('_', ' ').title()} - {acct_name}"
        elif is_adj:
            desc = f"Adjustment: {acct_name} - {fake.sentence(nb_words=4)}"
        elif vendor:
            desc = f"{vendor} - {fake.sentence(nb_words=5)}"
        else:
            desc = f"{acct_name} - {fake.sentence(nb_words=5)}"

        source = random.choice(SOURCE_SYSTEMS)

        # Posting date is same day or up to 5 business days later
        posting_d = d + timedelta(days=random.randint(0, 5))

        batch.append((
            str(uuid.uuid4()),
            fy, period,
            d.isoformat(), posting_d.isoformat(),
            dept_code, dept_name,
            fund_code, fund_name, fund_type,
            acct_code, acct_name, acct_cat, acct_subcat,
            amount, budget_amt, enc_amt, enc_type,
            vendor, desc,
            grant_id, grant_name, grant_pi, grant_start, grant_end, grant_budget,
            source, entry_type, is_adj,
        ))

        count += 1

        if len(batch) >= batch_size:
            conn.executemany(
                "INSERT INTO gl_transactions VALUES ("
                + ",".join(["?"] * 29) + ")",
                batch,
            )
            conn.commit()
            batch = []
            print(f"  {count:>8,} / {target_count:,} transactions generated...")

    # Flush remaining
    if batch:
        conn.executemany(
            "INSERT INTO gl_transactions VALUES ("
            + ",".join(["?"] * 29) + ")",
            batch,
        )
        conn.commit()

    return count


def create_indexes(conn: sqlite3.Connection) -> None:
    """Create indexes for common query patterns."""
    indexes = [
        "CREATE INDEX idx_gl_fiscal_year ON gl_transactions(fiscal_year)",
        "CREATE INDEX idx_gl_fiscal_period ON gl_transactions(fiscal_year, fiscal_period)",
        "CREATE INDEX idx_gl_department ON gl_transactions(department_code)",
        "CREATE INDEX idx_gl_fund ON gl_transactions(fund_code)",
        "CREATE INDEX idx_gl_fund_type ON gl_transactions(fund_type)",
        "CREATE INDEX idx_gl_account ON gl_transactions(account_code)",
        "CREATE INDEX idx_gl_account_cat ON gl_transactions(account_category)",
        "CREATE INDEX idx_gl_entry_type ON gl_transactions(entry_type)",
        "CREATE INDEX idx_gl_grant ON gl_transactions(grant_id)",
        "CREATE INDEX idx_gl_vendor ON gl_transactions(vendor_name)",
        "CREATE INDEX idx_gl_date ON gl_transactions(transaction_date)",
        "CREATE INDEX idx_gl_dept_fy ON gl_transactions(department_code, fiscal_year)",
    ]
    print("Creating indexes...")
    for sql in indexes:
        conn.execute(sql)
    conn.commit()


def print_summary(conn: sqlite3.Connection) -> None:
    """Print a summary of the generated data."""
    row = conn.execute("SELECT COUNT(*) FROM gl_transactions").fetchone()
    print(f"\n{'='*60}")
    print(f"Dataset Summary")
    print(f"{'='*60}")
    print(f"Total transactions: {row[0]:,}")

    row = conn.execute("SELECT COUNT(*) FROM departments").fetchone()
    print(f"Departments: {row[0]}")

    row = conn.execute("SELECT COUNT(*) FROM chart_of_accounts").fetchone()
    print(f"GL Accounts: {row[0]}")

    row = conn.execute("SELECT COUNT(*) FROM grants").fetchone()
    print(f"Grants: {row[0]}")

    print(f"\nBy entry type:")
    for row in conn.execute(
        "SELECT entry_type, COUNT(*), ROUND(SUM(amount), 2) "
        "FROM gl_transactions GROUP BY entry_type ORDER BY COUNT(*) DESC"
    ):
        print(f"  {row[0]:15s} {row[1]:>10,} rows  ${row[2]:>15,.2f}")

    print(f"\nBy fund type:")
    for row in conn.execute(
        "SELECT fund_type, COUNT(*) FROM gl_transactions "
        "GROUP BY fund_type ORDER BY COUNT(*) DESC"
    ):
        print(f"  {row[0]:15s} {row[1]:>10,} rows")

    print(f"\nBy fiscal year:")
    for row in conn.execute(
        "SELECT fiscal_year, COUNT(*), ROUND(SUM(amount), 2) "
        "FROM gl_transactions GROUP BY fiscal_year ORDER BY fiscal_year"
    ):
        print(f"  FY{row[0]}  {row[1]:>10,} rows  ${row[2]:>15,.2f}")

    # Database file size
    page_count = conn.execute("PRAGMA page_count").fetchone()[0]
    page_size = conn.execute("PRAGMA page_size").fetchone()[0]
    db_size_mb = (page_count * page_size) / (1024 * 1024)
    print(f"\nDatabase size: {db_size_mb:.1f} MB")


def main():
    parser = argparse.ArgumentParser(description="Generate university GL dataset")
    parser.add_argument(
        "--output", default="data/university_gl.db",
        help="Output SQLite database path (default: data/university_gl.db)",
    )
    parser.add_argument(
        "--transactions", type=int, default=500_000,
        help="Number of transactions to generate (default: 500000)",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database
    if output_path.exists():
        output_path.unlink()
        print(f"Removed existing database: {output_path}")

    conn = sqlite3.connect(str(output_path))

    # Enable WAL mode for better write performance
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    print("Generating reference data...")
    departments = generate_departments(conn)
    generate_chart_of_accounts(conn)
    generate_funds(conn)
    grants = generate_grants(conn, departments)

    create_transactions_table(conn)
    count = generate_transactions(conn, departments, grants, args.transactions)

    create_indexes(conn)
    print_summary(conn)

    conn.close()
    print(f"\nDatabase written to: {output_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Update README.md**

Append to `README.md`:

```markdown
## Step 04: Financial Dataset Generator

This step creates a synthetic university general ledger dataset with ~500K+ transactions.

### Fund Accounting Concepts

Universities use **fund accounting** — money is tracked by purpose, not just by department:

| Fund Type | Purpose | Example |
|-----------|---------|---------|
| Unrestricted (Operating) | General university operations | Faculty salaries, utilities |
| Restricted (Grants) | Externally funded research | NSF grants, NIH awards |
| Endowment | Investment returns on permanent gifts | Endowed chair income |
| Auxiliary | Self-supporting operations | Housing, dining, parking |
| Agency | Held on behalf of others | Student organization funds |

### Other key concepts

- **Chart of Accounts** — hierarchical numbering system for GL accounts (4xxx = revenue, 5xxx-7xxx = expenses, 1xxx = assets, 2xxx = liabilities)
- **Fiscal Year** — universities use July 1 - June 30 (FY2025 = July 2024 - June 2025)
- **Encumbrances** — commitments to spend (purchase orders, contracts) that reserve budget but haven't been paid yet
- **Budget entries** — planned spending tracked alongside actual spending
- **Indirect Cost Recovery (IDC)** — overhead charges on grants that reimburse the university for facilities and administration

### Generating the data

```bash
pip install -r requirements.txt
python generate_data.py
# Or customize:
python generate_data.py --output data/university_gl.db --transactions 500000
```

The generated database is ~150-200MB with 500K transactions.
```

- [ ] **Step 5: Generate the dataset and verify**

```bash
python generate_data.py --transactions 500000
```

Expected: Output showing transaction counts, fund types, fiscal years. Database at `data/university_gl.db`.

- [ ] **Step 6: Commit (excluding the .db file)**

```bash
git add generate_data.py requirements.txt README.md .gitignore
git commit -m "feat: step-04 university GL dataset generator

Generates 500K+ synthetic financial transactions with fund
accounting, chart of accounts, grants, and encumbrances."
```

---

## Task 5: step-05 — Basic Financial Query Server

**Branch:** `step-05` (from `step-04`)

**Files:**
- Create: `financial_server.py`
- Create: `database.py`
- Create: `config.py`
- Create: `.env.example`
- Modify: `requirements.txt`
- Modify: `README.md`

- [ ] **Step 1: Create branch**

```bash
git checkout step-04
git checkout -b step-05
```

- [ ] **Step 2: Update requirements.txt**

```
fastmcp>=2.14.0
uvicorn>=0.34.0
faker>=33.0.0
aiosqlite>=0.20.0
pydantic-settings>=2.10.0
python-dotenv>=1.0.0
```

- [ ] **Step 3: Create config.py**

```python
"""Configuration settings for the Financial MCP Server."""

import logging
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    server_host: str = Field(default="0.0.0.0")
    server_port: int = Field(default=8000)

    # Database
    database_path: str = Field(
        default="data/university_gl.db",
        description="Path to the SQLite database",
    )

    # Query limits
    max_rows: int = Field(default=2000, description="Max rows returned per query")
    warning_rows: int = Field(default=100, description="Row count that triggers a warning")

    # Logging
    log_level: str = Field(default="INFO")

    @property
    def database_path_resolved(self) -> Path:
        return Path(self.database_path)

    def get_log_level(self) -> int:
        levels = {
            "DEBUG": logging.DEBUG, "INFO": logging.INFO,
            "WARNING": logging.WARNING, "ERROR": logging.ERROR,
        }
        return levels.get(self.log_level.upper(), logging.INFO)


def load_config() -> Settings:
    return Settings()
```

- [ ] **Step 4: Create database.py**

```python
"""Async database layer with SQL safety for the Financial MCP Server."""

import logging
import re
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

# Tables that queries are allowed to reference
ALLOWED_TABLES = {"gl_transactions", "departments", "chart_of_accounts", "funds", "grants"}

# Patterns that indicate dangerous SQL
DANGEROUS_PATTERNS = [
    re.compile(r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE|REPLACE)\b", re.IGNORECASE),
    re.compile(r"\b(ATTACH|DETACH)\b", re.IGNORECASE),
    re.compile(r"--"),  # SQL comments
    re.compile(r"/\*"),  # Block comments
]


class DatabaseError(Exception):
    """Raised for database-related errors."""
    pass


class SQLValidationError(DatabaseError):
    """Raised when SQL fails validation."""
    pass


def validate_sql(sql: str) -> None:
    """Validate that a SQL query is safe to execute.

    Only SELECT queries are allowed. Dangerous keywords and patterns are blocked.

    Raises:
        SQLValidationError: If the query fails validation.
    """
    stripped = sql.strip().rstrip(";")

    if not stripped.upper().startswith("SELECT"):
        raise SQLValidationError("Only SELECT queries are allowed.")

    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(stripped):
            raise SQLValidationError(
                f"Query contains disallowed pattern: {pattern.pattern}"
            )


async def get_connection(db_path: Path) -> aiosqlite.Connection:
    """Open an async SQLite connection."""
    if not db_path.exists():
        raise DatabaseError(f"Database not found: {db_path}")
    conn = await aiosqlite.connect(str(db_path))
    conn.row_factory = aiosqlite.Row
    return conn


async def execute_query(
    db_path: Path, sql: str, max_rows: int = 2000
) -> tuple[list[dict], int]:
    """Execute a validated SELECT query and return results.

    Returns:
        Tuple of (rows as list of dicts, total row count before limiting).
    """
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
    """Get information about all tables in the database."""
    conn = await get_connection(db_path)
    try:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
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
                tables.append({
                    "table_name": table_name,
                    "row_count": count,
                    "columns": columns,
                })
        return tables
    finally:
        await conn.close()


async def get_column_info(db_path: Path, table_name: str) -> dict:
    """Get detailed column information for a specific table."""
    if table_name not in ALLOWED_TABLES:
        raise SQLValidationError(f"Table not allowed: {table_name}")

    conn = await get_connection(db_path)
    try:
        col_cursor = await conn.execute(f"PRAGMA table_info([{table_name}])")
        columns = []
        for col in await col_cursor.fetchall():
            columns.append({
                "name": col[1],
                "type": col[2],
                "nullable": not col[3],
                "primary_key": bool(col[5]),
            })

        count_cursor = await conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        count = (await count_cursor.fetchone())[0]

        return {
            "table_name": table_name,
            "row_count": count,
            "columns": columns,
        }
    finally:
        await conn.close()
```

- [ ] **Step 5: Create financial_server.py**

```python
"""
Step 05: Financial Query MCP Server

A database-backed MCP server for querying university general ledger data.
Provides SQL query execution with safety checks, schema resources, and
domain knowledge resources.
"""

import json
import logging

from fastmcp import FastMCP, Context

from config import load_config, Settings
from database import execute_query, get_table_info, get_column_info, SQLValidationError, DatabaseError

config = load_config()
logging.basicConfig(level=config.get_log_level(), format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "FinancialData",
    instructions=(
        "University General Ledger query server. Use the schema:// resources to "
        "discover tables and columns. Use domain:// resources to understand fund "
        "accounting concepts. Use query_sql to execute SELECT queries."
    ),
)


# === Tools ===


@mcp.tool
async def query_sql(sql: str, ctx: Context) -> str:
    """Execute a SQL SELECT query against the university general ledger database.

    IMPORTANT:
    - Only SELECT queries are allowed (read-only access).
    - Results are limited to 2000 rows. If your query returns more, add a LIMIT clause.
    - Use schema:// resources to discover available tables and columns.
    - Use domain:// resources to understand fund accounting terminology.
    """
    try:
        rows, total = await execute_query(
            config.database_path_resolved, sql, max_rows=config.max_rows
        )
    except SQLValidationError as e:
        return f"Query validation error: {e}"
    except DatabaseError as e:
        return f"Database error: {e}"

    if total > config.warning_rows:
        await ctx.warning(
            f"Query returned {total:,} rows (showing first {min(total, config.max_rows):,}). "
            f"Consider adding a LIMIT clause or more specific WHERE conditions."
        )

    if total > config.max_rows:
        await ctx.info(f"Results truncated from {total:,} to {config.max_rows:,} rows.")

    return json.dumps({
        "total_rows": total,
        "returned_rows": len(rows),
        "truncated": total > config.max_rows,
        "data": rows,
    })


@mcp.tool
async def get_database_info(ctx: Context) -> str:
    """Get a summary of all tables, their columns, and row counts.

    Call this first to understand the database structure before writing queries.
    """
    try:
        tables = await get_table_info(config.database_path_resolved)
    except DatabaseError as e:
        return f"Error: {e}"

    await ctx.info(f"Found {len(tables)} tables")
    return json.dumps(tables, indent=2)


# === Schema Resources ===


@mcp.resource("schema://tables", mime_type="application/json")
async def list_tables() -> str:
    """List all available tables with their row counts."""
    tables = await get_table_info(config.database_path_resolved)
    summary = [
        {"table": t["table_name"], "rows": t["row_count"], "columns": len(t["columns"])}
        for t in tables
    ]
    return json.dumps(summary, indent=2)


@mcp.resource("schema://{table_name}/columns", mime_type="application/json")
async def table_columns(table_name: str) -> str:
    """Get column details for a specific table."""
    try:
        info = await get_column_info(config.database_path_resolved, table_name)
    except SQLValidationError as e:
        return json.dumps({"error": str(e)})
    return json.dumps(info, indent=2)


# === Domain Resources ===


@mcp.resource("domain://funds", mime_type="text/markdown")
def fund_types() -> str:
    """Explains university fund accounting types."""
    return """# Fund Types in University Accounting

| Fund Code | Name | Type | Description |
|-----------|------|------|-------------|
| 10 | General Operating | Unrestricted | Primary university operations — faculty salaries, utilities, supplies |
| 20 | Restricted Grants | Restricted | Externally sponsored research (NSF, NIH, DOD). Must be spent per grant terms |
| 25 | Restricted Gifts | Restricted | Donor-restricted gifts. Spending limited to donor's specified purpose |
| 30 | Endowment | Endowment | Permanent funds — only investment returns can be spent |
| 40 | Auxiliary Enterprises | Auxiliary | Self-supporting: housing, dining, parking, bookstore |
| 50 | Agency Funds | Agency | Held on behalf of student organizations and affiliates |
| 60 | Plant Funds | Unrestricted | Capital projects, building construction, major equipment |
| 70 | Loan Funds | Restricted | Student loan programs (Perkins, institutional) |

## Key concepts

- **Restricted vs Unrestricted**: Restricted funds have external constraints on how they can be spent
- **Encumbrances**: Commitments (purchase orders, contracts) that reserve budget but haven't been paid
- **Budget vs Actual**: Budget entries show planned spending; actual entries show real spending
- **Indirect Cost Recovery (IDC)**: Overhead charges on grants (~50-60% of direct costs)
"""


@mcp.resource("domain://accounts", mime_type="text/markdown")
def chart_of_accounts() -> str:
    """Explains the chart of accounts structure."""
    return """# Chart of Accounts

University GL accounts follow a standard numbering system:

| Range | Category | Examples |
|-------|----------|----------|
| 1xxx | Assets | Cash, Receivables, Investments, Buildings |
| 2xxx | Liabilities | Accounts Payable, Deferred Revenue, Bonds |
| 3xxx | Net Assets (Equity) | Unrestricted, Temporarily Restricted, Permanently Restricted |
| 4xxx | Revenue | Tuition, Grants, Gifts, Investment Income, Clinical Revenue |
| 5xxx | Salaries & Benefits | Faculty Salaries, Staff Salaries, Benefits, Stipends |
| 6xxx | Operating Expenses | Supplies, Travel, Equipment, Services, Facilities |
| 7xxx | Transfers & Debt | Internal Transfers, Debt Service |

## Key subcategories for expenses

- **salaries** (5110-5140): Faculty, staff, graduate stipends, hourly wages
- **benefits** (5200-5230): Health insurance, retirement, tuition remission
- **supplies** (6100-6130): Office, lab, computer, medical supplies
- **travel** (6200-6220): Domestic, international, conference registration
- **equipment** (6300-6330): Computers, lab equipment, furniture (capital items)
- **services** (6400-6440): Software, cloud computing, consulting, maintenance
"""


@mcp.resource("domain://departments", mime_type="text/markdown")
def department_list() -> str:
    """Lists all departments organized by school."""
    return """# University Departments

## Arts & Sciences
COMPSCI (Computer Science), MATH (Mathematics), PHYS (Physics), CHEM (Chemistry),
BIO (Biology), ENGLISH (English), HISTORY (History), POLISCI (Political Science),
ECON (Economics), PSYCH (Psychology), SOCIOL (Sociology), PHILO (Philosophy),
ROMANCE (Romance Studies), STATS (Statistical Science), NEURO (Neuroscience)

## Engineering
ECE (Electrical & Computer Engineering), MECHENG (Mechanical Engineering),
CIVENG (Civil & Environmental Engineering), BME (Biomedical Engineering),
MATSCI (Materials Science)

## Medicine
MEDSCHOOL (School of Medicine), PATHOL (Pathology), PEDS (Pediatrics),
SURG (Surgery), NEUROMD (Neurology), CARDIO (Cardiology),
ONCOL (Oncology), RADIOL (Radiology)

## Law
LAW (School of Law), LAWCLIN (Law Clinical Programs)

## Business
BUSINESS (School of Business), FINANCE (Finance Department), MKTG (Marketing)

## Other Schools
PUBPOL (Public Policy), ENVIRON (Environmental Policy), NURSING (School of Nursing),
DIVINITY (Divinity School), GRADSCH (Graduate School Administration)

## Central Administration
PROVOST (Provost Office), FINAID (Financial Aid), REGIST (Registrar),
ITDEPT (Information Technology), FACMGMT (Facilities Management), HR (Human Resources),
LIBR (University Libraries), ATHLET (Athletics), ALUMNI (Alumni Affairs),
RESADM (Research Administration)
"""


# === Entry Point ===


if __name__ == "__main__":
    mcp.run(transport="http", host=config.server_host, port=config.server_port)
```

- [ ] **Step 6: Create .env.example**

```
# Financial MCP Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DATABASE_PATH=data/university_gl.db
MAX_ROWS=2000
WARNING_ROWS=100
LOG_LEVEL=INFO
```

- [ ] **Step 7: Update README.md**

Append to `README.md`:

```markdown
## Step 05: Basic Financial Query Server

This is the first "real" MCP server — a database-backed query engine for university financial data.

### Architecture

```
financial_server.py  — MCP server (tools, resources)
database.py          — async SQLite layer with SQL safety
config.py            — Pydantic settings from .env
```

### Tools

- `query_sql(sql)` — Execute a SELECT query. Returns JSON with data and row counts.
- `get_database_info()` — List all tables, columns, and row counts.

### Resources

- `schema://tables` — Table listing
- `schema://{table_name}/columns` — Column details for any table
- `domain://funds` — Fund accounting explanation
- `domain://accounts` — Chart of accounts reference
- `domain://departments` — Department listing by school

### SQL Safety

The server enforces read-only access:
1. Only `SELECT` queries are allowed
2. Dangerous keywords are blocked (DROP, DELETE, INSERT, etc.)
3. Results are limited to 2,000 rows with warnings at 100+
4. Only known tables can be queried

### Running

```bash
# Generate the dataset first (step-04)
python generate_data.py

# Copy and configure environment
cp .env.example .env

# Start the server
python financial_server.py
```
```

- [ ] **Step 8: Commit**

```bash
git add financial_server.py database.py config.py .env.example requirements.txt README.md
git commit -m "feat: step-05 basic financial query server

SQLite-backed MCP server with query_sql tool, schema resources,
domain knowledge resources, and SQL injection prevention."
```

---

## Task 6: step-06 — Natural Language to SQL

**Branch:** `step-06` (from `step-05`)

**Files:**
- Create: `nl2sql.py`
- Modify: `financial_server.py`
- Modify: `requirements.txt`
- Modify: `README.md`

- [ ] **Step 1: Create branch**

```bash
git checkout step-05
git checkout -b step-06
```

- [ ] **Step 2: Update requirements.txt**

Add `anthropic` and `openai`:

```
fastmcp>=2.14.0
uvicorn>=0.34.0
faker>=33.0.0
aiosqlite>=0.20.0
pydantic-settings>=2.10.0
python-dotenv>=1.0.0
anthropic>=0.40.0
openai>=1.0.0
```

- [ ] **Step 3: Update config.py**

Add LLM configuration fields to the Settings class:

```python
    # LLM Configuration (for NL-to-SQL)
    anthropic_api_key: str = Field(default="", description="Anthropic API key for NL-to-SQL")
    anthropic_model: str = Field(default="claude-sonnet-4-5", description="Anthropic model")
    openai_api_key: str = Field(default="", description="OpenAI API key for NL-to-SQL")
    openai_base_url: str = Field(default="", description="OpenAI base URL (for proxies)")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model")
    llm_provider: str = Field(default="anthropic", description="LLM provider: 'anthropic' or 'openai'")
```

- [ ] **Step 4: Create nl2sql.py**

```python
"""
Natural Language to SQL pipeline for the Financial MCP Server.

Takes a plain English question about university finances,
generates a SQL query using an LLM, validates and executes it.
"""

import json
import logging
from pathlib import Path

from config import Settings
from database import validate_sql, execute_query, SQLValidationError, DatabaseError

logger = logging.getLogger(__name__)

# DDL-based context — LLMs generate better SQL from CREATE TABLE than prose descriptions
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
    account_category TEXT NOT NULL,        -- 'revenue', 'expense', 'asset', 'liability', 'equity'
    account_subcategory TEXT NOT NULL,
    normal_balance TEXT NOT NULL           -- 'debit' or 'credit'
);

CREATE TABLE funds (
    fund_code TEXT PRIMARY KEY,
    fund_name TEXT NOT NULL,
    fund_type TEXT NOT NULL,               -- 'unrestricted', 'restricted', 'endowment', 'auxiliary', 'agency'
    description TEXT
);

CREATE TABLE grants (
    grant_id TEXT PRIMARY KEY,
    grant_name TEXT NOT NULL,
    grant_pi TEXT NOT NULL,
    sponsor TEXT NOT NULL,                 -- 'National Science Foundation', 'NIH', etc.
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
    # Try to find SQL in code block
    if "```sql" in text:
        start = text.index("```sql") + 6
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    # If no code block, try to find SELECT statement
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
        messages=[
            {
                "role": "user",
                "content": f"Database schema:\n{SCHEMA_CONTEXT}\n\nQuestion: {question}",
            }
        ],
    )
    return extract_sql_from_response(response.content[0].text)


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
            {
                "role": "user",
                "content": f"Database schema:\n{SCHEMA_CONTEXT}\n\nQuestion: {question}",
            },
        ],
    )
    return extract_sql_from_response(response.choices[0].message.content)


async def nl_to_sql(question: str, config: Settings) -> str:
    """Convert a natural language question to SQL.

    Uses the configured LLM provider (anthropic or openai).

    Returns:
        The generated SQL query string.
    """
    logger.info(f"NL2SQL question: {question}")

    if config.llm_provider == "openai" and config.openai_api_key:
        sql = await generate_sql_openai(question, config)
    elif config.anthropic_api_key:
        sql = await generate_sql_anthropic(question, config)
    else:
        raise ValueError(
            "No LLM API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env"
        )

    logger.info(f"Generated SQL: {sql}")
    return sql
```

- [ ] **Step 5: Update financial_server.py — add ask tool and prompts**

Add these after the existing tools in `financial_server.py`:

```python
from nl2sql import nl_to_sql

# Add to imports at top:
from fastmcp.prompts import Message


@mcp.tool
async def ask(question: str, ctx: Context) -> str:
    """Ask a natural language question about university financial data.

    Converts your question to SQL, executes it, and returns results.
    Examples:
    - "What did Computer Science spend on travel last year?"
    - "Which grants have less than 10% budget remaining?"
    - "Show me total expenses by department for FY2025"
    """
    await ctx.info(f"Understanding question: {question}")

    try:
        sql = await nl_to_sql(question, config)
    except ValueError as e:
        return f"Configuration error: {e}"
    except Exception as e:
        logger.error(f"NL2SQL error: {e}")
        return f"Failed to generate SQL: {e}"

    await ctx.info(f"Generated SQL: {sql}")

    try:
        rows, total = await execute_query(
            config.database_path_resolved, sql, max_rows=config.max_rows
        )
    except SQLValidationError as e:
        return f"Generated SQL failed validation: {e}\nSQL: {sql}"
    except DatabaseError as e:
        return f"Query execution error: {e}\nSQL: {sql}"

    if total > config.warning_rows:
        await ctx.warning(f"Query returned {total:,} rows (showing {min(total, config.max_rows):,})")

    return json.dumps({
        "question": question,
        "sql": sql,
        "total_rows": total,
        "returned_rows": len(rows),
        "data": rows,
    })


# === Prompts ===


@mcp.prompt
def budget_analysis(department: str, fiscal_year: int = 2025) -> list[Message]:
    """Generate a budget vs actual analysis request for a department."""
    return [
        Message(
            f"Analyze the budget vs actual spending for the {department} department "
            f"in fiscal year {fiscal_year}. Compare budgeted amounts to actual spending "
            f"by account category. Highlight any categories that are over or under budget "
            f"by more than 10%."
        ),
    ]


@mcp.prompt
def grant_status(status: str = "active") -> list[Message]:
    """Generate a grant status report request."""
    return [
        Message(
            f"Generate a report of all {status} grants. For each grant, show: "
            f"grant name, PI, sponsor, department, total budget, remaining budget, "
            f"and percentage spent. Flag any grants with less than 10% budget remaining."
        ),
    ]


@mcp.prompt
def department_spending(fiscal_year: int = 2025) -> list[Message]:
    """Generate a department spending comparison request."""
    return [
        Message(
            f"Compare total actual spending across all departments for fiscal year "
            f"{fiscal_year}. Break down by expense subcategory (salaries, supplies, "
            f"travel, equipment, services). Show the top 10 departments by total spending."
        ),
    ]
```

- [ ] **Step 6: Update .env.example**

Add LLM fields:

```
# Financial MCP Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DATABASE_PATH=data/university_gl.db
MAX_ROWS=2000
WARNING_ROWS=100
LOG_LEVEL=INFO

# LLM Configuration (for NL-to-SQL)
# Set one of these:
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-5
# Or:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=
# OPENAI_BASE_URL=
# OPENAI_MODEL=gpt-4o
```

- [ ] **Step 7: Update README.md**

Append to `README.md`:

```markdown
## Step 06: Natural Language to SQL

This step adds the ability to ask questions in plain English. An LLM generates the SQL.

### How it works

1. User calls `ask("What did Chemistry spend on supplies?")`
2. Server sends the question + full DDL schema to an LLM
3. LLM generates a SQL query
4. Server validates the SQL (safety checks)
5. Server executes the query and returns results

### The NL2SQL pipeline

The key design decisions:

- **DDL-based context**: We send `CREATE TABLE` statements to the LLM, not prose. LLMs are trained on DDL and produce better SQL from it.
- **Inline comments**: Each column has a comment explaining what it means in the domain.
- **Important notes section**: Domain-specific rules (fiscal year boundaries, entry types) are called out explicitly.
- **SQL extraction**: The LLM response is parsed to extract just the SQL from markdown code blocks.

### Prompts

Three reusable prompts give the LLM structured starting points:

- `budget_analysis(department, fiscal_year)` — budget vs actual comparison
- `grant_status(status)` — grant portfolio overview
- `department_spending(fiscal_year)` — cross-department comparison

### Configuration

Set `LLM_PROVIDER=anthropic` or `LLM_PROVIDER=openai` in `.env` with the appropriate API key.
```

- [ ] **Step 8: Commit**

```bash
git add nl2sql.py financial_server.py config.py requirements.txt .env.example README.md
git commit -m "feat: step-06 natural language to SQL

NL2SQL pipeline with LLM-generated queries, DDL-based context,
and domain-aware prompts for budget, grant, and spending analysis."
```

---

## Task 7: step-07 — Lifespans, Tasks, and Composition

**Branch:** `step-07` (from `step-06`)

**Files:**
- Modify: `financial_server.py`
- Modify: `database.py`
- Create: `composed_server.py`
- Modify: `requirements.txt`
- Modify: `README.md`

- [ ] **Step 1: Create branch**

```bash
git checkout step-06
git checkout -b step-07
```

- [ ] **Step 2: Update requirements.txt**

Add tasks extra:

```
fastmcp[tasks]>=2.14.0
uvicorn>=0.34.0
faker>=33.0.0
aiosqlite>=0.20.0
pydantic-settings>=2.10.0
python-dotenv>=1.0.0
anthropic>=0.40.0
openai>=1.0.0
```

- [ ] **Step 3: Add lifespan to database.py**

Add a connection manager to `database.py`:

```python
# Add at the end of database.py:

class DatabasePool:
    """Simple async connection manager for SQLite.

    Used with FastMCP lifespans to open the database once at startup
    and close it on shutdown, rather than opening per-request.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        if not self.db_path.exists():
            raise DatabaseError(f"Database not found: {self.db_path}")
        self._conn = await aiosqlite.connect(str(self.db_path))
        self._conn.row_factory = aiosqlite.Row
        logger.info(f"Database connected: {self.db_path}")

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("Database connection closed")

    async def execute_query(self, sql: str, max_rows: int = 2000) -> tuple[list[dict], int]:
        """Execute a query using the persistent connection."""
        validate_sql(sql)
        if not self._conn:
            raise DatabaseError("Database not connected")
        cursor = await self._conn.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        all_rows = await cursor.fetchall()
        total = len(all_rows)
        rows = [dict(zip(columns, row)) for row in all_rows[:max_rows]]
        return rows, total

    async def get_table_info(self) -> list[dict]:
        """Get table info using the persistent connection."""
        if not self._conn:
            raise DatabaseError("Database not connected")
        cursor = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = []
        for row in await cursor.fetchall():
            name = row[0]
            if name in ALLOWED_TABLES:
                count = (await (await self._conn.execute(f"SELECT COUNT(*) FROM [{name}]")).fetchone())[0]
                cols = await (await self._conn.execute(f"PRAGMA table_info([{name}])")).fetchall()
                tables.append({
                    "table_name": name,
                    "row_count": count,
                    "columns": [{"name": c[1], "type": c[2], "nullable": not c[3]} for c in cols],
                })
        return tables
```

- [ ] **Step 4: Update financial_server.py with lifespan and background task**

Update `financial_server.py` to use the lifespan and add a background task tool:

```python
"""
Step 07: Lifespans, Tasks, and Composition

Adds:
- Lifespan for database connection management
- Background task for long-running report generation
- Server composition with mount()
"""

import csv
import io
import json
import logging

from fastmcp import FastMCP, Context
from fastmcp.server.lifespan import lifespan
from fastmcp.prompts import Message

from config import load_config
from database import DatabasePool, SQLValidationError, DatabaseError
from nl2sql import nl_to_sql

config = load_config()
logging.basicConfig(level=config.get_log_level(), format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


# === Lifespan ===


@lifespan
async def db_lifespan(server):
    """Open database on startup, close on shutdown.

    The yielded dict becomes the 'lifespan context' —
    tools access it via ctx.lifespan_context['db'].
    """
    db = DatabasePool(config.database_path_resolved)
    await db.connect()
    try:
        yield {"db": db}
    finally:
        await db.close()


mcp = FastMCP(
    "FinancialData",
    instructions=(
        "University General Ledger query server. Use the schema:// resources to "
        "discover tables and columns. Use domain:// resources to understand fund "
        "accounting concepts. Use query_sql or ask to query the data."
    ),
    lifespan=db_lifespan,
)


def get_db(ctx: Context) -> DatabasePool:
    """Helper to get the database from lifespan context."""
    return ctx.lifespan_context["db"]


# === Tools ===


@mcp.tool
async def query_sql(sql: str, ctx: Context) -> str:
    """Execute a SQL SELECT query against the university general ledger database.

    Only SELECT queries are allowed. Results limited to 2000 rows.
    """
    db = get_db(ctx)
    try:
        rows, total = await db.execute_query(sql, max_rows=config.max_rows)
    except SQLValidationError as e:
        return f"Query validation error: {e}"
    except DatabaseError as e:
        return f"Database error: {e}"

    if total > config.warning_rows:
        await ctx.warning(f"Query returned {total:,} rows (showing {min(total, config.max_rows):,})")

    return json.dumps({"total_rows": total, "returned_rows": len(rows), "data": rows})


@mcp.tool
async def ask(question: str, ctx: Context) -> str:
    """Ask a natural language question about university financial data."""
    await ctx.info(f"Understanding: {question}")
    db = get_db(ctx)

    try:
        sql = await nl_to_sql(question, config)
    except Exception as e:
        return f"Failed to generate SQL: {e}"

    await ctx.info(f"Generated SQL: {sql}")

    try:
        rows, total = await db.execute_query(sql, max_rows=config.max_rows)
    except (SQLValidationError, DatabaseError) as e:
        return f"Query error: {e}\nSQL: {sql}"

    return json.dumps({"question": question, "sql": sql, "total_rows": total, "data": rows})


@mcp.tool
async def get_database_info(ctx: Context) -> str:
    """Get a summary of all tables, columns, and row counts."""
    db = get_db(ctx)
    tables = await db.get_table_info()
    return json.dumps(tables, indent=2)


@mcp.tool(task=True)
async def export_report(
    query_description: str,
    sql: str,
    ctx: Context,
) -> str:
    """Export a query result as a CSV report (runs as a background task).

    Use this for large exports that might take a while. The task runs
    in the background and you can check its progress.

    Args:
        query_description: What this report is (e.g., "FY2025 travel expenses")
        sql: The SQL query to execute
    """
    db = get_db(ctx)
    await ctx.info(f"Starting report export: {query_description}")

    try:
        rows, total = await db.execute_query(sql, max_rows=50_000)
    except (SQLValidationError, DatabaseError) as e:
        return f"Export failed: {e}"

    await ctx.info(f"Retrieved {total:,} rows, generating CSV...")

    # Generate CSV
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    csv_content = output.getvalue()
    await ctx.info(f"Report complete: {len(rows):,} rows, {len(csv_content):,} bytes")

    return json.dumps({
        "description": query_description,
        "sql": sql,
        "total_rows": total,
        "exported_rows": len(rows),
        "csv": csv_content,
    })


# === Resources (same as step-05/06, kept for brevity — domain resources unchanged) ===
# [Include all the schema:// and domain:// resources from step-05]

@mcp.resource("schema://tables", mime_type="application/json")
async def list_tables(ctx: Context) -> str:
    db = get_db(ctx)
    tables = await db.get_table_info()
    summary = [{"table": t["table_name"], "rows": t["row_count"]} for t in tables]
    return json.dumps(summary, indent=2)


@mcp.resource("domain://funds", mime_type="text/markdown")
def fund_types() -> str:
    """Explains university fund accounting types."""
    return """# Fund Types in University Accounting

| Fund Code | Name | Type | Description |
|-----------|------|------|-------------|
| 10 | General Operating | Unrestricted | Primary university operations |
| 20 | Restricted Grants | Restricted | Sponsored research (NSF, NIH, DOD) |
| 25 | Restricted Gifts | Restricted | Donor-restricted gifts |
| 30 | Endowment | Endowment | Permanent funds — only returns spent |
| 40 | Auxiliary Enterprises | Auxiliary | Self-supporting: housing, dining, parking |
| 50 | Agency Funds | Agency | Held on behalf of student organizations |
| 60 | Plant Funds | Unrestricted | Capital projects and equipment |
| 70 | Loan Funds | Restricted | Student loan programs |
"""


@mcp.resource("domain://accounts", mime_type="text/markdown")
def chart_of_accounts() -> str:
    """Chart of accounts reference."""
    return """# Chart of Accounts
| Range | Category | Examples |
|-------|----------|----------|
| 1xxx | Assets | Cash, Receivables, Investments |
| 2xxx | Liabilities | Accounts Payable, Deferred Revenue |
| 3xxx | Net Assets | Unrestricted, Restricted |
| 4xxx | Revenue | Tuition, Grants, Gifts |
| 5xxx | Salaries & Benefits | Faculty, Staff, Benefits |
| 6xxx | Operating Expenses | Supplies, Travel, Equipment |
| 7xxx | Transfers & Debt | Internal Transfers, Debt Service |
"""


@mcp.resource("domain://departments", mime_type="text/markdown")
def department_list() -> str:
    """Department listing by school."""
    return """# Departments
Arts & Sciences: COMPSCI, MATH, PHYS, CHEM, BIO, ENGLISH, HISTORY, POLISCI, ECON, PSYCH, SOCIOL, PHILO, ROMANCE, STATS, NEURO
Engineering: ECE, MECHENG, CIVENG, BME, MATSCI
Medicine: MEDSCHOOL, PATHOL, PEDS, SURG, NEUROMD, CARDIO, ONCOL, RADIOL
Law: LAW, LAWCLIN
Business: BUSINESS, FINANCE, MKTG
Other: PUBPOL, ENVIRON, NURSING, DIVINITY, GRADSCH
Admin: PROVOST, FINAID, REGIST, ITDEPT, FACMGMT, HR, LIBR, ATHLET, ALUMNI, RESADM
"""


# === Prompts (from step-06) ===


@mcp.prompt
def budget_analysis(department: str, fiscal_year: int = 2025) -> list[Message]:
    """Budget vs actual analysis for a department."""
    return [Message(f"Analyze budget vs actual for {department} in FY{fiscal_year}.")]


@mcp.prompt
def grant_status(status: str = "active") -> list[Message]:
    """Grant status report."""
    return [Message(f"Report on all {status} grants with budget remaining.")]


@mcp.prompt
def department_spending(fiscal_year: int = 2025) -> list[Message]:
    """Department spending comparison."""
    return [Message(f"Compare department spending for FY{fiscal_year} by category.")]


if __name__ == "__main__":
    mcp.run(transport="http", host=config.server_host, port=config.server_port)
```

- [ ] **Step 5: Create composed_server.py**

```python
"""
Server Composition Demo

Demonstrates mounting multiple FastMCP servers into a single endpoint.
The financial server is mounted with a namespace prefix.
"""

from fastmcp import FastMCP

# Import the financial server's mcp instance
from financial_server import mcp as financial_mcp

# Create a parent server
main = FastMCP(
    "UniversityServices",
    instructions=(
        "Unified university services server. Use finance_* tools for "
        "financial data queries, and other namespaced tools as available."
    ),
)

# Mount the financial server under a namespace
# All tools become prefixed: query_sql -> finance_query_sql
main.mount(financial_mcp, namespace="finance")

if __name__ == "__main__":
    main.run(transport="http", host="0.0.0.0", port=8000)
```

- [ ] **Step 6: Update README.md**

Append to `README.md`:

```markdown
## Step 07: Lifespans, Tasks, and Composition

Three advanced FastMCP features that make servers production-ready.

### Lifespans

Lifespans run setup/teardown code once when the server starts and stops:

```python
@lifespan
async def db_lifespan(server):
    db = DatabasePool(path)
    await db.connect()
    try:
        yield {"db": db}       # dict becomes lifespan_context
    finally:
        await db.close()       # cleanup on shutdown

mcp = FastMCP("Server", lifespan=db_lifespan)
```

Tools access the lifespan context via `ctx.lifespan_context["db"]`.

### Background Tasks

Long-running operations can run as background tasks:

```python
@mcp.tool(task=True)
async def export_report(sql: str, ctx: Context) -> str:
    # Runs asynchronously — client gets a task ID to check progress
    ...
```

Install with `pip install "fastmcp[tasks]"`. The client gets a task ID and polls for results.

### Server Composition

Mount multiple servers into one:

```python
main = FastMCP("Parent")
main.mount(financial_mcp, namespace="finance")
# finance_query_sql, finance_ask, etc.
```

Run: `python composed_server.py`
```

- [ ] **Step 7: Commit**

```bash
git add financial_server.py database.py composed_server.py requirements.txt README.md
git commit -m "feat: step-07 lifespans, tasks, and composition

Database lifespan for connection management, background task
export_report tool, and composed_server.py demonstrating mount()."
```

---

## Task 8: step-08 — Azure OAuth (Confidential Client)

**Branch:** `step-08` (from `step-07`)

**Files:**
- Modify: `financial_server.py`
- Modify: `config.py`
- Modify: `.env.example`
- Create: `docs/azure-setup-step08.md`
- Modify: `requirements.txt`
- Modify: `README.md`

- [ ] **Step 1: Create branch**

```bash
git checkout step-07
git checkout -b step-08
```

- [ ] **Step 2: Update requirements.txt**

```
fastmcp[tasks]>=2.14.0
uvicorn>=0.34.0
faker>=33.0.0
aiosqlite>=0.20.0
pydantic-settings>=2.10.0
python-dotenv>=1.0.0
anthropic>=0.40.0
openai>=1.0.0
cryptography>=42.0.0
```

- [ ] **Step 3: Update config.py with Azure fields**

Add Azure OAuth fields to the Settings class:

```python
    # Azure OAuth Settings
    azure_client_id: str = Field(default="", description="Azure AD Application (Client) ID")
    azure_client_secret: str = Field(default="", description="Azure AD Client Secret")
    azure_tenant_id: str = Field(default="", description="Azure AD Tenant ID")
    mcp_api_scope: str = Field(default="access_as_user", description="Custom API scope name")
    oauth_base_url: str = Field(default="http://localhost:8000", description="OAuth callback base URL")
    additional_auth_scopes: str = Field(
        default="email,openid,profile,offline_access",
        description="Comma-separated additional OAuth scopes",
    )

    @property
    def full_mcp_scope(self) -> str:
        return f"api://{self.azure_client_id}/{self.mcp_api_scope}"

    @property
    def additional_auth_scopes_list(self) -> list[str]:
        return [s.strip() for s in self.additional_auth_scopes.split(",") if s.strip()]

    @property
    def auth_enabled(self) -> bool:
        return bool(self.azure_client_id and self.azure_tenant_id)
```

- [ ] **Step 4: Update financial_server.py with OAuth**

Add auth setup to `financial_server.py`. Replace the mcp initialization section:

```python
from fastmcp.server.auth import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token

# === Auth Setup ===

auth = None
if config.auth_enabled:
    tenant = config.azure_tenant_id
    token_verifier = JWTVerifier(
        jwks_uri=f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys",
        issuer=f"https://login.microsoftonline.com/{tenant}/v2.0",
        audience=config.azure_client_id,
    )
    auth = OAuthProxy(
        upstream_authorization_endpoint=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
        upstream_token_endpoint=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        upstream_client_id=config.azure_client_id,
        upstream_client_secret=config.azure_client_secret,
        upstream_scopes=[config.full_mcp_scope] + config.additional_auth_scopes_list,
        token_verifier=token_verifier,
        base_url=config.oauth_base_url,
    )
    logger.info("Azure OAuth enabled")


mcp = FastMCP(
    "FinancialData",
    instructions="University General Ledger query server.",
    lifespan=db_lifespan,
    auth=auth,
)


# Add authenticated user tool:

@mcp.tool
async def get_authenticated_user() -> str:
    """Get information about the currently authenticated user.

    Returns the user's claims from their Azure AD token.
    """
    token = get_access_token()
    if token is None:
        return json.dumps({"error": "Not authenticated"})

    claims = token.claims or {}
    return json.dumps({
        "email": claims.get("preferred_username", "unknown"),
        "name": claims.get("name", "unknown"),
        "tenant_id": claims.get("tid", "unknown"),
        "token_issuer": claims.get("iss", "unknown"),
    })
```

- [ ] **Step 5: Update .env.example**

```
# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DATABASE_PATH=data/university_gl.db
MAX_ROWS=2000
LOG_LEVEL=INFO

# LLM Configuration
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-5

# Azure OAuth (leave blank to disable auth)
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_TENANT_ID=
MCP_API_SCOPE=access_as_user
OAUTH_BASE_URL=http://localhost:8000
ADDITIONAL_AUTH_SCOPES=email,openid,profile,offline_access
```

- [ ] **Step 6: Create docs/azure-setup-step08.md**

```markdown
# Azure App Registration: Confidential Client (Step 08)

This guide walks through creating an Azure AD app registration for the financial MCP server.

## Prerequisites

- An Azure AD tenant (organization account)
- Permission to register applications (or an admin who can do it)

## Step 1: Register the Application

1. Go to [Azure Portal](https://portal.azure.com) > **Azure Active Directory** > **App registrations**
2. Click **New registration**
3. Configure:
   - **Name**: `MCP Financial Server` (or any descriptive name)
   - **Supported account types**: "Accounts in this organizational directory only" (Single tenant)
   - **Redirect URI**: Select **Web**, enter `http://localhost:8000/mcp/oauth/callback`
4. Click **Register**
5. Copy the **Application (client) ID** — this is your `AZURE_CLIENT_ID`
6. Copy the **Directory (tenant) ID** — this is your `AZURE_TENANT_ID`

## Step 2: Create a Client Secret

1. In your app registration, go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description (e.g., "MCP Server Dev") and expiration
4. Click **Add**
5. **Copy the Value immediately** — it won't be shown again. This is your `AZURE_CLIENT_SECRET`

## Step 3: Expose an API (Custom Scope)

This creates the custom scope that MCP clients will request during authentication.

1. Go to **Expose an API**
2. Click **Set** next to "Application ID URI" — accept the default `api://<client-id>`
3. Click **Add a scope**:
   - **Scope name**: `access_as_user`
   - **Who can consent**: Admins and users
   - **Admin consent display name**: "Access Financial Data as User"
   - **Admin consent description**: "Allows the MCP client to access university financial data on behalf of the signed-in user"
   - **User consent display name**: "Access Financial Data"
   - **User consent description**: "Access university financial data on your behalf"
   - **State**: Enabled
4. Click **Add scope**

The full scope URI will be: `api://<client-id>/access_as_user`

## Step 4: Configure API Permissions

1. Go to **API permissions**
2. The default `Microsoft Graph > User.Read` permission is sufficient for this step
3. No admin consent is needed for basic permissions

## Step 5: Configure .env

```env
AZURE_CLIENT_ID=<Application (client) ID from Step 1>
AZURE_CLIENT_SECRET=<Client secret Value from Step 2>
AZURE_TENANT_ID=<Directory (tenant) ID from Step 1>
MCP_API_SCOPE=access_as_user
OAUTH_BASE_URL=http://localhost:8000
```

## What is a Confidential Client?

A **confidential client** has a client secret that is kept secure on the server. This is appropriate when:

- The server runs in a trusted environment (your server, not a user's browser)
- You can keep the client secret secure
- The server itself authenticates to Azure AD

The OAuth flow:
1. User is redirected to Azure AD login
2. User authenticates and consents to the `access_as_user` scope
3. Azure AD sends an authorization code to the redirect URI
4. **The server** exchanges the code for tokens using the client secret
5. The server issues its own JWT to the MCP client

The client secret proves the server's identity to Azure AD. This is more secure than a public client flow, but requires secret management.

## Redirect URI for Production

When deploying, update:
- **Redirect URI** in Azure Portal to your production URL: `https://your-domain.com/mcp/oauth/callback`
- `OAUTH_BASE_URL` in `.env` to match
```

- [ ] **Step 7: Update README.md**

Append to `README.md`:

```markdown
## Step 08: Azure OAuth — Confidential Client

Adds Azure AD authentication to the financial server.

### What changes

- Server now requires Azure AD authentication (when configured)
- New `get_authenticated_user` tool returns user claims from the token
- `OAuthProxy` bridges Azure AD's OAuth flow with MCP's client protocol

### Setup

See `docs/azure-setup-step08.md` for the full Azure Portal walkthrough.

### Key concepts

- **Confidential client** — server has a client secret, proving its identity
- **OAuthProxy** — bridges traditional OAuth providers (Azure, Google) with MCP's Dynamic Client Registration
- **Custom scope** — `api://<client-id>/access_as_user` scopes the token to your API
- **JWTVerifier** — validates tokens using Azure AD's published signing keys (JWKS)
- **get_access_token()** — access the authenticated user's token in any tool
```

- [ ] **Step 8: Commit**

```bash
git add financial_server.py config.py .env.example requirements.txt README.md docs/
git commit -m "feat: step-08 Azure OAuth confidential client

OAuthProxy with Azure AD, JWTVerifier, get_authenticated_user tool,
and Azure portal setup documentation."
```

---

## Task 9: step-09 — Azure Public Client + Security

**Branch:** `step-09` (from `step-08`)

**Files:**
- Modify: `financial_server.py`
- Modify: `config.py`
- Create: `audit.py`
- Create: `docs/azure-setup-step09.md`
- Modify: `README.md`

- [ ] **Step 1: Create branch**

```bash
git checkout step-08
git checkout -b step-09
```

- [ ] **Step 2: Create audit.py**

```python
"""
Audit logging with tamper-detected hash chain.

Every query is logged with a SHA-256 hash chain — each entry
includes the hash of the previous entry, making it detectable
if any log entry is modified or deleted.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class AuditLogger:
    """Append-only audit log with hash chain integrity."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._previous_hash = "GENESIS"

    def _current_log_path(self) -> Path:
        """Monthly log rotation."""
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        return self.log_dir / f"audit-{month}.jsonl"

    def _compute_hash(self, entry: dict) -> str:
        """SHA-256 hash of the entry content."""
        content = json.dumps(entry, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    def log(
        self,
        user_email: str,
        action: str,
        detail: str = "",
        result_count: int = 0,
    ) -> None:
        """Write an audit log entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": user_email,
            "action": action,
            "detail": detail[:500],  # Truncate long details
            "result_count": result_count,
            "previous_hash": self._previous_hash,
        }
        entry["hash"] = self._compute_hash(entry)
        self._previous_hash = entry["hash"]

        log_path = self._current_log_path()
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def verify_chain(self, log_path: Path | None = None) -> tuple[bool, int]:
        """Verify the hash chain integrity of a log file.

        Returns:
            Tuple of (is_valid, entry_count).
        """
        path = log_path or self._current_log_path()
        if not path.exists():
            return True, 0

        previous_hash = "GENESIS"
        count = 0

        with open(path) as f:
            for line in f:
                entry = json.loads(line.strip())
                if entry.get("previous_hash") != previous_hash:
                    logger.error(f"Hash chain broken at entry {count}")
                    return False, count

                stored_hash = entry.pop("hash")
                computed = self._compute_hash(entry)
                if computed != stored_hash:
                    logger.error(f"Entry {count} has been tampered with")
                    return False, count

                previous_hash = stored_hash
                count += 1

        return True, count
```

- [ ] **Step 3: Update config.py with public client and security fields**

Add to Settings:

```python
    # Access Control
    allowed_users: str = Field(
        default="",
        description="Comma-separated list of allowed user emails (empty = allow all authenticated)",
    )

    # Audit
    audit_log_dir: str = Field(default="logs", description="Directory for audit logs")

    @property
    def allowed_users_list(self) -> list[str]:
        if not self.allowed_users.strip():
            return []
        return [e.strip().lower() for e in self.allowed_users.split(",") if e.strip()]
```

- [ ] **Step 4: Update financial_server.py with allowlist and audit logging**

Add to `financial_server.py` after auth setup, modify `query_sql` and `ask` tools:

```python
from audit import AuditLogger

audit = AuditLogger(config.audit_log_dir)


def check_user_allowed(email: str) -> bool:
    """Check if user is in the allowlist (if configured)."""
    allowed = config.allowed_users_list
    if not allowed:
        return True  # No allowlist = allow all authenticated users
    return email.lower() in allowed


# Modify query_sql to include audit logging:
@mcp.tool
async def query_sql(sql: str, ctx: Context) -> str:
    """Execute a SQL SELECT query against the university general ledger database."""
    user_email = "anonymous"
    if config.auth_enabled:
        token = get_access_token()
        if token and token.claims:
            user_email = token.claims.get("preferred_username", "unknown")
            if not check_user_allowed(user_email):
                audit.log(user_email, "DENIED", f"query_sql: {sql[:200]}")
                return json.dumps({"error": "Access denied. Your account is not authorized."})

    db = get_db(ctx)
    try:
        rows, total = await db.execute_query(sql, max_rows=config.max_rows)
    except (SQLValidationError, DatabaseError) as e:
        audit.log(user_email, "QUERY_ERROR", str(e))
        return f"Error: {e}"

    audit.log(user_email, "QUERY", sql[:200], result_count=total)

    if total > config.warning_rows:
        await ctx.warning(f"Query returned {total:,} rows")

    return json.dumps({"total_rows": total, "returned_rows": len(rows), "data": rows})
```

- [ ] **Step 5: Create docs/azure-setup-step09.md**

```markdown
# Azure App Registration: Public Client (Step 09)

This guide covers converting from a confidential client to a public client configuration.

## What Changes from Step 08

| Setting | Confidential (Step 08) | Public (Step 09) |
|---------|------------------------|-------------------|
| Client Secret | Required | Not used |
| PKCE | Optional | Required (automatic) |
| Platform | Web | Mobile/Desktop |
| Security Model | Secret proves server identity | PKCE proves request origin |

## Why Public Clients?

Public clients are appropriate when:
- You cannot securely store a client secret (desktop apps, CLI tools, SPAs)
- You want to eliminate secret rotation overhead
- PKCE provides sufficient security for your use case

Public clients + PKCE are considered **more secure** than confidential clients for many deployment scenarios because there is no secret that can be leaked.

## Step 1: Enable Public Client Flows

1. In your app registration, go to **Authentication**
2. Under **Advanced settings**, set **Allow public client flows** to **Yes**
3. Click **Save**

## Step 2: Update Platform Configuration

1. Still in **Authentication**
2. Click **Add a platform** > **Mobile and desktop applications**
3. Add redirect URI: `http://localhost:8000/mcp/oauth/callback`
4. (Optional) Remove the **Web** platform if you only want public client flows

## Step 3: Remove Client Secret (Optional)

If you're switching entirely to public client:
1. Go to **Certificates & secrets**
2. Delete the client secret created in Step 08
3. Remove `AZURE_CLIENT_SECRET` from your `.env`

## Step 4: Update .env

```env
AZURE_CLIENT_ID=<same as before>
# AZURE_CLIENT_SECRET=  # Not needed for public client
AZURE_TENANT_ID=<same as before>
```

## Step 5: Add User Allowlist

With public client flow, anyone with a valid Azure AD account can authenticate. Add an allowlist to restrict access:

```env
ALLOWED_USERS=alice@university.edu,bob@university.edu
```

## PKCE (Proof Key for Code Exchange)

PKCE is automatically handled by FastMCP's OAuthProxy. Here's how it works:

1. Client generates a random `code_verifier` (43-128 chars)
2. Client computes `code_challenge = BASE64URL(SHA256(code_verifier))`
3. Authorization request includes `code_challenge`
4. Token exchange includes `code_verifier`
5. Azure AD verifies that `SHA256(code_verifier) == code_challenge`

This prevents authorization code interception attacks because the attacker would need the `code_verifier` to exchange the code.

## When to Use Confidential vs Public

| Scenario | Recommendation |
|----------|---------------|
| Server-side app with secure storage | Confidential |
| Desktop/CLI application | Public + PKCE |
| Single-page app (browser) | Public + PKCE |
| Multi-tenant SaaS | Confidential |
| Development/testing | Either (public is simpler) |
```

- [ ] **Step 6: Update README.md**

Append:

```markdown
## Step 09: Azure Public Client + Security

### Public vs Confidential

- **Confidential** (step-08): Server has a client secret. More traditional.
- **Public** (step-09): No client secret. Uses PKCE instead. Simpler, and more secure for many scenarios.

### Security additions

- **User allowlist**: Only specified email addresses can use the server
- **Audit logging**: Every query is logged with a SHA-256 hash chain for tamper detection
- **PKCE**: Automatic with FastMCP — prevents authorization code interception

See `docs/azure-setup-step09.md` for Azure Portal changes.
```

- [ ] **Step 7: Commit**

```bash
git add financial_server.py config.py audit.py docs/azure-setup-step09.md .env.example README.md
git commit -m "feat: step-09 public client auth and security hardening

Public client with PKCE, user allowlist, and tamper-detected
audit logging with SHA-256 hash chain."
```

---

## Task 10: step-10 — OBO Flow: Directory Server

**Branch:** `step-10` (from `step-09`)

**Files:**
- Create: `directory_server.py`
- Create: `token_exchange.py`
- Create: `ms_graph_client.py`
- Create: `directory_service.py`
- Create: `models.py`
- Create: `docs/azure-setup-step10.md`
- Modify: `composed_server.py`
- Modify: `config.py`
- Modify: `requirements.txt`
- Modify: `README.md`

- [ ] **Step 1: Create branch**

```bash
git checkout step-09
git checkout -b step-10
```

- [ ] **Step 2: Update requirements.txt**

Add httpx:

```
fastmcp[tasks]>=2.14.0
uvicorn>=0.34.0
faker>=33.0.0
aiosqlite>=0.20.0
pydantic-settings>=2.10.0
python-dotenv>=1.0.0
anthropic>=0.40.0
openai>=1.0.0
cryptography>=42.0.0
httpx>=0.27.0
```

- [ ] **Step 3: Add directory config to config.py**

Add a separate DirectorySettings class:

```python
class DirectorySettings(BaseSettings):
    """Configuration for the directory server (OBO flow)."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore",
        env_prefix="DIR_",
    )

    azure_client_id: str = Field(..., description="Directory app client ID")
    azure_client_secret: str = Field(..., description="Directory app client secret")
    azure_tenant_id: str = Field(..., description="Azure tenant ID")
    mcp_api_scope: str = Field(default="access_as_user")
    graph_scopes: str = Field(
        default="https://graph.microsoft.com/User.Read.All https://graph.microsoft.com/Directory.Read.All",
    )
    server_host: str = Field(default="0.0.0.0")
    server_port: int = Field(default=8001)
    oauth_base_url: str = Field(default="http://localhost:8001")
    obo_token_cache_ttl: int = Field(default=3000)
    cache_ttl_seconds: int = Field(default=300)
    graph_base_url: str = Field(default="https://graph.microsoft.com/beta")
    additional_auth_scopes: str = Field(default="email,openid,profile,offline_access")

    @property
    def full_mcp_scope(self) -> str:
        return f"api://{self.azure_client_id}/{self.mcp_api_scope}"

    @property
    def graph_scopes_list(self) -> list[str]:
        return [s.strip() for s in self.graph_scopes.split() if s.strip()]

    @property
    def token_endpoint(self) -> str:
        return f"https://login.microsoftonline.com/{self.azure_tenant_id}/oauth2/v2.0/token"

    @property
    def additional_auth_scopes_list(self) -> list[str]:
        return [s.strip() for s in self.additional_auth_scopes.split(",") if s.strip()]
```

- [ ] **Step 4: Create token_exchange.py**

Use the pattern from the reference DukeDirectoryMCPOauth project:

```python
"""
Azure AD On-Behalf-Of (OBO) Token Exchange

Exchanges a user's MCP access token for a Microsoft Graph API token,
allowing the server to call Graph on behalf of the authenticated user.
"""

import hashlib
import logging
import time
from collections import OrderedDict
from threading import Lock

import httpx

logger = logging.getLogger(__name__)


class OBOTokenCache:
    """Thread-safe cache for OBO tokens with TTL and LRU eviction."""

    def __init__(self, ttl_seconds: int = 3000, max_size: int = 500):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: OrderedDict[str, tuple[str, float, float]] = OrderedDict()
        self._lock = Lock()

    def _hash_key(self, assertion: str) -> str:
        return hashlib.sha256(assertion.encode()).hexdigest()[:32]

    def get(self, assertion: str) -> str | None:
        key = self._hash_key(assertion)
        with self._lock:
            if key in self._cache:
                token, timestamp, expires_at = self._cache[key]
                now = time.time()
                if now - timestamp < self.ttl_seconds and now < expires_at:
                    self._cache.move_to_end(key)
                    return token
                del self._cache[key]
        return None

    def set(self, assertion: str, token: str, expires_in: int = 3600) -> None:
        key = self._hash_key(assertion)
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            self._cache[key] = (token, time.time(), time.time() + expires_in - 60)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class OBOExchangeError(Exception):
    pass


class OBOTokenExchange:
    """Handles Azure AD On-Behalf-Of token exchange."""

    def __init__(self, client_id: str, client_secret: str, token_endpoint: str,
                 graph_scopes: str, cache_ttl: int = 3000):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_endpoint = token_endpoint
        self.graph_scopes = graph_scopes
        self._cache = OBOTokenCache(ttl_seconds=cache_ttl)

    async def exchange(self, user_assertion: str) -> str:
        """Exchange user's MCP token for a Graph API token."""
        cached = self._cache.get(user_assertion)
        if cached:
            return cached

        logger.info("Performing OBO token exchange")

        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "assertion": user_assertion,
            "scope": self.graph_scopes,
            "requested_token_use": "on_behalf_of",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                error = response.json()
                msg = error.get("error_description", error.get("error", "Unknown"))
                logger.error(f"OBO exchange failed: {msg}")
                raise OBOExchangeError(f"Token exchange failed: {msg}")

            result = response.json()
            token = result["access_token"]
            expires_in = result.get("expires_in", 3600)
            self._cache.set(user_assertion, token, expires_in)
            return token
```

- [ ] **Step 5: Create ms_graph_client.py**

```python
"""Microsoft Graph API client for directory lookups."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

USER_PROPERTIES = (
    "id,displayName,givenName,surname,mail,userPrincipalName,"
    "jobTitle,department,officeLocation,businessPhones,mobilePhone"
)


class GraphClient:
    """Async client for Microsoft Graph API."""

    def __init__(self, base_url: str = "https://graph.microsoft.com/beta"):
        self.base_url = base_url.rstrip("/")

    async def get(self, endpoint: str, token: str, params: dict | None = None) -> dict:
        """Make a GET request to Graph API."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)

            if response.status_code == 404:
                return {"value": []}
            if response.status_code != 200:
                logger.error(f"Graph API error {response.status_code}: {response.text[:200]}")
                response.raise_for_status()

            return response.json()

    async def find_user(self, token: str, query: str) -> list[dict]:
        """Search for a user by email, name, or UPN."""
        # Escape single quotes for OData filter
        safe_query = query.replace("'", "''")

        if "@" in query:
            filter_str = (
                f"mail eq '{safe_query}' or "
                f"userPrincipalName eq '{safe_query}'"
            )
        else:
            filter_str = (
                f"startswith(displayName, '{safe_query}') or "
                f"startswith(surname, '{safe_query}') or "
                f"startswith(givenName, '{safe_query}')"
            )

        result = await self.get(
            "/users",
            token,
            params={
                "$filter": filter_str,
                "$select": USER_PROPERTIES,
                "$top": "10",
            },
        )
        return result.get("value", [])

    async def get_user_groups(self, token: str, user_id: str) -> list[dict]:
        """Get a user's group memberships."""
        result = await self.get(
            f"/users/{user_id}/memberOf",
            token,
            params={"$select": "id,displayName,groupTypes,mailEnabled"},
        )
        # Filter to actual groups
        return [
            m for m in result.get("value", [])
            if m.get("@odata.type") == "#microsoft.graph.group"
        ]
```

- [ ] **Step 6: Create directory_service.py**

```python
"""Business logic for directory operations."""

import logging

from ms_graph_client import GraphClient
from token_exchange import OBOTokenExchange, OBOExchangeError

logger = logging.getLogger(__name__)


def sanitize_for_log(value: str) -> str:
    """Mask PII in log output."""
    if "@" in value:
        parts = value.split("@")
        return f"{parts[0][:2]}***@{parts[1]}"
    if len(value) > 4:
        return f"{value[:3]}***"
    return "***"


class DirectoryService:
    """Coordinates token exchange and Graph API calls."""

    def __init__(self, obo: OBOTokenExchange, graph: GraphClient):
        self.obo = obo
        self.graph = graph

    async def find_user(self, user_token: str, query: str) -> list[dict]:
        """Search for users in the directory."""
        logger.info(f"Finding user: {sanitize_for_log(query)}")
        graph_token = await self.obo.exchange(user_token)
        return await self.graph.find_user(graph_token, query)

    async def get_user_groups(self, user_token: str, user_id: str) -> list[dict]:
        """Get a user's group memberships."""
        logger.info(f"Getting groups for: {sanitize_for_log(user_id)}")
        graph_token = await self.obo.exchange(user_token)
        return await self.graph.get_user_groups(graph_token, user_id)
```

- [ ] **Step 7: Create models.py**

```python
"""Pydantic models for directory results."""

from pydantic import BaseModel


class UserResult(BaseModel):
    """Formatted user directory result."""
    id: str = ""
    display_name: str = ""
    email: str = ""
    upn: str = ""
    job_title: str = ""
    department: str = ""
    office: str = ""
    phone: str = ""

    @classmethod
    def from_graph(cls, data: dict) -> "UserResult":
        phones = data.get("businessPhones", [])
        return cls(
            id=data.get("id", ""),
            display_name=data.get("displayName", ""),
            email=data.get("mail", ""),
            upn=data.get("userPrincipalName", ""),
            job_title=data.get("jobTitle", "") or "",
            department=data.get("department", "") or "",
            office=data.get("officeLocation", "") or "",
            phone=phones[0] if phones else data.get("mobilePhone", "") or "",
        )
```

- [ ] **Step 8: Create directory_server.py**

```python
"""
Step 10: Directory MCP Server with OBO Flow

Uses On-Behalf-Of token exchange to call Microsoft Graph API
for user directory lookups. The server exchanges the user's
MCP token for a Graph API token, then makes Graph calls on
their behalf.
"""

import json
import logging

from fastmcp import FastMCP
from fastmcp.server.auth import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token

from config import DirectorySettings
from token_exchange import OBOTokenExchange, OBOExchangeError
from ms_graph_client import GraphClient
from directory_service import DirectoryService
from models import UserResult

config = DirectorySettings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

# === Auth Setup ===

tenant = config.azure_tenant_id
token_verifier = JWTVerifier(
    jwks_uri=f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys",
    issuer=f"https://login.microsoftonline.com/{tenant}/v2.0",
    audience=config.azure_client_id,
)
auth = OAuthProxy(
    upstream_authorization_endpoint=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
    upstream_token_endpoint=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
    upstream_client_id=config.azure_client_id,
    upstream_client_secret=config.azure_client_secret,
    upstream_scopes=[config.full_mcp_scope] + config.additional_auth_scopes_list,
    token_verifier=token_verifier,
    base_url=config.oauth_base_url,
)

# === Services ===

obo = OBOTokenExchange(
    client_id=config.azure_client_id,
    client_secret=config.azure_client_secret,
    token_endpoint=config.token_endpoint,
    graph_scopes=" ".join(config.graph_scopes_list),
    cache_ttl=config.obo_token_cache_ttl,
)
graph = GraphClient(base_url=config.graph_base_url)
directory = DirectoryService(obo=obo, graph=graph)

# === MCP Server ===

mcp = FastMCP(
    "DirectoryService",
    instructions=(
        "University directory lookup service. Use find_user to search for "
        "people by name, email, or NetID. Requires authentication."
    ),
    auth=auth,
)


@mcp.tool
async def find_user(query: str) -> str:
    """Search the university directory for a person.

    Search by name, email address, or NetID.
    Returns up to 10 matching results.

    Args:
        query: Name, email, or NetID to search for
    """
    token = get_access_token()
    if not token:
        return json.dumps({"error": "Not authenticated"})

    try:
        results = await directory.find_user(token.token, query)
    except OBOExchangeError as e:
        return json.dumps({"error": f"Authentication error: {e}. Try re-authenticating."})

    users = [UserResult.from_graph(r).model_dump() for r in results]
    return json.dumps({"query": query, "count": len(users), "results": users}, indent=2)


@mcp.tool
async def get_user_groups(user_id: str) -> str:
    """Get group memberships for a user.

    Args:
        user_id: The user's Azure AD object ID (from find_user results)
    """
    token = get_access_token()
    if not token:
        return json.dumps({"error": "Not authenticated"})

    try:
        groups = await directory.get_user_groups(token.token, user_id)
    except OBOExchangeError as e:
        return json.dumps({"error": f"Authentication error: {e}"})

    return json.dumps({
        "user_id": user_id,
        "count": len(groups),
        "groups": [{"id": g.get("id"), "name": g.get("displayName")} for g in groups],
    }, indent=2)


@mcp.tool
async def health_check() -> str:
    """Check the directory service status."""
    return json.dumps({"status": "healthy", "service": "DirectoryService"})


@mcp.tool
async def get_authenticated_user() -> str:
    """Get the authenticated user's information from their token."""
    token = get_access_token()
    if not token:
        return json.dumps({"error": "Not authenticated"})

    claims = token.claims or {}
    return json.dumps({
        "email": claims.get("preferred_username", "unknown"),
        "name": claims.get("name", "unknown"),
        "tenant_id": claims.get("tid", "unknown"),
    })


@mcp.resource("directory://auth/user", mime_type="application/json")
async def auth_user_resource() -> str:
    """The currently authenticated user's directory info."""
    token = get_access_token()
    if not token:
        return json.dumps({"error": "Not authenticated"})
    claims = token.claims or {}
    return json.dumps({
        "email": claims.get("preferred_username"),
        "name": claims.get("name"),
    })


if __name__ == "__main__":
    mcp.run(transport="http", host=config.server_host, port=config.server_port)
```

- [ ] **Step 9: Update composed_server.py**

```python
"""
Composed University Services Server

Mounts both the financial and directory servers under one endpoint.
"""

from fastmcp import FastMCP

from financial_server import mcp as financial_mcp
from directory_server import mcp as directory_mcp

main = FastMCP(
    "UniversityServices",
    instructions=(
        "Unified university services. Use finance_* tools for financial data, "
        "directory_* tools for people lookup."
    ),
)

main.mount(financial_mcp, namespace="finance")
main.mount(directory_mcp, namespace="directory")

if __name__ == "__main__":
    main.run(transport="http", host="0.0.0.0", port=8000)
```

- [ ] **Step 10: Create docs/azure-setup-step10.md**

```markdown
# Azure App Registration: OBO Flow (Step 10)

The On-Behalf-Of (OBO) flow requires a **second** Azure app registration for the directory server. This server exchanges the user's MCP token for a Microsoft Graph token.

## Why OBO?

Some organizations restrict application-level Graph API permissions. OBO lets the server call Graph **as the user**, using their delegated permissions. This provides:

- Per-user audit trails (Graph logs show the actual user, not a service account)
- Granular access control (users only see what they're permitted to see)
- No need for admin-consented application permissions

## Architecture

```
User → MCP Client → Directory Server → Azure AD (OBO) → Microsoft Graph
                         ↓
                    User's MCP token                  Graph API token
                    (custom scope)                    (Graph scopes)
```

1. User authenticates, gets MCP token with `api://<client-id>/access_as_user` scope
2. Directory server receives the MCP token
3. Server exchanges it for a Graph token via OBO grant
4. Server calls Graph API with the Graph token

## Step 1: Create the Directory App Registration

1. Azure Portal > **App registrations** > **New registration**
2. Name: `MCP Directory Server`
3. Account type: Single tenant
4. Redirect URI: Web — `http://localhost:8001/mcp/oauth/callback`
5. Register

Copy the **Client ID** and **Tenant ID**.

## Step 2: Create Client Secret

1. **Certificates & secrets** > **New client secret**
2. Copy the Value — this is `DIR_AZURE_CLIENT_SECRET`

## Step 3: Expose an API

1. **Expose an API** > Set Application ID URI (`api://<client-id>`)
2. **Add a scope**:
   - Name: `access_as_user`
   - Who can consent: Admins and users
   - Display name: "Access Directory as User"
   - State: Enabled

## Step 4: Add Microsoft Graph Permissions

1. **API permissions** > **Add a permission** > **Microsoft Graph** > **Delegated permissions**
2. Add:
   - `User.Read.All` — Read all users' profiles
   - `Directory.Read.All` — Read directory data
3. Click **Grant admin consent** (requires admin role)

**Why admin consent?** These permissions let the app read ANY user's profile in the directory. Individual users can't consent to this — an admin must approve it for the organization.

## Step 5: Configure knownClientApplications (Optional)

If the financial server and directory server share a client, configure consent propagation:

1. In the directory app's **Manifest** editor
2. Find `"knownClientApplications": []`
3. Add the financial server's client ID:
   ```json
   "knownClientApplications": ["<financial-server-client-id>"]
   ```
4. Save

This lets users consent to both apps' scopes in a single prompt.

## Step 6: Configure .env

```env
# Directory Server (OBO)
DIR_AZURE_CLIENT_ID=<Directory app client ID>
DIR_AZURE_CLIENT_SECRET=<Directory app client secret>
DIR_AZURE_TENANT_ID=<Tenant ID>
DIR_MCP_API_SCOPE=access_as_user
DIR_OAUTH_BASE_URL=http://localhost:8001
DIR_SERVER_PORT=8001
DIR_GRAPH_SCOPES=https://graph.microsoft.com/User.Read.All https://graph.microsoft.com/Directory.Read.All
```

## The OBO Token Exchange (Detailed)

```
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token

grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer
client_id=<directory-app-client-id>
client_secret=<directory-app-secret>
assertion=<user's MCP token>
scope=https://graph.microsoft.com/User.Read.All https://graph.microsoft.com/Directory.Read.All
requested_token_use=on_behalf_of
```

The response contains an `access_token` scoped for Microsoft Graph, with the user's identity embedded. This token can then be used to call Graph endpoints.

## Token Caching

The server caches Graph tokens with TTL (default 50 minutes):
- **Key**: SHA-256 hash of the user's MCP token (first 32 chars)
- **Value**: Graph token + timestamp + expiration
- **Eviction**: LRU when cache exceeds 500 entries
- **Expiry**: Checked on every access (both TTL and token expiration)

This avoids redundant OBO exchanges for the same user session.
```

- [ ] **Step 11: Update .env.example**

Add directory section:

```
# Directory Server (OBO) — Step 10
DIR_AZURE_CLIENT_ID=
DIR_AZURE_CLIENT_SECRET=
DIR_AZURE_TENANT_ID=
DIR_SERVER_PORT=8001
DIR_OAUTH_BASE_URL=http://localhost:8001
DIR_GRAPH_SCOPES=https://graph.microsoft.com/User.Read.All https://graph.microsoft.com/Directory.Read.All
```

- [ ] **Step 12: Update README.md**

Append:

```markdown
## Step 10: OBO Flow — Directory Server

The final step: a directory lookup server that calls Microsoft Graph on behalf of the user.

### On-Behalf-Of (OBO) Flow

The user authenticates once. The server exchanges their token for a Graph API token:

```
User token (api://app/access_as_user) → OBO exchange → Graph token (User.Read.All)
```

### Architecture

```
directory_server.py    — MCP server with auth
token_exchange.py      — OBO token cache and exchange
ms_graph_client.py     — Graph API wrapper
directory_service.py   — Business logic layer
models.py              — Pydantic models for results
```

### Tools

- `find_user(query)` — Search by name, email, or NetID
- `get_user_groups(user_id)` — Get group memberships
- `get_authenticated_user()` — Current user info
- `health_check()` — Service status

### Composed Server

`composed_server.py` mounts both financial + directory servers:
- `finance_query_sql`, `finance_ask` — financial tools
- `directory_find_user`, `directory_get_user_groups` — directory tools

See `docs/azure-setup-step10.md` for the two-app-registration walkthrough.
```

- [ ] **Step 13: Commit**

```bash
git add directory_server.py token_exchange.py ms_graph_client.py directory_service.py models.py composed_server.py config.py requirements.txt .env.example README.md docs/
git commit -m "feat: step-10 OBO directory server with Graph API

Directory MCP server using On-Behalf-Of flow, token exchange
with TTL cache, MS Graph integration, and composed server."
```
