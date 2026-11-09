"""Feature 012, phase 4: the League page reads every card player and applies only the pick."""
import re
from pathlib import Path

PAGE = Path(__file__).resolve().parents[1] / "pages" / "3_🏆_League.py"
SOURCE = PAGE.read_text(encoding="utf-8")
SELECTOR_RE = re.compile(r'st\.selectbox\(\s*"Player",.*?\n\s*\)', re.S)
READ_RE = re.compile(r"read_league_scorecard_players\(\s*image_bytes")
APPLY_RE = re.compile(
    r"apply_selected_player_scorecard_updates\(\s*players_result,\s*selected_index,\s*widget_keys,"
    r"\s*st\.session_state,?\s*\)"
)


def _league_scorecard_imports(source):
    names = set()
    for match in re.finditer(r"from league_scorecard import (\([^)]*\)|[^\n]+)", source):
        chunk = match.group(1).strip().strip("()")
        for part in chunk.split(","):
            name = part.strip().split(" as ")[0].strip()
            if name:
                names.add(name)
    return names


def test_page_imports_the_multi_player_helpers():
    names = _league_scorecard_imports(SOURCE)
    assert {
        "read_league_scorecard_players",
        "apply_selected_player_scorecard_updates",
        "LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY",
    } <= names


def test_player_selector_lists_every_entry_labelled_as_printed():
    match = SELECTOR_RE.search(SOURCE)
    assert match is not None
    text = " ".join(match.group(0).split())
    assert "options=[player.index for player in players_result.players]" in text
    assert "format_func=lambda index: players_result.players[index].label" in text
    assert "index=None" in text
    assert "key=LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY" in text


def test_selector_sits_above_the_selected_player_apply():
    read = READ_RE.search(SOURCE)
    selector = SELECTOR_RE.search(SOURCE)
    apply = APPLY_RE.search(SOURCE)
    assert read and selector and apply
    assert read.start() < selector.start() < apply.start()


def test_page_no_longer_uses_the_single_player_helpers():
    assert "read_league_scorecard(" not in SOURCE
    assert "apply_scorecard_updates(" not in SOURCE
