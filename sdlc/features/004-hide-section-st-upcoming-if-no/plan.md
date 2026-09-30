<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@4affedb -->
## Approach

Wrap the existing right-hand-column "⏰ 近期赛事 Upcoming" block in `streamlit_app.py` in a single `if <upcoming-list>:` guard — so the `section(...)` heading, the event-card loop and the `st.page_link("pages/2_📅_Events.py", …)` call all render only when the already-computed upcoming list (events with `date >= str(datetime.date.today())`, ascending, first 3) is non-empty — and delete the `else`/`st.info("近期暂无赛事 No upcoming events.")` fallback, leaving nothing in its place. A new `tests/test_upcoming_section_visibility.py` drives the real front-page script through `streamlit.testing.v1.AppTest` with `data.load_events` / `data.load_announcements` patched, records every string the page renders (by wrapping the Streamlit text APIs and harvesting the AppTest element tree), and asserts both the hidden and visible states.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| With zero upcoming events, the front page shows no "⏰ 近期赛事 Upcoming" heading and no "No upcoming events" placeholder. | 1 (empty list), 2 (only past-dated), 3 (no placeholder), 4 (no exception / no error element), 11 (no calendar link) | Phase 1 |
| With one or more upcoming events, the section renders unchanged, listing the events as before. | 5 (heading rendered), 6 (ascending date order), 7 (today counts), 8 (cap at three earliest), 9 (card renders date/name/details), 10 (full-calendar link + label) | Phase 1 (5, 6, 10) and Phase 2 (7, 8, 9) |
| The rest of the front page layout and ordering is unaffected in both states. | 12 (non-Upcoming elements keep their relative order) | Phase 2 |
| A test covers both the empty and non-empty cases. | 1–11 across `tests/test_upcoming_section_visibility.py` | Phase 1 (`empty` cases + basic `non-empty`) and Phase 2 (remaining `non-empty` cases) |
| The existing tests still pass. | all (no regressions from removing the placeholder) | Phase 1 (runs `test_streamlit_app.py` and `tests/`), Phase 2 (re-runs them; whole suite re-run at final verification) |

## Phase 1: Guard the Upcoming block and prove hidden/visible states

<!-- phase: 1 -->
<!-- targets: streamlit_app.py, tests/test_upcoming_section_visibility.py -->
<!-- frozen: data.py, theme.py, test_streamlit_app.py, tests/test_announcement_page_wiring.py, tests/test_pinned_announcements.py, tests/test_pinned_winners_announcement.py, pages/**, features/** -->

**Goal:** With no upcoming events the front page renders neither the "近期赛事 Upcoming" heading, nor "No upcoming events", nor the calendar link; with upcoming events it still renders the heading, the events in date order and the calendar link.

**Changes:**

- `streamlit_app.py`: edit only the front page's `with col2:` block (the right column of the two-column row that holds the "⏰ 近期赛事 Upcoming" section). No new module-level name, function or class; no import changes; every other line stays byte-for-byte identical.
  - Keep the existing statement that builds the upcoming list exactly as it is (same local variable name — this plan calls it `upcoming`; filter `date >= str(datetime.date.today())`, sort ascending by `date`, slice `[:3]`). It must be a statement that runs *before* the section is rendered, not an expression inline in a `for`/`if`. If it currently sits after the `section(...)` call, move only that statement above the guard; do not alter the expression.
  - Immediately after it, add `if <upcoming>:`, and indent the whole remainder of the `col2` block by four extra spaces so that, after the edit, the block ends with exactly this shape (blank lines and comments may be kept):
    ```python
        <existing upcoming-list statement, unchanged>
        if <upcoming>:
            section(st, "⏰", "近期赛事 Upcoming")
            for <event> in <upcoming>:              # existing loop, unchanged
                <existing event-card rendering statements, unchanged>
            st.page_link("pages/2_📅_Events.py", label="查看完整赛历 View full calendar →", icon="📅")
    ```
  - Delete the `st.info("近期暂无赛事 No upcoming events.")` call together with the `else:` line that introduces it. There is no `else` branch and no replacement content afterwards. After the edit the string `近期暂无赛事 No upcoming events` must occur zero times in the file, and the file must contain exactly one occurrence of `近期赛事 Upcoming`.
- `tests/test_upcoming_section_visibility.py` (new file, pytest, self-contained — no conftest, no server, no network): module docstring `"""Front-page behaviour: hide the Upcoming section when nothing is upcoming."""`, then exactly:
  ```python
  from __future__ import annotations

  import dataclasses
  import datetime
  import pathlib

  import pytest
  import streamlit as st
  from streamlit.testing.v1 import AppTest

  REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
  FRONT_PAGE = REPO_ROOT / "streamlit_app.py"
  CALENDAR_PAGE = "pages/2_📅_Events.py"
  CALENDAR_LABEL = "查看完整赛历 View full calendar →"
  HEADING = "近期赛事 Upcoming"
  PLACEHOLDER = "No upcoming events"
  PAST_DATE = "1999-01-01"

  # Real Streamlit APIs, captured at import before any test patches them.
  _REAL_MARKDOWN = st.markdown
  _REAL_CAPTION = st.caption
  _REAL_TITLE = st.title
  _REAL_HEADER = st.header
  _REAL_SUBHEADER = st.subheader
  _REAL_TEXT = st.text
  _REAL_INFO = st.info
  _REAL_ERROR = st.error
  _REAL_PAGE_LINK = st.page_link


  def _event(date: str, name: str, details: str | None = "details") -> dict:
      """Event record in the schema used by data.py; omit `details` when passed None."""
      event: dict = {"date": date, "name": name, "type": "League"}
      if details is not None:
          event["details"] = details
      return event


  @dataclasses.dataclass
  class RenderedPage:
      texts: list[str]      # every string rendered as text/markdown/info/… 
      errors: list[str]     # every string passed to st.error
      page_links: list[dict]  # {"page": str(page), "label": str | None}
      exceptions: list[str]   # messages of AppTest exception elements

      def contains(self, needle: str) -> bool:
          return any(needle in text for text in [*self.texts, *self.errors])

      def index_of(self, needle: str) -> int:
          for index, text in enumerate([*self.texts, *self.errors]):
              if needle in text:
                  return index
          raise AssertionError(f"{needle!r} was not rendered on the front page")


  def _harvest_element_tree(app: AppTest) -> list[str]:
      """Fallback text harvest, in case an element is rendered by an API we did not wrap."""
      collected: list[str] = []
      for name in ("markdown", "caption", "title", "header", "subheader", "text",
                   "info", "error", "warning", "success", "code", "exception"):
          try:
              elements = getattr(app, name)
          except Exception:
              continue
          try:
              iterator = list(elements)
          except Exception:
              continue
          for element in iterator:
              for field in ("value", "body", "label", "message"):
                  value = getattr(element, field, None)
                  if isinstance(value, str):
                      collected.append(value)
      return collected


  @pytest.fixture
  def render_front_page(monkeypatch):
      """Return render(events, announcements=None) -> RenderedPage for streamlit_app.py."""

      def _render(events: list[dict], announcements: list[dict] | None = None) -> RenderedPage:
          import data

          monkeypatch.setattr(data, "load_events", lambda: list(events))
          monkeypatch.setattr(data, "load_announcements", lambda: list(announcements or []))

          texts: list[str] = []
          errors: list[str] = []
          page_links: list[dict] = []

          def _record(real, sink: list[str]):
              def wrapper(*args, **kwargs):
                  body = args[0] if args else kwargs.get("body", "")
                  if isinstance(body, str):
                      sink.append(body)
                  return real(*args, **kwargs)
              return wrapper

          monkeypatch.setattr(st, "markdown", _record(_REAL_MARKDOWN, texts))
          monkeypatch.setattr(st, "caption", _record(_REAL_CAPTION, texts))
          monkeypatch.setattr(st, "title", _record(_REAL_TITLE, texts))
          monkeypatch.setattr(st, "header", _record(_REAL_HEADER, texts))
          monkeypatch.setattr(st, "subheader", _record(_REAL_SUBHEADER, texts))
          monkeypatch.setattr(st, "text", _record(_REAL_TEXT, texts))
          monkeypatch.setattr(st, "info", _record(_REAL_INFO, texts))
          monkeypatch.setattr(st, "error", _record(_REAL_ERROR, errors))

          def _recording_page_link(page, *args, **kwargs):
              page_links.append({"page": str(page), "label": kwargs.get("label")})
              return _REAL_PAGE_LINK(page, *args, **kwargs)

          monkeypatch.setattr(st, "page_link", _recording_page_link)

          app = AppTest.from_file(str(FRONT_PAGE), default_timeout=60)
          app.run()

          return RenderedPage(
              texts=[*texts, *_harvest_element_tree(app)],
              errors=list(errors),
              page_links=[dict(link) for link in page_links],
              exceptions=[
                  str(getattr(element, "message", None) or getattr(element, "value", element))
                  for element in app.exception
              ],
          )

      return _render


  def test_upcoming_section_absent_when_events_empty(render_front_page) -> None:
      """Spec 1 + 3: empty event list → no heading, no placeholder."""
      page = render_front_page(events=[])
      assert page.exceptions == []
      assert not page.contains(HEADING)
      assert not page.contains(PLACEHOLDER)


  def test_upcoming_section_absent_when_only_past_events(render_front_page) -> None:
      """Spec 2: only past-dated events → no heading and the past event is not listed."""
      page = render_front_page(events=[_event(PAST_DATE, "PAST-ONLY-EVENT")])
      assert page.exceptions == []
      assert not page.contains(HEADING)
      assert not page.contains("PAST-ONLY-EVENT")


  def test_calendar_link_absent_when_no_upcoming_events(render_front_page) -> None:
      """Spec 11: empty list and past-only list → no link to pages/2_📅_Events.py."""
      empty_page = render_front_page(events=[])
      past_page = render_front_page(events=[_event(PAST_DATE, "PAST-ONLY-EVENT")])
      for page in (empty_page, past_page):
          assert not any(link["page"] == CALENDAR_PAGE for link in page.page_links)


  def test_front_page_renders_without_exception_when_events_empty(render_front_page) -> None:
      """Spec 4: the script completes without raising and emits no error element."""
      page = render_front_page(events=[])
      assert page.exceptions == []
      assert page.errors == []


  def test_upcoming_section_present_and_date_ordered_when_events_exist(render_front_page) -> None:
      """Spec 5, 6, 10: heading + ascending order + full-calendar link when events exist."""
      events = [
          _event("2099-03-01", "EVENT-GAMMA"),
          _event("2099-01-01", "EVENT-ALPHA"),
          _event("2099-02-01", "EVENT-BETA"),
      ]
      page = render_front_page(events=events)
      assert page.exceptions == []
      assert page.contains(HEADING)
      assert page.index_of("EVENT-ALPHA") < page.index_of("EVENT-BETA") < page.index_of("EVENT-GAMMA")
      calendar_links = [link for link in page.page_links if link["page"] == CALENDAR_PAGE]
      assert calendar_links, "the full-calendar page link was not rendered"
      assert calendar_links[0]["label"] == CALENDAR_LABEL
  ```
  Teardown: none needed beyond pytest's `monkeypatch` fixture, which restores `data.load_events`, `data.load_announcements` and every patched `streamlit` attribute after each test; `AppTest` runs in-process and starts no server, thread or subprocess.

**Definition of done:**
- [ ] `tests/test_upcoming_section_visibility.py::test_upcoming_section_absent_when_events_empty`: proves spec 1 and 3 — render with `events=[]`, assert `page.exceptions == []`, `not page.contains("近期赛事 Upcoming")`, `not page.contains("No upcoming events")`.
- [ ] `tests/test_upcoming_section_visibility.py::test_upcoming_section_absent_when_only_past_events`: proves spec 2 — render with one `"1999-01-01"` event, assert no heading and the past event name is not rendered.
- [ ] `tests/test_upcoming_section_visibility.py::test_calendar_link_absent_when_no_upcoming_events`: proves spec 11 in both empty and past-only states — assert no recorded `st.page_link` call has `page == "pages/2_📅_Events.py"`.
- [ ] `tests/test_upcoming_section_visibility.py::test_front_page_renders_without_exception_when_events_empty`: proves spec 4 — `page.exceptions == []` and `page.errors == []`.
- [ ] `tests/test_upcoming_section_visibility.py::test_upcoming_section_present_and_date_ordered_when_events_exist`: proves spec 5, 6 and 10 — heading present, `index_of("EVENT-ALPHA") < index_of("EVENT-BETA") < index_of("EVENT-GAMMA")`, calendar link present with label `查看完整赛历 View full calendar →`.
- [ ] No teardown fixtures required; `monkeypatch` undoes every patch and `AppTest` leaves no background process.
- [ ] Observable source check: `streamlit_app.py` contains zero occurrences of `近期暂无赛事 No upcoming events` and exactly one of `近期赛事 Upcoming`.
- [ ] Existing suites still pass (run in Verify): `python -m pytest test_streamlit_app.py tests/ -v`.

**Verify:**
```bash
python -m pytest tests/test_upcoming_section_visibility.py -v
python -m pytest test_streamlit_app.py tests/ -v
test -z "$(grep -n '近期暂无赛事 No upcoming events' streamlit_app.py || true)"
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Prove the visible-state details and untouched layout

<!-- phase: 2 -->
<!-- targets: tests/test_upcoming_section_visibility.py -->
<!-- frozen: streamlit_app.py, data.py, theme.py, test_streamlit_app.py, tests/test_announcement_page_wiring.py, tests/test_pinned_announcements.py, tests/test_pinned_winners_announcement.py, pages/** -->

**Goal:** Four more tests pin the today boundary, the three-event cap, the card payload and the unchanged relative order of the rest of the front page, with `streamlit_app.py` untouched.

**Changes:**

- `tests/test_upcoming_section_visibility.py`: append the four functions below after the Phase 1 tests. Do not modify the imports, `_event`, `RenderedPage`, `_harvest_element_tree`, the `render_front_page` fixture, or any Phase 1 test.
  ```python
  def test_today_event_counts_as_upcoming(render_front_page) -> None:
      """Spec 7: an event dated exactly today is upcoming and is listed."""
      today = datetime.date.today().isoformat()
      page = render_front_page(events=[_event(today, "EVENT-TODAY")])
      assert page.exceptions == []
      assert page.contains(HEADING)
      assert page.contains("EVENT-TODAY")


  def test_upcoming_block_lists_at_most_three_earliest_events(render_front_page) -> None:
      """Spec 8: four future events → exactly the three earliest, ascending."""
      events = [
          _event("2099-04-01", "EVENT-DELTA"),
          _event("2099-01-01", "EVENT-ALPHA"),
          _event("2099-03-01", "EVENT-GAMMA"),
          _event("2099-02-01", "EVENT-BETA"),
      ]
      page = render_front_page(events=events)
      assert page.exceptions == []
      assert page.index_of("EVENT-ALPHA") < page.index_of("EVENT-BETA") < page.index_of("EVENT-GAMMA")
      assert not page.contains("EVENT-DELTA")


  def test_event_card_content_matches_event_record(render_front_page) -> None:
      """Spec 9: card renders date, name and details; a missing `details` key still renders."""
      page = render_front_page(
          events=[_event("2099-01-01", "EVENT-ALPHA", details="DETAILS-ALPHA")]
      )
      assert page.contains("2099-01-01")
      assert page.contains("EVENT-ALPHA")
      assert page.contains("DETAILS-ALPHA")

      page = render_front_page(
          events=[_event("2099-01-02", "EVENT-NO-DETAILS", details=None)]
      )
      assert page.exceptions == []
      assert page.contains("EVENT-NO-DETAILS")


  def test_other_front_page_sections_ordering_unchanged(render_front_page) -> None:
      """Spec 12: elements rendered in both states keep their relative order.

      Texts that exist in only one of the two states (e.g. anything derived from the
      upcoming list) are excluded; every shared element must keep its relative order.
      """
      hidden_page = render_front_page(events=[])
      shown_page = render_front_page(events=[_event("2099-01-01", "EVENT-ALPHA")])

      hidden_texts = hidden_page.texts
      shown_texts = shown_page.texts
      assert hidden_texts, "the front page rendered no text at all"
      assert not hidden_page.contains("EVENT-ALPHA")

      shared = set(hidden_texts) & set(shown_texts)
      assert shared, "the hidden and shown renders share no front-page element"

      hidden_order = [text for text in hidden_texts if text in shared]
      shown_order = [text for text in shown_texts if text in shared]
      assert hidden_order == shown_order
  ```
- No production file changes in this phase; `streamlit_app.py` is frozen so this phase re-runs the Phase 1 Verify commands unchanged and must still pass.

**Definition of done:**
- [ ] `tests/test_upcoming_section_visibility.py::test_today_event_counts_as_upcoming`: proves spec 7 — event with `datetime.date.today().isoformat()` renders the heading and the event.
- [ ] `tests/test_upcoming_section_visibility.py::test_upcoming_block_lists_at_most_three_earliest_events`: proves spec 8 — four future events, the three earliest render in ascending order and the fourth (`EVENT-DELTA`) is absent.
- [ ] `tests/test_upcoming_section_visibility.py::test_event_card_content_matches_event_record`: proves spec 9 — date, name and `details` all appear for a normal record; an event dict without a `details` key renders without an exception.
- [ ] `tests/test_upcoming_section_visibility.py::test_other_front_page_sections_ordering_unchanged`: proves spec 12 — the ordered list of texts shared by the empty-events render and the one-event render is identical, and the event is absent from the hidden render.
- [ ] Phase 1 tests still pass unchanged, and `streamlit_app.py` is byte-identical to the end of Phase 1 (it is frozen in this phase).
- [ ] No teardown fixtures required; `monkeypatch` restores every patched attribute after each test.

**Verify:**
```bash
python -m pytest tests/test_upcoming_section_visibility.py -v
python -m pytest test_streamlit_app.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks

- If the "近期赛事 Upcoming" heading is rendered by a Streamlit API the fixture does not wrap, the *absence* assertions would pass vacuously but `test_upcoming_section_present_and_date_ordered_when_events_exist` (Phase 1) would fail on `page.contains(HEADING)` — the fixture also harvests the AppTest element tree (`_harvest_element_tree`) to cover other sinks.
- If an existing test asserts the old "No upcoming events" placeholder, Phase 1's Verify fails at `python -m pytest test_streamlit_app.py tests/ -v`; see Open questions for the assumption.
- If the event-card renderer indexes `event["details"]` directly instead of `.get("details", "")`, the missing-`details` half of `test_event_card_content_matches_event_record` (Phase 2) fails; see Open questions.
- If removing the `else` leaves the placeholder reachable through another branch, the Phase 1 grep check (`test -z "$(grep -n '近期暂无赛事 No upcoming events' streamlit_app.py || true)"`) fails.
- If the front page contains other `st.page_link` calls, the link assertions still hold because they filter by `CALENDAR_PAGE` rather than counting calls (Phase 1, Phase 2).
- If the rest of the front page re-orders when the block disappears (e.g. the column collapses), `test_other_front_page_sections_ordering_unchanged` (Phase 2) fails.
- If `AppTest.from_file` cannot execute the front page (login gate, missing secret, slow import), every Phase 1 test fails loudly with the captured `app.exception` message; `default_timeout=60` bounds a hung run.

## Open questions

- Does any existing test assert the placeholder "近期暂无赛事 No upcoming events."? Assumption: no — the intent's "existing tests still pass" is taken at face value, and Phase 1's Verify runs `test_streamlit_app.py` and `tests/` to prove it.
- Does the event-card renderer tolerate an event record without a `details` key? Assumption per spec behaviour 9: yes, it renders an empty string. The plan keeps the check but as a separate part of `test_event_card_content_matches_event_record`, so a failure is isolated and can be revised.
- What is the existing local variable name for the upcoming list? Assumption per the spec's Interfaces section: `upcoming`; the plan says to keep whatever name the file already uses and never rename it.
- Where exactly does `section(...)` render its heading? Assumption: through `st.markdown` (a `theme.py` helper passed `st`), which the fixture records; the element-tree harvest is the fallback.
- Behaviour 12 is tested as "every text rendered in both states keeps its relative order"; text that exists in only one state (for example something computed from the upcoming list elsewhere on the page) is excluded rather than asserted equal.
- The whole suite runs `behave` at final verification; this plan does not add or change `.feature` files because the spec keeps the change inside the Streamlit script body.

## Hand back

When every phase is built and its Verify block passes:
1. Create `sdlc/features/004-hide-section-st-upcoming-if-no/build-log.md` with one section per phase, in order. Head each one `## Phase <n>: <title>`, then list the files changed, the Verify command you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/004-hide-section-st-upcoming-if-no`.
