import ast
import sys
from pathlib import Path

# `uv run pytest tests/...` puts only tests/ on sys.path; ai_summary.py lives at the repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import ai_summary  # noqa: E402
import pytest  # noqa: E402
from streamlit.runtime.pages_manager import PagesManager  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

# Absolute: Streamlit 1.64 resolves a relative AppTest.from_file() path against this file,
# not the working directory.
PAGE_PATH = REPO_ROOT / "pages" / "3_🏆_League.py"
PLAYER = "刘北南"


@pytest.fixture(autouse=True)
def _isolate_pages_directory_flag(monkeypatch):
    """Streamlit sets PagesManager.uses_pages_directory once per process, from the first
    AppTest script's folder; pages/3_🏆_League.py's folder has no pages/ inside it. Reset it
    per test and let monkeypatch restore it, so the front-page AppTests in
    tests/test_upcoming_section_visibility.py still see the repository's pages/ folder."""
    monkeypatch.setattr(PagesManager, "uses_pages_directory", None)


def test_league_page_imports_and_calls_summary_once_after_metrics():
    source = PAGE_PATH.read_text(encoding="utf-8")
    assert "from ai_summary import render_season_summary" in source
    tree = ast.parse(source)
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "render_season_summary"
    ]
    assert len(calls) == 1, "the deep-dive must call render_season_summary exactly once"
    call = calls[0]
    assert len(call.args) == 2, "must pass the selected player and that player's season rounds"
    metric_lines = sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "metric"
    )
    preceding = [line for line in metric_lines if line < call.lineno]
    assert len(preceding) >= 4, "the four deep-dive metrics must be rendered above the button"
    lines = source.splitlines()
    between = lines[preceding[-1] : call.lineno - 1]
    assert not any("st." in line for line in between), (
        "no other Streamlit call may sit between the deep-dive metrics and the summary button"
    )


def test_league_page_renders_summary_button_for_selected_player(monkeypatch):
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("test-key", "test-model"))
    at = AppTest.from_file(str(PAGE_PATH), default_timeout=60).run()
    if ai_summary.AI_SUMMARY_BUTTON_LABEL not in [button.label for button in at.button]:
        for widget in list(at.selectbox) + list(at.radio) + list(at.multiselect):
            options = list(getattr(widget, "options", []) or [])
            if PLAYER in options:
                widget.select(PLAYER)
                at.run()
                break
    assert ai_summary.AI_SUMMARY_BUTTON_LABEL in [button.label for button in at.button]
    assert len(at.metric) >= 4
    assert at.exception == []
