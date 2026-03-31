# Duke OIDC Authentication Setup

This guide walks through registering a Duke OAuth application and configuring it for your MCP server.

## Duke OIDC vs Azure AD

Duke provides its own OIDC identity provider at `oauth.oit.duke.edu`. This is **separate from Azure AD/Entra ID**:

| | Duke OIDC | Azure AD |
|-|-----------|----------|
| Provider | Duke OIT | Microsoft |
| Registration | authentication.oit.duke.edu | portal.azure.com |
| Auth UI | Duke Shibboleth login | Microsoft login |
| User identity | NetID, DukeID | UPN, Object ID |
| Scopes | openid, email, profile, groups | Custom API scopes |
| Token format | OAuth 2.0 / OIDC | OAuth 2.0 / OIDC |
| Introspection | Required for scope validation | Not needed (JWT claims) |

## Prerequisites

- A Duke NetID
- A [support group](https://duke.service-now.com/kb_view.do?sysparm_article=KB0027623) established in ServiceNow

## Step 1: Register Your OAuth Application

1. Go to [Duke Authentication Manager](https://authentication.oit.duke.edu/manager/oauth/register)
2. Log in with your Duke credentials
3. Fill in the registration form:
   - **Application Name**: "MCP Financial Server" (or your name)
   - **Redirect URI**: `http://localhost:8000/auth/callback`
   - **Scopes**: Select `openid`, `email`, `profile`, `offline_access`
   - **Grant Type**: Authorization Code
   - **Enable Introspection**: Yes (required for this setup)
4. Submit the registration

You will receive:
- **Client ID** — your `OIDC_CLIENT_ID`
- **Client Secret** — your `OIDC_CLIENT_SECRET`

## Step 2: Configure Your .env

```env
OIDC_CLIENT_ID=<your client ID>
OIDC_CLIENT_SECRET=<your client secret>
OIDC_SCOPES=openid email profile offline_access
BASE_URL=http://localhost:8000
```

## Step 3: Run the Server

```bash
python financial_server.py
```

The server starts with Duke OIDC authentication enabled. When an MCP client connects, the user will be redirected to Duke's Shibboleth login page.

## Duke OIDC Endpoints

All endpoints are discoverable via the well-known URL:

| Endpoint | URL |
|----------|-----|
| OIDC Discovery | `https://oauth.oit.duke.edu/oidc/.well-known/openid-configuration` |
| Authorization | `https://oauth.oit.duke.edu/oidc/authorize` |
| Token | `https://oauth.oit.duke.edu/oidc/token` |
| Introspection | `https://oauth.oit.duke.edu/oidc/introspect` |
| UserInfo | `https://oauth.oit.duke.edu/oidc/userinfo` |
| Logout | `https://oauth.oit.duke.edu/oidc/logout.jsp` |

## Duke OIDC Scopes

| Scope | Claims Provided |
|-------|----------------|
| `openid` | `sub` (eduPersonPrincipalName), `dukeNetID`, `dukeUniqueID` |
| `profile` | `dukePrimaryAffiliation`, `name`, `given_name`, `family_name` |
| `email` | `email` |
| `groups` | Group memberships from Duke Group Manager |
| `offline_access` | Enables refresh tokens for long-lived sessions |

## Why Token Introspection?

Duke OIDC tokens don't include scope claims in the JWT payload. This means standard JWT validation (checking the `scope` claim in the token) won't work for scope verification.

The solution is **Token Introspection** ([RFC 7662](https://tools.ietf.org/html/rfc7662)):
1. Server receives a token from the client
2. Server calls Duke's introspection endpoint with the token
3. Duke returns the full token metadata including scopes
4. Server verifies the token is active and has required scopes

This is implemented via a custom `IntrospectionTokenVerifier` class that extends FastMCP's `TokenVerifier`.

## Production Deployment

For production:
- Update **Redirect URI** to your production URL: `https://your-domain.com/auth/callback`
- Update `BASE_URL` in `.env` to match
- Ensure `STORAGE_DIR` points to a persistent volume
- The encrypted token storage allows sessions to survive server restarts
