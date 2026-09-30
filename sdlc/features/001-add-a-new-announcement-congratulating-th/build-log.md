# Build log: 001-add-a-new-announcement-congratulating-th

## Phase 1: Add display-only winners announcement helpers
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `pages/1_📢_Announcements.py`, `tests/test_pinned_winners_announcement.py` (new).

`pages/1_📢_Announcements.py` now defines `PINNED_2026_WINNERS_ANNOUNCEMENT_ID`, the display-only `PINNED_2026_WINNERS_ANNOUNCEMENT` record (id, title, date, author, pinned, body, tags; body names 张纬 as 2026 个人联赛 winner and 王文龙 as 2026 个人杯赛 winner), `get_pinned_winners_announcement()` (a fresh copy, tags included) and `get_display_announcements()` (a new list with the winners announcement first), exactly as the plan gives them; the render loop is untouched until Phase 2. `tests/test_pinned_winners_announcement.py` has the plan's fake-Streamlit fixture and its six tests.

- `uv run pytest tests/test_pinned_winners_announcement.py -v` (Phase 1 Verify): first attempt failed, 6 errors `ModuleNotFoundError: No module named 'data'`; after the fix below, exit 0, 6 passed.
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 001-add-a-new-announcement-congratulating-th --phase 1`: with `ly2xxx/.github@f54a5f2` as published, exit 1 on scope only (`1 outside the plan: "pages/1_\360\237\223\242_Announcements.py"`); whole suite and Phase 1 Verify passed, no frozen file touched, contract matches. With the one-line `core.quotePath=false` fix below applied to the checker, exit 0: PASSED, scope all inside the targets.
- Whole suite: `python -m pytest -q` 11 passed (5 existing + 6 new); `behave --format progress` 17 scenarios passed.
- SDLC Phase Check on the first push (run 36696828767): FAILED on scope only, the same octal-escaped path; whole suite and Phase 1 Verify passed. After the checker fix landed as `ly2xxx/.github@e924f2e`, the same local verify against the committed branch (`--base feature/001-add-a-new-announcement-congratulating-th`) exits 0: PASSED, scope all inside the targets.

**Deviations:**
- The fixture adds `monkeypatch.syspath_prepend(str(PAGE_PATH.parents[1]))` before `import data`. The Verify block runs `uv run pytest tests/...`, whose sys.path holds `tests/` but not the repository root where `data.py`, `theme.py` and `auth.py` live, so the plan's fixture could not import them. It stands because it is the same fix the existing `test_streamlit_app.py` uses (`sys.path.append(...)`), scoped to the test by `monkeypatch`, and changes no page behaviour.
- Checker bug outside the plan: `sdlc_stage.py` reads `git diff --name-only` and `git ls-files` with git's default `core.quotePath=true`, so a non-ASCII target such as `pages/1_📢_Announcements.py` is reported as an octal-escaped path outside the targets. The fix belongs in `ly2xxx/.github` (`git()` helper passes `-c core.quotePath=false`), not in this feature's targets; the owner committed it there as `e924f2e`. Nothing in this repository changed for it.
