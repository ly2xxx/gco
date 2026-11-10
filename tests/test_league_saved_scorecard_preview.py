"""Feature 013, phase 2: the League page's saved-scorecard thumbnail and View dialog.

The helpers are taken out of the page source and run against a recording stand-in
for Streamlit, so no server, browser, image file or network is involved.
"""
import ast
import logging
from pathlib import Path

import pytest

from league_scorecard import SCORECARD_THUMBNAIL_WIDTH, SavedScorecard, scorecard_image_url

PAGE = Path(__file__).resolve().parents[1] / "pages" / "3_🏆_League.py"
HELPERS = ("_saved_scorecard_dialog", "show_saved_scorecard_dialog", "render_league_scorecard_preview")
LABELS = ("SAVED_SCORECARD_LABEL", "SAVED_SCORECARD_LINK_HINT", "SAVED_SCORECARD_VIEW_LABEL")
CARD = SavedScorecard("foo.jpg", "scorecard_images/foo.jpg", "20260101000000")
RAW_URL = "https://raw.githubusercontent.com/owner/repo/HEAD/scorecard_images/foo.jpg"


class FakeStreamlit:
    """Records what the helpers ask Streamlit to show."""

    def __init__(self):
        self.image_calls = []      # (image, width, link)
        self.caption_calls = []
        self.markdown_calls = []
        self.button_calls = []     # (label, key)
        self.dialog_title = None
        self.dialog_kwargs = None
        self.dialog_opened = 0
        self.button_clicked = False
        self.image_error = None

    def image(self, image, caption=None, width=None, link=None, **kwargs):
        if self.image_error is not None:
            raise self.image_error
        self.image_calls.append((image, width, link))

    def caption(self, body, **kwargs):
        self.caption_calls.append(body)

    def markdown(self, body, unsafe_allow_html=False, **kwargs):
        self.markdown_calls.append((body, unsafe_allow_html))

    def button(self, label, key=None, **kwargs):
        self.button_calls.append((label, key))
        return self.button_clicked

    def dialog(self, title, **kwargs):
        self.dialog_title, self.dialog_kwargs = title, kwargs

        def decorator(function):
            def opened(*args, **kw):
                self.dialog_opened += 1
                return function(*args, **kw)

            return opened

        return decorator

    def shown(self):
        """Every string handed to Streamlit, for the no-data-URL checks."""
        strings = [str(image) for image, _, _ in self.image_calls]
        strings += [str(link) for _, _, link in self.image_calls if link]
        strings += list(self.caption_calls) + [body for body, _ in self.markdown_calls]
        return strings


@pytest.fixture
def page_preview():
    """The page's preview helpers, bound to a FakeStreamlit and configurable lookups."""
    tree = ast.parse(PAGE.read_text(encoding="utf-8"))
    wanted = [
        node for node in tree.body
        if (isinstance(node, ast.FunctionDef) and node.name in HELPERS)
        or (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in LABELS for t in node.targets))
    ]
    assert {node.name for node in wanted if isinstance(node, ast.FunctionDef)} == set(HELPERS)

    fake = FakeStreamlit()
    lookups = {"card": CARD, "repo": None, "calls": []}

    def find_saved_scorecard(tournament, game_label, player):
        lookups["calls"].append((tournament, game_label, player))
        card = lookups["card"]
        return card(tournament, game_label, player) if callable(card) else card

    namespace = {
        "st": fake,
        "SavedScorecard": SavedScorecard,
        "SCORECARD_THUMBNAIL_WIDTH": SCORECARD_THUMBNAIL_WIDTH,
        "find_saved_scorecard": find_saved_scorecard,
        "scorecard_github_repo": lambda: lookups["repo"],
        "scorecard_image_url": scorecard_image_url,
        "scorecard_log": logging.getLogger("test.saved_scorecard_preview"),
    }
    exec(compile(ast.Module(body=wanted, type_ignores=[]), str(PAGE), "exec"), namespace)
    return namespace, fake, lookups


def test_render_preview_uses_saved_path_at_160px_without_github_repo(page_preview):
    namespace, fake, lookups = page_preview
    namespace["render_league_scorecard_preview"]("Cup", "Game 2", "Alice")

    assert lookups["calls"] == [("Cup", "Game 2", "Alice")]
    assert fake.image_calls == [("scorecard_images/foo.jpg", 160, None)]
    assert fake.markdown_calls == []
    assert len(fake.button_calls) == 1
    assert "View" in fake.button_calls[0][0]
    assert fake.button_calls[0][1] == "view_saved_scorecard_foo.jpg"
    assert fake.dialog_opened == 0
    assert fake.caption_calls == ["已存计分卡 Saved scorecard · 2026-01-01"]
    assert not any("data:" in text for text in fake.shown())


def test_render_preview_links_thumbnail_when_github_repo_set(page_preview):
    namespace, fake, lookups = page_preview
    lookups["repo"] = "owner/repo"
    namespace["render_league_scorecard_preview"]("Cup", "Game 2", "Alice")

    # Still the saved file itself at 160 px; the link opens the original on GitHub.
    assert fake.image_calls == [("scorecard_images/foo.jpg", 160, RAW_URL)]
    assert fake.markdown_calls == []
    assert len(fake.button_calls) == 1
    assert "Click the thumbnail to open the original" in fake.caption_calls[0]
    assert not any("data:" in text for text in fake.shown())


def test_show_saved_scorecard_dialog_uses_same_saved_path(page_preview):
    namespace, fake, _ = page_preview
    namespace["show_saved_scorecard_dialog"](CARD)

    assert "Saved scorecard" in fake.dialog_title
    assert fake.dialog_opened == 1
    assert fake.image_calls == [("scorecard_images/foo.jpg", None, None)]
    assert not any("data:" in text for text in fake.shown())


def test_view_button_opens_dialog_with_same_path(page_preview):
    namespace, fake, _ = page_preview
    fake.button_clicked = True
    namespace["render_league_scorecard_preview"]("Cup", "Game 2", "Alice")

    assert fake.image_calls == [("scorecard_images/foo.jpg", 160, None), ("scorecard_images/foo.jpg", None, None)]
    assert "Saved scorecard" in fake.dialog_title
    assert fake.dialog_opened == 1


def test_no_match_renders_nothing(page_preview):
    namespace, fake, lookups = page_preview
    lookups["card"] = None
    fake.button_clicked = True
    namespace["render_league_scorecard_preview"]("Cup", "Game 2", "Alice")

    assert fake.image_calls == []
    assert fake.caption_calls == []
    assert fake.markdown_calls == []
    assert fake.button_calls == []
    assert fake.dialog_opened == 0


def test_preview_changes_with_selection(page_preview):
    namespace, fake, lookups = page_preview
    card_a = SavedScorecard("a.jpg", "scorecard_images/a.jpg", "20260101000000")
    card_b = SavedScorecard("b.png", "scorecard_images/b.png", "20260202000000")
    lookups["card"] = lambda tournament, game_label, player: {"Alice": card_a, "Bob": card_b}.get(player)
    render = namespace["render_league_scorecard_preview"]

    render("Cup", "Game 2", "Alice")
    assert fake.image_calls[-1][0] == "scorecard_images/a.jpg"

    fake.image_calls.clear()
    fake.button_calls.clear()
    render("Cup", "Game 2", "Bob")
    assert fake.image_calls[0] == ("scorecard_images/b.png", 160, None)
    assert fake.button_calls[0][1] == "view_saved_scorecard_b.png"

    fake.image_calls.clear()
    fake.button_calls.clear()
    render("Cup", "Game 2", "Carol")  # no saved card: the thumbnail and the button go
    assert fake.image_calls == [] and fake.button_calls == []


def test_file_streamlit_cannot_display_shows_nothing_and_does_not_raise(page_preview):
    namespace, fake, _ = page_preview
    fake.image_error = ValueError("cannot identify image file")
    fake.button_clicked = True
    namespace["render_league_scorecard_preview"]("Cup", "Game 2", "Alice")

    assert fake.caption_calls == []
    assert fake.button_calls == []
    assert fake.dialog_opened == 0


def test_preview_never_reads_the_image_itself(page_preview, monkeypatch):
    namespace, fake, _ = page_preview

    def refuse(*args, **kwargs):
        raise AssertionError("the page must hand Streamlit the path, not read the file")

    monkeypatch.setattr("builtins.open", refuse)
    fake.button_clicked = True
    namespace["render_league_scorecard_preview"]("Cup", "Game 2", "Alice")
    assert [image for image, _, _ in fake.image_calls] == ["scorecard_images/foo.jpg"] * 2


def test_page_imports_the_saved_scorecard_helpers():
    source = PAGE.read_text(encoding="utf-8")
    for name in (
        "SCORECARD_THUMBNAIL_WIDTH",
        "SavedScorecard",
        "find_saved_scorecard",
        "scorecard_github_repo",
        "scorecard_image_url",
    ):
        assert f"    {name},\n" in source, name
    assert source.count("from league_scorecard import") == 1
