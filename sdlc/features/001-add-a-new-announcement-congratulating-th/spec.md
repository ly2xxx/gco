<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@3b3e8ba -->
## Summary

The Announcements page gains a display-only, pinned 2026 season winners announcement that always appears as the first item, ahead of every stored announcement. It names 张纬 as the 2026 个人联赛 winner and 王文龙 as the 2026 个人杯赛 winner, and carries the same field set as stored announcements (id, title, date, author, pinned, body, tags) with `pinned` set to true. Stored announcements and the storage format are untouched.

## Behaviour

1. Given an empty stored announcements list, when the Announcements page builds its display list, then the display list contains exactly one announcement and it is the 2026 winners announcement.
2. Given a stored announcements list of N entries (N ≥ 0) that includes at least one entry with `pinned` true, when the Announcements page builds its display list, then the 2026 winners announcement is at index 0 and the N stored entries occupy indices 1..N in their original relative order.
3. Given the 2026 winners announcement object, when its keys are inspected, then it has exactly the keys `id`, `title`, `date`, `author`, `pinned`, `body`, `tags` and no others.
4. Given the 2026 winners announcement object, when its `pinned` value is read, then it is the boolean `True`.
5. Given the 2026 winners announcement object, when its `id` value is read, then it equals the constant string `"pinned-2026-season-winners"`, which differs from every id present in the stored announcements list.
6. Given the 2026 winners announcement object, when its `body` is read, then the body text contains `张纬` together with `个人联赛` and contains `王文龙` together with `个人杯赛`.
7. Given the 2026 winners announcement object, when its `title`, `date`, `author` and `tags` are read, then `title` is a non-empty string, `date` is a non-empty string, `author` is a non-empty string, `tags` is a list of strings, and `body` is a non-empty string.
8. Given any stored announcements list, when the Announcements page builds its display list, then the stored list object, its length, its entry order and every field of every stored entry are identical before and after the call.
9. Given a stored announcements list containing an entry whose `author`, `date` or `tags` value is missing/`None`/empty, when the Announcements page builds its display list, then the call still returns N+1 entries and that stored entry is passed through byte-for-byte unchanged.
10. Given no network access, no secrets and no data store configured, when the winners announcement is requested via its accessor, then it returns the same announcement object as any other call and no read of the stored announcements store occurs.
11. Given a stored announcements list, when the Announcements page is rendered, then the winners announcement's title and body are displayed above the stored announcements' titles and bodies.

## Interfaces

All additions belong in `pages/1_📢_Announcements.py`. No signature in `data.py` or any storage module changes.

```python
# pages/1_📢_Announcements.py

PINNED_2026_WINNERS_ANNOUNCEMENT_ID: str = "pinned-2026-season-winners"
"""Stable synthetic id for the display-only 2026 winners announcement."""

PINNED_2026_WINNERS_ANNOUNCEMENT: dict[str, Any] = {
    "id": PINNED_2026_WINNERS_ANNOUNCEMENT_ID,
    "title": "🎉 2026 赛季个人冠军公告",
    "date": "2026-09-15",
    "author": "GCO 组委会",
    "pinned": True,
    "body": "...",  # congratulatory notice naming 张纬 (个人联赛) and 王文龙 (个人杯赛)
    "tags": ["2026", "冠军"],
}
"""Display-only record; never written to or read from the saved announcements store."""


def get_pinned_winners_announcement() -> dict[str, Any]:
    """Return the 2026 season winners announcement record (a copy of the constant)."""


def get_display_announcements(stored_announcements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a new list with the pinned winners announcement first, followed by
    every stored announcement unchanged, in its original order."""
```

The existing render path in `pages/1_📢_Announcements.py` must obtain its items from `get_display_announcements(...)` rather than rendering the stored list directly, so that the pinned first position and the shared field set (including `pinned`) flow through the existing rendering code unchanged. The save/create/delete/import/export paths must continue to use the stored announcements list only; `get_display_announcements` is never their input.

`body` is a non-empty string, `date` is an ISO-8601 `YYYY-MM-DD` string, `tags` is a `list[str]`.

## Out of scope

- Verifying, recalculating or changing any standings, scores or leaderboards.
- Changes to the League, Cup, Events, Outing, API Data or other dashboard pages.
- Adding scorecard images, photos or links to match records in the announcement.
- Announcing team, outing or any other award not named in the intent.
- Translating the announcement into additional languages.
- Adding the winners announcement to the saved announcements list, or any persistence/export/import behaviour for it.
- Changing the stored announcement schema or storage format.
- Adding new styling, badges or layout behaviour to the announcement renderer.

## Open questions

- The intent spells the league winner `张纬` while scorecard filenames use `张维`. Assumption: the body uses `张纬` exactly as given; no alias, mapping or scorecard lookup is introduced.
- Title text is unspecified. Assumption: `🎉 2026 赛季个人冠军公告` as listed in Interfaces.
- Date is unspecified. Assumption: `2026-09-15`, the season end date stated in the README; the owner may correct it.
- Author is unspecified. Assumption: `GCO 组委会`, a club/system author independent of the logged-in user.
- Id format is unspecified. Assumption: the fixed literal `pinned-2026-season-winners`, which no stored announcement uses.
- Tags convention is unspecified. Assumption: `["2026", "冠军"]`; no other field derives from stored data.
- Exact body wording is unspecified. Assumption: a short congratulatory Chinese notice containing only the two winners, their honours and the 2026 season, with no additional facts.
- "First" placement is read as before every stored announcement including pinned stored ones. Assumption: yes, index 0 unconditionally.
