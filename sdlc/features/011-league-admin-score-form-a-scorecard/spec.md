<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@6580c0b -->
## Summary
Add an optional scorecard image picker above the existing League admin score form. A successful read populates only the date, venue, net, gross, stableford, and eagle/birdie/par/bogey/double-bogey-or-worse fields it can determine via `st.session_state`, while every other field keeps its prior value. No upload or any read failure leaves the form values as they are today, shows a non-blocking unavailable notice, and the existing Save path still uploads the selected image through `github_upload_image`.

## Behaviour
1. Given the League admin score form is rendered, when an admin views it, then a scorecard image picker appears above the date, venue, net, gross, stableford, eagle, birdie, par, bogey and double-bogey-or-worse fields, and the existing fields, defaults and Save button are otherwise unchanged.
2. Given no scorecard image is selected, when the League score form renders, then no extraction request is made, every field keeps its prior value (the existing round score when editing, otherwise the existing 72/36/0 defaults), and a non-blocking auto-fill-unavailable notice is shown.
3. Given a selected scorecard image, when auto-fill runs, then exactly one image-capable request is sent to `https://ollama.com/api/generate` using the existing configured model with a 120-second cap, and no retry is made.
4. Given `read_league_scorecard` returns a successful `ScorecardReadResult`, when `scorecard_field_updates` is applied, then `st.session_state` is updated only for the found target fields in `LEAGUE_SCORECARD_FIELD_KEYS`.
5. Given a successful extraction omits a target field or returns `None`, an empty string, a non-parseable value, or a value the extractor marks not found, when updates are selected, then that field is absent from the updates and keeps its prior value.
6. Given extraction returns a date and venue, when found fields are built, then date is expressed in the app's existing date format and venue is the closest existing venue name when one is close enough, otherwise the venue text as read.
7. Given an auto-filled target field, when the admin edits that field, then the widget displays the edited value and that edited value is in `st.session_state` before Save.
8. Given the admin edits any auto-filled or manually entered field, when Save succeeds, then the stored round contains the values visible on screen after correction, not the original extraction values.
9. Given a scorecard image is selected, when Save runs, then the image is uploaded through the existing `github_upload_image` call exactly once as part of the existing save path.
10. Given no scorecard image is selected, when Save runs, then the existing save path proceeds without a new `github_upload_image` call and without any extraction-related error.
11. Given `github_upload_image` fails during Save, when Save completes, then the League form's existing upload-failure behaviour is unchanged and auto-fill does not persist round values independently of Save.
12. Given a selected file is an unreadable image or an unsupported file type, when auto-fill is attempted, then no form field changes, a non-blocking auto-fill-unavailable notice is shown, and no exception leaves the League score form.
13. Given the Ollama generate request returns an error or a non-success response, when auto-fill is attempted, then no form field changes, a non-blocking auto-fill-unavailable notice is shown, and no exception leaves the League score form.
14. Given the Ollama generate request does not answer within 120 seconds, when the timeout elapses, then the request is treated as failed, no form field changes, a non-blocking auto-fill-unavailable notice is shown, and no exception leaves the League score form.
15. Given any auto-fill failure, when another page or player-facing view renders, then no error or notice from that failure is visible there.
16. Given a successful auto-fill, when the admin does not press Save, then no league round is created or updated and no extraction result is persisted outside `st.session_state`.
17. Given one scorecard image is selected, when auto-fill runs, then only one player's round fields are populated and no batch or multi-player extraction is attempted.
18. Given an auto-fill failure, when no new scorecard image is selected, then no automatic retry, cache or queued extraction is started.
19. Given the existing repository test suite, when it is run, then all existing tests pass.

## Interfaces

File: `pages/3_🏆_League.py`

```python
ScorecardFieldValue = str | int

LEAGUE_SCORECARD_FIELD_KEYS: tuple[str, ...] = (
    "date",
    "venue",
    "net",
    "gross",
    "stableford",
    "eagles",
    "birdies",
    "pars",
    "bogeys",
    "double_bogeys_or_worse",
)

@dataclass(frozen=True)
class ScorecardReadResult:
    found_fields: dict[str, ScorecardFieldValue]
    unavailable_reason: str | None = None


def read_league_scorecard(
    image_bytes: bytes,
    mime_type: str | None,
    *,
    timeout_seconds: float = 120.0,
) -> ScorecardReadResult:
    ...


def scorecard_field_updates(
    extracted_fields: Mapping[str, object],
) -> dict[str, ScorecardFieldValue]:
    ...
```

- `read_league_scorecard` sends the image to the Ollama Cloud image-capable generate endpoint, uses the model from existing app configuration/secrets (`glm-5.3-flash:cloud`) without adding a model picker, and returns only fields the extractor considers found.
- `scorecard_field_updates` filters extracted values to the target fields in `LEAGUE_SCORECARD_FIELD_KEYS`, drops missing/empty/non-parseable/not-found values, and returns only the key/value updates the page may write to `st.session_state`.
- No signature change is made to the existing `github_upload_image`; the existing save path continues to call it.

## Out of scope
- The Cup and Outing score forms, or any page other than the League admin score form.
- Batch or multi-player extraction from a single card, and extracting multiple cards in one upload.
- Changing `github_upload_image`, the save path, or where the uploaded image is stored.
- Linking extracted data into backup/export payloads or into league statistics beyond the round being entered.
- Auto-submitting a round, or saving extraction results without the admin pressing Save.
- Changing league scoring rules, field definitions, or the existing statistics and AI summary features.
- Retrying, caching, or queuing failed extractions.

## Open questions
- Which fields the 72/36/0 fallback maps to: assumed these are today's form defaults and are left untouched, so no mapping is defined here.
- What "found fields only" means for an empty or implausible value: assumed empty, missing, null, non-parseable and low-confidence values are treated as not found and the field keeps its prior value.
- Mixed Chinese/English handwritten cards: assumed both are attempted, and any value the vision model is not confident of is treated as not found.
- Venue and date are free text: assumed the extracted date is normalised to the app's existing date format and the venue is matched to an existing venue name where one is close enough, otherwise kept as read.
- Whether one upload serves one player's card only: assumed one card image per player per round.
- Which model is called: assumed the model comes from existing app configuration/secrets as before (`glm-5.3-flash:cloud`) and is not changed here.
- Trigger and retry behaviour: assumed selecting a scorecard image triggers at most one read attempt, with no automatic retry, cache or queue.
- No-upload notice: assumed "the admin is told auto-fill was unavailable" is a non-blocking informational notice near the picker, not an error state.
