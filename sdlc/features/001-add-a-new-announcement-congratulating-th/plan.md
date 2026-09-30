<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@9779b62 -->
## Approach
Add one static, module-level announcement dict plus a pure accessor to `pages/1_📢_Announcements.py`, prepend it as the first element of the page's existing announcement collection (rendered by the existing loop, unchanged), and prove it with four offline pytest cases in `test_streamlit_app.py`: the copy contract (names, titles, 2026, 祝贺, no 张维), newest-entry ordering, an unchanged-pre-existing-entries check against a checked-in JSON baseline, and a `streamlit.testing.v1.AppTest` render check.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| The Announcements page displays an announcement announcing the 2026 individual season winners. | 1, 2, 10, 11, 12 | Phase 1, Phase 2, Phase 3 |
| The announcement names 张纬 as the 个人联赛 winner and 王文龙 as the 个人杯赛 winner. | 2, 3, 4, 5, 6 | Phase 1 |
| The wording is congratulatory and clearly attributes both honours to the 2026 season. | 7, 8 | Phase 1 |
| All announcements that already existed on the page remain visible and unchanged. | 10, 11 | Phase 2 |
| The existing tests still pass. | 13 | Phase 3 |

## Phase 1: Add the 2026 winners announcement data and accessor
<!-- phase: 1 -->
<!-- targets: pages/1_📢_Announcements.py, test_streamlit_app.py -->
<!-- frozen: data.py, streamlit_app.py, theme.py, auth.py, features/**, pages/2_📅_Events.py, pages/3_🏆_League.py, pages/4_🥊_Cup.py, pages/5_⛳_Outing.py, pages/6_💾_API_Data.py, pyproject.toml, requirements.txt, uv.lock -->

**Goal:** `pages/1_📢_Announcements.py` exposes a non-empty congratulatory 2026 winners announcement with the exact required copy, and the page still imports.

**Changes:**
- Read (do not modify yet, do not run shell probes) `pages/1_📢_Announcements.py`. Note the name of its module-level announcement collection and how it is rendered; you will need both in Phase 2. Do not rename any existing symbol.
- `pages/1_📢_Announcements.py`: immediately after the last top-level `import` statement and before the first pre-existing constant/function/render statement, add exactly:

```python
SEASON_2026_WINNERS_ANNOUNCEMENT: dict[str, str] = {
    "title": "🎉 祝贺2026赛季个人赛冠军揭晓",
    "body": (
        "2026赛季个人赛已圆满结束，特此祝贺！\n\n"
        "- **个人联赛冠军：张纬** — 恭喜张纬在2026赛季个人联赛中一路领先，最终夺冠！\n"
        "- **个人杯赛冠军：王文龙** — 恭喜王文龙在2026赛季个人杯赛中过关斩将，最终捧杯！\n\n"
        "祝贺两位冠军，也感谢所有球员在2026赛季的精彩表现！\n"
    ),
}


def get_season_2026_winners_announcement() -> dict[str, str]:
    """Return the 2026 individual season-winners announcement.

    Returns a dict with exactly the keys "title" and "body", both non-empty str.
    Pure: performs no Streamlit calls and no file, network, secret or file-system access.
    """
    return dict(SEASON_2026_WINNERS_ANNOUNCEMENT)
```

  Change nothing else in this file: no edits to existing entries, the existing render loop, or any existing symbol name.
- `test_streamlit_app.py`: add `import importlib.util`, `import re` and `from pathlib import Path` to the existing import block (leave the existing `import sys`, `import os`, `import pytest`, `import pandas as pd` and the `sys.path.append(...)` line untouched). Then append at the end of the file (after the existing `if __name__ == "__main__":` block, which stays exactly as-is):

```python
REPO_ROOT = Path(__file__).resolve().parent
ANNOUNCEMENTS_PAGE_PATH = REPO_ROOT / "pages" / "1_📢_Announcements.py"


@pytest.fixture(scope="module")
def announcements_page():
    """Import pages/1_📢_Announcements.py as a module without starting Streamlit."""
    spec = importlib.util.spec_from_file_location("gco_announcements_page", ANNOUNCEMENTS_PAGE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_2026_season_winners_announcement_names_both_winners(announcements_page) -> None:
    """Spec behaviours 1-9: accessor contract and the exact winner copy."""
    announcement = announcements_page.get_season_2026_winners_announcement()

    # Behaviour 1: exactly two keys, both non-empty strings.
    assert set(announcement) == {"title", "body"}
    assert isinstance(announcement["title"], str) and announcement["title"].strip() != ""
    assert isinstance(announcement["body"], str) and announcement["body"].strip() != ""

    # The constant is the single source of truth; the accessor hands back a copy.
    assert announcement == announcements_page.SEASON_2026_WINNERS_ANNOUNCEMENT
    announcement["title"] = "mutated"
    assert announcements_page.SEASON_2026_WINNERS_ANNOUNCEMENT["title"] == "🎉 祝贺2026赛季个人赛冠军揭晓"
    announcement = announcements_page.get_season_2026_winners_announcement()

    text = announcement["title"] + "\n" + announcement["body"]

    # Behaviours 2-5, 7, 8.
    for required in ("张纬", "个人联赛", "王文龙", "个人杯赛", "2026", "祝贺"):
        assert required in text, f"missing {required!r} in {text!r}"

    # Behaviour 9.
    assert "张维" not in text

    # Behaviour 6: every clause naming a winner also names that winner's title.
    segments = [s for s in re.split(r"[\n。！？；!?;]+", text) if s.strip()]
    zhang_clauses = [s for s in segments if "张纬" in s]
    wang_clauses = [s for s in segments if "王文龙" in s]
    assert zhang_clauses, "no clause names 张纬"
    assert wang_clauses, "no clause names 王文龙"
    assert all("个人联赛" in s for s in zhang_clauses)
    assert all("个人杯赛" in s for s in wang_clauses)
```

**Definition of done:**
- [ ] `test_streamlit_app.py::test_2026_season_winners_announcement_names_both_winners`: proves spec behaviours 1–9 (two non-empty string keys, the accessor returns a copy of the constant, `张纬`+`个人联赛` and `王文龙`+`个人杯赛` appear in the same clause, `2026` and `祝贺` present, `张维` absent). Pure in-process pytest, no fixture teardown needed beyond the module-scoped import fixture.
- [ ] `pages/1_📢_Announcements.py` still imports cleanly under that fixture (existing announcements and render code untouched).
- [ ] No new dependency is added.

**Verify:**
```bash
uv run pytest "test_streamlit_app.py::test_2026_season_winners_announcement_names_both_winners" -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Prepend the announcement and prove existing entries are unchanged
<!-- phase: 2 -->
<!-- targets: pages/1_📢_Announcements.py, test_streamlit_app.py, tests/fixtures/announcements_before_2026_winners.json -->
<!-- frozen: data.py, streamlit_app.py, theme.py, auth.py, features/**, pages/2_📅_Events.py, pages/3_🏆_League.py, pages/4_🥊_Cup.py, pages/5_⛳_Outing.py, pages/6_💾_API_Data.py, pyproject.toml, requirements.txt, uv.lock -->

**Goal:** The new announcement is the first element of the page's announcement collection, every pre-existing entry is byte-for-byte unchanged, and the collection is exactly one entry longer.

**Changes:**
- Read `pages/1_📢_Announcements.py` and resolve the placeholder `<COLLECTION_NAME>` below to the real module-level announcement collection name (the list of `{"title": ..., "body": ...}` dicts that the page renders). Never rename or shadow an existing symbol.
- `pages/1_📢_Announcements.py`: prepend `SEASON_2026_WINNERS_ANNOUNCEMENT` as the new index-0 element of `<COLLECTION_NAME>`.
  - If `<COLLECTION_NAME>` is assigned a list literal, insert the bare name `SEASON_2026_WINNERS_ANNOUNCEMENT` as the first element of that literal.
  - If it is assigned an expression (for example a loader call), change the assignment to `COLLECTION_NAME = [SEASON_2026_WINNERS_ANNOUNCEMENT, *<EXISTING EXPRESSION>]` — never mutate the source list in place.
  - Keep every pre-existing entry's exact `title` and `body` text and its relative order. Add no new keys (no `date`, no `id`) to any entry.
  - Change nothing else: the existing render path is reused verbatim and is not edited.
- `tests/fixtures/announcements_before_2026_winners.json` (new file): a JSON array containing one object per pre-existing announcement, in the same order they appear in `<COLLECTION_NAME>` before the prepend, each object with exactly the keys `"title"` and `"body"` and the exact original string values (emoji, Chinese punctuation, `\n` escapes and trailing spaces preserved). Write it UTF-8, `ensure_ascii=False`, two-space indent, trailing newline. Transcribe it by reading the file — never by running a shell command.
- `test_streamlit_app.py`: add `import json` to the existing import block, and append after the Phase 1 test:

```python
ANNOUNCEMENTS_BASELINE_PATH = REPO_ROOT / "tests" / "fixtures" / "announcements_before_2026_winners.json"


def _page_announcements(page):
    """The page's module-level announcement collection, in render order."""
    return page.<COLLECTION_NAME>


def test_2026_season_winners_announcement_is_newest_entry(announcements_page) -> None:
    """Spec behaviour 10: the 2026 winners announcement renders first."""
    collection = _page_announcements(announcements_page)
    assert isinstance(collection, list)
    assert len(collection) >= 1
    assert collection[0] == announcements_page.get_season_2026_winners_announcement()


def test_existing_announcements_are_unchanged(announcements_page) -> None:
    """Spec behaviour 11: exactly one entry added, all previous entries intact."""
    collection = _page_announcements(announcements_page)
    expected = json.loads(ANNOUNCEMENTS_BASELINE_PATH.read_text(encoding="utf-8"))
    assert isinstance(expected, list) and expected

    assert len(collection) == len(expected) + 1
    assert collection[1:] == expected

    pairs = [(entry["title"], entry["body"]) for entry in collection[1:]]
    assert len(pairs) == len(set(pairs))


def test_announcements_baseline_matches_page_history(announcements_page) -> None:
    """The baseline file is a faithful copy, not a hand-trimmed subset."""
    expected = json.loads(ANNOUNCEMENTS_BASELINE_PATH.read_text(encoding="utf-8"))
    assert all(set(entry) == {"title", "body"} for entry in expected)
    assert all(entry["title"].strip() != "" and entry["body"].strip() != "" for entry in expected)
```

**Definition of done:**
- [ ] `test_streamlit_app.py::test_2026_season_winners_announcement_is_newest_entry`: proves spec behaviour 10 — `collection[0]` equals `get_season_2026_winners_announcement()`.
- [ ] `test_streamlit_app.py::test_existing_announcements_are_unchanged`: proves spec behaviour 11 — `len(collection) == len(baseline) + 1`, `collection[1:] == baseline` (identical `title`/`body`, same order), and every `(title, body)` pair appears exactly once.
- [ ] `test_streamlit_app.py::test_announcements_baseline_matches_page_history`: proves the checked-in baseline is well-formed and non-empty, so the unchanged check is meaningful.
- [ ] The diff to `pages/1_📢_Announcements.py` contains only the two new Phase 1 symbols and the one prepended list element.

**Verify:**
```bash
uv run pytest "test_streamlit_app.py::test_2026_season_winners_announcement_is_newest_entry" "test_streamlit_app.py::test_existing_announcements_are_unchanged" "test_streamlit_app.py::test_announcements_baseline_matches_page_history" -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 3: Prove the rendered page shows the new announcement
<!-- phase: 3 -->
<!-- targets: test_streamlit_app.py, pages/1_📢_Announcements.py -->
<!-- frozen: data.py, streamlit_app.py, theme.py, auth.py, features/**, pages/2_📅_Events.py, pages/3_🏆_League.py, pages/4_🥊_Cup.py, pages/5_⛳_Outing.py, pages/6_💾_API_Data.py, pyproject.toml, requirements.txt, uv.lock, tests/fixtures/announcements_before_2026_winners.json -->

**Goal:** Running the Announcements page through `AppTest` offline renders the new announcement's title and every non-empty body line, with no change to the render path.

**Changes:**
- `test_streamlit_app.py`: append at the end of the file:

```python
def _rendered_text(at) -> str:
    """All text the running page emitted, across the element types it can use."""
    parts: list[str] = []
    for name in ("markdown", "subheader", "header", "title", "caption", "text"):
        for element in getattr(at, name, []):
            parts.append(str(getattr(element, "value", "")))
    for element in getattr(at, "expander", []):
        parts.append(str(getattr(element, "label", "")))
    return "\n".join(parts)


def test_announcements_page_includes_2026_season_winners(announcements_page) -> None:
    """Spec behaviour 12: the page renders the announcement offline."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ANNOUNCEMENTS_PAGE_PATH), default_timeout=30).run()
    announcement = announcements_page.get_season_2026_winners_announcement()
    rendered = _rendered_text(at)
    exceptions = [str(getattr(e, "value", e)) for e in at.exception]

    assert announcement["title"] in rendered, f"title not rendered; exceptions={exceptions}; rendered={rendered!r}"
    for line in announcement["body"].splitlines():
        stripped = line.strip()
        if stripped:
            assert stripped in rendered, f"line {stripped!r} not rendered; exceptions={exceptions}; rendered={rendered!r}"
```

- `pages/1_📢_Announcements.py`: default change is none. Only if the assertion above fails because the title is rendered through an element type not covered by `_rendered_text`, extend `_rendered_text` in `test_streamlit_app.py` to include that element collection (reading its `.value` or `.label`). Do not alter the page's render path.
- No new dependency: `streamlit.testing.v1` ships with the already-declared `streamlit` dependency.

**Definition of done:**
- [ ] `test_streamlit_app.py::test_announcements_page_includes_2026_season_winners`: proves spec behaviour 12 — `AppTest.from_file("pages/1_📢_Announcements.py").run()` with no network renders the announcement title and every non-empty body line (title, `个人联赛冠军：张纬`, `个人杯赛冠军：王文龙`, and the `祝贺` lines).
- [ ] `uv run pytest test_streamlit_app.py -v` passes with all pre-existing tests plus the three new ones — proving spec behaviour 13 (the existing suite still passes unchanged).
- [ ] The page render path is unmodified: the loop over `<COLLECTION_NAME>` is byte-identical to the approved tag's version.

**Verify:**
```bash
uv run pytest test_streamlit_app.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- The approved documents do not show the page's real collection name or its current copy; a wrong guess breaks Phase 2 — caught by `test_existing_announcements_are_unchanged` and by the import in Phase 1/2.
- `pages/1_📢_Announcements.py` may run Streamlit or network code at import time; in a bare pytest process that mostly no-ops, but a `st.session_state`/secrets/network failure surfaces as a Phase 1 or Phase 2 import error. Phase 3 shows whether the page truly renders offline.
- The page might gate on auth or a data source; if so, Phase 3's `AppTest` check fails and the plan must be revised (changing auth is out of scope), rather than loosening the test.
- The render path might emit the title through an element type `_rendered_text` does not collect; Phase 3 catches it and the collector is extended, not the page.
- Transcribing the baseline JSON by hand can introduce copy drift; Phase 2's exact-equality assertions catch it and the builder re-copies from the file (within the attempt budget).
- Mixing up `张纬` and `张维`; Phase 1's `"张维" not in text` assertion and the `张纬` presence check catch it.

## Open questions
- The real name of the module-level announcement collection and the exact pre-existing copy are not in the approved documents. Assumption: the builder resolves both by reading `pages/1_📢_Announcements.py` (a read, not an exploratory shell probe) and uses the real name wherever this plan writes `<COLLECTION_NAME>`.
- Whether the collection is a literal or a loader expression is unknown. Assumption: prepend via a list literal if it is a literal, otherwise `[SEASON_2026_WINNERS_ANNOUNCEMENT, *<EXISTING EXPRESSION>]`; never mutate in place.
- `streamlit.testing.v1.AppTest` (streamlit ≥ 1.28) is assumed importable. If it is not, stop at Phase 3 and revise the plan: adding or upgrading dependencies is out of scope for the spec.
- The intent's 张纬 vs the scorecard 张维 is left unresolved by design; the announcement uses 张纬 and nothing else in the repository is touched.

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/001-add-a-new-announcement-congratulating-th/build-log.md` with one section per phase, in order. Head each one `## Phase <n>: <title>`, then list the files changed, the Verify command you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/001-add-a-new-announcement-congratulating-th`.
