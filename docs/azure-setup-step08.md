# Azure App Registration: Confidential Client (Step 08)

This guide walks through creating an Azure AD app registration for the financial MCP server.

## Prerequisites

- An Azure AD tenant (organization account)
- Permission to register applications (or an admin who can do it)

## Step 1: Register the Application

1. Go to [Azure Portal](https://portal.azure.com) > **Azure Active Directory** > **App registrations**
2. Click **New registration**
3. Configure:
   - **Name**: `MCP Financial Server` (or any descriptive name)
   - **Supported account types**: "Accounts in this organizational directory only" (Single tenant)
   - **Redirect URI**: Select **Web**, enter `http://localhost:8000/auth/callback` (this is `AzureProvider`'s default redirect path)
4. Click **Register**
5. Copy the **Application (client) ID** — this is your `AZURE_CLIENT_ID`
6. Copy the **Directory (tenant) ID** — this is your `AZURE_TENANT_ID`

## Step 2: Create a Client Secret

1. In your app registration, go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description (e.g., "MCP Server Dev") and expiration
4. Click **Add**
5. **Copy the Value immediately** — it won't be shown again. This is your `AZURE_CLIENT_SECRET`

## Step 3: Expose an API (Custom Scope)

This creates the custom scope that MCP clients will request during authentication.

1. Go to **Expose an API**
2. Click **Set** next to "Application ID URI" — accept the default `api://<client-id>`
3. Click **Add a scope**:
   - **Scope name**: `access_as_user`
   - **Who can consent**: Admins and users
   - **Admin consent display name**: "Access Financial Data as User"
   - **Admin consent description**: "Allows the MCP client to access university financial data on behalf of the signed-in user"
   - **User consent display name**: "Access Financial Data"
   - **User consent description**: "Access university financial data on your behalf"
   - **State**: Enabled
4. Click **Add scope**

The full scope URI will be: `api://<client-id>/access_as_user`

## Step 4: Configure API Permissions

1. Go to **API permissions**
2. The default `Microsoft Graph > User.Read` permission is sufficient for this step
3. No admin consent is needed for basic permissions

## Step 5: Configure .env

```env
AZURE_CLIENT_ID=<Application (client) ID from Step 1>
AZURE_CLIENT_SECRET=<Client secret Value from Step 2>
AZURE_TENANT_ID=<Directory (tenant) ID from Step 1>
AZURE_API_SCOPE=access_as_user
SERVER_BASE_URL=http://localhost:8000
```

## What is a Confidential Client?

A **confidential client** has a client secret that is kept secure on the server. This is appropriate when:

- The server runs in a trusted environment (your server, not a user's browser)
- You can keep the client secret secure
- The server itself authenticates to Azure AD

The OAuth flow:
1. User is redirected to Azure AD login
2. User authenticates and consents to the `access_as_user` scope
3. Azure AD sends an authorization code to the redirect URI
4. **The server** exchanges the code for tokens using the client secret
5. The server issues its own JWT to the MCP client

The client secret proves the server's identity to Azure AD. This is more secure than a public client flow, but requires secret management.

## Redirect URI for Production

When deploying, update:
- **Redirect URI** in Azure Portal to your production URL: `https://your-domain.com/auth/callback`
- `SERVER_BASE_URL` in `.env` to match
