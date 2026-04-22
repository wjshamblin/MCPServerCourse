"""
Step 08: Minimal Duke OIDC Auth Demo

The smallest possible MCP server gated by Duke's OIDC provider. Strip away
everything except the auth wiring so the OIDC mechanics stay the focus.

Demonstrates:
  - Wiring an `OIDCProxy` onto a `FastMCP` server (`auth=...`)
  - A custom `IntrospectionTokenVerifier` (Duke's access tokens are opaque,
    so the stock JWTVerifier can't read scopes; we hit the introspection
    endpoint instead — a pattern that applies to many OIDC providers)
  - Reading the authenticated user's identity inside a tool

Endpoints exposed at runtime:
  - /mcp                                          — the MCP endpoint (auth required)
  - /.well-known/oauth-authorization-server       — OAuth metadata
  - /.well-known/oauth-protected-resource         — resource server metadata
  - /authorize, /token, /register, /callback      — OAuth proxy endpoints

Run:  python server.py

Required env vars (see .env.example):
  OIDC_WELL_KNOWN_URL   default: Duke OIT discovery URL
  OIDC_CLIENT_ID        Duke OAuth client ID
  OIDC_CLIENT_SECRET    Duke OAuth client secret
  OIDC_SCOPES           default: "openid email profile offline_access"
  SERVER_BASE_URL       default: http://localhost:8000
"""

import logging
import os

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from fastmcp.server.dependencies import get_access_token

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


# === Config (env-driven, kept inline to make the demo self-contained) ===

OIDC_WELL_KNOWN_URL = os.environ.get(
    "OIDC_WELL_KNOWN_URL",
    "https://oauth.oit.duke.edu/oidc/.well-known/openid-configuration",
)
OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET", "")
OIDC_SCOPES = os.environ.get("OIDC_SCOPES", "openid email profile offline_access")
SERVER_BASE_URL = os.environ.get("SERVER_BASE_URL", "http://localhost:8000")

if not OIDC_CLIENT_ID or not OIDC_CLIENT_SECRET:
    raise RuntimeError(
        "OIDC_CLIENT_ID and OIDC_CLIENT_SECRET must be set. See .env.example."
    )


# === Custom token verifier ===

class IntrospectionTokenVerifier(TokenVerifier):
    """Verify opaque OIDC access tokens via RFC 7662 introspection.

    Duke's tokens don't embed scopes as JWT claims, so we POST the token
    back to the provider's /introspect endpoint and use its response as
    the source of truth for activeness, scopes, and identity claims.
    """

    def __init__(self, introspection_endpoint: str, client_id: str, client_secret: str):
        self.introspection_endpoint = introspection_endpoint
        self.client_id = client_id
        self.client_secret = client_secret
        self.required_scopes: list[str] = OIDC_SCOPES.split()

    async def verify_token(self, token: str) -> AccessToken | None:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.introspection_endpoint,
                data={"token": token},
                auth=(self.client_id, self.client_secret),
            )
        if resp.status_code != 200:
            logger.warning("Introspection failed: HTTP %s", resp.status_code)
            return None
        data = resp.json()
        if not data.get("active", False):
            return None
        identity_keys = (
            "sub", "client_id", "scope", "email", "name",
            "given_name", "family_name", "dukeNetID",
            "dukeUniqueID", "dukePrimaryAffiliation",
        )
        return AccessToken(
            token=token,
            client_id=data.get("client_id", "unknown"),
            scopes=(data.get("scope") or "").split(),
            claims={k: data.get(k) for k in identity_keys if data.get(k) is not None},
        )


# === Build the auth proxy (one-time discovery to find /introspect) ===

_oidc_metadata = httpx.get(OIDC_WELL_KNOWN_URL).json()

auth = OIDCProxy(
    config_url=OIDC_WELL_KNOWN_URL,
    client_id=OIDC_CLIENT_ID,
    client_secret=OIDC_CLIENT_SECRET,
    base_url=SERVER_BASE_URL,
    token_verifier=IntrospectionTokenVerifier(
        introspection_endpoint=_oidc_metadata["introspection_endpoint"],
        client_id=OIDC_CLIENT_ID,
        client_secret=OIDC_CLIENT_SECRET,
    ),
    extra_authorize_params={"scope": OIDC_SCOPES},
)
logger.info("Duke OIDC authentication enabled (provider: %s)", OIDC_WELL_KNOWN_URL)


# === MCP server ===

mcp = FastMCP(
    "DukeOIDCDemo",
    instructions=(
        "Minimal MCP server gated by Duke OIDC. Use whoami() to inspect "
        "the authenticated user's identity claims, or hello(name) for a "
        "trivial greeting that still requires authentication."
    ),
    auth=auth,
)


@mcp.tool
def hello(name: str = "world") -> str:
    """Return a friendly greeting. Every tool is gated by auth."""
    return f"hello, {name}!"


@mcp.tool
def whoami() -> dict:
    """Return identity claims for the user currently calling this tool."""
    tok = get_access_token()
    if tok is None:
        return {"error": "no access token in context"}
    return {"client_id": tok.client_id, "scopes": tok.scopes, "claims": tok.claims}


@mcp.resource("user://me")
def me() -> dict:
    """Identity claims as a resource (mirrors whoami())."""
    return whoami()


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
