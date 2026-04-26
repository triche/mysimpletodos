# API Key Authentication — TDD Phased Implementation Plan

_March 2026_

## Overview

Add API key authentication as an alternative credential for programmatic access to GTD TODOs. Users authenticate via passkey in the browser to reach a new **Settings** page, where they can generate, view, and revoke API keys. API requests include the key in an `Authorization: Bearer <key>` header. This enables CLI tools and scripts to interact with the API without a browser session.

### Key Design Decisions

| Decision | Choice |
|---|---|
| **Auth scope** | Same single owner — API keys are just an alternative credential |
| **Key format** | `gtd_<random-hex>` — 32-byte random token with a recognizable prefix |
| **Storage** | Store a SHA-256 hash of the key; never store the plaintext after creation |
| **Display** | Show the full key exactly once at creation time; after that only show a masked suffix |
| **Limit** | Allow up to 10 active keys (prevents unbounded growth, easy to raise later) |
| **Revocation** | Immediate — delete the row; subsequent requests with that key get 401 |
| **Header** | `Authorization: Bearer gtd_<hex>` |
| **Middleware change** | `AuthMiddleware` gains a second auth path: check `Authorization` header before falling back to cookie |
| **Settings page** | New `/settings` route, linked from nav via a gear icon |
| **AUTH_DISABLED** | When `true`, API key auth is also skipped (existing dev/test behavior unchanged) |
| **No expiration (MVP)** | Keys do not expire automatically; user revokes manually. Expiration can be added later. |

### New Dependencies

None — only stdlib (`secrets`, `hashlib`) needed beyond existing deps.

---

## Data Model

### New Table: `api_keys`

```python
class APIKey(SQLModel, table=True):
    __tablename__ = "api_keys"

    id: int | None = Field(default=None, primary_key=True)
    name: str                          # user-provided label, e.g. "CLI on laptop"
    key_hash: str = Field(unique=True) # SHA-256 hex digest of the full key
    key_suffix: str                    # last 6 chars of the plaintext key for display
    created_at: datetime = Field(default_factory=utc_now)
    last_used_at: datetime | None = None
```

**Notes:**

- `key_hash` is indexed and unique — used for lookups on every authenticated request.
- `key_suffix` is the last 6 characters of the plaintext key (e.g. `••••••a1b2c3`), stored only for UI display so the user can tell keys apart.
- `last_used_at` is updated on each successful authentication to help users identify stale keys.

---

## Settings Page & Navigation

### Nav Change

Add a gear icon link to the right side of the nav bar, before the Logout button (when auth is enabled):

```html
<a href="/settings" class="nav-settings-link" title="Settings">
  <!-- inline SVG gear icon -->
</a>
```

When `AUTH_DISABLED=true`, the gear icon still appears (settings page is accessible), but the API key section shows a note that auth is disabled.

### Settings Page (`/settings`)

The Settings page is a simple layout with sections. API Key Management is the first (and initially only) section.

#### API Key Management Section

- **Header:** "API Keys"
- **Description:** Brief text explaining that API keys allow programmatic access.
- **Create form:** A text input for the key name/label + a "Generate Key" button.
- **Key display (post-creation):** After generating, show the full key in a read-only input with a "Copy" button and a warning: _"This key will not be shown again."_ This uses a standard page reload flow — the key is flashed once via a query parameter or template context.
- **Key list table:**
  | Name | Key | Created | Last Used | Actions |
  |------|-----|---------|-----------|---------|
  | CLI on laptop | `gtd_••••••a1b2c3` | 2026-03-30 | 2026-03-30 | Revoke |
- **Revoke:** `POST /settings/api-keys/{key_id}/revoke` — deletes the key row, redirects back to `/settings`.

---

## Auth Middleware Changes

The existing `AuthMiddleware` in `app/auth.py` currently checks for a session cookie. The change adds a prior check for a `Bearer` token:

```
1. If AUTH_DISABLED → pass through (no change)
2. If path is exempt → pass through (no change)
3. Check Authorization header for "Bearer gtd_..." →
   a. Hash the token, look up key_hash in api_keys table
   b. If found → update last_used_at, allow request
   c. If not found → fall through to cookie check
4. Check session cookie (existing logic, no change)
5. If neither → 401 / redirect (existing logic, no change)
```

API key auth **skips** the cookie check entirely when a valid key is found. Requests with an invalid `Bearer` token still fall through to cookie auth (so a browser with a stale or wrong `Authorization` header but a valid cookie still works).

### Important Security Details

- API key lookups use constant-time comparison via `hmac.compare_digest` on the hex hash.
- API keys are only valid for non-exempt routes (same scope as session cookies).
- Rate limiting is not in scope for MVP but the `last_used_at` timestamp enables future monitoring.

---

## Routes

### Settings Page Routes

| Method | Path | Auth Required | Description |
|--------|------|---------------|-------------|
| `GET` | `/settings` | Yes (session) | Render the Settings page |
| `POST` | `/settings/api-keys` | Yes (session) | Generate a new API key |
| `POST` | `/settings/api-keys/{key_id}/revoke` | Yes (session) | Revoke (delete) an API key |

**Note:** API key management routes require a _session cookie_ (browser login). You cannot use an API key to create or revoke other API keys — this prevents a compromised key from being used to mint new credentials.

### File Organization

| File | Change |
|------|--------|
| `app/models.py` | Add `APIKey` model |
| `app/config.py` | No changes needed |
| `app/auth.py` | Add Bearer token check to `AuthMiddleware` |
| `app/services/api_key_service.py` | New — generate, verify, list, revoke |
| `app/routes/settings.py` | New — settings page + API key management routes |
| `app/templates/settings.html` | New — settings page template |
| `app/templates/base.html` | Add gear icon to nav |
| `app/main.py` | Register settings router |
| `docs/api.md` | Document new routes and Bearer auth |
| `.github/skills/todo-api/SKILL.md` | Update with API key info |

---

## Phase Structure

### Phase 1 — Data Model & API Key Service

**Goal:** Add the `APIKey` model, create a service layer for generating/verifying/listing/revoking keys, and ensure the table is created by `init_db()`.

#### New / Changed Files

| File | Change |
|------|--------|
| `app/models.py` | Add `APIKey` table model |
| `app/services/api_key_service.py` | New module with `generate_key`, `verify_key`, `list_keys`, `revoke_key` |

#### Service Functions

```python
def generate_key(session: Session, name: str) -> tuple[APIKey, str]:
    """Create a new API key. Returns (saved model, plaintext key).
    Raises ValueError if name is empty or limit (10) is reached."""

def verify_key(session: Session, plaintext_key: str) -> APIKey | None:
    """Look up a key by its hash. Returns the APIKey if valid, else None.
    Updates last_used_at on success."""

def list_keys(session: Session) -> list[APIKey]:
    """Return all API keys ordered by created_at desc."""

def revoke_key(session: Session, key_id: int) -> bool:
    """Delete an API key by ID. Returns True if deleted, False if not found."""
```

#### Tests (`tests/test_api_key_service.py`)

1. **`test_api_key_table_created`** — After `init_db()`, the `api_keys` table exists.
2. **`test_generate_key_returns_plaintext_and_model`** — `generate_key` returns a tuple with the plaintext starting with `gtd_` and a persisted `APIKey` row.
3. **`test_generated_key_hash_matches`** — SHA-256 of the returned plaintext equals the stored `key_hash`.
4. **`test_key_suffix_matches`** — `key_suffix` equals the last 6 chars of the plaintext.
5. **`test_verify_valid_key`** — `verify_key` returns the `APIKey` for a valid plaintext.
6. **`test_verify_invalid_key`** — `verify_key` returns `None` for a random string.
7. **`test_verify_updates_last_used_at`** — After `verify_key`, `last_used_at` is set.
8. **`test_list_keys_ordered`** — Returns keys ordered by `created_at` descending.
9. **`test_revoke_key_deletes`** — After `revoke_key`, the key is gone and `verify_key` returns `None`.
10. **`test_revoke_nonexistent_returns_false`** — `revoke_key` with a bad ID returns `False`.
11. **`test_generate_key_empty_name_raises`** — Empty or whitespace-only name raises `ValueError`.
12. **`test_generate_key_limit_enforced`** — After 10 keys, `generate_key` raises `ValueError`.

#### Acceptance Criteria

- [ ] `uv run pytest` passes with all existing tests green
- [ ] `api_keys` table is created by `init_db()`
- [ ] Keys are generated with `gtd_` prefix and SHA-256 hashed for storage
- [ ] Plaintext is never persisted

---

### Phase 2 — Auth Middleware Bearer Token Support

**Goal:** Extend `AuthMiddleware` to accept `Authorization: Bearer <key>` as an alternative to the session cookie.

#### Changed Files

| File | Change |
|------|--------|
| `app/auth.py` | Add Bearer token extraction and verification before cookie check |
| `app/db.py` | Possibly expose a helper for getting a session inside middleware (if not already available) |

#### Tests (`tests/test_api_key_auth.py`)

1. **`test_bearer_token_grants_access`** — `GET /inbox` with valid `Authorization: Bearer gtd_...` returns 200.
2. **`test_invalid_bearer_token_falls_through`** — `GET /inbox` with invalid Bearer token and no cookie returns 401/redirect.
3. **`test_bearer_token_on_json_route`** — `GET /export/tasks.json` with valid Bearer returns 200 JSON.
4. **`test_no_auth_returns_401_for_api`** — `GET /export/tasks.json` with no credentials returns 401.
5. **`test_bearer_token_updates_last_used`** — After a request with a valid key, `last_used_at` is updated.
6. **`test_revoked_key_returns_401`** — After revoking a key, requests with it fail.
7. **`test_auth_disabled_skips_bearer_check`** — With `AUTH_DISABLED=true`, routes work without any token.
8. **`test_bearer_and_cookie_both_work`** — A request with a valid cookie but no Bearer header still succeeds (regression guard).

#### Acceptance Criteria

- [ ] Existing cookie-based auth is unaffected
- [ ] `AUTH_DISABLED=true` behavior is unchanged
- [ ] Valid API keys in the `Authorization` header grant access to all protected routes
- [ ] Invalid/revoked keys fall through to cookie auth

---

### Phase 3 — Settings Page & API Key Management UI

**Goal:** Add the Settings page with API key management, a gear icon in the nav, and the routes for generating/revoking keys.

#### New / Changed Files

| File | Change |
|------|--------|
| `app/routes/settings.py` | New router: `GET /settings`, `POST /settings/api-keys`, `POST /settings/api-keys/{key_id}/revoke` |
| `app/templates/settings.html` | New template extending `base.html` |
| `app/templates/base.html` | Add gear icon link in nav bar |
| `app/main.py` | Register settings router |

#### Nav Bar Gear Icon

Place the gear icon to the left of the Logout button (or as the rightmost nav element when auth is disabled). Use an inline SVG so there are no external icon dependencies:

```html
<a href="/settings" class="nav-settings-link" title="Settings">
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
       fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
       stroke-linejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06
             a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09
             A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83
             l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09
             A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83
             l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09
             a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83
             l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09
             a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
</a>
```

#### Settings Page Sections

The template should include:

1. **Page title:** "Settings"
2. **API Keys section:**
   - Heading "API Keys" with a short description
   - A form with a name input and "Generate Key" button
   - If a key was just created: a highlighted box showing the full key with a copy button and a one-time warning
   - A table of existing keys (name, masked key, created date, last used date, revoke button)
   - If no keys exist: a message saying "No API keys yet."
3. **When `AUTH_DISABLED=true`:** Show an info banner: _"Authentication is disabled. API keys are not enforced but can still be managed."_

#### Tests (`tests/test_settings_page.py`)

1. **`test_settings_page_loads`** — `GET /settings` returns 200 with "Settings" in the body.
2. **`test_settings_page_shows_api_keys_section`** — Response contains "API Keys".
3. **`test_generate_key_shows_plaintext_once`** — `POST /settings/api-keys` with `name=test` redirects to `/settings` and the response contains the `gtd_` plaintext key.
4. **`test_generated_key_appears_in_list`** — After generating, the key list table includes the key name and masked suffix.
5. **`test_revoke_key_removes_from_list`** — After `POST /settings/api-keys/{id}/revoke`, the key no longer appears.
6. **`test_generate_key_empty_name_shows_error`** — Submitting with an empty name shows a validation message.
7. **`test_generate_key_at_limit_shows_error`** — When 10 keys exist, trying to generate another shows an error.
8. **`test_gear_icon_in_nav`** — `GET /inbox` response includes `/settings` link in the nav.
9. **`test_settings_requires_auth`** — With `AUTH_DISABLED=false` and no session, `GET /settings` redirects to login.

#### Acceptance Criteria

- [ ] Gear icon visible in nav on all pages
- [ ] Settings page renders with API key management
- [ ] Keys can be generated and the plaintext is shown once
- [ ] Keys can be revoked
- [ ] Settings page requires authentication (session cookie, not API key)
- [ ] All existing tests pass

---

### Phase 4 — Documentation & Skill Updates

**Goal:** Update all docs and `.github` assets to reflect the new API key auth capability.

#### Changed Files

| File | Change |
|------|--------|
| `docs/api.md` | Add Bearer auth section, settings routes, API key lifecycle |
| `docs/llm-integration.md` | Mention API key as a way for LLM agents to authenticate |
| `.github/skills/todo-api/SKILL.md` | Add API key usage examples and `Authorization` header details |
| `.github/skills/todo-data-model/SKILL.md` | Add `APIKey` model fields and semantics (hashed storage, suffix, last-used tracking) |
| `.github/skills/gtd-daily-report/SKILL.md` | Update Step 2 to recommend API key auth via HTTP as the preferred method over direct SQLite queries inside the container |
| `.github/copilot-instructions.md` | Update architecture constraints with API key info |
| `README.md` | Add API key section to usage docs |

#### Documentation Additions for `docs/api.md`

```markdown
## Authentication Methods

### Session Cookie (Browser)

(existing content)

### API Key (Programmatic Access)

Include the key in the `Authorization` header:

    Authorization: Bearer gtd_your_key_here

API keys grant access to all protected routes (same scope as session cookies).
API keys cannot be used to access the Settings page or manage other keys.

### Managing API Keys

- `GET /settings` — Settings page with API key management (requires session)
- `POST /settings/api-keys` — Generate a new key (requires session)
- `POST /settings/api-keys/{key_id}/revoke` — Revoke a key (requires session)
```

#### Acceptance Criteria

- [ ] `docs/api.md` documents both auth methods and settings routes
- [ ] Skill files are updated so future agent sessions know about API keys
- [ ] README mentions API key support

---

## Security Considerations

1. **Keys are hashed at rest** — Only SHA-256 digests are stored. The plaintext is shown once and never persisted.
2. **Constant-time comparison** — Key lookups use `hmac.compare_digest` to prevent timing attacks.
3. **Key management requires session auth** — A stolen API key cannot be used to create new keys or revoke others. The attacker would need browser access with a passkey.
4. **Keys have a recognizable prefix** — The `gtd_` prefix makes keys easy to identify in secret scanners and `.gitignore` patterns.
5. **Key limit** — A cap of 10 keys prevents abuse and simplifies management.
6. **Last-used tracking** — `last_used_at` helps users identify and revoke stale keys.
7. **No key rotation (MVP)** — Users revoke and re-create. Automatic rotation can be added later.
8. **`AUTH_DISABLED` bypass** — When auth is disabled (dev/test), API key verification is skipped along with all other auth, matching existing behavior.
