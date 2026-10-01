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
