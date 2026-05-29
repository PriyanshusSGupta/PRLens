# Codebase Concerns

**Analysis Date:** 2026-05-29

## Tech Debt

### `ReviewRun.status` — Incomplete State Machine
- **Issue:** Status transitions are partially enforced. `ReviewRun` starts as `"in_progress"` and ends as `"completed"` or `"failed"`, but the model defaults to `"pending"`. There's no `"pending"→"in_progress"` transition anywhere — the status is set directly to `"in_progress"` at creation time (`backend/app/api/webhooks.py:83`).
- **Files:** `backend/app/models/review_run.py:11`, `backend/app/api/webhooks.py:83-98`, `backend/app/api/review.py:73`
- **Impact:** Inconsistency between model default (`"pending"`) and actual usage (`"in_progress"`). The status field is a string with no enum or validation, so any string value is accepted.
- **Fix approach:** Use an enum for `ReviewRun.status` with explicit transitions, or update the default to match actual usage.

### Evaluation Endpoint — Stub Implementation
- **Issue:** `POST /api/evaluations` creates a `EvaluationRun` record then immediately marks it as `"completed"` without actually running any review pipeline. The comment on line 58-59 says "In production, this would actually re-run the review pipeline" — this is dead code.
- **Files:** `backend/app/api/evaluations.py:43-66`
- **Impact:** The evaluations feature is non-functional. `precision`, `false_positive_rate`, and `coverage` fields are always `null`. Users can create evaluation runs but they never produce actual metrics.
- **Fix approach:** Either implement the review re-run pipeline with the specified prompt version, or remove the endpoint and model.

### `verification_code` in `RegisterBody` — Missing Field
- **Issue:** The `RegisterBody` model (`backend/app/api/auth.py:38-40`) doesn't have a `verification_code` field, but the `/api/auth/register` endpoint sends an OTP after registration. The frontend has no corresponding UI to enter the code on the registration flow — the `/verify-otp` endpoint exists separately but there's no way to call it from the register flow gracefully.
- **Files:** `backend/app/api/auth.py:38-50, 83-110, 113-144`
- **Impact:** Registration flow forces users to check their email for OTP, then navigate to a separate verification step without clear UX continuity. The OTP code is logged to console in dev (`backend/app/core/email.py:49`), which is intentional for dev but leaks codes in production if log level is too permissive.

### Password Validation — Minimal
- **Issue:** The only password validation is `len(body.password) >= 8` (`backend/app/api/auth.py:88-89`). No complexity requirements (uppercase, digit, special char), no common-password check, no breach check.
- **Files:** `backend/app/api/auth.py:88-89`
- **Impact:** Weak passwords are accepted. Since OTP verification is required for email-password registration, the actual risk is reduced, but direct login bypasses OTP if the account is already verified.
- **Fix approach:** Add password complexity validation (zxcvbn or regex for min requirements) and a common-password blocklist.

### `PullRequest` Model — Unindexed Foreign Keys
- **Issue:** `PullRequest.repo_id` is a `ForeignKey("repositories.id")` with no explicit index. For a system that may accumulate thousands of PRs per repo, queries filtering by `repo_id` will perform full table scans.
- **Files:** `backend/app/models/pull_request.py:10`, `backend/app/models/finding.py:10`, `backend/app/models/review_run.py:10`
- **Impact:** Queries in `backend/app/api/prs.py:20-24` (which joins `PullRequest` + `Repository`) and `backend/app/api/webhooks.py:53-60` (which filters by `repo_id` + `pr_number`) degrade with scale.
- **Fix approach:** Add `index=True` on `repo_id` in `PullRequest`, `pr_id` in `Finding` and `ReviewRun`, and `email` in `User`.

### Rate Limiter — Global Scope, Not Per-Route
- **Issue:** Rate limiting is configured at app level (`"200/minute"`) via SlowAPI in `backend/app/main.py:43-46`. Only the auth endpoints add `@limiter.limit("5/minute")` decorators. All other endpoints inherit the global limit, which is generous enough that targeted abuse of `/api/review` or `/api/repos` is not meaningfully throttled.
- **Files:** `backend/app/main.py:43-46`
- **Impact:** Unauthenticated or lightly-limited endpoints can be hammered. The `/api/review` endpoint makes external API calls to GitHub and could be used for SSRF-style exploration or to exhaust GitHub API quotas.
- **Fix approach:** Implement per-route rate limits on expensive endpoints (`/api/review`, `/api/repos/install`, `/api/auth/register`).

### No Test Suite
- **Issue:** Zero test files exist anywhere in the codebase. No unit tests, integration tests, or E2E tests. The `backend/pyproject.toml` has no test framework dependency. The CI workflow `pr-coverage.yml` references a script (`bash .wednesday/scripts/pr-coverage.sh`) that likely doesn't exist as a standalone — and there's nothing for npm to test given no test scripts in the frontend.
- **Files:** Entire codebase
- **Impact:** Every refactor, dependency upgrade, or feature addition is blind. No regression safety net. The review engine analyzers themselves (`backend/app/review_engine/analyzers/`), which are purely logic-based with regex and string matching, are prime candidates for unit tests but have none.
- **Fix approach:** Start with unit tests for the diff parser (`backend/app/review_engine/diff_parser.py`) and individual analyzers. Add pytest to pyproject.toml. Add vitest for frontend.

### CORS Configuration — Frontend URL Hardcoded
- **Issue:** CORS origins are set from `settings.frontend_url` (`backend/app/main.py:59`), which defaults to `http://localhost:5173`. In production, this must be configured to the production frontend URL. If misconfigured, CORS will reject all browser requests.
- **Files:** `backend/app/main.py:57-63`, `backend/app/core/config.py:21`
- **Impact:** Required configuration step with no documentation warning. A wrong `FRONTEND_URL` env var silently breaks the app with opaque CORS errors.
- **Fix approach:** Add validation in startup to warn if `frontend_url` appears to be a development URL when not in development mode.

### Session Token — No Revocation / Rotation
- **Issue:** JWT session tokens (`backend/app/core/auth.py:19-25`) have no revocation mechanism. The `logout` endpoint (`backend/app/api/auth.py:371-374`) simply deletes the cookie client-side. The token remains valid until its expiration (`SESSION_DURATION_HOURS`, default 24 hours).
- **Files:** `backend/app/core/auth.py:19-25`, `backend/app/api/auth.py:371-374`
- **Impact:** Logout doesn't actually invalidate the session. A stolen token can be used for up to 24 hours. There's no token blacklist or refresh mechanism.
- **Fix approach:** Maintain a server-side token blacklist (Redis or DB table of revoked JWT IDs), or use short-lived tokens with refresh tokens.

## Known Bugs

### `POST /api/auth/login` — `limiter.limit` Applied But `request` Not Used
- **Issue:** The `login` endpoint has `@limiter.limit("5/minute")` and accepts `request: Request` as a parameter, but FastAPI's dependency injection requires SlowAPI's `Limiter` to be injected as a dependency for the per-route limit to actually work with the `request` parameter. The `limiter` object is initialized at module level (`backend/app/api/auth.py:23`) instead of being passed from the app instance.
- **Files:** `backend/app/api/auth.py:23, 113-114, 148-149`
- **Impact:** Per-route rate limiting on auth endpoints may not function as intended. The auth module creates its own `Limiter(key_func=get_remote_address)` which is a separate instance from the one in `main.py`. SlowAPI's `@limiter.limit()` decorators use the module-level instance, not the app-level one.
- **Trigger:** Attempt more than 5 rapid requests to `/api/auth/login` or `/api/auth/verify-otp`.

### GitHub Webhook — No `context` or `comment` Type Filtering
- **Issue:** The webhook endpoint (`backend/app/api/webhooks.py:27-32`) accepts both `"pull_request"` and `"pull_request_review"` events. For `"pull_request_review"`, there's no filtering on the `action` field, meaning `submitted`, `edited`, and `dismissed` review events all trigger a full review run. This can result in duplicate reviews when a reviewer leaves a comment (which triggers `pull_request_review`).
- **Files:** `backend/app/api/webhooks.py:27-32`
- **Impact:** Unnecessary API calls to GitHub and duplicate review runs for the same PR.
- **Trigger:** Any `pull_request_review` event type, regardless of action.

### `github_connect=true` — State Pollution on OAuth Redirect
- **Issue:** The GitHub connect callback (`backend/app/api/auth.py:302`) appends `?github_connect_needed=true` to the frontend redirect URL. The frontend's `AuthCallback` component (`frontend/src/pages/AuthCallback.tsx`) checks for `exchange_token` in query params but does not handle `github_connect_needed=true` — this flag is effectively dead and may trigger React warnings or unexpected behavior.
- **Files:** `backend/app/api/auth.py:302`, `frontend/src/pages/AuthCallback.tsx`
- **Impact:** The `github_connect_needed` parameter is sent to the frontend but never consumed. It's unclear if this was intended to trigger a redirect to the GitHub connect flow.
- **Trigger:** Login via GitHub OAuth.

### `print()` Statements in Console Logging
- **Issue:** The `_send_smtp_sync` function in `backend/app/core/email.py:43` calls `logger.info("OTP for %s: %s", to_email, code)` when SMTP fails. When `settings.smtp_host == "console"`, the same log line is written (`backend/app/core/email.py:49`). In production with a real SMTP server, if SMTP fails, the OTP is logged as a fallback — this is a PII leak risk.
- **Files:** `backend/app/core/email.py:42-43, 48-50`
- **Impact:** In production, if SMTP is configured but temporarily unavailable, OTP codes are logged in plaintext. If log aggregation systems are not carefully access-controlled, email-bound OTP codes are exposed to anyone with log access.
- **Trigger:** SMTP failure after a real SMTP server has been configured.

## Security Considerations

### GitHub Token Scope Not Enforced at the API Level
- **Issue:** The `require_scope` dependency (`backend/app/core/auth.py:49-63`) checks whether the user's stored GitHub token has the required OAuth scopes. However, the `GitHubClient` (`backend/app/integrations/github_client.py`) uses whichever token is available (user-specific or app-level `github_private_key`) without enforcing that the token actually has the scopes needed for the operation. The scope check only happens for endpoints that use `require_scope`, not for webhook-triggered reviews.
- **Files:** `backend/app/core/auth.py:49-63`, `backend/app/integrations/github_client.py:7-14`, `backend/app/api/webhooks.py:87-91`
- **Risk:** Webhook-triggered reviews pick the most recent GitHub token (`backend/app/api/webhooks.py:87-90`) without scope verification. If that token's scopes don't include `pull_requests:read`, the PR diff fetch will fail with a 401.
- **Current mitigation:** The `fetch_pr_and_diff` method handles 401 explicitly (`backend/app/integrations/github_client.py:29-30`), but raises a `RuntimeError` instead of trying the next available token.
- **Recommendations:** Implement token fallback (try user tokens, then app-level key) and add scope-aware token selection.

### `encrypt()` / `decrypt()` — Static Key Without Rotation
- **Issue:** The encryption key (`ENCRYPTION_KEY`) is loaded once at startup and never rotated. If a key is compromised, all encrypted tokens (`UserToken.encrypted_token` and `UserAIConfig.encrypted_api_key`) are decryptable. There's no key versioning or re-encryption support.
- **Files:** `backend/app/core/crypto.py:7-33`
- **Risk:** A compromised ENCRYPTION_KEY exposes all stored GitHub tokens and LLM API keys. No rotation mechanism exists without a data migration.
- **Current mitigation:** Key is 32-byte random base64 (AES-256-GCM), nonce is fresh per encryption.
- **Recommendations:** Add key ID prefix to ciphertexts so keys can be rotated. Implement a re-encryption endpoint or migration command.

### `GitHubClient` — Token Leakage via Error Messages
- **Issue:** When `GitHubClient.fetch_pr_and_diff` encounters a 401, it raises `RuntimeError("GitHub authentication failed. Token may be invalid or expired.")` (`backend/app/integrations/github_client.py:29-30`). If this exception propagates up uncaught (e.g., through `backend/app/api/webhooks.py:96-99`), the error message is returned to the caller in the 502 response. The token itself is not leaked, but token validity state is exposed.
- **Files:** `backend/app/integrations/github_client.py:26-30`, `backend/app/api/webhooks.py:95-99`, `backend/app/api/review.py:42-45`
- **Risk:** Information disclosure about token state. The 502 response from `webhooks.py:99` includes the exception message in `f"Failed to fetch PR diff: {e}"`.
- **Current mitigation:** Generic error wrapping is used, but exception messages contain auth state details.
- **Recommendations:** Sanitize exception messages before returning to the caller. Log the detailed error server-side.

### OAuth State Token — In-Memory Only
- **Issue:** OAuth state tokens are stored in memory via `TTLCache` (`backend/app/api/auth.py:32-33`). If the server restarts, all pending OAuth flows fail. For a single-process deployment this is acceptable, but for multi-process or horizontally scaled deployments, state verification will randomly fail.
- **Files:** `backend/app/api/auth.py:32, 186, 201, 245, 259, 308, 323`
- **Risk:** OAuth login failures after server restart. Not horizontally scalable.
- **Current mitigation:** TTL is 10 minutes, which is reasonable but in-memory.
- **Recommendations:** Use a database-backed or Redis-backed state store for production deployments.

### Webhook Secret Storage — Plaintext in Database
- **Issue:** Repository webhook secrets are stored as plaintext in `Repository.webhook_secret` (`backend/app/models/repository.py:16`). These secrets provide authenticated access to the webhook endpoint and are generated with `secrets.token_hex(32)`.
- **Files:** `backend/app/models/repository.py:16`, `backend/app/api/repos.py:88, 116, 123`
- **Risk:** A database breach exposes webhook secrets, allowing attackers to send forged webhook payloads. Since webhook verification uses HMAC-SHA256, a known secret enables signature forgery.
- **Current mitigation:** Generated with `secrets.token_hex(32)` (cryptographically random).
- **Recommendations:** Encrypt `webhook_secret` using the same AES-256-GCM mechanism used for `encrypted_token`. Decrypt only when verifying signatures.

## Performance Bottlenecks

### Diff Parser — Line-by-Line String Processing
- **Problem:** `parse_diff()` (`backend/app/review_engine/diff_parser.py:35-110`) processes diffs line-by-line as plain strings, constructing intermediate arrays and joining them repeatedly. For large diffs (approaching `MAX_DIFF_SIZE` = 5000 chars), this creates many temporary string objects.
- **Files:** `backend/app/review_engine/diff_parser.py`
- **Cause:** Naive `split("\n")`, per-line string slicing (`line[6:]`, `line.lstrip("+")`), and repeated `"\n".join()` for hunk content.
- **Improvement path:** Use `io.StringIO` for streaming, reduce allocations in tight loops, or rewrite using a state-machine parser that emits hunks as generators.

### Webhook Handler — Sequential PR + Diff Fetching
- **Problem:** `GitHubClient.fetch_pr_and_diff()` (`backend/app/integrations/github_client.py:19-47`) makes two sequential HTTP requests to GitHub — first for PR metadata, then for the diff. These could be parallelized.
- **Files:** `backend/app/integrations/github_client.py:19-47`
- **Cause:** Two separate `async with httpx.AsyncClient()` blocks run sequentially.
- **Improvement path:** Use `asyncio.gather()` to fetch both simultaneously. The PR metadata fetch is cheap (needed for the response), while the diff fetch is expensive.

### Database — `create_all` on Startup
- **Problem:** `Base.metadata.create_all` is called on every startup (`backend/app/main.py:30-31`). While this is idempotent (it's a "create if not exists"), it requires schema introspection queries against the database on every boot.
- **Files:** `backend/app/main.py:28-33`
- **Cause:** Dev convenience pattern that was never replaced with Alembic migrations for production.
- **Improvement path:** Remove `create_all` from the startup path. Use Alembic migrations with a `check` command on startup to warn if migration is needed.

### Findings Serialization — Repeated Dict Construction
- **Problem:** The PR detail endpoint (`backend/app/api/prs.py:66-77`) recomputes `file_risk` from the findings list on every request, using a dictionary comprehension with inline calculation. The same pattern exists in the findings list endpoint (`backend/app/api/prs.py:94-107`).
- **Files:** `backend/app/api/prs.py:66-107`
- **Cause:** No caching layer. Every PR detail page load re-queries and re-serializes all findings.
- **Improvement path:** Add server-side caching (in-memory or Redis) for PR detail and dashboard summary endpoints, with cache invalidation on new review runs.

## Fragile Areas

### Analyzer System — String-Based Regex Matching
- **Files:** `backend/app/review_engine/analyzers/security.py`, `backend/app/review_engine/analyzers/reliability.py`, `backend/app/review_engine/analyzers/performance.py`, `backend/app/review_engine/analyzers/testing.py`
- **Why fragile:** All four analyzers operate on raw diff text using regex patterns and string matching (`".all()" in line`, `"eval(" in line`). This is inherently language-agnostic but produces high false-positive rates. The patterns don't account for string literals (e.g., a comment `# eval is dangerous` triggers a finding), commented-out code, or language-specific syntax.
- **Safe modification:** Any change to analyzer patterns must be tested against a corpus of known diffs to measure precision/recall impact. Currently no test corpus exists.
- **Test coverage:** Zero. These are the most logic-dense files in the review engine and have no tests.

### LLM Analyzer — 8KB Chunk Boundary
- **Files:** `backend/app/review_engine/analyzers/llm.py:23-33`
- **Why fragile:** The LLM analyzer splits file content into 8KB chunks (`chunk_max = 8000`). If a chunk boundary falls in the middle of a function or logical block, the LLM receives incomplete context and may produce misleading findings. There's no overlap between chunks, no attempt to align boundaries with function boundaries.
- **Safe modification:** Wrap chunking in a testable function. Validate against multi-function files to ensure logical coherence.
- **Test coverage:** None.

### GitHub API Client — No Retry on Non-429 Errors
- **Files:** `backend/app/integrations/github_client.py:19-47`
- **Why fragile:** The GitHub client has no retry logic for transient errors (5xx, connection reset, DNS failures). Only the LLM client has retry logic (`backend/app/integrations/llm_client.py:28-51`). A brief GitHub API outage causes permanent webhook review failures.
- **Safe modification:** Add retry with exponential backoff for 5xx and connection errors, similar to the pattern in `llm_client.py:28-51`.

### `_PrContext` — Minimal Abstraction
- **Files:** `backend/app/review_engine/__init__.py:11-15`
- **Why fragile:** The `_PrContext` class has only two fields (`diff_text`, `title`) but the analyzers call `getattr(pr, "diff_text", "")` to access them (`backend/app/review_engine/analyzers/security.py:28`), suggesting the interface is implicitly duck-typed. If a new field is needed (e.g., `pr_description`), all analyzers must be updated individually.
- **Safe modification:** Convert `_PrContext` to a proper typed dataclass with all known fields, and have analyzers accept typed parameters instead of duck-typed objects.

## Scaling Limits

### Database — Single-User Token Scoping
- **Current capacity:** The webhook handler (`backend/app/api/webhooks.py:87-90`) selects `UserToken` where `provider == "github"` without filtering by user. In a multi-tenant deployment with multiple users, the most recent token from any user is used for webhook-triggered reviews.
- **Limit:** When multiple users install the same repository, the webhook uses a random user's token (the most recently created one across all users). If that user's token is revoked, all webhook reviews for that repo fail.
- **Scaling path:** The `Repository` model should store a reference to the `UserToken` or `User` that installed it, so webhook reviews always use the installer's token.

### Session Storage — In-Memory Only
- **Current capacity:** Auth sessions are JWT-based (stateless) so this is not a problem for session data. However, OAuth state tokens (`OAUTH_STATES`) and exchange tokens (`EXCHANGE_TOKENS`) are stored in `TTLCache` in memory with fixed max sizes (10000 and 1000 respectively).
- **Limit:** 1000 concurrent exchange tokens. With a 60-second TTL, this means 1000 logins per minute max before tokens start getting evicted. For a single-server deployment this is acceptable, but multiple workers won't share the cache.
- **Scaling path:** Move OAuth state and exchange token storage to a shared Redis instance for multi-worker deployments.

## Dependencies at Risk

### `passlib` — Deprecated Library
- **Risk:** passlib has been unmaintained since 2022. The `passlib.context.CryptContext` with bcrypt scheme works but may not receive security updates for new bcrypt vulnerabilities.
- **Impact:** Password hashing is core to the email-password auth flow. A bcrypt vulnerability would require migrating all password hashes.
- **Migration plan:** Move to `bcrypt` directly (the `bcrypt` package) or use FastAPI's built-in password utilities if they become available.

### `slowapi` — Niche Rate Limiting Library
- **Risk:** slowapi has limited community adoption and infrequent releases. It's tied to older versions of FastAPI internals. There are known issues with per-route limiters when used with dependency injection.
- **Impact:** Rate limiting may not work correctly across all endpoints, as evidenced by the auth module's separate `Limiter` instance (`backend/app/api/auth.py:23`).
- **Migration plan:** Replace with a middleware-based rate limiter (e.g., `fastapi-limiter` with Redis backend, or add rate limiting at the reverse-proxy level with nginx).

## Missing Critical Features

### No Password Reset Flow
- **Problem:** Email-password registration and login exist, but there's no password reset endpoint. Users who forget their password have no way to regain access.
- **Blocks:** User self-service for password recovery. Admin intervention required.

### No Repository-Level Token Association
- **Problem:** When a user installs a repo (`backend/app/api/repos.py:69-127`), the webhook callback uses the installing user's token. But the `Repository` model has no `user_id` or `token_id` field to track who installed it, so webhook-triggered reviews (`backend/app/api/webhooks.py:87-90`) use the most recent token from any user.
- **Blocks:** Multi-user review reliability. When the installing user revokes their GitHub token, webhook reviews silently fail for the entire repository.

### No Token Health Monitoring
- **Problem:** If a user's GitHub token is revoked or expires, the system only detects it when an API call fails with a 401. There's no background job to check token health or proactively notify users.
- **Blocks:** User experience — the first sign of trouble is a failed PR review with a generic error message.

### No Performance / Load Testing
- **Problem:** The `backend/app/review_engine/__init__.py:25-27` has a hard cap (`MAX_DIFF_SIZE = 5000 chars`) that rejects diffs exceeding this size. There's no load testing infrastructure to determine what review throughput the system can handle. For a production deployment, a single large PR with LLM analysis enabled could take 30+ seconds to process.
- **Blocks:** Production readiness without performance characterization.

## Test Coverage Gaps

### Untested Area: Diff Parser
- **What's not tested:** `backend/app/review_engine/diff_parser.py` — the core parsing logic. Handles diff headers (`diff --git`, `--- a/`, `+++ b/`, `@@ ... @@`), binary detection, rename detection, hunk splitting. No unit tests exist.
- **Files:** `backend/app/review_engine/diff_parser.py`
- **Risk:** A parser bug can cause all analyzers to miss findings or produce garbage. The try/except on line 88-94 silently swallows `ValueError`/`IndexError` during hunk line parsing.
- **Priority:** High

### Untested Area: All Four Analyzers
- **What's not tested:** `SecurityAnalyzer`, `ReliabilityAnalyzer`, `PerformanceAnalyzer`, `TestingAnalyzer`. Each has 50-110 lines of pattern-matching logic with multiple regex patterns, confidence scores, and edge case handling.
- **Files:** `backend/app/review_engine/analyzers/security.py`, `reliability.py`, `performance.py`, `testing.py`
- **Risk:** Regression on pattern changes. False-positive/true-positive ratio unknown.
- **Priority:** High

### Untested Area: Crypto Module
- **What's not tested:** `backend/app/core/crypto.py` — AES-256-GCM encryption/decryption. Any bug here would silently corrupt stored tokens.
- **Files:** `backend/app/core/crypto.py`
- **Risk:** Token corruption = permanent loss of GitHub access. No way to recover encrypted data without the key.
- **Priority:** High

### Untested Area: Auth / Session Handling
- **What's not tested:** `backend/app/core/auth.py`, `backend/app/api/auth.py` — JWT creation/verification, OAuth flows, OTP verification, cookie setting. This is 374 lines of security-critical code.
- **Files:** `backend/app/core/auth.py`, `backend/app/api/auth.py`
- **Risk:** Auth bypass, session hijacking, OTP brute force.
- **Priority:** High

### Untested Area: Risk Score Calculation
- **What's not tested:** `backend/app/scoring/risk.py` — the `calculate_risk_score` function.
- **Files:** `backend/app/scoring/risk.py`
- **Risk:** Incorrect risk scoring undermines the entire review UI, which displays risk scores prominently.
- **Priority:** Medium

---

*Concerns audit: 2026-05-29*
