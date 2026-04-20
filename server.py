"""
Step 08: Minimal Azure AD Auth Demo (Confidential Client)

The smallest possible MCP server gated by Azure AD using the confidential
client OAuth flow. The financial server, database, NL-to-SQL, and lifespan
machinery from earlier steps are intentionally absent — the only new
concept on this branch is auth.

Demonstrates:
  - Wiring an `OAuthProxy` against Azure AD (`upstream_*` endpoints)
  - JWT-based token verification with `JWTVerifier` (Azure issues JWT
    access tokens, so we can validate locally against the tenant's JWKS)
  - Confidential-client model: server holds a client secret, exchanges
    the auth code on the user's behalf
  - Reading the authenticated user's identity inside a tool

Endpoints exposed at runtime:
  - /mcp                                          — the MCP endpoint (auth required)
  - /.well-known/oauth-authorization-server       — OAuth metadata
  - /.well-known/oauth-protected-resource         — resource server metadata
  - /authorize, /token, /register, /callback      — OAuth proxy endpoints

Run:  python server.py

Required env vars (see .env.example):
  AZURE_TENANT_ID       Your Azure AD tenant ID
  AZURE_CLIENT_ID       Application (client) ID of the registered app
  AZURE_CLIENT_SECRET   Client secret value (NOT the secret ID)
  AZURE_API_SCOPE       default: "access_as_user"
  SERVER_BASE_URL       default: http://localhost:8000
"""

import logging
import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


# === Config (env-driven, kept inline so the demo is self-contained) ===

AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
AZURE_API_SCOPE = os.environ.get("AZURE_API_SCOPE", "access_as_user")
SERVER_BASE_URL = os.environ.get("SERVER_BASE_URL", "http://localhost:8000")
ADDITIONAL_SCOPES = [
    s.strip() for s in os.environ.get(
        "ADDITIONAL_AUTH_SCOPES", "email,openid,profile,offline_access"
    ).split(",") if s.strip()
]

if not (AZURE_TENANT_ID and AZURE_CLIENT_ID and AZURE_CLIENT_SECRET):
    raise RuntimeError(
        "AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET must all be set. "
        "See .env.example."
    )

FULL_MCP_SCOPE = f"api://{AZURE_CLIENT_ID}/{AZURE_API_SCOPE}"


# === Build the auth proxy ===

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
    upstream_client_secret=AZURE_CLIENT_SECRET,
    valid_scopes=_all_scopes,
    extra_authorize_params={"scope": " ".join(_all_scopes)},
    token_verifier=token_verifier,
    base_url=SERVER_BASE_URL,
)
logger.info("Azure OAuth (confidential client) enabled (tenant: %s)", AZURE_TENANT_ID)


# === MCP server ===

mcp = FastMCP(
    "AzureConfidentialDemo",
    instructions=(
        "Minimal MCP server gated by Azure AD (confidential client). Use "
        "whoami() to inspect the caller's identity claims, or hello(name) "
        "for a trivial greeting that still requires authentication."
    ),
    auth=auth,
)


@mcp.tool
def hello(name: str = "world") -> str:
    """Return a friendly greeting. Every tool is gated by auth."""
    return f"hello, {name}!"


@mcp.tool
def whoami() -> dict:
    """Return identity claims for the user currently calling this tool.

    Useful claim names from Azure AD:
      - oid     stable user object ID
      - upn     user principal name (typically email)
      - name    display name
      - tid     tenant ID
      - scp     space-separated granted scopes
    """
    tok = get_access_token()
    if tok is None:
        return {"error": "no access token in context"}
    interesting = ("oid", "upn", "preferred_username", "name", "tid", "scp", "appid")
    return {
        "client_id": tok.client_id,
        "scopes": tok.scopes,
        "claims": {k: tok.claims.get(k) for k in interesting if tok.claims.get(k) is not None},
    }


@mcp.resource("user://me")
def me() -> dict:
    """Identity claims as a resource (mirrors whoami())."""
    return whoami()


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
