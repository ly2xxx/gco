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


@pytest.fixture(autouse=True)
def _isolate_pages_directory_flag(monkeypatch):
    """Streamlit sets PagesManager.uses_pages_directory once per process, from the first
    AppTest script's folder. The harness script lives in a temp folder without pages/, so
    reset the flag per test and let monkeypatch restore it: otherwise this module and
    page-level AppTests (tests/test_upcoming_section_visibility.py) break each other."""
    monkeypatch.setattr(PagesManager, "uses_pages_directory", None)

ROUNDS = [
    {"Game": "Game 1", "Net_Score": -8, "Birdies": 3, "Pars": 8},
    {"Game": "Game 2", "Net_Score": 3, "Birdies": 2, "Pars": 10},
]
SUMMARY_TEXT = "本赛季你的整体表现稳定，第 1 轮净杆 -8 是亮点。"
SECOND_TEXT = "第二次生成：整体发挥稳定。"


def _harness_script(player_name: str, rounds) -> str:
    return (
        "import streamlit as st\n"
        "import ai_summary\n"
        'st.metric("场均净杆", "-2.5")\n'
        'st.metric("总小鸟球", "5")\n'
        'st.metric("平均保帕", "9")\n'
        'st.metric("比赛轮次", "2")\n'
        f"ai_summary.render_season_summary({player_name!r}, {rounds!r})\n"
    )


def _run(player_name: str = "刘北南", rounds=ROUNDS, timeout: float = 10) -> AppTest:
    return AppTest.from_string(_harness_script(player_name, rounds), default_timeout=timeout).run()


def _configure(monkeypatch, api_key: str = "test-key", model: str = "test-model") -> None:
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: (api_key, model))


def _record_transport(monkeypatch, result=SUMMARY_TEXT) -> list:
    calls: list = []

    def fake(api_key, model, prompt):
        calls.append({"api_key": api_key, "model": model, "prompt": prompt})
        return result

    monkeypatch.setattr(ai_summary, "_call_ollama_chat", fake)
    return calls


def test_button_rendered_below_metrics_with_nothing_shown_before_press(monkeypatch):
    """Spec behaviours 1, 2, 3."""
    _configure(monkeypatch)
    calls: list = []
    monkeypatch.setattr(ai_summary, "summarize_season", lambda *args: calls.append(args) or SUMMARY_TEXT)

    at = _run()

    assert len(at.metric) == 4
    assert [b.label for b in at.button] == [ai_summary.AI_SUMMARY_BUTTON_LABEL]
    assert calls == []
    assert at.error == [] and at.warning == [] and at.exception == []
    assert all(SUMMARY_TEXT not in m.value for m in at.markdown)


def test_page_renders_without_ai_secrets_before_press():
    """Spec behaviour 3: the real guarded st.secrets lookup, no secrets configured."""
    at = _run()

    assert len(at.metric) == 4
    assert ai_summary.AI_SUMMARY_BUTTON_LABEL in [b.label for b in at.button]
    assert at.error == []
    assert at.warning == []
    assert at.exception == []


def test_button_not_rendered_without_player(monkeypatch):
    """Spec behaviour 13."""
    _configure(monkeypatch)

    at = _run(player_name="")

    assert len(at.button) == 0
    assert at.error == [] and at.warning == [] and at.exception == []


def test_press_renders_exact_summary_text(monkeypatch):
    """Spec behaviours 4, 12."""
    _configure(monkeypatch)
    calls = _record_transport(monkeypatch)

    at = _run()
    at.button[0].click().run()

    assert len(calls) == 1
    assert calls[0]["api_key"] == "test-key"
    assert calls[0]["model"] == "test-model"
    assert "刘北南" in calls[0]["prompt"]
    assert SUMMARY_TEXT in [m.value for m in at.markdown]
    assert at.error == []
    assert at.exception == []


def test_summary_flow_needs_no_admin_token(monkeypatch):
    """Spec behaviour 12."""
    _configure(monkeypatch)
    monkeypatch.setattr(ai_summary, "_call_ollama_chat", lambda *args: SUMMARY_TEXT)
    source = Path(ai_summary.__file__).read_text(encoding="utf-8")
    assert "import auth" not in source
    assert "is_admin_user" not in source

    at = _run()
    at.button[0].click().run()

    assert SUMMARY_TEXT in [m.value for m in at.markdown]
    assert at.exception == []


def test_press_twice_issues_two_independent_requests(monkeypatch):
    """Spec behaviour 11."""
    _configure(monkeypatch)
    responses = iter([SUMMARY_TEXT, SECOND_TEXT])
    calls: list = []
    monkeypatch.setattr(ai_summary, "_call_ollama_chat", lambda *args: calls.append(args) or next(responses))

    at = _run()
    at.button[0].click().run()
    assert SUMMARY_TEXT in [m.value for m in at.markdown]

    at.button[0].click().run()
    assert len(calls) == 2
    assert SECOND_TEXT in [m.value for m in at.markdown]


def test_press_without_secrets_shows_error_and_makes_no_request(monkeypatch):
    """Spec behaviour 7."""
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("", ""))
    calls = _record_transport(monkeypatch)

    at = _run()
    at.button[0].click().run()

    assert calls == []
    assert ai_summary.MISSING_CONFIG_MESSAGE in [e.value for e in at.error]
    assert at.exception == []
    assert all(SUMMARY_TEXT not in m.value for m in at.markdown)


def test_press_with_failing_call_shows_error_and_no_exception(monkeypatch):
    """Spec behaviour 8."""
    _configure(monkeypatch)

    def failing(api_key, model, prompt):
        raise ai_summary.AISummaryError(ai_summary.CALL_FAILED_MESSAGE.format(detail="HTTP 500"))

    monkeypatch.setattr(ai_summary, "_call_ollama_chat", failing)

    at = _run()
    at.button[0].click().run()

    assert at.exception == []
    assert any("HTTP 500" in e.value for e in at.error)


def test_press_with_zero_rounds_shows_no_rounds_message(monkeypatch):
    """Spec behaviour 9."""
    _configure(monkeypatch)
    calls = _record_transport(monkeypatch)

    at = _run(rounds=[])
    at.button[0].click().run()

    assert calls == []
    assert [w.value for w in at.warning] == [ai_summary.NO_ROUNDS_MESSAGE]
    assert at.error == []
    assert at.exception == []


def test_press_with_blank_response_shows_error(monkeypatch):
    """Spec behaviour 10."""
    _configure(monkeypatch)
    _record_transport(monkeypatch, result="   ")

    at = _run()
    at.button[0].click().run()

    assert ai_summary.EMPTY_RESPONSE_MESSAGE in [e.value for e in at.error]
    assert at.exception == []
