# Adaptive UX — Desktop and Phone Implementation Plan

_April 2026_

## Overview

This plan defines the work required to make MySimpleTodos feel first-class on
both desktop and phone browsers, with no horizontal page scrolling and no
critical controls hidden off-screen.

The current UI is visually strong but mostly tuned for wide screens. The top
navigation uses a single horizontal row, which causes overflow on narrow
devices. This plan introduces adaptive navigation, layout scaling rules, and
device-focused testing to ensure a predictable and efficient experience across
screen sizes.

## Problem Statement

Current pain points observed on phone browsers:

1. Top-right control icons can render off-screen.
2. Primary nav tabs do not fit naturally within the viewport.
3. Users must horizontally pan to reach core navigation and controls.

The app should never require horizontal panning for primary interactions.

## Goals

1. Deliver a fully usable phone experience for daily task workflows.
2. Preserve and refine the desktop experience without regressions.
3. Ensure all primary navigation destinations are discoverable and reachable on
   small screens.
4. Keep implementation aligned with current stack: server-rendered templates,
   small JS, HTMX where needed.
5. Use test-first development for each phase.

## Non-Goals

1. Native mobile app development.
2. Full frontend framework migration.
3. Rebranding or major visual redesign unrelated to adaptive behavior.
4. Adding a headless browser dependency (e.g. Playwright). All automated
   tests must run with the current stack: `pytest`, FastAPI `TestClient`,
   and Python stdlib HTML parsing.
5. Changes to the MST CLI or HTTP API surfaces. Only the browser UI is in
   scope.

## Adaptive UX Principles

1. No horizontal page overflow at viewport widths >= 320px.
2. Navigation must prioritize reachability over visual symmetry.
3. Desktop and phone each get intentional layouts, not simple element shrink.
4. Touch targets must be >= 44x44 CSS px for interactive controls on phone,
   with >= 8 px spacing between adjacent targets (WCAG 2.5.8).
5. Keyboard and screen-reader behavior must remain correct.

## Breakpoint Strategy

Use explicit, behavior-based breakpoints rather than ad hoc one-off fixes.

1. `sm`: 320px-599px (phone portrait)
2. `md`: 600px-899px (phone landscape / small tablets)
3. `lg`: >= 900px (desktop and larger tablets)

### CSS Architecture Rules

1. Define breakpoint values once in a `:root` comment block at the top of
   `app/static/app.css` (e.g. `/* bp:sm max 599px; bp:md max 899px; bp:lg
   min 900px */`). `@media` cannot consume custom properties for ranges, so
   the comment block is the source of truth referenced by every component.
2. Group responsive rules by component, not by breakpoint. Each component
   should have at most one `@media` block per breakpoint.
3. New media queries must reuse the three documented breakpoint values
   (`599px`, `899px`, `900px`). Ad hoc breakpoints require an inline comment
   explaining why.
4. No new external runtime CSS or JS dependencies.

## Current Overflow Inventory

Captured during Phase 0 audit; this is the working list of known offenders to
fix in Phase 2. Update as new sources are discovered.

Status legend: ✅ resolved (Phase 1 or 2) · ⏳ deferred · ❌ open.

1. ✅ `.top-nav` is a single flex row containing brand + 4 nav links + 3
   utility icon buttons. Resolved in Phase 1: section links move to the
   bottom tab bar on `sm`; top bar shrinks to brand + utility cluster.
2. ✅ `.nav-links` does not wrap and has no horizontal scroll affordance.
   Resolved in Phase 1: replaced by a fixed bottom tab bar on `sm` with
   four equal slots.
3. ✅ Nav badge counters render inline and prevent text truncation of link
   labels. Resolved in Phase 1: section labels live in their own
   `nav-link-label` span and the bottom tab bar gives each badge its own
   slot.
4. ✅ Task list rows use horizontal flex layouts whose metadata (project
   chip, due date, recurrence) does not stack. Resolved in Phase 2 (the
   existing `md` rule wraps `.task-header` and stacks `.task-meta`; Phase 2
   added `min-width: 0` and `overflow-wrap: anywhere` on `.task-title` so
   long titles do not force overflow inside the flex parent).
5. ✅ Inline selectors in `_task_inline_selectors.html` use fixed-width
   selects that exceed narrow viewports. Resolved in Phase 2: at `sm` the
   inline selectors expand to `width: 100%` with a 36px minimum height.
6. ✅ `project_detail.html` and `tasks_list.html` contain unwrapped tabular
   structures. Verified in Phase 2: those templates do not actually contain
   `<table>` elements (rendered as `<ul>`/`<ol>`); the only `<table>` in
   the app is the API keys list in `settings.html`, now wrapped in
   `.table-scroll`.
7. ✅ `task_edit.html` and `project_edit.html` forms use multi-column
   layouts without single-column fallback. Resolved (already in place): the
   `md` block collapses `.form-row` and `.panel-grid` to a single column.
8. ✅ `.shell` may impose a `min-width` that prevents the body from
   shrinking. Verified in Phase 2: `.shell` declares only width with
   `min(...)` clamping, no `min-width`. Covered by the
   `test_no_oversized_min_width_on_top_level_wrappers` CSS contract test.
9. ✅ Long task titles and project names lack `overflow-wrap: anywhere` or
   `min-width: 0` on flex children. Resolved in Phase 2 for `.task-title`.

## Target Navigation Behavior

### Desktop (`lg`)

1. Keep a single top nav row.
2. Brand, primary tabs, and controls remain in one horizontal line.
3. Maintain current quick-scan information density.

### Mid-size (`md`)

1. Keep the top nav row but compress padding and badge spacing.
2. Allow nav link labels to remain visible without wrapping.
3. Utility icons (settings, theme, logout) stay in the top row.

### Phone (`sm`) — Decision

**Decision: bottom tab bar for primary sections + compact top bar for brand
and utility icons.** Recorded April 2026.

Rationale (decision criteria, weighted by importance):

1. One-hand reach for primary navigation — bottom bar wins decisively.
2. Fit within 320px without horizontal scroll — bottom bar uses full
   viewport width with even slots; a top scroll-strip hides items behind a
   gesture.
3. Badge visibility — bottom bar shows all badges simultaneously; a
   scroll-strip hides badges that are off-screen.
4. Implementation cost — both are CSS-only; bottom bar is slightly simpler
   because no JS scroll affordance is needed.

Layout:

1. Top bar (sticky): brand on the left, utility cluster on the right
   containing settings, theme toggle, and logout. Height tuned for 44px
   tap targets.
2. Bottom tab bar (fixed): four equal slots for Inbox, Today, All Tasks,
   Projects. Each slot shows icon + short label + badge. Active slot is
   visually distinct.
3. Bottom bar respects iOS safe area: padding-bottom uses
   `env(safe-area-inset-bottom)` and `<meta name="viewport">` is updated to
   include `viewport-fit=cover`.
4. Main content gets a bottom padding equal to bottom bar height + safe area
   so the last list item is never hidden.

Theme toggle placement on phone: top bar utility cluster (alongside settings
and logout). Confirmed by decision above.

## Work Phases (TDD)

Five phases including Phase 0. Implement one at a time. Each phase must end
with green tests, updated docs, and no layout regressions on desktop.

### Phase 0 — Baseline, Inventory, and Test Harness

Goal: establish reproducible checks before UI changes.

Tasks:

1. Audit every primary route and update "Current Overflow Inventory" above
   as new sources are found.
2. Add a `responsive` pytest marker (declare in `pyproject.toml` under
   `[tool.pytest.ini_options]` markers).
3. Create `tests/test_responsive_layout.py` using `TestClient` and
   `html.parser` (stdlib) to assert structural responsive contracts on
   rendered HTML for `/inbox`, `/today`, `/tasks`, `/projects`, `/settings`,
   and `/auth/login`:
   - `<nav>` landmarks exist with the expected `aria-label` values.
   - Brand link, every primary nav link, settings, theme toggle, and (when
     authenticated) logout exist in the DOM.
   - Required CSS classes for adaptive layout are present
     (e.g. `nav-top`, `nav-tabbar`, `nav-utility`).
   - Viewport meta tag includes `viewport-fit=cover`.
4. Create `tests/test_responsive_css.py` that scans `app/static/app.css`
   text to enforce architecture rules (see Test Strategy section).
5. The Phase 0 tests must initially fail in ways that describe the current
   overflow problems (red baseline).

Acceptance Criteria:

1. `uv run pytest -m responsive` runs and exhibits the expected red
   baseline.
2. Overflow inventory section is filled in and reviewed.
3. No new runtime or test dependencies introduced.

### Phase 1 — Navigation Information Architecture Update

Goal: implement the bottom tab bar + compact top bar pattern on `sm`,
preserve `lg` nav, refine `md`.

Tasks:

1. Restructure `app/templates/base.html` so the nav DOM contains:
   - A top bar with brand and utility cluster (settings, theme, logout).
   - A primary section nav element rendered as a horizontal top row on
     `lg`/`md` and as a bottom tab bar on `sm`.
   - Both elements are present in the DOM at all breakpoints; CSS controls
     visibility and position. Keep a single source of truth for nav links
     (one Jinja loop or include).
2. Add semantic landmarks: `<header>`, `<nav aria-label="Primary">` for the
   utility/top region, `<nav aria-label="Sections">` for primary section
   navigation. Confirm `<main>` is the only landmark with role `main`.
3. Update `app/static/app.css`:
   - Add the `:root` breakpoint comment block.
   - Add tab-bar styles with safe-area padding.
   - Compact top bar at `md`.
   - Ensure all nav buttons are >= 44x44 CSS px on `sm`.
4. Update `<meta viewport>` in `base.html` head to include
   `viewport-fit=cover`.
5. No new JS unless strictly required. If added, it must be < 2 KB
   unminified inline and respect `prefers-reduced-motion`.
6. Document the constraint that any HTMX swap touching nav fragments must
   preserve adaptive classes.

Acceptance Criteria:

1. No critical control declares `display:none` at any breakpoint
   (verified by structural test) and the CSS contract test passes.
2. All primary sections are reachable within one tap on `sm`.
3. Desktop nav remains visually stable; existing pages tests still pass.
4. Theme toggle, settings, and logout are reachable on `sm` from the top
   bar.

### Phase 2 — Page Layout Adaptation and Touch Ergonomics

Goal: ensure content areas are phone-friendly beyond the header. Resolve
every item in the Current Overflow Inventory.

Tasks:

1. Normalize spacing and typography scale for `sm` and `md`.
2. Stack task row metadata (project, due date, recurrence) on `sm`.
3. Make inline selectors in `_task_inline_selectors.html` full-width and
   touch-friendly on `sm`.
4. Single-column fallback for `task_edit.html` and `project_edit.html`.
5. Wrap tabular content in `tasks_list.html`, `project_detail.html`, and
   `settings.html` with `.table-scroll` containers (only the table scrolls,
   not the page).
6. Add `min-width: 0` to flex children where needed and
   `overflow-wrap: anywhere` to long-text elements.
7. Ensure auth pages (`auth_login.html`, `auth_setup.html`) and the
   backup/restore form on `settings.html` work at 320px.
8. Confirm HTMX swaps for quick update, save-and-close, and inline edits
   return fragments that preserve responsive classes and restore focus
   correctly.

Acceptance Criteria:

1. Structural assertions pass: tabular content lives inside `.table-scroll`
   wrappers; no inline `style="width: ..."` declarations exceed 320px on
   pages tested at `sm`; flex children that contained long text have
   `min-width: 0` declared via class.
2. Core flows (add task, complete task, edit task, quick update,
   save-and-close, navigate between views, login, run backup) are
   comfortable one-hand interactions on phone (manual QA).
3. Desktop typography and spacing remain coherent.
4. Every item in the Current Overflow Inventory is resolved or explicitly
   deferred with a written reason recorded in this section.

### Phase 3 — Accessibility, Motion, and HTMX Polish

Goal: maintain quality while improving responsiveness.

Tasks:

1. Verify focus order and visible focus states in adapted nav at all
   breakpoints. Tab order should follow visual order
   (top bar -> main -> bottom bar on `sm`).
2. Ensure icon-only controls expose accessible names via `aria-label` or
   visually-hidden text.
3. Add `prefers-reduced-motion` guards around any nav transitions.
4. Validate color contrast for nav badges and controls in both themes.
   Record measured values in the phase PR description.
5. Verify HTMX fragment swaps preserve focus and do not collapse the bottom
   bar. Test scenarios: completing a task from a list, inline edit save,
   quick update, save-and-close.
6. iOS Safari sanity check: software keyboard does not push the bottom tab
   bar above inputs that live near the bottom of the page. Documented
   fallback: hide bottom bar when an input near the bottom is focused,
   applied only if the issue is observed.

Acceptance Criteria:

1. Keyboard navigation works at all breakpoints.
2. Screen readers identify both nav landmarks correctly.
3. No motion regressions for users preferring reduced motion.
4. HTMX swaps do not break adaptive layout or focus.

### Phase 4 — Documentation and Regression Guardrails

Goal: make adaptive behavior durable and easy to maintain.

Tasks:

1. Update `README.md` with responsive support expectations and the exact
   commands listed under "Test Commands" below.
2. Update `.github/copilot-instructions.md` "Architecture Constraints"
   with: "UI must remain usable without horizontal panning at >= 320px;
   use the three-tier breakpoint strategy in
   `docs/plans/Adaptive-Responsive-UX-Implementation-Plan.md`."
3. Add a short "Responsive Checklist" section to `README.md` for future
   UI changes (links present at all breakpoints, no fixed widths > 320px,
   tap targets >= 44px, safe-area padding for bottom-fixed elements).
4. Ensure the `responsive` pytest marker runs as part of the default
   `uv run pytest` invocation. No new CI jobs required.

Acceptance Criteria:

1. Documentation matches shipped responsive behavior.
2. `uv run pytest` (default invocation) exercises responsive assertions.
3. No new external dependencies introduced.

## Test Strategy

All automated tests use the existing stack: `pytest`, FastAPI `TestClient`,
and HTML parsing from the standard library. No headless browsers.

### Structural / Template-Level Tests (`tests/test_responsive_layout.py`)

1. Assert nav landmarks (`<nav aria-label="Primary">` and
   `<nav aria-label="Sections">`) exist on every authenticated page.
2. Assert critical controls (brand, every primary nav link, settings, theme
   toggle, logout) are present in the rendered DOM and not hidden by
   inline `style="display:none"`. CSS-controlled visibility is verified by
   the CSS contract test below.
3. Assert viewport meta includes both `width=device-width` and
   `viewport-fit=cover`.
4. Assert tabular content lives inside `.table-scroll` wrappers on the
   pages that contain tables.
5. Assert each rendered page contains the breakpoint-specific structural
   classes (`nav-top`, `nav-tabbar`, `nav-utility`).

### CSS Contract Tests (`tests/test_responsive_css.py`)

A small text-level scan over `app/static/app.css` to enforce architecture
rules without a browser. These are heuristics, but cheap and catch the
common regressions:

1. The file declares the three breakpoint markers
   (`bp:sm`, `bp:md`, `bp:lg`) in a leading comment block, and only the
   documented values (`599px`, `899px`, `900px`) appear inside
   `@media (max-width: ...)` and `@media (min-width: ...)` declarations.
2. No declaration outside an `@media (min-width: 900px)` block has
   `min-width:` greater than 320px on selectors targeting top-level layout
   wrappers (configurable list of selectors).
3. Bottom-fixed elements include `env(safe-area-inset-bottom)` in a
   `padding-bottom` or `padding` declaration.
4. Nav button rules at `sm` declare `min-height` and `min-width` >= 44px.

### Manual QA Checklist

Required before marking the initiative complete. Recorded in the closing PR
description.

1. iPhone-class browser portrait and landscape (Safari).
2. Android-class browser portrait (Chrome).
3. Desktop browser at >= 1280px (Chrome and Firefox).
4. Light and dark theme on each.
5. Auth flows: setup, login, logout, theme toggle.
6. Settings and backup/restore.
7. Project create/edit, task create/edit/quick-update/save-and-close.

### Overflow Tolerance

When measuring "no horizontal overflow" manually in devtools:
`document.documentElement.scrollWidth - window.innerWidth <= 1` (allow 1px
for sub-pixel rounding).

## Test Commands

Run the full suite (includes responsive assertions):

```bash
uv run pytest
```

Run only the responsive subset:

```bash
uv run pytest -m responsive
```

Lint and type checks:

```bash
uv run ruff check .
uv run mypy app
```

Local server for manual QA:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

## Performance Budget

1. No new external runtime CSS or JS dependencies.
2. Total nav-related JS additions: < 2 KB unminified.
3. No regressions in initial render: page weight increase < 5 KB gzipped.
4. No layout shift > 0.1 CLS on initial render of key routes
   (verified manually during QA).

## Risks and Mitigations

1. Risk: desktop regressions while fixing phone nav.
   Mitigation: structural tests assert `lg` nav structure; manual desktop
   QA in every phase PR.
2. Risk: CSS complexity growth from one-off media fixes.
   Mitigation: enforce CSS architecture rules; reject ad hoc breakpoints
   in review.
3. Risk: hidden accessibility regressions from nav restructuring.
   Mitigation: Phase 3 explicit keyboard and screen-reader checks; landmark
   assertions.
4. Risk: HTMX fragment swaps drop adaptive classes or focus.
   Mitigation: explicit Phase 3 task; document constraint that swapped
   fragments must include adaptive classes their parent expects.
5. Risk: iOS Safari keyboard pushes fixed bottom bar over inputs.
   Mitigation: Phase 3 sanity check; documented fallback to hide bottom bar
   when an input near the bottom is focused, applied only if observed.
6. Risk: dark-mode contrast regression on new nav surfaces.
   Mitigation: Phase 3 contrast check; record values in the phase PR.
7. Risk: CSRF token loss when restructuring forms inside nav (logout form).
   Mitigation: keep `{{ csrf_hidden_input(request) }}` in the logout form
   regardless of placement; covered by existing auth tests.
8. Risk: heuristic CSS contract tests give false positives or negatives.
   Mitigation: keep them narrow and explicit; rely on manual QA for the
   final visual sign-off.

## Rollout

Single-user app; no feature flag needed. Direct cutover with PR review per
phase. Each phase PR must include before/after screenshots at 320px, 390px,
768px, and 1366px widths attached to the description.

## Definition of Done

This initiative is complete when all of the following are true:

1. Phone users can access all core sections and top controls without
   horizontal page panning at viewport widths >= 320px.
2. Desktop experience remains polished and functionally unchanged.
3. Responsive structural and CSS-contract tests are in place and passing
   as part of the default `uv run pytest`.
4. Documentation (`README.md`, `.github/copilot-instructions.md`, this
   plan) describes adaptive behavior and maintenance expectations.
5. Every item in the Current Overflow Inventory is resolved or explicitly
   deferred with a written reason.
6. No new runtime or test dependencies were added.

## Suggested Execution Order

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4

Do not merge later phases ahead of earlier ones unless a blocker demands a
small prerequisite patch.
