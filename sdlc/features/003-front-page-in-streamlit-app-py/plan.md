<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@ea50231 -->

## Approach

Create one new module `pinned_announcements.py` that holds the pinned announcement records (copied byte-identically from the copies currently in `streamlit_app.py` and `pages/1_📢_Announcements.py`) plus a single `get_display_announcements(announcements=None)` selector, then delete the two page-local copies and have both pages import the shared helper, keeping each page's own `[:2]` cap and body truncation at the call site. Phase 1 adds and unit-tests the module while both pages keep working as they do today; Phase 2 rewires the home page; Phase 3 rewires the Announcements page and proves by parsing every application file that the records and the helper now exist in exactly one place, and that both pages derive the same pinned sequence for the same data.

## Coverage

| Done when (intent.md)                                                                                                                                                                              | Spec behaviours       | Phase                                                               |
| :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------- | :------------------------------------------------------------------ |
| The pinned announcement records are defined in exactly one place in the codebase, and that place is`pinned_announcements.py`.                                                                    | 1, 2                  | 1 (module created) and 3 (duplicates removed and uniqueness proven) |
| `get_display_announcements()` is defined in exactly one place, is importable from `pinned_announcements.py`, and is imported by both `streamlit_app.py` and `pages/1_📢_Announcements.py`. | 1, 2, 3, 4            | 1 (defined) and 2, 3 (imported by both pages)                       |
| Neither page contains a local pinned-records definition or a local copy of the display-selection logic.                                                                                            | 3, 4                  | 2 (home page) and 3 (Announcements page)                            |
| For the same underlying announcement data, the home page's 最新动态 block and the Announcements page surface the same pinned announcements in the same order.                                      | 5, 6, 7, 8, 9, 10, 11 | 1 (ordering contract) and 3 (cross-page proof)                      |
| The existing tests still pass.                                                                                                                                                                     | 12                    | 2 and 3 (imports updated) plus whole-suite verification             |

## Phase 1: Shared pinned-announcements module

<!-- phase: 1 -->

<!-- targets: pinned_announcements.py, tests/test_pinned_announcements.py -->

<!-- frozen: streamlit_app.py, pages/1_📢_Announcements.py, data.py, auth.py, theme.py, test_streamlit_app.py, tests/test_pinned_winners_announcement.py, pyproject.toml, requirements.txt -->

**Goal:** `import pinned_announcements` works with no Streamlit, no secrets and no I/O, and `get_display_announcements` returns module pinned records first, extra pinned records next, remaining records last, without mutating or truncating.

**Changes:**

- `pinned_announcements.py` (new file, repository root, sibling of `data.py`): create it with exactly this content, substituting the full verbatim record list:

```python
"""Single home for the pinned announcement records and the shared display selector.

Both the home page (``streamlit_app.py``, the 最新动态 block) and the
Announcements page (``pages/1_📢_Announcements.py``) import
``get_display_announcements`` from here. Importing this module must stay free of
I/O, Streamlit imports and network access.
"""
from __future__ import annotations


PINNED_ANNOUNCEMENTS: list[dict] = [
    # ... verbatim copy of the module-level pinned list literal ...
]


def get_display_announcements(announcements: list[dict] | None = None) -> list[dict]:
    """Return the announcements to display, pinned records first.

    Order: the records in ``PINNED_ANNOUNCEMENTS`` (in that order), then any
    additional pinned records from ``announcements`` in input order, then the
    remaining input records in input order. Input records whose ``id`` already
    appears in ``PINNED_ANNOUNCEMENTS`` are not repeated. The argument is never
    mutated and the result is never truncated.
    """
    if not announcements:
        return list(PINNED_ANNOUNCEMENTS)

    known_ids = {record.get("id") for record in PINNED_ANNOUNCEMENTS}
    remaining = [record for record in announcements if record.get("id") not in known_ids]
    extra_pinned = [record for record in remaining if record.get("pinned")]
    others = [record for record in remaining if not record.get("pinned")]

    return list(PINNED_ANNOUNCEMENTS) + extra_pinned + others
```

  For `PINNED_ANNOUNCEMENTS`, open `streamlit_app.py`, locate the module-level list literal of announcement dicts whose entries all have `"pinned": True` (the list the page's 最新动态 block used before this change), and copy those dicts **verbatim**: same key order, same `id`/`title`/`date`/`author`/`body` strings, same unicode and embedded `\n` newlines, same `tags` lists. Open `pages/1_📢_Announcements.py` and confirm its module-level pinned list is identical; if it is not, keep the `streamlit_app.py` copy (the home page must not change visibly) and record the difference in `build-log.md`. Do not change either page in this phase — the page-local lists and helpers stay until Phase 2 and Phase 3.

- No other file changes. No new dependency: `pinned_announcements.py` must not import `streamlit`, `data`, `auth` or `theme`, and must not read or write files.

**Definition of done:**

- [ ] `tests/test_pinned_announcements.py` (new file). Its header must be exactly:

```python
import copy
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pinned_announcements import PINNED_ANNOUNCEMENTS, get_display_announcements  # noqa: E402


def _ann(ann_id: str, pinned=None, **extra) -> dict:
    """iBuild a minimal input record; omit the pinned key when pinned is None."""
    record = {
        "id": ann_id,
        "title": f"title-{ann_id}",
        "date": "2026-01-01",
        "author": "author",
        "body": "body",
        "tags": [],
    }
    if pinned is not None:
        record["pinned"] = pinned
    record.update(extra)
    return record


PINNED_IDS = [record["id"] for record in PINNED_ANNOUNCEMENTS]
```

  All tests are pure and need no fixtures, threads, servers or teardown; none touches the network.

- [ ] `tests/test_pinned_announcements.py::test_module_exposes_records_and_helper` — proves spec behaviour 1. Assert `isinstance(PINNED_ANNOUNCEMENTS, list)`, `PINNED_ANNOUNCEMENTS` is non-empty, `all(isinstance(record, dict) for record in PINNED_ANNOUNCEMENTS)`, `callable(get_display_announcements)`, and for each record `set(record) >= {"id", "title", "date", "author", "pinned", "body", "tags"}` with `record["pinned"] is True` and `isinstance(record["tags"], list)`.
- [ ] `tests/test_pinned_announcements.py::test_import_is_side_effect_free_and_streamlit_free` — proves spec behaviour 1 (no import-time side effects, I/O or exceptions). Run `subprocess.run([sys.executable, "-c", CODE], cwd=REPO_ROOT, env={**os.environ, "PYTHONPATH": str(REPO_ROOT)}, capture_output=True, text=True, check=True)` where `CODE` is a one-liner that imports `sys` and `pinned_announcements`, asserts `PINNED_ANNOUNCEMENTS` is a non-empty list of dicts, asserts `callable(p.get_display_announcements)`, and asserts `"streamlit" not in sys.modules`. Then assert `_proc.stdout == ""` and `_proc.stderr == ""`.
- [ ] `tests/test_pinned_announcements.py::test_pinned_records_come_before_non_pinned` — proves spec behaviour 5. Input `[_ann("x-1", pinned=False), _ann("x-2", pinned=True), _ann("x-3")]`; assert `result[:len(PINNED_ANNOUNCEMENTS)] == PINNED_ANNOUNCEMENTS`, `result[len(PINNED_ANNOUNCEMENTS)]["id"] == "x-2"`, and `[item["id"] for item in result] == PINNED_IDS + ["x-2", "x-1", "x-3"]`.
- [ ] `tests/test_pinned_announcements.py::test_module_records_then_extra_pinned_then_rest` — proves spec behaviour 6. Input `[_ann("n-1"), _ann("p-extra", pinned=True), _ann("n-2"), _ann("p-extra-2", pinned=True)]`; assert the returned ids equal `PINNED_IDS + ["p-extra", "p-extra-2", "n-1", "n-2"]`.
- [ ] `tests/test_pinned_announcements.py::test_module_record_is_not_duplicated_by_input` — proves spec behaviour 6 ("additional pinned input records"): dedupe by `id`. Input `[{**PINNED_ANNOUNCEMENTS[0], "title": "changed-in-input"}]`; assert the returned list equals `PINNED_ANNOUNCEMENTS` (length and contents), i.e. the module copy wins and the announcement is not shown twice.
- [ ] `tests/test_pinned_announcements.py::test_none_and_empty_return_the_module_records` — proves spec behaviour 7. Assert `get_display_announcements(None) == PINNED_ANNOUNCEMENTS`, `get_display_announcements([]) == PINNED_ANNOUNCEMENTS`, and `get_display_announcements(None) is not PINNED_ANNOUNCEMENTS` (a fresh list, so callers cannot mutate module state).
- [ ] `tests/test_pinned_announcements.py::test_missing_none_or_false_pinned_goes_to_non_pinned_group` — proves spec behaviour 8. Input `[_ann("no-key"), _ann("none-value", pinned=None), _ann("false-value", pinned=False)]`; assert `[item["id"] for item in result] == PINNED_IDS + ["no-key", "none-value", "false-value"]`.
- [ ] `tests/test_pinned_announcements.py::test_call_is_pure_and_repeatable` — proves spec behaviour 9. Build `input_list = [_ann("n-1"), _ann("p-1", pinned=True)]`, take `snapshot = copy.deepcopy(input_list)`, call twice; assert `first == second`, `first is not second`, and `input_list == snapshot` (no mutation of the argument or module state, verified again by asserting `PINNED_ANNOUNCEMENTS` still equals a deep-copied snapshot taken before the calls).
- [ ] `tests/test_pinned_announcements.py::test_result_is_not_truncated` — proves spec behaviour 10. Input `[_ann(f"n-{i}") for i in range(5)]`; assert `len(result) == len(PINNED_ANNOUNCEMENTS) + 5` and that all five ids survive in order, i.e. no "2 results" cap is applied inside the function.
- [ ] Observable check, no truncation of the module itself: `uv run python -c "import pinned_announcements as p; print(len(p.PINNED_ANNOUNCEMENTS), [a['id'] for a in p.get_display_announcements(None)])"` prints the number of pinned records followed by their ids, in module order, with no traceback.

**Verify:**

```bash
uv run pytest tests/test_pinned_announcements.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Home page uses the shared selector

<!-- phase: 2 -->

<!-- targets: streamlit_app.py, test_streamlit_app.py, tests/test_pinned_winners_announcement.py, tests/test_announcement_page_wiring.py -->

<!-- frozen: pinned_announcements.py, pages/1_📢_Announcements.py, data.py, auth.py, theme.py, tests/test_pinned_announcements.py, pyproject.toml, requirements.txt -->

**Goal:** `streamlit_app.py` contains no pinned-record literal and no local `get_display_announcements`, imports the helper from `pinned_announcements`, and its 最新动态 block still shows the same two announcements as before (same order, same truncation, same markup).

**Changes:**

- `streamlit_app.py`:
  - Add `from pinned_announcements import get_display_announcements` after the existing first-party imports (`data` / `theme`), before any Streamlit page code runs.
  - Delete the module-level pinned-record list literal that was copied into `pinned_announcements.py` in Phase 1.
  - Delete the local `def get_display_announcements(...)` function.
  - At the 最新动态 call site, replace the deleted local name with the imported one: `get_display_announcements(<the same announcements expression the local call used>)`; if the local call took no argument, call `get_display_announcements()`. Keep the existing `[:2]` slice, the body truncation, the card markup, tags and styling exactly as they are. Do not rename any other public name and do not change the preview-only presentation.
- `test_streamlit_app.py`: change nothing unless it imports `get_display_announcements`/the pinned list from `streamlit_app` or asserts that the pinned literal appears in `streamlit_app.py`'s source. If it does, point the import at `from pinned_announcements import PINNED_ANNOUNCEMENTS, get_display_announcements` and replace source-literal assertions with assertions on `PINNED_ANNOUNCEMENTS`; keep every other assertion untouched.
- `tests/test_pinned_winners_announcement.py`: replace the import of the relocated names with `from pinned_announcements import PINNED_ANNOUNCEMENTS, get_display_announcements` (keep the test logic; if it asserted the pinned announcement exists in a page's source text, assert membership in `PINNED_ANNOUNCEMENTS` instead — page-source assertions belong to `tests/test_announcement_page_wiring.py`).
- `tests/test_announcement_page_wiring.py` (new file) — source-parsing and selection tests, no Streamlit execution, no fixtures or teardown. Header and helpers:

```python
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pinned_announcements import PINNED_ANNOUNCEMENTS, get_display_announcements  # noqa: E402

HOME_PAGE = REPO_ROOT / "streamlit_app.py"
ANNOUNCEMENTS_PAGE = REPO_ROOT / "pages" / "1_📢_Announcements.py"
APP_FILES = [
    REPO_ROOT / "streamlit_app.py",
    REPO_ROOT / "data.py",
    REPO_ROOT / "auth.py",
    REPO_ROOT / "theme.py",
    REPO_ROOT / "pinned_announcements.py",
    *sorted((REPO_ROOT / "pages").glob("*.py")),
    *sorted((REPO_ROOT / "utilities").glob("*.py")),
]
RELOCATED_NAMES = {"PINNED_ANNOUNCEMENTS", "get_display_announcements"}


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _import_sources(tree: ast.Module) -> dict[str, set[str]]:
    """Map local name -> set of modules it is imported from."""
    sources: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                sources.setdefault(alias.asname or alias.name, set()).add(node.module)
    return sources


def _defines_helper(tree: ast.Module) -> bool:
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "get_display_announcements"
        for node in ast.walk(tree)
    )


def _has_module_level_pinned_literal(tree: ast.Module) -> bool:
    """True for a module-level list/tuple literal of dicts that all have pinned=True."""
    def is_all_pinned(value: ast.AST) -> bool:
        if not isinstance(value, (ast.List, ast.Tuple)) or not value.elts:
            return False
        for element in value.elts:
            if not isinstance(element, ast.Dict):
                return False
            pairs = dict(zip(element.keys, element.values))
            key = pairs.get(ast.Constant(value="pinned"))
            if not (isinstance(key, ast.Constant) and key.value is True):
                return False
        return True

    for node in tree.body:
        if isinstance(node, ast.Assign) and is_all_pinned(node.value):
            return True
        if isinstance(node, ast.AnnAssign) and node.value is not None and is_all_pinned(node.value):
            return True
    return False
```

  Phase 2 adds these tests to that file (Phase 3 extends the same file):

- [ ] `tests/test_announcement_page_wiring.py::test_home_page_imports_shared_helper` — proves spec behaviour 3: `"pinned_announcements" in _import_sources(_tree(HOME_PAGE)).get("get_display_announcements", set())`.
- [ ] `tests/test_announcement_page_wiring.py::test_home_page_has_no_local_pinned_records_or_helper` — proves spec behaviour 3: assert `_has_module_level_pinned_literal(_tree(HOME_PAGE))` is `False` and `_defines_helper(_tree(HOME_PAGE))` is `False`.
- [ ] `tests/test_announcement_page_wiring.py::test_home_page_calls_the_shared_helper` — proves spec behaviour 11 (home side): assert the `streamlit_app.py` tree contains at least one `ast.Call` whose `func` is `ast.Name(id="get_display_announcements")`.
- [ ] `tests/test_announcement_page_wiring.py::test_home_page_selection_is_the_shared_selection` — proves spec behaviours 5, 6: with `sample = [{"id": "n-1", "pinned": False}, {"id": "p-extra", "pinned": True}]` (plus the required keys), assert `[a["id"] for a in get_display_announcements(sample)[:2]] == [record["id"] for record in PINNED_ANNOUNCEMENTS][:2]`, i.e. the 最新动态 cap keeps the first two module pinned records in module order.
- [ ] `tests/test_announcement_page_wiring.py::test_no_file_imports_relocated_names_from_old_locations` — proves spec behaviour 12: for every file in `APP_FILES`, `REPO_ROOT.glob("test_*.py")`, `(REPO_ROOT / "tests").glob("*.py")` and `(REPO_ROOT / "features").rglob("*.py")`, assert that for each relocated name in `_import_sources(_tree(path))`, the only allowed source module is `pinned_announcements` (collect violations into a list and assert the list is empty, so the failure message names the offender).
- [ ] Observable check: `uv run python -c "import ast, pathlib; tree = ast.parse(pathlib.Path('streamlit_app.py').read_text(encoding='utf-8')); print(sum(isinstance(n, ast.FunctionDef) and n.name == 'get_display_announcements' for n in ast.walk(tree)))"` prints `0`.

**Definition of done:**

- [ ] `tests/test_announcement_page_wiring.py` passes with the five tests above, proving the home page no longer owns pinned records or the selector and that no file imports the relocated names from the old locations.
- [ ] No stale import of the relocated names remains in `test_streamlit_app.py` or `tests/test_pinned_winners_announcement.py` (enforced by `test_no_file_imports_relocated_names_from_old_locations`).
- [ ] `uv run pytest tests/test_pinned_announcements.py -v` (Phase 1's block) still passes unchanged; `pinned_announcements.py` is frozen in this phase.
- [ ] Observable check above prints `0`.

**Verify:**

```bash
uv run pytest tests/test_announcement_page_wiring.py tests/test_pinned_announcements.py tests/test_pinned_winners_announcement.py test_streamlit_app.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 3: Announcements page uses the shared selector and uniqueness is proven

<!-- phase: 3 -->

<!-- targets: pages/1_📢_Announcements.py, tests/test_announcement_page_wiring.py, tests/test_pinned_winners_announcement.py -->

<!-- frozen: streamlit_app.py, pinned_announcements.py, data.py, auth.py, theme.py, tests/test_pinned_announcements.py, test_streamlit_app.py, pyproject.toml, requirements.txt -->

**Goal:** `pages/1_📢_Announcements.py` holds no pinned records and no local selector, and parsing all application Python files shows the records and `get_display_announcements` exist only in `pinned_announcements.py`.

**Changes:**

- `pages/1_📢_Announcements.py`:
  - Add `from pinned_announcements import get_display_announcements` after the existing first-party imports, before any Streamlit page code runs.
  - Delete the module-level pinned-record list literal (the copy that was kept in Phase 1/2).
  - Delete the local `def get_display_announcements(...)` function.
  - At each call site replace the deleted local name with the imported one, passing the same announcements expression (or no argument if the local call took none). Keep the page's existing cap (`[:2]` if it applies one, otherwise render the full list), card markup, tags and styling unchanged.
- `tests/test_announcement_page_wiring.py`: append these tests using the helpers already defined in Phase 2:
  - [ ] `tests/test_announcement_page_wiring.py::test_announcements_page_imports_shared_helper` — proves spec behaviour 4: `"pinned_announcements" in _import_sources(_tree(ANNOUNCEMENTS_PAGE)).get("get_display_announcements", set())`.
  - [ ] `tests/test_announcement_page_wiring.py::test_announcements_page_has_no_local_pinned_records_or_helper` — proves spec behaviour 4: assert `_has_module_level_pinned_literal(_tree(ANNOUNCEMENTS_PAGE))` is `False` and `_defines_helper(_tree(ANNOUNCEMENTS_PAGE))` is `False`.
  - [ ] `tests/test_announcement_page_wiring.py::test_announcements_page_calls_the_shared_helper` — proves spec behaviour 11 (Announcements side): the page tree contains at least one `ast.Call` with `func=ast.Name(id="get_display_announcements")`.
  - [ ] `tests/test_announcement_page_wiring.py::test_only_shared_module_defines_records_or_helper` — proves spec behaviour 2: over `APP_FILES`, assert `{path.name for path in APP_FILES if _has_module_level_pinned_literal(_tree(path))} == {"pinned_announcements.py"}` and `{path.name for path in APP_FILES if _defines_helper(_tree(path))} == {"pinned_announcements.py"}`.
  - [ ] `tests/test_announcement_page_wiring.py::test_both_pages_share_one_pinned_sequence` — proves spec behaviours 5, 6, 11 for one identical input list: build `sample` from `PINNED_ANNOUNCEMENTS` plus an extra pinned record `{"id": "p-extra", "pinned": True, ...}` and two non-pinned records; compute `home_ids = [a["id"] for a in get_display_announcements(sample)[:2]]` (home page's cap) and `announcements_ids = [a["id"] for a in get_display_announcements(sample)]`; assert `home_ids == announcements_ids[:2]` and `home_ids == [record["id"] for record in PINNED_ANNOUNCEMENTS][:2]`, so both pages derive the same pinned `id` sequence from the same data via the single shared function.
- `tests/test_pinned_winners_announcement.py`: finish any remaining page-source assertion by pointing it at the two page files' import of `pinned_announcements` (or remove it where `tests/test_announcement_page_wiring.py` now proves the same thing); the test file's other assertions must keep passing.

**Definition of done:**

- [ ] All nine tests in `tests/test_announcement_page_wiring.py` pass; the two pages are proven to import the shared helper and to define neither pinned records nor a local selector, and `pinned_announcements.py` is proven to be the only application file that defines either.
- [ ] `tests/test_pinned_announcements.py` (Phase 1) and `test_streamlit_app.py` (Phase 2) are unchanged and still pass.
- [ ] A repository-wide scan finds no stale import of `PINNED_ANNOUNCEMENTS` or `get_display_announcements` from `streamlit_app` or from the Announcements page (Phase 2 test, re-run in this phase's Verify).

**Verify:**

```bash
uv run pytest tests/test_announcement_page_wiring.py tests/test_pinned_announcements.py tests/test_pinned_winners_announcement.py -v
test -z "$(grep -n 'def get_display_announcements' streamlit_app.py 'pages/1_📢_Announcements.py' || true)"
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks

- **The copied record literal drifts from the original.** Phase 3's `test_only_shared_module_defines_records_or_helper` proves a single source, but not byte-identity. Reviewers should diff the new list against the approved tag with `git show sdlc/003-front-page-in-streamlit-app-py/approved:streamlit_app.py`.
- **A pinned announcement is rendered twice** because the loaded data already contains a record whose `id` is in `PINNED_ANNOUNCEMENTS`. Caught by Phase 1's `test_module_record_is_not_duplicated_by_input` and Phase 3's `test_both_pages_share_one_pinned_sequence`.
- **The "2 results" cap leaks into the shared function** and changes the Announcements page. Caught by Phase 1's `test_result_is_not_truncated`.
- **The removed page-local helpers ordered or deduplicated differently from the spec.** The spec is authoritative; Phase 3's cross-page test and Phase 1's ordering tests catch a mismatch, and the difference must be recorded in the build log.
- **Import-time side effects in the new module** (accidentally importing `streamlit`/`data`, which attempts GitHub access in `data.py`). Caught by Phase 1's `test_import_is_side_effect_free_and_streamlit_free`.
- **An existing test still imports the relocated names from a page.** Caught by Phase 2's `test_no_file_imports_relocated_names_from_old_locations` and by the whole-suite run.
- **Emoji filename handling in shell checks.** The page path is always single-quoted in commands and read via `pathlib`, so no globbing or locale-dependent expansion occurs.

## Open questions

- The bodies of the two page-local helpers were not visible when this plan was written. Assumption: the canonical implementation given in Phase 1 (module records first, de-duplicated by `id`, then additional pinned input records, then the rest, no truncation, no mutation) matches the current ordering, and only its location changes. If a page helper ordered records differently, the spec in `sdlc/features/003-front-page-in-streamlit-app-py/spec.md` wins and the difference goes in `build-log.md`.
- Assumption: the pinned literals in `streamlit_app.py` and `pages/1_📢_Announcements.py` are identical. If they are not, the `streamlit_app.py` copy is used so the home page stays visually unchanged, and the difference is recorded in `build-log.md`.
- Assumption: the dedupe-by-`id` reading of "additional pinned input records" (spec behaviour 6) is intended, so an input record whose `id` is already in `PINNED_ANNOUNCEMENTS` is not repeated even when it is pinned.
- Assumption: spec behaviour 2's "every `*.py` file" is checked over application files (`streamlit_app.py`, `data.py`, `auth.py`, `theme.py`, `pages/*.py`, `utilities/*.py`, and `pinned_announcements.py`) so that pre-existing test fixtures that construct pinned-looking dicts are not treated as duplicate definitions; the two pages are additionally checked individually by `test_home_page_has_no_local_pinned_records_or_helper` and `test_announcements_page_has_no_local_pinned_records_or_helper`. The stale-import half of behaviour 12 *is* checked across test and feature files.
- Assumption: the pinned literals are written as plain list-of-dict literals with `"pinned": True`, which is what the AST check in `_has_module_level_pinned_literal` matches. If a page builds its list programmatically, the manual review of the Phase 3 diff covers it.

## Hand back

When every phase is built and its Verify block passes:

1. Create `sdlc/features/003-front-page-in-streamlit-app-py/build-log.md` with one section per phase, in order. Head each one `## Phase <n>: <title>`, then list the files changed, the Verify command you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/003-front-page-in-streamlit-app-py`.
