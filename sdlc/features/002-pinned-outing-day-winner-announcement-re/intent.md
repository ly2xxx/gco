<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@bd52450 -->
# Intent: Pin Outing Day 对抗赛 Winner Announcement

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
Members and visitors reading the Announcements page currently see the pinned 2026 winners announcement but not the result of the Outing Day 对抗赛. That leaves a completed club event unrecorded where members look for news, and forces anyone wanting the result to ask around or dig through other sources.

## Outcome
The Announcements page in `pages/1_📢_Announcements.py` displays a pinned, display-only announcement for the Outing Day 对抗赛 result: 红队 Red Team 5.0 pts defeated 黑队 Black Team 3.0 pts, with the Red Team roster (刘北南 • 李扬 • 赵鲲 • 张纬 • Justin • 曾诚). It follows the same presentation pattern as the existing 2026 winners announcement and is delivered as the second item from `get_display_announcements()`, so it appears in the page's announcement flow without requiring data entry, scoring logic, or manual editing by viewers. The announcement is fixed content, not generated from tournament state.

## Done when
- `pages/1_📢_Announcements.py` renders an Outing Day 对抗赛 pinned announcement showing 红队 Red Team at 5.0 pts and 黑队 Black Team at 3.0 pts.
- The announcement lists the Red Team roster exactly as 刘北南 • 李扬 • 赵鲲 • 张纬 • Justin • 曾诚.
- `get_display_announcements()` returns the Outing Day 对抗赛 announcement as the second item, after the existing 2026 winners announcement.
- The announcement is display-only: no scoring, editing, persistence, or tournament-state calculation is introduced to produce it.
- Tests in `tests/test_pinned_winners_announcement.py` are updated to cover the new second announcement and its content.
- The existing tests still pass.

## Not in scope
- Calculating or validating the Outing Day 对抗赛 scores from match data.
- Adding or changing data models, Google Sheets fields, or persistence for team match results.
- Making announcements editable, configurable, or dynamically generated.
- Changing the existing 2026 winners announcement beyond what is needed to keep it first.
- Other pages, tournament standings, or the Team Match feature.
- Adding images, scorecards, or new assets for this announcement.

## Open questions
- The exact title, date, and wording of the announcement are not specified. Assumption: follow the existing 2026 winners announcement's phrasing and layout, with the result and roster as given in the idea.
- Whether the announcement is pinned visually (for example, an emoji or badge) is not stated. Assumption: match the existing pinned 2026 winners announcement's treatment.
- Whether the Red Team roster order matters is not stated. Assumption: preserve the order in the idea.
- Whether "second via `get_display_announcements()`" means second overall or second among pinned announcements is not stated. Assumption: second overall in the list returned by `get_display_announcements()`, immediately after the 2026 winners announcement.
