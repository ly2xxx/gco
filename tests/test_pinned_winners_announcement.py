from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys
import types
from typing import Any

import pytest

PAGE_PATH = pathlib.Path(__file__).resolve().parents[1] / "pages" / "1_📢_Announcements.py"


class _SessionState(dict):
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class _Recorder:
    def __init__(self, name: str, log: list[tuple[str, tuple[Any, ...], dict[str, Any]]]):
        self.name = name
        self.log = log

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.log.append((self.name, args, kwargs))
        leaf = self.name.rsplit(".", 1)[-1]
        if leaf in {"button", "form_submit_button", "download_button", "link_button", "checkbox", "toggle"}:
            return False
        if leaf in {"text_input", "text_area"}:
            return ""
        if leaf == "number_input":
            return 0
        if leaf in {"selectbox", "radio"}:
            if args and isinstance(args[0], (list, tuple)) and args[0]:
                return args[0][0]
            if args and isinstance(args[0], dict) and args[0]:
                return next(iter(args[0]))
            return None
        if leaf == "multiselect":
            return []
        if leaf == "slider":
            if len(args) >= 3:
                return args[1]
            return 0
        if leaf == "date_input":
            import datetime
            return datetime.date(2026, 9, 15)
        if leaf == "file_uploader":
            return None
        if leaf == "color_picker":
            return "#000000"
        return self

    def __enter__(self) -> "_Recorder":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def __iter__(self):
        return iter(())

    def __getitem__(self, item: Any) -> "_Recorder":
        return _Recorder(f"{self.name}[{item!r}]", self.log)

    def __getattr__(self, name: str) -> "_Recorder":
        return _Recorder(f"{self.name}.{name}", self.log)


def _cache_decorator(*args: Any, **kwargs: Any):
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return args[0]

    def decorator(func):
        return func

    return decorator


class _FakeStreamlit(types.ModuleType):
    def __init__(self, log: list[tuple[str, tuple[Any, ...], dict[str, Any]]]):
        super().__init__("streamlit")
        self.log = log
        self.session_state = _SessionState()
        self.secrets: dict[str, Any] = {}

    def _columns(self, spec: Any) -> list[_Recorder]:
        n = spec if isinstance(spec, int) else len(spec)
        return [_Recorder(f"st.column[{i}]", self.log) for i in range(n)]

    def _tabs(self, labels: list[str]) -> list[_Recorder]:
        return [_Recorder(f"st.tab[{label}]", self.log) for label in labels]

    def __getattr__(self, name: str) -> Any:
        if name in {"cache_data", "cache_resource", "experimental_memo", "experimental_singleton"}:
            return _cache_decorator
        if name == "columns":
            return self._columns
        if name == "tabs":
            return self._tabs
        if name == "sidebar":
            return _Recorder("st.sidebar", self.log)
        return _Recorder(f"st.{name}", self.log)


@pytest.fixture
def load_announcements_page(monkeypatch):
    loaded: list[str] = []
    save_calls: list[list[dict[str, Any]]] = []

    def _load(stored_announcements: list[dict[str, Any]] | None = None):
        log: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        fake_st = _FakeStreamlit(log)
        monkeypatch.setitem(sys.modules, "streamlit", fake_st)
        # `uv run pytest tests/...` puts only tests/ on sys.path; the page and data.py live at the repo root.
        monkeypatch.syspath_prepend(str(PAGE_PATH.parents[1]))
        import data

        stored = [] if stored_announcements is None else stored_announcements
        monkeypatch.setattr(data, "load_announcements", lambda: stored)
        monkeypatch.setattr(data, "save_announcements", lambda anns: save_calls.append(anns))

        module_name = f"announcements_page_under_test_{len(loaded)}"
        loaded.append(module_name)
        spec = importlib.util.spec_from_file_location(module_name, PAGE_PATH)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module, log, save_calls

    yield _load
    for module_name in loaded:
        sys.modules.pop(module_name, None)


def test_pinned_announcement_has_exact_fields(load_announcements_page):
    """Spec behaviours 3, 4, 5, 6, 7."""
    module, _, _ = load_announcements_page()
    ann = module.get_pinned_winners_announcement()

    assert set(ann) == {"id", "title", "date", "author", "pinned", "body", "tags"}
    assert ann["id"] == "pinned-2026-season-winners"
    assert ann["pinned"] is True
    assert "张纬" in ann["body"] and "个人联赛" in ann["body"]
    assert "王文龙" in ann["body"] and "个人杯赛" in ann["body"]
    for field in ("title", "date", "author", "body"):
        assert isinstance(ann[field], str) and ann[field]
    assert isinstance(ann["tags"], list) and all(isinstance(t, str) for t in ann["tags"])


def test_get_pinned_winners_announcement_returns_fresh_copy(load_announcements_page):
    """The accessor returns a copy and does not expose the constant's mutable tags."""
    module, _, _ = load_announcements_page()
    first = module.get_pinned_winners_announcement()
    second = module.get_pinned_winners_announcement()

    assert first == second
    assert first is not second

    first["tags"].append("mutated")
    assert "mutated" not in module.PINNED_2026_WINNERS_ANNOUNCEMENT["tags"]
    assert "mutated" not in module.get_pinned_winners_announcement()["tags"]


def test_get_display_announcements_empty(load_announcements_page):
    """Spec behaviour 1."""
    module, _, _ = load_announcements_page()
    result = module.get_display_announcements([])

    assert len(result) == 1
    assert result[0] == module.get_pinned_winners_announcement()


def test_get_display_announcements_pins_first_before_stored_pinned(load_announcements_page):
    """Spec behaviours 2 and 8."""
    module, _, _ = load_announcements_page()
    stored = [
        {
            "id": "s1",
            "title": "Stored pinned",
            "date": "2026-01-01",
            "author": "Author",
            "pinned": True,
            "body": "Stored pinned body",
            "tags": ["stored"],
        },
        {
            "id": "s2",
            "title": "Stored normal",
            "date": "2026-01-02",
            "author": "Author",
            "pinned": False,
            "body": "Stored normal body",
            "tags": [],
        },
    ]
    before = copy.deepcopy(stored)

    result = module.get_display_announcements(stored)

    assert [a["id"] for a in result] == ["pinned-2026-season-winners", "s1", "s2"]
    assert stored == before


def test_get_display_announcements_passes_through_missing_fields(load_announcements_page):
    """Spec behaviour 9."""
    module, _, _ = load_announcements_page()
    stored = [
        {
            "id": "s1",
            "title": "Stored with gaps",
            "date": None,
            "author": None,
            "pinned": False,
            "body": "Stored body",
            "tags": None,
        },
    ]

    result = module.get_display_announcements(stored)

    assert len(result) == 2
    assert result[1] == stored[0]
    assert result[1] is stored[0]


def test_get_pinned_winners_announcement_does_not_read_stored_store(load_announcements_page, monkeypatch):
    """Spec behaviour 10."""
    module, _, _ = load_announcements_page()
    import data

    def fail():
        raise AssertionError("stored announcements store was read")

    monkeypatch.setattr(data, "load_announcements", fail)

    ann = module.get_pinned_winners_announcement()
    assert ann["id"] == "pinned-2026-season-winners"


def test_page_renders_pinned_winners_before_stored(load_announcements_page):
    """Spec behaviours 1, 2, 11 and the render-path half of 8."""
    stored = [
        {
            "id": "stored-pinned",
            "title": "STORED PINNED TITLE",
            "date": "2026-01-01",
            "author": "Author",
            "pinned": True,
            "body": "STORED PINNED BODY",
            "tags": ["stored"],
        },
        {
            "id": "stored-normal",
            "title": "STORED NORMAL TITLE",
            "date": "2026-01-02",
            "author": "Author",
            "pinned": False,
            "body": "STORED NORMAL BODY",
            "tags": [],
        },
    ]
    before = copy.deepcopy(stored)

    module, log, save_calls = load_announcements_page(stored)

    text = "\n".join(
        str(value)
        for name, args, kwargs in log
        for value in (*args, *kwargs.values())
    )

    assert "🎉 2026 赛季个人冠军公告" in text
    assert "张纬" in text and "王文龙" in text
    assert "STORED PINNED TITLE" in text
    assert "STORED NORMAL TITLE" in text
    assert text.index("🎉 2026 赛季个人冠军公告") < text.index("STORED PINNED TITLE")
    assert text.index("🎉 2026 赛季个人冠军公告") < text.index("STORED NORMAL TITLE")
    assert stored == before
    assert save_calls == []
