from unittest.mock import MagicMock

import pandas as pd
import pytest

# `uv run pytest tests/...` puts only tests/ on sys.path; ai_summary.py lives at the repo root.
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import ai_summary  # noqa: E402


def fake_st() -> MagicMock:
    fake = MagicMock(name="st")
    fake.session_state = {}
    return fake


def chat_recorder(result: str = "ANSWER_SENTINEL", error: Exception | None = None):
    calls: list[dict] = []

    def _chat(api_key, model, prompt, system_message=ai_summary.SYSTEM_MESSAGE):
        calls.append({"api_key": api_key, "model": model, "prompt": prompt, "system_message": system_message})
        if error is not None:
            raise error
        return result

    _chat.calls = calls
    return _chat


def exploding(*args, **kwargs):
    raise AssertionError("_call_ollama_chat must not be called in this scenario")


def test_prompt_contains_summary_rounds_history_and_question():
    """Spec behaviour 8."""
    prompt = ai_summary.build_follow_up_prompt(
        "杨明",
        [{"date": "ROUND_ONE_DATE", "net": 72}, {"date": "ROUND_TWO_DATE", "net": 80}],
        "SUMMARY_SENTINEL",
        [{"question": "Q1_SENTINEL", "answer": "A1_SENTINEL"}],
        "QUESTION_SENTINEL",
    )
    for marker in ("SUMMARY_SENTINEL", "ROUND_ONE_DATE", "ROUND_TWO_DATE", "Q1_SENTINEL", "A1_SENTINEL", "QUESTION_SENTINEL", "72"):
        assert marker in prompt
    assert ai_summary.FOLLOW_UP_INSTRUCTION in prompt
    assert "ROUND_THREE_DATE" not in prompt


def test_prompt_keeps_only_the_newest_history_turns():
    """Spec behaviour 9."""
    history = [{"question": f"turn-{i}-q", "answer": f"turn-{i}-a"} for i in range(1, 9)]

    prompt = ai_summary.build_follow_up_prompt("p", [{"date": "d"}], "s", history, "q")

    assert "turn-8-q" in prompt
    assert "turn-3-q" in prompt
    assert "turn-1-q" not in prompt
    assert "turn-2-a" not in prompt


def test_prompt_accepts_a_dataframe_and_lists_each_row():
    """Spec behaviour 8."""
    prompt = ai_summary.build_follow_up_prompt(
        "p", pd.DataFrame([{"date": "DF_ROW_ONE"}, {"date": "DF_ROW_TWO"}]), "s", [], "q"
    )

    assert "DF_ROW_ONE" in prompt
    assert "DF_ROW_TWO" in prompt


def test_prompt_notes_missing_rounds():
    """Spec behaviour 13."""
    assert ai_summary.MISSING_ROUNDS_NOTE in ai_summary.build_follow_up_prompt("p", [], "s", [], "q")

    english = ai_summary.build_follow_up_prompt("p", [], "s", [], "q", language=ai_summary.LANGUAGE_ENGLISH)
    assert ai_summary.MISSING_ROUNDS_NOTE_EN in english
    assert ai_summary.MISSING_ROUNDS_NOTE not in english


def test_prompt_uses_english_instruction_for_english():
    """Spec behaviour 10."""
    english = ai_summary.build_follow_up_prompt("p", [{"d": 1}], "s", [], "q", language=ai_summary.LANGUAGE_ENGLISH)
    chinese = ai_summary.build_follow_up_prompt("p", [{"d": 1}], "s", [], "q")

    assert ai_summary.FOLLOW_UP_INSTRUCTION_EN in english
    assert ai_summary.FOLLOW_UP_INSTRUCTION not in english
    assert ai_summary.FOLLOW_UP_INSTRUCTION in chinese
    assert ai_summary.FOLLOW_UP_INSTRUCTION_EN not in chinese


def test_prompt_never_raises():
    """Interface guarantee: arbitrary input still returns a string."""
    assert isinstance(ai_summary.build_follow_up_prompt("p", None, None, None, None), str)
    assert isinstance(ai_summary.build_follow_up_prompt("p", object(), "s", object(), "q"), str)


def test_answer_raises_for_empty_question_without_calling_chat(monkeypatch):
    """Spec behaviour 6."""
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("key", "model"))
    monkeypatch.setattr(ai_summary, "_call_ollama_chat", exploding)

    for question in ("", "   "):
        with pytest.raises(ai_summary.AISummaryError) as exc:
            ai_summary.answer_follow_up_question("p", [{"d": 1}], "s", [], question)
        assert str(exc.value) == ai_summary.EMPTY_QUESTION_MESSAGE


def test_answer_raises_when_config_is_missing(monkeypatch):
    """Spec behaviour 11."""
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("", ""))
    monkeypatch.setattr(ai_summary, "_call_ollama_chat", exploding)

    with pytest.raises(ai_summary.AISummaryError) as exc:
        ai_summary.answer_follow_up_question("p", [{"d": 1}], "s", [], "q")
    assert str(exc.value) == ai_summary.MISSING_CONFIG_MESSAGE


def test_answer_uses_the_selected_language_system_message(monkeypatch):
    """Spec behaviour 10."""
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("key", "model"))
    chat = chat_recorder("A")
    monkeypatch.setattr(ai_summary, "_call_ollama_chat", chat)

    assert ai_summary.answer_follow_up_question("p", [{"d": 1}], "s", [], "q", language=ai_summary.LANGUAGE_ENGLISH) == "A"
    assert chat.calls[-1]["system_message"] == ai_summary.SYSTEM_MESSAGE_EN

    assert ai_summary.answer_follow_up_question("p", [{"d": 1}], "s", [], "q") == "A"
    assert chat.calls[-1]["system_message"] == ai_summary.SYSTEM_MESSAGE


def test_answer_propagates_chat_error(monkeypatch):
    """Spec behaviour 12."""
    message = ai_summary.CALL_FAILED_MESSAGE.format(detail="HTTP 500")
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("key", "model"))
    monkeypatch.setattr(ai_summary, "_call_ollama_chat", chat_recorder(error=ai_summary.AISummaryError(message)))

    with pytest.raises(ai_summary.AISummaryError) as exc:
        ai_summary.answer_follow_up_question("p", [{"d": 1}], "s", [], "q")
    assert str(exc.value) == message


def test_answer_raises_on_empty_response(monkeypatch):
    """Spec behaviour 12."""
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("key", "model"))
    monkeypatch.setattr(ai_summary, "_call_ollama_chat", chat_recorder("   "))

    with pytest.raises(ai_summary.AISummaryError) as exc:
        ai_summary.answer_follow_up_question("p", [{"d": 1}], "s", [], "q")
    assert str(exc.value) == ai_summary.EMPTY_RESPONSE_MESSAGE


def test_history_starts_empty_and_records_the_summary(monkeypatch):
    """Spec behaviour 14 (foundation)."""
    fake = fake_st()
    monkeypatch.setattr(ai_summary, "st", fake)

    assert ai_summary.get_follow_up_history("S1") == []
    assert fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY] == {"summary": "S1", "turns": []}


def test_append_and_get_round_trip(monkeypatch):
    """Spec behaviour 14."""
    monkeypatch.setattr(ai_summary, "st", fake_st())

    ai_summary.append_follow_up_turn("S1", "q1", "a1")
    ai_summary.append_follow_up_turn("S1", "q2", "a2")

    assert ai_summary.get_follow_up_history("S1") == [
        {"question": "q1", "answer": "a1"},
        {"question": "q2", "answer": "a2"},
    ]


def test_history_is_discarded_when_summary_differs(monkeypatch):
    """Spec behaviour 15."""
    fake = fake_st()
    monkeypatch.setattr(ai_summary, "st", fake)
    ai_summary.append_follow_up_turn("S1", "q1", "a1")
    ai_summary.append_follow_up_turn("S1", "q2", "a2")

    assert ai_summary.get_follow_up_history("S2") == []
    assert fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY]["summary"] == "S2"
    assert ai_summary.get_follow_up_history("S1") == []


def test_history_helpers_never_raise_without_session_state(monkeypatch):
    """Interface guarantee."""

    class _Broken:
        @property
        def session_state(self):
            raise RuntimeError("no session state")

    monkeypatch.setattr(ai_summary, "st", _Broken())

    assert ai_summary.get_follow_up_history("S") == []
    assert ai_summary.append_follow_up_turn("S", "q", "a") is None
