<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea,intent.md@cdc26e8 -->
# Intent: League admin score form shows the saved scorecard thumbnail and viewer

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
League admins entering scores in the league admin score form cannot tell from the form whether a photographed scorecard has already been saved for the tournament, game and player they are currently editing, nor inspect it at a readable size without leaving the form. They must browse the `scorecard_images/` folder themselves, which costs time and leads to mistyped scores when the wrong or an older card is consulted. When a card exists, seeing a thumbnail next to the inputs and being able to open it makes the entry verifiable at a glance.

## Outcome
While an admin has a tournament, game and player selected in the league admin score form, the form shows a thumbnail of that player's saved scorecard if one exists in `scorecard_images/`. The thumbnail is a small upright JPEG prepared in memory from the saved image with EXIF orientation applied and cached for reuse; the stored file is not changed. The match is by filename pattern `league_<tournament>_<Game_N>_<player>_<timestamp>.<ext>`, and when several files match, the newest timestamp is shown. When `GITHUB_REPO` is set, the thumbnail links to the original file on GitHub and opens in a new tab. A View button opens an upright version of the image in a dialog; images are not supplied as `data:` URLs. The page treats a selected "Game 5" as game number 5 when looking up saved filenames. When nothing matches, the form shows no image and behaves exactly as it does today. This belongs with the existing league scorecard logic in `league_scorecard.py`, surfaced on the league admin score form in `pages/3_🏆_League.py`.

## Done when
- With a tournament, game and player selected that have a matching saved scorecard, the form displays a small upright thumbnail; when more than one file matches, the thumbnail is the one with the newest timestamp in its filename.
- When `GITHUB_REPO` is set, the thumbnail links to the original file on GitHub and opens in a new tab.
- The View button opens an upright version of the image in a dialog, and no displayed scorecard image is supplied as a `data:` URL.
- Changing the selected tournament, game or player updates the thumbnail and dialog image to match, or removes them when nothing matches; no match or incomplete selection shows no thumbnail and no error, and selecting "Game 5" matches game 5 filenames.
- The existing tests still pass.

## Not in scope
- Uploading, replacing, deleting or rotating the stored scorecard image files.
- Reading scores out of the image or auto-filling the form from it.
- Cup, outing or other non-league scorecards.
- Showing scorecards anywhere other than the league admin score form (e.g. the player deep dive or the public leaderboard).
- Image conversion or resizing on disk, or any change to how scorecards are named or stored.
- `data:` URL image embedding or a fallback that puts image bytes directly into the page.
- Changing the GitHub repository layout or adding another image host.

## Open questions
- Does "selected" mean all three of tournament, game and player must be chosen before anything is shown? Assumed yes: with any of the three missing, nothing is shown.
- When `GITHUB_REPO` is not set, should the thumbnail itself still open a larger image? Assumed the View dialog is the in-app enlargement and the thumbnail has no separate enlarge action without `GITHUB_REPO`.
- Are non-JPEG saved scorecards (e.g. `.png`) in scope? Assumed yes; the thumbnail is produced as JPEG in memory, and the original file is untouched.
- What is the cache lifetime? Assumed the cached thumbnail is keyed by the matched scorecard and selection, reused while unchanged, and refreshed when the selection or file changes; eviction details are left to later stages.
- What counts as "newest" — file modification time or the timestamp in the filename? Assumed the timestamp segment in the filename, since that is what the pattern encodes.
- If two files for the same player and game share a timestamp, which one wins? Assumed an arbitrary but stable choice; not important enough to add a tie-break rule.
- What changed from the previous intent: the previous revision assumed thumbnails were not cached and said clicking the thumbnail opens the full-size image. This revision requires an in-memory upright JPEG thumbnail cached for reuse, replaces that click behaviour with a GitHub link when `GITHUB_REPO` is set plus a View dialog, forbids `data:` URLs, and records that the page supplies 5 for a "Game 5" selection.
