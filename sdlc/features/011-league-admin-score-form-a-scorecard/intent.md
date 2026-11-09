<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea,intent.md@49d4c06 -->
# Intent: League score form scorecard auto-fill

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
League admins record each player's round in the league score form by reading numbers off a photographed physical scorecard and retyping them. Doing this for every player in every game is slow, and transcription mistakes silently distort the standings and the season summaries built on top of them. The photos already exist (they are filed under `scorecard_images/` and already uploaded on save), so the information is available — it just has to be re-entered by hand.

## Outcome
The League admin score form keeps exactly the shape it has today: the same fields, the same defaults, and a Save that still uploads the selected scorecard image via `github_upload_image`. Added to it is a scorecard picker above the form. When a read succeeds, only the fields the service could actually determine — date, venue, net, gross, stableford, and the eagle/birdie/par/bogey/double-bogey-or-worse counts — are populated through `st.session_state`, so anything not found keeps the value the form already had; every populated value stays editable and nothing is saved without the admin's Save. When there is no upload, or the read fails for any reason (unreadable image, unsupported file, service error, or no answer within 120 seconds), the form is left exactly as it is today — the existing score if one is being edited, otherwise 72/36/0 — and the admin simply types the numbers in. Reads go to the Ollama Cloud image-capable generate endpoint (`ollama.com/api/generate`, with image input, 120-second cap). This belongs in `pages/3_🏆_League.py`, where the league score entry form lives.

## Done when
- The League score form shows a scorecard image picker above its fields and is otherwise unchanged in layout, fields and defaults.
- Reading a scorecard fills only the date, venue, net, gross, stableford and eagle/birdie/par/bogey/double-bogey-or-worse fields the service reports as found, and leaves every other field holding the value it already had (existing score when editing, otherwise the current default).
- Pre-filled values remain editable, and saving stores what the admin sees on screen after any corrections.
- Saving still uploads the scorecard image via `github_upload_image`, and a save with no image or a failed upload behaves as it does today.
- With no upload, an unreadable image, an unsupported file type, a service error, or no response within 120 seconds, the form renders with its existing values (the round's current score if editing, else 72/36/0), the admin is told auto-fill was unavailable, and no error surfaces to players or other pages.
- The existing tests still pass.

## Not in scope
- The Cup and Outing score forms, or any page other than the League admin score form.
- Batch or multi-player extraction from a single card, and extracting multiple cards in one upload.
- Changing `github_upload_image`, the save path, or where the uploaded image is stored — the existing upload-on-save behaviour is kept as-is.
- Linking extracted data into the backup/export payloads or into league statistics beyond the round being entered.
- Auto-submitting a round, or saving extraction results without the admin pressing Save.
- Changing league scoring rules, field definitions, or the existing statistics and AI summary features.
- Retrying, caching, or queuing failed extractions.

## Open questions
- Which fields the 72/36/0 fallback maps to: assumed these are today's form defaults and are kept untouched, so no mapping is decided here.
- What "found fields only" means for a field the model returns empty or implausible: assumed empty/unreadable values are treated as not found and the field keeps its prior value, never a guess.
- Scorecards are photographed in mixed Chinese/English and often handwritten: assumed both are attempted, and any value the vision model is not confident of is treated as not found.
- Venue and date are free text on the card: assumed the extracted date is normalised to the app's existing date format and the venue is matched to an existing venue name where one is close enough, otherwise kept as read.
- Whether one upload serves one player's card only: assumed one card per player per round, matching how the photos are filed.
- Which model is called: the idea now fixes the endpoint (`ollama.com/api/generate`), image input and a 120-second limit but names no model; assumed the model comes from existing app configuration/secrets as before (`glm-5.3-flash:cloud`) and is not changed here.
- **Changed from previous version:** the outcome no longer leaves the uploaded image unlinked — saving still uploads the scorecard via `github_upload_image`, and that was removed from Not in scope; the failure/no-upload path no longer blanks the form but keeps today's values (existing score, otherwise 72/36/0); a successful read now writes only the found fields through `st.session_state`; and the Ollama Cloud generate endpoint, image input and 120-second limit are now stated. Everything else — problem, page, upload location, editability, one-card-per-round, out-of-scope features — is carried over unchanged.
