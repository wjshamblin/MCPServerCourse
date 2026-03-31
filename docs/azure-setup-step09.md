# Azure App Registration: OBO Flow (Step 10)

The On-Behalf-Of (OBO) flow requires a **second** Azure app registration for the directory server. This server exchanges the user's MCP token for a Microsoft Graph token.

## Why OBO?

Some organizations restrict application-level Graph API permissions. OBO lets the server call Graph **as the user**, using their delegated permissions. This provides:

- Per-user audit trails (Graph logs show the actual user, not a service account)
- Granular access control (users only see what they're permitted to see)
- No need for admin-consented application permissions

## Architecture

```
User -> MCP Client -> Directory Server -> Azure AD (OBO) -> Microsoft Graph
                           |
                      User's MCP token                  Graph API token
                      (custom scope)                    (Graph scopes)
```

1. User authenticates, gets MCP token with `api://<client-id>/access_as_user` scope
2. Directory server receives the MCP token
3. Server exchanges it for a Graph token via OBO grant
4. Server calls Graph API with the Graph token

## Step 1: Create the Directory App Registration

1. Azure Portal > **App registrations** > **New registration**
2. Name: `MCP Directory Server`
3. Account type: Single tenant
4. Redirect URI: Web — `http://localhost:8001/mcp/oauth/callback`
5. Register

Copy the **Client ID** and **Tenant ID**.

## Step 2: Create Client Secret

1. **Certificates & secrets** > **New client secret**
2. Copy the Value — this is `DIR_AZURE_CLIENT_SECRET`

## Step 3: Expose an API

1. **Expose an API** > Set Application ID URI (`api://<client-id>`)
2. **Add a scope**:
   - Name: `access_as_user`
   - Who can consent: Admins and users
   - Display name: "Access Directory as User"
   - State: Enabled

## Step 4: Add Microsoft Graph Permissions

1. **API permissions** > **Add a permission** > **Microsoft Graph** > **Delegated permissions**
2. Add:
   - `User.Read.All` — Read all users' profiles
   - `Directory.Read.All` — Read directory data
3. Click **Grant admin consent** (requires admin role)

**Why admin consent?** These permissions let the app read ANY user's profile in the directory. Individual users can't consent to this — an admin must approve it for the organization.

## Step 5: Configure knownClientApplications (Optional)

If the financial server and directory server share a client, configure consent propagation:

1. In the directory app's **Manifest** editor
2. Find `"knownClientApplications": []`
3. Add the financial server's client ID:
   ```json
   "knownClientApplications": ["<financial-server-client-id>"]
   ```
4. Save

This lets users consent to both apps' scopes in a single prompt.

## Step 6: Configure .env

```env
# Directory Server (OBO)
DIR_AZURE_CLIENT_ID=<Directory app client ID>
DIR_AZURE_CLIENT_SECRET=<Directory app client secret>
DIR_AZURE_TENANT_ID=<Tenant ID>
DIR_MCP_API_SCOPE=access_as_user
DIR_OAUTH_BASE_URL=http://localhost:8001
DIR_SERVER_PORT=8001
DIR_GRAPH_SCOPES=https://graph.microsoft.com/User.Read.All https://graph.microsoft.com/Directory.Read.All
```

## The OBO Token Exchange (Detailed)

```
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token

grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer
client_id=<directory-app-client-id>
client_secret=<directory-app-secret>
assertion=<user's MCP token>
scope=https://graph.microsoft.com/User.Read.All https://graph.microsoft.com/Directory.Read.All
requested_token_use=on_behalf_of
```

The response contains an `access_token` scoped for Microsoft Graph, with the user's identity embedded. This token can then be used to call Graph endpoints.

## Token Caching

The server caches Graph tokens with TTL (default 50 minutes):
- **Key**: SHA-256 hash of the user's MCP token (first 32 chars)
- **Value**: Graph token + timestamp + expiration
- **Eviction**: LRU when cache exceeds 500 entries
- **Expiry**: Checked on every access (both TTL and token expiration)

This avoids redundant OBO exchanges for the same user session.
