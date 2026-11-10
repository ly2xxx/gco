<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@1ca6622 -->
# Intent: League admin score form shows the saved scorecard

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
League admins entering scores in the league admin score form cannot tell from the form whether a photographed scorecard has already been saved for the tournament, game and player they are currently editing. They must leave the form and browse the `scorecard_images/` folder themselves, which costs time and leads to mistyped scores when the wrong or an older card is consulted. When a card exists, seeing it next to the inputs makes the entry verifiable at a glance.

## Outcome
While an admin has a tournament, game and player selected in the league admin score form, the form shows a thumbnail of that player's saved scorecard if one exists in `scorecard_images/`; clicking the thumbnail opens the full-size image. The match is by filename pattern `league_<tournament>_<Game_N>_<player>_<timestamp>.<ext>`, and when several files match, the newest timestamp is shown. When nothing matches, the form shows no image and behaves exactly as it does today. This belongs with the existing league scorecard logic in `league_scorecard.py`, surfaced on the league admin score form in `pages/3_🏆_League.py`.

## Done when
- With a tournament, game and player selected that have a matching saved scorecard, the form displays a thumbnail of that image.
- When more than one file matches, the thumbnail shown is the one with the newest timestamp in its filename.
- Clicking the thumbnail opens the full-size image.
- Changing the selected tournament, game or player updates the thumbnail to match, or removes it when nothing matches.
- When no file matches, or no player is selected yet, the form shows no thumbnail and no error.
- The existing tests still pass.

## Not in scope
- Uploading, replacing, deleting or rotating scorecard images.
- Reading scores out of the image or auto-filling the form from it.
- Cup, outing or other non-league scorecards.
- Showing scorecards anywhere other than the league admin score form (e.g. the player deep dive or the public leaderboard).
- Image conversion, resizing on disk, or any change to how scorecards are named or stored.

## Open questions
- Does "selected" mean all three of tournament, game and player must be chosen before anything is shown? Assumed yes: with any of the three missing, nothing is shown.
- Should thumbnails be cached or pre-generated? Assumed no: the existing image file is shown at thumbnail width, no new files are written.
- What counts as "newest" — file modification time or the timestamp in the filename? Assumed the timestamp segment in the filename, since that is what the pattern encodes.
- Are all extensions in the pattern (e.g. `.jpg`, `.png`) acceptable? Assumed yes, any extension, preferring the newest by the timestamp rule.
- If two files for the same player and game share a timestamp, which one wins? Assumed an arbitrary but stable choice; not important enough to add a tie-break rule.
- No existing intent document was supplied with this idea, so this is a fresh intent rather than a revision; if it supersedes an earlier version of this feature's intent, only the scorecard-thumbnail behaviour described above has changed.
