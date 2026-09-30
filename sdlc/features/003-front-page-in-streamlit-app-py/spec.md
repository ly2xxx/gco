<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@2431eae -->
## Summary
The pinned-announcement records and the display-selection logic move out of `streamlit_app.py` and `pages/1_📢_Announcements.py` into a new shared module `pinned_announcements.py`. Both pages import `get_display_announcements()` from that module, so the home page's 最新动态 block and the Announcements page select the same pinned announcements in the same order from the same data. Visible behaviour is otherwise unchanged.

## Behaviour
1. Given a Python process with no network access and no Streamlit secrets configured, when `import pinned_announcements` runs, then it succeeds and exposes `PINNED_ANNOUNCEMENTS` (a non-empty `list[dict]`) and `get_display_announcements` (a callable), with no import-time side effects, I/O, or exceptions.
2. Given every `*.py` file in the repository, when each is parsed, then the pinned-record literal is defined in exactly one file (`pinned_announcements.py`) and the name `get_display_announcements` is bound by a `def` in exactly one file (`pinned_announcements.py`).
3. Given the source of `streamlit_app.py`, when it is parsed, then it imports `get_display_announcements` from `pinned_announcements`, defines no module-level list of pinned announcement dicts, and defines no local `get_display_announcements` function.
4. Given the source of `pages/1_📢_Announcements.py`, when it is parsed, then it imports `get_display_announcements` from `pinned_announcements`, defines no module-level list of pinned announcement dicts, and defines no local `get_display_announcements` function.
5. Given a list containing both records with a truthy `pinned` and records with a falsy or missing `pinned`, when `get_display_announcements(announcements)` is called, then every pinned record appears before every non-pinned record in the returned list.
6. Given the same list, when `get_display_announcements(announcements)` is called, then the pinned records appear in the order defined by `PINNED_ANNOUNCEMENTS`, followed by any additional pinned input records in their input order, and the non-pinned records keep their input relative order.
7. Given `announcements=[]` or `announcements=None`, when `get_display_announcements(announcements)` is called, then it returns a list equal to `PINNED_ANNOUNCEMENTS` and raises no exception.
8. Given an input record that omits the `pinned` key or sets it to `None` or `False`, when `get_display_announcements(announcements)` is called, then that record is placed in the non-pinned group.
9. Given any input list, when `get_display_announcements(announcements)` is called twice, then the two returned lists are equal and the input list is unchanged (the function does not mutate its argument or module state).
10. Given an input list whose selection contains more than two announcements, when `get_display_announcements(announcements)` is called, then the returned list is not truncated by the function (no "2 results" cap is applied inside it).
11. Given one identical announcements list, when the home page's 最新动态 selection and the Announcements page's selection are derived, then the sequence of pinned announcement `id` values used by both is identical, because both call `get_display_announcements` from `pinned_announcements` with that same list.
12. Given the existing automated test suite, when it is run after the change (with any imports of the relocated names updated to `pinned_announcements`), then every existing test passes and no test imports a pinned-record definition or a selection helper from `streamlit_app.py` or `pages/1_📢_Announcements.py`.

## Interfaces

**`pinned_announcements.py`** — new file, repository root (sibling of `data.py`):

```python
from __future__ import annotations

# Single definition of the pinned announcement records.
# Records are byte-identical to the ones currently duplicated in
# streamlit_app.py and pages/1_📢_Announcements.py.
PINNED_ANNOUNCEMENTS: list[dict] = [
    {
        "id": str,        # e.g. "ann-001"
        "title": str,
        "date": str,      # "YYYY-MM-DD"
        "author": str,
        "pinned": True,
        "body": str,
        "tags": list[str],
    },
    # ...
]


def get_display_announcements(announcements: list[dict] | None = None) -> list[dict]:
    """Return the announcements to display: pinned records first (in
    PINNED_ANNOUNCEMENTS order, then any additional pinned input records in
    input order), then the remaining input records in input order."""
```

**`streamlit_app.py`** — remove the local pinned-record list and the local display-selection function; add:

```python
from pinned_announcements import get_display_announcements
```

Existing preview-only presentation (e.g. body truncation) stays in this file; no other public names change.

**`pages/1_📢_Announcements.py`** — remove the local pinned-record list and the local display-selection function; add:

```python
from pinned_announcements import get_display_announcements
```

**`tests/test_pinned_winners_announcement.py`** (and any other test currently importing the relocated names) — change the import to:

```python
from pinned_announcements import PINNED_ANNOUNCEMENTS, get_display_announcements
```

## Out of scope
- Changing which announcements are pinned, or adding/removing pinned announcements.
- Changing how announcements are sourced, stored, or loaded (Google Sheets, `data.py`, backups, `data/announcements.json`).
- Changing how many announcements are shown, or the "2 results" limit.
- Redesigning the announcement card markup, tags, or styling on either page.
- Moving or changing the home page's preview-specific body truncation.
- Adding new pages or new announcement features.

## Open questions
- The exact signatures of the two current per-page helpers were not visible in the provided files. Assumption: `get_display_announcements(announcements: list[dict] | None = None) -> list[dict]` takes the underlying announcement records and returns the ordered display list; if the existing call sites pass no argument, the parameter keeps its `None` default.
- Ordering between module-defined pinned records and pinned records coming from the loaded data. Assumption: module records first, then input pinned records, then the non-pinned records, preserving the existing relative order within each group.
- Behaviour when nothing is pinned or when fewer than two announcements exist. Assumption: unchanged from today, only relocated — pinned records still come first, remaining records follow, and no error is raised.
- Whether the "2 results" cap belongs inside the shared function. Assumption: no — the cap stays at each call site, so the shared function returns the full selection.
- Whether the duplicated pinned records in the two pages are identical to each other. Assumption: yes, and the single copy in `pinned_announcements.py` is byte-identical to them, so no visible content changes.
- Whether any test or import currently references the old locations. Assumption: yes, and those imports are updated to `pinned_announcements` so no stale references remain.
