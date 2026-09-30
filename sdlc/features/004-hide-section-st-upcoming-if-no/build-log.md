# Build log: 004-hide-section-st-upcoming-if-no

## Phase 1: Guard the Upcoming block and prove hidden/visible states
**Status:** implementation complete, awaiting user testing & approval.
**Files changed:** `streamlit_app.py`, `tests/test_upcoming_section_visibility.py` (new).

In `streamlit_app.py`, reordered the `with col2:` block so `events = load_events()`, `today_str = ...`, and `upcoming = sorted(...)[:3]` execute before rendering. The entire rendering block (`section(...)`, event-card loop, and `st.page_link(...)` to the events calendar) is now guarded with `if upcoming:`. The `else:` branch and `st.info("近期暂无赛事 No upcoming events.")` fallback have been removed, leaving no placeholder when there are zero upcoming events.

`tests/test_upcoming_section_visibility.py` provides the self-contained `AppTest` fixture `render_front_page` and the 5 Phase 1 tests covering specifications 1, 2, 3, 4, 5, 6, 10, and 11:
- `test_upcoming_section_absent_when_events_empty`
- `test_upcoming_section_absent_when_only_past_events`
- `test_calendar_link_absent_when_no_upcoming_events`
- `test_front_page_renders_without_exception_when_events_empty`
- `test_upcoming_section_present_and_date_ordered_when_events_exist`

**Verify commands:**
- `python -m pytest tests/test_upcoming_section_visibility.py -v`
- `python -m pytest test_streamlit_app.py tests/ -v`
- `test -z "$(grep -n '近期暂无赛事 No upcoming events' streamlit_app.py || true)"`

**Deviations:**
- none.
