"""Feature 013, phase 3: the League admin score form shows the round's saved scorecard.

The first tests read the page source (the plan's Definition of done). The rest run
the real page as an admin against a temporary scorecard folder: no network, and no
file upload, so they also run on the Streamlit the deployed app uses (1.55).
"""
import ast
import struct
import sys
import zlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PAGE_PATH = REPO_ROOT / "pages" / "3_🏆_League.py"
SOURCE = PAGE_PATH.read_text(encoding="utf-8")
ADMIN_TOKEN = "test-admin-token"


def _preview_calls():
    return [
        node for node in ast.walk(ast.parse(SOURCE))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "render_league_scorecard_preview"
    ]


def test_league_score_form_calls_saved_scorecard_preview_with_selection_values():
    calls = _preview_calls()
    assert len(calls) == 1, "the form must call the preview exactly once"
    call = calls[0]
    assert len(call.args) == 3 and call.keywords == []
    assert all(isinstance(arg, (ast.Name, ast.Attribute, ast.Subscript)) for arg in call.args)
    assert "tournament, game_label, player = t_sel, g_sel, p_sel" in SOURCE


def test_league_page_compiles_after_preview_wiring():
    compile(SOURCE, str(PAGE_PATH), "exec")


def test_preview_is_called_in_the_admin_block_and_outside_the_form():
    call_at = SOURCE.index("render_league_scorecard_preview(tournament, game_label, player)")
    assert SOURCE.index("if is_admin_user():") < call_at, "the saved scorecard is for admins only"
    assert call_at < SOURCE.index('with st.form("league_score_form")'), "inside the form it would not rerun on a new selection"


# ── The page itself, run as an admin ─────────────────────────────────────────

def _png(width=40, height=30):
    """A small valid PNG, so Streamlit can display it."""
    rows = b"".join(b"\x00" + b"\xff\xff\xff" * width for _ in range(height))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


@pytest.fixture
def league_page(monkeypatch, tmp_path):
    """Runs the League page against tmp_path as its scorecard folder.

    Returns ``start(admin=True, repo=None)`` -> AppTest, plus the tournament and players.
    """
    AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
    from streamlit.runtime.pages_manager import PagesManager

    import data
    import league_scorecard

    # See tests/test_league_deep_dive_wiring.py: keep the front-page AppTests' pages/ flag intact.
    monkeypatch.setattr(PagesManager, "uses_pages_directory", None)
    real_find = league_scorecard.find_saved_scorecard
    monkeypatch.setattr(
        league_scorecard,
        "find_saved_scorecard",
        lambda tournament, game_label, player: real_find(tournament, game_label, player, directory=str(tmp_path)),
    )
    settings = {"repo": None}
    monkeypatch.setattr(league_scorecard, "scorecard_github_repo", lambda: settings["repo"])

    def start(admin=True, repo=None):
        settings["repo"] = repo
        at = AppTest.from_file(str(PAGE_PATH), default_timeout=60)
        if admin:
            at.secrets["ADMIN_TOKEN"] = ADMIN_TOKEN
            at.query_params["admin"] = ADMIN_TOKEN
        return at.run()

    tournament = next(iter(data.LEAGUE_TOURNAMENTS))
    return start, tournament, list(data.PLAYERS), tmp_path


def _save_card(folder, tournament, game, player, timestamp, content=None, suffix=".png"):
    name = f"league_{tournament}_{game}_{player}_{timestamp}{suffix}".replace(" ", "_")
    (folder / name).write_bytes(_png() if content is None else content)
    return name


def _select_round(at, player, game):
    next(w for w in at.selectbox if w.label.startswith("球员 Player")).select(player)
    next(w for w in at.selectbox if w.label.startswith("轮次 Game")).select(game)
    return at.run()


def _images(at):
    """Image elements anywhere on the page, dialogs included ("imgs" before Streamlit 1.6x, "image" after)."""
    return list(at.get("imgs")) + list(at.get("image"))


def _view_buttons(at):
    return [b for b in at.button if (b.key or "").startswith("view_saved_scorecard_")]


def test_admin_sees_the_rounds_saved_scorecard_as_a_thumbnail(league_page):
    start, tournament, players, folder = league_page
    _save_card(folder, tournament, "Game 1", players[0], "20260101000000")
    newest = _save_card(folder, tournament, "Game 1", players[0], "20260315101500")
    at = _select_round(start(), players[0], "Game 1")

    images = _images(at)
    assert len(images) == 1
    assert images[0].proto.link == "", "no GITHUB_REPO: the thumbnail is not a link"
    assert [b.key for b in _view_buttons(at)] == [f"view_saved_scorecard_{newest}"]
    assert any("Saved scorecard · 2026-03-15" in c.value for c in at.caption)
    assert at.exception == []


def test_thumbnail_links_to_the_original_on_github_when_the_repo_is_configured(league_page):
    start, tournament, players, folder = league_page
    name = _save_card(folder, tournament, "Game 1", players[0], "20260101000000")
    at = _select_round(start(repo="owner/repo"), players[0], "Game 1")

    from urllib.parse import quote

    images = _images(at)
    assert len(images) == 1
    assert images[0].proto.link == f"https://raw.githubusercontent.com/owner/repo/HEAD/scorecard_images/{quote(name)}"
    assert any("Click the thumbnail to open the original" in c.value for c in at.caption)
    assert at.exception == []


def test_view_button_opens_the_saved_scorecard_in_a_dialog(league_page):
    start, tournament, players, folder = league_page
    _save_card(folder, tournament, "Game 1", players[0], "20260101000000")
    at = _select_round(start(), players[0], "Game 1")

    _view_buttons(at)[0].click()
    at.run()

    assert len(_images(at)) == 2, "the thumbnail, and the same file in the dialog"
    assert at.exception == []


def test_changing_the_selection_updates_or_removes_the_thumbnail(league_page):
    start, tournament, players, folder = league_page
    first = _save_card(folder, tournament, "Game 1", players[0], "20260101000000")
    second = _save_card(folder, tournament, "Game 2", players[1], "20260202000000")
    at = _select_round(start(), players[0], "Game 1")
    assert [b.key for b in _view_buttons(at)] == [f"view_saved_scorecard_{first}"]

    at = _select_round(at, players[1], "Game 2")
    assert [b.key for b in _view_buttons(at)] == [f"view_saved_scorecard_{second}"]
    assert len(_images(at)) == 1

    at = _select_round(at, players[1], "Game 1")  # nothing saved for this round
    assert _view_buttons(at) == []
    assert _images(at) == []
    assert at.exception == []


def test_round_without_a_saved_scorecard_shows_nothing_extra(league_page):
    start, tournament, players, folder = league_page
    _save_card(folder, tournament, "Game 15", players[0], "20260101000000")  # not Game 1
    at = _select_round(start(), players[0], "Game 1")

    assert _images(at) == []
    assert _view_buttons(at) == []
    assert not any("Saved scorecard" in c.value for c in at.caption)
    assert at.exception == []


def test_visitors_who_are_not_admins_never_see_saved_scorecards(league_page):
    start, tournament, players, folder = league_page
    for player in players:
        _save_card(folder, tournament, "Game 1", player, "20260101000000")
    at = start(admin=False)

    assert _images(at) == []
    assert _view_buttons(at) == []
    assert at.exception == []


def test_saved_file_that_cannot_be_displayed_does_not_break_the_form(league_page):
    start, tournament, players, folder = league_page
    _save_card(folder, tournament, "Game 1", players[0], "20260101000000", content=b"", suffix=".jpg")
    at = _select_round(start(), players[0], "Game 1")

    assert at.exception == []
    assert _images(at) == [] and _view_buttons(at) == []
    assert any(b.label.startswith("✅ 保存成绩 Save") for b in at.button), "the score form still renders"
