"""Phase 3: writing found fields into widget session state, and the upload fingerprint."""
import hashlib

import pytest

from league_scorecard import LEAGUE_SCORECARD_FIELD_KEYS, apply_scorecard_updates, scorecard_upload_fingerprint


def test_apply_writes_only_found_fields_with_widget_keys():
    state = {"league_sc_net": 99, "league_sc_venue": "Old"}
    widget_keys = {"date": "league_sc_date", "venue": "league_sc_venue", "net": "league_sc_net"}
    applied = apply_scorecard_updates({"venue": "New", "gross": 77}, widget_keys, state)
    assert applied == ["venue"]
    assert state["league_sc_venue"] == "New"
    assert state["league_sc_net"] == 99
    assert "league_sc_gross" not in state
    assert "league_sc_date" not in state


def test_apply_ignores_unknown_fields_and_missing_widget_keys():
    state = {}
    assert apply_scorecard_updates({"eagles": 2, "player": "Neo"}, {}, state) == []
    assert state == {}


def test_apply_returns_fields_in_key_order_and_is_idempotent():
    updates = {field: index for index, field in reversed(list(enumerate(LEAGUE_SCORECARD_FIELD_KEYS)))}
    widget_keys = {field: f"league_sc_{field}" for field in LEAGUE_SCORECARD_FIELD_KEYS}
    state = {}
    first = apply_scorecard_updates(updates, widget_keys, state)
    assert first == list(LEAGUE_SCORECARD_FIELD_KEYS)
    state_copy = dict(state)
    second = apply_scorecard_updates(updates, widget_keys, state)
    assert second == first
    assert state == dict(state_copy)


def test_fingerprint_is_stable_and_payload_sensitive():
    first = scorecard_upload_fingerprint("a.jpg", b"x")
    again = scorecard_upload_fingerprint("a.jpg", b"x")
    assert first == again
    assert len(first) == 64
    assert first == first.lower()
    assert all(ch in "0123456789abcdef" for ch in first)
    assert first == hashlib.sha256(b"a.jpg\x00" + b"x").hexdigest()
    assert scorecard_upload_fingerprint("a.jpg", b"y") != first
    assert scorecard_upload_fingerprint("b.jpg", b"x") != first


@pytest.mark.parametrize("payload", (b"", None))
def test_fingerprint_accepts_empty_payload(payload):
    assert scorecard_upload_fingerprint("a.jpg", payload) == hashlib.sha256(b"a.jpg\x00").hexdigest()
