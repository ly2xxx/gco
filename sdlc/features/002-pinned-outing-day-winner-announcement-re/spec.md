<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@eb319e6 -->
## Summary

The Announcements page gains a second pinned, display-only announcement recording the Outing Day 对抗赛 result (红队 Red Team 5.0 pts over 黑队 Black Team 3.0 pts, with the Red Team roster), so members and visitors see the completed club event where they already look for news. `get_display_announcements()` now returns that announcement as the second item, directly after the existing 2026 winners announcement, and the pinned-announcement test module is updated to cover it.

## Behaviour

1. Given the page module `pages/1_📢_Announcements.py` is imported, when `get_pinned_outing_day_result_announcement()` is called, then it returns a `dict` whose key set is exactly `{"id", "title", "date", "author", "pinned", "body", "tags"}`.
2. Given `get_pinned_outing_day_result_announcement()` has been called, when the returned announcement's `id` is inspected, then it is exactly `"pinned-2026-outing-day-result"`.
3. Given `get_pinned_outing_day_result_announcement()` has been called, when the returned announcement's `pinned` field is inspected, then it is `True`.
4. Given `get_pinned_outing_day_result_announcement()` has been called, when the returned announcement's `title` is inspected, then it is a non-empty string containing both `"Outing Day"` and `"对抗赛"`.
5. Given `get_pinned_outing_day_result_announcement()` has been called, when the returned announcement's `date` is inspected, then it is a non-empty string matching `YYYY-MM-DD`.
6. Given `get_pinned_outing_day_result_announcement()` has been called, when the returned announcement's `author` is inspected, then it is a non-empty string.
7. Given `get_pinned_outing_day_result_announcement()` has been called, when the returned announcement's `tags` is inspected, then it is a `list` in which every element is a `str`.
8. Given `get_pinned_outing_day_result_announcement()` has been called, when the returned announcement's `body` is inspected, then it contains the substring `"红队 Red Team"` and the substring `"5.0 pts"`.
9. Given `get_pinned_outing_day_result_announcement()` has been called, when the returned announcement's `body` is inspected, then it contains the substring `"黑队 Black Team"` and the substring `"3.0 pts"`.
10. Given `get_pinned_outing_day_result_announcement()` has been called, when the returned announcement's `body` is inspected, then it contains the substring `"刘北南 • 李扬 • 赵鲲 • 张纬 • Justin • 曾诚"` with those `" • "` separators and that name order.
11. Given two separate calls to `get_pinned_outing_day_result_announcement()`, when the results are compared, then they are equal but not the same object, and appending to the first result's `tags` leaves both `PINNED_OUTING_DAY_RESULT_ANNOUNCEMENT["tags"]` and the next call's `tags` unchanged.
12. Given the stored-announcements store is patched to raise on read, when `get_pinned_outing_day_result_announcement()` is called, then the announcement is returned without the store being read.
13. Given an empty stored-announcements list, when `get_display_announcements([])` is called, then the result has exactly two items: index 0 equals `get_pinned_winners_announcement()` and index 1 equals `get_pinned_outing_day_result_announcement()`.
14. Given a stored list containing both pinned and unpinned announcements, when `get_display_announcements(stored)` is called, then the result's `id` values are `["pinned-2026-season-winners", "pinned-2026-outing-day-result"]` followed by the stored announcements' ids in their original order.
15. Given a stored list, when `get_display_announcements(stored)` is called, then the input list and its dicts are unchanged, and every stored dict in the result is the same object as in the input (no copying).
16. Given a stored announcement with missing data (`date` is `None`, `author` is `None`, `tags` is `None`), when `get_display_announcements(stored)` is called, then that dict is returned unchanged and by identity, at its original relative position after the two pinned announcements.
17. Given the page module is executed to render with a non-empty stored list, when the recorded Streamlit call log is inspected, then the outing announcement's `title` text and its score and roster text appear in the log after the winners announcement text and before any stored announcement text.
18. Given the page module is executed to render, when the recorded Streamlit call log is inspected, then `data.save_announcements` is never called.
19. Given `tests/test_pinned_winners_announcement.py` is run with no network access, secrets, or manual steps, when the suite completes, then all tests pass, including a test asserting the two-pinned ordering of `get_display_announcements([])` and a test asserting the outing announcement's scores and roster.

## Interfaces

### `pages/1_📢_Announcements.py`

New module-level constant (same shape as the existing `PINNED_2026_WINNERS_ANNOUNCEMENT: dict[str, Any]`):

```python
PINNED_OUTING_DAY_RESULT_ANNOUNCEMENT: dict[str, Any]
```

Required key/value contract:

| key      | type        | required value                                                            |
| -------- | ----------- | ------------------------------------------------------------------------- |
| `id`     | `str`       | `"pinned-2026-outing-day-result"`                                          |
| `title`  | `str`       | non-empty; contains `"Outing Day"` and `"对抗赛"`                          |
| `date`   | `str`       | non-empty; `YYYY-MM-DD`                                                    |
| `author` | `str`       | non-empty                                                                  |
| `pinned` | `bool`      | `True`                                                                     |
| `body`   | `str`       | contains the score lines and the roster line shown below                   |
| `tags`   | `list[str]` | every element a `str`                                                      |

Required `body` content (substrings are what tests assert; surrounding layout may follow the existing winners announcement):

```
🏌️ Outing Day 对抗赛结果

红队 Red Team 5.0 pts 战胜 黑队 Black Team 3.0 pts
红队阵容：刘北南 • 李扬 • 赵鲲 • 张纬 • Justin • 曾诚
```

New function, no parameters:

```python
def get_pinned_outing_day_result_announcement() -> dict[str, Any]:
    """Return a fresh deep copy of PINNED_OUTING_DAY_RESULT_ANNOUNCEMENT."""
```

Changed function — signature is unchanged (one positional parameter, no new parameters, same return type); only the returned list changes:

```python
def get_display_announcements(announcements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return [pinned winners announcement, pinned outing day result announcement, *announcements]."""
```

Unchanged in this file:

```python
PINNED_2026_WINNERS_ANNOUNCEMENT: dict[str, Any]   # value unchanged
def get_pinned_winners_announcement() -> dict[str, Any]: ...   # unchanged
```

The page render path is unchanged: it iterates the list returned by `get_display_announcements(...)` and renders each announcement with the existing rendering calls. No new branch, badge, constant-to-route mapping, or page-level state is introduced.

### `tests/test_pinned_winners_announcement.py`

Updated, not replaced:

- `test_get_display_announcements_empty` changes from expecting a single pinned item to expecting exactly the two pinned announcements in order.
- `test_get_display_announcements_pins_first_before_stored` and `test_page_renders_pinned_winners_before_stored` are extended to expect the outing announcement second and to assert its rendered title, scores, and roster.
- New tests cover: the outing announcement's key set and field values, fresh-copy semantics of `get_pinned_outing_day_result_announcement()`, and no store read/`save_announcements` call.
- No new test files are added.

## Out of scope

- Calculating or validating the Outing Day 对抗赛 scores from match data.
- Adding or changing data models, Google Sheets fields, or persistence for team match results.
- Making announcements editable, configurable, or dynamically generated.
- Changing the existing 2026 winners announcement beyond keeping it first.
- Other pages, tournament standings, or the Team Match feature.
- Adding images, scorecards, or new assets for this announcement.
- Deduplicating a stored announcement that duplicates the new pinned id, or otherwise changing stored-announcement filtering/ordering beyond inserting the new pinned item second.

## Open questions

- **Title, date, and wording.** Not specified by the intent. Assumption: follow the existing 2026 winners announcement's phrasing and layout; `title` contains `"Outing Day"` and `"对抗赛"` (e.g. `🎉 2026 Outing Day 对抗赛结果公告`), `date` is the announcement date in `YYYY-MM-DD` form (e.g. `2026-08-16`), and `author` is the same non-empty author value used by `PINNED_2026_WINNERS_ANNOUNCEMENT`. Tests assert format and required substrings, not the literal date.
- **Visible pinning treatment.** Not stated. Assumption: the announcement carries `pinned: True` and is rendered by the same path as the existing pinned winners announcement, so it gets the identical pinned treatment; no new badge or emoji logic is added.
- **Red Team roster order.** Not stated. Assumption: order matters and is preserved exactly as `刘北南 • 李扬 • 赵鲲 • 张纬 • Justin • 曾诚`.
- **Meaning of "second".** Not stated. Assumption: second overall in the list returned by `get_display_announcements()`, immediately after the 2026 winners announcement and before any stored announcement, including stored pinned ones.
- **`tags` content.** Not mentioned by the intent. Assumption: `tags` mirrors the existing announcement's convention (a list of short strings such as the event name); tests assert only that it is a list of strings.
- **Black Team roster.** Not provided by the intent. Assumption: only the Red Team roster is listed, as stated in the intent; the Black Team appears by name and score only.
