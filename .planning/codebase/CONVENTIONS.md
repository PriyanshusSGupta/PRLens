# Coding Conventions

**Analysis Date:** 2026-05-29

## Naming Patterns

### Python (`backend/app/`)

**Files:**
- `snake_case.py` — Modules match their content: `security.py`, `github_client.py`, `diff_parser.py`, `pull_request.py`

**Functions:**
- `snake_case` for all functions and methods: `create_session_token()`, `verify_password()`, `calculate_risk_score()`
- Async functions prefixed appropriately: `async def analyze()`, `async def get_current_user()`
- Private helpers prefixed with underscore: `_secret()`, `_build_url()`, `_set_auth_cookie()`, `_assert_configured()`
- Factory/hook function names: `get_db()`, `get_engine()`, `get_policy()`

**Classes:**
- `PascalCase` — `SecurityAnalyzer(BaseAnalyzer)`, `GitHubClient`, `Settings(BaseSettings)`, `User(Base)`, `FileHunk`

**Variables:**
- `snake_case` — `diff_text`, `current_file`, `findings`, `pr_data`, `risk_score`
- Constants: `UPPER_SNAKE_CASE` — `GITHUB_API_BASE = "..."`, `BINARY_EXTENSIONS = {...}`, `OTP_EXPIRY_MINUTES`

**Models (SQLAlchemy):**
- `__tablename__` in `snake_case` plural: `"users"`, `"pull_requests"`, `"review_runs"`, `"user_tokens"`
- Columns: `snake_case` — `hashed_password`, `pr_number`, `risk_score`, `encrypted_token`
- Relationships: `back_populates` matching the related model's relationship name

**Pydantic schemas:**
- `PascalCase` with `Body`/`Request` suffix: `RegisterBody`, `LoginBody`, `ReviewRequest`, `SetAIConfigBody`

**Router variables:**
- `router = APIRouter(prefix="/api/...", tags=["..."])` — always named `router`, defined at module level

### TypeScript (`frontend/src/`)

**Files:**
- `PascalCase.tsx` for React components and pages: `FindingCard.tsx`, `SeverityBadge.tsx`, `LoginPage.tsx`, `Dashboard.tsx`
- `camelCase.ts` for hooks and utilities: `useAuth.tsx`, `usePrs.ts`, `api.ts`
- Exception: `index.css` and `App.tsx` follow framework conventions

**Functions:**
- `camelCase` for all functions: `handleRegister()`, `handleLogin()`, `handleReview()`
- `camelCase` for named hooks: `usePRs()`, `useFindings()`, `useAuth()`
- Private helpers: lowercase, e.g. `riskColor()`, `severityVars`, `categoryVars`

**Components:**
- Default exports with `PascalCase`: `export default function FindingCard()`, `export default function Dashboard()`
- Props interface defined in-file: `interface FindingCardProps { ... }`, `interface RiskGaugeProps { score: number }`

**Variables:**
- `camelCase` — `setLoading`, `handleOtp`, `filtered`, `riskColor`, `sevColor`
- Constants: `UPPER_SNAKE_CASE` — `CATEGORIES = ['All', 'Security', ...]`

**Interfaces:**
- `PascalCase` — `PullRequest`, `Finding`, `AuthUser`, `AuthContextType`, `ReviewResult`, `DashboardStats`

## Code Style

**Formatting:**
- **Python:** No explicit formatter detected (no `ruff` or `black` config in `pyproject.toml`). Uses consistent style with 4-space indentation, blank lines between top-level definitions.
- **TypeScript:** No `.prettierrc` or `eslint.config.*` detected. Uses single quotes, semicolons, 2-space indentation, consistent trailing commas.

**Linting:**
- **Python:** No linting config detected in `pyproject.toml` (dev dependency group is empty).
- **TypeScript:** `strict: true` in `tsconfig.json` with `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch` enabled.
- **Commits:** `@commitlint/config-conventional` enforced via `.commitlintrc.json` — types: `feat|fix|refactor|perf|docs|style|test|chore`, lowercase, subjects ≤50 chars, body ≤72 chars.

**TypeScript Strict Rules:**
```json
{
  "strict": true,
  "noUnusedLocals": true,
  "noUnusedParameters": true,
  "noFallthroughCasesInSwitch": true,
  "forceConsistentCasingInFileNames": true
}
```

## Import Organization

### Python (`backend/app/`)

**Order:**
1. Standard library: `import datetime`, `import secrets`, `import re`, `from abc import ABC`, `from dataclasses import dataclass`
2. Third-party: `from fastapi import APIRouter`, `from sqlalchemy import select`, `import httpx`
3. Internal: `from app.core.config import settings`, `from app.db.session import get_db`

**Style:**
- Explicit imports preferred: `from fastapi import APIRouter, Depends` (not `import fastapi`)
- Internal imports use absolute paths from `app.`: `from app.review_engine.diff_parser import parse_diff`
- Inline imports inside functions for occasional use: e.g. `from app.core.policy import get_policy as _get_policy` inside `dashboard.py`; `from urllib.parse import urlparse` inside `ai.py`

### TypeScript (`frontend/src/`)

**Order:**
1. Third-party: `import { Routes, Route } from 'react-router-dom'`, `import { useState, useEffect } from 'react'`, `import axios from 'axios'`
2. Internal absolute (relative): `import App from './App'`, `import Layout from './components/Layout'`, `import api from '../lib/api'`
3. CSS: `import './index.css'`

**Path Aliases:**
- None detected. All imports use relative paths (`./`, `../`).

## Error Handling

### Python (Backend)

**Patterns:**
- **HTTP errors:** `raise HTTPException(status_code=4xx, detail="message")` — used in all API route handlers. Standard FastAPI pattern.
- **External API errors:** Wrapped with `HTTPException(status_code=502)` — `raise HTTPException(status_code=502, detail=f"Failed to fetch PR from GitHub: {e}")`
- **Configuration errors:** `raise RuntimeError("JWT_SECRET environment variable is required...")` — used in crypto/auth core modules
- **Validation errors:** Pydantic `@field_validator` decorators with `raise ValueError(...)` — used in `ReviewRequest` and `SetAIConfigBody`
- **Async DB errors:** Not explicitly caught — relies on FastAPI's auto-rollback on exception
- **Rate limiting:** `@limiter.limit("5/minute")` decorator on sensitive endpoints (`/verify-otp`, `/login`)
- **"Validate at system boundaries only"** per AGENTS.md — no try/catch for impossible scenarios

Example patterns:
```python
# Standard API error
if not pr:
    raise HTTPException(status_code=404, detail="PR not found")

# External service error
try:
    pr_data, diff_text = await client.fetch_pr_and_diff(owner, repo, pr_number)
except Exception as e:
    raise HTTPException(status_code=502, detail=f"Failed to fetch PR from GitHub: {e}")

# Validation
@field_validator("owner", "repo")
@classmethod
def validate_name(cls, v: str) -> str:
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$', v):
        raise ValueError("must match GitHub naming rules")
    return v
```

### TypeScript (Frontend)

**Patterns:**
- API calls use `try/catch` with type assertion for error extraction:
```typescript
try {
  const res = await api.post('/review', { ... });
  setResult(res.data);
} catch (err: unknown) {
  const msg = err instanceof Error ? err.message : 'Failed to fetch review';
  setError(msg);
}
```
- OAuth error extraction pattern:
```typescript
const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Registration failed';
```
- API errors are stored in `error` state variables and rendered conditionally in the UI
- Promise rejection caught with `.catch(() => ...)` in hooks:
```typescript
api.get('/prs').then((res) => {
  setPRs(res.data);
  setLoading(false);
}).catch(() => setLoading(false));
```

## Logging

**Python (Backend):**
- Framework: `import logging` — standard library only
- Logger: `logger = logging.getLogger(__name__)` at module level
- Patterns:
  - `logger.info("OTP for %s: %s", to_email, code)` — console logging for OTP in dev
  - `logger.warning("Database not available, skipping auto-migration: %s", e)` — non-fatal warnings
  - `logger.warning("Failed to send OTP via SMTP, logging to console: %s", e)` — degraded path logging
- No structured logging, no log aggregator integration

**TypeScript (Frontend):**
- No logging library. No `console.log` statements detected.
- No error monitoring integration (Sentry, etc.) detected.

## Comments

### Python (Backend)

**When to Comment:**
- Docstrings on dataclasses: `"""Synchronous SMTP call — MUST be run via asyncio.to_thread()."""`
- No docstrings on models (SQLAlchemy) — schema is self-evident from column definitions
- No JSDoc/TSDoc style — Python uses `"""` docstrings sparingly
- Inline comments for complex regex or non-obvious state:
  ```python
  # In production, this would actually re-run the review pipeline
  ```

### TypeScript (Frontend)

- No JSDoc/TSDoc comments detected
- No inline comments in any component
- Self-documenting code through descriptive variable/function names

## Function Design

### Python

**Size:**
- Analyzer `analyze()` methods: 50-110 lines
- API route handlers: 15-100 lines
- Helper functions: 3-30 lines
- Keeping things readable but not aggressively splitting

**Parameters:**
- Default values for optional params: `def __init__(self, api_key: str = "", model: str = "", base_url: str = "")`
- Type hints always present: `async def fetch_pr_and_diff(self, owner: str, repo: str, pr_number: int) -> tuple[dict, str]`
- Union types: `def __init__(self, llm_client: LLMClient | None = None)`

**Return Values:**
- API handlers return dicts (serialized by FastAPI)
- Internal functions: typed return values `-> float`, `-> str`, `-> list[dict]`, `-> bool`
- None return: functions returning nothing or using `yield` (generators for DB sessions)
- Error states: `dict | None` for `verify_session_token()`

### TypeScript

**Size:**
- Pages: 65-248 lines
- Components: 23-105 lines
- Hooks: 27-75 lines

**Parameters:**
- Props interface always defined: `interface FindingCardProps { finding: { ... } }`
- Destructured props: `export default function FindingCard({ finding }: FindingCardProps)`

**Return Values:**
- React components return JSX (implicit `ReactNode`)
- Hooks return `{ data, loading }` objects: `return { prs, loading }`
- Helper functions return primitives: `function riskColor(score: number): string`

## Module Design

### Python

**Exports:**
- `__init__.py` files re-export key symbols: `app/review_engine/__init__.py` exports `run_review_on_diff`
- Models imported in `main.py` for SQLAlchemy `create_all` detection
- Analyzer classes exported from their own files, instantiated in `__init__.py`

**Imports Convention:**
- All models explicitly imported in `main.py` for table creation:
```python
import app.models.user
import app.models.user_token
import app.models.user_ai_config
...
```

### TypeScript

**Exports:**
- Components use `export default` — consistent across all pages and components
- Hooks use named exports: `export function usePRs()`, `export function useFindings()`, `export function useAuth()`, `export function AuthProvider()`
- `useAuth.tsx` exports both `AuthProvider` (named) and `useAuth` (named)
- `api.ts` exports default: `export default api`

**Barrel Files:**
- None detected. Each import path is explicit: `'../lib/api'`, `'../hooks/useAuth'`, `'./FindingCard'`

## TypeScript-Specific Conventions

**No unused imports:** `noUnusedLocals: true` and `noUnusedParameters: true` enforced in tsconfig
**JSX:** `"jsx": "react-jsx"` — modern automatic JSX transform
**Module resolution:** `"bundler"` — Vite-compatible
**noEmit:** TypeScript for type-checking only (Vite handles bundling)

---

*Convention analysis: 2026-05-29*
