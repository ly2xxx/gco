<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@d8bc04e -->
# Intent: League score form scorecard auto-fill

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
League admins record each player's round in the league score form by reading numbers off a photographed physical scorecard and retyping them. Doing this for every player in every game is slow, and transcription mistakes silently distort the standings and the season summaries built on top of them. The photos already exist (they are filed under `scorecard_images/`), so the information is available — it just has to be re-entered by hand.

## Outcome
The League admin score form accepts a scorecard image (JPG or PNG) in a upload area above the form. When extraction succeeds, the round's date, venue, net, gross, stableford and the eagle/birdie/par/bogey/double-bogey-or-worse counts arrive pre-filled for the admin to review; nothing is saved without their confirmation and every pre-filled value remains manually editable. When extraction cannot be done — no upload, unreadable image, unsupported file, or the Ollama Cloud vision service failing for any reason — the form behaves exactly as it does today and the admin simply types the values in. This belongs in `pages/3_🏆_League.py`, where the league score entry form lives.

## Done when
- The League score form shows a JPG/PNG scorecard upload control above the form fields.
- Uploading a readable scorecard fills in date, venue, net, gross, stableford, and each eagle/birdie/par/bogey/double-bogey count for a card that contains them, without the admin retyping them.
- Pre-filled values stay editable, and saving stores what the admin sees on screen after any corrections.
- If there is no upload, the image is unreadable, the file type is unsupported, or the vision service errors or times out, the form still renders with empty manual entry fields, the admin is told auto-fill was unavailable, and no error is shown to players or other pages.
- Any field the extraction could not determine is left blank for manual entry rather than guessed or defaulted.
- The existing tests still pass.

## Not in scope
- The Cup and Outing score forms, or any page other than the League admin score form.
- Batch or multi-player extraction from a single card, and extracting multiple cards in one upload.
- Storing, archiving or linking the uploaded image to the saved round, or adding extracted data to the backup/export payloads.
- Auto-submitting a round, or saving extraction results without admin review.
- Changing league scoring rules, field definitions, or the existing statistics and AI summary features.
- Retrying, caching, or queuing failed extractions.

## Open questions
- Which counts "eagle..double-bogey" covers: assumed the counts already tracked for league stats (eagle, birdie, par, bogey, double bogey, and worse), nothing new.
- Scorecards are photographed in mixed Chinese/English and often handwritten: assumed both are attempted, and any value the vision model is not confident of is left blank rather than filled.
- Venue and date are free text on the card: assumed the extracted date is normalised to the app's existing date format and the venue is matched to an existing venue name where one is close enough, otherwise kept as read.
- Whether one upload serves one player's card only: assumed one card per player per round, matching how the photos are filed.
- Where the Ollama Cloud credentials/model name come from: assumed existing app configuration/secrets, with the model `glm-5.3-flash:cloud` as stated.
- **Changed from previous version:** this is the first intent for this feature, so nothing was carried over or altered.
