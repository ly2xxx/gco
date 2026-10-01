import contextlib
import sys
from pathlib import Path

import pytest

# `uv run pytest tests/...` puts only tests/ on sys.path; ai_summary.py lives at the repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import ai_summary  # noqa: E402


class FakeStreamlit:
    """Minimal stand-in for the streamlit module used by ai_summary's fragment."""

    def __init__(self, *, submit: bool = False, download: bool = False) -> None:
        self.session_state: dict = {}
        self.calls: list[tuple[str, dict]] = []
        self._submit = submit
        self._download = download

    def form(self, *args, **kwargs):
        self.calls.append(("form", {"args": args, "kwargs": kwargs}))
        return contextlib.nullcontext()

    def spinner(self, *args, **kwargs):
        self.calls.append(("spinner", {"args": args, "kwargs": kwargs}))
        return contextlib.nullcontext()

    def columns(self, spec, **kwargs):
        return [contextlib.nullcontext() for _ in spec]

    def fragment(self, func=None, **kwargs):
        return func if func is not None else (lambda inner: inner)

    def text_input(self, label, **kwargs):
        self.calls.append(("text_input", {"label": label, **kwargs}))
        return self.session_state.get(kwargs.get("key"), "")

    def form_submit_button(self, label, **kwargs):
        self.calls.append(("form_submit_button", {"label": label, **kwargs}))
        return self._submit

    def download_button(self, label, data, file_name, mime, key=None, **kwargs):
        self.calls.append(("download_button", {"label": label, "data": data,
                                               "file_name": file_name, "mime": mime, "key": key}))
        return self._download

    def button(self, label, **kwargs):
        self.calls.append(("button", {"label": label, **kwargs}))
        return False

    def radio(self, label, options, index=0, **kwargs):
        return options[index]

    def markdown(self, body, **kwargs):
        self.calls.append(("markdown", {"body": body}))

    def warning(self, message, **kwargs):
        self.calls.append(("warning", {"message": message}))

    def error(self, message, **kwargs):
        self.calls.append(("error", {"message": message}))


@pytest.fixture
def make_fake_st(monkeypatch):
    def _make(*, submit: bool = False, download: bool = False) -> FakeStreamlit:
        fake = FakeStreamlit(submit=submit, download=download)
        monkeypatch.setattr(ai_summary, "st", fake)
        return fake
    return _make


def _call(fake: FakeStreamlit, name: str) -> dict:
    matches = [payload for called, payload in fake.calls if called == name]
    assert len(matches) == 1, f"expected exactly one {name} call, got {len(matches)}"
    return matches[0]


def _render(player_name: str, summary: str) -> None:
    func = getattr(
        ai_summary.render_follow_up_questions,
        "__wrapped__",
        ai_summary.render_follow_up_questions,
    )
    func(player_name, [{"round": 1}], summary)


def _seed(fake: FakeStreamlit, summary: str, turns: list[dict]) -> None:
    fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY] = {"summary": summary, "turns": list(turns)}


def _markdown_bodies(fake: FakeStreamlit) -> list[str]:
    return [payload["body"] for called, payload in fake.calls if called == "markdown"]


def test_download_button_is_rendered_once_after_the_turns_and_form(make_fake_st):
    """Spec behaviours 1, 3, 4, 11."""
    summary = "AI 总结正文"
    turns = [{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}]
    fake = make_fake_st()
    _seed(fake, summary, turns)

    _render("Neo", summary)

    download = _call(fake, "download_button")
    assert download["label"] == ai_summary.DOWNLOAD_BUTTON_LABEL
    assert download["key"] == ai_summary.DOWNLOAD_BUTTON_KEY
    assert download["mime"] == ai_summary.TRANSCRIPT_MIME_TYPE
    assert download["file_name"].startswith(ai_summary.TRANSCRIPT_FILENAME_PREFIX)
    assert download["file_name"].endswith(ai_summary.TRANSCRIPT_FILE_EXTENSION)
    assert download["data"] == ai_summary.build_transcript_text("Neo", summary, turns)
    assert "问 / Q: Q1" in download["data"]

    names = [name for name, _ in fake.calls]
    assert names.index("form_submit_button") < names.index("download_button")
    assert max(i for i, n in enumerate(names) if n == "markdown") < names.index("download_button")


@pytest.mark.parametrize("summary", ["", "   ", "\n\t "])
def test_no_download_control_for_blank_summary_and_no_session_state_write(make_fake_st, summary):
    """Spec behaviour 2."""
    fake = make_fake_st()

    _render("Neo", summary)

    assert fake.calls == []
    assert fake.session_state == {}


def test_download_control_exists_with_zero_turns_and_contains_the_summary(make_fake_st):
    """Spec behaviour 3."""
    fake = make_fake_st()

    _render("Neo", "只有总结 SUMMARY_BODY_MARKER")

    data = _call(fake, "download_button")["data"]
    assert "SUMMARY_BODY_MARKER" in data
    assert "问 / Q:" not in data


def test_submitted_question_lands_in_the_download_data_in_the_same_render(make_fake_st, monkeypatch):
    """Spec behaviour 14."""
    summary = "AI 总结正文"
    fake = make_fake_st(submit=True)
    fake.session_state[ai_summary.FOLLOW_UP_INPUT_KEY] = "新问题?"
    monkeypatch.setattr(ai_summary, "answer_follow_up_question", lambda *a, **k: "新回答")

    _render("Neo", summary)

    data = _call(fake, "download_button")["data"]
    assert "问 / Q: 新问题?" in data
    assert "答 / A: 新回答" in data
    assert data == ai_summary.build_transcript_text("Neo", summary, [{"question": "新问题?", "answer": "新回答"}])


def test_download_activation_issues_no_ai_request_and_keeps_the_transcript(make_fake_st, monkeypatch):
    """Spec behaviour 15."""
    summary = "AI 总结正文"
    ai_calls: list = []
    monkeypatch.setattr(ai_summary, "summarize_season", lambda *a, **k: ai_calls.append(("summarize", a)))
    monkeypatch.setattr(ai_summary, "answer_follow_up_question", lambda *a, **k: ai_calls.append(("answer", a)))

    bodies = []
    for download in (False, True):
        fake = make_fake_st(download=download)
        _seed(fake, summary, [{"question": "Q1", "answer": "A1"}])
        _render("Neo", summary)
        bodies.append(_markdown_bodies(fake))

    assert ai_calls == []
    assert bodies[0] == bodies[1] == ["**Q1**", "A1"]


def test_empty_submission_warns_and_still_offers_the_download(make_fake_st, monkeypatch):
    """Spec behaviour 1 with a submitted-but-empty question."""
    fake = make_fake_st(submit=True)
    fake.session_state[ai_summary.FOLLOW_UP_INPUT_KEY] = "   "
    monkeypatch.setattr(ai_summary, "answer_follow_up_question", lambda *a, **k: pytest.fail("no AI call expected"))

    _render("Neo", "AI 总结正文")

    assert _call(fake, "warning")["message"] == ai_summary.EMPTY_QUESTION_MESSAGE
    assert "问 / Q:" not in _call(fake, "download_button")["data"]
