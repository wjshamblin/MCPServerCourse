# Azure App Registration: OBO Flow (Step 10)

The On-Behalf-Of (OBO) flow lets the directory server exchange the user's MCP token for a Microsoft Graph token, so Graph calls run under the user's identity rather than the app's.

> **Upstream reference:** [FastMCP — Azure On-Behalf-Of (OBO) guide](https://gofastmcp.com/integrations/azure#on-behalf-of-obo). This step uses `AzureProvider` + the `EntraOBOToken` dependency exactly as described there — no hand-rolled token exchange.

## Why OBO?

Some organizations restrict application-level Graph API permissions. OBO lets the server call Graph **as the user**, using their delegated permissions. This provides:

- Per-user audit trails (Graph logs show the actual user, not a service account)
- Granular access control (users only see what they're permitted to see)
- No need for admin-consented *application* permissions — delegated permissions are enough

## Architecture

```
User -> MCP Client -> Directory Server -> Azure AD (OBO) -> Microsoft Graph
                           |
                      User's MCP token                  Graph API token
                      (api://<client_id>/access_as_user) (Graph scopes)
```

1. User authenticates, gets an MCP token with `api://<client-id>/access_as_user` scope and the Graph scopes pre-consented via `additional_authorize_scopes`
2. Directory server receives the MCP token in `Authorization: Bearer …`
3. `EntraOBOToken([...])` (via `azure.identity.aio.OnBehalfOfCredential`) exchanges it for a Graph-audience token
4. Server calls Graph API with the Graph token

## Step 1: Create the App Registration

1. Azure Portal > **App registrations** > **New registration**
2. Name: `MCP Directory Server`
3. Account type: Single tenant
4. Redirect URI: **Web** — `http://localhost:8000/auth/callback` (`AzureProvider`'s default redirect path)
5. Register

Copy the **Application (client) ID** and **Directory (tenant) ID**.

## Step 2: Create Client Secret

OBO requires a confidential client — you cannot run OBO with a public client.

1. **Certificates & secrets** > **New client secret**
2. Copy the Value — this is `AZURE_CLIENT_SECRET`

## Step 3: Expose an API

1. **Expose an API** > Set Application ID URI (accept default `api://<client-id>`)
2. **Add a scope**:
   - Name: `access_as_user`
   - Who can consent: Admins and users
   - Display name: "Access Directory as User"
   - State: Enabled

## Step 4: Request v2 Access Tokens

`AzureProvider` validates tokens against Azure's v2.0 issuer and JWKS. v1 tokens will fail validation.

1. Go to **Manifest**
2. Set `"requestedAccessTokenVersion": 2`
3. Save

## Step 5: Add Microsoft Graph Permissions

1. **API permissions** > **Add a permission** > **Microsoft Graph** > **Delegated permissions**
2. Add:
   - `User.Read.All` — Read all users' profiles
   - `Directory.Read.All` — Read directory data
3. Click **Grant admin consent for \[Your Organization]**

> **Why admin consent?** These permissions let the app read any user's profile. Individual users can't self-consent to that — an admin must approve it tenant-wide. Without admin consent, OBO token exchange fails with `AADSTS65001`.

> **Only delegated permissions.** Application permissions bypass user context entirely and are inappropriate for OBO.

## Step 6: Configure .env

```env
AZURE_CLIENT_ID=<Application (client) ID>
AZURE_CLIENT_SECRET=<Client secret Value>
AZURE_TENANT_ID=<Directory (tenant) ID>
AZURE_API_SCOPE=access_as_user
SERVER_BASE_URL=http://localhost:8000
AZURE_GRAPH_SCOPES=https://graph.microsoft.com/User.Read.All https://graph.microsoft.com/Directory.Read.All
```

## How OBO works in this codebase

`server.py` wires things like this (abridged):

```python
from fastmcp.server.auth.providers.azure import AzureProvider, EntraOBOToken

auth = AzureProvider(
    client_id=AZURE_CLIENT_ID,
    client_secret=AZURE_CLIENT_SECRET,
    tenant_id=AZURE_TENANT_ID,
    required_scopes=["access_as_user"],
    additional_authorize_scopes=[
        "openid", "profile", "email",
        "https://graph.microsoft.com/User.Read.All",
        "https://graph.microsoft.com/Directory.Read.All",
    ],
    base_url=SERVER_BASE_URL,
)

@mcp.tool
async def find_user(
    query: str,
    graph_token: str = EntraOBOToken(["https://graph.microsoft.com/User.Read.All"]),
) -> str:
    ...
```

Key invariants:
- Every scope passed to `EntraOBOToken([...])` must also appear in `additional_authorize_scopes` (Azure only lets you OBO-exchange for scopes the user has already consented to).
- `EntraOBOToken` uses `azure.identity.aio.OnBehalfOfCredential` under the hood, which caches exchanged tokens keyed by user assertion + scopes — no custom cache needed.
- `offline_access` is added automatically by `AzureProvider`, so refresh tokens are available.

## The OBO Token Exchange (what FastMCP is doing for you)

```
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token

grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer
client_id=<client-id>
client_secret=<client-secret>
assertion=<user's MCP token>
scope=https://graph.microsoft.com/User.Read.All
requested_token_use=on_behalf_of
```

The response contains an `access_token` for Microsoft Graph with the user's identity embedded, which is what gets injected into the `graph_token` parameter of each tool.
