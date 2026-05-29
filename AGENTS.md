# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, Cursor, Copilot, Antigravity, etc.) when working with code in this repository.

## Repository Overview

PRLens is a GitHub pull request reviewer that combines rule-based checks, LLM reasoning, and risk scoring. FastAPI backend + React frontend, SQLite for dev.

### Directory Map

```
backend/          FastAPI app (uv, SQLAlchemy async, SQLite)
  app/
    api/          Route handlers (auth, repos, review, webhooks, prs, dashboard, evaluations, ai)
    core/         crypto, auth (JWT), passwords (bcrypt), email (SMTP/console), policy, config
    db/           Base + session (auto-detects postgresql:// or sqlite:///)
    integrations/ github_client, llm_client (OpenAI-compatible, per-user key support)
    models/       SQLAlchemy models (User, UserToken, UserAIConfig, OTPCode, Repository, PullRequest, ReviewRun, Finding, EvaluationRun)
    prompts/      System prompts for LLM review
    review_engine/ analyzers/ (Security, Reliability, Performance, Testing, LLM), diff_parser, __init__ (orchestration)
    scoring/      Risk score calculation (severity-weighted)
  alembic/        Migrations (not used in dev — create_all on startup)
frontend/         React + Vite + Tailwind + Hallmark design tokens
  src/
    pages/        Dashboard, PRList, PRDetail, Evaluation, LoginPage, RepoPicker, AISettings, AuthCallback
    components/   Layout, AuthRequired, FindingCard, SeverityBadge, RiskGauge
    hooks/        useAuth (AuthProvider context), usePRs, useFindings
    lib/          Axios instance with Bearer token interceptor
infra/            docker-compose.yml, Dockerfiles, nginx.conf
scripts/          setup-dev.sh, run-backend.sh, run-frontend.sh, generate-keys.sh
docs/             SECURITY.md
```

### Auth Architecture

- **Login providers**: email+OTP, Google OAuth, GitHub OAuth (identity only)
- **Token delivery**: JWT returned in JSON → frontend stores in `localStorage` → sent as `Authorization: Bearer` header
- **GitHub repo access**: separate OAuth flow (`/api/auth/github-connect/login`) scoped to `repo:status,pull_requests:read` — runs after identity login
- **OTP**: 6-digit code, 10-min expiry, SMTP delivery (defaults to `console` logging in dev, flip `SMTP_HOST` for Resend/SendGrid)
- **Password hashing**: bcrypt via passlib
- **Token encryption**: AES-256-GCM via `cryptography` library, key from `ENCRYPTION_KEY` env var

### UI Design System (Hallmark)

- **Colors**: All via CSS custom properties — `var(--color-ink)`, `var(--color-ink-2)`, `var(--color-paper)`, `var(--color-paper-2)`, `var(--color-accent)`, `var(--color-muted)`, `var(--color-rule-subtle)`, severity/category vars in `tokens.css`
- **Typography**: `font-display` for headings, `font-outlier` for monospace/code, system stack for body
- **Radius**: `rounded-card` for cards, `rounded-pill` for buttons/pills, `rounded-input` for form inputs
- **Transitions**: `var(--dur-short)` with `var(--ease-out)` on interactive elements
- **Layout**: Tailwind grid/flex utilities only. No Tailwind colors — use design tokens always.
- **Never** use emoji in UI unless user explicitly requests it
- **Never** use Tailwind color classes (bg-blue-500, text-gray-700, etc.) — always `var(--color-*)`

### Developer Conventions

- **Python**: `uv` for package management, `uv run` to execute. `pyproject.toml` not requirements.txt.
- **TypeScript**: strict mode, no unused imports. Components are default exports.
- **Database**: SQLAlchemy async with `create_all` on startup. Models imported in `main.py` for table detection. No Alembic for dev.
- **Errors**: Don't add try/catch for scenarios that can't happen. Validate at system boundaries only.
- **Simplicity**: No single-use abstractions. Three similar lines → better than one premature helper.
- **Surgical changes**: Touch only files relevant to the task. Don't clean up adjacent code.

## Intent → Skill Mapping

When starting any task, first map user intent to the appropriate skill:

- **New feature / functionality** → `spec-driven-development`, then `incremental-implementation`, then `test-driven-development`
- **Planning / task breakdown** → `planning-and-task-breakdown`
- **Bug / failure / unexpected behavior** → `debugging-and-error-recovery`
- **Code review / quality check** → `code-review-and-quality`
- **Refactoring / simplification** → `code-simplification`
- **API or interface design** → `api-and-interface-design`
- **Frontend UI / page work** → `frontend-ui-engineering`
- **Security / auth / tokens** → `security-and-hardening`
- **Deployment / production prep** → `shipping-and-launch`
- **Documentation / architecture decisions** → `documentation-and-adrs`
- **Performance optimization** → `performance-optimization`
- **CI/CD / automation** → `ci-cd-and-automation`
- **Deprecation / migration** → `deprecation-and-migration`
- **Browser testing / debugging** → `browser-testing-with-devtools`

## Lifecycle Mapping

For full feature development, follow this sequence internally:

- **DEFINE** → `spec-driven-development`
- **PLAN** → `planning-and-task-breakdown`
- **BUILD** → `incremental-implementation` + `test-driven-development`
- **VERIFY** → `debugging-and-error-recovery`
- **REVIEW** → `code-review-and-quality`
- **SHIP** → `shipping-and-launch`

## Execution Model

For every request:

1. Determine if any skill applies (even 1% chance)
2. Invoke the appropriate skill using the `skill` tool
3. Follow the skill workflow strictly
4. Only proceed to implementation after required steps (spec, plan, etc.) are complete

### Anti-Rationalization

The following thoughts are incorrect and must be ignored:

- "This is too small for a skill"
- "I can just quickly implement this"
- "I'll gather context first"

Correct behavior: Always check for and use skills first.

## Common File Locations (Quick Reference)

| What | Where |
|---|---|
| Add a route | `backend/app/api/` — create or edit, then register in `main.py` |
| Add a model | `backend/app/models/` — import in `main.py` for create_all |
| Add a new analyzer | `backend/app/review_engine/analyzers/` — subclass `BaseAnalyzer` |
| Add a page | `frontend/src/pages/` — register route in `App.tsx` |
| Add env var | `backend/app/core/config.py` + `.env.example` |
| Change auth | `backend/app/api/auth.py` + `backend/app/core/auth.py` |
| Change UI style | `frontend/tokens.css` for tokens, `tailwind.config.js` for utilities |
| Change LLM prompt | `backend/app/prompts/system.py` |

## Pre-Flight Checklist (Before Marking Task Complete)

- [ ] Backend imports compile (`uv run python -c "from app.main import app"`)
- [ ] Frontend typechecks (`npx tsc --noEmit`)
- [ ] New models imported in `main.py`
- [ ] New routes registered in `main.py`
- [ ] New env vars in `.env.example` + `config.py`
- [ ] Design tokens used for all colors (no Tailwind color classes)
- [ ] No hardcoded secrets or keys
- [ ] Auth required on protected routes
