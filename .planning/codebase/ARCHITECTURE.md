# Architecture

**Analysis Date:** 2026-05-29

## Pattern Overview

**Overall:** Single-module FastAPI backend + SPA React frontend, connected via REST API

**Key Characteristics:**
- **Backend**: Monolithic FastAPI application with clear internal layering (api → integrations/engine → db/models)
- **Frontend**: Single-page React app with client-side routing, AuthProvider context for session management
- **Review pipeline**: Rule-based analyzers (plugin pattern via `BaseAnalyzer` ABC) + optional LLM analyzer, orchestrated by `run_review_on_diff()` in `backend/app/review_engine/__init__.py`
- **Database**: SQLAlchemy async with auto-detection of SQLite (dev) or PostgreSQL (prod), `create_all` on startup
- **Auth**: JWT session tokens stored in httpOnly cookies, with separate OAuth flows for identity (Google/GitHub) and repo access (GitHub scoped)
- **Scoring**: Simple severity-weighted risk score calculation in `backend/app/scoring/risk.py`

## Layers

### API Layer
- Purpose: HTTP route handlers, request validation, response formatting
- Location: `backend/app/api/`
- Contains: 8 router modules — `auth.py`, `repos.py`, `review.py`, `webhooks.py`, `prs.py`, `dashboard.py`, `evaluations.py`, `ai.py`
- Depends on: `core/` (auth, config, crypto), `db/session.py`, `models/`, `integrations/`, `review_engine/`, `scoring/`
- Used by: Frontend browser requests, GitHub webhooks

### Core Layer
- Purpose: Shared infrastructure — config, JWT auth, password hashing, encryption, email, webhook verification, review policy
- Location: `backend/app/core/`
- Contains: `config.py`, `auth.py`, `passwords.py`, `crypto.py`, `email.py`, `security.py`, `policy.py`
- Depends on: `config.py` (read by everything), standard library + pydantic-settings
- Used by: API layer, integrations, review engine

### Database Layer
- Purpose: Async SQLAlchemy engine and session management
- Location: `backend/app/db/`
- Contains: `base.py` (DeclarativeBase), `session.py` (engine factory, session generator for FastAPI Depends)
- Depends on: `core/config.py` for `database_url`
- Used by: All API route handlers, auth layer

### Model Layer
- Purpose: SQLAlchemy ORM models defining the database schema
- Location: `backend/app/models/`
- Contains: 8 models — `User`, `UserToken`, `UserAIConfig`, `OTPCode`, `Repository`, `PullRequest`, `ReviewRun`, `Finding`, `EvaluationRun`
- Depends on: `db/base.py`
- Used by: API layer, review engine, scoring

### Integration Layer
- Purpose: External service clients — GitHub API and LLM providers
- Location: `backend/app/integrations/`
- Contains: `github_client.py` (GitHubClient class), `llm_client.py` (LLMClient class)
- Depends on: `core/config.py`, `httpx`
- Used by: API layer (`review.py`, `repos.py`, `webhooks.py`), review engine (`LLMAnalyzer`)

### Review Engine Layer
- Purpose: PR diff parsing, rule-based analysis, LLM analysis, policy filtering
- Location: `backend/app/review_engine/`
- Sub-directories: `analyzers/`, `diff_parser.py`, `__init__.py` (orchestration)
- Contains: `diff_parser.py` (DiffFile/FileHunk dataclasses, `parse_diff()`), `analyzers/base.py` (BaseAnalyzer ABC), `analyzers/security.py`, `analyzers/reliability.py`, `analyzers/performance.py`, `analyzers/testing.py`, `analyzers/llm.py`
- Depends on: `core/config.py`, `integrations/llm_client.py`, `prompts/system.py`
- Used by: API layer (`review.py`, `webhooks.py`)

### Scoring Layer
- Purpose: Calculate aggregate risk score from findings
- Location: `backend/app/scoring/`
- Contains: `risk.py` — single function `calculate_risk_score(findings)`
- Used by: API layer (`review.py`, `webhooks.py`)

### Prompt Layer
- Purpose: LLM system prompts and prompt builders
- Location: `backend/app/prompts/`
- Contains: `system.py` — `REVIEW_SYSTEM_PROMPT` constant, `build_review_prompt()` function
- Used by: Review engine (`analyzers/llm.py`)

### Frontend Layer
- Purpose: User interface — login, dashboard, PR review, AI settings
- Location: `frontend/src/`
- Sub-layers: `pages/`, `components/`, `hooks/`, `lib/`
- Contains: 8 page components, 4 shared components, 3 hooks, 1 API client

## Data Flow

### Manual PR Review Flow
1. User enters `owner`/`repo`/`pr_number` in Dashboard form → POST `/api/review`
2. `review.py` handler creates `GitHubClient`, calls `fetch_pr_and_diff(owner, repo, pr_number)`
3. `run_review_on_diff()` in `review_engine/__init__.py` orchestrates analysis:
   - Parses diff text via `parse_diff()` into `DiffFile[]` with `FileHunk[]`
   - Runs each enabled rule-based analyzer (`SecurityAnalyzer`, `ReliabilityAnalyzer`, `PerformanceAnalyzer`, `TestingAnalyzer`) — each parses the diff independently
   - If LLM enabled and client has API key, runs `LLMAnalyzer` — chunks diff into 8000-char segments, calls `LLMClient.generate_structured()` per chunk, deduplicates results
   - Applies policy filter via `_apply_policy()` — filters by severity threshold and minimum confidence
4. `calculate_risk_score()` computes 0.0–1.0 score from severity-weighted + confidence-weighted findings
5. Results persisted to DB (PullRequest, ReviewRun, Finding rows) and returned as JSON

### Webhook-Triggered PR Review Flow
1. GitHub sends `pull_request` or `pull_request_review` event to POST `/api/webhooks/github`
2. `webhooks.py` handler:
   - Validates event type and action (only `opened`/`synchronize`/`ready_for_review`)
   - Looks up Repository by `full_name` in DB
   - Verifies HMAC-SHA256 signature using repo's `webhook_secret`
   - Creates or updates PullRequest row
   - Creates ReviewRun row with `status="in_progress"`
   - Fetches latest GitHub user token from DB, decrypts it, creates `GitHubClient`
   - Fetches PR diff via `fetch_pr_and_diff()`
   - Runs `run_review_on_diff()` and `calculate_risk_score()` (same pipeline as manual)
   - Persists findings, updates ReviewRun to `completed`
   - Attempts to post PR comment with findings summary via `GitHubClient.post_pr_comment()` (best-effort, errors silently caught)

### Auth Flows
- **Email+Password Registration**: POST `/api/auth/register` → creates User + generates OTP → POST `/api/auth/verify-otp` → sets `prlens_session` httpOnly cookie → JWT in cookie
- **Email+Password Login**: POST `/api/auth/login` → verifies password → sets cookie
- **Google OAuth**: GET `/api/auth/google/login` → redirects to Google → callback at `/api/auth/google/callback` → creates/updates User → redirects to frontend with exchange token → frontend calls POST `/api/auth/exchange` to set cookie
- **GitHub OAuth (identity)**: Same pattern as Google, but redirect returns `github_connect_needed=true` flag
- **GitHub OAuth (repo access)**: GET `/api/auth/github-connect/login` → scoped to `repo:status,pull_requests:read` → callback encrypts access token via AES-256-GCM → stores in `UserToken` row → redirects to `/repos`
- **Session check**: Every protected route uses `get_current_user` Depends → reads `prlens_session` cookie → decodes JWT → loads User from DB

### State Management
- **Backend**: Stateless — all state in database (SQLite file or PostgreSQL). Auth state via JWT in httpOnly cookies. OAuth state via in-memory `TTLCache` (`OAUTH_STATES`, `EXCHANGE_TOKENS`)
- **Frontend**: Minimal local state — `AuthProvider` context holds `user`, `loading`, `scopes`, `warnings`. Each page/component fetches data via `useEffect` + API calls. No client-side state manager (no Redux, no Zustand)

## Key Abstractions

### BaseAnalyzer (ABC)
- Purpose: Plugin interface for all rule-based and LLM analyzers
- Location: `backend/app/review_engine/analyzers/base.py`
- Pattern: Abstract base class with single async method `analyze(pr) -> list[dict]`
- Subclasses: `SecurityAnalyzer`, `ReliabilityAnalyzer`, `PerformanceAnalyzer`, `TestingAnalyzer`, `LLMAnalyzer`

### DiffFile / FileHunk (dataclasses)
- Purpose: Structured representation of parsed git diffs
- Location: `backend/app/review_engine/diff_parser.py`
- `DiffFile`: `file_path`, `status` (modified/deleted/new/binary/renamed), `hunks: list[FileHunk]`
- `FileHunk`: `file_path`, `start_line`, `end_line`, `content` (diff text)

### _PrContext
- Purpose: Lightweight protocol object passed to analyzers (provides `diff_text` and `title` attributes)
- Location: `backend/app/review_engine/__init__.py` (private class `_PrContext`)
- Pattern: Simple class with `__slots__`, avoids coupling analyzers to DB models

### LLMClient
- Purpose: OpenAI-compatible chat completion client with retry logic and JSON extraction
- Location: `backend/app/integrations/llm_client.py`
- Methods: `generate(system_prompt, user_prompt) -> str`, `generate_structured(system_prompt, user_prompt) -> list[dict]`

### GitHubClient
- Purpose: GitHub REST API wrapper — fetch PR data + diff, post PR comments
- Location: `backend/app/integrations/github_client.py`
- Methods: `fetch_pr_and_diff(owner, repo, pr_number) -> tuple[dict, str]`, `post_pr_comment(owner, repo, pr_number, findings) -> dict`

### Settings (Pydantic BaseSettings)
- Purpose: Centralized configuration from environment variables + `.env` file
- Location: `backend/app/core/config.py`
- Pattern: Single `Settings` class loaded once as module-level `settings` singleton
- Reads: `.env` file at project root, OS environment variables

### Policy (dataclass)
- Purpose: Runtime review policy — which analyzers are enabled, severity thresholds, confidence minimum
- Location: `backend/app/core/policy.py`
- Created by: `get_policy()` function that reads values from `settings`

### AuthProvider (React Context)
- Purpose: Auth state management for frontend — user, loading, scopes, login/logout
- Location: `frontend/src/hooks/useAuth.tsx`
- Pattern: React Context + Provider pattern with `useCallback` for stable references

## Entry Points

### Backend
- **FastAPI app**: `backend/app/main.py` — creates `FastAPI` instance with lifespan handler, registers middleware (CORS, security headers, rate limiting), includes all 8 routers, serves `/health` endpoint
- **Startup**: `lifespan` async context manager — calls `Base.metadata.create_all` on engine
- **Server**: `uvicorn app.main:app` via `uv run` (specified in `scripts/run-backend.sh`)

### Frontend
- **Entry point**: `frontend/src/main.tsx` — mounts React app in `BrowserRouter`
- **App shell**: `frontend/src/App.tsx` — defines route tree with `<Layout>` wrapper for authenticated routes
- **Vite dev server**: `frontend/vite.config.ts` — proxies `/api` to `localhost:8000`, serves on port 5173

## Error Handling

**Strategy:** HTTP exceptions via FastAPI's `HTTPException` — raised in route handlers and core/auth layer, caught by FastAPI middleware.

**Patterns:**
- `HTTPException(status_code=4xx, detail="message")` for all client errors (validation, auth, not found)
- `HTTPException(status_code=502, detail=...)` for upstream service failures (GitHub API, OAuth providers)
- External errors in `webhooks.py` caught and handled without crashing the webhook response
- `GitHubClient` methods raise specific Python exceptions (`ValueError` for 404, `RuntimeError` for 403/401)
- `LLMClient.generate()` has retry logic (3 attempts with exponential backoff) for transient failures
- `post_pr_comment()` failures silently caught in webhook handler (best-effort)
- Rate limiting via `slowapi` — `200/minute` global default, `5/minute` on auth endpoints

## Cross-Cutting Concerns

**Logging:** Python `logging` module via `logging.getLogger(__name__)` — level from `settings.log_level`. SMTP failures fall back to console logging. OTP codes logged to console in dev.

**Validation:** Pydantic `BaseModel` for request bodies with `@field_validator` decorators. Pydantic's native type validation (EmailStr, URLs). GitHub naming validated via regex in `ReviewRequest`. Custom base_url validated against private/internal IPs in `SetAIConfigBody`.

**Authentication:** JWT session tokens in httpOnly cookies — `create_session_token(user_id)` / `verify_session_token(token)` in `backend/app/core/auth.py`. Protected routes use `get_current_user` FastAPI dependency. Scope checking via `require_scope(*scopes)` dependency factory. GitHub tokens encrypted at rest with AES-256-GCM.

---

*Architecture analysis: 2026-05-29*
