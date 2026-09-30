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

## Phase 2: Home page uses the shared selector
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `streamlit_app.py`, `tests/test_announcement_page_wiring.py` (new).

`streamlit_app.py` imports `get_display_announcements` from `pinned_announcements` after its `data` import, and its 最新动态 block now takes `get_display_announcements(anns_sorted)[:2]`; the sort, the `[:2]` cap, the body truncation and the card markup are unchanged. `tests/test_announcement_page_wiring.py` has the plan's header, helpers and five tests; `test_streamlit_app.py` and `tests/test_pinned_winners_announcement.py` import neither relocated name, so they are unchanged.

- `uv run pytest tests/test_announcement_page_wiring.py tests/test_pinned_announcements.py tests/test_pinned_winners_announcement.py test_streamlit_app.py -v` (Phase 2 Verify): exit 0, 30 passed.
- Observable check (`get_display_announcements` defs in `streamlit_app.py`): prints `0`.
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 003-front-page-in-streamlit-app-py --phase 2`: exit 0, PASSED (scope all inside the targets, no frozen file touched, contract matches; Phase 1 and Phase 2 Verify passed; pytest 30 passed, behave 17 scenarios passed).
- Extra check, not in the plan and not committed: `streamlit.testing.v1.AppTest.from_file("streamlit_app.py").run()` with the repository's data shows two 最新动态 cards, `📌 🎉 2026 赛季个人冠军公告` and `📌 🎉 2026 Outing Day 对抗赛结果公告`, with no exception. Before this phase it showed the first two stored announcements.

**Deviations:**
- Fixed the plan's `_has_module_level_pinned_literal` helper: it looked the key up with `pairs.get(ast.Constant(value="pinned"))`, but AST nodes compare by identity, so that lookup always returns `None` and the helper returned `False` for every file. The Phase 2 "no pinned literal" checks would pass vacuously and Phase 3's `test_only_shared_module_defines_records_or_helper` (which expects `{"pinned_announcements.py"}`) could never pass. The helper now keys the dict by each constant key's value, which is what its docstring describes; checked: `True` for `pinned_announcements.py`, `False` for `data.py` (a list mixing pinned and unpinned records) and for `streamlit_app.py`.
- Added two small helpers to the test module: `_record()` builds the sample records with the required keys the plan asks for ("plus the required keys"), and `_calls_helper()` is the `ast.Call` check used by `test_home_page_calls_the_shared_helper` (and by the Phase 3 test for the Announcements page).
- The plan's Goal says the 最新动态 block "still shows the same two announcements as before". It assumed the home page already had its own pinned copy; it did not, so the block now shows the two pinned records instead of the first two stored announcements. That is the change the feature exists for (the home page matching the Announcements page), so it stands.
- `streamlit_app.py` had no pinned list or local `get_display_announcements` to delete; the call site is new, placed on the existing `[:2]` line.

## Phase 3: Announcements page uses the shared selector and uniqueness is proven
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `pages/1_📢_Announcements.py`, `tests/test_announcement_page_wiring.py`.

`pages/1_📢_Announcements.py` no longer defines the two pinned record literals, `PINNED_2026_WINNERS_ANNOUNCEMENT_ID` or its own `get_display_announcements`; it imports `PINNED_ANNOUNCEMENTS` and `get_display_announcements` from `pinned_announcements`, and its existing `get_display_announcements(anns_sorted)` call now uses the shared one (render path, cap and markup unchanged). The wiring test module gains the plan's five Phase 3 tests; `tests/test_pinned_winners_announcement.py` had no page-source assertion or relocated import to update, so it is unchanged and all its tests still pass.

- `uv run pytest tests/test_announcement_page_wiring.py tests/test_pinned_announcements.py tests/test_pinned_winners_announcement.py -v` (Phase 3 Verify, first command): exit 0, 30 passed.
- `test -z "$(grep -n 'def get_display_announcements' streamlit_app.py 'pages/1_📢_Announcements.py' || true)"` (second command): exit 0.
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 003-front-page-in-streamlit-app-py --phase 3`: exit 0, PASSED (scope all inside the targets, no frozen file touched, contract matches; Phase 1-3 Verify passed; pytest 35 passed, behave 17 scenarios passed).
- `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=.venv` (CI's fatal lint): 0, exit 0.
- Extra check, not in the plan and not committed: `streamlit.testing.v1.AppTest` with the repository's data renders, with no exception, the home page 最新动态 as `📌 🎉 2026 赛季个人冠军公告`, `📌 🎉 2026 Outing Day 对抗赛结果公告`, and the Announcements page as those two followed by `📌 🏌️ 2026赛季正式开幕！`, `📋 个人杯赛抽签结果公布`.

**Deviations:**
- The page keeps `PINNED_2026_WINNERS_ANNOUNCEMENT`, `PINNED_OUTING_DAY_RESULT_ANNOUNCEMENT`, `get_pinned_winners_announcement()` and `get_pinned_outing_day_result_announcement()`, now bound to the shared records (`PINNED_2026_WINNERS_ANNOUNCEMENT, PINNED_OUTING_DAY_RESULT_ANNOUNCEMENT = PINNED_ANNOUNCEMENTS`) rather than defining them. The plan requires `tests/test_pinned_winners_announcement.py`'s other assertions to keep passing, and 15 of them read those names from the page module (they come from features 001 and 002), while `pinned_announcements.py` is frozen with the plan's exact content, which has no named records or copy accessors. Keeping thin views on the page satisfies both without redefining any record, copying the selector or weakening a test; the page still imports `get_display_announcements` and defines no pinned literal, as the Phase 3 tests check. The page imports `PINNED_ANNOUNCEMENTS` as well as `get_display_announcements` for these views.
- `_calls_helper()` from Phase 2 backs `test_announcements_page_calls_the_shared_helper`, and `_record()` builds `test_both_pages_share_one_pinned_sequence`'s extra records with the required keys.
