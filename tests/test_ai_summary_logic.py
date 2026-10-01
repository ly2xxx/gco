import json
import re
import sys
import urllib.error
from pathlib import Path

import pandas as pd
import pytest

# `uv run pytest tests/...` puts only tests/ on sys.path; ai_summary.py lives at the repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import ai_summary  # noqa: E402

KEY = "key-1"
MODEL = "model-1"
ROUNDS = [
    {"Game": "Game 1", "Net_Score": -8, "Birdies": 3, "Pars": 8},
    {"Game": "Game 2", "Net_Score": 3, "Birdies": 2, "Pars": 10},
]


class _StubSecrets:
    def __init__(self, data=None, raises=False):
        self._data = data or {}
        self._raises = raises

    def get(self, key, default=None):
        if self._raises:
            raise RuntimeError("no secrets file")
        return self._data.get(key, default)


class _StubStreamlit:
    def __init__(self, secrets):
        self.secrets = secrets


class _FakeResponse:
    def __init__(self, payload: bytes, status: int = 200):
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeUrlOpen:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        if self.error is not None:
            raise self.error
        return self.response


def _use_secrets(monkeypatch, data=None, raises=False):
    secrets = _StubSecrets(data, raises=raises)
    monkeypatch.setattr(ai_summary, "st", _StubStreamlit(secrets))


def _configured(monkeypatch):
    _use_secrets(monkeypatch, {"OLLAMA_API_KEY": KEY, "OLLAMA_MODEL": MODEL})


def _counting_transport(monkeypatch, result="总结文本"):
    calls = []

    def fake(api_key, model, prompt):
        calls.append((api_key, model, prompt))
        return result

    monkeypatch.setattr(ai_summary, "_call_ollama_chat", fake)
    return calls


def test_get_ai_config_reads_secrets(monkeypatch):
    _use_secrets(monkeypatch, {"OLLAMA_API_KEY": KEY, "OLLAMA_MODEL": MODEL})
    assert ai_summary.get_ai_config() == (KEY, MODEL)


def test_get_ai_config_returns_empty_pair_when_secrets_unavailable(monkeypatch):
    _use_secrets(monkeypatch, raises=True)
    assert ai_summary.get_ai_config() == ("", "")


def test_get_ai_config_defaults_missing_keys_to_empty_strings(monkeypatch):
    _use_secrets(monkeypatch, {})
    assert ai_summary.get_ai_config() == ("", "")


def test_is_ai_configured_requires_both_values(monkeypatch):
    _use_secrets(monkeypatch, {"OLLAMA_MODEL": MODEL})
    assert ai_summary.is_ai_configured() is False
    _use_secrets(monkeypatch, {"OLLAMA_API_KEY": KEY, "OLLAMA_MODEL": MODEL})
    assert ai_summary.is_ai_configured() is True


def test_build_summary_prompt_contains_only_this_players_name_and_fields():
    prompt = ai_summary.build_summary_prompt("刘北南", ROUNDS)
    assert "刘北南" in prompt
    for record in ROUNDS:
        assert all(str(value) in prompt for value in record.values())
        assert all(str(key) in prompt for key in record)
    assert "Jacky" not in prompt
    assert "赛季总结" in prompt
    assert "简体中文" in prompt


def test_build_summary_prompt_accepts_dataframe_input():
    prompt = ai_summary.build_summary_prompt("刘北南", pd.DataFrame(ROUNDS))
    assert "Game 1" in prompt
    assert "-8" in prompt


def test_summarize_season_passes_secrets_values_and_prompt_to_transport(monkeypatch):
    _use_secrets(monkeypatch, {"OLLAMA_API_KEY": "key-2", "OLLAMA_MODEL": "model-2"})
    calls: list[tuple] = []
    monkeypatch.setattr(
        ai_summary, "_call_ollama_chat", lambda api_key, model, prompt: calls.append((api_key, model, prompt)) or "总结文本"
    )

    assert ai_summary.summarize_season("刘北南", ROUNDS) == "总结文本"
    assert calls[0][0] == "key-2"
    assert calls[0][1] == "model-2"
    assert calls[0][2] == ai_summary.build_summary_prompt("刘北南", ROUNDS)


def test_summarize_season_raises_when_config_missing(monkeypatch):
    _use_secrets(monkeypatch, {})
    calls = _counting_transport(monkeypatch)

    with pytest.raises(ai_summary.AISummaryError) as excinfo:
        ai_summary.summarize_season("刘北南", ROUNDS)
    assert ai_summary.MISSING_CONFIG_MESSAGE in str(excinfo.value)
    assert calls == []


def test_summarize_season_raises_and_skips_transport_when_no_rounds(monkeypatch):
    _configured(monkeypatch)
    calls = _counting_transport(monkeypatch)

    with pytest.raises(ai_summary.AISummaryError) as excinfo:
        ai_summary.summarize_season("刘北南", [])
    assert ai_summary.NO_ROUNDS_MESSAGE in str(excinfo.value)
    assert calls == []


def test_summarize_season_raises_on_blank_transport_response(monkeypatch):
    _configured(monkeypatch)
    _counting_transport(monkeypatch, result="   ")

    with pytest.raises(ai_summary.AISummaryError) as excinfo:
        ai_summary.summarize_season("刘北南", ROUNDS)
    assert ai_summary.EMPTY_RESPONSE_MESSAGE in str(excinfo.value)


def test_summarize_season_propagates_transport_error(monkeypatch):
    _configured(monkeypatch)

    def failing(api_key, model, prompt):
        raise ai_summary.AISummaryError(ai_summary.CALL_FAILED_MESSAGE.format(detail="boom"))

    monkeypatch.setattr(ai_summary, "_call_ollama_chat", failing)

    with pytest.raises(ai_summary.AISummaryError) as excinfo:
        ai_summary.summarize_season("刘北南", ROUNDS)
    assert "boom" in str(excinfo.value)


def test_call_ollama_chat_posts_expected_payload_and_returns_content(monkeypatch):
    fake = _FakeUrlOpen(
        response=_FakeResponse(json.dumps({"message": {"content": "你好"}}).encode("utf-8"), status=200)
    )
    monkeypatch.setattr(ai_summary.urllib.request, "urlopen", fake)

    assert ai_summary._call_ollama_chat(KEY, MODEL, "提示") == "你好"

    request, timeout = fake.requests[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert payload["model"] == MODEL
    assert payload["stream"] is False
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][-1]["content"] == "提示"
    assert request.full_url == ai_summary.OLLAMA_CHAT_URL
    assert request.get_method() == "POST"
    # urllib.request.Request stores header names via str.capitalize().
    assert request.get_header("Authorization") == f"Bearer {KEY}"
    assert request.get_header("Content-type") == "application/json"
    assert timeout == ai_summary.REQUEST_TIMEOUT_SECONDS


def test_call_ollama_chat_raises_on_http_error(monkeypatch):
    fake = _FakeUrlOpen(error=urllib.error.HTTPError(ai_summary.OLLAMA_CHAT_URL, 401, "Unauthorized", {}, None))
    monkeypatch.setattr(ai_summary.urllib.request, "urlopen", fake)

    with pytest.raises(ai_summary.AISummaryError):
        ai_summary._call_ollama_chat(KEY, MODEL, "提示")


def test_call_ollama_chat_raises_on_non_success_status(monkeypatch):
    monkeypatch.setattr(ai_summary.urllib.request, "urlopen", _FakeUrlOpen(response=_FakeResponse(b"{}", status=500)))

    with pytest.raises(ai_summary.AISummaryError):
        ai_summary._call_ollama_chat(KEY, MODEL, "提示")


def test_call_ollama_chat_raises_on_malformed_json(monkeypatch):
    monkeypatch.setattr(
        ai_summary.urllib.request, "urlopen", _FakeUrlOpen(response=_FakeResponse(b"not json", status=200))
    )

    with pytest.raises(ai_summary.AISummaryError):
        ai_summary._call_ollama_chat(KEY, MODEL, "提示")


def test_call_ollama_chat_raises_on_empty_content(monkeypatch):
    response = _FakeResponse(json.dumps({"message": {"content": "  "}}).encode("utf-8"), status=200)
    monkeypatch.setattr(ai_summary.urllib.request, "urlopen", _FakeUrlOpen(response=response))

    with pytest.raises(ai_summary.AISummaryError) as excinfo:
        ai_summary._call_ollama_chat(KEY, MODEL, "提示")
    assert ai_summary.EMPTY_RESPONSE_MESSAGE in str(excinfo.value)


def test_module_has_no_hardcoded_credentials():
    src = Path(ai_summary.__file__).read_text(encoding="utf-8")
    assert "sk-" not in src
    assert re.search(r"(?i)\b(api_key|token|secret)\b\s*=\s*[\"'][^\"']{16,}[\"']", src) is None
    assert "st.secrets.get(OLLAMA_API_KEY_SECRET" in src
    assert "st.secrets.get(OLLAMA_MODEL_SECRET" in src
