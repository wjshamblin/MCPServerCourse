# Step 11: Directory Server with Azure AD On-Behalf-Of (OBO)

First lesson where auth *does something substantive*. Instead of a
hello-world shape, this server looks up real people in Microsoft Graph
— **as the signed-in user**, not as the app. That's the
On-Behalf-Of (OBO) flow.

## Why OBO?

The naive alternative is to call Graph with the **app's own
credentials**. That works, but it means the server can access any
directory data the app has been granted, regardless of who's actually
calling. With OBO, the server exchanges the *user's* MCP access token
for a *Graph-audience* token, then calls Graph with it. Graph sees
requests as the user, so:

- **Audit trails point at real users**, not a shared service account.
- **Least privilege survives the hop**: the user can only see what
  their delegated permissions allow, even though the server is doing
  the work.
- **No admin-consented application permissions required** — delegated
  permissions are sufficient.

## The OBO token dance

```
User → MCP Client → Directory Server → Azure AD /token (OBO) → Microsoft Graph
                        │
                  User's MCP token                  Graph-audience token
                  (api://…/access_as_user)          (User.Read.All, …)
```

1. User authenticates, gets an MCP token with `access_as_user` **plus
   the Graph scopes** pre-consented via `additional_authorize_scopes`.
2. Directory server receives the MCP token in `Authorization: Bearer …`.
3. `EntraOBOToken([...])` (via `azure.identity.aio.OnBehalfOfCredential`)
   exchanges it for a Graph-audience token.
4. Server calls Graph API with the Graph token.

## What's on this branch

```
.
├── server.py              # AzureProvider + EntraOBOToken wiring
├── ms_graph_client.py     # thin httpx wrapper around Graph
├── directory_service.py   # coordinator that calls Graph with the OBO token
├── models.py              # pydantic types for Graph results
├── .env.example
├── docs/
│   ├── azure-setup-step09.md   # confidential client (prereq)
│   ├── azure-setup-step10.md   # public client (step 10 variant)
│   └── azure-setup-step11.md   # OBO-specific app setup (this step)
└── README.md
```

Three helper modules and a server. The server stays small — Graph
client and directory coordinator are split out because they're
naturally testable in isolation.

## Why confidential client here?

Step 10 moved the auth demo to a public client. **OBO cannot run on a
public client** — the token exchange requires the server to prove its
identity with a client secret. So step 11 backs off to a confidential
client. Step 10's security add-ons (allowlist, audit log) still apply
in principle, but this branch keeps the focus on OBO and leaves them
out.

## The key FastMCP piece: `EntraOBOToken`

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

`EntraOBOToken([...])` is a FastMCP **dependency** used as a parameter
default. Per request, FastMCP calls it, which triggers the OBO
exchange and injects the resulting Graph token into the tool. Token
caching is done by `azure.identity.aio.OnBehalfOfCredential` — keyed
by user assertion + scopes, so repeated calls in the same session
don't re-exchange.

### Invariants worth knowing

- Every scope passed to `EntraOBOToken([...])` **must** also appear in
  `additional_authorize_scopes`. Azure only lets you OBO-exchange for
  scopes the user has already consented to.
- Graph scopes must be fully qualified URIs (not short names).
- `offline_access` is added automatically by `AzureProvider`, so
  refresh tokens are available without extra config.

## Setting it up

1. **Register the Azure app** — follow
   [`docs/azure-setup-step11.md`](docs/azure-setup-step11.md). Critical
   bits: confidential client (Web platform + secret), `access_as_user`
   scope, **Delegated** Graph permissions (`User.Read.All`,
   `Directory.Read.All`), and **admin consent granted** — without it,
   OBO fails with `AADSTS65001`.
2. **Copy `.env.example` → `.env`** and fill in the tenant, client ID,
   client secret, and Graph scopes.
3. **Run:**
   ```bash
   uv sync
   python server.py
   ```
4. **Connect an MCP client.** Ask it to find a user — Graph sees the
   call as you, and the result respects your directory permissions.

## Docs reference

| Topic | Link |
|---|---|
| FastMCP × Azure OBO guide | [gofastmcp.com/integrations/azure#on-behalf-of-obo](https://gofastmcp.com/integrations/azure#on-behalf-of-obo) |
| `AzureProvider` | [gofastmcp.com/servers/auth/providers/azure](https://gofastmcp.com/servers/auth/providers/azure) |
| Azure OBO specification | [learn.microsoft.com/entra/identity-platform/v2-oauth2-on-behalf-of-flow](https://learn.microsoft.com/entra/identity-platform/v2-oauth2-on-behalf-of-flow) |
| Microsoft Graph — Users | [learn.microsoft.com/graph/api/user-list](https://learn.microsoft.com/graph/api/user-list) |
| `azure.identity` OnBehalfOfCredential | [learn.microsoft.com/python/api/azure-identity/azure.identity.onbehalfofcredential](https://learn.microsoft.com/python/api/azure-identity/azure.identity.onbehalfofcredential) |
