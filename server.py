"""
Step 09: Minimal Azure Public-Client Auth Demo + Security Add-Ons

Builds on step 08 by switching from a confidential client to a public
client with PKCE, then layering on two production-leaning concerns:

  1. **User allowlist** — only configured emails may call sensitive tools.
  2. **Tamper-detected audit log** — every sensitive call is appended to a
     SHA-256 hash chain (see audit.py) so any later tampering is detectable.

Like steps 07 and 08, this branch deliberately strips the financial /
database / NL-to-SQL machinery so the auth + security pieces are the only
things on the page.

What's new versus step 08:
  - No `upstream_client_secret` → public client; PKCE proves identity.
  - `check_user_allowed()` gate around the privileged tool.
  - `audit.log(...)` on every privileged call (allowed or denied).

Endpoints exposed at runtime are the same as step 08.

Run:  python server.py

Required env vars (see .env.example):
  AZURE_TENANT_ID       Your Azure AD tenant ID
  AZURE_CLIENT_ID       Application (client) ID; configure the app as a
                        "Mobile and desktop applications" / public client
                        with redirect URI http://localhost:8000/callback
  AZURE_API_SCOPE       default: "access_as_user"
  SERVER_BASE_URL       default: http://localhost:8000
  ALLOWED_USERS         comma-separated emails; empty = allow any
                        authenticated user
  AUDIT_LOG_DIR         default: "logs"
"""

import logging
import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token

from audit import AuditLogger

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


# === Config (env-driven, kept inline so the demo is self-contained) ===

AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_API_SCOPE = os.environ.get("AZURE_API_SCOPE", "access_as_user")
SERVER_BASE_URL = os.environ.get("SERVER_BASE_URL", "http://localhost:8000")
ADDITIONAL_SCOPES = [
    s.strip() for s in os.environ.get(
        "ADDITIONAL_AUTH_SCOPES", "email,openid,profile,offline_access"
    ).split(",") if s.strip()
]
ALLOWED_USERS = [
    e.strip().lower() for e in os.environ.get("ALLOWED_USERS", "").split(",") if e.strip()
]
AUDIT_LOG_DIR = os.environ.get("AUDIT_LOG_DIR", "logs")
JWT_SIGNING_KEY = os.environ.get("JWT_SIGNING_KEY", "")

if not (AZURE_TENANT_ID and AZURE_CLIENT_ID):
    raise RuntimeError(
        "AZURE_TENANT_ID and AZURE_CLIENT_ID must be set. See .env.example."
    )
if not JWT_SIGNING_KEY:
    raise RuntimeError(
        "JWT_SIGNING_KEY must be set when using a public client (no upstream "
        "client secret). Generate one with:  python -c \"import secrets; "
        "print(secrets.token_urlsafe(32))\""
    )

FULL_MCP_SCOPE = f"api://{AZURE_CLIENT_ID}/{AZURE_API_SCOPE}"


# === Build the auth proxy (PUBLIC client — no client_secret) ===
# Azure validates the request via PKCE (forward_pkce=True is the default)
# instead of a shared secret. Configure the Azure app registration as
# "Mobile and desktop applications" so it accepts public-client requests.

token_verifier = JWTVerifier(
    jwks_uri=f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/discovery/v2.0/keys",
    issuer=f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/v2.0",
    audience=AZURE_CLIENT_ID,
)

_all_scopes = [FULL_MCP_SCOPE] + ADDITIONAL_SCOPES

auth = OAuthProxy(
    upstream_authorization_endpoint=f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/authorize",
    upstream_token_endpoint=f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token",
    upstream_client_id=AZURE_CLIENT_ID,
    valid_scopes=_all_scopes,
    extra_authorize_params={"scope": " ".join(_all_scopes)},
    token_verifier=token_verifier,
    base_url=SERVER_BASE_URL,
    jwt_signing_key=JWT_SIGNING_KEY,
)
logger.info("Azure OAuth (public client + PKCE) enabled (tenant: %s)", AZURE_TENANT_ID)
if ALLOWED_USERS:
    logger.info("Allowlist active: %d user(s)", len(ALLOWED_USERS))
else:
    logger.warning("Allowlist empty — privileged tools will accept any authenticated user")


# === Security helpers ===

audit = AuditLogger(AUDIT_LOG_DIR)


def caller_email() -> str:
    """Pull the caller's email from the access token claims."""
    tok = get_access_token()
    if tok is None:
        return ""
    return (tok.claims.get("upn") or tok.claims.get("preferred_username") or tok.claims.get("email") or "").lower()


def check_user_allowed(email: str) -> bool:
    """Return True iff the email is on the allowlist (empty allowlist = allow all)."""
    return not ALLOWED_USERS or email in ALLOWED_USERS


# === MCP server ===

mcp = FastMCP(
    "AzurePublicClientDemo",
    instructions=(
        "Minimal MCP server gated by Azure AD (public client + PKCE). "
        "Some tools additionally require the caller to be on the allowlist; "
        "every sensitive call is appended to a hash-chained audit log."
    ),
    auth=auth,
)


@mcp.tool
def hello(name: str = "world") -> str:
    """Return a friendly greeting. Authenticated, but not allowlisted."""
    return f"hello, {name}!"


@mcp.tool
def whoami() -> dict:
    """Return identity claims for the user currently calling this tool."""
    tok = get_access_token()
    if tok is None:
        return {"error": "no access token in context"}
    interesting = ("oid", "upn", "preferred_username", "name", "tid", "scp")
    return {
        "client_id": tok.client_id,
        "scopes": tok.scopes,
        "claims": {k: tok.claims.get(k) for k in interesting if tok.claims.get(k) is not None},
    }


@mcp.tool
def privileged_action(message: str) -> dict:
    """Allowlist-gated tool. Returns the message verbatim on success.

    Demonstrates the security pattern: extract email from the token,
    check it against ALLOWED_USERS, audit the outcome regardless.
    """
    email = caller_email()
    if not check_user_allowed(email):
        audit.log(email or "<unknown>", "DENIED", f"privileged_action: {message[:200]}")
        return {"error": "not authorized", "user": email}
    audit.log(email, "ALLOWED", f"privileged_action: {message[:200]}")
    return {"ok": True, "user": email, "echoed": message}


@mcp.resource("user://me")
def me() -> dict:
    """Identity claims as a resource (mirrors whoami())."""
    return whoami()


@mcp.resource("audit://verify")
def verify_audit_chain() -> dict:
    """Verify the integrity of the current month's audit log."""
    valid, count = audit.verify_chain()
    return {"valid": valid, "entries": count}


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
