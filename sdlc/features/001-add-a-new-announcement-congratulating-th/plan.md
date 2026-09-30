<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@db96a2f -->
## Approach
Add a fixed display-only 2026 winners announcement and a pure helper in `pages/1_📢_Announcements.py` that prepends it to a copy of the stored list, then make the existing render loop consume that helper while leaving save/delete/import/export paths on the original stored list. Add pytest coverage using a fake Streamlit module so page import is side-effect-free and the render order can be asserted.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| The Announcements page displays the 2026 winners announcement as the first announcement, before all stored announcements. | 1, 2, 11 | Phase 2 |
| The announcement names 张纬 as the 2026 个人联赛 winner and 王文龙 as the 2026 个人杯赛 winner. | 6, 11 | Phase 1 (body), Phase 2 (render) |
| The announcement exposes the same fields as stored announcements: id, title, date, author, pinned, body, tags, with pinned true. | 3, 4, 5, 7 | Phase 1 |
| The announcement is not present in the saved announcements list and does not modify saved announcements. | 8, 9, 10 | Phase 1 (pure helper), Phase 2 (render path) |
| All announcements that already existed remain visible and unchanged. | 2, 8, 9, 11 | Phase 1 (pass-through), Phase 2 (render includes stored) |
| The existing tests still pass. | — | Phase 1, Phase 2 (final whole-suite verification) |

## Phase 1: Add display-only winners announcement helpers
<!-- phase: 1 -->
<!-- targets: pages/1_📢_Announcements.py, tests/test_pinned_winners_announcement.py -->
<!-- frozen: test_streamlit_app.py, features/**, data.py, streamlit_app.py, pages/2_📅_Events.py, pages/3_🏆_League.py, pages/4_🥊_Cup.py, pages/5_⛳_Outing.py, pages/6_💾_API_Data.py, gco_state.json, gco_state_live.json, backup/** -->

**Goal:** The page module exposes the pinned 2026 winners announcement and a pure display-list builder that prepends it without reading or writing stored announcements.

**Changes:**
- `pages/1_📢_Announcements.py`: immediately after the existing import block, add `from typing import Any` if it is not already imported. Then add exactly:

```python
PINNED_2026_WINNERS_ANNOUNCEMENT_ID: str = "pinned-2026-season-winners"

PINNED_2026_WINNERS_ANNOUNCEMENT: dict[str, Any] = {
    "id": PINNED_2026_WINNERS_ANNOUNCEMENT_ID,
    "title": "🎉 2026 赛季个人冠军公告",
    "date": "2026-09-15",
    "author": "GCO 组委会",
    "pinned": True,
    "body": (
        "2026赛季个人荣誉揭晓！\n\n"
        "恭喜 张纬 获得 2026 个人联赛冠军！\n"
        "恭喜 王文龙 获得 2026 个人杯赛冠军！\n\n"
        "感谢所有成员的参与，期待下个赛季再创佳绩！"
    ),
    "tags": ["2026", "冠军"],
}


def get_pinned_winners_announcement() -> dict[str, Any]:
    """Return a fresh copy of the 2026 season winners announcement."""
    announcement = dict(PINNED_2026_WINNERS_ANNOUNCEMENT)
    announcement["tags"] = list(PINNED_2026_WINNERS_ANNOUNCEMENT["tags"])
    return announcement


def get_display_announcements(
    stored_announcements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a new list with the pinned winners announcement first."""
    return [get_pinned_winners_announcement(), *stored_announcements]
```

- `tests/test_pinned_winners_announcement.py`: create this file. Use a fake `streamlit` module so importing the page does not execute real Streamlit UI or touch real widgets. The fixture must patch `data.load_announcements` to return the test list and `data.save_announcements` to record calls. Use this structure:

```python
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
```

Add these tests in the same file:
- `test_pinned_announcement_has_exact_fields`: call `module.get_pinned_winners_announcement()`. Assert `set(ann) == {"id", "title", "date", "author", "pinned", "body", "tags"}`. Assert `ann["id"] == "pinned-2026-season-winners"`. Assert `ann["pinned"] is True`. Assert `"张纬" in ann["body"] and "个人联赛" in ann["body"]`. Assert `"王文龙" in ann["body"] and "个人杯赛" in ann["body"]`. Assert `isinstance(ann["title"], str) and ann["title"]`, same for `date`, `author`, `body`. Assert `isinstance(ann["tags"], list) and all(isinstance(t, str) for t in ann["tags"])`.
- `test_get_pinned_winners_announcement_returns_fresh_copy`: call the accessor twice. Assert equal values, `is not` identity. Append `"mutated"` to `first["tags"]`; assert `"mutated" not in module.PINNED_2026_WINNERS_ANNOUNCEMENT["tags"]` and `"mutated" not in module.get_pinned_winners_announcement()["tags"]`.
- `test_get_display_announcements_empty`: call `module.get_display_announcements([])`. Assert length `1` and `result[0] == module.get_pinned_winners_announcement()`.
- `test_get_display_announcements_pins_first_before_stored_pinned`: use two stored dicts, the first with `"pinned": True`. Deepcopy before. Call helper. Assert `[a["id"] for a in result] == ["pinned-2026-season-winners", "s1", "s2"]`. Assert stored equals the deepcopy.
- `test_get_display_announcements_passes_through_missing_fields`: stored entry with `"author": None`, `"date": None`, `"tags": None`. Call helper. Assert length `2` and `result[1] == stored[0]` and `result[1] is stored[0]`.
- `test_get_pinned_winners_announcement_does_not_read_stored_store`: use `monkeypatch.setattr(data, "load_announcements", fail)` where `fail` raises `AssertionError("stored announcements store was read")`. Call `module.get_pinned_winners_announcement()` and assert `id`.

**Definition of done:**
- [ ] `tests/test_pinned_winners_announcement.py::test_pinned_announcement_has_exact_fields`: proves spec behaviours 3, 4, 5, 6, 7.
- [ ] `tests/test_pinned_winners_announcement.py::test_get_pinned_winners_announcement_returns_fresh_copy`: proves the accessor returns a copy and does not expose the constant’s mutable `tags`.
- [ ] `tests/test_pinned_winners_announcement.py::test_get_display_announcements_empty`: proves spec behaviour 1.
- [ ] `tests/test_pinned_winners_announcement.py::test_get_display_announcements_pins_first_before_stored_pinned`: proves spec behaviour 2.
- [ ] `tests/test_pinned_winners_announcement.py::test_get_display_announcements_passes_through_missing_fields`: proves spec behaviour 9.
- [ ] `tests/test_pinned_winners_announcement.py::test_get_pinned_winners_announcement_does_not_read_stored_store`: proves spec behaviour 10.
- [ ] `tests/test_pinned_winners_announcement.py::test_get_display_announcements_does_not_mutate_stored` is not required as a separate name because the deepcopy assertion in `test_get_display_announcements_pins_first_before_stored_pinned` proves spec behaviour 8.
- [ ] Teardown: the fixture removes every loaded page module from `sys.modules`; `monkeypatch` restores `data.load_announcements`, `data.save_announcements`, and `sys.modules["streamlit"]` automatically.

**Verify:**
```bash
uv run pytest tests/test_pinned_winners_announcement.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Render pinned announcement first
<!-- phase: 2 -->
<!-- targets: pages/1_📢_Announcements.py, tests/test_pinned_winners_announcement.py -->
<!-- frozen: test_streamlit_app.py, features/**, data.py, streamlit_app.py, pages/2_📅_Events.py, pages/3_🏆_League.py, pages/4_🥊_Cup.py, pages/5_⛳_Outing.py, pages/6_💾_API_Data.py, gco_state.json, gco_state_live.json, backup/** -->

**Goal:** The Announcements page render loop obtains its items from `get_display_announcements(...)`, so the pinned winner appears above every stored announcement and no save/delete path sees the display list.

**Changes:**
- `pages/1_📢_Announcements.py`: locate the render loop that consumes the stored announcements list. Introduce `display_announcements = get_display_announcements(stored_announcements)` immediately before that loop and use `display_announcements` only as the loop iterable. Leave the original stored list variable unchanged for save/create/delete/import/export. Do not change the loop body. If the existing code sorts or filters stored announcements before rendering, call `get_display_announcements` after that sort/filter so the pinned synthetic announcement is still prepended to the final render list. Do not add new styling, badges, or layout behaviour.
- `tests/test_pinned_winners_announcement.py`: add `test_page_renders_pinned_winners_before_stored`. Use `load_announcements_page` with a stored list containing one pinned stored announcement and one non-pinned stored announcement:

```python
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
```

In the test:
- `before = copy.deepcopy(stored)`.
- `module, log, save_calls = load_announcements_page(stored)`.
- Flatten the fake Streamlit log to one text string:

```python
text = "\n".join(
    str(value)
    for name, args, kwargs in log
    for value in (*args, *kwargs.values())
)
```

- Assert `"🎉 2026 赛季个人冠军公告" in text`.
- Assert `"张纬" in text and "王文龙" in text`.
- Assert `"STORED PINNED TITLE" in text` and `"STORED NORMAL TITLE" in text`.
- Assert `text.index("🎉 2026 赛季个人冠军公告") < text.index("STORED PINNED TITLE")`.
- Assert `text.index("🎉 2026 赛季个人冠军公告") < text.index("STORED NORMAL TITLE")`.
- Assert `stored == before`.
- Assert `save_calls == []`.

**Definition of done:**
- [ ] `tests/test_pinned_winners_announcement.py::test_page_renders_pinned_winners_before_stored`: proves spec behaviours 1, 2, 11 and the render-path half of spec behaviour 8. The fake Streamlit fixture is torn down via `monkeypatch` and the loaded module name is removed from `sys.modules` in the fixture finalizer.

**Verify:**
```bash
uv run pytest tests/test_pinned_winners_announcement.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- The fake Streamlit fixture may not implement every API the page calls. Phase 2’s page-import/render test would fail with `AttributeError` or missing text. Extend the fake fixture’s no-op/default return values; do not change page behaviour to satisfy the fake.
- The page may already sort or filter stored announcements. Phase 2 asserts only winner-before-stored and stored visibility; Phase 1 asserts prepend order in the helper. If the page sorts after prepending, Phase 2 catches it when a stored pinned title moves above the winner title.
- The page filename contains emoji. Phase 1’s `PAGE_PATH` uses the exact literal path `pages/1_📢_Announcements.py`; a mismatch fails collection.
- The page could accidentally pass the display list to save/delete/import/export. Phase 2 records `save_announcements` calls and asserts none during render; the final whole-suite run catches persisted changes.
- Importing the page module executes its top-level Streamlit code. The fake module prevents real side effects in the targeted tests; the pipeline’s final `python -m pytest -q && behave --format progress` catches real-environment regressions.

## Open questions
None. The spec resolves the intent’s open questions; this plan implements those exact values: 张纬 spelling, title `🎉 2026 赛季个人冠军公告`, date `2026-09-15`, author `GCO 组委会`, id `pinned-2026-season-winners`, tags `["2026", "冠军"]`.

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/001-add-a-new-announcement-congratulating-th/build-log.md` with one section per phase, in order. Head each one `## Phase <n>: <title>`, then list the files changed, the Verify command you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/001-add-a-new-announcement-congratulating-th`.

The pipeline waits for this file. Once it has a section for every phase, it verifies the whole branch and opens the pull request.
