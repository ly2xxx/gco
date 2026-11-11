<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@36ae97b -->
# Intent: League scorecard hole-by-hole verification table

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
League admins upload a photo of a paper scorecard and rely on auto-fill to populate the form, but the current read gives them only a summary figure they cannot cross-check against the image. Without seeing the par values and hole-by-hole scores that were actually read, an admin cannot spot a misread digit before saving, and a wrong score silently corrupts league standings that players and announcements depend on.

## Outcome
The league scorecard auto-fill reads the full card: the par for each of the 18 holes plus every player's hole-by-hole scores. Once the admin selects which player the card is for, the admin score form shows a verification table next to the uploaded image — holes 1-18 across the top, a Par row, the selected player's Score row, and Out/In/Total columns — so the read can be compared against the photo and corrected or rejected before Save. The work most likely belongs in `league_scorecard.py` with the admin form in `pages/3_🏆_League.py`.

## Done when
- The auto-fill read returns par values for holes 1-18 and hole-by-hole scores for each player on the card, not just a summary.
- After the admin picks the card player, a table appears on the score form alongside the uploaded scorecard image.
- The table has columns for holes 1-18 plus Out, In and Total, with a Par row and a Score row for the selected player.
- The table's Par and Score values match what the auto-fill read produced for that image, without the admin re-entering them.
- The image and the table are visible at the same time, before Save is pressed.
- The existing tests still pass.

## Not in scope
- Editing scores inside the verification table (corrections still happen in the existing form fields).
- Changes to what is saved, or to score storage and league standings calculations.
- Cup scorecards or any non-league scorecard flow.
- Re-processing or repairing scorecards that were already saved.
- Changes to how the image is uploaded, stored or displayed.

## Open questions
- **Which players appear in the table?** The idea names a Par row and a Score row, so the assumption is: all players' hole scores are read, but only the admin-selected player's scores are displayed.
- **Where par comes from.** Assumed the par row is read from the same uploaded card image, not from a course/par reference kept elsewhere.
- **Unreadable holes.** Assumed holes the read cannot determine are shown as empty rather than as zero, so a missing read looks different from a real score.
- **Layout specifics.** Assumed image and table sit side by side, with the table adjacent to the image, but the exact arrangement is left to the spec.
- **Read-only table.** Assumed the table is for checking only and does not itself change the saved values.
