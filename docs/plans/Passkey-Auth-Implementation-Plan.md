# Passkey Authentication — TDD Phased Implementation Plan

_March 2026_

## Overview

Add single-user passkey (WebAuthn) authentication to GTD TODOs using `py_webauthn` and `itsdangerous` for session management. After implementation, every route except `/health` and `/login` requires an authenticated session. A single owner account is established during first-run setup.

### Key Design Decisions

| Decision | Choice |
|---|---|
| **Auth scope** | Single user (the owner) |
| **Credential type** | Passkeys via WebAuthn (passwordless) |
| **Session mechanism** | Signed cookie via `itsdangerous` |
| **Libraries** | `py_webauthn` for WebAuthn, `itsdangerous` for cookie signing |
| **Registration flow** | One-time setup on first visit when no credentials exist |
| **Login flow** | Passkey challenge → browser authenticator → verify → set session cookie |
| **Protected surface** | All routes except `/health`, `/auth/*`, and `/static/*` |
| **Auth bypass for dev/test** | `AUTH_DISABLED=true` env var skips middleware (used in existing tests) |
| **Database changes** | New `webauthn_credentials` table; no changes to existing tables |

### New Dependencies

```
py-webauthn>=2.0,<3.0
itsdangerous>=2.0,<3.0
```

### New Configuration (Environment Variables)

| Variable | Purpose | Default |
|---|---|---|
| `AUTH_DISABLED` | Disable auth entirely (for local dev / existing tests) | `false` |
| `AUTH_SECRET_KEY` | Secret for signing session cookies | *required in production* |
| `AUTH_SESSION_MAX_AGE` | Session cookie max age in seconds | `604800` (7 days) |
| `WEBAUTHN_RP_ID` | WebAuthn Relying Party ID (domain) | `localhost` |
| `WEBAUTHN_RP_NAME` | Human-readable RP name | `GTD TODOs` |
| `WEBAUTHN_ORIGIN` | Expected origin for WebAuthn ceremonies | `http://localhost:8080` |

---

## Phase Structure

Each phase follows the project's existing TDD conventions:

1. Write or update failing tests
2. Implement minimum code to pass
3. Verify all existing tests still pass
4. Update docs and `.github` assets if behavior changed

---

## Phase 1 — Auth Model, Config & `AUTH_DISABLED` Bypass

**Goal:** Add the `WebAuthnCredential` model, extend `Settings`, and wire an auth middleware that is disabled by default so all existing tests continue to pass unchanged.

### New / Changed Files

| File | Change |
|---|---|
| `app/models.py` | Add `WebAuthnCredential` table model |
| `app/config.py` | Add auth-related settings fields |
| `app/auth.py` | New module: session helpers, `require_auth` middleware |
| `app/main.py` | Register auth middleware |
| `pyproject.toml` | Add `py-webauthn`, `itsdangerous` dependencies |

### Model: `WebAuthnCredential`

```python
class WebAuthnCredential(SQLModel, table=True):
    __tablename__ = "webauthn_credentials"

    id: int | None = Field(default=None, primary_key=True)
    credential_id: bytes          # unique identifier from authenticator
    public_key: bytes             # stored public key
    sign_count: int = 0           # replay-attack counter
    created_at: datetime = Field(default_factory=utc_now)
```

### Tests (`tests/test_auth_model.py`)

1. **`test_credential_table_created`** — After `init_db`, the `webauthn_credentials` table exists in SQLite.
2. **`test_credential_round_trip`** — Insert a `WebAuthnCredential` row, read it back, verify all fields.
3. **`test_auth_disabled_allows_all_routes`** — With `AUTH_DISABLED=true`, `GET /inbox` returns 200 (no login required). This confirms existing behavior is preserved.
4. **`test_settings_includes_auth_fields`** — `get_settings()` includes `auth_disabled`, `auth_secret_key`, `webauthn_rp_id`, etc.
5. **`test_existing_tests_unaffected`** — (Implicit: run the full existing suite with `AUTH_DISABLED=true`.)

### Acceptance Criteria

- [ ] `uv run pytest` passes with all existing tests green
- [ ] New `webauthn_credentials` table is created by `init_db()`
- [ ] Auth middleware is registered but is a no-op when `AUTH_DISABLED=true`
- [ ] `conftest.py` sets `AUTH_DISABLED=true` so existing tests are unaffected

---

## Phase 2 — Auth Middleware (Enforcement Mode)

**Goal:** When `AUTH_DISABLED=false` and no session cookie is present, all protected routes redirect to `/auth/login`. Unauthenticated requests to API/export routes return 401.

### New / Changed Files

| File | Change |
|---|---|
| `app/auth.py` | Implement session cookie verification, redirect/401 logic |
| `app/main.py` | No changes (middleware already registered) |

### Middleware Behavior

```
Request → Is path exempt? (/health, /auth/*, /static/*) → Allow
        → Has valid signed session cookie?               → Allow
        → Is HTML request?                                → 302 → /auth/login
        → Is API/JSON request?                            → 401
```

### Session Cookie

- Name: `gtd_session`
- Value: `itsdangerous.TimestampSigner`-signed payload containing `{"authenticated": true}`
- `HttpOnly`, `SameSite=Lax`, `Secure` (when origin is HTTPS)
- Max age from `AUTH_SESSION_MAX_AGE`

### Tests (`tests/test_auth_middleware.py`)

All tests in this file use `AUTH_DISABLED=false` and **no** credentials in the DB.

1. **`test_health_always_accessible`** — `GET /health` → 200 regardless of auth state.
2. **`test_static_always_accessible`** — `GET /static/app.css` → 200 regardless of auth state.
3. **`test_unauthenticated_html_redirects_to_login`** — `GET /inbox` without cookie → 302 to `/auth/login`.
4. **`test_unauthenticated_api_returns_401`** — `GET /api/tasks` without cookie → 401.
5. **`test_valid_session_cookie_allows_access`** — Manually set a valid signed `gtd_session` cookie → `GET /inbox` → 200.
6. **`test_expired_session_cookie_redirects`** — Set a cookie signed with an old timestamp beyond `AUTH_SESSION_MAX_AGE` → 302.
7. **`test_tampered_cookie_redirects`** — Set a cookie with an invalid signature → 302.
8. **`test_auth_disabled_skips_enforcement`** — With `AUTH_DISABLED=true`, unauthenticated `GET /inbox` → 200.

### Acceptance Criteria

- [ ] All existing tests still pass (they use `AUTH_DISABLED=true`)
- [ ] Phase 2 tests all pass
- [ ] No changes needed to any existing route handler

---

## Phase 3 — Registration (First-Run Setup)

**Goal:** When no credentials exist in the database, visiting any page redirects to `/auth/setup` where the owner registers a passkey. After setup, future visits go to `/auth/login`.

### New / Changed Files

| File | Change |
|---|---|
| `app/routes/auth.py` | New router: `/auth/setup`, `/auth/setup/options`, `/auth/setup/verify` |
| `app/services/auth_service.py` | New service: `has_credentials()`, `generate_registration_options()`, `verify_registration()` |
| `app/templates/auth_setup.html` | Setup page with JS to call `navigator.credentials.create()` |
| `app/main.py` | Register auth router |

### Routes

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/auth/setup` | Render setup page (only if no credentials exist) |
| `POST` | `/auth/setup/options` | Return `PublicKeyCredentialCreationOptions` JSON |
| `POST` | `/auth/setup/verify` | Verify registration response, store credential, set session cookie |

### Flow

```
First visit → middleware sees no credentials → redirect /auth/setup
           → Browser: navigator.credentials.create()
           → POST /auth/setup/verify → store credential → set cookie → redirect /inbox
```

### Tests (`tests/test_auth_registration.py`)

1. **`test_setup_page_renders_when_no_credentials`** — `GET /auth/setup` with empty DB → 200, contains expected HTML.
2. **`test_setup_redirects_to_login_when_credentials_exist`** — Insert a credential, `GET /auth/setup` → 302 to `/auth/login`.
3. **`test_setup_options_returns_valid_json`** — `POST /auth/setup/options` → 200, response contains `challenge`, `rp`, `user`.
4. **`test_setup_verify_stores_credential`** — `POST /auth/setup/verify` with a mocked valid registration response → credential row appears in DB, response sets `gtd_session` cookie.
5. **`test_setup_verify_rejects_invalid_response`** — `POST /auth/setup/verify` with malformed data → 400.
6. **`test_middleware_redirects_to_setup_when_no_credentials`** — With `AUTH_DISABLED=false` and no credentials, `GET /inbox` → 302 to `/auth/setup`.

### Mocking Strategy

The `py_webauthn` verification functions talk to no external service — they validate cryptographic signatures. Tests will:
- Use `unittest.mock.patch` to mock `verify_registration_response` from `py_webauthn` at the service layer.
- Provide a fixture that returns a realistic `VerifiedRegistration` object.

### Acceptance Criteria

- [ ] First-run setup flow works end-to-end (with mocked WebAuthn)
- [ ] After setup, the credential is persisted and a session cookie is set
- [ ] If credentials already exist, `/auth/setup` redirects to `/auth/login`
- [ ] Existing tests unaffected

---

## Phase 4 — Login (Passkey Authentication)

**Goal:** Returning users authenticate via passkey at `/auth/login`. On success, a session cookie is set and they are redirected to `/inbox`.

### New / Changed Files

| File | Change |
|---|---|
| `app/routes/auth.py` | Add `/auth/login`, `/auth/login/options`, `/auth/login/verify`, `/auth/logout` |
| `app/services/auth_service.py` | Add `generate_authentication_options()`, `verify_authentication()` |
| `app/templates/auth_login.html` | Login page with JS to call `navigator.credentials.get()` |

### Routes

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/auth/login` | Render login page |
| `POST` | `/auth/login/options` | Return `PublicKeyCredentialRequestOptions` JSON |
| `POST` | `/auth/login/verify` | Verify authentication response, update sign count, set cookie |
| `POST` | `/auth/logout` | Clear session cookie, redirect to `/auth/login` |

### Flow

```
GET /auth/login → page loads, JS fetches /auth/login/options
               → Browser: navigator.credentials.get()
               → POST /auth/login/verify → verify signature → set cookie → redirect /inbox
```

### Tests (`tests/test_auth_login.py`)

1. **`test_login_page_renders`** — `GET /auth/login` → 200, contains expected HTML.
2. **`test_login_options_returns_challenge_and_credentials`** — With a stored credential, `POST /auth/login/options` → 200, response JSON includes `challenge` and `allowCredentials` list.
3. **`test_login_verify_sets_session_and_redirects`** — `POST /auth/login/verify` with mocked valid authentication response → `gtd_session` cookie set, redirect to `/inbox`.
4. **`test_login_verify_updates_sign_count`** — After successful login, the credential's `sign_count` is incremented in the DB.
5. **`test_login_verify_rejects_invalid_response`** — Invalid authentication response → 400.
6. **`test_login_verify_rejects_replayed_sign_count`** — Authentication response with a `sign_count` ≤ stored value → 400.
7. **`test_logout_clears_cookie_and_redirects`** — `POST /auth/logout` → `gtd_session` cookie cleared, 302 to `/auth/login`.
8. **`test_login_redirects_to_setup_when_no_credentials`** — `GET /auth/login` with no credentials in DB → 302 to `/auth/setup`.

### Mocking Strategy

Same as Phase 3: mock `verify_authentication_response` from `py_webauthn` at the service layer.

### Acceptance Criteria

- [ ] Login flow works end-to-end (with mocked WebAuthn)
- [ ] Session cookie is set on successful authentication
- [ ] Sign count is validated and updated (replay protection)
- [ ] Logout clears the session
- [ ] Existing tests unaffected

---

## Phase 5 — UI Polish & Logout

**Goal:** Add a logout button to the app navigation, style the login/setup pages to match the existing design, and handle edge cases.

### New / Changed Files

| File | Change |
|---|---|
| `app/templates/base.html` | Add logout button/link in nav (only when authenticated) |
| `app/templates/auth_login.html` | Final styling pass |
| `app/templates/auth_setup.html` | Final styling pass |
| `app/static/auth.js` | Shared JS for WebAuthn browser API calls |
| `app/static/app.css` | Auth page styles |

### Tests (`tests/test_auth_ui.py`)

1. **`test_nav_shows_logout_when_authenticated`** — Authenticated `GET /inbox` → HTML contains logout form/link.
2. **`test_nav_hides_logout_when_auth_disabled`** — With `AUTH_DISABLED=true`, `GET /inbox` → HTML does **not** contain logout link.
3. **`test_login_page_is_styled`** — `GET /auth/login` → response includes `app.css` link and expected structure.
4. **`test_setup_page_is_styled`** — `GET /auth/setup` → response includes `app.css` link and expected structure.

### Acceptance Criteria

- [ ] Logout button visible in nav bar when authenticated
- [ ] Login and setup pages match the visual style of the rest of the app
- [ ] `auth.js` handles the `navigator.credentials` API calls and error display
- [ ] All tests pass

---

## Phase 6 — Integration Tests & Documentation

**Goal:** End-to-end integration tests for the full auth lifecycle, documentation updates, and `.github` asset updates.

### Tests (`tests/test_auth_integration.py`)

1. **`test_full_setup_then_login_lifecycle`** — No credentials → redirect to setup → mock register → cookie set → access `/inbox` → logout → redirect to login → mock login → cookie set → access `/inbox`.
2. **`test_second_passkey_registration_blocked`** — After setup, `GET /auth/setup` → redirects to login (cannot re-register).
3. **`test_auth_protects_all_page_routes`** — Parameterized test hitting every known page route without auth → all redirect to `/auth/login` (or `/auth/setup`).
4. **`test_auth_protects_all_api_routes`** — Parameterized test hitting every API/export route without auth → all return 401.
5. **`test_auth_disabled_env_bypasses_everything`** — With `AUTH_DISABLED=true`, all routes behave as before (regression safety net).

### Documentation Updates

| File | Change |
|---|---|
| `README.md` | Add auth section: setup flow, env vars, disabling for local dev |
| `docs/api.md` | Document auth endpoints |
| `.github/copilot-instructions.md` | Note auth config for future agent sessions |
| `.github/skills/todo-api/SKILL.md` | Add auth endpoints and cookie handling |
| `docker-compose.yml` | Add `AUTH_SECRET_KEY` env var (with generation instructions) |
| `Dockerfile` | No changes expected |

### Acceptance Criteria

- [ ] `uv run pytest` — all tests pass (existing + all new auth tests)
- [ ] `uv run ruff check .` — clean
- [ ] `uv run mypy app` — clean
- [ ] `docker build .` — succeeds
- [ ] Documentation is accurate and complete

---

## File Inventory (All Phases)

### New Files

| File | Phase |
|---|---|
| `app/auth.py` | 1 |
| `app/routes/auth.py` | 3 |
| `app/services/auth_service.py` | 3 |
| `app/templates/auth_setup.html` | 3 |
| `app/templates/auth_login.html` | 4 |
| `app/static/auth.js` | 5 |
| `tests/test_auth_model.py` | 1 |
| `tests/test_auth_middleware.py` | 2 |
| `tests/test_auth_registration.py` | 3 |
| `tests/test_auth_login.py` | 4 |
| `tests/test_auth_ui.py` | 5 |
| `tests/test_auth_integration.py` | 6 |

### Modified Files

| File | Phase(s) |
|---|---|
| `pyproject.toml` | 1 |
| `app/models.py` | 1 |
| `app/config.py` | 1 |
| `app/main.py` | 1, 3 |
| `tests/conftest.py` | 1 |
| `app/templates/base.html` | 5 |
| `app/static/app.css` | 5 |
| `docker-compose.yml` | 6 |
| `README.md` | 6 |
| `docs/api.md` | 6 |
| `.github/copilot-instructions.md` | 6 |
| `.github/skills/todo-api/SKILL.md` | 6 |

---

## Security Considerations

- **No passwords** — Passkeys are phishing-resistant and never leave the authenticator device.
- **Replay protection** — `sign_count` is validated on every login to detect cloned authenticators.
- **Cookie security** — `HttpOnly`, `SameSite=Lax`, `Secure` (HTTPS), cryptographically signed.
- **Challenge storage** — Short-lived challenges stored in server-side state (in-memory dict with TTL). Never reused.
- **Single-user constraint** — Registration is locked after the first credential is stored. No username/password attack surface.
- **AUTH_DISABLED safety** — Only active when explicitly set. Production deployments should never set this.
