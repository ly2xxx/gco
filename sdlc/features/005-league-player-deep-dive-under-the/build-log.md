# Build log: 005-league-player-deep-dive-under-the

## Phase 1: AI summary core (no UI)
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `ai_summary.py` (new), `tests/test_ai_summary_logic.py` (new).

`ai_summary.py` is the plan's module byte for byte (extracted from the approved plan's code block): `get_ai_config()` reads `OLLAMA_API_KEY`/`OLLAMA_MODEL` with the guarded `st.secrets.get(..., "")` pattern, `build_summary_prompt()` builds a 简体中文 prompt from one player's rounds, and `_call_ollama_chat()` is the single `urllib.request` seam to `https://ollama.com/api/chat`. `tests/test_ai_summary_logic.py` has the plan's helpers (verbatim) and its seventeen tests; every transport test patches `urllib.request.urlopen` and every `summarize_season` test patches `_call_ollama_chat`, so nothing touches the network or needs credentials.

- `uv run pytest tests/test_ai_summary_logic.py -v` (Phase 1 Verify): exit 0, 17 passed.
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 005-league-player-deep-dive-under-the --phase 1`: exit 0, PASSED (scope all inside the targets, no frozen file touched, contract matches; pytest 61 passed, behave 17 scenarios passed).

**Deviations:**
- The test module inserts the repository root into `sys.path` before `import ai_summary`. The Verify block runs `uv run pytest tests/...`, whose `sys.path` holds `tests/` but not the root (the repo has no `conftest.py` or pytest `pythonpath`), so the plan's bare `import ai_summary` cannot resolve. It is the same three lines `tests/test_pinned_announcements.py` uses; the plan's helpers are otherwise copied verbatim.
- Two small helpers, `_configured()` and `_counting_transport()`, hold the repeated "configured secrets" and "counting `_call_ollama_chat` fake" setups the plan's test list describes.
- The header assertion reads `get_header("Content-type")`: `urllib.request.Request` stores header names via `str.capitalize()`, so the plan's `Content-Type == "application/json"` is checked under that key.

## Phase 2: Summary button component
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `ai_summary.py`, `tests/test_ai_season_summary.py` (new).

`ai_summary.py` gains the plan's `render_season_summary()` exactly as given (appended; no other line changed): the `🤖 AI 赛季总结` button, a 无轮次 warning, a spinner around `summarize_season()`, and the summary as markdown or the `AISummaryError` message as `st.error`. `tests/test_ai_season_summary.py` has the plan's helpers (verbatim) and its ten `AppTest.from_string` tests, with `get_ai_config` and `_call_ollama_chat` patched so nothing touches the network.

- `uv run pytest tests/test_ai_summary_logic.py tests/test_ai_season_summary.py -v` (Phase 2 Verify): exit 0, 27 passed.
- First phase check: Verify passed but the whole suite failed (`python -m pytest -q`: 7 failed in `tests/test_upcoming_section_visibility.py`, `KeyError: 'url_pathname'`). Isolated: each file passes alone (9 and 10 passed); together they fail in either order (7 failed / 10 failed). Fixed as below, then both orders pass (19 passed each).
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 005-league-player-deep-dive-under-the --phase 2`: exit 0, PASSED (scope all inside the targets, no frozen file touched, contract matches; Phase 1 and Phase 2 Verify passed; pytest 71 passed, behave 17 scenarios passed).

**Deviations:**
- `tests/test_ai_season_summary.py` has an autouse fixture that sets `streamlit.runtime.pages_manager.PagesManager.uses_pages_directory` to `None` through `monkeypatch` for each test. Streamlit sets that class flag once per process, from the first `AppTest` script's folder (does it contain `pages/`?). The plan's harness runs from a temp folder without `pages/`, which leaves the flag `False` and makes the later front-page `AppTest` in `tests/test_upcoming_section_visibility.py` fail on `st.page_link` (`KeyError: 'url_pathname'`); in the other order the flag is `True` and the harness page fails ("The title of the page cannot be empty"). Resetting it per test, and letting `monkeypatch` restore the previous value, keeps both modules independent without touching the frozen feature-004 test.
- The same three-line repo-root `sys.path` insertion as Phase 1, so `uv run pytest tests/...` can import `ai_summary`; `from pathlib import Path` serves both it and `test_summary_flow_needs_no_admin_token`'s source check.
- One helper, `_record_transport()`, holds the recording `_call_ollama_chat` fake the plan's tests describe.

## Phase 3: Wire into the League deep-dive
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `pages/3_🏆_League.py` (two added lines), `tests/test_league_deep_dive_wiring.py` (new).

`pages/3_🏆_League.py` imports `render_season_summary` directly after its `from data import ...` line and calls `render_season_summary(selected, p_df.to_dict(orient="records"))` as the statement right after `c4.metric("总老鹰数", ...)`, inside `if not p_df.empty:`; `selected` is the deep-dive `selectbox` value and `p_df` holds only that player's played rounds. `tests/test_league_deep_dive_wiring.py` has the plan's two tests, bodies unchanged.

- Phase 3 Verify, each command alone: `uv run pytest tests/test_league_deep_dive_wiring.py -v` exit 0, 2 passed; `uv run pytest tests/test_ai_summary_logic.py tests/test_ai_season_summary.py -q` exit 0, 27 passed; `uv run pytest test_streamlit_app.py tests/test_announcement_page_wiring.py tests/test_pinned_announcements.py tests/test_pinned_winners_announcement.py tests/test_upcoming_section_visibility.py -q` exit 0, 44 passed; `uv run behave --format progress` exit 0, 17 scenarios passed.
- With the plan's test file exactly as written: `uv run pytest tests/test_league_deep_dive_wiring.py` failed at collection (`ModuleNotFoundError: No module named 'ai_summary'`), and `python -m pytest -q` had 7 failures in `tests/test_upcoming_section_visibility.py` (`KeyError: 'url_pathname'`). Both fixed as below.
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 005-league-player-deep-dive-under-the --phase 3`: exit 0, PASSED (scope all inside the targets, no frozen file touched, contract matches; Phase 1-3 Verify passed; pytest 73 passed, behave 17 scenarios passed).
- `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=.venv` (CI's fatal lint): 0, exit 0.
- Extra check, not in the plan and not committed: `AppTest.from_file("pages/3_🏆_League.py")` with `_call_ollama_chat` and `get_ai_config` stubbed renders the button for the default player 刘北南 with no exception; clicking it shows the stubbed summary, and the prompt holds that player's one played round and no other player's name. With the real (empty) secrets, clicking shows `AI 服务未配置：请在 secrets 中设置 OLLAMA_API_KEY 和 OLLAMA_MODEL。` and no exception.

**Deviations:**
- `tests/test_league_deep_dive_wiring.py` adds, around the plan's unchanged test bodies, the three-line repo-root `sys.path` insertion (as in Phases 1 and 2) and the same autouse `PagesManager.uses_pages_directory` reset fixture as `tests/test_ai_season_summary.py`. The League page's folder has no `pages/` inside it, so its `AppTest` otherwise leaves the per-process flag `False` and the later front-page `AppTest`s in `tests/test_upcoming_section_visibility.py` fail on `st.page_link`.
