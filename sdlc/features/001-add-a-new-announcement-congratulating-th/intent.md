<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@af849bd -->
# Intent: 2026 Season Winners Announcement

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
Club members follow the 2026 season through the dashboard, but the final individual honours are not stated anywhere in it. Readers of the Announcements page currently have no place to see who won 个人联赛 and who won 个人杯赛 for 2026. This costs the winners their recognition and leaves members unsure of the season's official results.

## Outcome
The Announcements page carries a new announcement congratulating the 2026 个人联赛 winner 张纬 and the 2026 个人杯赛 winner 王文龙. The announcement reads as a congratulatory club notice and names both winners together with the title each one won. It most likely belongs in `pages/1_📢_Announcements.py`.

## Done when
- The Announcements page displays an announcement announcing the 2026 individual season winners.
- The announcement names 张纬 as the 个人联赛 winner and 王文龙 as the 个人杯赛 winner.
- The wording is congratulatory and clearly attributes both honours to the 2026 season.
- All announcements that already existed on the page remain visible and unchanged.
- The existing tests still pass.

## Not in scope
- Verifying, recalculating or changing any standings, scores or leaderboards.
- Changes to the League, Cup, Events or other dashboard pages.
- Adding scorecard images, photos or links to match records in the announcement.
- Announcing team, outing or any other award not named in the idea.
- Translating the announcement into additional languages.

## Open questions
- The idea spells the league winner as 张纬, while existing scorecard filenames for that player use 张维. Assumption: use the spelling exactly as given in the idea (张纬) and treat this as the display name until told otherwise.
- The idea does not say where on the page the announcement should sit or whether it carries a date. Assumption: add it as the newest entry at the top, following the format already used by existing announcements on that page.
- The idea does not mention any announcement title or headline text. Assumption: the later stages may choose a short congratulatory headline, without adding facts beyond the two winners and their titles.
- No existing intent document was provided, so this is a new intent rather than a revision and nothing from a prior version has been carried over.
