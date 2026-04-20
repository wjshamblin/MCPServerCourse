"""
Step 08: Minimal Azure AD Auth Demo (Confidential Client)

The smallest possible MCP server gated by Azure AD using the confidential
client OAuth flow. The financial server, database, NL-to-SQL, and lifespan
machinery from earlier steps are intentionally absent — the only new
concept on this branch is auth.

Reference:
  FastMCP Azure (Microsoft Entra ID) OAuth integration guide:
  https://gofastmcp.com/integrations/azure#azure-microsoft-entra-id-oauth--fastmcp

Demonstrates:
  - Wiring FastMCP's purpose-built `AzureProvider` against an Entra tenant
  - JWT-based token verification (built into `AzureProvider` — Azure issues
    JWT access tokens, so we validate locally against the tenant's JWKS)
  - Confidential-client model: server holds a client secret, exchanges
    the auth code on the user's behalf
  - Reading the authenticated user's identity inside a tool

Endpoints exposed at runtime:
  - /mcp                                          — the MCP endpoint (auth required)
  - /.well-known/oauth-authorization-server       — OAuth metadata
  - /.well-known/oauth-protected-resource         — resource server metadata
  - /authorize, /token, /register                 — OAuth proxy endpoints
  - /auth/callback                                — redirect URI registered with Azure

Run:  python server.py

Required env vars (see .env.example):
  AZURE_TENANT_ID       Your Azure AD tenant ID
  AZURE_CLIENT_ID       Application (client) ID of the registered app
  AZURE_CLIENT_SECRET   Client secret value (NOT the secret ID)
  AZURE_API_SCOPE       default: "access_as_user"  (unprefixed — AzureProvider
                        prepends `api://<client_id>/` automatically)
  AZURE_GRAPH_SCOPES    optional, comma-separated Microsoft Graph scopes
                        (e.g. "https://graph.microsoft.com/User.Read")
  SERVER_BASE_URL       default: http://localhost:8000
"""

import logging
import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.azure import AzureProvider
from fastmcp.server.dependencies import get_access_token

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


# === Config (env-driven, kept inline so the demo is self-contained) ===

AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
AZURE_API_SCOPE_RAW = os.environ.get("AZURE_API_SCOPE", "access_as_user")
AZURE_GRAPH_SCOPES_RAW = os.environ.get("AZURE_GRAPH_SCOPES", "")
SERVER_BASE_URL = os.environ.get("SERVER_BASE_URL", "http://localhost:8000")

if not (AZURE_TENANT_ID and AZURE_CLIENT_ID and AZURE_CLIENT_SECRET):
    raise RuntimeError(
        "AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET must all be set. "
        "See .env.example."
    )


def _normalize_scopes() -> tuple[list[str], list[str]]:
    """Split AZURE_API_SCOPE / AZURE_GRAPH_SCOPES into the two buckets
    AzureProvider expects:

      - required_scopes:             unprefixed custom API scopes (e.g. "access_as_user")
      - additional_authorize_scopes: Graph / OIDC scopes passed through verbatim

    Tolerates a legacy convention where AZURE_API_SCOPE was a single
    comma-joined list mixing an already-URI-prefixed API scope with Graph
    scopes, so an existing `.env` won't silently produce tokens that can
    never validate.
    """
    api_prefix = f"api://{AZURE_CLIENT_ID}/"
    required: list[str] = []
    graph: list[str] = [s.strip() for s in AZURE_GRAPH_SCOPES_RAW.split(",") if s.strip()]

    for raw in AZURE_API_SCOPE_RAW.split(","):
        scope = raw.strip()
        if not scope:
            continue
        if scope.startswith("https://graph.microsoft.com/"):
            graph.append(scope)
        elif scope.startswith(api_prefix):
            required.append(scope[len(api_prefix):])
        elif "://" in scope or "/" in scope:
            graph.append(scope)
        else:
            required.append(scope)

    if not required:
        raise RuntimeError(
            "AZURE_API_SCOPE must include at least one custom API scope name "
            "(unprefixed, e.g. 'access_as_user')."
        )
    return required, graph


REQUIRED_SCOPES, GRAPH_SCOPES = _normalize_scopes()


# === Build the Azure auth provider ===
#
# AzureProvider is a subclass of OAuthProxy pre-wired for Microsoft Entra:
#   - Builds the authorize / token endpoints from the tenant ID
#   - Builds a JWTVerifier against the tenant's JWKS (issuer + audience)
#   - Auto-prefixes unprefixed scopes with `api://<client_id>/`
#   - Handles Azure-v2 quirks (strips the `resource` param, adds
#     `prompt=select_account`, respects AADSTS28000 "one resource per request"
#     during token exchange / refresh)
#   - Automatically includes `offline_access` to get refresh tokens
#
# `required_scopes` must be UNPREFIXED, non-OIDC scope names (e.g.
# "access_as_user"). AzureProvider prefixes them for the upstream authorize
# request and validates the short form in the token's `scp` claim.
#
# OIDC scopes (openid, profile, email) go into `additional_authorize_scopes`:
# they're requested from Azure but not advertised to MCP clients and not
# validated on tokens (Azure doesn't include them in `scp`).

auth = AzureProvider(
    client_id=AZURE_CLIENT_ID,
    client_secret=AZURE_CLIENT_SECRET,
    tenant_id=AZURE_TENANT_ID,
    required_scopes=REQUIRED_SCOPES,
    additional_authorize_scopes=["openid", "profile", "email", *GRAPH_SCOPES],
    base_url=SERVER_BASE_URL,
)
logger.info(
    "Azure OAuth (confidential client) enabled (tenant: %s, required: %s, graph: %s)",
    AZURE_TENANT_ID, REQUIRED_SCOPES, GRAPH_SCOPES or "(none)",
)


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
