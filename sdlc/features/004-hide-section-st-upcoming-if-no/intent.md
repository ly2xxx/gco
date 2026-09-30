<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@77fc814 -->
# Intent: Hide the "Upcoming Events" section when there is nothing upcoming

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
Members opening the GCO dashboard see a "⏰ 近期赛事 Upcoming" heading followed by the placeholder text "No upcoming events". This takes up prime front-page space and makes the club look inactive during quiet periods, forcing readers to scan past a block that carries no information.

## Outcome
When there are no upcoming events, the "⏰ 近期赛事 Upcoming" section is not rendered at all — no heading, no placeholder text. When at least one upcoming event exists, the section renders exactly as it does today. This most likely belongs on the front page in `streamlit_app.py`.

## Done when
- With zero upcoming events, the front page shows no "⏰ 近期赛事 Upcoming" heading and no "No upcoming events" placeholder.
- With one or more upcoming events, the section renders unchanged, listing the events as before.
- The rest of the front page layout and ordering is unaffected in both states.
- A test covers both the empty and non-empty cases.
- The existing tests still pass.

## Not in scope
- Changing how upcoming events are selected, filtered or sorted.
- Redesigning the event list, its styling, or the `section` helper itself.
- Applying the same hiding behaviour to other sections or other pages.
- Adding replacement content or an empty-state message in place of the hidden section.

## Open questions
- What exactly counts as "no upcoming events" — an empty event list, or the presence of the literal placeholder string? Assumption: the condition is derived from the underlying event data being empty, not from matching display text.
- Should the heading be hidden while the placeholder text is suppressed, or only the body? Assumption: the whole section, heading included, is hidden.
- Does this apply only to the front page? Assumption: yes, only where this section currently appears on the front page.
- No prior intent document was supplied, so this is written from scratch rather than as a revision.
