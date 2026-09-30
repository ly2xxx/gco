# Build log: 002-pinned-outing-day-winner-announcement-re

## Phase 1: Add the pinned Outing Day result announcement and its accessor
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `pages/1_📢_Announcements.py`, `tests/test_pinned_winners_announcement.py`.

`pages/1_📢_Announcements.py` now defines `PINNED_OUTING_DAY_RESULT_ANNOUNCEMENT` (id `pinned-2026-outing-day-result`; body 红队 Red Team 5.0 pts 战胜 黑队 Black Team 3.0 pts with the roster 刘北南 • 李扬 • 赵鲲 • 张纬 • Justin • 曾诚) right after the winners constant, and `get_pinned_outing_day_result_announcement()` returning `copy.deepcopy` of it right after the winners accessor; `get_display_announcements` and the render path are unchanged. The test module gains `import re` and the plan's four new tests.

- `uv run pytest tests/test_pinned_winners_announcement.py -v` (Phase 1 Verify): exit 0, 11 passed (7 existing, still expecting one pinned entry, plus 4 new).
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 002-pinned-outing-day-winner-announcement-re --phase 1`: exit 0, PASSED (scope all inside the targets, no frozen file touched, contract matches; pytest 16 passed, behave 17 scenarios passed).

**Deviations:**
- Added `import copy` at the top of `pages/1_📢_Announcements.py`. The plan asks for `return copy.deepcopy(PINNED_OUTING_DAY_RESULT_ANNOUNCEMENT)` and says to add the import "if the winners accessor uses `copy.deepcopy`"; the winners accessor uses `dict(...)` plus `list(tags)` instead, but `copy.deepcopy` cannot run without the import, so it stands. The winners accessor is unchanged.
