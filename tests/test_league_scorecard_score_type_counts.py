"""Feature 015, phase 1: score-type counts from the card's pars and one player's hole scores."""
import pytest

from league_scorecard import COUNT_FIELD_KEYS, scorecard_score_type_counts

COMPLETE_PARS = {hole: 4 for hole in range(1, 19)}
COMPLETE_SCORES = {hole: 5 for hole in range(1, 19)}


def test_scorecard_score_type_counts_categorizes_all_differences_and_sums_to_18():
    pars = {hole: 4 for hole in range(1, 19)}
    hole_scores = {1: 1, 2: 2, 3: 3, 4: 4, 5: 4, 6: 5}
    hole_scores.update({hole: 6 for hole in range(7, 19)})

    result = scorecard_score_type_counts(pars, hole_scores)

    assert result == {"eagles": 2, "birdies": 1, "pars": 2, "bogeys": 1, "double_bogeys_or_worse": 12}
    assert list(result) == list(COUNT_FIELD_KEYS)
    assert sum(result.values()) == 18


def test_scorecard_score_type_counts_real_card():
    # 李扬 · 2026个人联赛 · Game 5: the counts the admin entered by hand for that round.
    pars = dict(zip(range(1, 19), [4, 4, 4, 4, 4, 3, 5, 4, 4, 4, 4, 3, 4, 4, 5, 4, 3, 4]))
    hole_scores = dict(zip(range(1, 19), [6, 7, 6, 5, 7, 5, 6, 6, 8, 6, 5, 3, 5, 5, 5, 6, 4, 5]))

    result = scorecard_score_type_counts(pars, hole_scores)

    assert result == {"eagles": 0, "birdies": 0, "pars": 2, "bogeys": 7, "double_bogeys_or_worse": 9}


@pytest.mark.parametrize(
    ("pars", "hole_scores"),
    [
        ({}, COMPLETE_SCORES),
        (COMPLETE_PARS, {}),
        ({hole: 4 for hole in range(1, 18)}, COMPLETE_SCORES),
        (COMPLETE_PARS, {hole: 5 for hole in range(2, 19)}),
    ],
    ids=["empty-pars", "empty-hole-scores", "pars-missing-18", "hole-scores-missing-1"],
)
def test_scorecard_score_type_counts_returns_none_for_empty_or_missing_holes(pars, hole_scores):
    assert scorecard_score_type_counts(pars, hole_scores) is None


def test_scorecard_score_type_counts_returns_none_for_non_mapping_inputs():
    assert scorecard_score_type_counts(None, COMPLETE_SCORES) is None
    assert scorecard_score_type_counts(COMPLETE_PARS, None) is None
