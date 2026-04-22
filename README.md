# Step 09: Azure AD / Entra — Confidential Client

Second auth lesson. Same shape as step 08 (hello-world + whoami + one
resource), different identity provider: **Microsoft Entra ID** (Azure
AD), using the **confidential-client** OAuth flow — the server holds
a client secret and exchanges the auth code on the user's behalf.

## Why repeat the shape?

| Step | Auth flavor | Token format | Verification |
|---|---|---|---|
| 08 | Duke OIDC | Opaque | Introspection endpoint |
| **09** (this step) | **Azure confidential client** | **JWT** | **Local JWKS validation** |
| 10 | Azure public client + scope ACL | JWT | Local JWKS + scope checks |

Keeping server.py identical except for the auth block makes it obvious
where the differences live: inside FastMCP's provider class, not
scattered across the demo.

## The `AzureProvider` one-liner

```python
from fastmcp.server.auth.providers.azure import AzureProvider

auth = AzureProvider(
    client_id=AZURE_CLIENT_ID,
    client_secret=AZURE_CLIENT_SECRET,
    tenant_id=AZURE_TENANT_ID,
    required_scopes=["access_as_user"],
    additional_authorize_scopes=["openid", "profile", "email"],
    base_url=SERVER_BASE_URL,
)

mcp = FastMCP("AzureConfidentialDemo", auth=auth)
```

That's the whole auth integration. `AzureProvider` is a subclass of
`OAuthProxy` pre-wired for Entra:

- Builds the authorize / token endpoints from the tenant ID.
- Builds a `JWTVerifier` against the tenant's JWKS (issuer + audience).
- Auto-prefixes unprefixed scopes with `api://<client_id>/`.
- Handles Azure-v2 quirks (strips the `resource` param, adds
  `prompt=select_account`, obeys AADSTS28000 "one resource per request").
- Automatically includes `offline_access` so refresh tokens work.

## Opaque vs JWT — why Azure is different

Unlike Duke's opaque tokens (step 08), Azure issues **JWT access tokens**.
The server can validate them **locally** against the tenant's public
JWKS — no per-request round-trip to an introspection endpoint.

```
Duke (step 08):    token → POST /introspect → {active, scopes, claims}
Azure (this step): token → decode + verify JWT signature locally
```

The tradeoff: JWTs are valid until they expire (no revocation without
an extra check); opaque + introspection lets the provider revoke
immediately.

## Required scopes vs additional authorize scopes

```python
required_scopes=["access_as_user"],
additional_authorize_scopes=["openid", "profile", "email"],
```

- **`required_scopes`** (unprefixed custom API scopes) — these get
  auto-prefixed with `api://<client_id>/` for Azure, validated against
  the `scp` claim on every request, and advertised to MCP clients.
- **`additional_authorize_scopes`** — OIDC scopes (and optional Graph
  scopes) passed through verbatim in the authorize request. Requested
  from Azure but not validated on tokens — Azure doesn't include OIDC
  scopes in `scp`.

If you mix the two up, you get tokens that authenticate but never
validate. The `_normalize_scopes()` helper in `server.py` is defensive
against that common mistake.

## Setting it up

1. **Register an app in Azure Portal** — follow
   [`docs/azure-setup-step09.md`](docs/azure-setup-step09.md).
   You'll need an Entra tenant, a "Web" redirect URI at
   `http://localhost:8000/auth/callback`, a client secret, and a
   custom scope named `access_as_user`.
2. **Copy `.env.example` → `.env`** and fill in the tenant, client ID,
   client secret, and scope name.
3. **Run:**
   ```bash
   uv sync
   python server.py
   ```
4. **Connect an MCP client.** Calling any tool opens a Microsoft login
   page; the server completes the code exchange and issues a session.

## Docs reference

| Topic | Link |
|---|---|
| FastMCP × Azure guide | [gofastmcp.com/integrations/azure](https://gofastmcp.com/integrations/azure) |
| `AzureProvider` | [gofastmcp.com/servers/auth/providers/azure](https://gofastmcp.com/servers/auth/providers/azure) |
| `OAuthProxy` (base class) | [gofastmcp.com/servers/auth/oauth-proxy](https://gofastmcp.com/servers/auth/oauth-proxy) |
| Microsoft identity platform | [learn.microsoft.com/entra/identity-platform](https://learn.microsoft.com/entra/identity-platform) |
| Access token v2 format | [learn.microsoft.com/entra/identity-platform/access-tokens](https://learn.microsoft.com/entra/identity-platform/access-tokens) |
