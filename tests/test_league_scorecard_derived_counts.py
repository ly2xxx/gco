"""Feature 015, phase 2: a complete hole read fills the picked player's five count fields."""
import pytest

import league_scorecard
from league_scorecard import (
    COUNT_FIELD_KEYS,
    LEAGUE_SCORECARD_FIELD_KEYS,
    LeagueScorecardPlayersResult,
    ScorecardPlayerEntry,
    apply_selected_player_scorecard_updates,
    selected_player_scorecard_updates,
)

CARD_FIELDS = {"date": "2026-01-01", "venue": "Course", "net": -1, "gross": 72, "stableford": 36}
MODEL_COUNTS = {"eagles": 9, "birdies": 9, "pars": 0, "bogeys": 0, "double_bogeys_or_worse": 0}
EXPECTED_COUNTS = {"eagles": 2, "birdies": 3, "pars": 4, "bogeys": 3, "double_bogeys_or_worse": 6}


def _complete_pars():
    return {hole: 4 for hole in range(1, 19)}


def _complete_hole_scores():
    """Two eagles, three birdies, four pars, three bogeys and six double-bogeys-or-worse on par 4s."""
    scores = [2, 1, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 6, 7, 8, 6, 6, 9]
    return dict(zip(range(1, 19), scores))


def _result(found_fields, *, pars=None, hole_scores=None):
    entry = ScorecardPlayerEntry(
        index=0,
        label="Player A",
        found_fields=dict(found_fields),
        hole_scores=_complete_hole_scores() if hole_scores is None else hole_scores,
    )
    return LeagueScorecardPlayersResult(players=[entry], pars=_complete_pars() if pars is None else pars)


def test_helper_hole_scores_match_expected_counts():
    diffs = [score - 4 for score in _complete_hole_scores().values()]
    assert sum(d <= -2 for d in diffs) == 2
    assert diffs.count(-1) == 3 and diffs.count(0) == 4 and diffs.count(1) == 3
    assert sum(d >= 2 for d in diffs) == 6


def test_selected_player_scorecard_updates_adds_hole_derived_counts_when_found_fields_have_none():
    result = _result(CARD_FIELDS)

    updates = selected_player_scorecard_updates(result, 0)

    assert updates == {**CARD_FIELDS, **EXPECTED_COUNTS}
    for field, value in CARD_FIELDS.items():
        assert updates[field] == value


def test_selected_player_scorecard_updates_replaces_model_counts_with_hole_derived_counts():
    result = _result({**MODEL_COUNTS, **CARD_FIELDS})

    updates = selected_player_scorecard_updates(result, 0)

    assert {field: updates[field] for field in COUNT_FIELD_KEYS} == EXPECTED_COUNTS
    assert sum(updates[field] for field in COUNT_FIELD_KEYS) == 18
    for field, value in CARD_FIELDS.items():
        assert updates[field] == value


@pytest.mark.parametrize(
    ("pars", "hole_scores"),
    [
        ({hole: 4 for hole in range(1, 18)}, None),
        (None, {hole: 5 for hole in range(2, 19)}),
        ({}, None),
        (None, {}),
    ],
    ids=["pars-missing-18", "hole-scores-missing-1", "empty-pars", "empty-hole-scores"],
)
def test_selected_player_scorecard_updates_returns_found_fields_when_incomplete(pars, hole_scores):
    found_fields = {**MODEL_COUNTS, **CARD_FIELDS}
    result = _result(found_fields, pars=pars, hole_scores=hole_scores)

    assert selected_player_scorecard_updates(result, 0) == found_fields


@pytest.mark.parametrize("selected_index", [None, True, False, "0", 1.0, 99])
def test_selected_player_scorecard_updates_returns_empty_for_invalid_selection(selected_index):
    result = _result(CARD_FIELDS)

    assert selected_player_scorecard_updates(result, selected_index) == {}


def test_apply_selected_player_scorecard_updates_writes_all_hole_derived_count_widgets():
    result = _result({**MODEL_COUNTS, **CARD_FIELDS})
    widget_keys = {field: f"count_{field}" for field in COUNT_FIELD_KEYS}
    session_state = {key: 0 for key in widget_keys.values()}

    applied = apply_selected_player_scorecard_updates(result, 0, widget_keys, session_state)

    for field in COUNT_FIELD_KEYS:
        assert session_state[widget_keys[field]] == EXPECTED_COUNTS[field]
    assert applied == [field for field in LEAGUE_SCORECARD_FIELD_KEYS if field in COUNT_FIELD_KEYS]


def test_apply_selected_player_scorecard_updates_only_writes_present_widget_keys():
    result = _result(CARD_FIELDS)
    widget_keys = {"eagles": "count_eagles", "birdies": "count_birdies"}
    session_state = {"count_eagles": 0, "count_birdies": 0, "count_pars": 99}

    applied = apply_selected_player_scorecard_updates(result, 0, widget_keys, session_state)

    assert session_state["count_eagles"] == EXPECTED_COUNTS["eagles"]
    assert session_state["count_birdies"] == EXPECTED_COUNTS["birdies"]
    assert session_state["count_pars"] == 99
    assert applied == ["eagles", "birdies"]


def test_apply_selected_player_scorecard_updates_does_not_touch_saved_scorecard_files(tmp_path, monkeypatch):
    monkeypatch.setattr(league_scorecard, "SCORECARD_IMAGES_DIR", str(tmp_path))
    existing = tmp_path / "existing.jpg"
    existing.write_bytes(b"original")
    mtime_ns = existing.stat().st_mtime_ns
    result = _result(CARD_FIELDS)
    widget_keys = {field: f"count_{field}" for field in COUNT_FIELD_KEYS}

    apply_selected_player_scorecard_updates(result, 0, widget_keys, {})

    assert sorted(path.name for path in tmp_path.iterdir()) == ["existing.jpg"]
    assert existing.read_bytes() == b"original"
    assert existing.stat().st_mtime_ns == mtime_ns
