# Build log: 008-league-ai-summary-add-a-download

## Phase 1: Transcript text and file-name helpers
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `ai_summary.py`, `tests/test_ai_transcript_text.py` (new).

`ai_summary.py` gains the `re`/`datetime` imports, the plan's `DOWNLOAD_BUTTON_*`/`TRANSCRIPT_*` constants and four private regexes (after `MISSING_ROUNDS_NOTE_EN`), and `_transcript_safe_text()`, `_transcript_turns()`, `build_transcript_text()` and `build_transcript_filename()` (after `append_follow_up_turn`), as written in the plan. `tests/test_ai_transcript_text.py` holds the plan's nine pure-function tests.

- `uv run pytest tests/test_ai_transcript_text.py tests/test_ai_follow_up_logic.py -v` (Verify): exit 0, 24 passed.
- `uv run python -c "import datetime, ai_summary; assert ai_summary.build_transcript_filename('Neo', datetime.datetime(2026, 1, 2, 3, 4, 5)) == 'gco_league_ai_summary_Neo_20260102_030405.txt', 'unexpected filename'"` (Verify): exit 0, no output.
- The same files and the whole suite (`python -m pytest -q`: 143 passed; `behave --format progress`: 17 scenarios passed) pass on Streamlit 1.55 (`uv.lock`) and 1.64 (`requirements.txt`, as CI installs it).
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 008-league-ai-summary-add-a-download --phase 1`: exit 0, PASSED (scope inside the targets, no frozen file touched, contract matches).
- `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`: 0.

**Deviations:**
- The new test module inserts the repository root into `sys.path` before `import ai_summary as m`, as features 005–007's tests do: the Verify block runs `uv run pytest tests/...`, whose `sys.path` holds `tests/` but not the root.
- `build_transcript_filename`'s docstring writes the backslash as `\\` instead of the plan's bare `\ `, which Python 3.12 reports as an invalid escape sequence (`SyntaxWarning`). The docstring's value is the same string.

## Phase 2: Render the download control inside the follow-up fragment
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `ai_summary.py`, `tests/test_ai_follow_up_download_ui.py` (new).

`render_follow_up_questions()` now has the plan's body. The guard for a blank summary runs before any session-state read. An empty question or an AI error now shows its message and carries on instead of returning. After the form, the history is read again and one `st.download_button` (`⬇️ 下载 / Download`, `text/plain`, `gco_league_ai_summary_<player>_<timestamp>.txt`) offers `build_transcript_text()` for that history. `tests/test_ai_follow_up_download_ui.py` has the plan's `FakeStreamlit`, `make_fake_st`, `_call` and `_render` and its six tests (eight cases with the blank-summary parametrization).

- `uv run pytest tests/test_ai_follow_up_download_ui.py tests/test_ai_follow_up_ui.py tests/test_ai_follow_up_logic.py tests/test_league_follow_up_wiring.py -v` (Verify): exit 0, 37 passed. Same result on Streamlit 1.64.
- Whole suite: `python -m pytest -q`: 151 passed; `behave --format progress`: 17 scenarios passed, on Streamlit 1.55 and 1.64.
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 008-league-ai-summary-add-a-download --phase 2`: exit 0, PASSED.
- `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`: 0.
- Browser check (not committed): the real League page on Streamlit 1.64 with only `get_ai_config` and `_call_ollama_chat` stubbed, driven by Playwright/Chromium.
  - Download before any question: `gco_league_ai_summary_刘北南_<timestamp>.txt`, holding the two headings and the summary.
  - Download after two follow-up questions: both `问 / Q:`/`答 / A:` pairs, in the order asked.
  - After each download click the summary and every turn stayed on screen (the click reruns only the fragment).
  - The live DOM shows the buttons Phase 3 targets: `[data-testid="stFormSubmitButton"] button` (`kind="secondaryFormSubmit"`) and `[data-testid="stDownloadButton"] button`. Both are still unstyled (`background-image: none`).

**Deviations:**
- The same repo-root `sys.path` insertion as Phase 1 before `import ai_summary`.
- Two small test helpers beyond the plan's four, `_seed()` (writes the stored history the plan's tests describe) and `_markdown_bodies()` (the `markdown` bodies behaviour 15 compares); the plan's helpers and assertions are otherwise as written.

## Phase 3: Green styling for submit and download buttons
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `theme.py`, `tests/test_theme_button_styles.py` (new).

In `THEME_CSS` only the two button selector lines changed, each widened to the plan's six selectors (`.stButton > button` first, then the form-submit and download button elements); the comment, both declaration blocks and every other rule are byte-identical. `tests/test_theme_button_styles.py` has the plan's constants, `_rules()`/`_rule_for()`/`_approved_theme_css()` helpers and its three tests.

- `uv run pytest tests/test_theme_button_styles.py -v` (Verify): exit 0, 3 passed; `test_non_button_rules_are_unchanged` ran against the approved tag (not skipped).
- `uv run pytest -q` (Verify): exit 0, 154 passed. Same results on Streamlit 1.64.
- `behave --format progress`: 17 scenarios passed.
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 008-league-ai-summary-add-a-download --phase 3`: exit 0, PASSED.
- `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`: 0.
- Browser check (not committed): the same mocked League page on Streamlit 1.64 rerun after this change. Computed styles of `[data-testid="stFormSubmitButton"] button` (提问 / Ask) and `[data-testid="stDownloadButton"] button` (⬇️ 下载 / Download) are now `linear-gradient(135deg, rgb(45, 106, 79), rgb(82, 183, 136))` with `rgb(255, 255, 255)` text. Before this phase they were `background-image: none` with pale text. Both downloads still hold the expected transcript.

**Deviations:**
- The same repo-root `sys.path` insertion as Phases 1 and 2 before `import theme`.
- `_approved_theme_css()` passes `cwd=REPO_ROOT` to `git show`, so the comparison reads this repository wherever pytest is started from; otherwise as written.
- A `NEW_BUTTON_SELECTORS` tuple holds the two selector fragments the first test loops over (the plan lists them inline).
