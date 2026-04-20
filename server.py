"""
Step 10: Directory MCP Server with Azure AD On-Behalf-Of (OBO) Flow

Builds on the public-client + security pattern from step 09 by introducing
OBO token exchange: the server takes the user's MCP access token and
exchanges it (against Azure AD's `/token` endpoint with the OBO grant)
for a *new* token usable against Microsoft Graph. We then make Graph
calls with that token, so Graph sees them as the user, not the app.

Why OBO matters: the alternative — calling Graph with the app's own
client credentials — would let the server access *any* directory data
the app is granted, regardless of who's actually calling. With OBO the
server can only see what the calling user can see, so audit and
least-privilege survive across the hop.

Pieces on this branch:
  server.py             this file — auth, OBO wiring, MCP tools
  token_exchange.py     OBOTokenExchange (cached upstream POST)
  ms_graph_client.py    thin httpx wrapper around Graph
  directory_service.py  business logic that ties OBO + Graph together
  models.py             pydantic types

Endpoints exposed at runtime are the same as step 09 plus the OBO
exchange happens internally on each tool call.

Run:  python server.py

Required env vars (see .env.example):
  AZURE_TENANT_ID       Your Azure AD tenant ID
  AZURE_CLIENT_ID       Application (client) ID — confidential client app
                        with Graph delegated permissions
                        (User.Read.All, Directory.Read.All) AND your own
                        api://<client_id>/access_as_user scope
  AZURE_CLIENT_SECRET   Client secret value (OBO requires a secret)
  AZURE_API_SCOPE       default: "access_as_user"
  GRAPH_SCOPES          space-separated, default:
                          "https://graph.microsoft.com/User.Read.All
                           https://graph.microsoft.com/Directory.Read.All"
  GRAPH_BASE_URL        default: "https://graph.microsoft.com/beta"
  SERVER_BASE_URL       default: http://localhost:8000
  OBO_TOKEN_CACHE_TTL   seconds, default 3000
"""

import json
import logging
import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token

from token_exchange import OBOTokenExchange, OBOExchangeError
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
AZURE_API_SCOPE = os.environ.get("AZURE_API_SCOPE", "access_as_user")
SERVER_BASE_URL = os.environ.get("SERVER_BASE_URL", "http://localhost:8000")
ADDITIONAL_SCOPES = [
    s.strip() for s in os.environ.get(
        "ADDITIONAL_AUTH_SCOPES", "email,openid,profile,offline_access"
    ).split(",") if s.strip()
]
GRAPH_SCOPES = os.environ.get(
    "GRAPH_SCOPES",
    "https://graph.microsoft.com/User.Read.All https://graph.microsoft.com/Directory.Read.All",
).split()
GRAPH_BASE_URL = os.environ.get("GRAPH_BASE_URL", "https://graph.microsoft.com/beta")
OBO_TOKEN_CACHE_TTL = int(os.environ.get("OBO_TOKEN_CACHE_TTL", "3000"))

if not (AZURE_TENANT_ID and AZURE_CLIENT_ID and AZURE_CLIENT_SECRET):
    raise RuntimeError(
        "AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET must all be set. "
        "OBO requires a confidential client. See .env.example."
    )

FULL_MCP_SCOPE = f"api://{AZURE_CLIENT_ID}/{AZURE_API_SCOPE}"
TOKEN_ENDPOINT = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"


# === Auth proxy (confidential client; OBO requires a real secret) ===

token_verifier = JWTVerifier(
    jwks_uri=f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/discovery/v2.0/keys",
    issuer=f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/v2.0",
    audience=AZURE_CLIENT_ID,
)

_all_scopes = [FULL_MCP_SCOPE] + ADDITIONAL_SCOPES

auth = OAuthProxy(
    upstream_authorization_endpoint=f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/authorize",
    upstream_token_endpoint=TOKEN_ENDPOINT,
    upstream_client_id=AZURE_CLIENT_ID,
    upstream_client_secret=AZURE_CLIENT_SECRET,
    valid_scopes=_all_scopes,
    extra_authorize_params={"scope": " ".join(_all_scopes)},
    token_verifier=token_verifier,
    base_url=SERVER_BASE_URL,
)
logger.info("Azure OAuth + OBO ready (tenant: %s)", AZURE_TENANT_ID)


# === Services ===

obo = OBOTokenExchange(
    client_id=AZURE_CLIENT_ID,
    client_secret=AZURE_CLIENT_SECRET,
    token_endpoint=TOKEN_ENDPOINT,
    graph_scopes=" ".join(GRAPH_SCOPES),
    cache_ttl=OBO_TOKEN_CACHE_TTL,
)
graph = GraphClient(base_url=GRAPH_BASE_URL)
directory = DirectoryService(obo=obo, graph=graph)


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
async def find_user(query: str) -> str:
    """Search the university directory for a person.

    Args:
        query: Name, email, or NetID. Up to 10 matching results returned.
    """
    token = get_access_token()
    if not token:
        return json.dumps({"error": "Not authenticated"})
    try:
        results = await directory.find_user(token.token, query)
    except OBOExchangeError as e:
        return json.dumps({"error": f"OBO exchange failed: {e}. Try re-authenticating."})
    users = [UserResult.from_graph(r).model_dump() for r in results]
    return json.dumps({"query": query, "count": len(users), "results": users}, indent=2)


@mcp.tool
async def get_user_groups(user_id: str) -> str:
    """Get group memberships for a user.

    Args:
        user_id: Azure AD object ID (from a find_user result).
    """
    token = get_access_token()
    if not token:
        return json.dumps({"error": "Not authenticated"})
    try:
        groups = await directory.get_user_groups(token.token, user_id)
    except OBOExchangeError as e:
        return json.dumps({"error": f"OBO exchange failed: {e}"})
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
