# Build log: 007-follow-up-q-a-under-the

## Phase 1: `render_season_summary` returns the summary text
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `ai_summary.py`, `tests/test_ai_season_summary_return.py` (new).

`render_season_summary()` is the plan's version verbatim: it returns the summary it rendered and `""` on every no-summary path, with the same selector, button, warning and error output as before. `tests/test_ai_season_summary_return.py` has the plan's `make_fake_streamlit()`/`exploding()` helpers and its six tests.

- `uv run pytest tests/test_ai_season_summary_return.py tests/test_ai_season_summary.py tests/test_ai_summary_logic.py tests/test_ai_summary_language_logic.py tests/test_ai_summary_language_ui.py -v` (Verify): exit 0, 59 passed.
- The same files and the whole suite (`python -m pytest -q`: 105 passed; `behave --format progress`: 17 scenarios passed) pass on Streamlit 1.55 (`uv.lock`) and 1.64 (`requirements.txt`, as CI installs it).
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 007-follow-up-q-a-under-the --phase 1`: exit 0, PASSED (scope all inside the targets, no frozen file touched, contract matches).

**Deviations:**
- The new test module inserts the repository root into `sys.path` before `import ai_summary` (as feature 005's tests do): the Verify block runs `uv run pytest tests/...`, whose `sys.path` holds `tests/` but not the root. The plan's helpers are otherwise verbatim.

## Phase 2: Follow-up constants, prompt builder, answer call and session history
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `ai_summary.py`, `tests/test_ai_follow_up_logic.py` (new).

`ai_summary.py` gains the plan's `FOLLOW_UP_*`, `EMPTY_QUESTION_MESSAGE` and `MISSING_ROUNDS_NOTE*` constants (after `PROMPT_INSTRUCTION_EN`) and its four functions (after `summarize_season`), verbatim from the plan: `build_follow_up_prompt()`, `answer_follow_up_question()`, `get_follow_up_history()` and `append_follow_up_turn()`. `tests/test_ai_follow_up_logic.py` has the plan's helpers and its fifteen tests.

- `uv run pytest tests/test_ai_follow_up_logic.py tests/test_ai_season_summary_return.py -v` (Verify): exit 0, 21 passed.
- The same files and the whole suite (`python -m pytest -q`: 120 passed; `behave --format progress`: 17 scenarios passed) pass on Streamlit 1.55 and 1.64.
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 007-follow-up-q-a-under-the --phase 2`: exit 0, PASSED.

**Deviations:**
- The same repo-root `sys.path` insertion as Phase 1 before `import ai_summary`; the plan's helpers are otherwise verbatim.

## Phase 3: The `render_follow_up_questions` fragment
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `ai_summary.py`, `tests/test_ai_follow_up_ui.py` (new).

`ai_summary.py` gains `FOLLOW_UP_FORM_KEY` (next to the other `FOLLOW_UP_*` constants) and the plan's `@st.fragment` `render_follow_up_questions()` directly below `render_season_summary()`, verbatim: it renders the stored turns, a `st.form` with the question input and 提问 / Ask button, and on submit shows the answer (storing the turn) or a readable message. `tests/test_ai_follow_up_ui.py` has the plan's helpers (calling the function through `__wrapped__`, which `st.fragment` sets on both Streamlit 1.55 and 1.64) and its twelve tests.

- `uv run pytest tests/test_ai_follow_up_ui.py tests/test_ai_follow_up_logic.py tests/test_ai_season_summary_return.py -v` (Verify): exit 0, 33 passed.
- The same files and the whole suite (`python -m pytest -q`: 132 passed; `behave --format progress`: 17 scenarios passed) pass on Streamlit 1.55 and 1.64.
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 007-follow-up-q-a-under-the --phase 3`: exit 0, PASSED.

**Deviations:**
- The same repo-root `sys.path` insertion as Phases 1 and 2; one helper, `_patch()`, holds the `st` / `get_ai_config` / `_call_ollama_chat` patching every test in the plan describes.

## Phase 4: League page wiring
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `pages/3_🏆_League.py`, `tests/test_league_follow_up_wiring.py` (new).

The League page now keeps `render_season_summary()`'s return value as `summary` and, only when it is non-empty, calls `render_follow_up_questions(player_name, season_rounds, summary)` on the next lines, so the Q&A area sits directly under the summary and above the score-trend chart. `tests/test_league_follow_up_wiring.py` has the plan's `LEAGUE_PAGE`/`SOURCE`/`LINES`/`line_indexes()`/`follow_up_call_indexes()` helpers and its two source-inspection tests.

- `uv run pytest tests/test_league_follow_up_wiring.py tests/test_league_deep_dive_wiring.py tests/test_ai_follow_up_ui.py -v` (Verify): exit 0, 16 passed. Same result on Streamlit 1.64 (`requirements.txt`, as CI installs it).
- Whole suite: `python -m pytest -q`: 134 passed; `behave --format progress`: 17 scenarios passed, on Streamlit 1.55 and 1.64.
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 007-follow-up-q-a-under-the --phase 4`: exit 0, PASSED.
- `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`: 0.
- Browser check (not committed): the real League page under Streamlit 1.64 with only `get_ai_config` and `_call_ollama_chat` stubbed, driven by Playwright/Chromium. Pressing 🤖 AI 赛季总结 showed the summary; two follow-up questions each showed their answer (the second prompt carried the first turn) while the summary and earlier turns stayed on screen and the input cleared; an empty submit showed `请先输入问题再提交。`.

**Deviations:**
- Import: the plan says to change `from ai_summary import render_season_summary` to `from ai_summary import render_follow_up_questions, render_season_summary`. That would break the frozen `tests/test_league_deep_dive_wiring.py`, which looks for the exact substring `from ai_summary import render_season_summary` (with the comma-separated form it no longer matches). So that line stays as it is and a second line, `from ai_summary import render_follow_up_questions`, follows it.
- Call-site names: the plan assumes the page calls `render_season_summary(player_name, season_rounds)`; the page actually called `render_season_summary(selected, p_df.to_dict(orient="records"))`. The page now sets `player_name = selected` and `season_rounds = p_df.to_dict(orient="records")` first, so the plan's three lines (and the argument-order regex in its test) apply verbatim.
- Guard regex: the plan's `line_indexes(r"^if summary:\s*$")` cannot match an indented `if summary:`, and the call sits inside the page's `if not p_df.empty:` block (the plan says to keep the page's current indentation). With the plan's pattern the guard list was `[]`; the test uses `r"^\s*if summary:\s*$"`, which finds the guard at line index 174. The indentation assertion (call deeper than guard) is kept as written.
