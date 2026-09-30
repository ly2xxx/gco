"""Front-page behaviour: hide the Upcoming section when nothing is upcoming."""
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

