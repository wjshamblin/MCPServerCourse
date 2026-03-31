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
