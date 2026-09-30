# Build log: 003-front-page-in-streamlit-app-py

## Phase 1: Shared pinned-announcements module
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `pinned_announcements.py` (new), `tests/test_pinned_announcements.py` (new).

`pinned_announcements.py` is the plan's module as given: `PINNED_ANNOUNCEMENTS` holds the two pinned records (2026 individual winners, then the Outing Day 对抗赛 result) and `get_display_announcements(announcements=None)` returns them first, then extra pinned input records, then the rest, de-duplicated by `id`, without mutating or truncating. It imports nothing but `__future__`; both pages are untouched until Phases 2 and 3. `tests/test_pinned_announcements.py` has the plan's header and its nine tests.

- `uv run pytest tests/test_pinned_announcements.py -v` (Phase 1 Verify): exit 0, 9 passed.
- `uv run python -c "import pinned_announcements as p; print(len(p.PINNED_ANNOUNCEMENTS), [a['id'] for a in p.get_display_announcements(None)])"`: prints `2 ['pinned-2026-season-winners', 'pinned-2026-outing-day-result']`, no traceback.
- The two records compare equal (`==`) to `get_pinned_winners_announcement()` and `get_pinned_outing_day_result_announcement()` from the unchanged `pages/1_📢_Announcements.py`, so no announcement content changes.
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 003-front-page-in-streamlit-app-py --phase 1`: exit 0, PASSED (scope all inside the targets, no frozen file touched, contract matches; pytest 25 passed, behave 17 scenarios passed).

**Deviations:**
- The records were copied from `pages/1_📢_Announcements.py`, not `streamlit_app.py`. The plan says to copy "the module-level list literal" from `streamlit_app.py` and to confirm the page's copy matches, but `streamlit_app.py` has no pinned records (its 最新动态 block shows the first two stored announcements from `load_announcements()`), and the page holds them as two dicts, `PINNED_2026_WINNERS_ANNOUNCEMENT` and `PINNED_OUTING_DAY_RESULT_ANNOUNCEMENT`. They stand as the only existing copy. Two values the page expressed as name references are written out as the strings they evaluate to, since the list lives in a new module: `"id": "pinned-2026-season-winners"` (was `PINNED_2026_WINNERS_ANNOUNCEMENT_ID`) and the outing record's `"author": "GCO 组委会"` (was `PINNED_2026_WINNERS_ANNOUNCEMENT["author"]`).
