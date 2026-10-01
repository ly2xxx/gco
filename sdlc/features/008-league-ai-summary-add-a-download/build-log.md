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
