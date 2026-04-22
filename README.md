# Step 08: Duke OIDC Authentication

The first auth lesson. Gate an MCP server behind Duke's OIDC provider
(`oauth.oit.duke.edu`). The server code is deliberately minimal —
`hello()`, `whoami()`, one resource — so the OIDC wiring is the only
new concept on the page.

## Why a fresh restart after step 07?

Auth is a significant concept on its own. Steps 08–10 each isolate
*one* auth flavor on top of a hello-world-shaped server:

| Step | Auth flavor |
|---|---|
| **08** (this step) | **Duke OIDC** (opaque tokens + introspection) |
| 09 | Azure / Entra confidential client (JWT tokens) |
| 10 | Azure public client + scope-based access control |

Steps 11 and 12 then come back to richer servers (directory data with
on-behalf-of delegation, and MCP Apps) to show how auth layers onto
real business logic.

## What's in this branch

```
.
├── server.py           # the entire demo
├── .env.example        # 5 env vars
├── docs/
│   └── duke-oidc-setup.md     # step-by-step Duke app registration
├── pyproject.toml      # fastmcp, uvicorn, httpx, python-dotenv
└── README.md
```

Four dependencies. No database, no audit, no composition.

## OIDC in 60 seconds

- **OpenID Connect** is an identity layer on top of OAuth 2.0.
- Every OIDC provider advertises its endpoints at a *discovery URL*:
  `<issuer>/.well-known/openid-configuration`.
- Standard endpoints: `authorize`, `token`, `userinfo`, `introspect`.
- Duke's discovery URL:
  `https://oauth.oit.duke.edu/oidc/.well-known/openid-configuration`

## Two FastMCP pieces

### 1. `OIDCProxy` — the auth backend

FastMCP ships an `OIDCProxy` that handles the standard OAuth dance —
authorize/token/register/callback — so the MCP client can be redirected
to Duke's login and come back with an access token.

```python
from fastmcp.server.auth.oidc_proxy import OIDCProxy

auth = OIDCProxy(
    config_url=OIDC_WELL_KNOWN_URL,
    client_id=OIDC_CLIENT_ID,
    client_secret=OIDC_CLIENT_SECRET,
    base_url=SERVER_BASE_URL,
    token_verifier=...,
    extra_authorize_params={"scope": OIDC_SCOPES},
)
```

### 2. A custom `IntrospectionTokenVerifier`

Duke's access tokens are **opaque** — not JWTs. The scopes and claims
live on Duke's server, not inside the token. FastMCP's stock
`JWTVerifier` can't read them. We subclass `TokenVerifier` and hit
Duke's `/introspect` endpoint (RFC 7662) to validate every request.

```python
class IntrospectionTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.introspection_endpoint,
                data={"token": token},
                auth=(self.client_id, self.client_secret),
            )
        data = resp.json()
        if not data.get("active", False):
            return None
        return AccessToken(
            token=token,
            client_id=data.get("client_id", "unknown"),
            scopes=(data.get("scope") or "").split(),
            claims={...},
        )
```

This pattern — subclass `TokenVerifier` and call the provider's
introspection endpoint — applies to **any** OIDC provider that issues
opaque tokens, not just Duke.

## Reading the authenticated user

Inside a tool, `get_access_token()` returns the verified
`AccessToken`. Its `claims` dict holds whatever identity fields Duke's
introspection response surfaced (netID, email, name, primary
affiliation, etc.).

```python
from fastmcp.server.dependencies import get_access_token

@mcp.tool
def whoami() -> dict:
    tok = get_access_token()
    return {"client_id": tok.client_id, "scopes": tok.scopes, "claims": tok.claims}
```

## Setting it up

1. **Register a Duke OAuth application** — follow
   [`docs/duke-oidc-setup.md`](docs/duke-oidc-setup.md). You'll need a
   Duke NetID and a ServiceNow support group.
2. **Copy `.env.example` to `.env`** and fill in `OIDC_CLIENT_ID` and
   `OIDC_CLIENT_SECRET` from the registration.
3. **Run:**
   ```bash
   uv sync
   python server.py
   ```
4. **Connect an MCP client.** When you call any tool, the client will
   open a browser to Duke's login page; after you authenticate,
   subsequent tool calls carry the access token.

## Docs reference

| Topic | Link |
|---|---|
| FastMCP auth overview | [gofastmcp.com/servers/auth](https://gofastmcp.com/servers/auth) |
| `OIDCProxy` | [gofastmcp.com/servers/auth/oidc-proxy](https://gofastmcp.com/servers/auth/oidc-proxy) |
| `TokenVerifier` | [gofastmcp.com/servers/auth/token-verification](https://gofastmcp.com/servers/auth/token-verification) |
| OAuth 2.0 Token Introspection (RFC 7662) | [rfc-editor.org/rfc/rfc7662](https://www.rfc-editor.org/rfc/rfc7662) |
| Duke Authentication Manager | [authentication.oit.duke.edu](https://authentication.oit.duke.edu) |
