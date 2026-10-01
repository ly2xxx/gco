import re
import subprocess
import sys
from pathlib import Path

import pytest

# `uv run pytest tests/...` puts only tests/ on sys.path; theme.py lives at the repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import theme  # noqa: E402

APPROVED_TAG = "sdlc/008-league-ai-summary-add-a-download/approved"
RULE_RE = re.compile(r"(?P<selector>[^{}]+)\{(?P<body>[^{}]*)\}")
BUTTON_DECLARATIONS = (
    "background: linear-gradient(135deg, var(--green-mid), var(--green-light)) !important;",
    "color: #fff !important;",
    "border: none !important;",
    "border-radius: 8px !important;",
    "font-weight: 600 !important;",
    "transition: transform .15s, box-shadow .15s;",
)
HOVER_DECLARATIONS = (
    "transform: translateY(-2px);",
    "box-shadow: 0 6px 20px rgba(82,183,136,.35) !important;",
)
NEW_BUTTON_SELECTORS = (
    '[data-testid="stFormSubmitButton"] button',
    '[data-testid="stDownloadButton"] button',
)


def _rules(css: str) -> list[tuple[str, str]]:
    return [
        (match.group("selector").strip(), match.group("body").strip())
        for match in RULE_RE.finditer(css)
    ]


def _rule_for(css: str, selector_fragment: str, *, hover: bool) -> tuple[str, str]:
    found = [
        (selector, body)
        for selector, body in _rules(css)
        if selector_fragment in selector and ("hover" in selector) == hover
    ]
    assert len(found) == 1, f"expected exactly one rule for {selector_fragment}"
    return found[0]


def _approved_theme_css() -> str | None:
    result = subprocess.run(
        ["git", "show", f"{APPROVED_TAG}:theme.py"],
        capture_output=True, text=True, check=False, cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        return None
    match = re.search(r'THEME_CSS = """(.*?)"""', result.stdout, re.DOTALL)
    return match.group(1) if match else None


def test_form_submit_and_download_selectors_share_the_green_button_rule():
    """Spec behaviours 16, 17."""
    for fragment in NEW_BUTTON_SELECTORS:
        selector, body = _rule_for(theme.THEME_CSS, fragment, hover=False)
        assert ".stButton > button" in selector
        for declaration in BUTTON_DECLARATIONS:
            assert declaration in body

        selector, body = _rule_for(theme.THEME_CSS, fragment, hover=True)
        assert ".stButton > button" in selector
        for declaration in HOVER_DECLARATIONS:
            assert declaration in body


def test_button_declarations_are_unchanged():
    """Spec behaviour 18 for the button rules."""
    _, body = _rule_for(theme.THEME_CSS, ".stButton > button", hover=False)
    for declaration in BUTTON_DECLARATIONS:
        assert declaration in body

    _, body = _rule_for(theme.THEME_CSS, ".stButton > button", hover=True)
    for declaration in HOVER_DECLARATIONS:
        assert declaration in body


def test_non_button_rules_are_unchanged():
    """Spec behaviour 18 for every other rule."""
    old_css = _approved_theme_css()
    if old_css is None:
        pytest.skip(f"approved tag {APPROVED_TAG} is not available in this checkout")

    new_rules = _rules(theme.THEME_CSS)
    assert len(new_rules) == len(_rules(old_css))
    for selector, body in _rules(old_css):
        if "stButton" not in selector:
            assert (selector, body) in new_rules
