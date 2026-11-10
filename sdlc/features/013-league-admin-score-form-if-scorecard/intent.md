<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea,intent.md@3c15a7b -->
# Intent: League admin score form shows the saved scorecard thumbnail and viewer

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
League admins entering scores in the league admin score form cannot tell from the form whether a photographed scorecard has already been saved for the tournament, game and player they are currently editing, nor inspect it at a readable size without leaving the form. They must browse the `scorecard_images/` folder themselves, which costs time and leads to mistyped scores when the wrong or an older card is consulted. When a card exists, seeing a thumbnail next to the inputs and being able to open it makes the entry verifiable at a glance.

## Outcome
While an admin has a tournament, game and player selected in the league admin score form, the form shows a thumbnail of that player's saved scorecard if one exists in `scorecard_images/`. The thumbnail is the saved file itself, shown as-is at a small fixed width of 160 pixels, with no rotation, conversion, or caching. The match is by filename pattern `league_<tournament>_<Game_N>_<player>_<timestamp>.<ext>`, and when several files match, the newest timestamp is shown. When `GITHUB_REPO` is set, the thumbnail links to `raw.githubusercontent.com/<repo>/HEAD/scorecard_images/<file>` and opens in a new tab. A View button opens a dialog showing the same saved file as-is. The page treats a selected "Game 5" as game number 5 when looking up saved filenames. When nothing matches, the form shows no image and behaves exactly as it does today. This belongs with the existing league scorecard logic in `league_scorecard.py`, surfaced on the league admin score form in `pages/3_🏆_League.py`.

## Done when
- With a tournament, game and player selected that have a matching saved scorecard, the form displays the saved file as-is at 160 pixels wide; when more than one file matches, the thumbnail is the one with the newest timestamp in its filename.
- The thumbnail and View dialog show the saved file without rotation or EXIF orientation handling, and no cached thumbnail is used.
- When `GITHUB_REPO` is set, the thumbnail links to `raw.githubusercontent.com/<repo>/HEAD/scorecard_images/<file>` and opens in a new tab.
- The View button opens a dialog showing the same saved file as-is, and no displayed scorecard image is supplied as a `data:` URL.
- Changing the selected tournament, game or player updates the thumbnail and dialog image to match, or removes them when nothing matches; no match or incomplete selection shows no thumbnail and no error, and selecting "Game 5" matches game 5 filenames.
- The existing tests still pass.

## Not in scope
- Uploading, replacing, deleting or rotating the stored scorecard image files.
- Applying EXIF orientation, rotating, converting, or resizing scorecard images for display.
- Pillow-based image processing, generated thumbnail images, or caching of scorecard images.
- Reading scores out of the image or auto-filling the form from it.
- Cup, outing or other non-league scorecards.
- Showing scorecards anywhere other than the league admin score form (e.g. the player deep dive or the public leaderboard).
- Any change to how scorecards are named or stored.
- `data:` URL image embedding or a fallback that puts image bytes directly into the page.
- Changing the GitHub repository layout or adding another image host.

## Open questions
- Does "no rotation" also mean ignoring EXIF orientation entirely, even when a photo would appear sideways? Assumed yes: the saved file is shown as stored.
- Does "no cache" rule out any in-memory or session-level cached copy? Assumed yes: no cached thumbnail is kept or reused; the saved file is read when it is shown.
- Does the 160-pixel width apply to the View dialog as well? Assumed no: the thumbnail is 160 pixels wide, and the dialog shows the saved file as-is.
- Are non-JPEG saved scorecards (e.g. `.png`) in scope? Assumed yes; any saved file the page can display is shown as-is, with no conversion.
- Does "selected" mean all three of tournament, game and player must be chosen before anything is shown? Assumed yes: with any of the three missing, nothing is shown.
- When `GITHUB_REPO` is not set, should the thumbnail itself still open a larger image? Assumed the View dialog is the in-app enlargement and the thumbnail has no separate enlarge action without `GITHUB_REPO`.
- What counts as "newest" — file modification time or the timestamp in the filename? Assumed the timestamp segment in the filename, since that is what the pattern encodes.
- If two files for the same player and game share a timestamp, which one wins? Assumed an arbitrary but stable choice; not important enough to add a tie-break rule.
- What changed from the previous intent: the previous revision required an in-memory upright JPEG thumbnail with EXIF orientation applied and cached for reuse. This revision removes rotation, Pillow-based processing and caching; the thumbnail is the saved file shown as-is at 160 pixels wide, the View dialog shows the same saved file as-is, and the `GITHUB_REPO` link now points explicitly to `raw.githubusercontent.com/<repo>/HEAD/scorecard_images/<file>`.
