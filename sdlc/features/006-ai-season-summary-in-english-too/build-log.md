# Build log: 006-ai-season-summary-in-english-too

## Phase 1: Bilingual prompt and summary logic
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `ai_summary.py`, `tests/test_ai_summary_language_logic.py` (new).

`ai_summary.py` gains the plan's language constants, `normalize_language()`, a `language` argument on `build_summary_prompt()` and `summarize_season()`, and a `system_message` argument on `_call_ollama_chat()`, each taken verbatim from the plan's code blocks; the Chinese prompt is byte-identical to before and the Chinese path still calls `_call_ollama_chat` with three positional arguments. `render_season_summary()` is untouched in this phase. `tests/test_ai_summary_language_logic.py` has the plan's data, fixture and ten tests (17 cases with the parametrizations).

- `python -m pytest tests/test_ai_summary_language_logic.py -v` (Verify 1): exit 0, 17 passed.
- `python -m pytest tests/test_ai_summary_logic.py tests/test_ai_season_summary.py -v` (Verify 2, frozen feature-005 tests): exit 0, 27 passed.
- Both Verify commands and the whole suite (`python -m pytest -q`: 90 passed; `behave --format progress`: 17 scenarios passed) were run on Streamlit 1.55 (`uv.lock`) and on Streamlit 1.64 (a venv built from `requirements.txt`, as CI installs it), with the same results.
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 006-ai-season-summary-in-english-too --phase 1`: exit 0, PASSED (scope all inside the targets, no frozen file touched, contract matches).

**Deviations:**
- One helper, `_recording_call()`, installs the call-recording `_call_ollama_chat` the no-rounds and missing-config tests describe. Otherwise none.
