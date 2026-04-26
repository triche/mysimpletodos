# Multi-User Support — TDD Phased Implementation Plan

_April 2026_

## Overview

Transform MySimpleTodos from a single-owner app into a multi-tenant system
where each user has completely isolated tasks, projects, and API keys.
Any user account can be granted the **admin role**, which adds access to a
user-management UI — admin users still have their own tasks and projects like
everyone else. Users are invited by an admin — there is no self-registration.

### Key Design Decisions

| Decision | Choice |
|---|---|
| **Tenancy model** | Row-level isolation — every data table gets a `user_id` FK |
| **Database engine** | Stay on SQLite (WAL mode, `check_same_thread=False`) |
| **Migration tooling** | Alembic (replaces hand-rolled `ALTER TABLE` migrations) |
| **User authentication** | Passkeys (WebAuthn) only |
| **User onboarding** | Admin creates user → generates invite link with one-time token → user registers passkey |
| **Admin role** | `is_admin` flag on `User`; admins use the app normally AND get access to `/admin/` user-management UI via a key icon in the nav bar |
| **Existing data** | Auto-create a user **with admin role** from the existing passkey credential; assign all tasks, projects, and API keys to that user |
| **CLI** | No changes — API keys are already per-bearer; they become user-scoped in the DB |
| **AUTH_DISABLED mode** | Preserved for dev/test; assumes a single synthetic user context |

---

## Current State (Single-User)

- **Session cookie** stores `{"authenticated": True}` — no user identity.
- **WebAuthnCredential** has no `user_id`; the service hardcodes `user_name="owner"`.
- **Task**, **Project**, **APIKey** have no `user_id`; services query all rows.
- **Project.name** has a global `UNIQUE` constraint.
- **In-memory challenge store** is a single global variable.
- **Middleware** checks "is someone authenticated?" — doesn't know *who*.
- **Backup/Restore** (`GET /backup/download`, `POST /backup/restore`) operates on the
  raw SQLite file — the entire database for all users. The CLI exposes this via
  `mst backup download` and `mst backup restore`. The Settings page provides a UI.
  The old `scripts/backup-db.sh` Docker-only shell script has been removed.

---

## New & Changed Models

### `User` (new table: `users`)

| Column | Type | Notes |
|---|---|---|
| `id` | `int` PK | Auto-increment |
| `username` | `str` | Unique, used in WebAuthn `user_name` |
| `display_name` | `str` | Shown in UI |
| `is_admin` | `bool` | Default `False` |
| `is_active` | `bool` | Default `True`; disabled users cannot log in |
| `invite_token_hash` | `str \| None` | SHA-256 of one-time invite token; cleared after passkey registration |
| `invite_expires_at` | `datetime \| None` | Invite expiry |
| `created_at` | `datetime` | |
| `updated_at` | `datetime` | |

### Changes to Existing Tables

| Table | Change |
|---|---|
| `tasks` | Add `user_id INT NOT NULL REFERENCES users(id)` (indexed) |
| `projects` | Add `user_id INT NOT NULL REFERENCES users(id)` (indexed); change `UNIQUE(name)` → `UNIQUE(user_id, name)` |
| `webauthn_credentials` | Add `user_id INT NOT NULL REFERENCES users(id)` (indexed) |
| `api_keys` | Add `user_id INT NOT NULL REFERENCES users(id)` (indexed); _MAX_KEYS limit becomes per-user |

### ER Diagram (post-migration)

```
users 1──∞ tasks
users 1──∞ projects
users 1──∞ webauthn_credentials
users 1──∞ api_keys
projects 1──∞ tasks
```

---

## Session & Middleware Changes

### Session Cookie

Currently: `{"authenticated": True}`

After: `{"user_id": <int>, "is_admin": <bool>}`

The `create_session_cookie(user_id, is_admin)` and `verify_session_cookie()` functions
will encode/decode user identity. `verify_session_cookie` returns a `SessionInfo`
dataclass (or `None`) instead of a bare `bool`.

### Auth Middleware

- Extracts `user_id` from the session cookie (or from the API key lookup).
- Sets `request.state.user_id` and `request.state.is_admin`.
- Admin users can access **all** regular routes (they are normal users too)
  **and** `/admin/*` routes.
- Regular users requesting `/admin/*` → 403.
- `AUTH_DISABLED` mode sets `request.state.user_id` to a hard-coded sentinel
  (e.g., `1`) and `request.state.is_admin = False`.

### API Key Authentication

`verify_key()` already returns an `APIKey` object. After adding `user_id` to the
model, the middleware reads `api_key.user_id` and sets `request.state.user_id`.

---

## Invite & Registration Flow

```
Admin UI                     Server                        New User
  │                            │                              │
  ├─ POST /admin/users ───────►│ create User row              │
  │   {username, display_name} │ generate invite_token        │
  │                            │ store hash, set expiry       │
  │◄── invite URL ─────────────┤                              │
  │                            │                              │
  │   (admin shares link       │                              │
  │    out-of-band)            │                              │
  │                            │                              │
  │                            │◄── GET /auth/invite/<token> ─┤
  │                            │ validate token, show          │
  │                            │ passkey registration page     │
  │                            │                              │
  │                            │◄── POST /auth/invite/verify ─┤
  │                            │ verify registration           │
  │                            │ store WebAuthnCredential      │
  │                            │ clear invite_token_hash       │
  │                            │ set session cookie            │
  │                            │──── redirect to / ───────────►│
```

**Invite token format:** `mst_invite_<32-hex-bytes>` — stored as SHA-256 hash.
Default expiry: 72 hours (configurable via `INVITE_EXPIRY_HOURS` env var).

---

## Admin UI

The admin role is granted during first-run setup and can be assigned to other
users later. Admins access user management at `/admin/` — they also use all
normal app routes for their own tasks and projects.

### Nav Bar Integration

Admin users see a **key icon** (🔑 as SVG) in the top-right nav actions area,
between the existing settings gear and the theme toggle. Clicking it navigates
to `/admin/`. The icon is conditionally rendered in `base.html` based on a
template variable `is_admin` (set by the route layer / middleware).

```html
{% if is_admin %}
<a href="/admin/" class="nav-icon-btn" title="Admin">
  <!-- key SVG icon -->
</a>
{% endif %}
```

The admin pages themselves use the same `base.html` layout (so the admin
always sees the full nav and can switch back to their tasks). The admin
content area replaces the normal task/project content.

### Admin Routes

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/` | Dashboard — user list, system stats |
| `GET` | `/admin/users` | User table (username, display name, active, admin role, credential count, created) |
| `POST` | `/admin/users` | Create new user → returns invite link |
| `GET` | `/admin/users/{id}` | User detail / edit |
| `POST` | `/admin/users/{id}` | Update user (display name, active toggle, admin role toggle) |
| `POST` | `/admin/users/{id}/reinvite` | Generate a new invite token (invalidates old) |
| `POST` | `/admin/users/{id}/deactivate` | Set `is_active=False`; revoke sessions |
| `POST` | `/admin/users/{id}/activate` | Set `is_active=True` |
| `POST` | `/admin/users/{id}/grant-admin` | Set `is_admin=True` — only admins can do this |
| `POST` | `/admin/users/{id}/revoke-admin` | Set `is_admin=False` — cannot revoke your own admin role |

### Admin Templates

- `admin_dashboard.html` — extends `base.html`; user list table with action buttons.
- `admin_user_detail.html` — extends `base.html`; edit form, re-invite, activate/deactivate, admin role toggle.
- `admin_invite_success.html` — extends `base.html`; shows invite link with copy button.

---

## First-Run Setup (Admin Bootstrapping)

Current behavior: first visitor to `/auth/setup` registers a passkey as "owner."

New behavior:

1. If the `users` table is empty, `/auth/setup` renders an **admin setup** page.
2. The visitor chooses a username and display name, then registers a passkey.
3. The server creates a `User(is_admin=True)` row and the linked `WebAuthnCredential`.
4. The admin is logged in and redirected to `/` (their normal task view — they can
   reach admin UI via the key icon in the nav).
5. Subsequent visits to `/auth/setup` redirect to `/auth/login` (same as today).

---

## Login Flow Changes

Current: `generate_authentication_options` returns challenges for *all* credentials
in the DB. Any valid passkey logs you in as "authenticated."

New:

1. `/auth/login` is a **usernameless** WebAuthn flow — the browser's credential
   picker shows all passkeys registered on this RP.
2. On verification, the server looks up the `WebAuthnCredential` by `credential_id`,
   reads `user_id`, checks `User.is_active`, and creates a session with that user's
   identity.
3. Redirect to `/` regardless of admin status (admins are normal users first;
   they reach admin UI via the key icon in the nav bar).

### Challenge Store

Replace the single global `_current_challenge` variable with a short-lived
in-memory dict keyed by a random challenge ID (stored in a temporary cookie or
returned as part of the options JSON). This handles concurrent login attempts from
different users. Entries expire after 5 minutes.

---

## Service Layer Changes

Every service function that reads or writes tasks, projects, or API keys gains a
required `user_id: int` parameter and filters accordingly.

### Pattern

```python
# Before
def list_tasks(session: Session, *, status=None, project_id=None) -> list[Task]:
    stmt = select(Task)
    ...

# After
def list_tasks(session: Session, *, user_id: int, status=None, project_id=None) -> list[Task]:
    stmt = select(Task).where(Task.user_id == user_id)
    ...
```

The same pattern applies to `create_task`, `get_task`, `update_task`, `complete_task`,
`create_project`, `get_project`, `list_projects`, `generate_key`, `list_keys`,
`revoke_key`, and all export functions.

**Critical:** Every `get_*` and `update_*` that takes an entity ID must also verify
`user_id` matches — never trust the ID alone. This prevents horizontal privilege
escalation.

### Backup & Restore Service

The current backup endpoints (`GET /backup/download`, `POST /backup/restore`) operate
on the raw SQLite file. In multi-user mode, **per-user export/import replaces
whole-database backup** for regular users:

- `create_user_backup(session, user_id)` → exports the user's tasks, projects,
  and API key metadata as a JSON archive (no credentials or other users' data).
- `restore_user_backup(session, user_id, data)` → validates and imports the JSON
  archive, creating/updating only rows belonging to that user. Duplicate handling:
  match by original ID; on conflict, update in place.

The JSON archive format:

```json
{
  "format": "mst-user-backup-v1",
  "exported_at": "2026-04-18T12:00:00",
  "user": {"username": "alice", "display_name": "Alice"},
  "tasks": [ ... ],
  "projects": [ ... ]
}
```

**Admin-only:** The raw SQLite download/restore endpoints remain available but are
restricted to admin users. They are hidden from the Settings page for non-admins.

**Regular users** see only user-scoped backup/restore on the Settings page:

- "Download My Data" → `GET /backup/download?scope=user` → JSON archive of their data.
- "Restore My Data" → `POST /backup/restore` with JSON upload → imports only their data.

One user's backup **cannot** contain or affect another user's rows. The service
validates that every row in the archive either has no `user_id` (single-user format,
assigned to the importing user) or matches the authenticated user's ID.

### Route Layer

Routes extract `user_id` from `request.state.user_id` and pass it to service
functions. A small helper makes this ergonomic:

```python
def current_user_id(request: Request) -> int:
    uid = getattr(request.state, "user_id", None)
    if uid is None:
        raise HTTPException(status_code=401)
    return uid
```

---

## Database Migration Strategy (Alembic)

### Adopting Alembic

1. Add `alembic` to `pyproject.toml` dependencies.
2. Run `alembic init alembic/` — creates `alembic.ini` and `alembic/env.py`.
3. Configure `env.py` to read `DATABASE_URL` from `app.config.get_settings()` and
   use `SQLModel.metadata` as `target_metadata`.
4. Remove `_migrate_schema()` from `app/db.py`; roll its logic into the initial
   Alembic baseline migration.
5. `init_db()` calls `alembic.command.upgrade(config, "head")` instead of
   `SQLModel.metadata.create_all()`.

### Migration Script: `add_multi_user_support`

The migration must handle two cases:

#### Case A — Fresh database (no tables yet)

Create all tables from current models (which include `user_id` columns).

#### Case B — Existing single-user database

1. **Create `users` table.**
2. **Create migration user:** Insert a `User(username="owner", display_name="Owner", is_admin=True, is_active=True)`.
3. **Add `user_id` columns** (nullable initially) to `tasks`, `projects`,
   `webauthn_credentials`, `api_keys`.
4. **Backfill:** `UPDATE tasks SET user_id = <owner_id>`, same for all tables.
5. **Make `user_id` NOT NULL** via SQLite table-rebuild (Alembic's `batch_alter_table`).
6. **Drop old `UNIQUE(name)` on projects**, add `UNIQUE(user_id, name)`.
7. **Add indexes** on `user_id` columns.

SQLite doesn't support `ALTER COLUMN` — Alembic's batch mode handles this by
rebuilding the table, which is fine for the expected data volumes.

---

## Deployment Environments

Two environments are in active use. The implementation must work correctly in both.

### Production — Hetzner VPS

- Deployed via GitHub Actions ([`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml)):
  `git pull origin main` → `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`.
- The production overlay (`docker-compose.prod.yml`) adds port bindings 80/443/443-udp and
  sets `CADDY_HTTP_PORT=80`. Caddy terminates TLS and reverse-proxies to the app on 8080.
- SQLite DB is persisted in the **named Docker volume** `todo_app_data`, mounted at `/data`.
- Production `.env` on the server supplies:
  ```
  AUTH_SECRET_KEY=<32-byte hex>
  CADDY_SITE_ADDRESS=mysimpletodos.com
  WEBAUTHN_RP_ID=mysimpletodos.com
  WEBAUTHN_ORIGIN=https://mysimpletodos.com
  ```
- **Alembic migrations** run automatically at startup via `init_db()` (which calls
  `alembic upgrade head`). The named volume persists data across redeploys — no manual
  migration step is needed in CI.
- **Passkey recovery:** if the browser-side passkey is lost (keychain cleared, new device),
  clear `webauthn_credentials` via the DB exec method documented below and re-register at
  `/auth/setup`. In multi-user mode this becomes `/admin/users/{id}/reinvite`.
- **Raw SQLite backup/restore** must remain accessible to the admin via the Settings page
  and `mst backup download/restore` — this is the primary DR mechanism on Hetzner.

### Local Development — Docker Compose (single-compose file)

- Started with: `docker compose up --build` (base file only, no prod overlay).
- Caddy is exposed only on host port 8080; no TLS.
- Typical local `.env` or environment:
  ```
  AUTH_DISABLED=true          # skip auth during dev
  WEBAUTHN_RP_ID=localhost
  WEBAUTHN_ORIGIN=http://localhost:8080
  ```
- SQLite DB lives in the same `todo_app_data` named volume (or `sqlite:///./data/todo.db`
  if running outside Docker with `uv run uvicorn ...`).
- For multi-user testing with auth enabled, set `AUTH_DISABLED=false` and use the
  `/auth/setup` first-run flow at `http://localhost:8080`.

### Environment Implications for This Implementation

| Concern | Hetzner production | Local dev |
|---|---|---|
| Alembic runs on | Container startup (auto) | Container startup (auto) |
| First admin setup | `/auth/setup` after first deploy | `/auth/setup` or `AUTH_DISABLED=true` |
| TLS / Secure cookies | Yes — `WEBAUTHN_ORIGIN` starts with `https` | No — `http://localhost:8080` |
| Data persistence | Named Docker volume `todo_app_data` | Named volume or local path |
| Raw DB backup access | Admin only (Settings + CLI) | Unrestricted in dev |
| WEBAUTHN_RP_ID | `mysimpletodos.com` | `localhost` |

---

## Configuration Changes

| Variable | Purpose | Default |
|---|---|---|
| `INVITE_EXPIRY_HOURS` | How long invite links are valid | `72` |

No other new env vars needed. Existing `WEBAUTHN_*` variables continue to work.

---

## Phase Plan

### Phase 0: Alembic Setup & Baseline

**Goal:** Adopt Alembic without changing behavior.

1. Add `alembic` dependency.
2. Initialize Alembic config.
3. Create baseline migration that represents the current schema.
4. Replace `_migrate_schema()` and `create_all()` with `alembic upgrade head`.
5. Tests: existing test suite passes unchanged (Alembic creates schema in test DBs).

**Deployment note:** `alembic upgrade head` is called inside `init_db()`, which runs at
app startup. Both environments (Hetzner and local Docker) run migrations automatically on
`docker compose up --build`. No manual SSH migration step is needed.

### Phase 1: User Model & Migration

**Goal:** Add the `User` table and `user_id` FK columns; migrate existing data.

1. Define `User` model.
2. Write Alembic migration (Case A + Case B as described above).
3. Tests: migration applies cleanly on empty DB and on a DB with existing data;
   all existing rows get `user_id` assigned.

### Phase 2: Session Identity & Middleware

**Goal:** Sessions carry user identity; middleware populates `request.state.user_id`.

1. Update `create_session_cookie` / `verify_session_cookie` to encode/decode `user_id`.
2. Update `AuthMiddleware` to set `request.state.user_id` and `request.state.is_admin`.
3. Update API key auth path to set `request.state.user_id` from `api_key.user_id`.
4. `AUTH_DISABLED` mode: auto-set `user_id=1`, `is_admin=False`.
5. Tests: middleware correctly populates request state; admin vs. regular routing.

### Phase 3: Service Layer Scoping

**Goal:** All data access is scoped to the authenticated user.

1. Add `user_id` parameter to every service function.
2. Filter all queries by `user_id`.
3. Ownership checks on `get_*` / `update_*` / `delete_*`.
4. Update route handlers to pass `request.state.user_id`.
5. Convert backup service: `create_user_backup(session, user_id)` exports only
   that user's tasks/projects as JSON; `restore_user_backup(session, user_id, data)`
   imports only their data. Restrict raw SQLite backup/restore to admin role.
6. Tests: user A cannot see/modify user B's data (horizontal privilege tests);
   user A's backup download contains none of user B's data; restoring user A's
   backup does not create/modify any rows belonging to user B.

### Phase 4: Login Flow for Multi-User

**Goal:** Login resolves to a specific user via their passkey credential.

1. Replace global `_current_challenge` with challenge-ID-keyed dict + TTL.
2. `verify_authentication` looks up `WebAuthnCredential.user_id` after verification.
3. Create session with resolved `user_id`.
4. Tests: two users can log in with different passkeys; challenge replay fails.

### Phase 5: Admin Setup & Dashboard

**Goal:** First-run creates an admin; admin can view users.

1. Modify `/auth/setup` to create a `User(is_admin=True)` instead of a bare credential.
2. Add `is_admin` template variable to `base.html` context; render key icon conditionally.
3. Build `admin_dashboard.html` (extends `base.html`).
4. `/admin/` route shows user list.
5. Admin middleware guard: regular users → 403 on `/admin/*`; admins access everything.
6. Tests: first-run creates admin; admin sees dashboard and key icon; regular user gets 403 on `/admin/`; admin can still access task routes.

### Phase 6: User Invitation

**Goal:** Admin can create users and generate invite links.

1. `POST /admin/users` creates `User` with invite token.
2. `GET /auth/invite/<token>` validates and shows passkey registration.
3. `POST /auth/invite/verify` registers passkey, clears invite token, logs in.
4. Admin can re-invite (generate new token for existing user).
5. Tests: full invite → register → login flow; expired token rejected; reused token rejected.

### Phase 7: User Management

**Goal:** Admin can deactivate/activate users and manage admin role.

1. Deactivate: sets `is_active=False`, invalidates sessions (cookie TTL means they'll fail on next check).
2. Activate: sets `is_active=True`.
3. Grant admin: sets `is_admin=True` on target user.
4. Revoke admin: sets `is_admin=False` — admin cannot revoke their own role (safety check).
5. Login and middleware check `is_active` before granting access.
6. Tests: deactivated user cannot log in; reactivated user can; admin role grant/revoke works; self-revoke blocked.

### Phase 8: Cleanup & Hardening

**Goal:** Final polish and security review.

1. Audit all routes for missing `user_id` scoping.
2. Rate-limit invite token validation (prevent brute force).
3. Add `user_id` context to structured logging.
4. Update `AUTH_DISABLED` test fixtures to set user context.
5. Verify backup isolation: admin-only raw SQLite endpoints; per-user JSON
   backup/restore for regular users; no cross-user data leakage.
6. Update all docs, skills, and `README.md`.
7. Full regression test run.
8. **Deployment verification:**
   - Test full flow on local Docker (`docker compose up --build`, `AUTH_DISABLED=false`).
   - Verify Alembic runs cleanly on the Hetzner `todo_app_data` volume (existing data
     migrated; no data loss).
   - Confirm Hetzner passkey registration works end-to-end at `https://mysimpletodos.com/auth/setup`
     after the first multi-user deploy.
   - Update deploy runbook in `README.md` with multi-user first-run admin setup steps.

---

## Security Considerations

- **Row-level isolation is mandatory.** Every query touching user data MUST filter
  by `user_id`. Forgetting this is the single most dangerous bug class.
- **Invite tokens are sensitive.** Hash before storing; expire after 72h; one-time use.
- **Admin privilege escalation.** Only the `is_admin` flag on the `User` row controls
  admin access — never trust client input for this. An admin cannot revoke their
  own admin role (prevents accidental lockout). At least one admin must always exist.
- **SQLite concurrency.** WAL mode allows concurrent reads with single writes. For the
  expected user count (< 10), this is adequate. Document this as a scaling boundary.
- **Challenge store.** Moving from a single variable to a dict with TTL prevents
  challenge confusion between concurrent auth ceremonies.
- **Backup isolation.** Regular users can only export/import their own data as a
  JSON archive — never the raw SQLite file. The raw database download/restore
  endpoints are restricted to admin users. A user's backup archive is validated
  on import to ensure it contains no rows belonging to other users.

---

## Out of Scope (Future Considerations)

- **PostgreSQL migration.** If user count grows beyond ~50 concurrent, revisit SQLite.
- **User self-service profile editing.** Users cannot yet change their display name.
- **Multiple passkeys per user.** The model supports it (1:N), but the UI doesn't
  expose adding/removing individual passkeys yet.
- **Audit log.** Admin actions (create user, deactivate, re-invite) are not logged
  beyond application logs.
- **Email notifications.** Invite links are shared out-of-band (copy-paste). No email
  integration planned.
- **Shared projects / task delegation.** Explicitly excluded — each user is fully isolated.
- **Cross-user backup restore.** An admin importing a user's JSON backup as a
  different user (migration use-case) is not supported initially.
- **Separate admin UI layout.** Admin pages share `base.html` with the full nav bar
  so admins can seamlessly switch between their tasks and user management.
