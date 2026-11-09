"""Phase 1: field filtering and normalisation for the League scorecard auto-fill."""
import dataclasses
from datetime import date, datetime

import pytest

from league_scorecard import (
    LEAGUE_SCORECARD_FIELD_KEYS,
    ScorecardReadResult,
    match_venue_name,
    scorecard_field_updates,
    venue_names_from_records,
)


def test_league_scorecard_field_keys_and_result_contract():
    assert LEAGUE_SCORECARD_FIELD_KEYS == (
        "date",
        "venue",
        "net",
        "gross",
        "stableford",
        "eagles",
        "birdies",
        "pars",
        "bogeys",
        "double_bogeys_or_worse",
    )
    result = ScorecardReadResult({})
    assert result.unavailable_reason is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.found_fields = {}


def test_scorecard_field_updates_keeps_only_found_target_fields():
    result = scorecard_field_updates({
        "date": "2026/06/23",
        "venue": "Pine Valley",
        "net": 5,
        "gross": 77,
        "stableford": 36,
        "eagles": 1,
        "birdies": 2,
        "pars": 3,
        "bogeys": 4,
        "double_bogeys_or_worse": 5,
    })
    assert tuple(result) == LEAGUE_SCORECARD_FIELD_KEYS
    assert result["date"] == "2026-06-23"
    for key, value in result.items():
        if key not in ("date", "venue"):
            assert type(value) is int, key
    assert result["venue"] == "Pine Valley"


def test_scorecard_field_updates_drops_missing_empty_and_unparseable():
    assert scorecard_field_updates({
        "net": None,
        "gross": "",
        "stableford": "n/a",
        "date": "unknown",
        "venue": "   ",
        "birdies": [],
    }) == {}


def test_scorecard_field_updates_drops_not_found_markers():
    assert scorecard_field_updates({
        "net": {"value": 5, "found": False},
        "gross": {"value": 77, "found": True},
        "stableford": {"value": 36, "found": "no"},
    }) == {"gross": 77}


def test_scorecard_field_updates_parses_numeric_forms():
    assert scorecard_field_updates({"net": "+5", "gross": " 12 ", "stableford": 7.0}) == {
        "net": 5,
        "gross": 12,
        "stableford": 7,
    }
    for bad in (7.5, True, "five", object()):
        assert scorecard_field_updates({"gross": bad}) == {}, bad
    assert scorecard_field_updates({"eagles": -1}) == {}
    assert scorecard_field_updates({"gross": 250}) == {}
    assert scorecard_field_updates({"net": -12}) == {"net": -12}


@pytest.mark.parametrize(
    "raw",
    (
        "2026-06-23",
        "2026/06/23",
        "2026.06.23",
        "2026年6月23日",
        "20260623",
        date(2026, 6, 23),
        datetime(2026, 6, 23, 18, 0),
    ),
)
def test_scorecard_field_updates_normalises_dates(raw):
    assert scorecard_field_updates({"date": raw}) == {"date": "2026-06-23"}


def test_match_venue_name_prefers_known_venue():
    assert match_venue_name("pine valley golf club", ["Pine Valley Golf Club"]) == "Pine Valley Golf Club"
    assert match_venue_name(
        "Pine Valey Golf Club", ["Pine Valley Golf Club", "Augusta National"]
    ) == "Pine Valley Golf Club"
    assert match_venue_name("Somewhere Else", ["Augusta National"]) == "Somewhere Else"
    assert match_venue_name("  Pine   Valley ", []) == "Pine Valley"


def test_venue_names_from_records():
    records = [{"venue": "A"}, {"venue": " A "}, {"Venue": "B"}, {"venue": ""}, {}]
    assert venue_names_from_records(records) == ["A", "B"]


def test_scorecard_field_updates_aliases_and_unknown_keys():
    result = scorecard_field_updates({
        "Total": "77",
        "net_score": "5",
        "Double Bogey or Worse": "6",
        "player": "Neo",
    })
    assert tuple(result) == ("net", "gross", "double_bogeys_or_worse")
    assert result == {"net": 5, "gross": 77, "double_bogeys_or_worse": 6}
