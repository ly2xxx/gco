<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea,intent.md@f020d98 -->
# Intent: Pinned 2026 Season Winners Announcement

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
Club members follow the 2026 season through the dashboard, but the final individual honours are not stated anywhere in it. Readers of the Announcements page currently have no place to see who won 个人联赛 and who won 个人杯赛 for 2026. This costs the winners their recognition and leaves members unsure of the season's official results.

## Outcome
The Announcements page carries a pinned 2026 winners announcement at the top, before any stored announcements. It reads as a congratulatory club notice and names 张纬 as the 2026 个人联赛 winner and 王文龙 as the 2026 个人杯赛 winner. The announcement exposes the same fields as stored announcements: id, title, date, author, pinned, body, tags, with pinned true. It remains display-only: it is not added to the saved announcements list and does not change stored announcements. It most likely belongs in `pages/1_📢_Announcements.py`.

## Done when
- The Announcements page displays the 2026 winners announcement as the first announcement, before all stored announcements.
- The announcement names 张纬 as the 2026 个人联赛 winner and 王文龙 as the 2026 个人杯赛 winner.
- The announcement exposes the same fields as stored announcements: id, title, date, author, pinned, body, tags, with pinned true.
- The announcement is not present in the saved announcements list and does not modify saved announcements.
- All announcements that already existed remain visible and unchanged.
- The existing tests still pass.

## Not in scope
- Verifying, recalculating or changing any standings, scores or leaderboards.
- Changes to the League, Cup, Events or other dashboard pages.
- Adding scorecard images, photos or links to match records in the announcement.
- Announcing team, outing or any other award not named in the idea.
- Translating the announcement into additional languages.
- Adding the winners announcement to the saved announcements list or any persistence/export/import behavior.
- Changing the stored announcement schema or storage format.

## Open questions
- The idea spells the league winner as 张纬, while existing scorecard filenames for that player use 张维. Assumption: use the spelling exactly as given in the idea (张纬) and treat this as the display name until told otherwise.
- The idea does not specify the announcement title text. Assumption: later stages may choose a short congratulatory title without adding facts beyond the two winners and their honours.
- The idea does not specify the announcement date. Assumption: use a date appropriate to the 2026 season winners announcement; the owner can correct the exact date.
- The idea does not specify the announcement author. Assumption: use a club/system author or the Announcements page's existing default.
- The idea does not specify the announcement id. Assumption: use a stable synthetic id that will not collide with stored announcement ids.
- The idea does not specify tags. Assumption: use tags consistent with 2026 winners/announcements, or leave them empty if no convention exists.
- The idea does not specify body wording beyond the two winners and their honours. Assumption: later stages write a congratulatory body using only those facts.
- "First" is read as before all stored announcements, including any stored announcements that are pinned. Assumption: yes.
- Revision note: the prior intent said to add the announcement as the newest entry at the top following the existing announcement format. This idea changes that to: pinned, first on the page, with the same fields as stored announcements (id, title, date, author, pinned, body, tags), and not added to the saved announcements list. The prior position/date assumption is superseded.
