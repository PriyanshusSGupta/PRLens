# External Integrations

**Analysis Date:** 2026-05-29

## APIs & External Services

### GitHub API (REST v3)

**Purpose:** Core integration — fetching PR data, PR diffs, posting review comments, listing user repos, installing webhooks.

**SDK/Client:** Custom `GitHubClient` class in `backend/app/integrations/github_client.py` using `httpx.AsyncClient`.

**Auth:**
- User OAuth tokens (scoped `repo:status,pull_requests:read`) — encrypted at rest via AES-256-GCM, decrypted in-memory at call time
- Token retrieved from `UserToken` model where `provider == "github"`
- Fallback: `github_private_key` for GitHub App installations (legacy)

**Endpoints used:**
| Endpoint | Purpose | File |
|---|---|---|
| `GET /repos/{owner}/{repo}/pulls/{number}` | Fetch PR metadata | `backend/app/integrations/github_client.py` |
| `GET /repos/{owner}/{repo}/pulls/{number}` (diff Accept header) | Fetch PR diff text | `backend/app/integrations/github_client.py` |
| `POST /repos/{owner}/{repo}/issues/{number}/comments` | Post review comment | `backend/app/integrations/github_client.py` |
| `GET /user/repos` | List authenticated user's repos | `backend/app/api/repos.py` |
| `POST /repos/{owner}/{repo}/hooks` | Install webhook | `backend/app/api/repos.py` |
| `DELETE /repos/{owner}/{repo}/hooks/{id}` | Uninstall webhook | `backend/app/api/repos.py` |
| `POST /login/oauth/access_token` | OAuth token exchange | `backend/app/api/auth.py` |
| `GET /user` | Get authenticated user profile | `backend/app/api/auth.py` |
| `GET /user/emails` | Get primary email | `backend/app/api/auth.py` |

**Rate Limits:** 5,000 requests/hour (authenticated), 60/hour (unauthenticated). Handled via `403` response detection in `fetch_pr_and_diff`.

### Google OAuth API

**Purpose:** Identity login provider (user authentication only).

**SDK/Client:** Direct `httpx.AsyncClient` calls in `backend/app/api/auth.py`.

**Auth:** OAuth 2.0 authorization code flow — `google_client_id` and `google_client_secret` from env.

**Endpoints used:**
| Endpoint | Purpose |
|---|---|
| `https://accounts.google.com/o/oauth2/v2/auth` | User authorization redirect |
| `https://oauth2.googleapis.com/token` | Token exchange |
| `https://www.googleapis.com/oauth2/v2/userinfo` | User profile fetch |

**Scopes:** `openid email profile`

### GitHub OAuth API (Identity)

**Purpose:** Identity login provider (separate from repo access OAuth).

**SDK/Client:** Direct `httpx.AsyncClient` calls in `backend/app/api/auth.py`.

**Auth:** OAuth 2.0 authorization code flow — same `github_client_id` / `github_client_secret` as repo connect, but `scope: user:email` only.

**Note:** This is a separate OAuth flow from the repo-scoped one (`/api/auth/github-connect/login`). The identity flow uses `scope: user:email`, while repo access uses `scope: repo:status,pull_requests:read`.

### LLM Providers (OpenAI-compatible)

**Purpose:** AI-powered code review analysis (optional, disabled by default via `ENABLE_LLM=false`).

**SDK/Client:** Custom `LLMClient` class in `backend/app/integrations/llm_client.py` using `httpx.AsyncClient`.

**Supported providers (defined in `backend/app/api/ai.py`, `PROVIDER_PRESETS`):**
| Provider | Default Model | Base URL |
|---|---|---|
| OpenAI | `gpt-4o` | `https://api.openai.com/v1` |
| Anthropic (Claude) | `claude-3-5-sonnet-latest` | `https://api.anthropic.com/v1` |
| Groq | `llama-3.3-70b-versatile` | `https://api.groq.com/openai/v1` |
| xAI (Grok) | `grok-2-latest` | `https://api.x.ai/v1` |
| DeepSeek | `deepseek-chat` | `https://api.deepseek.com/v1` |
| Moonshot (Kimi) | `moonshot-v1-8k` | `https://api.moonshot.cn/v1` |
| Google (Gemini) | `gemini-2.0-flash` | `https://generativelanguage.googleapis.com/v1beta/openai` |
| Custom | `gpt-4o` | User-defined |

**Auth:** API key stored per-user (encrypted via AES-256-GCM) OR global fallback via `LLM_API_KEY` env var.

**API Endpoint Called:** `POST /chat/completions` with `response_format: {"type": "json_object"}`. Retry with exponential backoff on 429/5xx (3 retries max). Timeout: 60 seconds.

**System Prompt:** In `backend/app/prompts/system.py` — instructs the LLM to analyze diffs for reliability, security, performance, maintainability, and testing issues.

## Data Storage

### Databases

**Primary: SQLite (dev) / PostgreSQL 16 (production)**

- **SQLite driver:** `aiosqlite>=0.22.0`
- **PostgreSQL driver:** `asyncpg>=0.30.0`
- **Connection:** `DATABASE_URL` env var — auto-detects protocol (sqlite:/// vs postgresql://)
- **Client:** SQLAlchemy async with `create_async_engine` (`backend/app/db/session.py`)
- **ORM:** `DeclarativeBase` with `async_sessionmaker`

**Connection auto-detection in `backend/app/db/session.py`:**
- `sqlite:///` → `sqlite+aiosqlite:///`
- `postgresql://` → `postgresql+asyncpg://`

**Default dev config:** `sqlite:///prlens.db` (file-based SQLite at project root)

**Models (in `backend/app/models/`):**
- `user.py` — Users (email, hashed password, OAuth provider IDs, avatar)
- `user_token.py` — Encrypted OAuth tokens per user
- `user_ai_config.py` — Per-user LLM provider config
- `otp_code.py` — One-time passwords for email verification
- `repository.py` — Installed repos (webhook ID, secret)
- `pull_request.py` — PR metadata (title, state, risk score)
- `review_run.py` — Analysis run per PR
- `finding.py` — Individual findings per review run
- `evaluation.py` — Evaluation run/task

**Migrations:** Alembic installed (`backend/alembic.ini` present) but not used — table creation via `Base.metadata.create_all` on startup in `backend/app/main.py`.

### File Storage
Local filesystem only — no external file storage service. Static frontend files served by nginx.

### Caching
**In-memory only** via `cachetools.TTLCache`:
- `OAUTH_STATES` — OAuth CSRF state tokens (10 min TTL, 10,000 max)
- `EXCHANGE_TOKENS` — OAuth session exchange tokens (1 min TTL, 1,000 max)
- No Redis, Memcached, or distributed cache

## Authentication & Identity

### Auth Provider: Multi-method

**Implementation location:** `backend/app/core/auth.py`, `backend/app/api/auth.py`

**Methods:**
| Method | Description |
|---|---|
| Email + OTP | Register with email/password, verify via 6-digit OTP | 
| Google OAuth | Identity login via Google (`openid email profile` scope) |
| GitHub OAuth | Identity login via GitHub (`user:email` scope) |
| GitHub OAuth (connect) | Separate flow for repo access (`repo:status,pull_requests:read` scope) |

**Session Management:**
- JWT (HS256) signed with `JWT_SECRET`
- Cookie-based: `prlens_session`, `httpOnly`, `SameSite=Lax`, `Secure` in production
- Duration: 24 hours (configurable via `SESSION_DURATION_HOURS`)
- Endpoint: `/api/auth/me` returns current user; `/api/auth/scopes` returns GitHub OAuth scopes

**Password hashing:** bcrypt via `passlib.context.CryptContext` (`backend/app/core/passwords.py`)

**Token encryption:** AES-256-GCM via `cryptography` library (`backend/app/core/crypto.py`), key from `ENCRYPTION_KEY` env var

**Rate limiting:** `slowapi` — 5 requests/minute on login/OTP endpoints, 200/minute global default

## Monitoring & Observability

**Error Tracking:** None detected — no Sentry, Datadog, or similar integration

**Logs:**
- Python `logging` module with `LOG_LEVEL` env var (default: `INFO`)
- Structured text logs to stdout
- Security logs for OTP delivery fallback (logs code when SMTP fails)
- No external log aggregation service

## CI/CD & Deployment

**Hosting:** Docker Compose deployment (targeted for self-hosted/VPS)

**CI Pipeline:** GitHub Actions (5 workflows):
| Workflow | File | Purpose |
|---|---|---|
| Commit Lint | `.github/workflows/commit-lint.yml` | Conventional commit validation |
| PR Coverage | `.github/workflows/pr-coverage.yml` | Test coverage reporting |
| PR Sonar | `.github/workflows/pr-sonar.yml` | Sonar quality gate |
| Stale Deps | `.github/workflows/stale-deps.yml` | Dependency freshness check |
| Triage | `.github/workflows/triage.yml` | Issue/PR triage |

**Docker Compose services (3):**
1. `db` — PostgreSQL 16-alpine with volume `pgdata`
2. `backend` — Python 3.11-slim, exposed on port 8000
3. `frontend` — Nginx serving built React app, exposed on port 3000

**Production reverse proxy:** Nginx in `infra/docker/nginx.conf` proxies `/api/` to backend, serves SPA for all other routes.

## Environment Configuration

**Required env vars** (no defaults, app fails to start without):
```
JWT_SECRET          # HS256 signing key (generate via scripts/generate-keys.sh)
ENCRYPTION_KEY      # AES-256-GCM base64 key (generate via scripts/generate-keys.sh)
```

**Required for OAuth login:**
```
GITHUB_CLIENT_ID
GITHUB_CLIENT_SECRET
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
```

**Required for email OTP (production):**
```
SMTP_HOST           # Set to smtp.resend.com for Resend, etc.
SMTP_USERNAME
SMTP_PASSWORD
```

**Optional:**
```
LLM_PROVIDER, LLM_API_KEY, LLM_MODEL, LLM_BASE_URL  # LLM review (disabled by default)
GITHUB_APP_ID, GITHUB_WEBHOOK_SECRET, GITHUB_PRIVATE_KEY  # Legacy GitHub App
DATABASE_URL         # Defaults to sqlite:///prlens.db
APP_BASE_URL         # Default: http://localhost:8000
FRONTEND_URL         # Default: http://localhost:5173
SESSION_DURATION_HOURS, LOG_LEVEL, SEVERITY_*, MIN_CONFIDENCE, MAX_DIFF_SIZE, ENABLE_*
```

**Secrets location:** Environment variables + `.env` file at project root (gitignored). Documentation at `.env.example`.

## Webhooks & Callbacks

### Incoming

**GitHub Webhook**
- **Endpoint:** `POST /api/webhooks/github`
- **Events handled:** `pull_request` (opened, synchronize, ready_for_review), `pull_request_review`
- **Signature verification:** HMAC-SHA256 via `X-Hub-Signature-256` header, compared with per-repo `webhook_secret`
- **Behavior:** On relevant event, fetches PR diff, runs analysis (rule-based + optional LLM), stores findings, posts review comment, calculates risk score
- **Per-repo secret:** Generated via `secrets.token_hex(32)` at install time, stored in `Repository.webhook_secret`

### Outgoing

**GitHub PR Comments**
- Posts review results as PR comments via `GitHubClient.post_pr_comment()` using the GitHub Issues API (`/repos/{owner}/{repo}/issues/{number}/comments`)
- Format: Markdown summary with emoji severity indicators, findings per file
- Silently fails on error (try/except pass)

**SMTP Email**
- OTP verification emails sent via SMTP
- Defaults to `console` mode (logs code to stdout)
- Production: SendGrid, Resend, or any SMTP provider
- Supports both STARTTLS (port 587) and implicit TLS (port 465)

---

*Integration audit: 2026-05-29*
