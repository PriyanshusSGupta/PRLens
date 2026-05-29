# Testing Patterns

**Analysis Date:** 2026-05-29

## Test Framework

### Backend (Python)

**Framework:** **Not configured.** No test framework detected.

- `pyproject.toml` has empty `[dependency-groups] dev = []` — no pytest, no test runner installed
- No `pytest.ini`, `conftest.py`, `tox.ini`, or `setup.cfg` detected
- No `test` directory with actual tests — `backend/tests/` contains only an empty `__init__.py`

### Frontend (TypeScript)

**Framework:** **Not configured.** No test framework detected.

- `package.json` has no test-related dependencies — no Vitest, no Jest, no Playwright, no Testing Library
- No `vitest.config.*` or `jest.config.*` detected
- No `test` or `spec` files exist anywhere in the frontend

### CI/CD

- `.github/workflows/pr-coverage.yml` references a custom shell script `.wednesday/scripts/pr-coverage.sh` that runs coverage, but no test tool is installed to generate actual coverage data
- `.github/workflows/commit-lint.yml` — only enforces commit message format, not tests
- `.github/workflows/pr-sonar.yml` — SonarQube analysis, requires tests to exist

**Test Framework:**
- **Runner:** Not detected (none installed)
- **Config:** N/A
- **Assertion Library:** N/A

**Run Commands:**
```bash
# No test commands exist. No scripts/test target in package.json or pyproject.toml
```

## Test File Organization

**Location:**
- Backend: `backend/tests/` (empty — only `__init__.py`)
- Frontend: No test directories or test files found anywhere

**Naming:**
- No convention exists (no `.test.*` or `.spec.*` files in the repository)

**Structure:**
```
backend/tests/
  __init__.py           # Empty — placeholder only
```

No test subdirectories, no fixtures, no test data factories.

## Test Structure

**No existing tests to analyze.** The codebase has zero test coverage across both backend and frontend.

### Observed Testing Gaps

**Backend areas without tests:**
- `backend/app/api/auth.py` (374 lines) — complex OAuth flows, OTP verification, session management
- `backend/app/api/review.py` (101 lines) — core review orchestration with external GitHub API
- `backend/app/api/webhooks.py` (129 lines) — webhook signature verification, PR processing
- `backend/app/api/repos.py` (158 lines) — GitHub API interactions for repo installation
- `backend/app/review_engine/__init__.py` (56 lines) — review orchestration and policy filtering
- `backend/app/review_engine/diff_parser.py` (110 lines) — diff parsing with multiple edge cases
- `backend/app/scoring/risk.py` (14 lines) — risk calculation logic
- `backend/app/integrations/llm_client.py` (64 lines) — LLM API client with retry logic
- `backend/app/integrations/github_client.py` (87 lines) — GitHub API client
- `backend/app/core/crypto.py` (33 lines) — AES-256-GCM encryption/decryption
- `backend/app/core/auth.py` (64 lines) — JWT session token creation/verification
- `backend/app/core/passwords.py` (12 lines) — bcrypt password hashing
- `backend/app/core/security.py` (12 lines) — webhook signature verification
- All 5 analyzers in `backend/app/review_engine/analyzers/` (combined ~403 lines)

**Frontend areas without tests:**
- All 8 page components in `frontend/src/pages/`
- All 5 components in `frontend/src/components/`
- All 3 hooks in `frontend/src/hooks/`
- `frontend/src/lib/api.ts` — Axios instance configuration

## Mocking

**Framework:** Not configured. No mocking library installed.

**No existing mocking patterns to reference.**

### What Should Be Mocked (based on codebase architecture):
- **External HTTP calls:** `httpx.AsyncClient` in `github_client.py`, `llm_client.py`, `auth.py` (OAuth callbacks), `repos.py` (GitHub API)
- **Database sessions:** SQLAlchemy `AsyncSession` in all route handlers
- **LLM API responses:** `LLMClient.generate()` in `llm.py` analyzer
- **Crypto operations:** `encrypt()`/`decrypt()` in token handling
- **SMTP email:** `send_otp()` in auth flows
- **GitHub API:** All calls to `api.github.com`
- **Frontend API calls:** Axios instance in `api.ts` for all hooks

### What Should NOT Be Mocked:
- Analyzer logic (security, reliability, performance, testing) — these are pure functions operating on string input
- `diff_parser.py` — operates on text input, no external dependencies
- `scoring/risk.py` — pure calculation
- `policy.py` — dataclass construction from settings

## Fixtures and Factories

**No existing test data fixtures.** No factory patterns detected.

### Recommended Fixtures (based on model schema):
- User factory (email, password hash, auth_provider, verification status)
- PullRequest factory (repo_id, pr_number, title, author, risk_score)
- Finding factory (pr_id, severity, category, file_path, confidence)
- Repository factory (owner, name, full_name, webhook_id)
- Diff text fixtures (sample unified diffs for parser testing)
- OAuth callback payloads (mock GitHub/Google user data)

## Coverage

**Requirements:** None enforced. No coverage tool configured.

**View Coverage:**
```bash
# No coverage commands exist. CI script `.wednesday/scripts/pr-coverage.sh` is defined but no test tool is installed.
```

## Test Types

### Unit Tests
- **Status:** None exist
- **High-value candidates:** All analyzers (parse diff, run pattern matching), `diff_parser.py`, `scoring/risk.py`, `core/crypto.py`, `core/auth.py` (JWT), `core/passwords.py`, `core/security.py`

### Integration Tests
- **Status:** None exist
- **High-value candidates:** API route handlers with mocked DB sessions, `github_client.py` with mocked HTTP, `llm_client.py` with mocked HTTP

### E2E Tests
- **Framework:** Not used
- **Status:** None exist

## Common Patterns

**No existing test patterns to follow.** When adding tests, the following conventions should be established:

### For Backend (Python + pytest):
```python
# Suggested pattern — no existing example
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_security_analyzer_detects_hardcoded_secrets():
    analyzer = SecurityAnalyzer()
    pr = _PrContext(diff_text='+API_KEY = "abc123"', title="test")
    findings = await analyzer.analyze(pr)
    assert len(findings) == 1
    assert findings[0]["severity"] == "critical"
```

### For Frontend (TypeScript + Vitest):
```typescript
// Suggested pattern — no existing example
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import SeverityBadge from './SeverityBadge';

describe('SeverityBadge', () => {
  it('renders critical severity with correct color', () => {
    render(<SeverityBadge severity="critical" />);
    expect(screen.getByText('CRITICAL')).toBeDefined();
  });
});
```

---

*Testing analysis: 2026-05-29*
