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

## Phase 2: Language selector beside the AI button
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `ai_summary.py`, `tests/test_ai_summary_language_ui.py` (new).

`render_season_summary()` is the plan's version verbatim: after the empty-name return it draws `st.columns([1, 1])`, the 中文 / English `st.radio` (default 中文, horizontal) in the left cell and the unchanged `🤖 AI 赛季总结` button (`key="ai_season_summary_button"`) in the right cell, and passes the selected language to `summarize_season()`; nothing is cached, so changing the radio without pressing shows nothing. `tests/test_ai_summary_language_ui.py` has the plan's fake-Streamlit classes and fixtures (verbatim) and its eight tests (nine cases).

- `python -m pytest tests/test_ai_summary_language_ui.py -v` (Verify 1): exit 0, 9 passed.
- `python -m pytest tests/test_ai_summary_language_logic.py tests/test_ai_season_summary.py tests/test_ai_summary_logic.py tests/test_league_deep_dive_wiring.py -v` (Verify 2, frozen tests): exit 0, 46 passed.
- Both Verify commands and the whole suite (`python -m pytest -q`: 99 passed; `behave --format progress`: 17 scenarios passed) were run on Streamlit 1.55 (`uv.lock`) and 1.64 (`requirements.txt`, as CI installs it), with the same results.
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 006-ai-season-summary-in-english-too --phase 2`: exit 0, PASSED (scope all inside the targets, no frozen file touched, contract matches; Phase 1 and Phase 2 Verify passed).
- `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=.venv` (CI's fatal lint): 0, exit 0.
- Extra check, not in the plan and not committed: `AppTest.from_file("pages/3_🏆_League.py")` on Streamlit 1.64 with `_call_ollama_chat` and `get_ai_config` stubbed shows the `语言 / Language` radio with options `中文`, `English` and `中文` selected, no exception; pressing with 中文 shows the Chinese stub reply, switching to English without pressing shows no summary, and pressing again shows the English stub reply; the two requests used `SYSTEM_MESSAGE` then `SYSTEM_MESSAGE_EN`.

**Deviations:** none.
