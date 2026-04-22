# Step 10: Azure Public Client + PKCE + Security Add-Ons

Third auth lesson. Same Azure Entra provider as step 09, but now we
treat the MCP server as a **public client** — no client secret, PKCE
instead — and add two production-leaning concerns on top:

1. **User allowlist** — only configured emails may call sensitive tools.
2. **Tamper-detected audit log** — every sensitive call is appended to a
   SHA-256 hash chain so any later tampering is detectable.

## What changes from step 09?

| Setting | Step 09 (confidential) | Step 10 (public) |
|---|---|---|
| `client_secret` | Required | **Not used** |
| PKCE | Optional | **Required (automatic)** |
| Azure platform | Web | **Mobile / desktop** |
| Security model | Secret proves server identity | PKCE proves request origin |
| `jwt_signing_key` | Derived from secret | **Must be supplied explicitly** |

The `server.py` is ~95% the same as step 09; only the `AzureProvider`
arguments and the security glue around `privileged_action()` change.

## Why public clients + PKCE?

Public clients are appropriate when you **cannot securely store a
client secret** — desktop apps, CLI tools, SPAs, mobile — or when you
want to eliminate secret rotation overhead. PKCE provides enough
security for most deployments, and is considered **more secure** than
confidential clients for many scenarios because there is no shared
secret that can leak.

FastMCP's `AzureProvider` handles PKCE automatically (inherited from
`OAuthProxy`): the client generates a random `code_verifier`, hashes
it into a `code_challenge`, Azure validates the pair at token
exchange. You don't write any of that code.

## Two security add-ons

### 1. User allowlist

A comma-separated env var, checked before the privileged tool runs:

```python
ALLOWED_USERS = [e.strip().lower() for e in os.environ.get("ALLOWED_USERS", "").split(",") if e.strip()]

def check_user_allowed(email: str) -> bool:
    return not ALLOWED_USERS or email in ALLOWED_USERS
```

With public-client flow, anyone with a valid Azure AD account can
authenticate. The allowlist is the second gate — the thing that turns
"this user is real" into "this user is authorized."

### 2. Hash-chained audit log (`audit.py`)

Every privileged call — allowed or denied — gets appended to a monthly
JSONL file. Each line stores the SHA-256 of the previous line, so any
later tampering (insertion, deletion, edit) breaks the chain and is
detectable at verify time.

```python
audit.log(actor=caller_email(), action="privileged_action", allowed=True, ...)
```

See `audit.py` for the implementation. The chain uses only `hashlib` —
no external dependencies.

## `jwt_signing_key` — new requirement

In confidential mode, FastMCP derives the signing key for its own
issued tokens from the Azure client secret. In public mode there's no
secret to derive from, so you must supply one explicitly:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Store the output in `.env` as `JWT_SIGNING_KEY=...`.

## Setting it up

1. **Either** re-register your step 09 app as a public client, **or**
   create a new one — follow
   [`docs/azure-setup-step10.md`](docs/azure-setup-step10.md). Key
   changes: enable "Allow public client flows", add a "Mobile and
   desktop applications" platform with redirect URI
   `http://localhost:8000/auth/callback`, (optionally) delete the
   client secret.
2. **Copy `.env.example` → `.env`** and fill in `AZURE_TENANT_ID`,
   `AZURE_CLIENT_ID`, `ALLOWED_USERS`, and `JWT_SIGNING_KEY`.
3. **Run:**
   ```bash
   uv sync
   python server.py
   ```
4. **Connect an MCP client.** Calling `privileged_action` as a user
   not on `ALLOWED_USERS` returns an error and writes a `denied` entry
   to the audit log.

## Docs reference

| Topic | Link |
|---|---|
| FastMCP × Azure guide | [gofastmcp.com/integrations/azure](https://gofastmcp.com/integrations/azure) |
| `AzureProvider` | [gofastmcp.com/servers/auth/providers/azure](https://gofastmcp.com/servers/auth/providers/azure) |
| OAuth 2.0 PKCE (RFC 7636) | [datatracker.ietf.org/doc/html/rfc7636](https://datatracker.ietf.org/doc/html/rfc7636) |
| Azure: public-client flows | [learn.microsoft.com/entra/identity-platform/msal-client-applications](https://learn.microsoft.com/entra/identity-platform/msal-client-applications) |
| Step 09 setup (prerequisite) | [`docs/azure-setup-step09.md`](docs/azure-setup-step09.md) |
