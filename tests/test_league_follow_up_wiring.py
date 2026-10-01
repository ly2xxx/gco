import re
from pathlib import Path

LEAGUE_PAGE = Path(__file__).resolve().parents[1] / "pages" / "3_🏆_League.py"
SOURCE = LEAGUE_PAGE.read_text(encoding="utf-8")
LINES = SOURCE.splitlines()


def line_indexes(pattern: str) -> list[int]:
    return [index for index, line in enumerate(LINES) if re.search(pattern, line)]


def follow_up_call_indexes() -> list[int]:
    return [
        index
        for index in line_indexes(r"\brender_follow_up_questions\(")
        if not LINES[index].lstrip().startswith(("from ", "import "))
    ]


def indentation(index: int) -> int:
    return len(LINES[index]) - len(LINES[index].lstrip())


def test_summary_return_value_is_passed_to_follow_up_fragment():
    """Spec behaviour 3."""
    assignment = line_indexes(r"^\s*summary\s*=\s*.*render_season_summary\(")
    calls = follow_up_call_indexes()

    assert assignment
    assert calls
    assert min(calls) > min(assignment)
    assert re.search(
        r"render_follow_up_questions\(\s*player_name\s*,\s*season_rounds\s*,\s*summary\s*\)",
        LINES[min(calls)],
    )


def test_follow_up_call_is_guarded_by_non_empty_summary():
    """Spec behaviours 3 and 5."""
    # The guard sits inside the deep-dive's `if not p_df.empty:` block, so allow its indentation.
    guards = line_indexes(r"^\s*if summary:\s*$")
    call = min(follow_up_call_indexes())

    assert guards
    assert call > min(guards)
    assert indentation(call) > indentation(min(guards))
