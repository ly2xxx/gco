"""Feature 013, phase 1: find the saved scorecard for a round, and its GitHub address."""
import os

import pytest
import streamlit

import league_scorecard
from league_scorecard import (
    SCORECARD_IMAGE_SUFFIXES,
    SCORECARD_IMAGES_DIR,
    SCORECARD_THUMBNAIL_WIDTH,
    SavedScorecard,
    find_saved_scorecard,
    game_number_from_label,
    scorecard_github_repo,
    scorecard_image_url,
)


def _touch(directory, *names):
    for name in names:
        (directory / name).write_bytes(b"")


def test_constants():
    assert SCORECARD_IMAGES_DIR == "scorecard_images"
    assert SCORECARD_THUMBNAIL_WIDTH == 160
    assert SCORECARD_IMAGE_SUFFIXES == (".jpg", ".jpeg", ".png", ".webp", ".gif")


def test_game_number_from_label_parses_supported_labels():
    assert game_number_from_label("Game 5") == 5
    assert game_number_from_label("game 15") == 15
    assert game_number_from_label("Game 0") == 0
    assert game_number_from_label("  Game   7 ") == 7
    for label in ("Game5", "5", None, "", "Game five", "Game 5 extra", 5, object()):
        assert game_number_from_label(label) is None, label


def test_find_saved_scorecard_selects_newest_matching_timestamp(tmp_path):
    _touch(tmp_path, "league_Cup_Game_2_Alice_20260101000000.jpg", "league_Cup_Game_2_Alice_20260202000000.png")
    # The older file name gets the newer modification time: the name's timestamp decides.
    os.utime(tmp_path / "league_Cup_Game_2_Alice_20260101000000.jpg", (2_000_000_000, 2_000_000_000))
    os.utime(tmp_path / "league_Cup_Game_2_Alice_20260202000000.png", (1_000_000_000, 1_000_000_000))

    result = find_saved_scorecard("Cup", "Game 2", "Alice", directory=str(tmp_path))

    assert result == SavedScorecard(
        filename="league_Cup_Game_2_Alice_20260202000000.png",
        path=str(tmp_path / "league_Cup_Game_2_Alice_20260202000000.png"),
        timestamp="20260202000000",
    )


def test_find_saved_scorecard_matches_exact_game_number(tmp_path):
    _touch(
        tmp_path,
        "league_Cup_Game_1_Alice_20260303000000.jpg",
        "league_Cup_Game_5_Alice_20260101000000.jpg",
        "league_Cup_Game_15_Alice_20260404000000.jpg",
    )
    result = find_saved_scorecard("Cup", "Game 5", "Alice", directory=str(tmp_path))
    assert result is not None
    assert result.filename == "league_Cup_Game_5_Alice_20260101000000.jpg"


def test_find_saved_scorecard_ignores_other_tournaments_players_and_odd_names(tmp_path):
    _touch(
        tmp_path,
        "league_Other_Game_5_Alice_20260101000000.jpg",       # another tournament
        "league_Cup_Game_5_Alicia_20260101000000.jpg",        # another player
        "league_Cup_Game_5_Alice_Smith_20260101000000.jpg",   # a longer player name
        "league_Cup_Game_5_Alice_2026x101000000.jpg",         # not a timestamp
        "league_Cup_Game_5_Alice_.jpg",                       # no timestamp
        "cup_F_P4_vs_P11_20260816222355.jpg",                 # a Cup scorecard
    )
    assert find_saved_scorecard("Cup", "Game 5", "Alice", directory=str(tmp_path)) is None


def test_find_saved_scorecard_returns_none_for_incomplete_selection_or_missing_directory(tmp_path):
    _touch(tmp_path, "league_Cup_Game_2_Alice_20260101000000.jpg")
    directory = str(tmp_path)
    assert find_saved_scorecard("Cup", "Game 2", "Alice", directory=directory) is not None
    for tournament, game_label, player in (
        (None, "Game 2", "Alice"),
        ("", "Game 2", "Alice"),
        ("   ", "Game 2", "Alice"),
        ("Cup", None, "Alice"),
        ("Cup", "", "Alice"),
        ("Cup", "2", "Alice"),
        ("Cup", "Game 2", None),
        ("Cup", "Game 2", ""),
        ("Cup", "Game 2", "  "),
    ):
        assert find_saved_scorecard(tournament, game_label, player, directory=directory) is None
    assert find_saved_scorecard("Cup", "Game 2", "Alice", directory=str(tmp_path / "missing")) is None


def test_find_saved_scorecard_returns_none_when_the_directory_cannot_be_listed(tmp_path, monkeypatch):
    _touch(tmp_path, "league_Cup_Game_2_Alice_20260101000000.jpg")

    def refuse(_directory):
        raise PermissionError("no access")

    monkeypatch.setattr(league_scorecard.os, "listdir", refuse)
    assert find_saved_scorecard("Cup", "Game 2", "Alice", directory=str(tmp_path)) is None


def test_find_saved_scorecard_supports_displayable_suffixes(tmp_path):
    for index, suffix in enumerate((".jpg", ".jpeg", ".png", ".webp", ".gif", ".JPG")):
        folder = tmp_path / f"case{index}"
        folder.mkdir()
        _touch(folder, f"league_Cup_Game_2_Alice_20260101000000{suffix}", "league_Cup_Game_2_Alice_20270101000000.txt")
        result = find_saved_scorecard("Cup", "Game 2", "Alice", directory=str(folder))
        assert result is not None and result.filename.endswith(suffix), suffix
    only_text = tmp_path / "only_text"
    only_text.mkdir()
    _touch(only_text, "league_Cup_Game_2_Alice_20260101000000.txt")
    assert find_saved_scorecard("Cup", "Game 2", "Alice", directory=str(only_text)) is None


def test_find_saved_scorecard_matches_names_as_the_page_saves_them(tmp_path):
    """Chinese names, and spaces written as "_" the way the League page names its uploads."""
    _touch(tmp_path, "league_2026个人联赛_Game_5_李扬_20261109172833.jpg", "league_Spring_Cup_Game_1_Li_Yang_20260101000000.jpg")
    chinese = find_saved_scorecard("2026个人联赛", "Game 5", "李扬", directory=str(tmp_path))
    assert chinese is not None and chinese.timestamp == "20261109172833"
    spaced = find_saved_scorecard("Spring Cup", "Game 1", "Li Yang", directory=str(tmp_path))
    assert spaced is not None and spaced.filename == "league_Spring_Cup_Game_1_Li_Yang_20260101000000.jpg"


def test_find_saved_scorecard_reads_file_names_only(tmp_path, monkeypatch):
    _touch(tmp_path, "league_Cup_Game_2_Alice_20260101000000.jpg")

    def refuse(*args, **kwargs):
        raise AssertionError("the image must not be opened")

    monkeypatch.setattr("builtins.open", refuse)
    assert find_saved_scorecard("Cup", "Game 2", "Alice", directory=str(tmp_path)) is not None


def test_scorecard_image_url_builds_raw_github_url():
    assert (
        scorecard_image_url("owner/repo", "foo.jpg")
        == "https://raw.githubusercontent.com/owner/repo/HEAD/scorecard_images/foo.jpg"
    )
    for repo in (None, "", "   "):
        assert scorecard_image_url(repo, "foo.jpg") is None
    assert scorecard_image_url("owner/repo", "") is None


def test_scorecard_image_url_quotes_the_file_name():
    url = scorecard_image_url("ly2xxx/gco", "league_2026个人联赛_Game_5_李扬_20261109172833.jpg")
    assert url == (
        "https://raw.githubusercontent.com/ly2xxx/gco/HEAD/scorecard_images/"
        "league_2026%E4%B8%AA%E4%BA%BA%E8%81%94%E8%B5%9B_Game_5_%E6%9D%8E%E6%89%AC_20261109172833.jpg"
    )
    assert scorecard_image_url("o/r", "a#b?c.jpg").endswith("/a%23b%3Fc.jpg")


def test_scorecard_github_repo_reads_environment_and_blank_is_unset(monkeypatch):
    monkeypatch.setattr(streamlit, "secrets", {})  # not this machine's .streamlit/secrets.toml
    monkeypatch.setenv("GITHUB_REPO", "owner/repo")
    assert scorecard_github_repo() == "owner/repo"
    monkeypatch.setenv("GITHUB_REPO", "   ")
    assert scorecard_github_repo() is None
    monkeypatch.delenv("GITHUB_REPO")
    assert scorecard_github_repo() is None


def test_scorecard_github_repo_falls_back_to_streamlit_secrets(monkeypatch):
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    monkeypatch.setattr(streamlit, "secrets", {"GITHUB_REPO": "ly2xxx/gco"})
    assert scorecard_github_repo() == "ly2xxx/gco"
