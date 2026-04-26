"""Phase 0 baseline tests for CSS architecture rules.

These are heuristic, text-level scans over `app/static/app.css` that enforce
the adaptive UX plan's CSS architecture rules without requiring a browser.

See: docs/plans/Adaptive-Responsive-UX-Implementation-Plan.md
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.responsive


CSS_PATH = Path(__file__).resolve().parent.parent / "app" / "static" / "app.css"

# Documented breakpoint values from the plan.
ALLOWED_BREAKPOINT_PX = {599, 899, 900}


@pytest.fixture(scope="module")
def css_text() -> str:
    return CSS_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Breakpoint markers
# ---------------------------------------------------------------------------


def test_breakpoint_marker_comment_block_present(css_text: str) -> None:
    """A leading comment block must declare the canonical breakpoint
    markers so the CSS file documents its own architecture."""
    head = css_text[:2000]
    for marker in ("bp:sm", "bp:md", "bp:lg"):
        assert marker in head, (
            f"app.css: missing '{marker}' marker in leading comment block "
            "(declare bp:sm, bp:md, bp:lg with their pixel values)"
        )


def test_only_documented_breakpoint_values_used(css_text: str) -> None:
    """Every @media (max-width|min-width: Npx) must use a documented value.

    Allowed values: 599, 899, 900. Ad hoc breakpoints require a removal or
    a documented exception — for now we enforce strictly.
    """
    pattern = re.compile(
        r"@media[^{]*\(\s*(?:max|min)-width\s*:\s*(\d+)px\s*\)",
        re.IGNORECASE,
    )
    found = {int(m.group(1)) for m in pattern.finditer(css_text)}
    bad = found - ALLOWED_BREAKPOINT_PX
    assert not bad, (
        f"app.css: undocumented @media breakpoint values: {sorted(bad)}; "
        f"allowed: {sorted(ALLOWED_BREAKPOINT_PX)}"
    )


# ---------------------------------------------------------------------------
# Bottom-fixed safe-area padding
# ---------------------------------------------------------------------------


def test_tabbar_uses_safe_area_inset_bottom(css_text: str) -> None:
    """The bottom tab bar must include env(safe-area-inset-bottom) padding
    so it renders correctly above the iOS home indicator."""
    # Find the .nav-tabbar rule block (first occurrence is enough for Phase 0).
    match = re.search(
        r"\.nav-tabbar\s*\{([^}]*)\}",
        css_text,
        re.DOTALL,
    )
    assert match, (
        "app.css: missing .nav-tabbar rule block (Phase 1 introduces the bottom tab bar)"
    )
    body = match.group(1)
    assert "safe-area-inset-bottom" in body, (
        "app.css: .nav-tabbar must include env(safe-area-inset-bottom) padding"
    )


# ---------------------------------------------------------------------------
# Tap-target sizing on phone
# ---------------------------------------------------------------------------


def test_phone_nav_buttons_meet_tap_target_size(css_text: str) -> None:
    """At the `sm` breakpoint, nav controls must declare min-height and
    min-width >= 44px (WCAG 2.5.8 spacing applies separately)."""
    # Locate the @media (max-width: 599px) block.
    match = re.search(
        r"@media[^{]*\(\s*max-width\s*:\s*599px\s*\)\s*\{",
        css_text,
        re.IGNORECASE,
    )
    assert match, (
        "app.css: missing @media (max-width: 599px) block for sm breakpoint"
    )
    # Extract the block body using brace counting.
    start = match.end()
    depth = 1
    i = start
    while i < len(css_text) and depth > 0:
        ch = css_text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    block = css_text[start : i - 1]

    # Within the sm block, nav-utility buttons and tab-bar items must
    # declare 44px minimums.
    nav_rules = re.findall(
        r"(\.nav-icon-btn|\.nav-tabbar\s+a|\.nav-tabbar\s+button)\s*\{([^}]*)\}",
        block,
        re.DOTALL,
    )
    assert nav_rules, (
        "app.css: sm block must declare sizing rules for .nav-icon-btn and "
        ".nav-tabbar a/button (>= 44px tap targets)"
    )

    px_pattern = re.compile(r"(\d+(?:\.\d+)?)px")
    for selector, body in nav_rules:
        for prop in ("min-height", "min-width"):
            prop_match = re.search(rf"{prop}\s*:\s*([^;]+);", body)
            assert prop_match, (
                f"app.css [sm] {selector}: missing {prop} declaration"
            )
            value = prop_match.group(1)
            sizes = [float(p) for p in px_pattern.findall(value)]
            assert sizes and max(sizes) >= 44, (
                f"app.css [sm] {selector}: {prop} must be >= 44px (got '{value.strip()}')"
            )


# ---------------------------------------------------------------------------
# No oversized min-width on top-level wrappers outside lg
# ---------------------------------------------------------------------------


# Selectors that gate page width.  If these declare min-width > 320px outside
# an `lg` (min-width: 900px) block, narrow viewports will overflow.
TOP_LEVEL_WRAPPERS = (
    ".shell",
    ".top-nav",
    "body",
    "main",
)


def test_no_oversized_min_width_on_top_level_wrappers(css_text: str) -> None:
    """Top-level wrappers must not declare min-width > 320px in the base
    cascade (outside an lg-only @media block)."""
    # Strip any @media (min-width: 900px) blocks before scanning the base
    # cascade so lg-only declarations are exempt.
    def _strip_lg_blocks(text: str) -> str:
        out: list[str] = []
        i = 0
        pattern = re.compile(
            r"@media[^{]*\(\s*min-width\s*:\s*900px\s*\)\s*\{",
            re.IGNORECASE,
        )
        while i < len(text):
            m = pattern.search(text, i)
            if not m:
                out.append(text[i:])
                break
            out.append(text[i : m.start()])
            depth = 1
            j = m.end()
            while j < len(text) and depth > 0:
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                j += 1
            i = j
        return "".join(out)

    base = _strip_lg_blocks(css_text)

    # For each wrapper, find every rule whose selector list contains it and
    # check its min-width declaration.
    px_pattern = re.compile(r"min-width\s*:\s*(\d+(?:\.\d+)?)px")
    rule_pattern = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
    offenders: list[str] = []
    for sel_match in rule_pattern.finditer(base):
        selectors = sel_match.group(1)
        body = sel_match.group(2)
        for wrapper in TOP_LEVEL_WRAPPERS:
            # Match wrapper as a standalone selector token.
            if re.search(rf"(^|[\s,>+~]){re.escape(wrapper)}(\s*[,{{]|$)", selectors):
                for px in px_pattern.findall(body):
                    if float(px) > 320:
                        offenders.append(
                            f"{selectors.strip()}: min-width {px}px (> 320px)"
                        )
    assert not offenders, (
        "app.css: top-level wrappers declare oversized min-width outside lg:\n  "
        + "\n  ".join(offenders)
    )


# ---------------------------------------------------------------------------
# Phase 2: layout contract for narrow viewports
# ---------------------------------------------------------------------------


def _extract_block(text: str, opener_pattern: str) -> str:
    """Return the body of the first CSS block whose header matches
    `opener_pattern` (a regex). Empty string if not found."""
    match = re.search(opener_pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    start = match.end()
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    return text[start : i - 1]


def test_table_scroll_wrapper_rule_present(css_text: str) -> None:
    """`.table-scroll` must declare horizontal-only overflow so wide tables
    scroll inside the wrapper instead of forcing the page to scroll."""
    body = _extract_block(css_text, r"\.table-scroll\s*\{")
    assert body, "app.css: missing .table-scroll rule block"
    assert "overflow-x" in body, (
        "app.css: .table-scroll must declare overflow-x (auto|scroll)"
    )


def test_task_title_has_min_width_zero(css_text: str) -> None:
    """`.task-title` lives inside a flex `.task-header`. Without
    `min-width: 0`, long titles force the flex parent wider than the
    viewport on narrow widths."""
    # Find any rule whose selector list contains `.task-title` at the top
    # level (not inside a media block we care about) and check for
    # `min-width: 0`.
    pattern = re.compile(r"([^{}]*\.task-title[^{}]*)\{([^}]*)\}", re.DOTALL)
    found_min_width_zero = False
    for m in pattern.finditer(css_text):
        body = m.group(2)
        if re.search(r"min-width\s*:\s*0\b", body):
            found_min_width_zero = True
            break
    assert found_min_width_zero, (
        "app.css: expected a .task-title rule declaring min-width: 0 "
        "to prevent overflow inside flex .task-header"
    )


def test_inline_selectors_full_width_on_sm(css_text: str) -> None:
    """Within the `sm` block, inline quick-update selectors must be allowed
    to take the full available width so they remain touch-friendly."""
    sm_block = _extract_block(
        css_text,
        r"@media[^{]*\(\s*max-width\s*:\s*599px\s*\)\s*\{",
    )
    assert sm_block, "app.css: missing sm media block"
    # Look for a rule that targets .inline-select / .inline-date / .inline-form
    # and declares either width: 100% or flex: 1 / min-width: 0.
    pattern = re.compile(
        r"(\.inline-select|\.inline-date|\.inline-form|\.inline-selector)"
        r"[^{}]*\{([^}]*)\}",
        re.DOTALL,
    )
    matches = list(pattern.finditer(sm_block))
    assert matches, (
        "app.css [sm]: expected inline-* rules sizing inline quick-update "
        "controls for narrow viewports"
    )
    sizing_ok = any(
        re.search(r"width\s*:\s*100%|flex\s*:\s*1", m.group(2))
        for m in matches
    )
    assert sizing_ok, (
        "app.css [sm]: expected inline-* rules to declare width: 100% "
        "or flex: 1 for full-width inline selectors on phone"
    )

