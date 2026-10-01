import inspect
import re
from unittest.mock import MagicMock

import pytest

# `uv run pytest tests/...` puts only tests/ on sys.path; ai_summary.py lives at the repo root.
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import ai_summary  # noqa: E402

SUMMARY = "SUMMARY_SENTINEL"


def fake_st(*, submitted: bool = False, question: str = "", language: str | None = None) -> MagicMock:
    fake = MagicMock(name="st")
    fake.session_state = {}
    if language is not None:
        fake.session_state[ai_summary.LANGUAGE_SELECTOR_KEY] = language
    fake.form_submit_button.return_value = submitted
    fake.text_input.return_value = question
    fake.form.return_value = MagicMock(name="form")
    fake.spinner.return_value = MagicMock(name="spinner")
    return fake


def render_follow_up(*args, **kwargs):
    target = getattr(
        ai_summary.render_follow_up_questions,
        "__wrapped__",
        ai_summary.render_follow_up_questions,
    )
    return target(*args, **kwargs)


def markdowns(fake: MagicMock) -> list[str]:
    return [str(call.args[0]) for call in fake.markdown.call_args_list]


def chat_recorder(result: str = "ANSWER_SENTINEL", error: Exception | None = None):
    calls: list[dict] = []

    def _chat(api_key, model, prompt, system_message=ai_summary.SYSTEM_MESSAGE):
        calls.append({"prompt": prompt, "system_message": system_message})
        if error is not None:
            raise error
        return result

    _chat.calls = calls
    return _chat


def exploding(*args, **kwargs):
    raise AssertionError("_call_ollama_chat must not be called in this scenario")


ROUNDS = [{"date": "ROUND_ONE"}]


def _patch(monkeypatch, fake, chat=None, config=("key", "model")):
    monkeypatch.setattr(ai_summary, "st", fake)
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: config)
    monkeypatch.setattr(ai_summary, "_call_ollama_chat", chat if chat is not None else exploding)


def test_fragment_decorator_is_present():
    """Interface requirement."""
    assert re.search(r"@st\.fragment\s*\ndef render_follow_up_questions\(", inspect.getsource(ai_summary))


def test_form_uses_expected_labels(monkeypatch):
    """Spec behaviour 4."""
    fake = fake_st(submitted=False)
    _patch(monkeypatch, fake)

    render_follow_up("杨明", ROUNDS, SUMMARY)

    fake.text_input.assert_called_once_with(ai_summary.FOLLOW_UP_INPUT_LABEL, key=ai_summary.FOLLOW_UP_INPUT_KEY)
    fake.form_submit_button.assert_called_once_with(ai_summary.FOLLOW_UP_BUTTON_LABEL)
    fake.form.assert_called_once_with(ai_summary.FOLLOW_UP_FORM_KEY, clear_on_submit=True)


def test_empty_summary_renders_nothing(monkeypatch):
    """Spec behaviour 5."""
    fake = fake_st(submitted=True, question="q")
    _patch(monkeypatch, fake)

    render_follow_up("杨明", ROUNDS, "")

    fake.text_input.assert_not_called()
    fake.form_submit_button.assert_not_called()
    fake.markdown.assert_not_called()
    assert ai_summary.FOLLOW_UP_HISTORY_KEY not in fake.session_state


def test_empty_question_shows_message_and_keeps_history(monkeypatch):
    """Spec behaviour 6."""
    fake = fake_st(submitted=True, question="   ")
    _patch(monkeypatch, fake)

    render_follow_up("杨明", ROUNDS, SUMMARY)

    fake.warning.assert_called_once_with(ai_summary.EMPTY_QUESTION_MESSAGE)
    assert markdowns(fake) == []
    assert fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY]["turns"] == []


def test_answer_is_displayed_and_stored(monkeypatch):
    """Spec behaviours 7, 8."""
    fake = fake_st(submitted=True, question="为什么他上升了？")
    chat = chat_recorder("ANSWER_SENTINEL")
    _patch(monkeypatch, fake, chat)

    render_follow_up("杨明", ROUNDS, SUMMARY)

    assert markdowns(fake)[-1] == "ANSWER_SENTINEL"
    assert fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY] == {
        "summary": SUMMARY,
        "turns": [{"question": "为什么他上升了？", "answer": "ANSWER_SENTINEL"}],
    }
    assert "SUMMARY_SENTINEL" in chat.calls[0]["prompt"]
    assert "为什么他上升了？" in chat.calls[0]["prompt"]


def test_stored_turns_are_rendered_on_rerun(monkeypatch):
    """Spec behaviour 14."""
    fake = fake_st(submitted=False)
    fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY] = {
        "summary": SUMMARY,
        "turns": [{"question": "q1", "answer": "a1"}, {"question": "q2", "answer": "a2"}],
    }
    _patch(monkeypatch, fake)

    render_follow_up("杨明", ROUNDS, SUMMARY)

    rendered = "\n".join(markdowns(fake))
    for text in ("q1", "a1", "q2", "a2"):
        assert text in rendered


def test_turns_from_another_summary_are_discarded(monkeypatch):
    """Spec behaviour 15."""
    fake = fake_st(submitted=False)
    fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY] = {
        "summary": "OLD_SUMMARY",
        "turns": [{"question": "OLD_Q", "answer": "OLD_A"}],
    }
    _patch(monkeypatch, fake)

    render_follow_up("杨明", ROUNDS, SUMMARY)

    assert "OLD_Q" not in "\n".join(markdowns(fake))
    assert fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY] == {"summary": SUMMARY, "turns": []}


def test_missing_config_shows_message_and_keeps_history(monkeypatch):
    """Spec behaviour 11."""
    fake = fake_st(submitted=True, question="q")
    _patch(monkeypatch, fake, config=("", ""))

    render_follow_up("杨明", ROUNDS, SUMMARY)

    fake.error.assert_called_once_with(ai_summary.MISSING_CONFIG_MESSAGE)
    assert fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY]["turns"] == []


def test_chat_error_shows_message_and_keeps_history(monkeypatch):
    """Spec behaviour 12."""
    message = ai_summary.CALL_FAILED_MESSAGE.format(detail="HTTP 500")
    fake = fake_st(submitted=True, question="q")
    _patch(monkeypatch, fake, chat_recorder(error=ai_summary.AISummaryError(message)))

    assert render_follow_up("杨明", ROUNDS, SUMMARY) is None
    fake.error.assert_called_once_with(message)
    assert fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY]["turns"] == []


def test_empty_response_shows_message(monkeypatch):
    """Spec behaviour 12."""
    fake = fake_st(submitted=True, question="q")
    _patch(monkeypatch, fake, chat_recorder("   "))

    render_follow_up("杨明", ROUNDS, SUMMARY)

    fake.error.assert_called_once_with(ai_summary.EMPTY_RESPONSE_MESSAGE)
    assert fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY]["turns"] == []


def test_missing_rounds_note_is_sent_and_answer_displayed(monkeypatch):
    """Spec behaviour 13."""
    fake = fake_st(submitted=True, question="q")
    chat = chat_recorder("A")
    _patch(monkeypatch, fake, chat)

    render_follow_up("杨明", None, SUMMARY)

    assert ai_summary.MISSING_ROUNDS_NOTE in chat.calls[0]["prompt"]
    assert "A" in markdowns(fake)


def test_english_language_uses_english_system_message(monkeypatch):
    """Spec behaviour 10."""
    fake = fake_st(submitted=True, question="q", language=ai_summary.LANGUAGE_ENGLISH)
    chat = chat_recorder("A")
    _patch(monkeypatch, fake, chat)

    render_follow_up("杨明", ROUNDS, SUMMARY)

    assert chat.calls[0]["system_message"] == ai_summary.SYSTEM_MESSAGE_EN
    assert ai_summary.FOLLOW_UP_INSTRUCTION_EN in chat.calls[0]["prompt"]
