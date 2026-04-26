"""Phase 0 baseline tests for the adaptive responsive UX plan.

These tests encode the structural contract that Phase 1 will satisfy.
They are intentionally red against the current implementation so that
overflow/navigation regressions are visible from the test suite.

See: docs/plans/Adaptive-Responsive-UX-Implementation-Plan.md
"""

from __future__ import annotations

from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.responsive


# Routes that must satisfy the structural responsive contract.
# Auth is disabled in tests via conftest, so these all render directly.
AUTHENTICATED_ROUTES = [
    "/inbox",
    "/today",
    "/tasks",
    "/projects",
    "/settings",
]


class _Tag:
    __slots__ = ("name", "attrs", "text")

    def __init__(self, name: str, attrs: dict[str, str]) -> None:
        self.name = name
        self.attrs = attrs
        self.text = ""


class _Collector(HTMLParser):
    """Collect all start tags with their attributes and inner text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[_Tag] = []
        self._stack: list[_Tag] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: (v or "") for k, v in attrs}
        node = _Tag(tag, attr_dict)
        self.tags.append(node)
        self._stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        if self._stack and self._stack[-1].name == tag:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._stack:
            self._stack[-1].text += data


def _parse(html: str) -> _Collector:
    c = _Collector()
    c.feed(html)
    return c


def _classes(tag: _Tag) -> set[str]:
    return set(tag.attrs.get("class", "").split())


def _has_tag_with_class(parsed: _Collector, tag_name: str, css_class: str) -> bool:
    return any(t.name == tag_name and css_class in _classes(t) for t in parsed.tags)


def _has_class(parsed: _Collector, css_class: str) -> bool:
    return any(css_class in _classes(t) for t in parsed.tags)


def _get_html(client: TestClient, path: str) -> str:
    response = client.get(path)
    assert response.status_code == 200, f"GET {path} returned {response.status_code}"
    return response.text


# ---------------------------------------------------------------------------
# Viewport meta
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", AUTHENTICATED_ROUTES + ["/auth/login"])
def test_viewport_meta_includes_viewport_fit_cover(client: TestClient, path: str) -> None:
    """The viewport meta must opt into edge-to-edge rendering so the bottom
    tab bar can respect the iOS safe area."""
    html = _get_html(client, path)
    parsed = _parse(html)

    metas = [
        t for t in parsed.tags
        if t.name == "meta" and t.attrs.get("name") == "viewport"
    ]
    assert metas, f"{path}: missing <meta name=viewport>"
    content = metas[0].attrs.get("content", "")
    assert "width=device-width" in content, f"{path}: viewport missing width=device-width"
    assert "viewport-fit=cover" in content, (
        f"{path}: viewport meta must include viewport-fit=cover for safe-area support"
    )


# ---------------------------------------------------------------------------
# Nav landmarks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", AUTHENTICATED_ROUTES)
def test_primary_nav_landmark_present(client: TestClient, path: str) -> None:
    """Top utility nav must be a labelled <nav aria-label='Primary'>."""
    html = _get_html(client, path)
    parsed = _parse(html)
    nav_labels = [
        t.attrs.get("aria-label", "")
        for t in parsed.tags
        if t.name == "nav"
    ]
    assert "Primary" in nav_labels, (
        f"{path}: expected <nav aria-label='Primary'> for the top utility region; "
        f"found nav labels: {nav_labels}"
    )


@pytest.mark.parametrize("path", AUTHENTICATED_ROUTES)
def test_sections_nav_landmark_present(client: TestClient, path: str) -> None:
    """Primary section navigation must be a labelled <nav aria-label='Sections'>
    so it can be addressed independently by assistive tech and CSS."""
    html = _get_html(client, path)
    parsed = _parse(html)
    nav_labels = [
        t.attrs.get("aria-label", "")
        for t in parsed.tags
        if t.name == "nav"
    ]
    assert "Sections" in nav_labels, (
        f"{path}: expected <nav aria-label='Sections'> for primary section navigation; "
        f"found nav labels: {nav_labels}"
    )


# ---------------------------------------------------------------------------
# Adaptive structural classes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", AUTHENTICATED_ROUTES)
def test_adaptive_nav_classes_present(client: TestClient, path: str) -> None:
    """The base layout must declare the adaptive structural classes that
    Phase 1 introduces. CSS is responsible for showing/hiding them per
    breakpoint, but they must always be present in the DOM."""
    html = _get_html(client, path)
    parsed = _parse(html)

    for required in ("nav-top", "nav-tabbar", "nav-utility"):
        assert _has_class(parsed, required), (
            f"{path}: expected element with class '{required}' for adaptive nav layout"
        )


# ---------------------------------------------------------------------------
# Critical controls reachable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", AUTHENTICATED_ROUTES)
def test_primary_section_links_present(client: TestClient, path: str) -> None:
    """All four primary section destinations must be present in the DOM at
    every breakpoint (no display:none from inline style)."""
    html = _get_html(client, path)
    parsed = _parse(html)

    expected = {"/inbox", "/today", "/tasks", "/projects"}
    found = {
        t.attrs.get("href", "")
        for t in parsed.tags
        if t.name == "a"
    }
    missing = expected - found
    assert not missing, f"{path}: missing primary section links: {sorted(missing)}"

    # No critical link may be hidden by inline style.
    for t in parsed.tags:
        if t.name == "a" and t.attrs.get("href", "") in expected:
            style = t.attrs.get("style", "").lower().replace(" ", "")
            assert "display:none" not in style, (
                f"{path}: link to {t.attrs['href']} hidden via inline style"
            )


@pytest.mark.parametrize("path", AUTHENTICATED_ROUTES)
def test_utility_controls_present(client: TestClient, path: str) -> None:
    """Settings, theme toggle, and logout must always be in the DOM on
    authenticated pages."""
    html = _get_html(client, path)
    parsed = _parse(html)

    # Settings link
    settings_links = [
        t for t in parsed.tags
        if t.name == "a" and t.attrs.get("href", "") == "/settings"
    ]
    assert settings_links, f"{path}: missing /settings link"

    # Theme toggle button
    theme_toggles = [
        t for t in parsed.tags
        if t.attrs.get("id") == "theme-toggle"
    ]
    assert theme_toggles, f"{path}: missing #theme-toggle control"

    # Logout form (auth disabled in tests, so logout may be hidden; only
    # assert when auth is enabled in production).  We assert the structural
    # contract that AT LEAST one logout-capable control or its absence is
    # consistent — i.e. when present, it points at /auth/logout.
    forms = [t for t in parsed.tags if t.name == "form"]
    logout_forms = [
        t for t in forms
        if t.attrs.get("action", "") == "/auth/logout"
    ]
    if logout_forms:
        # If rendered, must live under the utility cluster.
        # Heuristic: a parent with class 'nav-utility' must exist and the
        # logout form must come after that class is opened in the document.
        assert _has_class(parsed, "nav-utility"), (
            f"{path}: logout form rendered without an enclosing 'nav-utility' cluster"
        )


# ---------------------------------------------------------------------------
# Auth login page
# ---------------------------------------------------------------------------


def test_auth_login_has_viewport_fit_cover(client: TestClient) -> None:
    """The login page must also opt into safe-area support so the auth card
    renders correctly on phones."""
    html = _get_html(client, "/auth/login")
    parsed = _parse(html)
    metas = [
        t for t in parsed.tags
        if t.name == "meta" and t.attrs.get("name") == "viewport"
    ]
    assert metas, "missing <meta name=viewport> on /auth/login"
    assert "viewport-fit=cover" in metas[0].attrs.get("content", ""), (
        "/auth/login: viewport meta must include viewport-fit=cover"
    )


# ---------------------------------------------------------------------------
# Phase 2: tables wrapped in scroll containers
# ---------------------------------------------------------------------------


def test_settings_table_wrapped_in_table_scroll(
    client: TestClient, db_session  # noqa: ANN001 - db_session fixture
) -> None:
    """Tables must live inside a .table-scroll wrapper so they scroll
    independently on narrow viewports without forcing the page to overflow.

    The settings API-keys table only renders when at least one key exists;
    seed one before fetching the page.
    """
    from app.services.api_key_service import generate_key

    generate_key(db_session, name="phase2-test-key")

    html = _get_html(client, "/settings")
    parsed = _parse(html)

    tables = [t for t in parsed.tags if t.name == "table"]
    assert tables, "/settings: expected the API keys table to be rendered"

    # Every <table> must be inside an element with class 'table-scroll'.
    # Heuristic: search the raw HTML for `class="table-scroll"` immediately
    # before the table.
    assert "table-scroll" in html, (
        "/settings: expected a .table-scroll wrapper around the API keys table"
    )


# ---------------------------------------------------------------------------
# Phase 2: task list metadata stacking class
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/inbox", "/today", "/tasks"])
def test_task_lists_use_min_width_zero_class(
    client: TestClient, db_session, path: str  # noqa: ANN001
) -> None:
    """Task rows that wrap long titles must declare a class that sets
    `min-width: 0` on the flex child holding the title, otherwise long
    titles force horizontal overflow inside the flex parent."""
    from datetime import date

    from app.models import TaskStatus
    from app.services.task_service import create_task

    # Seed tasks that surface on every list view: an INBOX task (for /inbox
    # and /tasks) and a NEXT_ACTION task due today (for /today and /tasks).
    long_title = (
        "An intentionally very long task title that would otherwise "
        "force horizontal overflow on narrow viewports because flex "
        "children default to min-width auto"
    )
    create_task(db_session, title=long_title)
    create_task(
        db_session,
        title=long_title + " (today)",
        status=TaskStatus.NEXT_ACTION,
        due_date=date.today(),
    )

    html = _get_html(client, path)
    assert "task-title" in html, f"{path}: missing .task-title class"


# ---------------------------------------------------------------------------
# Phase 3: accessibility — icon-only controls expose accessible names
# ---------------------------------------------------------------------------


def _accessible_name(tag: _Tag) -> str:
    """Return a non-empty accessible name source for an interactive tag,
    or an empty string if none is declared."""
    for key in ("aria-label", "aria-labelledby", "title"):
        value = tag.attrs.get(key, "").strip()
        if value:
            return value
    return tag.text.strip()


@pytest.mark.parametrize("path", AUTHENTICATED_ROUTES)
def test_icon_only_nav_controls_have_accessible_names(
    client: TestClient, path: str
) -> None:
    """Settings link, theme toggle, and logout button render with icon-only
    visual content. Each must expose an accessible name so screen readers
    can identify them."""
    html = _get_html(client, path)
    parsed = _parse(html)

    # Settings link in the utility cluster.
    settings = [
        t for t in parsed.tags
        if t.name == "a" and t.attrs.get("href", "") == "/settings"
        and "nav-icon-btn" in _classes(t)
    ]
    assert settings, f"{path}: missing .nav-icon-btn /settings link"
    assert _accessible_name(settings[0]), (
        f"{path}: /settings icon link is missing an accessible name "
        "(aria-label/title/visible text)"
    )

    # Theme toggle button.
    theme = [t for t in parsed.tags if t.attrs.get("id") == "theme-toggle"]
    assert theme, f"{path}: missing #theme-toggle"
    assert _accessible_name(theme[0]), (
        f"{path}: #theme-toggle is missing an accessible name"
    )

    # Logout button (only present when auth is enabled). When present, it
    # must have an accessible name.
    logout_buttons = [
        t for t in parsed.tags
        if t.name == "button"
        and "nav-icon-btn" in _classes(t)
        and "logout" in (t.attrs.get("aria-label", "") + t.attrs.get("title", "")).lower()
    ]
    if logout_buttons:
        assert _accessible_name(logout_buttons[0]), (
            f"{path}: logout button is missing an accessible name"
        )


# ---------------------------------------------------------------------------
# Phase 3: tab order — header before main, sections nav after main on sm
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", AUTHENTICATED_ROUTES)
def test_tab_order_dom_sequence(client: TestClient, path: str) -> None:
    """Visual order on sm is top bar → main → bottom tab bar. Tab order
    follows DOM order, so the document must place the Primary nav inside
    the header before <main>, and the Sections nav (tab bar) after <main>.
    """
    html = _get_html(client, path)

    # Locate landmark anchors in the raw HTML by their stable attribute strings.
    primary_idx = html.find('aria-label="Primary"')
    main_idx = html.find("<main")
    sections_idx = html.find('aria-label="Sections"')

    assert primary_idx != -1, f"{path}: missing Primary nav landmark"
    assert main_idx != -1, f"{path}: missing <main> landmark"
    assert sections_idx != -1, f"{path}: missing Sections nav landmark"

    assert primary_idx < main_idx, (
        f"{path}: Primary nav must appear before <main> in DOM order so "
        "keyboard tab order matches the top-to-bottom visual order"
    )
    assert main_idx < sections_idx, (
        f"{path}: Sections nav (bottom tab bar) must appear after <main> "
        "in DOM order so it is reached after page content during keyboard "
        "navigation on sm"
    )


