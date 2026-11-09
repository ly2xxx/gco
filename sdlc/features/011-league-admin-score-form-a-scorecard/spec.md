<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@06faf94 -->
## Summary
The League admin score form in `pages/3_🏆_League.py` gains an optional JPG/PNG scorecard upload above its fields. When Ollama Cloud vision extraction succeeds, the round date, venue, net, gross, stableford and eagle/birdie/par/bogey/double-bogey-or-worse counts are pre-filled as editable defaults for admin review. On missing, unsupported, unreadable, errored or timed-out extraction, the form falls back to today's manual entry with a non-blocking notice and no error outside the League form.

## Behaviour
1. Given the League admin opens the League score form, when the form renders, then a scorecard upload control accepting JPG/JPEG/PNG files appears above the score fields.
2. Given one readable JPG or PNG scorecard for the current player's round is uploaded, when extraction succeeds, then the date, venue, net, gross, stableford, and eagle/birdie/par/bogey/double-bogey-or-worse count fields are pre-filled with the extracted values without the admin retyping them.
3. Given one scorecard is uploaded, when extraction succeeds, then only the current player's League round form is pre-filled and no other player's round is changed.
4. Given extraction succeeds with only some supported fields present or confident, when the form is pre-filled, then each missing or uncertain field is left blank for manual entry.
5. Given a field has been pre-filled, when the admin edits that field, then the form accepts and displays the edited value.
6. Given pre-filled values have been edited, when the admin triggers the existing save action, then the saved round stores the values currently displayed in the form.
7. Given extraction succeeds, when extraction completes, then no round is saved until the admin triggers the existing save action.
8. Given no scorecard is uploaded, when the League score form renders, then the score fields are empty and editable and a non-blocking status tells the admin that auto-fill is unavailable until a JPG/PNG scorecard is uploaded.
9. Given an uploaded file's MIME type or extension is not JPG/JPEG/PNG, when the upload is processed, then the form keeps empty manual-entry fields and shows a non-blocking auto-fill-unavailable notice.
10. Given uploaded image bytes are empty or the image is unreadable as a scorecard, when extraction is attempted, then the form keeps empty manual-entry fields and shows a non-blocking auto-fill-unavailable notice.
11. Given the Ollama Cloud vision service raises any error, times out, or returns malformed output, when extraction is attempted, then no exception escapes to the page and the form keeps empty manual-entry fields with a non-blocking auto-fill-unavailable notice.
12. Given extraction fails for any reason, when any player-facing view or other page renders, then no scorecard auto-fill error or warning is shown there.
13. Given extracted date text is parseable, when form defaults are built, then the date is normalised to `YYYY-MM-DD`.
14. Given extracted venue text matches a known venue after trimming surrounding whitespace and ignoring case, when form defaults are built, then the known venue spelling is used; otherwise the extracted venue text is kept.
15. Given the existing automated test suite, when it is run after the change, then all pre-existing tests pass.

## Interfaces
Add a new module `scorecard_extraction.py`:

```python
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TypeAlias

VisionExtractor: TypeAlias = Callable[[bytes, str], Mapping[str, object]]

@dataclass(frozen=True)
class ScorecardDraft:
    date: str | None = None
    venue: str | None = None
    net: int | None = None
    gross: int | None = None
    stableford: int | None = None
    eagle_count: int | None = None
    birdie_count: int | None = None
    par_count: int | None = None
    bogey_count: int | None = None
    double_bogey_or_worse_count: int | None = None

def extract_scorecard_fields(
    image_bytes: bytes | None,
    mime_type: str | None,
    *,
    vision_extractor: VisionExtractor | None = None,
) -> ScorecardDraft | None: ...

def normalise_scorecard_date(raw_date: str | None) -> str | None: ...

def match_scorecard_venue(
    raw_venue: str | None,
    known_venues: Sequence[str],
) -> str | None: ...
```

`extract_scorecard_fields` returns `None` for no upload, unsupported MIME type, empty or unreadable image bytes, any vision-service error/timeout, or malformed vision output. It returns a `ScorecardDraft` on successful extraction, using `None` for any field the extractor did not confidently determine. The default `vision_extractor` uses the existing Ollama Cloud configuration and model `glm-5.3-flash:cloud`; tests inject a fake extractor.

Add this UI helper in `pages/3_🏆_League.py`:

```python
def render_league_scorecard_upload(
    known_venues: Sequence[str],
    *,
    key: str = "league_scorecard_upload",
    vision_extractor: VisionExtractor | None = None,
) -> ScorecardDraft | None: ...
```

It renders the JPG/JPEG/PNG upload control above the League score form, renders the non-blocking auto-fill status, calls `extract_scorecard_fields`, normalises the date with `normalise_scorecard_date`, matches the venue with `match_scorecard_venue`, and returns the resulting draft for the existing form to use as editable widget defaults. It returns `None` when no upload exists or extraction fails.

No changes are needed to the public interfaces in `data.py`, `ai_summary.py`, or the Cup/Outing page files.

## Out of scope
- The Cup and Outing score forms, or any page other than the League admin score form.
- Batch or multi-player extraction from a single card, and extracting multiple cards from one upload.
- Storing, archiving or linking the uploaded image to the saved round, or adding extracted data to backup/export payloads.
- Auto-submitting a round, or saving extraction results without admin review.
- Changing league scoring rules, field definitions, or the existing statistics and AI summary features.
- Retrying, caching, or queuing failed extractions.
- Fuzzy venue matching beyond trimming whitespace and ignoring case.
- Any network access, secrets or manual steps in automated tests.

## Open questions
- Date format: assumed the League form's existing format is `YYYY-MM-DD`; extracted parseable dates are normalised to that format and unparseable dates remain blank.
- Venue "close enough": assumed case-insensitive, whitespace-trimmed exact matching against existing venue names; no fuzzy matching is added.
- Count fields: assumed the existing tracked counts are eagle, birdie, par, bogey, and double-bogey-or-worse; no new statistics or field definitions are added.
- No-upload notice: assumed a non-blocking status on the League form is acceptable and does not change the form's manual-entry behavior or appear on other pages.
- Admin confirmation: assumed the existing save action is the confirmation step; no new confirmation dialog or auto-save is added.
- Ollama Cloud configuration: assumed credentials and non-model configuration come from the existing app configuration/secrets, with model `glm-5.3-flash:cloud`.
- Mixed Chinese/English handwritten cards: assumed extraction attempts both; any value the extractor does not confidently return is represented as `None` and left blank.
