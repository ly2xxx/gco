from unittest.mock import MagicMock

import pytest

# `uv run pytest tests/...` puts only tests/ on sys.path; ai_summary.py lives at the repo root.
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import ai_summary  # noqa: E402


def make_fake_streamlit(*, pressed: bool = False, language: str = ai_summary.DEFAULT_LANGUAGE) -> MagicMock:
    fake = MagicMock(name="st")
    fake.session_state = {}
    fake.columns.return_value = [MagicMock(name="language_column"), MagicMock(name="button_column")]
    fake.radio.return_value = language
    fake.button.return_value = pressed
    fake.spinner.return_value = MagicMock(name="spinner")
    return fake


def exploding(*args, **kwargs):
    raise AssertionError("summarize_season must not be called in this scenario")


ROUNDS = [{"date": "ROUND_ONE"}]


def test_returns_summary_text_when_button_pressed(monkeypatch):
    """Spec behaviour 1."""
    fake = make_fake_streamlit(pressed=True)
    monkeypatch.setattr(ai_summary, "st", fake)
    monkeypatch.setattr(ai_summary, "summarize_season", lambda player, rounds, language: "SUMMARY_SENTINEL")

    assert ai_summary.render_season_summary("杨明", ROUNDS) == "SUMMARY_SENTINEL"
    fake.markdown.assert_called_once_with("SUMMARY_SENTINEL")
    fake.warning.assert_not_called()
    fake.error.assert_not_called()


def test_returns_empty_when_player_name_is_empty(monkeypatch):
    """Spec behaviour 2."""
    fake = make_fake_streamlit(pressed=True)
    monkeypatch.setattr(ai_summary, "st", fake)
    monkeypatch.setattr(ai_summary, "summarize_season", exploding)

    assert ai_summary.render_season_summary("", ROUNDS) == ""
    fake.columns.assert_not_called()


def test_returns_empty_when_button_not_pressed(monkeypatch):
    """Spec behaviour 2."""
    fake = make_fake_streamlit(pressed=False)
    monkeypatch.setattr(ai_summary, "st", fake)
    monkeypatch.setattr(ai_summary, "summarize_season", exploding)

    assert ai_summary.render_season_summary("杨明", ROUNDS) == ""
    fake.markdown.assert_not_called()


def test_returns_empty_when_no_rounds(monkeypatch):
    """Spec behaviour 2."""
    fake = make_fake_streamlit(pressed=True)
    monkeypatch.setattr(ai_summary, "st", fake)
    monkeypatch.setattr(ai_summary, "summarize_season", exploding)

    assert ai_summary.render_season_summary("杨明", []) == ""
    fake.warning.assert_called_once_with(ai_summary.NO_ROUNDS_MESSAGE)


def test_returns_empty_when_summarize_raises(monkeypatch):
    """Spec behaviour 2."""
    fake = make_fake_streamlit(pressed=True)
    monkeypatch.setattr(ai_summary, "st", fake)

    def raising_summarize(*args, **kwargs):
        raise ai_summary.AISummaryError(ai_summary.MISSING_CONFIG_MESSAGE)

    monkeypatch.setattr(ai_summary, "summarize_season", raising_summarize)

    assert ai_summary.render_season_summary("杨明", ROUNDS) == ""
    fake.error.assert_called_once_with(ai_summary.MISSING_CONFIG_MESSAGE)
    fake.markdown.assert_not_called()


def test_selected_language_is_passed_to_summarize_season(monkeypatch):
    """Spec behaviour 2: the radio value still reaches summarize_season unchanged."""
    fake = make_fake_streamlit(pressed=True, language=ai_summary.LANGUAGE_ENGLISH)
    monkeypatch.setattr(ai_summary, "st", fake)
    calls = []

    def recorder(player_name, season_rounds, language):
        calls.append((player_name, season_rounds, language))
        return "S"

    monkeypatch.setattr(ai_summary, "summarize_season", recorder)

    assert ai_summary.render_season_summary("杨明", ROUNDS) == "S"
    assert calls == [("杨明", ROUNDS, ai_summary.LANGUAGE_ENGLISH)]
