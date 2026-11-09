"""The scorecard read logs its Ollama request, the reply and the outcome, never the API key."""
import io
import json
import logging
import socket
import urllib.error

import pytest
import streamlit

import league_scorecard as ls

JPEG = b"\xff\xd8\xff" + b"\x00" * 64
API_KEY = "test-secret-key-7f3a"


class _Response:
    def __init__(self, body, status=200):
        self._body = body.encode("utf-8")
        self.status = status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def scorecard_log(monkeypatch):
    """Records the gco.scorecard log lines; the API key comes from the environment."""
    for name in ls.MODEL_ENV_NAMES + ls.API_KEY_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(streamlit, "secrets", {})
    monkeypatch.setenv("OLLAMA_API_KEY", API_KEY)
    records = []
    handler = logging.Handler()
    handler.emit = records.append
    logger = logging.getLogger(ls.LOGGER_NAME)
    logger.addHandler(handler)
    yield records
    logger.removeHandler(handler)


def _ollama(monkeypatch, *, body=None, raises=None):
    def fake_urlopen(request, timeout):
        if raises is not None:
            raise raises
        return _Response(body)

    monkeypatch.setattr(ls.urllib.request, "urlopen", fake_urlopen)


def _text(records):
    return "\n".join(r.getMessage() for r in records)


def test_successful_read_logs_request_reply_stats_and_players(monkeypatch, scorecard_log):
    reply = {"players": [
        {"label": "王", "fields": {"date": "2026-08-09", "gross": 93, "net": -1}},
        {"label": "李杨", "fields": {"gross": 100, "net": 13}},
    ]}
    _ollama(monkeypatch, body=json.dumps({
        "model": "glm-5.3-flash:cloud", "done": True, "done_reason": "stop",
        "prompt_eval_count": 812, "eval_count": 145, "total_duration": 41_500_000_000,
        "thinking": "x" * 300, "response": json.dumps(reply, ensure_ascii=False),
    }))

    result = ls.read_league_scorecard_players(JPEG, "image/jpeg")

    assert [p.label for p in result.players] == ["王", "李杨"]
    text = _text(scorecard_log)
    assert "ollama request: POST https://ollama.com/api/generate model=glm-5.3-flash:cloud prompt=players" in text
    assert "api_key=set" in text
    assert "ollama response: status=200" in text
    assert "done_reason=stop" in text and "eval_count=145" in text and "total_duration=41.5s" in text
    assert "thinking_chars=300" in text
    assert '"label": "李杨"' in text, "the model's reply text is logged"
    assert "players read: 2 player(s): '王' -> {'date': '2026-08-09', 'net': -1, 'gross': 93}" in text
    assert API_KEY not in text


def test_http_error_logs_status_and_ollamas_message(monkeypatch, scorecard_log):
    error = urllib.error.HTTPError(
        ls.OLLAMA_GENERATE_URL, 400, "Bad Request", {},
        io.BytesIO(b'{"error":"model does not support image input"}'),
    )
    _ollama(monkeypatch, raises=error)

    result = ls.read_league_scorecard_players(JPEG, "image/jpeg")

    assert result.unavailable_reason == "http 400"
    text = _text(scorecard_log)
    assert "ollama error: http 400" in text
    assert "model does not support image input" in text
    assert "players read: unavailable (http 400)" in text
    assert API_KEY not in text


def test_timeout_logs_the_elapsed_time_and_limit(monkeypatch, scorecard_log):
    _ollama(monkeypatch, raises=socket.timeout("timed out"))

    result = ls.read_league_scorecard_players(JPEG, "image/jpeg", timeout_seconds=7.0)

    assert result.unavailable_reason == "timeout"
    text = _text(scorecard_log)
    assert "ollama error: timeout after" in text and "(limit 7.0s)" in text
    assert "players read: unavailable (timeout)" in text


def test_empty_reply_is_explained(monkeypatch, scorecard_log):
    _ollama(monkeypatch, body=json.dumps({"done": True, "done_reason": "length", "response": ""}))

    result = ls.read_league_scorecard_players(JPEG, "image/jpeg")

    assert result.unavailable_reason == "unparseable response"
    assert "the model's reply is empty (done_reason=length)" in _text(scorecard_log)


def test_reply_without_labelled_players_logs_its_shape(monkeypatch, scorecard_log):
    reply = {"players": [{"printed_as": "A", "scores": {"gross": 93}}]}
    _ollama(monkeypatch, body=json.dumps({"done": True, "response": json.dumps(reply)}))

    result = ls.read_league_scorecard_players(JPEG, "image/jpeg")

    assert result.unavailable_reason == "no readable players"
    text = _text(scorecard_log)
    assert "no labelled players in the reply" in text
    assert "first record keys=['printed_as', 'scores']" in text


def test_long_replies_are_cut_in_the_log():
    assert ls._excerpt("x" * 50, limit=10) == "xxxxxxxxxx… (+40 chars)"
    assert ls._excerpt("a\n  b") == "a b"


def _own_handlers(logger):
    """The module's stderr handler(s), told apart from pytest's capture handlers by format."""
    return [
        h for h in logger.handlers
        if type(h) is logging.StreamHandler and h.formatter is not None and "[scorecard]" in h.formatter._fmt
    ]


def test_logger_writes_info_to_stderr_once():
    logger = logging.getLogger(ls.LOGGER_NAME)
    assert logger.level == logging.INFO
    assert logger.propagate is False
    assert len(_own_handlers(logger)) == 1
    ls._scorecard_logger()  # a module reload calls this again
    assert len(_own_handlers(logger)) == 1
