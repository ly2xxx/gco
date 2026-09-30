<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@770cc50 -->
## Summary
Adds a single new announcement to the Announcements page congratulating the 2026 individual season winners: 张纬 as 个人联赛 winner and 王文龙 as 个人杯赛 winner. It is a static, congratulatory club notice placed as the newest (topmost) entry; no existing announcement or other dashboard page changes.

## Behaviour
1. Given the `pages/1_📢_Announcements.py` module is imported, when the 2026 season-winners announcement is retrieved, then it exposes a `title` and a `body` that are both non-empty strings.
2. Given the 2026 season-winners announcement, when its title and body are concatenated into one text, then that text contains the exact string `张纬`.
3. Given the same concatenated text, when it is inspected, then it contains the exact string `个人联赛`.
4. Given the same concatenated text, when it is inspected, then it contains the exact string `王文龙`.
5. Given the same concatenated text, when it is inspected, then it contains the exact string `个人杯赛`.
6. Given the same concatenated text, when each winner is looked up, then the clause that names `张纬` also contains `个人联赛` and the clause that names `王文龙` also contains `个人杯赛`.
7. Given the same concatenated text, when it is inspected, then it contains the exact string `2026`.
8. Given the same concatenated text, when it is inspected, then it contains the congratulatory string `祝贺`.
9. Given the same concatenated text, when it is inspected, then it does not contain the string `张维` (the spelling used in existing scorecard filenames).
10. Given the page's announcement collection is enumerated, when the entries are listed in render order, then the 2026 season-winners announcement is the first element.
11. Given the page's announcement collection is enumerated, when it is compared against the pre-change collection, then every pre-existing entry is present exactly once with an identical title and body, and the collection length is exactly one greater than before.
12. Given the Announcements page is executed through `streamlit.testing.v1.AppTest` with no network access and with the data source unavailable, when the page renders, then the new announcement's title and body appear in the rendered markdown output.
13. Given the existing test suite, when it is run offline, then it passes unchanged.

## Interfaces

### `pages/1_📢_Announcements.py`

New module-level constant:

```python
SEASON_2026_WINNERS_ANNOUNCEMENT: dict[str, str]
# keys, both required, both non-empty:
#   "title": str  -> short congratulatory headline, may include "2026赛季"
#   "body":  str  -> Markdown body; must contain "2026", "祝贺", "张纬", "个人联赛",
#                    "王文龙", "个人杯赛"; must not contain "张维"
```

New module-level function:

```python
def get_season_2026_winners_announcement() -> dict[str, str]:
    """Return the 2026 individual season-winners announcement.

    Returns a dict with exactly the keys "title" and "body", both non-empty str.
    Pure: performs no Streamlit calls and no file, network, secret or file-system access.
    """
```

Changed existing module-level collection (keep whatever name the file already uses; the example name `ANNOUNCEMENTS` is illustrative only, do not rename existing symbols):

```python
ANNOUNCEMENTS: list[dict[str, str]]
# Change: SEASON_2026_WINNERS_ANNOUNCEMENT is prepended at index 0.
# No other element is added, removed, reordered or reworded.
```

No new render function is required: the existing per-entry render path on the page is reused unchanged.

### `test_streamlit_app.py`

New pytest tests, runnable offline (no network, no secrets, no manual steps):

```python
def test_announcements_page_includes_2026_season_winners() -> None: ...
def test_2026_season_winners_announcement_names_both_winners() -> None: ...
def test_2026_season_winners_announcement_is_newest_entry() -> None: ...
def test_existing_announcements_are_unchanged() -> None: ...
```

## Out of scope
- Verifying, recalculating or changing any standings, scores, rankings or leaderboards.
- Any change to the League, Cup, Events, Outing, API Data or overview pages.
- Scorecard images, photos, video or links to match records inside the announcement.
- Announcing team, outing or any other award not named in the intent.
- Translating the announcement or adding a language selector.
- Renaming or editing the existing `张维` scorecard filenames, or reconciling the two spellings anywhere outside this announcement.
- Changing, removing or re-wording any announcement that already exists on the page.
- Adding new dependencies, data sources, persistence or scheduled jobs.
- Adding a date, headline style or layout beyond what the existing per-entry render path already shows.

## Open questions
- The intent does not show the existing announcement entry shape. Assumption: entries are `dict[str, str]` mappings rendered from `title` and `body`, and the new entry uses exactly those same keys, adding no key (for example, no `date`) that existing entries do not already have.
- The exact `title` and `body` copy is not fixed by the intent beyond the two winners, their titles and the 2026 season. Assumption: implementation chooses the wording, constrained by criteria 2–9; no fact outside those is stated.
- The page's existing announcement collection name is not visible in the intent. Assumption: the existing name is kept as-is and the new entry is prepended; no symbol is renamed.
- The intent flags 张纬 versus the scorecard spelling 张维. Assumption: the announcement uses `张纬` exactly as given in the intent and all other files keep `张维`; this discrepancy is not resolved here.
- It is not stated whether the announcement should also be reachable outside the Announcements page. Assumption: it appears only on that page.
