import datetime
import sys
from pathlib import Path

# `uv run pytest tests/...` puts only tests/ on sys.path; ai_summary.py lives at the repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import ai_summary as m  # noqa: E402

UNSAFE_FILENAME_CHARS = ("/", "\\", ":", "*", "?", '"', "<", ">", "|")


def test_transcript_contains_headings_and_summary():
    """Spec behaviours 3, 4 (assembly)."""
    text = m.build_transcript_text("Neo", "SUMMARY_BODY_MARKER", None)

    assert m.TRANSCRIPT_SUMMARY_HEADING in text
    assert "SUMMARY_BODY_MARKER" in text
    assert m.TRANSCRIPT_QA_HEADING in text
    assert text.endswith("\n")
    assert "<" not in text


def test_question_before_answer_with_bilingual_prefixes():
    """Spec behaviour 5."""
    text = m.build_transcript_text("Neo", "SUMMARY", [{"question": "Q1", "answer": "A1"}])

    assert "问 / Q: Q1" in text
    assert "答 / A: A1" in text
    assert text.index("问 / Q: Q1") < text.index("答 / A: A1")


def test_turns_keep_stored_order_and_appear_once():
    """Spec behaviour 6."""
    history = [{"question": f"Q{i}", "answer": f"A{i}"} for i in (1, 2, 3)]

    text = m.build_transcript_text("Neo", "SUMMARY", history)

    positions = [text.index(f"问 / Q: Q{i}") for i in (1, 2, 3)]
    assert positions == sorted(positions)
    for i in (1, 2, 3):
        assert text.count(f"问 / Q: Q{i}") == 1
        assert text.count(f"答 / A: A{i}") == 1


def test_incomplete_turns_contribute_nothing():
    """Spec behaviour 7."""
    history = [
        {"question": "   ", "answer": "A-ignored"},
        {"question": "Q-ignored", "answer": ""},
        {"answer": "A-ignored-2"},
        {"question": "Q-ignored-2"},
        {"question": "", "answer": "   "},
    ]

    text = m.build_transcript_text("Neo", "SUMMARY", history)

    assert "问 / Q:" not in text
    assert "答 / A:" not in text
    assert "A-ignored" not in text
    assert "Q-ignored" not in text


def test_identical_turn_pairs_collapse_but_same_question_with_new_answer_does_not():
    """Spec behaviour 8."""
    history = [
        {"question": "same?", "answer": "yes"},
        {"question": "same?", "answer": "yes"},
        {"question": "same?", "answer": "no"},
    ]

    text = m.build_transcript_text("Neo", "SUMMARY", history)

    assert text.count("问 / Q: same?") == 2
    assert text.count("答 / A: yes") == 1
    assert text.count("答 / A: no") == 1


def test_bad_history_returns_summary_only():
    """Spec behaviour 9."""
    for history in (None, "nope", 42, {"question": "Q", "answer": "A"}, [1, "x", None, object()]):
        text = m.build_transcript_text("Neo", "SUMMARY_BODY_MARKER", history)

        assert "问 / Q:" not in text
        assert m.TRANSCRIPT_SUMMARY_HEADING in text
        assert "SUMMARY_BODY_MARKER" in text


def test_html_and_fences_are_stripped():
    """Spec behaviour 10."""
    text = m.build_transcript_text(
        "Neo", "<b>bold</b><br/>next line", [{"question": "<i>q</i>", "answer": "```code```"}]
    )

    assert "<" not in text
    assert ">" not in text
    assert "```" not in text
    assert "bold" in text
    assert "next line" in text
    assert "问 / Q: q" in text
    assert "答 / A: code" in text


def test_filename_is_stable_and_safe():
    """Spec behaviours 11, 12."""
    stamp = datetime.datetime(2026, 1, 2, 3, 4, 5)

    name = m.build_transcript_filename("Neo / 赵鲲", stamp)

    assert name == "gco_league_ai_summary_Neo_赵鲲_20260102_030405.txt"
    assert name.startswith(m.TRANSCRIPT_FILENAME_PREFIX)
    assert name.endswith(m.TRANSCRIPT_FILE_EXTENSION)
    assert "20260102_030405" in name
    assert m.build_transcript_filename("Neo / 赵鲲", stamp) == name
    assert not any(char in name for char in UNSAFE_FILENAME_CHARS)


def test_filename_always_has_a_stem():
    """Spec behaviour 13."""
    stamp = datetime.datetime(2026, 1, 2, 3, 4, 5)
    for player_name in ("", "   ", "///", "..."):
        name = m.build_transcript_filename(player_name, stamp)

        assert name.endswith(".txt")
        assert name.startswith(m.TRANSCRIPT_FILENAME_PREFIX + "_")
        assert name[:-4].strip("_")
