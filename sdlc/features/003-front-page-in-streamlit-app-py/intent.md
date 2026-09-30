<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@2e8584f -->
# Intent: Share pinned announcements between the home page and the Announcements page

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
The home page's 最新动态 block and the 公告 (Announcements) page each decide on their own which announcements to surface and how to order pinned ones, and the pinned records themselves are duplicated. Because of that, the two pages can silently show different things, and any change to which announcements are pinned or how they are ordered has to be made in two files. The result is a front page that drifts from the source of truth and a maintenance cost that grows with every announcement change.

## Outcome
There is a single shared source for the pinned announcement records and for the function that selects the announcements to display (`get_display_announcements()`), living in a new module `pinned_announcements.py`. Both `streamlit_app.py` and `pages/1_📢_Announcements.py` import that shared logic instead of holding their own copy, so the home page's 最新动态 and the Announcements page present the same pinned announcements for the same data, and neither page owns that logic any more. Visible behaviour is unchanged apart from being consistent by construction.

## Done when
- The pinned announcement records are defined in exactly one place in the codebase, and that place is `pinned_announcements.py`.
- `get_display_announcements()` is defined in exactly one place, is importable from `pinned_announcements.py`, and is imported by both `streamlit_app.py` and `pages/1_📢_Announcements.py`.
- Neither page contains a local pinned-records definition or a local copy of the display-selection logic.
- For the same underlying announcement data, the home page's 最新动态 block and the Announcements page surface the same pinned announcements in the same order.
- The existing tests still pass.

## Not in scope
- Changing which announcements are pinned, or adding or removing pinned announcements.
- Changing how announcements are sourced, stored or loaded (Google Sheets, `data.py`, backups).
- Changing how many announcements are shown, or the "2 results" limit.
- Redesigning the announcement card markup, tags, or styling on either page.
- Adding new pages or new announcement features.

## Open questions
- How the shared selection should behave when nothing is pinned or when fewer than two announcements exist: assumed the current selection behaviour is preserved exactly as-is, only relocated.
- Whether the home page should keep any preview-specific trimming (body truncation) separate from the shared selection: assumed yes — selection is shared, presentation stays per page.
- Whether any tests or imports currently reference the old locations: assumed they are updated to the new module so no stale references remain.
