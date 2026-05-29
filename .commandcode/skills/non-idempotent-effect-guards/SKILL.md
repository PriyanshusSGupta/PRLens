---
name: non-idempotent-effect-guards
description: Audits code for non-idempotent side effects that break under double-invocation. Use when reviewing React effects (StrictMode), API endpoints (retry safety), single-use tokens, redirects in async callbacks, destructive state mutations, or any pattern where a second call produces different results than the first. Triggers on "check React effects", "StrictMode bugs", "API idempotency", "double-firing bugs", "non-idempotent effects", "StrictMode hardening".
---

# Non-Idempotent Effect Guards

## Overview

A non-idempotent effect is any operation that produces a different result or destroys state when called more than once. These bugs survive unit tests (which mount/fire once) and static analysis (which traces single paths). They only surface in production or StrictMode — where effects, hooks, and network calls can fire twice.

**The rule:** If calling something twice can fail, corrupt state, or redirect away, guard it.

## When to Use

- Reviewing any `useEffect` that calls an external API, stores data, or navigates
- Auditing React components in StrictMode (dev mode double-mounts effects)
- Before deploying any OAuth flow, payment flow, or single-use token exchange
- When logs show duplicated API calls or "400 Bad Request" after a "200 OK" on the same endpoint
- Auditing any POST endpoint that mutates state without idempotency protection

## The Four Bug Patterns

### Pattern 1: React useEffect Without Dedup Guard

**Symptom:** POST endpoint returns 200 then 400 on the same request. Token consumed. Redirect loops. State corruption.

**Root cause:** React StrictMode mounts → unmounts → re-mounts every component in development. Effects fire twice. Without a guard, the effect's side effect (API call, token exchange, redirect) executes twice.

**Fix:** Use a `useRef` boolean as a gate:

```tsx
// BROKEN: Effect fires twice in StrictMode, token consumed
useEffect(() => {
  api.post('/auth/exchange', { token }).then(navigate('/'));
}, [token]);

// FIXED: Guard prevents double invocation
const startedRef = useRef(false);

useEffect(() => {
  if (startedRef.current) return;
  startedRef.current = true;
  api.post('/auth/exchange', { token }).then(navigate('/'));
}, [token]);
```

**Also valid for non-destructive reads:** Add a cleanup function to abort in-flight requests:

```tsx
useEffect(() => {
  const controller = new AbortController();
  api.get('/data', { signal: controller.signal }).then(setData);
  return () => controller.abort();
}, []);
```

### Pattern 2: Destructive Backend State Without Idempotency Key

**Symptom:** Client retries a POST (network timeout, React re-mount) and gets 400/409 because state was already consumed.

**Root cause:** The backend mutates state destructively (`.pop()`, `used=True`, deletes a record) on first use and has no way to detect replays.

**Fix patterns:**

**Option A — Destructive read (single-use tokens):**
```python
# BROKEN: Second caller gets None, 400 error
EXCHANGE_TOKENS: TTLCache = TTLCache(ttl=60)
user_id = EXCHANGE_TOKENS.pop(token, None)  # Destroyed on first call

# FIXED: Replay-aware — returns the same result for the same key
EXCHANGE_TOKENS: TTLCache = TTLCache(ttl=60)
user_id = EXCHANGE_TOKENS.get(token)  # Non-destructive — survives
if user_id:
    EXCHANGE_TOKENS.pop(token, None)  # Cleanup only after successful use
```

**Option B — Idempotency key (mutations):**
```python
# BROKEN: Creates duplicate on retry
@router.post("/orders")
async def create_order(body: CreateOrderBody):
    order = Order(...)
    db.add(order)

# FIXED: Idempotency key prevents duplicates
@router.post("/orders")
async def create_order(body: CreateOrderBody, request: Request):
    key = request.headers.get("Idempotency-Key")
    if key and await db.execute(select(Order).where(Order.idempotency_key == key)):
        return existing
    order = Order(idempotency_key=key, ...)
```

**Option C — State machine (OTP codes, verification):**
```python
# BROKEN: used=True prevents replay, but second caller gets 400
otp.used = True

# FIXED: Detect replay and return success if already verified
if otp.used:
    return {"status": "already_verified"}  # Idempotent success response
otp.used = True
```

### Pattern 3: `window.location.href` in Async Callbacks

**Symptom:** Navigation fires twice, browser races, user lands on wrong page or sees a flash.

**Fix:** Guard with a ref:

```tsx
const redirectingRef = useRef(false);
const handleOAuth = async (provider: string) => {
  if (redirectingRef.current) return;
  redirectingRef.current = true;
  const res = await api.get(`/auth/${provider}/login`);
  window.location.href = res.data.redirect_url;
};
```

### Pattern 4: Router Callbacks Without Re-Entry Protection

**Symptom:** Navigating to a callback route fires the effect multiple times — component mounts, unmounts, remounts.

**Fix:** Pattern 1 guard + graceful fallback if operation already succeeded:

```tsx
useEffect(() => {
  if (startedRef.current) return;
  startedRef.current = true;
  api.post('/auth/exchange', { token })
    .then(navigate('/'))
    .catch(() => {
      api.get('/auth/me').then(() => navigate('/')).catch(showError);
    });
}, [token]);
```

## The Audit Process

### Step 1: Scan for Non-Idempotent Operations

Walk the codebase and find every:

- `useEffect` that calls `fetch`/`axios`/`api.*` — tag as potential double-fire
- `window.location.href =` or `window.location.replace()` inside async callbacks — tag
- `.pop()` on caches, dicts, or collections — tag as destructive read
- `OTPCode.used = True`, `DELETE` queries, state transitions — tag as mutable state
- `setTimeout(() => navigate(...))` — tag as async redirect

### Step 2: Classify Each Finding

| Finding | Pattern | Severity |
|---------|---------|----------|
| POST/PUT with destructive state, no replay detection | Pattern 2 | Critical |
| `useEffect` with API call, no `useRef` guard | Pattern 1 | Critical |
| `window.location.href` in async callback, no guard | Pattern 3 | High |
| Route callback effect depending on params, no re-entry check | Pattern 4 | High |
| POST with no idempotency key where retry is likely | Pattern 2 | Medium |
| `useEffect` without cleanup for in-flight requests | Pattern 1 | Medium |

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It only fires twice in dev, not production" | StrictMode double-rendering catches bugs in dev that would surface in production as race conditions from fast clicks, network retries, or React concurrent features. |
| "useCallback/useMemo will fix it" | Memoization prevents re-creation of values, not re-invocation of effects. A memoized function called inside an unguarded `useEffect` still fires twice. |
| "The API call is idempotent anyway" | GET requests are idempotent. POST/PUT/DELETE may not be. Token exchanges, payments, and state transitions are NOT idempotent by default. |
| "I'll just disable StrictMode" | StrictMode is a debugging tool. The bugs it reveals are real — they'll surface in production under concurrent rendering or fast user actions. |

## Red Flags

- `useEffect` with `fetch`/`axios` and no cleanup function
- `useEffect` with `window.location` assignment and no guard
- Backend endpoint with `.pop()` or `used=True` and no replay detection
- Client retries producing 400/409 after a successful operation
- Logs showing paired 200+400 on the same request in quick succession
- Any single-use construct (tokens, OTP codes, nonces) without graceful replay handling

## Verification

After hardening:

- [ ] Effects with side effects have `useRef` guards or cleanup functions
- [ ] Backend destructive operations have replay detection
- [ ] POST endpoints are either idempotent or have idempotency keys
- [ ] Token exchanges survive double-invocation gracefully
- [ ] OAuth callbacks handle re-entry without errors
- [ ] App works correctly when running under React StrictMode
