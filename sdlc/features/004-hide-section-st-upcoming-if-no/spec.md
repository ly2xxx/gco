<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@6b87b0f -->
## Summary
The front page (`streamlit_app.py`) stops rendering the "⏰ 近期赛事 Upcoming" block when there are no events dated today or later, so members no longer see a heading above a "No upcoming events" placeholder during quiet periods. When at least one upcoming event exists, the block renders exactly as it does today. No other page or section is affected.

## Behaviour
1. Given `load_events()` returns an empty list, when the front page is rendered, then no rendered element contains the text "近期赛事 Upcoming".
2. Given `load_events()` returns only events dated before today, when the front page is rendered, then no rendered element contains the text "近期赛事 Upcoming".
3. Given `load_events()` returns an empty list, when the front page is rendered, then no rendered element contains the text "No upcoming events".
4. Given `load_events()` returns an empty list, when the front page is rendered, then the script finishes without raising an exception and no error element is emitted.
5. Given one or more events dated today or later, when the front page is rendered, then an element containing the text "近期赛事 Upcoming" is rendered.
6. Given events dated on three distinct future dates, when the front page is rendered, then the Upcoming block lists those events in ascending date order.
7. Given the only event is dated exactly today, when the front page is rendered, then the Upcoming block is rendered and lists that event.
8. Given four or more events dated today or later, when the front page is rendered, then the Upcoming block lists exactly the three earliest of them, in ascending date order.
9. Given one or more events dated today or later, when the front page is rendered, then each listed event's card renders that event's `date`, `name` and `details` values (an empty string where `details` is absent).
10. Given one or more events dated today or later, when the front page is rendered, then an element linking to `pages/2_📅_Events.py` with label "查看完整赛历 View full calendar →" is rendered.
11. Given no upcoming events (empty list, or only past-dated events), when the front page is rendered, then no element links to `pages/2_📅_Events.py`.
12. Given the same events data rendered once with an empty upcoming set and once with a non-empty upcoming set, when the front page is rendered in each state, then every element that is not part of the Upcoming block appears in the same relative order in both renders.

## Interfaces

### `streamlit_app.py` (modified — front-page script body, `with col2:` block only)
No new module-level names, functions or classes are added. Existing names keep their signatures:

```python
# theme.py — unchanged
def section(st, icon: str, title: str) -> None: ...

# data.py — unchanged
def load_events() -> list[dict]: ...        # each dict: {"date": str, "name": str, "details": str | absent}
def load_announcements() -> list[dict]: ...
```

Changed behaviour of the existing `with col2:` block: `section(st, "⏰", "近期赛事 Upcoming")`, the event-card loop, and `st.page_link("pages/2_📅_Events.py", label="查看完整赛历 View full calendar →", icon="📅")` execute only when the already-computed `upcoming` list (events with `date >= str(datetime.date.today())`, sorted ascending, capped at 3) is non-empty. There is no `else` branch; `st.info("近期暂无赛事 No upcoming events.")` is removed. No other line in the file changes.

### `tests/test_upcoming_section_visibility.py` (new)
Pytest functions, each driving the front page through `streamlit.testing.v1.AppTest.from_file("streamlit_app.py")` with `data.load_events` and `data.load_announcements` monkeypatched (no network, no secrets, no manual steps):

```python
def test_upcoming_section_absent_when_events_empty() -> None: ...
def test_upcoming_section_absent_when_only_past_events() -> None: ...
def test_calendar_link_absent_when_no_upcoming_events() -> None: ...
def test_front_page_renders_without_exception_when_events_empty() -> None: ...
def test_upcoming_section_present_and_date_ordered_when_events_exist() -> None: ...
def test_today_event_counts_as_upcoming() -> None: ...
def test_upcoming_block_lists_at_most_three_earliest_events() -> None: ...
def test_event_card_content_matches_event_record() -> None: ...
def test_other_front_page_sections_ordering_unchanged() -> None: ...
```

## Out of scope
- Changing how upcoming events are selected, filtered, capped or sorted (still `date >= today`, ascending, first 3).
- Redesigning event cards, their styling, or the `section` / `hero` helpers in `theme.py`.
- Hiding the same block on other pages (e.g. `pages/2_📅_Events.py`) or hiding any other front-page section.
- Adding replacement content or an empty-state message where the Upcoming block used to be.
- Changes to `data.py` loaders, data sources, caching, or the events schema.
- Validating or repairing event records with a missing/null `date` field; existing behaviour for malformed records is unchanged.

## Open questions
- Does the "查看完整赛历 View full calendar →" link belong to the hidden section? The intent says the section is not rendered at all and no replacement content is added, but the done-when list only names the heading and placeholder. Assumption: the link is part of the section and is hidden too (criteria 10–11); hiding it means a quiet-period front page has an empty right column.
- What exactly defines "no upcoming events"? Assumption: the already-computed `upcoming` list being empty, not matching the placeholder display text.
- What defines "today" for the date comparison? Assumption: unchanged — `datetime.date.today()` on the server's local clock, using the existing string comparison.
- What happens if an event record has no `date` key? Assumption: unchanged existing behaviour (the current comparison is left as-is); no new guard is added, per the out-of-scope note.
- Should the separator or Quick Links area shift when the block disappears? Assumption: no — only the `with col2:` Upcoming block is affected; the rest of the layout is untouched.
