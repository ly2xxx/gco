from __future__ import annotations

import pytest

import ai_summary


class Recorder:
    def __init__(self, button_pressed: bool = False, radio_value: str | None = None) -> None:
        self.calls: list[dict] = []
        self.button_pressed = button_pressed
        self.radio_value = radio_value
        self.current_column: int | None = None

    def record(self, method: str, args: tuple, kwargs: dict) -> None:
        self.calls.append(
            {"column": self.current_column, "method": method, "args": args, "kwargs": kwargs}
        )

    def all(self, method: str) -> list[dict]:
        return [call for call in self.calls if call["method"] == method]


class FakeColumn:
    def __init__(self, recorder: Recorder, index: int) -> None:
        self._recorder = recorder
        self._index = index

    def __enter__(self):
        self._recorder.current_column = self._index
        return self

    def __exit__(self, exc_type, exc, tb):
        self._recorder.current_column = None
        return False


class FakeSpinner:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeStreamlit:
    def __init__(self, recorder: Recorder) -> None:
        self._recorder = recorder

    def columns(self, spec, gap=None):
        count = spec if isinstance(spec, int) else len(spec)
        self._recorder.record("columns", (spec,), {})
        return tuple(FakeColumn(self._recorder, index) for index in range(count))

    def radio(self, label, options=None, index=0, key=None, horizontal=False):
        value = self._recorder.radio_value
        if value is None:
            value = options[index]
        self._recorder.record(
            "radio",
            (label,),
            {
                "options": options,
                "index": index,
                "key": key,
                "horizontal": horizontal,
                "value": value,
            },
        )
        return value

    def button(self, label, key=None, **kwargs):
        self._recorder.record("button", (label,), {"key": key})
        return self._recorder.button_pressed

    def spinner(self, text):
        self._recorder.record("spinner", (text,), {})
        return FakeSpinner()

    def markdown(self, text, **kwargs):
        self._recorder.record("markdown", (text,), kwargs)

    def warning(self, text, **kwargs):
        self._recorder.record("warning", (text,), kwargs)

    def error(self, text, **kwargs):
        self._recorder.record("error", (text,), kwargs)


ROUNDS: list[dict] = [{"score": 80, "birdies": 2}, {"score": 75, "birdies": 3}]


@pytest.fixture
def install_fake_st(monkeypatch):
    def _install(button_pressed: bool = False, radio_value: str | None = None) -> Recorder:
        recorder = Recorder(button_pressed=button_pressed, radio_value=radio_value)
        monkeypatch.setattr(ai_summary, "st", FakeStreamlit(recorder))
        return recorder

    return _install


@pytest.fixture
def ollama_stub(monkeypatch):
    calls: list[tuple[tuple, dict]] = []

    def fake_get_ai_config():
        return ("key", "model")

    def fake_call(*args, **kwargs):
        calls.append((args, kwargs))
        if kwargs.get("system_message") == ai_summary.SYSTEM_MESSAGE_EN:
            return "EN-SUMMARY"
        return "ZH-SUMMARY"

    monkeypatch.setattr(ai_summary, "get_ai_config", fake_get_ai_config)
    monkeypatch.setattr(ai_summary, "_call_ollama_chat", fake_call)
    return calls


def test_selector_renders_beside_button_with_chinese_preselected(install_fake_st):
    """Spec behaviour 1."""
    recorder = install_fake_st(button_pressed=False)

    ai_summary.render_season_summary("Jacky", ROUNDS)

    radios = recorder.all("radio")
    assert len(radios) == 1
    radio = radios[0]
    assert radio["args"] == (ai_summary.LANGUAGE_SELECTOR_LABEL,)
    assert radio["kwargs"]["options"] == ("中文", "English")
    assert radio["kwargs"]["index"] == 0
    assert radio["kwargs"]["key"] == ai_summary.LANGUAGE_SELECTOR_KEY
    assert radio["kwargs"]["horizontal"] is True
    assert radio["kwargs"]["value"] == "中文"
    assert radio["column"] == 0

    buttons = recorder.all("button")
    assert len(buttons) == 1
    assert buttons[0]["args"] == (ai_summary.AI_SUMMARY_BUTTON_LABEL,)
    assert buttons[0]["kwargs"]["key"] == "ai_season_summary_button"
    assert buttons[0]["column"] == 1

    assert recorder.all("markdown") == []


def test_empty_player_name_renders_nothing(install_fake_st):
    """Spec behaviour 2."""
    recorder = install_fake_st(button_pressed=True)

    ai_summary.render_season_summary("", ROUNDS)

    assert recorder.calls == []


def test_english_summary_rendered_with_markdown(install_fake_st, ollama_stub):
    """Spec behaviour 4."""
    recorder = install_fake_st(button_pressed=True, radio_value="English")

    ai_summary.render_season_summary("Jacky", ROUNDS)

    assert recorder.all("markdown")[0]["args"] == ("EN-SUMMARY",)
    assert recorder.all("error") == []
    assert ollama_stub == [
        (
            ("key", "model", ai_summary.build_summary_prompt("Jacky", ROUNDS, language="English")),
            {"system_message": ai_summary.SYSTEM_MESSAGE_EN},
        )
    ]


def test_switching_language_without_press_clears_summary_and_skips_request(install_fake_st, ollama_stub):
    """Spec behaviours 7, 12."""
    first = install_fake_st(button_pressed=True, radio_value="中文")
    ai_summary.render_season_summary("Jacky", ROUNDS)
    assert first.all("markdown")[0]["args"] == ("ZH-SUMMARY",)
    assert len(ollama_stub) == 1

    second = install_fake_st(button_pressed=False, radio_value="English")
    ai_summary.render_season_summary("Jacky", ROUNDS)

    assert second.all("markdown") == []
    assert len(ollama_stub) == 1


def test_pressing_after_switching_renders_new_language_summary(install_fake_st, ollama_stub):
    """Spec behaviour 8."""
    english = install_fake_st(button_pressed=True, radio_value="English")
    ai_summary.render_season_summary("Jacky", ROUNDS)
    chinese = install_fake_st(button_pressed=True, radio_value="中文")
    ai_summary.render_season_summary("Jacky", ROUNDS)

    assert english.all("markdown")[0]["args"] == ("EN-SUMMARY",)
    assert ollama_stub[0][1] == {"system_message": ai_summary.SYSTEM_MESSAGE_EN}
    assert chinese.all("markdown")[0]["args"] == ("ZH-SUMMARY",)
    assert ollama_stub[1] == (("key", "model", ai_summary.build_summary_prompt("Jacky", ROUNDS)), {})


def test_no_rounds_shows_warning_and_skips_request(install_fake_st, ollama_stub):
    """Spec behaviour 9."""
    recorder = install_fake_st(button_pressed=True, radio_value="English")

    ai_summary.render_season_summary("Jacky", [])

    assert recorder.all("warning")[0]["args"] == (ai_summary.NO_ROUNDS_MESSAGE,)
    assert recorder.all("markdown") == []
    assert ollama_stub == []


def test_missing_config_shows_error_without_request(install_fake_st, monkeypatch):
    """Spec behaviour 10."""
    calls: list = []
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("", ""))
    monkeypatch.setattr(ai_summary, "_call_ollama_chat", lambda *args, **kwargs: calls.append((args, kwargs)))
    recorder = install_fake_st(button_pressed=True, radio_value="English")

    ai_summary.render_season_summary("Jacky", ROUNDS)

    assert recorder.all("error")[0]["args"] == (ai_summary.MISSING_CONFIG_MESSAGE,)
    assert recorder.all("markdown") == []
    assert calls == []


@pytest.mark.parametrize(
    "message",
    [ai_summary.CALL_FAILED_MESSAGE.format(detail="HTTP 500"), ai_summary.EMPTY_RESPONSE_MESSAGE],
    ids=["call-failed", "empty-response"],
)
def test_call_failure_shows_error_and_no_markdown(install_fake_st, monkeypatch, message):
    """Spec behaviour 11."""
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("key", "model"))

    def failing(*args, **kwargs):
        raise ai_summary.AISummaryError(message)

    monkeypatch.setattr(ai_summary, "_call_ollama_chat", failing)
    recorder = install_fake_st(button_pressed=True, radio_value="English")

    ai_summary.render_season_summary("Jacky", ROUNDS)

    assert recorder.all("error")[0]["args"] == (message,)
    assert recorder.all("markdown") == []
