"""Feature 014, phase 1: the players read also returns pars and each player's hole scores."""
import json

import pytest

import league_scorecard
from league_scorecard import ScorecardRequestError, read_league_scorecard_players

JPEG = b"\xff\xd8\xff" + b"\x00" * 32
PARS = {str(h): (3 if h in (6, 12, 17) else 5 if h in (7, 15) else 4) for h in range(1, 19)}


def _scores(base):
    return {str(h): base + (h % 3) for h in range(1, 19)}


def _ints(mapping):
    return {int(k): v for k, v in mapping.items()}


@pytest.fixture
def reply(monkeypatch):
    """Set box["reply"] (a dict), box["body"] (raw text) or box["raise"]; counts requests."""
    box = {"calls": 0}

    def fake(payload, timeout_seconds):
        box["calls"] += 1
        if "raise" in box:
            raise box["raise"]
        return box["body"] if "body" in box else json.dumps({"response": json.dumps(box["reply"], ensure_ascii=False)})

    monkeypatch.setattr(league_scorecard, "_post_ollama_generate", fake)
    return box


def test_read_returns_all_pars_and_each_players_hole_scores(reply):
    reply["reply"] = {"pars": PARS, "players": [
        {"label": "王", "fields": {"gross": 93}, "hole_scores": _scores(4)},
        {"label": "张纬", "fields": {"gross": 100}, "hole_scores": _scores(5)},
        {"label": "Neo", "fields": {}, "hole_scores": _scores(6)},
    ]}
    result = read_league_scorecard_players(JPEG, "image/jpeg")

    assert result.unavailable_reason is None
    assert result.pars == _ints(PARS) and list(result.pars) == list(range(1, 19))
    assert [p.index for p in result.players] == [0, 1, 2]
    assert [p.label for p in result.players] == ["王", "张纬", "Neo"]
    assert [p.hole_scores for p in result.players] == [_ints(_scores(4)), _ints(_scores(5)), _ints(_scores(6))]
    assert result.players[0].found_fields == {"gross": 93}
    assert reply["calls"] == 1, "still one request per upload"


def test_unread_holes_are_absent_not_zero(reply):
    pars = {k: v for k, v in PARS.items() if k != "12"}
    scores = {k: v for k, v in _scores(4).items() if k != "7"}
    reply["reply"] = {"pars": pars, "players": [{"label": "A", "fields": {}, "hole_scores": scores}]}
    result = read_league_scorecard_players(JPEG, "image/jpeg")
    entry = result.players[0]

    assert 7 not in entry.hole_scores and 12 not in result.pars
    assert len(entry.hole_scores) == 17 and len(result.pars) == 17
    assert 0 not in entry.hole_scores.values() and 0 not in result.pars.values()
    assert 0 not in entry.hole_scores and 0 not in result.pars


def test_out_of_range_and_bad_keys_are_dropped(reply):
    bad = {"1": 4, "2": 0, "3": 21, "4": "x", "5": None, "6": 5, "0": 4, "19": 4, "hole 3": 4}
    reply["reply"] = {"pars": bad, "players": [{"label": "A", "fields": {}, "hole_scores": bad}]}
    result = read_league_scorecard_players(JPEG, "image/jpeg")

    assert result.pars == {1: 4, 6: 5}
    assert result.players[0].hole_scores == {1: 4, 6: 5}


@pytest.mark.parametrize("bad", ["not-a-map", [1, 2, 3], 7])
def test_malformed_pars_and_hole_scores_are_empty_mappings(reply, bad):
    reply["reply"] = {"pars": bad, "players": [{"label": "A", "fields": {}, "hole_scores": bad}]}
    result = read_league_scorecard_players(JPEG, "image/jpeg")
    assert result.pars == {}
    assert result.players[0].hole_scores == {}


def test_reply_without_hole_data_still_reads_the_totals(reply):
    reply["reply"] = {"players": [{"label": "A", "fields": {"gross": 90}}]}
    result = read_league_scorecard_players(JPEG, "image/jpeg")
    assert result.pars == {} and result.players[0].hole_scores == {}
    assert result.players[0].found_fields == {"gross": 90}


def test_empty_image_and_unsupported_type_keep_pars_empty(reply):
    for image, mime, reason in ((b"", None, "empty image"), (b"plain text", "text/plain", "unsupported file type")):
        result = read_league_scorecard_players(image, mime)
        assert (result.players, result.pars, result.unavailable_reason) == ([], {}, reason)
    assert reply["calls"] == 0


def test_transport_and_unparseable_failures_keep_pars_empty(reply):
    reply["raise"] = ScorecardRequestError("network error")
    result = read_league_scorecard_players(JPEG, "image/jpeg")
    assert (result.players, result.pars, result.unavailable_reason) == ([], {}, "network error")
    del reply["raise"]
    reply["body"] = "not json"
    result = read_league_scorecard_players(JPEG, "image/jpeg")
    assert (result.players, result.pars, result.unavailable_reason) == ([], {}, "unparseable response")


def test_reply_without_players_returns_no_readable_players_and_empty_pars(reply):
    for body in ({"pars": {"1": 4}}, {"players": []}):
        reply["reply"] = body
        result = read_league_scorecard_players(JPEG, "image/jpeg")
        assert (result.players, result.pars, result.unavailable_reason) == ([], {}, "no readable players")


def test_prompt_asks_for_pars_and_hole_scores_and_is_still_the_players_prompt():
    prompt = league_scorecard.SCORECARD_PLAYERS_PROMPT
    assert '"pars"' in prompt and '"hole_scores"' in prompt
    assert league_scorecard._prompt_kind({"prompt": prompt}) == "players"
