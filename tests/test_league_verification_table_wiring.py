"""Feature 014, phase 3: the uploaded card and the hole-by-hole check table above Save.

Source tests first (the plan's Definition of done), then the real page run as an
admin with the Ollama read replaced by a recorder: no network, nothing saved.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PAGE_PATH = REPO_ROOT / "pages" / "3_🏆_League.py"
SOURCE = PAGE_PATH.read_text(encoding="utf-8")
START = "scorecard_read_result = st.session_state.get(LEAGUE_SCORECARD_READ_RESULT_KEY)"


def _block():
    start = SOURCE.index(START)
    return SOURCE[start:SOURCE.index("st.form_submit_button", start)]


def test_read_result_is_stored_and_rendered_beside_image_before_save():
    assert "st.session_state[LEAGUE_SCORECARD_READ_RESULT_KEY] = scorecard_read_result" in SOURCE
    block = _block()
    assert block.count("st.columns(") == 1
    assert "with scorecard_image_column:" in block and "with scorecard_table_column:" in block
    assert block.index("st.image(") < block.index("st.dataframe(")
    assert "scorecard_verification_table(" in block and "VERIFICATION_TABLE_COLUMNS" in block
    assert SOURCE.index('with st.form("league_score_form")') < SOURCE.index(START), "inside the form, above Save"


def test_invalid_selection_keeps_image_and_skips_dataframe():
    block = _block()
    lines = block.splitlines()
    guard = next(line for line in lines if line.strip() == "if valid_player_selected:")
    frames = [line for line in lines if "st.dataframe(" in line]
    assert block.index("st.image(") < block.index("if valid_player_selected:") < block.index("st.dataframe(")
    indent = lambda line: len(line) - len(line.lstrip())  # noqa: E731
    assert frames and all(indent(line) > indent(guard) for line in frames)
    assert "any(" in block and 'getattr(player, "index", None) == selected_player_index' in block


def test_table_uses_stored_result_not_score_form_keys():
    block = _block()
    start = block.index("scorecard_verification_table(")
    call = block[start:block.index("\n", block.index("selected_player_hole_scores(", start))]
    assert "scorecard_read_result.pars" in call
    assert "selected_player_hole_scores(scorecard_read_result, selected_player_index)" in call
    assert "st.session_state" not in call
    for key in ("date", "venue", "net", "gross", "stableford", "eagles", "birdies", "pars", "bogeys",
                "double_bogeys_or_worse"):
        assert f'st.session_state.get("{key}")' not in block and f'st.session_state["{key}"]' not in block
    assert "LEAGUE_SCORECARD_WIDGET_KEYS" not in block and "widget_keys" not in block


# ── The page itself, run as an admin ─────────────────────────────────────────

ADMIN_TOKEN = "test-admin-token"
PLAYER = "刘北南"
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\r\xefF\xb8\x00\x00\x00\x00IEND\xaeB`\x82"
)
PARS = {h: (3 if h in (6, 12, 17) else 5 if h in (7, 15) else 4) for h in range(1, 19)}
WANG = {h: 5 for h in range(1, 19)}                       # 45 + 45 = 90
LI = {h: 6 for h in range(1, 19) if h != 9}               # hole 9 unread


def _card():
    from league_scorecard import LeagueScorecardPlayersResult, ScorecardPlayerEntry

    return LeagueScorecardPlayersResult(
        [
            ScorecardPlayerEntry(0, "王", {"gross": 93, "net": -1}, dict(WANG)),
            ScorecardPlayerEntry(1, "李杨", {"gross": 100, "net": 13}, dict(LI)),
        ],
        pars=dict(PARS),
    )


@pytest.fixture
def admin_page(monkeypatch):
    AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
    from streamlit.runtime.pages_manager import PagesManager

    import data
    import league_scorecard

    monkeypatch.setattr(PagesManager, "uses_pages_directory", None)
    calls = {"read": 0, "saved": [], "result": _card()}

    def fake_read(image_bytes, mime_type, **kwargs):
        calls["read"] += 1
        return calls["result"]

    monkeypatch.setattr(league_scorecard, "read_league_scorecard_players", fake_read)
    monkeypatch.setattr(league_scorecard, "find_saved_scorecard", lambda *a, **k: None)
    monkeypatch.setattr(data, "save_scores", lambda df: calls["saved"].append(df.copy()))
    monkeypatch.setattr(data, "github_upload_image", lambda content, name: True)

    at = AppTest.from_file(str(PAGE_PATH), default_timeout=60)
    at.secrets["ADMIN_TOKEN"] = ADMIN_TOKEN
    at.query_params["admin"] = ADMIN_TOKEN
    at.run()
    if not hasattr(at, "file_uploader"):
        pytest.skip("this Streamlit's AppTest can't drive st.file_uploader")
    next(w for w in at.selectbox if w.label.startswith("球员 Player")).select(PLAYER)
    at.run()
    return at, calls


def _upload(at):
    next(w for w in at.file_uploader if w.label.startswith("Scorecard image")).set_value(("card.png", PNG, "image/png"))
    return at.run()


def _pick(at, index):
    next(w for w in at.selectbox if w.label == "Player").select_index(index)
    return at.run()


def _check_tables(at):
    """The check tables on the page: frames whose index is exactly Par, Score."""
    return [d.value for d in at.dataframe if list(d.value.index) == ["Par", "Score"]]


def _images(at):
    return list(at.get("imgs")) + list(at.get("image"))


def test_no_table_until_a_card_player_is_picked_but_the_image_shows(admin_page):
    at, calls = admin_page
    assert _check_tables(at) == [] and _images(at) == []

    at = _upload(at)
    assert calls["read"] == 1
    assert len(_images(at)) == 1, "the uploaded card is shown"
    assert _check_tables(at) == [], "nobody picked yet"
    assert at.exception == []


def test_picked_players_pars_and_scores_are_shown_front_and_back_nine(admin_page):
    at, calls = admin_page
    at = _pick(_upload(at), 0)

    front, back = _check_tables(at)
    assert list(front.columns) == [str(h) for h in range(1, 10)] + ["Out"]
    assert list(back.columns) == [str(h) for h in range(10, 19)] + ["In", "Total"]
    assert list(front.loc["Par"]) == [str(PARS[h]) for h in range(1, 10)] + [str(sum(PARS[h] for h in range(1, 10)))]
    assert list(front.loc["Score"]) == ["5"] * 9 + ["45"]
    assert list(back.loc["Score"]) == ["5"] * 9 + ["45", "90"]
    assert list(back.loc["Par"])[-1] == str(sum(PARS.values()))
    assert any("Hole-by-hole check · 王" in c.value for c in at.caption)
    # 90 from the holes, but 93 was read as the gross: the admin is told.
    assert any("add up to 90" in w.value and "93" in w.value for w in at.warning)
    assert len(_images(at)) == 1 and calls["read"] == 1
    assert at.exception == []


def test_unread_hole_shows_a_dash_and_no_partial_totals(admin_page):
    at, _ = admin_page
    at = _pick(_upload(at), 1)

    front, back = _check_tables(at)
    assert list(front.loc["Score"]) == ["6"] * 8 + ["-", "-"]
    assert list(back.loc["Score"]) == ["6"] * 9 + ["54", "-"]
    assert any("could not be read" in c.value for c in at.caption)
    assert not any("add up to" in w.value for w in at.warning)
    assert at.exception == []


def test_switching_the_card_player_switches_the_table(admin_page):
    at, _ = admin_page
    at = _pick(_upload(at), 0)
    assert list(_check_tables(at)[0].loc["Score"])[0] == "5"
    at = _pick(at, 1)
    assert list(_check_tables(at)[0].loc["Score"])[0] == "6"
    assert any("Hole-by-hole check · 李杨" in c.value for c in at.caption)


def test_table_keeps_the_read_values_when_the_form_is_edited_and_saved(admin_page):
    at, calls = admin_page
    at = _pick(_upload(at), 0)
    next(w for w in at.number_input if w.label.startswith("总杆")).set_value(95)
    next(b for b in at.button if b.label.startswith("✅ 保存成绩 Save")).click()
    at.run()

    assert len(calls["saved"]) == 1
    saved = calls["saved"][0]
    assert saved[saved["Player"] == PLAYER].iloc[-1]["Gross_Score"] == 95, "Save stores the form, not the table"
    assert calls["read"] == 1


def test_card_without_hole_data_still_fills_the_form(admin_page):
    from league_scorecard import LeagueScorecardPlayersResult, ScorecardPlayerEntry

    at, calls = admin_page
    calls["result"] = LeagueScorecardPlayersResult([ScorecardPlayerEntry(0, "Neo", {"gross": 88})])
    at = _pick(_upload(at), 0)

    assert next(w for w in at.number_input if w.label.startswith("总杆")).value == 88
    front, back = _check_tables(at)
    assert set(front.loc["Score"]) == {"-"} and set(back.loc["Par"]) == {"-"}
    assert at.exception == []
