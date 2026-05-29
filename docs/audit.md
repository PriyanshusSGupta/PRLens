# PRLens Security & Quality Audit

**Date:** 2026-05-29
**Methodology:** Five-axis code review + code simplification + security hardening + performance optimization
**Skills Applied:** `code-review-and-quality`, `code-simplification`, `security-and-hardening`, `performance-optimization`

---

## 🔴 CRITICAL (9 findings — fix before any deployment)

### C1 — Live secrets potentially committed to git history
- **File:** `.env`
- **Category:** Security / Secrets Management
- **Details:** The `.env` file contains live GitHub OAuth credentials, JWT secret, and encryption key. Verify with `git log -- .env`. If committed, rotate all secrets immediately.
- **Fix:** Run `scripts/generate-keys.sh` to generate new keys. Recreate GitHub OAuth App credentials. Add `.env` to `.gitignore` (already done — verify it was added before any commits).

### C2 — JWT secret falls back to hardcoded `"dev-secret-change-me"`
- **File:** `backend/app/core/auth.py:14`
- **Category:** Security / Authentication
- **Fix:** Remove the fallback. Raise a fatal error if `JWT_SECRET` is unset:
  ```python
  def _secret() -> str:
      if not settings.jwt_secret:
          raise RuntimeError("JWT_SECRET environment variable is required")
      return settings.jwt_secret
  ```

### C3 — Encryption key falls back to 32 null bytes
- **File:** `backend/app/core/crypto.py:10-11`
- **Category:** Security / Cryptography
- **Fix:** Same pattern as C2 — raise fatal error on startup if `ENCRYPTION_KEY` is unset.

### C4 — OAuth state stored in global unbounded dict (memory leak + multi-process unsafe)
- **File:** `backend/app/api/auth.py:28`
- **Category:** Security / Performance
- **Details:** `OAUTH_STATES: dict[str, str] = {}` — no TTL, no cleanup, no shared state for multi-process deployments. Abandoned OAuth flows leak entries forever.
- **Fix:** Use a TTL cache (e.g., `cachetools.TTLCache`) with 10-minute expiry. For production, store OAuth state in the database.

### C5 — PostgreSQL Docker credentials hardcoded as `postgres/postgres`
- **File:** `infra/docker-compose.yml:5-7`
- **Category:** Security / Configuration
- **Fix:** Use `${POSTGRES_PASSWORD}` environment variable. Do not expose port 5432 to host in production.

### C6 — Blocking SMTP in async function blocks event loop
- **File:** `backend/app/core/email.py:33-42`
- **Category:** Performance / Async blocking
- **Details:** `smtplib.SMTP` is synchronous but called from `async def send_otp`. A slow SMTP server blocks the entire event loop.
- **Fix:** Wrap in `asyncio.to_thread()` or use `aiosmtplib`.

### C7 — Blocking bcrypt hash in async login/register handlers
- **File:** `backend/app/core/passwords.py:8`
- **Category:** Performance / Async blocking
- **Details:** `pwd_context.hash()` and `.verify()` are CPU-bound (200-500ms) and block the event loop during concurrent logins.
- **Fix:** Wrap in `asyncio.to_thread(hash_password, password)`.

### C8 — JWT token stored in localStorage (XSS-vulnerable)
- **File:** `frontend/src/lib/api.ts:11`
- **Category:** Security / Session Management
- **Details:** localStorage is accessible to any JavaScript on the page. Any XSS vulnerability allows token theft.
- **Fix:** Switch to `httpOnly` cookies set by the backend. Currently the backend sends tokens in JSON — implement proper `Set-Cookie` headers.

### C9 — AuthCallback passes JWT via URL query parameter
- **File:** `backend/app/api/auth.py:195,259`
- **Category:** Security / Token leakage
- **Details:** `?token=JWT` appears in browser history, server logs, Referer headers, and analytics.
- **Fix:** Use a short-lived single-use authorization code exchanged server-side, or set the JWT as an httpOnly cookie on redirect.

---

## 🟠 HIGH (22 findings — fix before production use)

### H1 — Missing `/api/auth/scopes` endpoint (frontend 404s)
- **File:** `backend/app/api/auth.py` (missing route), `frontend/src/hooks/useAuth.tsx:55`
- **Category:** Correctness
- **Fix:** Add `GET /api/auth/scopes` route or remove the frontend call.

### H2 — Webhook secret fallback exposes all repos to global secret
- **File:** `backend/app/api/webhooks.py:56-60`
- **Category:** Security / Access Control
- **Fix:** Remove the `elif settings.github_webhook_secret` fallback. Each repo must have its own secret. If unset, reject with 401.

### H3 — `_get_user_token` fetches any provider's token (Google users can't access repos)
- **File:** `backend/app/api/repos.py:20-25`
- **Category:** Correctness
- **Fix:** Add `UserToken.provider == "github"` filter.

### H4 — Policy threshold defaults to `critical` — all high/medium/low findings silently discarded
- **File:** `backend/app/review_engine/__init__.py:33-34`
- **Category:** Correctness
- **Fix:** Change default to `SEVERITY_THRESHOLD_BLOCK=low` or separate display threshold from block threshold.

### H5 — No rate limiting on any auth endpoint
- **Files:** `backend/app/api/auth.py` (all endpoints)
- **Category:** Security / Brute force
- **Fix:** Add rate limiting. At minimum: 5 login attempts/min per IP, 3 OTP attempts per email per 10 minutes. Use `slowapi` or similar.

### H6 — OTP brute-force possible (1M combinations, no attempt tracking)
- **File:** `backend/app/api/auth.py:78-98`
- **Category:** Security / Authentication
- **Fix:** Add `attempts` column to `OTPCode`. Lock account after 5 failed attempts. Increase to 8-digit OTP.

### H7 — Logout does nothing server-side (JWT remains valid for 24h)
- **File:** `backend/app/api/auth.py:341-343`
- **Category:** Security / Session Management
- **Fix:** Implement a token denylist (DB table or Redis set with TTL). Check denylist in `get_current_user`.

### H8 — No security headers (HSTS, X-Frame-Options, X-Content-Type-Options, CSP)
- **File:** `backend/app/main.py` (all endpoints)
- **Category:** Security / Misconfiguration
- **Fix:** Add security header middleware. Add CSP in nginx config.

### H9 — Error messages leak provider responses to client
- **File:** `backend/app/api/auth.py:173,208`
- **Category:** Security / Information leakage
- **Fix:** Log full error server-side; return generic "OAuth provider error" to client.

### H10 — No input validation on `owner`/`repo` path parameters
- **File:** `backend/app/api/review.py:17-22`
- **Category:** Security / Injection
- **Fix:** Validate against regex `^[a-zA-Z0-9][a-zA-Z0-9_.-]*$`.

### H11 — AI `base_url` accepts arbitrary URLs (SSRF vector)
- **File:** `backend/app/api/ai.py:104-106`
- **Category:** Security / SSRF
- **Fix:** Block private/RFC1918 IP ranges in `base_url`. Validate against allowlist of known provider domains.

### H12 — Webhook handler uses unauthenticated GitHub API calls
- **File:** `backend/app/api/webhooks.py:86`
- **Category:** Security / Architecture
- **Fix:** Use the repository owner's stored GitHub token from `user_tokens`. Never call GitHub API unauthenticated.

### H13 — `diff_max_size` config never enforced
- **File:** `backend/app/review_engine/__init__.py`
- **Category:** Security / Performance
- **Fix:** Check `len(diff_text)` against `settings.max_diff_size` before processing. Reject oversized diffs.

### H14 — `run_review_on_diff` never runs Security/Reliability/Performance/Testing analyzers
- **File:** `backend/app/review_engine/__init__.py`
- **Category:** Correctness / Architecture
- **Details:** The individual analyzers (with rich checks) are only used in the dead `run_review` path. The real code paths use only hardcoded rules + LLM.
- **Fix:** Route all reviews through the individual analyzers, or acknowledge that `run_review_on_diff` is the canonical path and merge the analyzer logic there.

### H15 — Two divergent review code paths (`run_review` vs `run_review_on_diff`)
- **File:** `backend/app/review_engine/__init__.py`
- **Category:** Architecture
- **Details:** `run_review` is dead code. `run_review_on_diff` duplicates LLM logic from `LLMAnalyzer`. These produce different results for the same diff.
- **Fix:** Consolidate into a single review pipeline.

### H16 — `send_otp` returns `True` even on SMTP failure (user sees "check email" but nothing sent)
- **File:** `backend/app/core/email.py:38-42`
- **Category:** Correctness
- **Fix:** Return `False` on SMTP failure. Let the caller decide how to handle it (show error, fall back to console, etc.).

### H17 — `list_repos` fetches all active repos unbounded (memory risk)
- **File:** `backend/app/api/repos.py:47-48`
- **Category:** Performance
- **Fix:** Add `.limit()` and use a `set` for O(1) lookup instead of iterating ORM objects.

### H18 — Missing database indexes on 6 tables
- **Files:** `backend/app/models/*.py`
- **Category:** Performance
- **Details:** No indexes on `pull_requests.risk_score`, `findings.pr_id`, `findings.severity`, `findings.category`, `review_runs.pr_id`, `otp_codes.(email,code,used,expires_at)`, `user_tokens.(user_id,created_at)`, `evaluation_runs.created_at`.
- **Fix:** Add indexes using SQLAlchemy `Index()`.

### H19 — No connection pool configuration
- **File:** `backend/app/db/session.py:15`
- **Category:** Performance
- **Fix:** Add `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, `pool_recycle=3600`.

### H20 — No pagination on findings endpoint
- **File:** `backend/app/api/prs.py:108-115`
- **Category:** Performance
- **Fix:** Add `.limit()` and `.offset()` or cursor-based pagination.

### H21 — `fetch_pr_and_diff` makes two sequential HTTP calls (can be parallel)
- **File:** `backend/app/integrations/github_client.py:22-43`
- **Category:** Performance
- **Fix:** Use `asyncio.gather` to fetch PR data and diff concurrently.

### H22 — `auth.py` uses `time.time()` for JWT expiry (not timezone-aware)
- **File:** `backend/app/core/auth.py:19`
- **Category:** Correctness
- **Fix:** Use `datetime.utcnow()` + `timedelta` or `time.time()` consistently. Prefer `datetime` with timezone.

---

## 🟡 MEDIUM (18 findings — address before launch)

### M1 — Dead code: `run_review` function never called
- **File:** `backend/app/review_engine/__init__.py:14`
- **Fix:** Remove or integrate into the canonical review pipeline.

### M2 — Dead code: `ANALYZERS` module-level list never used
- **File:** `backend/app/review_engine/__init__.py:11`
- **Fix:** Remove.

### M3 — Dead code: `get_user_llm_client` never called
- **File:** `backend/app/integrations/llm_client.py:67`
- **Fix:** Remove or wire into review pipeline.

### M4 — Dead code: `calculate_file_risk` never called
- **File:** `backend/app/scoring/risk.py:17`
- **Fix:** Remove.

### M5 — Dead code: `TOKEN_PATTERN` regex never used
- **File:** `backend/app/review_engine/analyzers/security.py:12`
- **Fix:** Remove or integrate.

### M6 — Dead code: no-op loop in `_run_rule_based_checks`
- **File:** `backend/app/review_engine/__init__.py:133-135`
- **Code:** `for line in added_lines: if line.startswith("+") and ("TODO" in line): pass`
- **Fix:** Remove.

### M7 — `UserToken.expires_at` field never set
- **File:** `backend/app/models/user_token.py:15`
- **Fix:** Set it when creating tokens or remove the column.

### M8 — Binary extension list duplicated (two different sets)
- **Files:** `backend/app/review_engine/__init__.py:105-113` and `diff_parser.py:22-28`
- **Fix:** Keep only the set in `diff_parser.py` and import it.

### M9 — Analyzer enable/disable if-chain repeated 5 times
- **File:** `backend/app/review_engine/__init__.py:21-35`
- **Fix:** Use a data-driven mapping: `{"security": settings.enable_security, ...}`.

### M10 — Severity color maps duplicated in two components
- **Files:** `frontend/src/components/SeverityBadge.tsx:2-6`, `FindingCard.tsx:18-24`
- **Fix:** Extract to `constants/colors.ts`. Have `FindingCard` use `<SeverityBadge>`.

### M11 — `LoginPage.tsx` at 248 lines handles 4 workflows in one component
- **File:** `frontend/src/pages/LoginPage.tsx`
- **Fix:** Extract `LoginForm`, `RegisterForm`, `OtpVerification`, and `OAuthButtons` sub-components.

### M12 — `Dashboard.tsx` duplicates FindingCard rendering inline
- **File:** `frontend/src/pages/Dashboard.tsx:88-118`
- **Fix:** Use the existing `<FindingCard>` component.

### M13 — Nested ternary for risk color repeated in 4 places
- **Files:** `Dashboard.tsx:140`, `PRList.tsx:7`, `PRDetail.tsx:33`, `RiskGauge.tsx:7`
- **Fix:** Extract to shared `riskColor(score)` utility.

### M14 — No client-side request caching (re-fetches on every mount)
- **Files:** All frontend hooks and pages
- **Fix:** Add React Query or SWR for data fetching with stale-while-revalidate caching.

### M15 — No route-level code splitting in React
- **File:** `frontend/src/App.tsx`
- **Fix:** Use `React.lazy()` + `Suspense` for page components.

### M16 — Inline style objects recreated on every render (all components)
- **Pattern:** Project-wide in all TSX files
- **Impact:** React re-applies styles to DOM nodes on every render due to reference inequality.
- **Fix:** Extract static styles to constants outside component bodies. Use CSS modules or styled-components for dynamic styles.

### M17 — CORS allows wildcard methods and headers
- **File:** `backend/app/main.py:39-43`
- **Fix:** Restrict to `["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]` and `["Authorization", "Content-Type"]`.

### M18 — `ReviewRun.findings_count` manually set (can drift from actual finding count)
- **File:** `backend/app/models/review_run.py`
- **Fix:** Either add FK relationship from Finding to ReviewRun, or compute count dynamically from `SELECT COUNT(*)`.

---

## 🟢 LOW (12 findings — backlog candidates)

### L1 — `.env` file path uses 4x `parent.parent` — fragile
- **File:** `backend/app/core/config.py:44`
- **Fix:** Use `PRLENS_CONFIG_DIR` env var or well-known location.

### L2 — OTP duration hardcoded at 10 minutes (no config option)
- **File:** `backend/app/api/auth.py`
- **Fix:** Add `OTP_EXPIRY_MINUTES` to `Settings`.

### L3 — Password complexity minimal (only 8-char minimum)
- **File:** `backend/app/api/auth.py:57`
- **Fix:** Add uppercase, digit, and special character requirements. Check against HIBP.

### L4 — `generate_otp` returns string via `.__str__().zfill(6)` — use `str()`
- **File:** `backend/app/core/email.py:50`
- **Fix:** Use `str(secrets.randbelow(1_000_000)).zfill(6)`.

### L5 — `Alembic` versions directory empty (no migration scripts)
- **File:** `backend/alembic/versions/`
- **Fix:** Generate initial migration with `alembic revision --autogenerate -m "initial"`.

### L6 — `Alembic` env.py missing model imports for `user_ai_config` and `otp_code`
- **File:** `backend/alembic/env.py:7-13`
- **Fix:** Add `import app.models.user_ai_config` and `import app.models.otp_code`.

### L7 — `Policy` serialization done manually per-field in dashboard endpoint
- **File:** `backend/app/api/dashboard.py:62-76`
- **Fix:** Add `.to_dict()` method on `Policy` dataclass or use `dataclasses.asdict()`.

### L8 — `Dashboard.tsx` compares `risk_score === 0` (strict equality — won't match `0.0`)
- **File:** `frontend/src/pages/Dashboard.tsx:72`
- **Fix:** Use `result.risk_score <= 0` or `result.risk_score === 0 || result.risk_score === 0.0`.

### L9 — `CATEGORIES` array defined inside component body (recreated per render)
- **File:** `frontend/src/pages/PRDetail.tsx:21`
- **Fix:** Move outside component to module level.

### L10 — `repoPicker` `filtered` recomputed on every render without `useMemo`
- **File:** `frontend/src/pages/RepoPicker.tsx:47-49`
- **Fix:** Wrap in `useMemo(() => repos.filter(...), [repos, search])`.

### L11 — No `React.memo` on presentational components (`FindingCard`, `SeverityBadge`, `RiskGauge`)
- **Files:** All presentation components
- **Fix:** Wrap in `React.memo()`.

### L12 — `httpx.AsyncClient()` created per-request (no connection reuse)
- **Files:** `github_client.py`, `auth.py`, `repos.py`
- **Fix:** Create shared `httpx.AsyncClient` instance or use FastAPI's dependency injection for a request-scoped client.

---

## ✅ CONFIRMED GOOD

- `.env` is in `.gitignore` (verified)
- All 9 models imported in `main.py` for `create_all`
- All dependencies in `pyproject.toml` and `package.json` are used
- HMAC uses `compare_digest` for timing-safe comparison
- OAuth state uses `secrets.token_urlsafe(32)` — cryptographically random
- No Tailwind color classes in UI — all Hallmark design tokens
- All new routes registered in `main.py`
- No hardcoded secrets in source code (except the dev fallbacks noted in C2/C3)
- Framework auto-escaping in React (JSX auto-escapes) — no raw `dangerouslySetInnerHTML`

---

## SUMMARY

| Severity | Count | Categories |
|----------|-------|------------|
| Critical | 9 | Auth secrets, async blocking, session management, memory leak |
| High | 22 | Correctness bugs, missing indexes, rate limiting, input validation, architecture divergence |
| Medium | 18 | Dead code, duplicated logic, component organization, caching, code splitting |
| Low | 12 | Minor style, config fragility, micro-optimizations |
| **Total** | **61** | |

**Recommended action order:**
1. Fix C1-C3 (rotate secrets, remove dev fallbacks) — immediate
2. Fix C4-C9 (OAuth state, async blocking, JWT storage, rate limiting) — before any user traffic
3. Fix H1-H8 (scopes endpoint, webhook security, auth hardening) — before production
4. Fix H9-H22 (input validation, indexes, code path consolidation) — first production iteration
5. Address Medium and Low items as backlog
