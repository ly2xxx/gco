import copy
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pinned_announcements import PINNED_ANNOUNCEMENTS, get_display_announcements  # noqa: E402


def _ann(ann_id: str, pinned=None, **extra) -> dict:
    """Build a minimal input record; omit the pinned key when pinned is None."""
    record = {
        "id": ann_id,
        "title": f"title-{ann_id}",
        "date": "2026-01-01",
        "author": "author",
        "body": "body",
        "tags": [],
    }
    if pinned is not None:
        record["pinned"] = pinned
    record.update(extra)
    return record


PINNED_IDS = [record["id"] for record in PINNED_ANNOUNCEMENTS]


def test_module_exposes_records_and_helper():
    """Spec behaviour 1."""
    assert isinstance(PINNED_ANNOUNCEMENTS, list)
    assert PINNED_ANNOUNCEMENTS
    assert all(isinstance(record, dict) for record in PINNED_ANNOUNCEMENTS)
    assert callable(get_display_announcements)
    for record in PINNED_ANNOUNCEMENTS:
        assert set(record) >= {"id", "title", "date", "author", "pinned", "body", "tags"}
        assert record["pinned"] is True
        assert isinstance(record["tags"], list)


def test_import_is_side_effect_free_and_streamlit_free():
    """Spec behaviour 1: no import-time side effects, I/O or exceptions."""
    code = (
        "import sys, pinned_announcements as p; "
        "assert isinstance(p.PINNED_ANNOUNCEMENTS, list) and p.PINNED_ANNOUNCEMENTS; "
        "assert all(isinstance(r, dict) for r in p.PINNED_ANNOUNCEMENTS); "
        "assert callable(p.get_display_announcements); "
        "assert 'streamlit' not in sys.modules"
    )
    _proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
        check=True,
    )
    assert _proc.stdout == ""
    assert _proc.stderr == ""


def test_pinned_records_come_before_non_pinned():
    """Spec behaviour 5."""
    result = get_display_announcements([_ann("x-1", pinned=False), _ann("x-2", pinned=True), _ann("x-3")])

    assert result[:len(PINNED_ANNOUNCEMENTS)] == PINNED_ANNOUNCEMENTS
    assert result[len(PINNED_ANNOUNCEMENTS)]["id"] == "x-2"
    assert [item["id"] for item in result] == PINNED_IDS + ["x-2", "x-1", "x-3"]


def test_module_records_then_extra_pinned_then_rest():
    """Spec behaviour 6."""
    result = get_display_announcements(
        [_ann("n-1"), _ann("p-extra", pinned=True), _ann("n-2"), _ann("p-extra-2", pinned=True)]
    )

    assert [item["id"] for item in result] == PINNED_IDS + ["p-extra", "p-extra-2", "n-1", "n-2"]


def test_module_record_is_not_duplicated_by_input():
    """Spec behaviour 6: an input record with a module record's id is not repeated."""
    result = get_display_announcements([{**PINNED_ANNOUNCEMENTS[0], "title": "changed-in-input"}])

    assert len(result) == len(PINNED_ANNOUNCEMENTS)
    assert result == PINNED_ANNOUNCEMENTS


def test_none_and_empty_return_the_module_records():
    """Spec behaviour 7."""
    assert get_display_announcements(None) == PINNED_ANNOUNCEMENTS
    assert get_display_announcements([]) == PINNED_ANNOUNCEMENTS
    assert get_display_announcements(None) is not PINNED_ANNOUNCEMENTS


def test_missing_none_or_false_pinned_goes_to_non_pinned_group():
    """Spec behaviour 8."""
    result = get_display_announcements(
        [_ann("no-key"), _ann("none-value", pinned=None), _ann("false-value", pinned=False)]
    )

    assert [item["id"] for item in result] == PINNED_IDS + ["no-key", "none-value", "false-value"]


def test_call_is_pure_and_repeatable():
    """Spec behaviour 9."""
    input_list = [_ann("n-1"), _ann("p-1", pinned=True)]
    snapshot = copy.deepcopy(input_list)
    module_snapshot = copy.deepcopy(PINNED_ANNOUNCEMENTS)

    first = get_display_announcements(input_list)
    second = get_display_announcements(input_list)

    assert first == second
    assert first is not second
    assert input_list == snapshot
    assert PINNED_ANNOUNCEMENTS == module_snapshot


def test_result_is_not_truncated():
    """Spec behaviour 10."""
    result = get_display_announcements([_ann(f"n-{i}") for i in range(5)])

    assert len(result) == len(PINNED_ANNOUNCEMENTS) + 5
    assert [item["id"] for item in result] == PINNED_IDS + [f"n-{i}" for i in range(5)]
