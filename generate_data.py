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

# ---------------------------------------------------------------------------
# Reference Data
# ---------------------------------------------------------------------------

SCHOOLS = {
    "Arts & Sciences": {
        "COMPSCI": "Computer Science",
        "MATH": "Mathematics",
        "PHYS": "Physics",
        "CHEM": "Chemistry",
        "BIO": "Biology",
        "ENGLISH": "English",
        "HISTORY": "History",
        "POLISCI": "Political Science",
        "ECON": "Economics",
        "PSYCH": "Psychology",
        "SOCIOL": "Sociology",
        "PHILO": "Philosophy",
        "ROMANCE": "Romance Studies",
        "STATS": "Statistical Science",
        "NEURO": "Neuroscience",
    },
    "Engineering": {
        "ECE": "Electrical & Computer Engineering",
        "MECHENG": "Mechanical Engineering",
        "CIVENG": "Civil & Environmental Engineering",
        "BME": "Biomedical Engineering",
        "MATSCI": "Materials Science",
    },
    "Medicine": {
        "MEDSCHOOL": "School of Medicine",
        "PATHOL": "Pathology",
        "PEDS": "Pediatrics",
        "SURG": "Surgery",
        "NEUROMD": "Neurology",
        "CARDIO": "Cardiology",
        "ONCOL": "Oncology",
        "RADIOL": "Radiology",
    },
    "Law": {
        "LAW": "School of Law",
        "LAWCLIN": "Law Clinical Programs",
    },
    "Business": {
        "BUSINESS": "School of Business",
        "FINANCE": "Finance Department",
        "MKTG": "Marketing",
    },
    "Public Policy": {
        "PUBPOL": "Public Policy",
        "ENVIRON": "Environmental Policy",
    },
    "Nursing": {
        "NURSING": "School of Nursing",
    },
    "Divinity": {
        "DIVINITY": "Divinity School",
    },
    "Graduate School": {
        "GRADSCH": "Graduate School Administration",
    },
    "Central Administration": {
        "PROVOST": "Provost Office",
        "FINAID": "Financial Aid",
        "REGIST": "Registrar",
        "ITDEPT": "Information Technology",
        "FACMGMT": "Facilities Management",
        "HR": "Human Resources",
        "LIBR": "University Libraries",
        "ATHLET": "Athletics",
        "ALUMNI": "Alumni Affairs",
        "RESADM": "Research Administration",
    },
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

# (code, name, category, subcategory, normal_balance)
CHART_OF_ACCOUNTS = [
    # Revenue - Tuition
    ("4100", "Undergraduate Tuition", "revenue", "tuition", "credit"),
    ("4110", "Graduate Tuition", "revenue", "tuition", "credit"),
    ("4120", "Professional Program Tuition", "revenue", "tuition", "credit"),
    # Revenue - State Appropriations
    ("4200", "State Appropriations", "revenue", "state_appropriations", "credit"),
    # Revenue - Grants
    ("4300", "Federal Grants", "revenue", "grants", "credit"),
    ("4310", "State Grants", "revenue", "grants", "credit"),
    ("4320", "Private Grants", "revenue", "grants", "credit"),
    # Revenue - Gifts
    ("4400", "Gifts and Donations", "revenue", "gifts", "credit"),
    # Revenue - Investment
    ("4500", "Investment Income", "revenue", "investment", "credit"),
    # Revenue - Auxiliary
    ("4600", "Housing Revenue", "revenue", "auxiliary_revenue", "credit"),
    ("4610", "Dining Revenue", "revenue", "auxiliary_revenue", "credit"),
    ("4620", "Parking Revenue", "revenue", "auxiliary_revenue", "credit"),
    ("4630", "Bookstore Revenue", "revenue", "auxiliary_revenue", "credit"),
    # Revenue - Clinical
    ("4700", "Clinical Revenue", "revenue", "clinical", "credit"),
    # Revenue - IDC Recovery
    ("4800", "Indirect Cost Recovery", "revenue", "idc_recovery", "credit"),
    # Revenue - Other
    ("4900", "Other Revenue", "revenue", "other_revenue", "credit"),
    # Expenses - Salaries
    ("5110", "Faculty Salaries", "expense", "salaries", "debit"),
    ("5120", "Staff Salaries", "expense", "salaries", "debit"),
    ("5130", "Graduate Assistant Stipends", "expense", "salaries", "debit"),
    ("5140", "Temporary Wages", "expense", "salaries", "debit"),
    # Expenses - Benefits
    ("5200", "Health Insurance", "expense", "benefits", "debit"),
    ("5210", "Retirement Contributions", "expense", "benefits", "debit"),
    ("5220", "FICA/Payroll Taxes", "expense", "benefits", "debit"),
    ("5230", "Tuition Remission", "expense", "benefits", "debit"),
    # Expenses - Supplies
    ("6100", "Office Supplies", "expense", "supplies", "debit"),
    ("6110", "Laboratory Supplies", "expense", "supplies", "debit"),
    ("6120", "Computer Supplies", "expense", "supplies", "debit"),
    ("6130", "Medical Supplies", "expense", "supplies", "debit"),
    # Expenses - Travel
    ("6200", "Domestic Travel", "expense", "travel", "debit"),
    ("6210", "International Travel", "expense", "travel", "debit"),
    ("6220", "Conference Registration", "expense", "travel", "debit"),
    # Expenses - Equipment
    ("6300", "Computer Equipment", "expense", "equipment", "debit"),
    ("6310", "Laboratory Equipment", "expense", "equipment", "debit"),
    ("6320", "Furniture & Fixtures", "expense", "equipment", "debit"),
    ("6330", "Medical Equipment", "expense", "equipment", "debit"),
    # Expenses - Services
    ("6400", "Consulting Services", "expense", "services", "debit"),
    ("6410", "Software Licenses", "expense", "services", "debit"),
    ("6420", "Maintenance Contracts", "expense", "services", "debit"),
    ("6430", "Printing & Publications", "expense", "services", "debit"),
    ("6440", "Telecommunications", "expense", "services", "debit"),
    # Expenses - Facilities
    ("6500", "Utilities", "expense", "facilities", "debit"),
    ("6510", "Rent & Leases", "expense", "facilities", "debit"),
    ("6520", "Building Maintenance", "expense", "facilities", "debit"),
    # Expenses - Financial Aid
    ("6600", "Scholarships", "expense", "financial_aid", "debit"),
    ("6610", "Fellowships", "expense", "financial_aid", "debit"),
    ("6620", "Student Grants-in-Aid", "expense", "financial_aid", "debit"),
    # Expenses - Subcontracts
    ("6700", "Subcontract Expenses", "expense", "subcontracts", "debit"),
    # Expenses - Other
    ("6800", "Insurance", "expense", "other_expense", "debit"),
    ("6810", "Memberships & Dues", "expense", "other_expense", "debit"),
    ("6820", "Recruiting Expenses", "expense", "other_expense", "debit"),
    ("6830", "Entertainment & Events", "expense", "other_expense", "debit"),
    # Expenses - Depreciation
    ("6900", "Depreciation Expense", "expense", "depreciation", "debit"),
    # Expenses - Transfers
    ("7000", "Interfund Transfers", "expense", "transfers", "debit"),
    # Expenses - Debt Service
    ("7100", "Debt Service - Interest", "expense", "debt_service", "debit"),
    # Assets - Cash
    ("1100", "Cash and Cash Equivalents", "asset", "cash", "debit"),
    # Assets - Receivables
    ("1200", "Accounts Receivable", "asset", "receivables", "debit"),
    ("1210", "Grants Receivable", "asset", "receivables", "debit"),
    # Assets - Prepaid
    ("1300", "Prepaid Expenses", "asset", "prepaid", "debit"),
    # Assets - Investments
    ("1400", "Investments", "asset", "investments", "debit"),
    # Assets - Fixed Assets
    ("1500", "Land", "asset", "fixed_assets", "debit"),
    ("1510", "Buildings", "asset", "fixed_assets", "debit"),
    ("1520", "Equipment", "asset", "fixed_assets", "debit"),
    ("1530", "Accumulated Depreciation", "asset", "fixed_assets", "credit"),
    # Liabilities - AP
    ("2100", "Accounts Payable", "liability", "accounts_payable", "credit"),
    # Liabilities - Accrued
    ("2200", "Accrued Salaries", "liability", "accrued", "credit"),
    ("2210", "Accrued Benefits", "liability", "accrued", "credit"),
    # Liabilities - Deferred
    ("2300", "Deferred Tuition Revenue", "liability", "deferred", "credit"),
    ("2310", "Deferred Grant Revenue", "liability", "deferred", "credit"),
    # Liabilities - Bonds
    ("2400", "Bonds Payable", "liability", "bonds", "credit"),
    # Equity
    ("3100", "Unrestricted Net Assets", "equity", "unrestricted", "credit"),
    ("3200", "Temporarily Restricted Net Assets", "equity", "temporarily_restricted", "credit"),
    ("3300", "Permanently Restricted Net Assets", "equity", "permanently_restricted", "credit"),
]

GRANT_SPONSORS = [
    "NSF", "NIH", "DOD", "DOE", "NASA", "DARPA", "HHMI",
    "Gates Foundation", "Mellon Foundation", "Ford Foundation",
    "Sloan Foundation", "NEH", "AHA", "ACS", "Simons Foundation",
]

VENDORS = {
    "supplies": [
        "Fisher Scientific", "VWR International", "Sigma-Aldrich",
        "Staples Business", "Amazon Business", "CDW Government",
        "Grainger", "Thomas Scientific", "Carolina Biological",
        "Office Depot Business",
    ],
    "equipment": [
        "Dell Technologies", "Apple Inc.", "Lenovo", "HP Enterprise",
        "Thermo Fisher Scientific", "Agilent Technologies",
        "Bio-Rad Laboratories", "Herman Miller", "Steelcase",
    ],
    "services": [
        "Microsoft Corporation", "Adobe Systems", "Amazon Web Services",
        "Google Cloud", "Deloitte Consulting", "McKinsey & Company",
        "KPMG", "Oracle Corporation", "Salesforce", "ServiceNow",
    ],
    "travel": [
        "American Airlines", "Delta Air Lines", "United Airlines",
        "Marriott International", "Hilton Hotels",
        "Enterprise Rent-A-Car",
    ],
    "facilities": [
        "Duke Power", "Piedmont Natural Gas", "CBRE Group",
        "Johnson Controls", "Siemens Building Technologies",
    ],
}

# Research-active schools for grant generation
RESEARCH_SCHOOLS = {"Arts & Sciences", "Engineering", "Medicine", "Public Policy"}

# Fund weights for transaction generation
FUND_WEIGHTS = {
    "10": 0.55,
    "20": 0.15,
    "25": 0.03,
    "30": 0.05,
    "40": 0.07,
    "50": 0.03,
    "60": 0.07,
    "70": 0.05,
}

# Amount ranges by expense subcategory
AMOUNT_RANGES = {
    "salaries": (2000, 25000),
    "benefits": (500, 8000),
    "supplies": (10, 5000),
    "travel": (100, 8000),
    "equipment": (500, 150000),
    "services": (100, 50000),
    "facilities": (200, 25000),
    "financial_aid": (500, 30000),
    "subcontracts": (1000, 100000),
    "other_expense": (50, 10000),
    "depreciation": (1000, 50000),
    "transfers": (1000, 500000),
    "debt_service": (5000, 200000),
}

# Revenue amount ranges
REVENUE_RANGES = {
    "tuition": (5000, 50000),
    "state_appropriations": (50000, 500000),
    "grants": (1000, 200000),
    "gifts": (100, 1000000),
    "investment": (1000, 500000),
    "auxiliary_revenue": (500, 50000),
    "clinical": (200, 100000),
    "idc_recovery": (500, 50000),
    "other_revenue": (100, 25000),
}


# ---------------------------------------------------------------------------
# Database Setup Functions
# ---------------------------------------------------------------------------


def generate_departments(conn):
    """Create departments table and return list of (code, name, school) tuples."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            dept_code TEXT PRIMARY KEY,
            dept_name TEXT NOT NULL,
            school TEXT NOT NULL
        )
    """)
    departments = []
    for school, depts in SCHOOLS.items():
        for code, name in depts.items():
            departments.append((code, name, school))
    conn.executemany(
        "INSERT INTO departments (dept_code, dept_name, school) VALUES (?, ?, ?)",
        departments,
    )
    conn.commit()
    print(f"  Created {len(departments)} departments across {len(SCHOOLS)} schools")
    return departments


def generate_chart_of_accounts(conn):
    """Create chart_of_accounts table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chart_of_accounts (
            account_code TEXT PRIMARY KEY,
            account_name TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT NOT NULL,
            normal_balance TEXT NOT NULL
        )
    """)
    conn.executemany(
        "INSERT INTO chart_of_accounts (account_code, account_name, category, subcategory, normal_balance) VALUES (?, ?, ?, ?, ?)",
        CHART_OF_ACCOUNTS,
    )
    conn.commit()
    print(f"  Created {len(CHART_OF_ACCOUNTS)} GL accounts")


def generate_funds(conn):
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
        "INSERT INTO funds (fund_code, fund_name, fund_type, description) VALUES (?, ?, ?, ?)",
        FUNDS,
    )
    conn.commit()
    print(f"  Created {len(FUNDS)} funds")


def generate_grants(conn, departments, count=200):
    """Create grants table with synthetic grant data.

    Only assigns grants to research-active departments (A&S, Engineering,
    Medicine, Public Policy). Uses Faker for PI names. Grants span 2-5 years
    starting between 2020 and 2024.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS grants (
            grant_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            sponsor TEXT NOT NULL,
            pi_name TEXT NOT NULL,
            department TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            total_budget REAL NOT NULL,
            remaining_budget REAL NOT NULL,
            status TEXT NOT NULL
        )
    """)

    research_depts = [
        (code, name, school)
        for code, name, school in departments
        if school in RESEARCH_SCHOOLS
    ]

    grants = []
    reference_date = date(2025, 6, 30)

    for _ in range(count):
        sponsor = random.choice(GRANT_SPONSORS)
        # Create grant_id with sponsor prefix
        grant_num = random.randint(1000000, 9999999)
        grant_id = f"{sponsor.split()[0].upper()}-{grant_num}"

        dept_code, dept_name, school = random.choice(research_depts)
        pi_name = fake.name()
        title = fake.catch_phrase() + " Research"

        # Grant duration 2-5 years, starting 2020-2024
        start_year = random.randint(2020, 2024)
        start_month = random.randint(1, 12)
        start_dt = date(start_year, start_month, 1)
        duration_years = random.randint(2, 5)
        end_dt = date(
            min(start_year + duration_years, 2029),
            start_month,
            28,  # safe end-of-month
        )

        total_budget = round(random.uniform(50000, 5000000), 2)

        # Calculate remaining budget based on progress through grant period
        total_days = (end_dt - start_dt).days
        elapsed_days = (reference_date - start_dt).days
        if elapsed_days <= 0:
            fraction_spent = 0.0
            status = "pending"
        elif elapsed_days >= total_days:
            fraction_spent = 1.0
            status = "closed"
        else:
            fraction_spent = elapsed_days / total_days
            # Add some randomness to spending rate
            fraction_spent = min(1.0, fraction_spent * random.uniform(0.7, 1.3))
            status = "active"

        remaining_budget = round(total_budget * (1 - fraction_spent), 2)
        remaining_budget = max(0, remaining_budget)

        grants.append((
            grant_id, title, sponsor, pi_name, dept_code,
            start_dt.isoformat(), end_dt.isoformat(),
            total_budget, remaining_budget, status,
        ))

    conn.executemany(
        "INSERT INTO grants (grant_id, title, sponsor, pi_name, department, start_date, end_date, total_budget, remaining_budget, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        grants,
    )
    conn.commit()
    print(f"  Created {len(grants)} grants across {len(research_depts)} research departments")
    return grants


def create_transactions_table(conn):
    """Create the gl_transactions table with all 29 columns."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gl_transactions (
            transaction_id TEXT PRIMARY KEY,
            fiscal_year INTEGER NOT NULL,
            fiscal_period INTEGER NOT NULL,
            transaction_date TEXT NOT NULL,
            posting_date TEXT NOT NULL,
            department_code TEXT NOT NULL,
            department_name TEXT NOT NULL,
            school TEXT NOT NULL,
            fund_code TEXT NOT NULL,
            fund_name TEXT NOT NULL,
            fund_type TEXT NOT NULL,
            account_code TEXT NOT NULL,
            account_name TEXT NOT NULL,
            account_category TEXT NOT NULL,
            account_subcategory TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            budget_amount REAL NOT NULL DEFAULT 0,
            encumbrance_amount REAL NOT NULL DEFAULT 0,
            encumbrance_type TEXT,
            grant_id TEXT,
            grant_pi TEXT,
            grant_sponsor TEXT,
            vendor_name TEXT,
            description TEXT,
            reference_number TEXT,
            batch_id TEXT,
            is_adjustment INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    print("  Created gl_transactions table")


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def fiscal_period_for_date(d):
    """Convert calendar date to (fiscal_year, period).

    Higher-ed fiscal year: July = period 1, June = period 12.
    July 2024 -> FY2025 period 1; June 2025 -> FY2025 period 12.
    """
    if d.month >= 7:
        fiscal_year = d.year + 1
        period = d.month - 6
    else:
        fiscal_year = d.year
        period = d.month + 6
    return fiscal_year, period


def seasonal_weight(period):
    """Return a spending weight for the given fiscal period (1-12).

    Higher spending in Q1 (Jul-Sep, periods 1-3) for new fiscal year
    startup and Q4 (Apr-Jun, periods 10-12) for year-end spending.
    Lower mid-year.
    """
    weights = {
        1: 1.3,   # July - new FY startup
        2: 1.2,   # August - fall semester prep
        3: 1.1,   # September - fall semester
        4: 0.9,   # October
        5: 0.8,   # November
        6: 0.7,   # December - holiday slowdown
        7: 0.8,   # January - spring startup
        8: 0.9,   # February
        9: 0.9,   # March
        10: 1.1,  # April - year-end ramp
        11: 1.2,  # May - year-end spending
        12: 1.3,  # June - fiscal year close
    }
    return weights.get(period, 1.0)


# ---------------------------------------------------------------------------
# Transaction Generator
# ---------------------------------------------------------------------------


def generate_transactions(conn, departments, grants, target_count=500000):
    """Generate synthetic GL transactions.

    Date range: FY2022 (Jul 2021) through FY2025 (Jun 2025).
    """
    # Build lookup structures
    fund_codes = [f[0] for f in FUNDS]
    fund_weights_list = [FUND_WEIGHTS[f[0]] for f in FUNDS]
    fund_lookup = {f[0]: (f[1], f[2]) for f in FUNDS}

    dept_list = [(code, name, school) for code, name, school in departments]

    expense_accounts = [a for a in CHART_OF_ACCOUNTS if a[2] == "expense"]
    revenue_accounts = [a for a in CHART_OF_ACCOUNTS if a[2] == "revenue"]
    all_accounts = expense_accounts + revenue_accounts

    active_grants = [g for g in grants if g[9] in ("active", "pending")]

    # Map subcategories to vendor lists
    vendor_subcategories = set(VENDORS.keys())

    # Date range: July 1, 2021 through June 30, 2025
    start_date = date(2021, 7, 1)
    end_date = date(2025, 6, 30)
    total_days = (end_date - start_date).days

    encumbrance_types = ["purchase_order", "contract", "salary_commitment", "travel_authorization"]

    rows = []
    batch_num = 0

    print(f"  Generating {target_count:,} transactions...")

    for _ in range(target_count):
        # Random date with seasonal weighting
        rand_day = random.randint(0, total_days)
        txn_date = start_date + timedelta(days=rand_day)
        fy, period = fiscal_period_for_date(txn_date)

        # Apply seasonal weight - skip and retry if weight test fails
        if random.random() > seasonal_weight(period):
            # Still count this iteration but adjust the date
            txn_date = start_date + timedelta(days=random.randint(0, total_days))
            fy, period = fiscal_period_for_date(txn_date)

        # Select fund
        fund_code = random.choices(fund_codes, weights=fund_weights_list, k=1)[0]
        fund_name, fund_type = fund_lookup[fund_code]

        # Select department
        dept_code, dept_name, school = random.choice(dept_list)

        # Entry type: 85% actual, 10% budget, 5% encumbrance
        entry_roll = random.random()
        if entry_roll < 0.85:
            entry_type = "actual"
        elif entry_roll < 0.95:
            entry_type = "budget"
        else:
            entry_type = "encumbrance"

        # Select account (expense-heavy for actuals, mix for budget)
        if entry_type == "actual":
            if random.random() < 0.75:
                account = random.choice(expense_accounts)
            else:
                account = random.choice(revenue_accounts)
        elif entry_type == "budget":
            account = random.choice(all_accounts)
        else:  # encumbrance
            account = random.choice(expense_accounts)

        acct_code, acct_name, acct_category, acct_subcategory, normal_balance = account

        # Calculate amount
        if acct_category == "expense":
            amt_range = AMOUNT_RANGES.get(acct_subcategory, (100, 10000))
        else:
            amt_range = REVENUE_RANGES.get(acct_subcategory, (100, 50000))
        base_amount = round(random.uniform(amt_range[0], amt_range[1]), 2)

        # Determine amounts based on entry type
        amount = 0.0
        budget_amount = 0.0
        encumbrance_amount = 0.0
        enc_type = None

        if entry_type == "actual":
            amount = base_amount
            # 15% of actuals also have encumbrance (liquidation)
            if random.random() < 0.15:
                encumbrance_amount = -base_amount  # negative = liquidation
                enc_type = random.choice(encumbrance_types)
        elif entry_type == "budget":
            budget_amount = base_amount
        else:  # encumbrance
            encumbrance_amount = base_amount
            enc_type = random.choice(encumbrance_types)

        # Is adjustment? 3% chance
        is_adjustment = 1 if random.random() < 0.03 else 0
        if is_adjustment and entry_type == "actual":
            amount = -abs(amount)  # adjustments are typically negative

        # Grant info for restricted fund transactions
        grant_id = None
        grant_pi = None
        grant_sponsor = None
        if fund_code == "20" and active_grants:
            grant = random.choice(active_grants)
            grant_id = grant[0]
            grant_pi = grant[3]
            grant_sponsor = grant[2]

        # Vendor name for expense actuals
        vendor_name = None
        if entry_type == "actual" and acct_category == "expense":
            if acct_subcategory in vendor_subcategories:
                vendor_name = random.choice(VENDORS[acct_subcategory])
            elif acct_subcategory in ("other_expense", "depreciation", "transfers", "debt_service"):
                vendor_name = None
            else:
                # For benefits, salaries, financial_aid, subcontracts
                vendor_name = None

        # Description
        if is_adjustment:
            description = f"Adjustment: {acct_name} - {dept_name}"
        elif entry_type == "budget":
            description = f"FY{fy} Budget: {acct_name} - {dept_name}"
        elif entry_type == "encumbrance":
            description = f"Encumbrance: {acct_name} - {dept_name} ({enc_type})"
        else:
            if vendor_name:
                description = f"{acct_name} - {vendor_name}"
            elif grant_id:
                description = f"{acct_name} - Grant {grant_id}"
            else:
                description = f"{acct_name} - {dept_name}"

        # Generate IDs
        transaction_id = str(uuid.uuid4())
        reference_number = f"REF-{fy}-{random.randint(100000, 999999)}"
        batch_id = f"BATCH-{txn_date.strftime('%Y%m%d')}-{random.randint(100, 999)}"
        posting_date = (txn_date + timedelta(days=random.randint(0, 3))).isoformat()

        rows.append((
            transaction_id,
            fy,
            period,
            txn_date.isoformat(),
            posting_date,
            dept_code,
            dept_name,
            school,
            fund_code,
            fund_name,
            fund_type,
            acct_code,
            acct_name,
            acct_category,
            acct_subcategory,
            entry_type,
            amount,
            budget_amount,
            encumbrance_amount,
            enc_type,
            grant_id,
            grant_pi,
            grant_sponsor,
            vendor_name,
            description,
            reference_number,
            batch_id,
            is_adjustment,
            txn_date.isoformat(),  # created_at
        ))

        # Batch insert every 10,000 rows
        if len(rows) >= 10000:
            conn.executemany(
                """INSERT INTO gl_transactions (
                    transaction_id, fiscal_year, fiscal_period,
                    transaction_date, posting_date, department_code,
                    department_name, school, fund_code, fund_name,
                    fund_type, account_code, account_name,
                    account_category, account_subcategory, entry_type,
                    amount, budget_amount, encumbrance_amount,
                    encumbrance_type, grant_id, grant_pi, grant_sponsor,
                    vendor_name, description, reference_number,
                    batch_id, is_adjustment, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )
            conn.commit()
            batch_num += 1
            count_so_far = batch_num * 10000
            print(f"    Inserted {count_so_far:>8,} / {target_count:,} transactions")
            rows = []

    # Insert remaining rows
    if rows:
        conn.executemany(
            """INSERT INTO gl_transactions (
                transaction_id, fiscal_year, fiscal_period,
                transaction_date, posting_date, department_code,
                department_name, school, fund_code, fund_name,
                fund_type, account_code, account_name,
                account_category, account_subcategory, entry_type,
                amount, budget_amount, encumbrance_amount,
                encumbrance_type, grant_id, grant_pi, grant_sponsor,
                vendor_name, description, reference_number,
                batch_id, is_adjustment, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
        print(f"    Inserted {target_count:>8,} / {target_count:,} transactions")


# ---------------------------------------------------------------------------
# Indexes and Summary
# ---------------------------------------------------------------------------


def create_indexes(conn):
    """Create indexes for common query patterns."""
    indexes = [
        ("idx_txn_fiscal_year", "gl_transactions(fiscal_year)"),
        ("idx_txn_fiscal_period", "gl_transactions(fiscal_year, fiscal_period)"),
        ("idx_txn_date", "gl_transactions(transaction_date)"),
        ("idx_txn_dept", "gl_transactions(department_code)"),
        ("idx_txn_school", "gl_transactions(school)"),
        ("idx_txn_fund", "gl_transactions(fund_code)"),
        ("idx_txn_fund_type", "gl_transactions(fund_type)"),
        ("idx_txn_account", "gl_transactions(account_code)"),
        ("idx_txn_category", "gl_transactions(account_category)"),
        ("idx_txn_subcategory", "gl_transactions(account_subcategory)"),
        ("idx_txn_entry_type", "gl_transactions(entry_type)"),
        ("idx_txn_grant", "gl_transactions(grant_id)"),
    ]
    for idx_name, idx_def in indexes:
        conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")
    conn.commit()
    print(f"  Created {len(indexes)} indexes")


def print_summary(conn):
    """Print summary statistics about the generated dataset."""
    print("\n" + "=" * 60)
    print("Dataset Summary")
    print("=" * 60)

    # Total transactions
    total = conn.execute("SELECT COUNT(*) FROM gl_transactions").fetchone()[0]
    print(f"\nTotal transactions: {total:,}")

    # By entry type
    print("\nBy entry type:")
    for row in conn.execute(
        "SELECT entry_type, COUNT(*) as cnt FROM gl_transactions GROUP BY entry_type ORDER BY cnt DESC"
    ):
        print(f"  {row[0]:20s} {row[1]:>10,}")

    # By fund type
    print("\nBy fund type:")
    for row in conn.execute(
        "SELECT fund_type, COUNT(*) as cnt FROM gl_transactions GROUP BY fund_type ORDER BY cnt DESC"
    ):
        print(f"  {row[0]:20s} {row[1]:>10,}")

    # By fiscal year
    print("\nBy fiscal year:")
    for row in conn.execute(
        "SELECT fiscal_year, COUNT(*) as cnt FROM gl_transactions GROUP BY fiscal_year ORDER BY fiscal_year"
    ):
        print(f"  FY{row[0]}              {row[1]:>10,}")

    # Database file size
    db_path = conn.execute("PRAGMA database_list").fetchone()[2]
    if db_path:
        size_mb = Path(db_path).stat().st_size / (1024 * 1024)
        print(f"\nDatabase size: {size_mb:.1f} MB")

    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic university general ledger transactions"
    )
    parser.add_argument(
        "--output",
        default="data/university_gl.db",
        help="Output SQLite database path (default: data/university_gl.db)",
    )
    parser.add_argument(
        "--transactions",
        type=int,
        default=500000,
        help="Number of transactions to generate (default: 500000)",
    )
    args = parser.parse_args()

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database
    if output_path.exists():
        output_path.unlink()

    print(f"Generating university GL dataset: {output_path}")
    print(f"Target transactions: {args.transactions:,}\n")

    conn = sqlite3.connect(str(output_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    print("Creating reference tables...")
    departments = generate_departments(conn)
    generate_chart_of_accounts(conn)
    generate_funds(conn)
    grants = generate_grants(conn, departments)

    print("\nCreating transactions table...")
    create_transactions_table(conn)

    print("\nGenerating transactions...")
    generate_transactions(conn, departments, grants, args.transactions)

    print("\nCreating indexes...")
    create_indexes(conn)

    print_summary(conn)

    conn.close()
    print(f"\nDone! Database written to: {output_path}")


if __name__ == "__main__":
    main()
