<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@98028f3 -->
## Approach
Add one module-level constant describing the fixed Outing Day 对抗赛 result plus a deep-copy accessor in `pages/1_📢_Announcements.py`, insert that announcement as the second element of the list returned by `get_display_announcements()`, and update `tests/test_pinned_winners_announcement.py` to assert the new content, its fresh-copy semantics, the two-pinned ordering, the rendered order in the Streamlit call log, and the absence of any store write. No data-model, scoring, persistence, or render-path code changes.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| `pages/1_📢_Announcements.py` renders an Outing Day 对抗赛 pinned announcement showing 红队 Red Team at 5.0 pts and 黑队 Black Team at 3.0 pts. | 8, 9, 17 | Phase 2 |
| The announcement lists the Red Team roster exactly as 刘北南 • 李扬 • 赵鲲 • 张纬 • Justin • 曾诚. | 10 | Phase 1 |
| `get_display_announcements()` returns the Outing Day 对抗赛 announcement as the second item, after the existing 2026 winners announcement. | 13, 14, 15, 16 | Phase 2 |
| The announcement is display-only: no scoring, editing, persistence, or tournament-state calculation is introduced to produce it. | 11, 12, 18 | Phase 1 and Phase 2 |
| Tests in `tests/test_pinned_winners_announcement.py` are updated to cover the new second announcement and its content. | 1–19 | Phase 1 and Phase 2 |
| The existing tests still pass. | 1–19 | Phase 1 and Phase 2 |

## Phase 1: Add the pinned Outing Day result announcement and its accessor
<!-- phase: 1 -->
<!-- targets: pages/1_📢_Announcements.py, tests/test_pinned_winners_announcement.py -->
<!-- frozen: data.py, streamlit_app.py, tests/test_streamlit_app.py, features/** -->

**Goal:** `pages/1_📢_Announcements.py` exposes a fresh-copy accessor returning a display-only pinned Outing Day 对抗赛 result dict with the exact required keys, scores and Red Team roster, and nothing about the existing display ordering changes yet.

**Changes:**

- `pages/1_📢_Announcements.py`:
  - Immediately after the existing `PINNED_2026_WINNERS_ANNOUNCEMENT: dict[str, Any] = {...}` literal, add a new module-level constant (keep the existing constant, `get_pinned_winners_announcement`, `get_display_announcements` and the render path byte-for-byte unchanged):

    ```python
    PINNED_OUTING_DAY_RESULT_ANNOUNCEMENT: dict[str, Any] = {
        "id": "pinned-2026-outing-day-result",
        "title": "🎉 2026 Outing Day 对抗赛结果公告",
        "date": "2026-08-16",
        "author": PINNED_2026_WINNERS_ANNOUNCEMENT["author"],
        "pinned": True,
        "body": (
            "🏌️ Outing Day 对抗赛结果\n"
            "\n"
            "红队 Red Team 5.0 pts 战胜 黑队 Black Team 3.0 pts\n"
            "红队阵容：刘北南 • 李扬 • 赵鲲 • 张纬 • Justin • 曾诚"
        ),
        "tags": ["Outing Day", "对抗赛"],
    }
    ```

    The literal `author` value is taken from the existing winners constant (same value, no new author concept). `title` must contain `"Outing Day"` and `"对抗赛"`; `date` must match `YYYY-MM-DD`. Do not add any import of `data` or any tournament/scoring call here.
  - Immediately after `get_pinned_winners_announcement()`, add the new accessor, implemented exactly the same way as the winners accessor (i.e. `return copy.deepcopy(PINNED_OUTING_DAY_RESULT_ANNOUNCEMENT)`); if the winners accessor uses `copy.deepcopy`, confirm `import copy` is present at module top and add it if it is missing. Signature and docstring:

    ```python
    def get_pinned_outing_day_result_announcement() -> dict[str, Any]:
        """Return a fresh deep copy of PINNED_OUTING_DAY_RESULT_ANNOUNCEMENT."""
    ```
  - Make **no** change in this phase to `get_display_announcements(announcements: list[dict[str, Any]]) -> list[dict[str, Any]]` or to the rendering block.

- `tests/test_pinned_winners_announcement.py`:
  - Add `import re` at module top (after `import pathlib`, keeping the import block alphabetical).
  - Append four new test functions at the end of the file, after `test_page_renders_pinned_winners_before_stored`, using the existing `load_announcements_page` fixture unchanged:

    ```python
    def test_pinned_outing_day_result_announcement_has_exact_fields(load_announcements_page):
        """Spec behaviours 1, 2, 3, 4, 5, 6, 7."""
        module, _, _ = load_announcements_page()
        ann = module.get_pinned_outing_day_result_announcement()

        assert set(ann) == {"id", "title", "date", "author", "pinned", "body", "tags"}
        assert ann["id"] == "pinned-2026-outing-day-result"
        assert ann["pinned"] is True
        assert isinstance(ann["title"], str) and ann["title"]
        assert "Outing Day" in ann["title"] and "对抗赛" in ann["title"]
        assert isinstance(ann["date"], str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", ann["date"])
        assert isinstance(ann["author"], str) and ann["author"]
        assert isinstance(ann["tags"], list) and all(isinstance(t, str) for t in ann["tags"])


    def test_pinned_outing_day_result_announcement_body_content(load_announcements_page):
        """Spec behaviours 8, 9, 10."""
        module, _, _ = load_announcements_page()
        body = module.get_pinned_outing_day_result_announcement()["body"]

        assert "红队 Red Team" in body
        assert "5.0 pts" in body
        assert "黑队 Black Team" in body
        assert "3.0 pts" in body
        assert "刘北南 • 李扬 • 赵鲲 • 张纬 • Justin • 曾诚" in body


    def test_get_pinned_outing_day_result_announcement_returns_fresh_copy(load_announcements_page):
        """Spec behaviour 11."""
        module, _, _ = load_announcements_page()
        first = module.get_pinned_outing_day_result_announcement()
        second = module.get_pinned_outing_day_result_announcement()

        assert first == second
        assert first is not second

        first["tags"].append("mutated")
        assert "mutated" not in module.PINNED_OUTING_DAY_RESULT_ANNOUNCEMENT["tags"]
        assert "mutated" not in module.get_pinned_outing_day_result_announcement()["tags"]


    def test_get_pinned_outing_day_result_announcement_does_not_read_stored_store(
        load_announcements_page, monkeypatch
    ):
        """Spec behaviour 12."""
        module, _, _ = load_announcements_page()
        import data

        def fail():
            raise AssertionError("stored announcements store was read")

        monkeypatch.setattr(data, "load_announcements", fail)

        ann = module.get_pinned_outing_day_result_announcement()
        assert ann["id"] == "pinned-2026-outing-day-result"
    ```

  - Leave every pre-existing test in this file unchanged in this phase.

**Definition of done:**

- [ ] `tests/test_pinned_winners_announcement.py::test_pinned_outing_day_result_announcement_has_exact_fields`: proves spec behaviours 1–7 — asserts the key set is exactly `{"id", "title", "date", "author", "pinned", "body", "tags"}`, `id == "pinned-2026-outing-day-result"`, `pinned is True`, `title` is a non-empty `str` containing `"Outing Day"` and `"对抗赛"`, `date` matches `re.fullmatch(r"\d{4}-\d{2}-\d{2}", ...)`, `author` is a non-empty `str`, `tags` is a `list` of `str`. Uses the existing `load_announcements_page` fixture, which restores `sys.modules["streamlit"]` via `monkeypatch` and pops loaded page modules in teardown; no extra cleanup is needed.
- [ ] `tests/test_pinned_winners_announcement.py::test_pinned_outing_day_result_announcement_body_content`: proves spec behaviours 8–10 — asserts `body` contains `"红队 Red Team"`, `"5.0 pts"`, `"黑队 Black Team"`, `"3.0 pts"` and the exact roster string `"刘北南 • 李扬 • 赵鲲 • 张纬 • Justin • 曾诚"`.
- [ ] `tests/test_pinned_winners_announcement.py::test_get_pinned_outing_day_result_announcement_returns_fresh_copy`: proves spec behaviour 11 — two calls are `==` but not `is`; appending to the first result's `tags` leaves `PINNED_OUTING_DAY_RESULT_ANNOUNCEMENT["tags"]` and a third call's `tags` untouched.
- [ ] `tests/test_pinned_winners_announcement.py::test_get_pinned_outing_day_result_announcement_does_not_read_stored_store`: proves spec behaviour 12 — after `monkeypatch.setattr(data, "load_announcements", fail)`, the accessor still returns the announcement (no store read, no scoring, no tournament state).
- [ ] Other observable check: the whole test file still passes, including the four pre-existing `get_display_announcements`/render assertions that still expect a single pinned entry (`test_get_display_announcements_empty` asserts `len(result) == 1`), which proves this phase did not yet alter display ordering.

**Verify:**
```bash
uv run pytest tests/test_pinned_winners_announcement.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Insert the outing announcement second in the display list and prove render order
<!-- phase: 2 -->
<!-- targets: pages/1_📢_Announcements.py, tests/test_pinned_winners_announcement.py -->
<!-- frozen: data.py, streamlit_app.py, tests/test_streamlit_app.py, features/** -->

**Goal:** `get_display_announcements([])` returns exactly `[pinned winners, pinned outing]`, stored announcements follow in their original order and identity, and the page renders winners → outing → stored with no `data.save_announcements` call.

**Changes:**

- `pages/1_📢_Announcements.py`:
  - Change only the body of `get_display_announcements` (signature and return type unchanged — one positional `list[dict[str, Any]]` parameter, `list[dict[str, Any]]` return) to:

    ```python
    def get_display_announcements(announcements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return [pinned winners announcement, pinned outing day result announcement, *announcements]."""
        return [
            get_pinned_winners_announcement(),
            get_pinned_outing_day_result_announcement(),
            *announcements,
        ]
    ```

    Keep the two accessor calls (fresh copies) and the `*announcements` unpack so stored dicts pass through by identity. Do not change the render block, and do not add any filtering/deduplication, badge, or new render branch.

- `tests/test_pinned_winners_announcement.py`: update the existing display/render tests in place (do not add a new test file); keep every other test untouched.

  - Replace `test_get_display_announcements_empty` with:

    ```python
    def test_get_display_announcements_empty(load_announcements_page):
        """Spec behaviour 13."""
        module, _, _ = load_announcements_page()
        result = module.get_display_announcements([])

        assert len(result) == 2
        assert [a["id"] for a in result] == ["pinned-2026-season-winners", "pinned-2026-outing-day-result"]
        assert result[0] == module.get_pinned_winners_announcement()
        assert result[1] == module.get_pinned_outing_day_result_announcement()
    ```

  - Extend `test_get_display_announcements_pins_first_before_stored_pinned` (the spec refers to this test as `test_get_display_announcements_pins_first_before_stored`): keep the existing `stored` fixtures (`s1` pinned, `s2` unpinned) and `before = copy.deepcopy(stored)`, and replace the assertions with:

    ```python
        result = module.get_display_announcements(stored)

        assert [a["id"] for a in result] == [
            "pinned-2026-season-winners",
            "pinned-2026-outing-day-result",
            "s1",
            "s2",
        ]
        assert result[2] is stored[0]
        assert result[3] is stored[1]
        assert len(stored) == 2
        assert stored == before
    ```

    (Spec behaviours 14, 15: two pinned ids first, then stored ids in original order; input list and its dicts unchanged; stored dicts are the same objects.)

  - Extend `test_get_display_announcements_passes_through_missing_fields` (stored dict with `date`, `author`, `tags` all `None`): replace the assertions with:

    ```python
        result = module.get_display_announcements(stored)

        assert len(result) == 3
        assert [a["id"] for a in result] == [
            "pinned-2026-season-winners",
            "pinned-2026-outing-day-result",
            "s1",
        ]
        assert result[2] == stored[0]
        assert result[2] is stored[0]
    ```

    (Spec behaviour 16: the malformed stored dict is returned unchanged and by identity at its original relative position after the two pinned announcements.)

  - Extend `test_page_renders_pinned_winners_before_stored`: keep the existing `stored` fixtures (`stored-pinned`, `stored-normal`), `before = copy.deepcopy(stored)`, `module, log, save_calls = load_announcements_page(stored)` and the existing `text = "\n".join(...)` construction. Replace the assertion block with:

    ```python
        winners_title = "🎉 2026 赛季个人冠军公告"
        outing_title = "🎉 2026 Outing Day 对抗赛结果公告"
        roster = "刘北南 • 李扬 • 赵鲲 • 张纬 • Justin • 曾诚"

        assert winners_title in text
        assert "张纬" in text and "王文龙" in text
        assert outing_title in text
        assert "红队 Red Team" in text and "5.0 pts" in text
        assert "黑队 Black Team" in text and "3.0 pts" in text
        assert roster in text
        assert "STORED PINNED TITLE" in text
        assert "STORED NORMAL TITLE" in text

        assert text.index(winners_title) < text.index(outing_title)
        assert text.index(outing_title) < text.index("STORED PINNED TITLE")
        assert text.index(outing_title) < text.index("STORED NORMAL TITLE")
        assert text.index(roster) < text.index("STORED NORMAL TITLE")

        assert stored == before
        assert save_calls == []
    ```

    (Spec behaviours 17, 18: outing title, scores and roster appear after the winners text and before any stored text; `data.save_announcements` is never called. `module` is still used for `load_announcements_page`'s import side effect — keep the assignment as `module, log, save_calls = ...`.)

**Definition of done:**

- [ ] `tests/test_pinned_winners_announcement.py::test_get_display_announcements_empty`: proves spec behaviour 13 — `get_display_announcements([])` has exactly two items, `result[0] == get_pinned_winners_announcement()`, `result[1] == get_pinned_outing_day_result_announcement()`, ids `["pinned-2026-season-winners", "pinned-2026-outing-day-result"]`. Runs through the `load_announcements_page` fixture with no extra cleanup needed.
- [ ] `tests/test_pinned_winners_announcement.py::test_get_display_announcements_pins_first_before_stored_pinned`: proves spec behaviours 14 and 15 — id order is the two pinned ids followed by `s1`, `s2`; `result[2] is stored[0]` and `result[3] is stored[1]`; `stored == before` (deepcopy snapshot taken before the call).
- [ ] `tests/test_pinned_winners_announcement.py::test_get_display_announcements_passes_through_missing_fields`: proves spec behaviour 16 — `len(result) == 3`, id order winners/outing/`s1`, and `result[2] is stored[0]` (unchanged identity with `date`/`author`/`tags` = `None`).
- [ ] `tests/test_pinned_winners_announcement.py::test_page_renders_pinned_winners_before_stored`: proves spec behaviours 17 and 18 — the recorded Streamlit call log contains the outing title, `"红队 Red Team"`, `"5.0 pts"`, `"黑队 Black Team"`, `"3.0 pts"` and the roster, positioned after the winners title and before both stored titles; `save_calls == []`; `stored == before`. The fixture's `monkeypatch` teardown restores `sys.modules["streamlit"]` and the `data.load_announcements`/`data.save_announcements` patches, so no server, thread, or file cleanup is required.
- [ ] Other observable check: the whole file passes, including the four Phase 1 tests and the unchanged `test_pinned_announcement_has_exact_fields`, `test_get_pinned_winners_announcement_returns_fresh_copy`, `test_get_pinned_winners_announcement_does_not_read_stored_store`.

**Verify:**
```bash
uv run pytest tests/test_pinned_winners_announcement.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- **A caller counts on a single pinned entry.** `get_display_announcements` gains a second element; Phase 2's `test_get_display_announcements_empty`, `..._pins_first_before_stored_pinned`, `..._passes_through_missing_fields` and the final whole-suite run (`python -m pytest -q && behave --format progress`) would catch a mismatch.
- **Shallow copy leaks mutable `tags` into the module constant.** Phase 1's `test_get_pinned_outing_day_result_announcement_returns_fresh_copy` fails if `dict(...)` or a bare literal is returned instead of `copy.deepcopy`.
- **`copy` not imported, or the new constant placed before `PINNED_2026_WINNERS_ANNOUNCEMENT`.** Import-time `NameError` fails every test in Phase 1's Verify block.
- **Stored dicts get copied instead of passed by identity.** Phase 2's `result[2] is stored[0]` / `result[3] is stored[1]` identity assertions fail.
- **Render-order assertions use the wrong title string.** Phase 2's `test_page_renders_pinned_winners_before_stored` fails on `assert outing_title in text` rather than on a `ValueError` from `text.index`.
- **A store write is introduced in the render path.** `save_calls == []` in the Phase 2 render test fails.
- **BDD / streamlit_app tests regress.** Nothing in either phase touches `data.py`, `streamlit_app.py` or `features/**` (all frozen); the final whole-suite run is the backstop.

## Open questions
- The spec names tests `test_get_display_announcements_pins_first_before_stored` and `test_get_display_announcements_empty`; the file already contains `test_get_display_announcements_pins_first_before_stored_pinned` and `test_get_display_announcements_empty`. Assumption: extend the existing functions in place and do not rename them. No new test files are created.
- Title, date, author and `tags` literals are unspecified. Assumption: `title = "🎉 2026 Outing Day 对抗赛结果公告"`, `date = "2026-08-16"`, `author = PINNED_2026_WINNERS_ANNOUNCEMENT["author"]` (same value as the existing pinned announcement), `tags = ["Outing Day", "对抗赛"]`. Tests assert format and required substrings only, never the literal date or tags.
- Whether the announcement needs a distinct pinned badge. Assumption: no — `pinned: True` plus the unchanged render path gives the identical treatment to the existing pinned winners announcement.
- Whether the Black Team roster should be listed. Assumption: no — the body contains the Black Team name and score only, exactly as the spec's required body shows.
- No dependency changes are needed; `pyproject.toml` and `requirements.txt` are frozen in both phases.

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/002-pinned-outing-day-winner-announcement-re/build-log.md` with one section per phase, in order. Head each one `## Phase <n>: <title>`, then list the files changed, the Verify command you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/002-pinned-outing-day-winner-announcement-re`.
