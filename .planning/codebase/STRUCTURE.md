# Codebase Structure

**Analysis Date:** 2026-05-29

## Directory Layout

```
prlens/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── api/                # HTTP route handlers (8 routers)
│   │   ├── core/               # Config, auth, crypto, email, passwords, policy, security
│   │   ├── db/                 # SQLAlchemy engine + session
│   │   ├── integrations/       # GitHub API client + LLM client
│   │   ├── models/             # SQLAlchemy ORM models (9 models)
│   │   ├── prompts/            # LLM system prompts
│   │   ├── review_engine/      # Review orchestration + analyzers + diff parser
│   │   │   └── analyzers/      # Rule-based + LLM analyzers (5 analyzers)
│   │   ├── scoring/            # Risk score calculation
│   │   ├── main.py             # FastAPI app entry point
│   │   └── __init__.py
│   ├── alembic/                # Migration templates (not actively used)
│   ├── tests/                  # Test directory (largely empty)
│   ├── pyproject.toml          # Python dependencies (uv)
│   └── uv.lock                 # Lockfile
├── frontend/                   # React + Vite + Tailwind SPA
│   ├── src/
│   │   ├── pages/              # Page components (8 pages)
│   │   ├── components/         # Shared UI components (4 components)
│   │   ├── hooks/              # React hooks + context (3 hooks)
│   │   ├── lib/                # API client, utilities
│   │   ├── App.tsx             # Route definitions
│   │   └── main.tsx            # React entry point
│   ├── package.json
│   ├── vite.config.ts          # Dev proxy for /api
│   ├── tailwind.config.js      # Tailwind + design tokens
│   ├── postcss.config.js
│   └── tsconfig.json
├── infra/                      # Docker deployment configs
│   ├── docker-compose.yml      # Postgres + backend + frontend
│   └── docker/
│       ├── Dockerfile.backend
│       ├── Dockerfile.frontend
│       └── nginx.conf
├── scripts/                    # Development helper scripts
│   ├── setup-dev.sh
│   ├── run-backend.sh
│   ├── run-frontend.sh
│   ├── generate-keys.sh
│   └── db-migrate.sh
├── docs/                       # Documentation
│   └── SECURITY.md
├── .env                        # Local environment (gitignored except .env.example)
├── .env.example                # Env var reference
├── AGENTS.md                   # AI agent onboarding doc
├── .claude/                    # Skills + session state
└── .planning/                  # Architecture/planning docs (this directory)
```

## Directory Purposes

### `backend/app/api/`
- **Purpose:** All HTTP route handlers, organized by domain
- **Contains:** 8 FastAPI `APIRouter` modules, each with prefix and tags
- **Route prefix mapping:**
  | File | Prefix | Purpose |
  |------|--------|---------|
  | `auth.py` | `/api/auth` | Register, login, OAuth flows (Google, GitHub), session exchange, scopes |
  | `repos.py` | `/api/repos` | List GitHub repos, install/uninstall webhooks |
  | `review.py` | `/api/review` | Manual PR review trigger |
  | `webhooks.py` | `/api/webhooks` | GitHub webhook receiver for auto-review |
  | `prs.py` | `/api/prs` | List/get PRs with findings and review runs |
  | `dashboard.py` | `/api/dashboard` | Summary stats, policy info |
  | `evaluations.py` | `/api/evaluations` | Evaluation run CRUD |
  | `ai.py` | `/api/ai` | LLM provider presets, per-user AI config |

### `backend/app/core/`
- **Purpose:** Shared infrastructure and cross-cutting concerns
- **Contains:**
  - `config.py` — `Settings` class (40 env vars), loaded from `.env` + environment
  - `auth.py` — JWT session token create/verify, `get_current_user` dependency, `require_scope` factory
  - `passwords.py` — bcrypt hash/verify via passlib (async via `asyncio.to_thread`)
  - `crypto.py` — AES-256-GCM encrypt/decrypt for GitHub tokens and LLM API keys
  - `email.py` — OTP email via SMTP (Resend/SendGrid) or console logging, OTP generation
  - `security.py` — HMAC-SHA256 signature verification for GitHub webhooks
  - `policy.py` — `Policy` dataclass mapping settings to review configuration

### `backend/app/db/`
- **Purpose:** Database engine and session lifecycle
- **Contains:**
  - `base.py` — `DeclarativeBase` subclass for all models
  - `session.py` — Engine factory with URL auto-detection (`postgresql://` → asyncpg, `sqlite:///` → aiosqlite), `get_db()` async generator for FastAPI

### `backend/app/models/`
- **Purpose:** SQLAlchemy ORM models — database schema definition
- **Contains (9 models):**
  | Model | Table | Key Relationships |
  |-------|-------|-------------------|
  | `User` | `users` | Has many `UserToken`, one `UserAIConfig` |
  | `UserToken` | `user_tokens` | Belongs to `User`, stores encrypted GitHub tokens |
  | `UserAIConfig` | `user_ai_configs` | Belongs to `User`, stores encrypted LLM API key |
  | `OTPCode` | `otp_codes` | Standalone (keyed by email) |
  | `Repository` | `repositories` | Has many `PullRequest` |
  | `PullRequest` | `pull_requests` | Belongs to `Repository`, has many `Finding` + `ReviewRun` |
  | `ReviewRun` | `review_runs` | Belongs to `PullRequest` |
  | `Finding` | `findings` | Belongs to `PullRequest` |
  | `EvaluationRun` | `evaluation_runs` | Belongs to `PullRequest` |

### `backend/app/integrations/`
- **Purpose:** External API clients
- **Contains:**
  - `github_client.py` — `GitHubClient` class: fetch PR + diff, post PR comment
  - `llm_client.py` — `LLMClient` class: OpenAI-compatible chat completions, retry logic, JSON extraction

### `backend/app/review_engine/`
- **Purpose:** Core review pipeline — diff parsing, analysis, policy filtering
- **Contains:**
  - `__init__.py` — `run_review_on_diff()` orchestrator, `_apply_policy()` filter, `_PrContext`
  - `diff_parser.py` — `parse_diff()` function, `DiffFile`/`FileHunk` dataclasses, binary extension detection
  - `analyzers/base.py` — `BaseAnalyzer` abstract base class
  - `analyzers/security.py` — `SecurityAnalyzer`: hardcoded secrets, eval/exec, SQL injection, open redirect
  - `analyzers/reliability.py` — `ReliabilityAnalyzer`: bare excepts, missing error handling, race conditions
  - `analyzers/performance.py` — `PerformanceAnalyzer`: N+1 queries, blocking I/O in async, missing pagination
  - `analyzers/testing.py` — `TestingAnalyzer`: missing tests for large diffs, uncovered functions, hack comments
  - `analyzers/llm.py` — `LLMAnalyzer`: delegates to LLM for review, chunks large diffs, deduplicates

### `backend/app/scoring/`
- **Purpose:** Risk score calculation
- **Contains:** `risk.py` — `calculate_risk_score(findings) -> float` (severity-weighted, confidence-weighted, normalized 0–1)

### `backend/app/prompts/`
- **Purpose:** LLM prompt templates
- **Contains:** `system.py` — `REVIEW_SYSTEM_PROMPT` constant, `build_review_prompt()` builder function

### `frontend/src/pages/`
- **Purpose:** Top-level page components, one per route
- **Contains (8 pages):**
  | Page | Route | Purpose |
  |------|-------|---------|
  | `Dashboard.tsx` | `/` | Manual review form, stats summary, recent PRs, review results |
  | `PRList.tsx` | `/prs` | List reviewed PRs sorted by risk score |
  | `PRDetail.tsx` | `/prs/:id` | Single PR with findings, file risk, review runs |
  | `Evaluation.tsx` | `/evaluations` | Evaluation run list |
  | `LoginPage.tsx` | `/login` | Email+password login/register, OAuth buttons, OTP entry |
  | `RepoPicker.tsx` | `/repos` | GitHub repo list with install/uninstall |
  | `AISettings.tsx` | `/ai` | LLM provider selection, API key config, model settings |
  | `AuthCallback.tsx` | `/auth/success` | OAuth callback handler (exchange token processing) |

### `frontend/src/components/`
- **Purpose:** Reusable UI components
- **Contains:**
  - `Layout.tsx` — App shell: navbar, auth check (`AuthProvider` wrapper), `Outlet` for nested routes
  - `AuthRequired.tsx` — Guard component: prompts GitHub connection if not authed, shows scope warnings
  - `FindingCard.tsx` — Single finding display with severity, category, message, suggestion
  - `SeverityBadge.tsx` — Colored severity label pill
  - `RiskGauge.tsx` — Horizontal progress bar for risk score

### `frontend/src/hooks/`
- **Purpose:** React hooks and context providers
- **Contains:**
  - `useAuth.tsx` — `AuthProvider` context + `useAuth` hook: user state, login/logout, scope management
  - `usePrs.ts` — `usePRs()` hook: fetch PR list from `/api/prs`
  - `useFindings.ts` — `useFindings(prId)` hook: fetch findings for a PR

### `frontend/src/lib/`
- **Purpose:** API client and utilities
- **Contains:** `api.ts` — Axios instance with `withCredentials: true`, proxies `/api` requests

## Key File Locations

**Entry Points:**
- `backend/app/main.py` — FastAPI app creation, router registration, middleware, lifespan, health endpoint
- `frontend/src/main.tsx` — React DOM render with `BrowserRouter`
- `frontend/src/App.tsx` — Route tree definition (`<Routes>` with `<Layout>` wrapper)

**Configuration:**
- `backend/app/core/config.py` — All env var definitions with defaults and `.env` file loading
- `frontend/vite.config.ts` — Dev server config with `/api` proxy to backend
- `frontend/tailwind.config.js` — Design token mappings to Tailwind utilities
- `backend/pyproject.toml` — Python dependencies
- `frontend/package.json` — JS dependencies
- `.env.example` — Documented env vars for onboarding

**Core Logic:**
- `backend/app/review_engine/__init__.py` — Review pipeline orchestration
- `backend/app/review_engine/analyzers/*.py` — All analysis logic
- `backend/app/integrations/github_client.py` — GitHub API interaction
- `backend/app/integrations/llm_client.py` — LLM API interaction
- `backend/app/core/auth.py` — JWT auth dependency
- `backend/app/core/crypto.py` — Token encryption

**Testing:**
- `backend/tests/__init__.py` — Test directory (empty — no tests implemented)

## Naming Conventions

**Files (Python):**
- Snake case: `auth.py`, `github_client.py`, `review_engine/`, `diff_parser.py`, `user_ai_config.py`
- All API route files are single-word or concise: `auth.py`, `repos.py`, `prs.py`, `ai.py`

**Files (TypeScript/React):**
- PascalCase for components: `FindingCard.tsx`, `SeverityBadge.tsx`, `RiskGauge.tsx`, `AuthRequired.tsx`
- camelCase for hooks and utilities: `useAuth.tsx`, `usePrs.ts`, `useFindings.ts`, `api.ts`
- PascalCase for pages: `Dashboard.tsx`, `LoginPage.tsx`, `PRDetail.tsx`, `AISettings.tsx`

**Functions:**
- **Python:** Snake case — `run_review_on_diff()`, `calculate_risk_score()`, `get_current_user()`, `_apply_policy()`
- **TypeScript:** camelCase — `handleReview()`, `handleSave()`, `checkAuth()`, `refreshScopes()`

**Classes:**
- **Python:** PascalCase — `SecurityAnalyzer`, `GitHubClient`, `LLMClient`, `Settings`, `PullRequest`
- **TypeScript:** PascalCase for interfaces — `AuthUser`, `Finding`, `DashboardStats`, `PullRequest`

**Variables:**
- **Python:** Snake case — `diff_text`, `findings_raw`, `repo_row`, `severity_rank`
- **TypeScript:** camelCase — `riskColor`, `pendingEmail`, `prNumber`, `showOtp`

**Database columns:** Snake case — `hashed_password`, `encrypted_api_key`, `risk_score`, `created_at`

## Where to Add New Code

**New Feature / Route:**
- Backend handler: `backend/app/api/` — create or edit a router module
- Frontend page: `frontend/src/pages/` — create a component
- Route registration: `backend/app/main.py` — `app.include_router()` AND `frontend/src/App.tsx` — `<Route>` definition

**New Model:**
- Create file in `backend/app/models/`
- Import in `backend/app/main.py` (for `create_all` detection)

**New Analyzer:**
- Create file in `backend/app/review_engine/analyzers/` subclassing `BaseAnalyzer`
- Add feature flag to `settings` in `backend/app/core/config.py`
- Wire into `run_review_on_diff()` in `backend/app/review_engine/__init__.py`

**New Frontend Component:**
- Shared/reusable: `frontend/src/components/`
- Page-level: `frontend/src/pages/`

**New Hook:**
- `frontend/src/hooks/`

**New Env Var:**
- Add to `backend/app/core/config.py` (`Settings` class)
- Add to `.env.example`
- Add to `infra/docker-compose.yml` if production-relevant

**Utilities:**
- Shared helpers: `frontend/src/lib/` (frontend) or `backend/app/core/` (backend)

## Special Directories

**`backend/alembic/`:**
- Purpose: Migration templates (generated by Alembic init)
- Generated: Yes (template)
- Actively used: **No** — dev uses `create_all` on startup

**`backend/app/review_engine/analyzers/`:**
- Purpose: Plugin-style analyzer modules
- Each analyzer is a self-contained class extending `BaseAnalyzer`
- New analyzers can be added without modifying existing ones

**`.planning/`:**
- Purpose: Architecture and planning documents generated by GSD tools
- Committed: Yes
- Contains: Codebase analysis documents consumed by AI agents

**`.claude/`:**
- Purpose: AI agent skills, session state, and local configuration
- Committed: Yes
- Contains: Skills for brownfield development, testing, design, etc.

---

*Structure analysis: 2026-05-29*
