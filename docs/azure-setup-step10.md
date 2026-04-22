# Azure App Registration: Public Client (Step 10)

This guide covers converting from a confidential client to a public client configuration.

> **Upstream reference:** [FastMCP — Azure (Microsoft Entra ID) OAuth integration guide](https://gofastmcp.com/integrations/azure#azure-microsoft-entra-id-oauth--fastmcp). `AzureProvider` supports both confidential and public clients: omit `client_secret` and supply `jwt_signing_key` to run as a public client with PKCE.

## What Changes from Step 09

| Setting | Confidential (Step 09) | Public (Step 10) |
|---------|------------------------|-------------------|
| Client Secret | Required | Not used |
| PKCE | Optional | Required (automatic) |
| Platform | Web | Mobile/Desktop |
| Security Model | Secret proves server identity | PKCE proves request origin |

## Why Public Clients?

Public clients are appropriate when:
- You cannot securely store a client secret (desktop apps, CLI tools, SPAs)
- You want to eliminate secret rotation overhead
- PKCE provides sufficient security for your use case

Public clients + PKCE are considered **more secure** than confidential clients for many deployment scenarios because there is no secret that can be leaked.

## Step 1: Enable Public Client Flows

1. In your app registration, go to **Authentication**
2. Under **Advanced settings**, set **Allow public client flows** to **Yes**
3. Click **Save**

## Step 2: Update Platform Configuration

1. Still in **Authentication**
2. Click **Add a platform** > **Mobile and desktop applications**
3. Add redirect URI: `http://localhost:8000/auth/callback` (this is `AzureProvider`'s default redirect path)
4. (Optional) Remove the **Web** platform if you only want public client flows

## Step 3: Remove Client Secret (Optional)

If you're switching entirely to public client:
1. Go to **Certificates & secrets**
2. Delete the client secret created in Step 09
3. Remove `AZURE_CLIENT_SECRET` from your `.env`

## Step 4: Update .env

```env
AZURE_CLIENT_ID=<same as before>
# AZURE_CLIENT_SECRET=  # Not needed for public client
AZURE_TENANT_ID=<same as before>
```

## Step 5: Add User Allowlist

With public client flow, anyone with a valid Azure AD account can authenticate. Add an allowlist to restrict access:

```env
ALLOWED_USERS=alice@university.edu,bob@university.edu
```

## PKCE (Proof Key for Code Exchange)

PKCE is automatically handled by `AzureProvider` (inherited from FastMCP's OAuth proxy). Here's how it works:

1. Client generates a random `code_verifier` (43-128 chars)
2. Client computes `code_challenge = BASE64URL(SHA256(code_verifier))`
3. Authorization request includes `code_challenge`
4. Token exchange includes `code_verifier`
5. Azure AD verifies that `SHA256(code_verifier) == code_challenge`

This prevents authorization code interception attacks because the attacker would need the `code_verifier` to exchange the code.

## When to Use Confidential vs Public

| Scenario | Recommendation |
|----------|---------------|
| Server-side app with secure storage | Confidential |
| Desktop/CLI application | Public + PKCE |
| Single-page app (browser) | Public + PKCE |
| Multi-tenant SaaS | Confidential |
| Development/testing | Either (public is simpler) |
