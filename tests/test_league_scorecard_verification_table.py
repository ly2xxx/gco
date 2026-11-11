"""Feature 014, phase 2: the selected player's hole scores and the 21-cell check table."""
from league_scorecard import (
    VERIFICATION_TABLE_COLUMNS,
    LeagueScorecardPlayersResult,
    ScorecardPlayerEntry,
    scorecard_hole_totals,
    scorecard_verification_row,
    scorecard_verification_table,
    selected_player_hole_scores,
)

ALL = range(1, 19)


def test_columns_are_the_18_holes_then_out_in_total():
    assert VERIFICATION_TABLE_COLUMNS == tuple(str(h) for h in ALL) + ("Out", "In", "Total")


def test_table_has_exactly_two_rows_and_21_ordered_cells():
    table = scorecard_verification_table({h: 4 for h in ALL}, {h: 5 for h in ALL})
    assert list(table) == ["Par", "Score"]
    assert all(isinstance(row, list) and len(row) == 21 for row in table.values())
    assert table["Par"][:18] == [4] * 18 and table["Score"][:18] == [5] * 18
    assert table["Par"][18:] == [36, 36, 72]
    assert table["Score"][18:] == [45, 45, 90]


def test_unread_holes_stay_blank_and_totals_never_partial():
    pars = {h: 4 for h in ALL if h != 9}
    scores = {h: (6 if h == 5 else 5) for h in ALL if h != 9}
    table = scorecard_verification_table(pars, scores)
    assert table["Par"][4] == 4 and table["Par"][8] is None
    assert table["Score"][4] == 6 and table["Score"][8] is None
    assert table["Par"][18:] == [None, 36, None]
    assert table["Score"][18:] == [None, 45, None]


def test_totals_are_sums_only_when_each_segment_is_complete():
    full = {h: 3 for h in ALL}
    assert scorecard_hole_totals(full) == {"Out": 27, "In": 27, "Total": 54}
    assert scorecard_hole_totals({h: 3 for h in ALL if h != 5}) == {"Out": None, "In": 27, "Total": None}
    assert scorecard_hole_totals({h: 3 for h in ALL if h != 15}) == {"Out": 27, "In": None, "Total": None}
    assert scorecard_hole_totals({}) == {"Out": None, "In": None, "Total": None}
    assert scorecard_hole_totals(None) == {"Out": None, "In": None, "Total": None}


def test_selected_player_scores_are_copied_and_invalid_selection_returns_empty():
    result = LeagueScorecardPlayersResult([
        ScorecardPlayerEntry(0, "A", {}, {1: 4}),
        ScorecardPlayerEntry(1, "B", {}, {1: 6}),
    ])
    scores = selected_player_hole_scores(result, 1)
    assert scores == {1: 6}
    scores[1] = 99
    assert result.players[1].hole_scores == {1: 6}
    for bad in (None, True, False, "1", 1.0, 99):
        assert selected_player_hole_scores(result, bad) == {}, bad
    assert selected_player_hole_scores(None, 0) == {}


def test_verification_row_places_values_in_verification_table_column_order():
    values = {h: (3 if h == 18 else 4 if h == 1 else 5) for h in ALL}
    row = scorecard_verification_row(values)
    assert row[0] == 4 and row[17] == 3
    assert row[18:] == [4 + 5 * 8, 5 * 8 + 3, 4 + 5 * 16 + 3]
    missing = scorecard_verification_row({h: v for h, v in values.items() if h != 7})
    assert missing[6] is None and missing[18] is None and missing[20] is None
    assert missing[19] == 5 * 8 + 3
