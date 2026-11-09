"""Feature 012, phase 3: apply only the selected player's fields."""
from league_scorecard import (
    LEAGUE_SCORECARD_FIELD_KEYS,
    LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY,
    LeagueScorecardPlayersResult,
    ScorecardPlayerEntry,
    apply_selected_player_scorecard_updates,
    selected_player_scorecard_updates,
)

WIDGET_KEYS = {field: f"league_{field}" for field in LEAGUE_SCORECARD_FIELD_KEYS}
RESULT = LeagueScorecardPlayersResult([
    ScorecardPlayerEntry(0, "Neo", {"date": "2026-06-23", "net": 2, "birdies": 3}),
    ScorecardPlayerEntry(1, "刘北南", {"gross": 80}),
])


def test_selector_key_constant():
    assert LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY == "league_scorecard_selected_player"


def test_no_selection_returns_empty_mapping():
    assert selected_player_scorecard_updates(RESULT, None) == {}
    assert selected_player_scorecard_updates(RESULT, 99) == {}
    assert selected_player_scorecard_updates(RESULT, True) == {}


def test_selected_entry_returns_only_its_fields():
    assert selected_player_scorecard_updates(RESULT, 0) == {"date": "2026-06-23", "net": 2, "birdies": 3}
    assert selected_player_scorecard_updates(RESULT, 1) == {"gross": 80}


def test_no_selection_clears_the_scorecard_widget_keys():
    session = {"league_net": 5, "league_gross": 90, "unrelated": 1}
    assert apply_selected_player_scorecard_updates(RESULT, None, WIDGET_KEYS, session) == []
    assert session == {"unrelated": 1}


def test_selecting_a_player_writes_only_its_present_fields():
    session = {"league_net": 9, "league_birdies": 9, "league_pars": 9}
    assert apply_selected_player_scorecard_updates(RESULT, 0, WIDGET_KEYS, session) == ["date", "net", "birdies"]
    assert session == {"league_date": "2026-06-23", "league_net": 2, "league_birdies": 3}


def test_switching_players_replaces_previous_values():
    session = {}
    apply_selected_player_scorecard_updates(RESULT, 0, WIDGET_KEYS, session)
    assert apply_selected_player_scorecard_updates(RESULT, 1, WIDGET_KEYS, session) == ["gross"]
    assert session == {"league_gross": 80}


def test_duplicate_labels_are_selected_by_index():
    result = LeagueScorecardPlayersResult([
        ScorecardPlayerEntry(0, "Neo", {"net": 1}),
        ScorecardPlayerEntry(1, "Neo", {"net": 3}),
    ])
    session = {}
    apply_selected_player_scorecard_updates(result, 1, WIDGET_KEYS, session)
    assert session == {"league_net": 3}


def test_applying_the_same_selection_twice_is_stable():
    session = {}
    apply_selected_player_scorecard_updates(RESULT, 1, WIDGET_KEYS, session)
    snapshot = dict(session)
    apply_selected_player_scorecard_updates(RESULT, 1, WIDGET_KEYS, session)
    assert session == snapshot
