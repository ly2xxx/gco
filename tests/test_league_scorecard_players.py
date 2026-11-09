"""Feature 012, phase 1: every player on a parsed scorecard, labelled as printed."""
from league_scorecard import ScorecardPlayerEntry, scorecard_player_entries


def test_entries_one_per_player_in_printed_order():
    entries = scorecard_player_entries({
        "players": [
            {"label": "Neo", "fields": {"net": 2}},
            {"label": "刘北南", "fields": {"gross": 80}},
            {"label": "张纬", "fields": {}},
        ]
    })
    assert [e.index for e in entries] == [0, 1, 2]
    assert [e.label for e in entries] == ["Neo", "刘北南", "张纬"]
    assert all(isinstance(e, ScorecardPlayerEntry) for e in entries)


def test_labels_are_exactly_as_printed():
    assert [e.label for e in scorecard_player_entries({"players": [{"label": "Neo", "fields": {}}]})] == ["Neo"]
    assert [
        e.label for e in scorecard_player_entries({"players": [{"column_header": "Player 2", "fields": {}}]})
    ] == ["Player 2"]


def test_no_assumed_labels_are_synthesized():
    entries = scorecard_player_entries({
        "players": [{"fields": {"net": 1}}, {"column_header": "Player 2", "fields": {}}]
    })
    assert [e.label for e in entries] == ["Player 2"]
    assert [e.index for e in entries] == [0]
    assert all(e.label not in {"A", "B", "C", "Marker"} for e in entries)


def test_duplicate_labels_remain_separate_entries():
    entries = scorecard_player_entries({
        "players": [{"label": "Neo", "fields": {"net": 1}}, {"label": "Neo", "fields": {"net": 3}}]
    })
    assert [e.index for e in entries] == [0, 1]
    assert [e.label for e in entries] == ["Neo", "Neo"]
    assert entries[0].found_fields == {"net": 1}
    assert entries[1].found_fields == {"net": 3}


def test_found_fields_are_normalized_target_fields_only():
    entries = scorecard_player_entries({
        "players": [{"label": "Neo", "fields": {"net_score": "+2", "birdie": 3, "bogus": 1}}]
    })
    assert entries[0].found_fields == {"net": 2, "birdies": 3}


def test_missing_or_malformed_players_returns_empty():
    for parsed in ({}, {"players": None}, {"players": "nope"}, {"players": []}, {"players": [1, "x", None]}):
        assert scorecard_player_entries(parsed) == [], parsed
