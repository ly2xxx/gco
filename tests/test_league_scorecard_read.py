"""Phase 2: one Ollama Cloud scorecard read with a 120 s cap. No real network."""
import base64
import json
from unittest.mock import Mock

import pytest
import streamlit

import league_scorecard as ls

JPEG_BYTES = b"\xff\xd8\xff\xe0card"


@pytest.fixture(autouse=True)
def _no_configured_model_or_key(monkeypatch):
    """Isolate model/key resolution from the developer's env and .streamlit/secrets.toml."""
    for name in ls.MODEL_ENV_NAMES + ls.API_KEY_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(streamlit, "secrets", {})


def _stub(monkeypatch, *, returns=None, raises=None):
    stub = Mock(return_value=returns, side_effect=raises)
    monkeypatch.setattr(ls, "_post_ollama_generate", stub)
    return stub


def test_read_success_returns_found_fields(monkeypatch):
    body = json.dumps({
        "response": "```json\n{\"date\": \"2026-06-23\", \"net\": \"5\", \"gross\": 77, \"player\": \"Neo\"}\n```"
    })
    stub = _stub(monkeypatch, returns=body)
    result = ls.read_league_scorecard(JPEG_BYTES, "image/jpeg")
    assert stub.call_count == 1
    assert result.unavailable_reason is None
    assert result.found_fields == {"date": "2026-06-23", "net": 5, "gross": 77}


def test_request_payload_and_timeout(monkeypatch):
    stub = _stub(monkeypatch, returns=json.dumps({"response": "{\"net\": 1}"}))
    ls.read_league_scorecard(JPEG_BYTES, "image/jpeg")
    payload, timeout_seconds = stub.call_args.args
    assert payload["model"] == "glm-5.3-flash:cloud"
    assert payload["stream"] is False
    assert payload["format"] == "json"
    assert payload["images"] == [base64.b64encode(JPEG_BYTES).decode("ascii")]
    assert payload["prompt"] == ls.SCORECARD_PROMPT
    assert timeout_seconds == 120.0

    ls.read_league_scorecard(JPEG_BYTES, "image/jpeg", timeout_seconds=5.0)
    _, timeout_seconds = stub.call_args.args
    assert timeout_seconds == 5.0


def test_model_env_override(monkeypatch):
    monkeypatch.setenv("OLLAMA_SCORECARD_MODEL", "custom:cloud")
    stub = _stub(monkeypatch, returns=json.dumps({"response": "{\"net\": 1}"}))
    ls.read_league_scorecard(JPEG_BYTES, "image/jpeg")
    payload, _ = stub.call_args.args
    assert payload["model"] == "custom:cloud"


def test_endpoint_constant():
    assert ls.OLLAMA_GENERATE_URL == "https://ollama.com/api/generate"


def test_unsupported_mime_sends_no_request(monkeypatch):
    stub = _stub(monkeypatch, raises=AssertionError("must not be called"))
    result = ls.read_league_scorecard(b"%PDF-1.4", "application/pdf")
    assert result.unavailable_reason == "unsupported file type"
    assert result.found_fields == {}
    stub.assert_not_called()


def test_empty_image_sends_no_request(monkeypatch):
    stub = _stub(monkeypatch, raises=AssertionError("must not be called"))
    result = ls.read_league_scorecard(b"", "image/jpeg")
    assert result.unavailable_reason == "empty image"
    stub.assert_not_called()


def test_mime_sniffed_from_magic_bytes(monkeypatch):
    stub = _stub(monkeypatch, returns=json.dumps({"response": "{\"net\": 3}"}))
    result = ls.read_league_scorecard(b"\x89PNG\r\n\x1a\n" + b"x" * 8, None)
    assert stub.call_count == 1
    assert result.found_fields == {"net": 3}


def test_http_error_becomes_unavailable(monkeypatch):
    stub = _stub(monkeypatch, raises=ls.ScorecardRequestError("http 500"))
    result = ls.read_league_scorecard(JPEG_BYTES, "image/jpeg")
    assert result.unavailable_reason == "http 500"
    assert result.found_fields == {}
    assert stub.call_count == 1


def test_timeout_becomes_unavailable(monkeypatch):
    stub = _stub(monkeypatch, raises=ls.ScorecardRequestError("timeout"))
    result = ls.read_league_scorecard(JPEG_BYTES, "image/jpeg")
    assert result.unavailable_reason == "timeout"
    assert stub.call_count == 1


def test_unparseable_and_fieldless_responses(monkeypatch):
    _stub(monkeypatch, returns="not json")
    assert ls.read_league_scorecard(JPEG_BYTES, "image/jpeg").unavailable_reason == "unparseable response"

    _stub(monkeypatch, returns=json.dumps({"response": "{}"}))
    assert ls.read_league_scorecard(JPEG_BYTES, "image/jpeg").unavailable_reason == "no readable fields"

    _stub(monkeypatch, returns=json.dumps({"error": "boom"}))
    result = ls.read_league_scorecard(JPEG_BYTES, "image/jpeg")
    assert result is not None
    assert result.found_fields == {}
    assert result.unavailable_reason is not None


def test_unexpected_exception_is_swallowed(monkeypatch):
    _stub(monkeypatch, raises=RuntimeError("kaboom"))
    result = ls.read_league_scorecard(JPEG_BYTES, "image/jpeg")
    assert result.unavailable_reason == "service error"
    assert result.found_fields == {}
