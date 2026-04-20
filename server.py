"""
Step 10: Directory MCP Server with Azure AD On-Behalf-Of (OBO) Flow

Builds on the auth pattern from steps 08/09 by introducing OBO: the
server takes the user's MCP access token and exchanges it — against
Azure's `/token` endpoint with the OBO grant — for a *new* token usable
against Microsoft Graph. We then call Graph with that token, so Graph
sees requests as the user, not the app.

Why OBO matters: the alternative — calling Graph with the app's own
client credentials — would let the server access *any* directory data
the app has been granted, regardless of who's actually calling. With OBO
the server can only see what the calling user can see, so audit and
least-privilege survive across the hop.

Reference:
  FastMCP Azure OBO guide:
  https://gofastmcp.com/integrations/azure#on-behalf-of-obo

Pieces on this branch:
  server.py             this file — AzureProvider + EntraOBOToken wiring
  ms_graph_client.py    thin httpx wrapper around Graph
  directory_service.py  business logic that calls Graph with the OBO token
  models.py             pydantic types

What changed vs. the hand-rolled implementation this step shipped with:
  - `AzureProvider` replaces hand-built `OAuthProxy` + `JWTVerifier`.
  - Graph scopes move into `additional_authorize_scopes` so they're
    requested during the initial OAuth consent (required for OBO to work).
  - `EntraOBOToken([...])` parameter default replaces the hand-rolled
    `OBOTokenExchange`/cache. Under the hood it uses
    `azure.identity.aio.OnBehalfOfCredential`, which has its own token
    cache shared across tool calls.

Run:  python server.py

Required env vars (see .env.example):
  AZURE_TENANT_ID       Your Azure AD tenant ID
  AZURE_CLIENT_ID       Application (client) ID — confidential client app
                        with Graph delegated permissions
                        (User.Read.All, Directory.Read.All) AND your own
                        api://<client_id>/access_as_user scope
  AZURE_CLIENT_SECRET   Client secret value (OBO requires a secret)
  AZURE_API_SCOPE       default: "access_as_user"  (unprefixed —
                        AzureProvider prepends `api://<client_id>/`)
  AZURE_GRAPH_SCOPES    space- or comma-separated, default:
                          "https://graph.microsoft.com/User.Read.All
                           https://graph.microsoft.com/Directory.Read.All"
  GRAPH_BASE_URL        default: "https://graph.microsoft.com/beta"
  SERVER_BASE_URL       default: http://localhost:8000
"""

import json
import logging
import os
import re

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.azure import AzureProvider, EntraOBOToken
from fastmcp.server.dependencies import get_access_token

from ms_graph_client import GraphClient
from directory_service import DirectoryService
from models import UserResult

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


# === Config (env-driven, inline) ===

AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
AZURE_API_SCOPE_RAW = os.environ.get("AZURE_API_SCOPE", "access_as_user")
SERVER_BASE_URL = os.environ.get("SERVER_BASE_URL", "http://localhost:8000")
AZURE_GRAPH_SCOPES_RAW = os.environ.get(
    "AZURE_GRAPH_SCOPES",
    "https://graph.microsoft.com/User.Read.All https://graph.microsoft.com/Directory.Read.All",
)
GRAPH_BASE_URL = os.environ.get("GRAPH_BASE_URL", "https://graph.microsoft.com/beta")

if not (AZURE_TENANT_ID and AZURE_CLIENT_ID and AZURE_CLIENT_SECRET):
    raise RuntimeError(
        "AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET must all be set. "
        "OBO requires a confidential client with a real secret. See .env.example."
    )

# AZURE_GRAPH_SCOPES can be space- or comma-separated.
GRAPH_SCOPES: list[str] = [s for s in re.split(r"[\s,]+", AZURE_GRAPH_SCOPES_RAW) if s]

# AzureProvider wants custom API scopes UNPREFIXED; tolerate legacy
# URI-prefixed/comma-joined values so an old `.env` still works.
def _normalize_required_scopes() -> list[str]:
    api_prefix = f"api://{AZURE_CLIENT_ID}/"
    scopes: list[str] = []
    for raw in re.split(r"[\s,]+", AZURE_API_SCOPE_RAW):
        s = raw.strip()
        if not s:
            continue
        if s.startswith(api_prefix):
            scopes.append(s[len(api_prefix):])
        elif "://" in s or "/" in s:
            continue
        else:
            scopes.append(s)
    if not scopes:
        raise RuntimeError(
            "AZURE_API_SCOPE must include at least one custom API scope name "
            "(unprefixed, e.g. 'access_as_user')."
        )
    return scopes


REQUIRED_SCOPES = _normalize_required_scopes()


# === Auth provider (AzureProvider — confidential client; OBO requires a secret) ===
#
# Graph scopes go into `additional_authorize_scopes` so they're included in
# the *initial* user consent. Azure only lets us perform OBO for scopes the
# user has already consented to. The scopes we later pass to
# `EntraOBOToken(...)` must be a SUBSET of these.
#
# See: https://gofastmcp.com/integrations/azure#on-behalf-of-obo

auth = AzureProvider(
    client_id=AZURE_CLIENT_ID,
    client_secret=AZURE_CLIENT_SECRET,
    tenant_id=AZURE_TENANT_ID,
    required_scopes=REQUIRED_SCOPES,
    additional_authorize_scopes=["openid", "profile", "email", *GRAPH_SCOPES],
    base_url=SERVER_BASE_URL,
)
logger.info(
    "Azure OAuth + OBO ready (tenant: %s, required: %s, graph: %s)",
    AZURE_TENANT_ID, REQUIRED_SCOPES, GRAPH_SCOPES,
)


# === Services ===
#
# No hand-rolled OBO exchange — EntraOBOToken handles it transparently.
# DirectoryService now receives an already-exchanged Graph token.

graph = GraphClient(base_url=GRAPH_BASE_URL)
directory = DirectoryService(graph=graph)


# === MCP server ===

mcp = FastMCP(
    "DirectoryService",
    instructions=(
        "University directory lookup service backed by Microsoft Graph. "
        "find_user(query) searches by name/email/NetID; get_user_groups(id) "
        "lists group memberships. Calls are made on behalf of the signed-in "
        "user via OBO, so Graph results respect that user's permissions."
    ),
    auth=auth,
)


@mcp.tool
async def find_user(
    query: str,
    graph_token: str = EntraOBOToken(GRAPH_SCOPES),
) -> str:
    """Search the university directory for a person.

    Args:
        query: Name, email, or NetID. Up to 10 matching results returned.
    """
    results = await directory.find_user(graph_token, query)
    users = [UserResult.from_graph(r).model_dump() for r in results]
    return json.dumps({"query": query, "count": len(users), "results": users}, indent=2)


@mcp.tool
async def get_user_groups(
    user_id: str,
    graph_token: str = EntraOBOToken(GRAPH_SCOPES),
) -> str:
    """Get group memberships for a user.

    Args:
        user_id: Azure AD object ID (from a find_user result).
    """
    groups = await directory.get_user_groups(graph_token, user_id)
    return json.dumps({
        "user_id": user_id,
        "count": len(groups),
        "groups": [{"id": g.get("id"), "name": g.get("displayName")} for g in groups],
    }, indent=2)


@mcp.tool
async def whoami() -> dict:
    """Identity claims for the user currently calling this tool."""
    tok = get_access_token()
    if tok is None:
        return {"error": "no access token in context"}
    interesting = ("oid", "upn", "preferred_username", "name", "tid", "scp")
    return {
        "client_id": tok.client_id,
        "scopes": tok.scopes,
        "claims": {k: tok.claims.get(k) for k in interesting if tok.claims.get(k) is not None},
    }


@mcp.resource("directory://auth/user", mime_type="application/json")
async def auth_user_resource() -> str:
    """Directory info for the currently authenticated user."""
    token = get_access_token()
    if not token:
        return json.dumps({"error": "Not authenticated"})
    claims = token.claims or {}
    return json.dumps({
        "email": claims.get("preferred_username") or claims.get("upn"),
        "name": claims.get("name"),
    })


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
