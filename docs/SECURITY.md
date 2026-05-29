# Security

## Token Storage

OAuth access tokens are encrypted at rest using **AES-256-GCM**. The encryption key is derived from the `ENCRYPTION_KEY` environment variable (base64-encoded 32-byte key). The key is never stored in code, configuration files, or the database.

- `ENCRYPTION_KEY` is read from environment only
- Nonce is randomly generated per encryption (12 bytes)
- Ciphertext stored as base64 in `user_tokens.encrypted_token`
- Generate a key: `python -c "import secrets; import base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"`

## OAuth Flow

1. User clicks "Connect GitHub" → backend generates a CSRF `state` parameter
2. Browser redirects to `github.com/login/oauth/authorize` with `client_id`, `redirect_uri`, `scope`, `state`
3. GitHub redirects back with `code` and `state`
4. Backend validates `state` against session-stored value
5. Backend exchanges `code` for an access token
6. Token is encrypted and stored; JWT session cookie is issued

### Requested Scopes

| Scope | Why |
|---|---|
| `repo:status` | Read PR metadata (title, author, state) |
| `pull_requests:read` | Read PR diffs for analysis |

We do NOT request: `repo` (write access), `user:email`, `admin:*`, or any write scopes beyond posting review comments (which uses the user's token stored in the session).

## Session Management

- JWT tokens signed with **HS256** using `JWT_SECRET` environment variable
- Session duration: 24 hours (configurable via `SESSION_DURATION_HOURS`)
- Cookies set with `httpOnly`, `SameSite=Lax`, and `Secure` (in production)
- Logout revokes the GitHub token via `DELETE /applications/{client_id}/token` and clears the session cookie

## AI Provider Keys

User-provided AI API keys are encrypted with the same AES-256-GCM scheme before storage. Keys are only decrypted in-memory when making API calls to the chosen provider. They are never logged or exposed in API responses.

## Rate Limiting

- **GitHub API**: PRLens respects GitHub's rate limits. Authenticated requests get 5,000/hour. Unauthenticated gets 60/hour.
- **LLM providers**: Each provider has its own rate limits. PRLens retries with exponential backoff on 429 responses.

## Reporting Vulnerabilities

Email [security@your-domain.com] or open a GitHub Security Advisory on the repository.

## Deployment Checklist

- [ ] Set `JWT_SECRET` to a random 64-character string
- [ ] Set `ENCRYPTION_KEY` to a base64-encoded 32-byte random key
- [ ] Ensure `APP_BASE_URL` uses `https://` in production
- [ ] Set `Secure` cookie flag (enabled by default when APP_BASE_URL is HTTPS)
- [ ] Restrict `FRONTEND_URL` to your actual frontend domain
- [ ] Use a dedicated PostgreSQL user with minimal permissions
- [ ] Never commit `.env` to version control
