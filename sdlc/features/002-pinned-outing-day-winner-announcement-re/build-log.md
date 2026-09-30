# Build log: 002-pinned-outing-day-winner-announcement-re

## Phase 1: Add the pinned Outing Day result announcement and its accessor
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `pages/1_📢_Announcements.py`, `tests/test_pinned_winners_announcement.py`.

`pages/1_📢_Announcements.py` now defines `PINNED_OUTING_DAY_RESULT_ANNOUNCEMENT` (id `pinned-2026-outing-day-result`; body 红队 Red Team 5.0 pts 战胜 黑队 Black Team 3.0 pts with the roster 刘北南 • 李扬 • 赵鲲 • 张纬 • Justin • 曾诚) right after the winners constant, and `get_pinned_outing_day_result_announcement()` returning `copy.deepcopy` of it right after the winners accessor; `get_display_announcements` and the render path are unchanged. The test module gains `import re` and the plan's four new tests.

- `uv run pytest tests/test_pinned_winners_announcement.py -v` (Phase 1 Verify): exit 0, 11 passed (7 existing, still expecting one pinned entry, plus 4 new).
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 002-pinned-outing-day-winner-announcement-re --phase 1`: exit 0, PASSED (scope all inside the targets, no frozen file touched, contract matches; pytest 16 passed, behave 17 scenarios passed).

**Deviations:**
- Added `import copy` at the top of `pages/1_📢_Announcements.py`. The plan asks for `return copy.deepcopy(PINNED_OUTING_DAY_RESULT_ANNOUNCEMENT)` and says to add the import "if the winners accessor uses `copy.deepcopy`"; the winners accessor uses `dict(...)` plus `list(tags)` instead, but `copy.deepcopy` cannot run without the import, so it stands. The winners accessor is unchanged.

## Phase 2: Insert the outing announcement second in the display list and prove render order
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `pages/1_📢_Announcements.py`, `tests/test_pinned_winners_announcement.py`.

`get_display_announcements()` now returns `[get_pinned_winners_announcement(), get_pinned_outing_day_result_announcement(), *stored_announcements]`; its signature, the render path and every save/edit/delete path are unchanged. The four display/render tests were updated in place exactly as the plan gives them: two pinned ids first, stored dicts after them by identity, and the rendered order winners → outing (title, scores, roster) → stored with no `save_announcements` call.

- `uv run pytest tests/test_pinned_winners_announcement.py -v` (Phase 2 Verify): exit 0, 11 passed.
- The four updated tests fail against the Phase 1 page (4 failed, 7 passed) and pass with the change, so they test the new ordering.
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 002-pinned-outing-day-winner-announcement-re --phase 2`: exit 0, PASSED (scope all inside the targets, no frozen file touched, contract matches; Phase 1 and Phase 2 Verify passed; pytest 16 passed, behave 17 scenarios passed).
- Extra check, not in the plan and not committed: `streamlit.testing.v1.AppTest.from_file("pages/1_📢_Announcements.py").run()` with the repository's data renders, with no exception: `📌 🎉 2026 赛季个人冠军公告`, `📌 🎉 2026 Outing Day 对抗赛结果公告`, `📌 🏌️ 2026赛季正式开幕！`, `📋 个人杯赛抽签结果公布`.

**Deviations:**
- Kept the existing parameter name `stored_announcements` in `get_display_announcements`, and the docstring names it (`*stored_announcements`). The plan's code block writes the parameter as `announcements`, but the same step says to change only the body and keep the signature unchanged; keeping the name does both, and every caller passes it positionally.
