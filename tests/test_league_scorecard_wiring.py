"""Phase 4: the League admin score form's scorecard picker, prefill and notice.

The first tests read the page source (the plan's Definition of done). The AppTest
tests below them run the page as an admin with the Ollama read, save_scores and
github_upload_image replaced by recorders: no network, no files written.
"""
import pathlib
import re
import sys
from datetime import date

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from league_scorecard import LEAGUE_SCORECARD_FIELD_KEYS  # noqa: E402

PAGE_PATH = REPO_ROOT / "pages" / "3_🏆_League.py"
LEAGUE_PAGE = PAGE_PATH.read_text(encoding="utf-8")


def test_picker_is_rendered_with_its_own_key():
    assert "st.file_uploader(" in LEAGUE_PAGE
    assert "LEAGUE_SCORECARD_UPLOAD_KEY" in LEAGUE_PAGE
    assert "type=None" in LEAGUE_PAGE
    assert LEAGUE_PAGE.index("st.file_uploader(") < LEAGUE_PAGE.index("_base_net")


def test_all_ten_widget_keys_are_wired():
    for field in LEAGUE_SCORECARD_FIELD_KEYS:
        assert f'"{field}": "league_sc_' in LEAGUE_PAGE, field
        assert f'_scorecard_widget_default("{field}"' in LEAGUE_PAGE, field


def test_read_and_filter_helpers_are_used():
    for call in (
        "read_league_scorecard_players(",
        "scorecard_field_updates(",
        "scorecard_upload_fingerprint(",
        "venue_names_from_records(",
        "st.rerun()",
    ):
        assert call in LEAGUE_PAGE, call


def test_unavailable_notice_is_informational_only():
    assert "AUTOFILL_UNAVAILABLE_NOTICE" in LEAGUE_PAGE
    assert "st.info(" in LEAGUE_PAGE
    assert "st.error(AUTOFILL_UNAVAILABLE_NOTICE" not in LEAGUE_PAGE
    assert "st.stop(" not in LEAGUE_PAGE


def test_save_path_still_uploads_exactly_once():
    assert LEAGUE_PAGE.count("github_upload_image(") == 1
    assert LEAGUE_PAGE.index("github_upload_image(") > LEAGUE_PAGE.index("st.file_uploader(")


def test_no_other_page_leaks_the_notice():
    for path in (REPO_ROOT / "pages").glob("*.py"):
        if path.name == PAGE_PATH.name:
            continue
        text = path.read_text(encoding="utf-8")
        assert "AUTOFILL_UNAVAILABLE_NOTICE" not in text, path.name
        assert "read_league_scorecard" not in text, path.name


def test_autofill_never_persists_without_save():
    assert not any(
        "github_upload_image" in line and "read_league_scorecard" in line for line in LEAGUE_PAGE.splitlines()
    )


def test_existing_field_defaults_unchanged():
    base_lines = [line for line in LEAGUE_PAGE.splitlines() if "_base_" in line]
    for literal in ("72", "36", "0"):
        assert any(re.search(rf"\b{literal}\b", line) for line in base_lines), literal


def test_snapshot_reset_guard_present():
    assert "LEAGUE_SCORECARD_SNAPSHOT_KEY" in LEAGUE_PAGE
    assert (
        "st.session_state.pop(_key, None)" in LEAGUE_PAGE
        or "st.session_state[_key] = _base_values[_field]" in LEAGUE_PAGE
    )


def test_prefill_is_applied_from_session_state():
    assert (
        "_prefill = st.session_state.pop(LEAGUE_SCORECARD_PREFILL_KEY" in LEAGUE_PAGE
        or re.search(
            r"apply_selected_player_scorecard_updates\(\s*players_result,\s*selected_index,\s*widget_keys,"
            r"\s*st\.session_state,?\s*\)",
            LEAGUE_PAGE,
        )
    )


# ── The page itself, run as an admin ─────────────────────────────────────────

ADMIN_TOKEN = "test-admin-token"
PLAYER = "刘北南"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"scorecard" * 4


@pytest.fixture
def admin_page(monkeypatch):
    """The League page as an admin, with the Ollama read, saving and image upload recorded."""
    AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
    from streamlit.runtime.pages_manager import PagesManager

    import data
    import league_scorecard

    # See tests/test_league_deep_dive_wiring.py: keep the front-page AppTests' pages/ flag intact.
    monkeypatch.setattr(PagesManager, "uses_pages_directory", None)
    calls = {"read": [], "saved": [], "uploaded": []}

    def fake_read(image_bytes, mime_type, **kwargs):
        calls["read"].append((image_bytes, mime_type))
        return calls["result"]

    monkeypatch.setattr(league_scorecard, "read_league_scorecard_players", fake_read)
    monkeypatch.setattr(data, "save_scores", lambda df: calls["saved"].append(df.copy()))
    monkeypatch.setattr(
        data, "github_upload_image", lambda content, name: calls["uploaded"].append((content, name)) or True
    )

    at = AppTest.from_file(str(PAGE_PATH), default_timeout=60)
    at.secrets["ADMIN_TOKEN"] = ADMIN_TOKEN
    at.query_params["admin"] = ADMIN_TOKEN
    at.run()
    if not hasattr(at, "file_uploader"):
        pytest.skip("this Streamlit's AppTest can't drive st.file_uploader")
    return at, calls


def _widget(at, kind, label_start):
    return next(w for w in getattr(at, kind) if w.label.startswith(label_start))


def _select_round(at, player, game):
    _widget(at, "selectbox", "球员 Player").select(player)
    _widget(at, "selectbox", "轮次 Game").select(game)
    at.run()


def _form_values(at):
    return {
        "date": _widget(at, "date_input", "日期 Date").value,
        "venue": _widget(at, "text_input", "场地 Venue").value,
        "net": _widget(at, "number_input", "净杆").value,
        "gross": _widget(at, "number_input", "总杆").value,
        "stableford": _widget(at, "number_input", "稳定福分").value,
        "eagles": _widget(at, "number_input", "老鹰").value,
        "birdies": _widget(at, "number_input", "小鸟").value,
        "pars": _widget(at, "number_input", "标准").value,
        "bogeys": _widget(at, "number_input", "柏忌").value,
        "double_bogeys_or_worse": _widget(at, "number_input", "双柏忌").value,
    }


def _card_player_picker(at):
    """The selector listing the players read off the card (absent until a card is read)."""
    return next((w for w in at.selectbox if w.label == "Player"), None)


def _two_player_card():
    """The card in ly2xxx/gco#50: 王 has the date and venue, 李杨 only their own scores."""
    from league_scorecard import LeagueScorecardPlayersResult, ScorecardPlayerEntry

    return LeagueScorecardPlayersResult([
        ScorecardPlayerEntry(0, "王", {
            "date": "2026-06-21", "venue": "Cowglen", "net": -1, "gross": 93, "pars": 3, "bogeys": 10,
            "double_bogeys_or_worse": 5,
        }),
        ScorecardPlayerEntry(1, "李杨", {"net": 13, "gross": 100, "pars": 1, "bogeys": 7}),
    ])


def _sent_to_browser(widget):
    """The value this run tells the browser to show, or None when the browser keeps its own.

    A keyed widget's browser copy only changes when the run sets ``set_value``; AppTest's
    ``.value`` reads session state and can't tell the two apart.
    """
    return widget.proto.value if widget.proto.set_value else None


def _assert_whole_number_inputs(at):
    """The eight score inputs stay integer inputs (the browser shows 12, not 12.00, and sends ints)."""
    from streamlit.proto.NumberInput_pb2 import NumberInput as NumberInputProto

    for label in ("净杆", "总杆", "稳定福分", "老鹰", "小鸟", "标准", "柏忌", "双柏忌"):
        assert _widget(at, "number_input", label).proto.data_type == NumberInputProto.INT, label


def _unplayed_game(at, player):
    """A game of the selected tournament with no real score yet, so the form shows 72/36/0."""
    import data

    scores = data.load_scores()
    for game in _widget(at, "selectbox", "轮次 Game").options:
        rows = scores[(scores["Player"] == player) & (scores["Game"] == game)]
        if rows.empty or not (rows["Gross_Score"].fillna(0) > 0).any():
            return game
    pytest.skip(f"every game of {player} already has a score")


def test_no_upload_keeps_todays_defaults_and_says_autofill_unavailable(admin_page):
    at, calls = admin_page
    game = _unplayed_game(at, PLAYER)
    _select_round(at, PLAYER, game)
    values = _form_values(at)
    assert (values["net"], values["gross"], values["stableford"]) == (0, 72, 36)
    assert all(values[f] == 0 for f in ("eagles", "birdies", "pars", "bogeys", "double_bogeys_or_worse"))
    assert all(type(values[f]) is int for f in values if f not in ("date", "venue"))
    _assert_whole_number_inputs(at)
    assert any("Auto-fill from the scorecard image was unavailable" in info.value for info in at.info)
    assert calls["read"] == []
    assert at.exception == []


def test_upload_lists_every_card_player_and_fills_only_the_picked_one(admin_page):
    at, calls = admin_page
    game = _unplayed_game(at, PLAYER)
    _select_round(at, PLAYER, game)
    before = _form_values(at)
    calls["result"] = _two_player_card()

    _widget(at, "file_uploader", "Scorecard image").set_value(("card.png", PNG_BYTES, "image/png"))
    at.run()

    assert calls["read"] == [(PNG_BYTES, "image/png")]
    picker = _card_player_picker(at)
    assert picker is not None and picker.options == ["王", "李杨"]
    assert picker.value is None, "nobody is picked until the admin chooses"
    assert _form_values(at) == before, "nothing is filled before a pick"

    picker.select_index(1)
    at.run()

    values = _form_values(at)
    assert (values["net"], values["gross"], values["pars"], values["bogeys"]) == (13, 100, 1, 7)
    # The card's date and venue, read with 王, apply to 李杨 too; 王's own scores don't.
    assert values["date"] == date(2026, 6, 21)
    assert values["venue"] == "Cowglen"
    assert (values["stableford"], values["eagles"], values["birdies"], values["double_bogeys_or_worse"]) == (
        36, 0, 0, 0,
    )
    assert all(type(values[f]) is int for f in values if f not in ("date", "venue"))
    _assert_whole_number_inputs(at)
    assert not any("unavailable" in info.value for info in at.info)
    assert at.exception == []


def test_switching_the_card_player_replaces_every_value(admin_page):
    at, calls = admin_page
    _select_round(at, PLAYER, _unplayed_game(at, PLAYER))
    calls["result"] = _two_player_card()
    _widget(at, "file_uploader", "Scorecard image").set_value(("card.png", PNG_BYTES, "image/png"))
    at.run()

    _card_player_picker(at).select_index(0)
    at.run()
    assert (_form_values(at)["gross"], _form_values(at)["double_bogeys_or_worse"]) == (93, 5)

    _card_player_picker(at).select_index(1)
    at.run()
    values = _form_values(at)
    assert (values["net"], values["gross"], values["bogeys"]) == (13, 100, 7)
    assert values["double_bogeys_or_worse"] == 0, "王's double bogeys must not stay in 李杨's form"
    assert _sent_to_browser(_widget(at, "number_input", "双柏忌")) == 0
    assert _sent_to_browser(_widget(at, "number_input", "总杆")) == 100
    assert len(calls["read"]) == 1
    assert at.exception == []


def test_save_keeps_the_admins_corrections_and_uploads_the_card_once(admin_page):
    at, calls = admin_page
    game = _unplayed_game(at, PLAYER)
    _select_round(at, PLAYER, game)
    calls["result"] = _two_player_card()
    _widget(at, "file_uploader", "Scorecard image").set_value(("card.png", PNG_BYTES, "image/png"))
    at.run()
    _card_player_picker(at).select_index(1)
    at.run()

    # The admin corrects one value; Save stores what is on screen, not the card's value.
    _widget(at, "number_input", "柏忌").set_value(6)
    _widget(at, "button", "✅ 保存成绩 Save").click()
    at.run()

    assert len(calls["read"]) == 1, "the same upload must not be read again"
    assert len(calls["saved"]) == 1
    saved = calls["saved"][0]
    row = saved[(saved["Player"] == PLAYER) & (saved["Game"] == game)].iloc[-1]
    assert (row["Date"], row["Venue"]) == ("2026-06-21", "Cowglen")
    assert (row["Net_Score"], row["Gross_Score"], row["Stableford"]) == (13, 100, 36)
    assert (row["Pars"], row["Bogeys"], row["Birdies"]) == (1, 6, 0)
    assert len(calls["uploaded"]) == 1
    content, name = calls["uploaded"][0]
    assert content == PNG_BYTES
    assert name.endswith(".png")
    assert at.exception == []


def test_manual_entry_without_a_card_is_saved_as_typed(admin_page):
    at, calls = admin_page
    game = _unplayed_game(at, PLAYER)
    _select_round(at, PLAYER, game)
    _widget(at, "number_input", "净杆").set_value(5)
    _widget(at, "number_input", "总杆").set_value(80)
    _widget(at, "button", "✅ 保存成绩 Save").click()
    at.run()

    assert calls["read"] == []
    assert len(calls["saved"]) == 1
    saved = calls["saved"][0]
    row = saved[(saved["Player"] == PLAYER) & (saved["Game"] == game)].iloc[-1]
    assert (row["Net_Score"], row["Gross_Score"]) == (5, 80)
    assert calls["uploaded"] == []
    assert at.exception == []


def test_duplicate_printed_labels_stay_separately_selectable(admin_page):
    from league_scorecard import LeagueScorecardPlayersResult, ScorecardPlayerEntry

    at, calls = admin_page
    _select_round(at, PLAYER, _unplayed_game(at, PLAYER))
    calls["result"] = LeagueScorecardPlayersResult([
        ScorecardPlayerEntry(0, "Neo", {"gross": 81}),
        ScorecardPlayerEntry(1, "Neo", {"gross": 95}),
    ])
    _widget(at, "file_uploader", "Scorecard image").set_value(("card.png", PNG_BYTES, "image/png"))
    at.run()

    picker = _card_player_picker(at)
    assert picker.options == ["Neo (1)", "Neo (2)"]
    picker.select_index(1)
    at.run()
    assert _form_values(at)["gross"] == 95
    assert at.exception == []


def test_failed_read_leaves_the_form_as_it_was(admin_page):
    from league_scorecard import LeagueScorecardPlayersResult

    at, calls = admin_page
    game = _unplayed_game(at, PLAYER)
    _select_round(at, PLAYER, game)
    before = _form_values(at)
    calls["result"] = LeagueScorecardPlayersResult([], "timeout")

    _widget(at, "file_uploader", "Scorecard image").set_value(("card.png", PNG_BYTES, "image/png"))
    at.run()

    assert len(calls["read"]) == 1
    assert _form_values(at) == before
    assert _card_player_picker(at) is None
    assert any("Auto-fill from the scorecard image was unavailable" in info.value for info in at.info)
    assert at.exception == []


def test_switching_round_shows_that_rounds_values_not_the_prefill(admin_page):
    at, calls = admin_page
    game = _unplayed_game(at, PLAYER)
    _select_round(at, PLAYER, game)
    calls["result"] = _two_player_card()
    _widget(at, "file_uploader", "Scorecard image").set_value(("card.png", PNG_BYTES, "image/png"))
    at.run()
    _card_player_picker(at).select_index(1)
    at.run()
    assert (_form_values(at)["net"], _form_values(at)["gross"]) == (13, 100)

    other = next(p for p in _widget(at, "selectbox", "球员 Player").options if p != PLAYER)
    _widget(at, "selectbox", "球员 Player").select(other)
    at.run()

    import data

    scores = data.load_scores()
    rows = scores[(scores["Player"] == other) & (scores["Game"] == game)]
    has_score = not rows.empty and float(rows.iloc[0]["Gross_Score"]) > 0
    expected_gross = int(rows.iloc[0]["Gross_Score"]) if has_score else 72
    assert _form_values(at)["gross"] == expected_gross
    assert _sent_to_browser(_widget(at, "number_input", "总杆")) == expected_gross
    assert _card_player_picker(at).value is None, "the pick belongs to the round it was made for"
    assert len(calls["read"]) == 1
    assert at.exception == []


def test_switching_between_unplayed_rounds_drops_the_prefill(admin_page):
    """Two unplayed rounds share the 72/36/0 defaults; a read for one must not follow to the other."""
    import data

    at, calls = admin_page
    scores = data.load_scores()

    def unplayed(player, game):
        rows = scores[(scores["Player"] == player) & (scores["Game"] == game)]
        return rows.empty or not (rows["Gross_Score"].fillna(0) > 0).any()

    players = list(_widget(at, "selectbox", "球员 Player").options)
    pair = next(
        (
            (game, [p for p in players if unplayed(p, game)][:2])
            for game in _widget(at, "selectbox", "轮次 Game").options
            if sum(unplayed(p, game) for p in players) >= 2
        ),
        None,
    )
    if pair is None:
        pytest.skip("no game that two players have both still to play")
    game, (first, other) = pair
    _select_round(at, first, game)
    calls["result"] = _two_player_card()
    _widget(at, "file_uploader", "Scorecard image").set_value(("card.png", PNG_BYTES, "image/png"))
    at.run()
    _card_player_picker(at).select_index(1)
    at.run()
    assert (_form_values(at)["net"], _form_values(at)["gross"], _form_values(at)["bogeys"]) == (13, 100, 7)

    _widget(at, "selectbox", "球员 Player").select(other)
    at.run()

    values = _form_values(at)
    assert (values["net"], values["gross"], values["stableford"], values["bogeys"]) == (0, 72, 36, 0)
    sent = [_sent_to_browser(_widget(at, "number_input", label)) for label in ("净杆", "总杆", "稳定福分", "柏忌")]
    assert sent == [0, 72, 36, 0], "the browser must be told the new round's values"
    assert at.exception == []


def test_save_uploads_a_webp_scorecard_the_reader_accepted(admin_page):
    from league_scorecard import LeagueScorecardPlayersResult, ScorecardPlayerEntry

    at, calls = admin_page
    _select_round(at, PLAYER, _unplayed_game(at, PLAYER))
    calls["result"] = LeagueScorecardPlayersResult([ScorecardPlayerEntry(0, "Neo", {"gross": 90})])
    webp = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"x" * 8
    _widget(at, "file_uploader", "Scorecard image").set_value(("card.webp", webp, "image/webp"))
    at.run()
    _widget(at, "button", "✅ 保存成绩 Save").click()
    at.run()

    assert len(calls["saved"]) == 1
    assert len(calls["uploaded"]) == 1
    content, name = calls["uploaded"][0]
    assert content == webp
    assert name.endswith(".webp")
    assert at.exception == []
