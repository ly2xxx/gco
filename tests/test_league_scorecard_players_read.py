"""Feature 012, phase 2: read every player from one scorecard image. No real network."""
import base64
import json

import pytest

import league_scorecard
from league_scorecard import read_league_scorecard_players

JPEG = b"\xff\xd8\xff" + b"\x00" * 32


@pytest.fixture
def ollama_stub(monkeypatch):
    calls = {"payloads": [], "timeouts": [], "body": ""}

    def _fake(payload, timeout_seconds):
        calls["payloads"].append(payload)
        calls["timeouts"].append(timeout_seconds)
        body = calls["body"]
        if isinstance(body, BaseException):
            raise body
        return str(body)

    monkeypatch.setattr(league_scorecard, "_post_ollama_generate", _fake)
    return calls


def _players_body(players):
    return json.dumps({"response": json.dumps({"players": players})})


def test_reads_every_player_from_one_card(ollama_stub):
    ollama_stub["body"] = _players_body([
        {"label": "Neo", "fields": {"net": 2, "birdies": 3}},
        {"label": "刘北南", "fields": {"gross": 80}},
    ])
    result = read_league_scorecard_players(JPEG, "image/jpeg")
    assert result.unavailable_reason is None
    assert [p.label for p in result.players] == ["Neo", "刘北南"]
    assert result.players[0].found_fields == {"net": 2, "birdies": 3}
    assert result.players[1].found_fields == {"gross": 80}


def test_request_uses_the_players_prompt(ollama_stub):
    ollama_stub["body"] = _players_body([{"label": "Neo", "fields": {"net": 2}}])
    read_league_scorecard_players(JPEG, "image/jpeg")
    payload = ollama_stub["payloads"][0]
    assert payload["prompt"] == league_scorecard.SCORECARD_PLAYERS_PROMPT
    assert payload["format"] == "json"
    assert payload["stream"] is False
    assert payload["images"] == [base64.b64encode(JPEG).decode("ascii")]
    assert ollama_stub["timeouts"][0] == league_scorecard.DEFAULT_TIMEOUT_SECONDS

    read_league_scorecard_players(JPEG, "image/jpeg", timeout_seconds=5.0)
    assert ollama_stub["timeouts"][1] == 5.0


def test_empty_image_is_reported(ollama_stub):
    result = read_league_scorecard_players(b"", "image/jpeg")
    assert result.players == []
    assert result.unavailable_reason == "empty image"
    assert ollama_stub["payloads"] == []


def test_unsupported_file_type_is_reported(ollama_stub):
    result = read_league_scorecard_players(b"not an image", "text/plain")
    assert result.players == []
    assert result.unavailable_reason == "unsupported file type"
    assert ollama_stub["payloads"] == []


def test_transport_error_is_reported_not_raised(ollama_stub):
    ollama_stub["body"] = league_scorecard.ScorecardRequestError("timeout")
    result = read_league_scorecard_players(JPEG, "image/jpeg")
    assert result.players == []
    assert result.unavailable_reason == "timeout"


def test_unexpected_error_is_reported_not_raised(ollama_stub):
    ollama_stub["body"] = RuntimeError("boom")
    result = read_league_scorecard_players(JPEG, "image/jpeg")
    assert result.players == []
    assert result.unavailable_reason == "service error"


def test_unparseable_body_is_reported(ollama_stub):
    ollama_stub["body"] = "not json"
    result = read_league_scorecard_players(JPEG, "image/jpeg")
    assert result.players == []
    assert result.unavailable_reason == "unparseable response"


def test_card_with_no_readable_players_is_reported(ollama_stub):
    ollama_stub["body"] = _players_body([])
    result = read_league_scorecard_players(JPEG, "image/jpeg")
    assert result.players == []
    assert result.unavailable_reason == "no readable players"
