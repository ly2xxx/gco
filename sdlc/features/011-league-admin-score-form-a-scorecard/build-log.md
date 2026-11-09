# Build log: 011-league-admin-score-form-a-scorecard

## Phase 1: Field filtering and normalisation module

**Status:** passed (local `sdlc_stage.py verify --phase 1`, exit 0)

**Files changed:**
- `league_scorecard.py` (new)
- `tests/test_league_scorecard_fields.py` (new)

**What was built:** `league_scorecard.py` holds the field contract (`LEAGUE_SCORECARD_FIELD_KEYS`, `ScorecardReadResult`) and `scorecard_field_updates`, which maps English/Chinese aliases to the ten target fields and keeps only found, parseable values: ISO dates, ints within range, and the closest known venue. Missing, empty, unparseable, out-of-range and `found: false` values are dropped, so the page only ever writes fields the read really found.

**Commands and results:**
- `python -m pytest tests/test_league_scorecard_fields.py -v` → 15 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 011-league-admin-score-form-a-scorecard --phase 1` → **Result: PASSED** (scope: 2 files, all inside the targets; frozen: none touched; contract matches the approved tag; whole suite and the Phase 1 Verify block passed)

**Deviations from the plan:** none.

## Phase 2: One Ollama Cloud scorecard read with a 120 s cap

**Status:** passed (local `sdlc_stage.py verify --phase 2`, exit 0)

**Files changed:**
- `league_scorecard.py`
- `tests/test_league_scorecard_read.py` (new)

**What was built:** `read_league_scorecard` makes at most one `POST https://ollama.com/api/generate` with the base64 image, `stream: false`, `format: json`, `Authorization: Bearer <OLLAMA_API_KEY>` and a 120 s timeout (the call proven in ly2xxx/ideas-playground#16), with model `OLLAMA_SCORECARD_MODEL`, else `OLLAMA_MODEL`, else `glm-5.3-flash:cloud`. Empty or non-image input never reaches the network, and every HTTP error, timeout, network error, unparseable body or field-less answer comes back as an `unavailable_reason` instead of an exception.

**Commands and results:**
- `python -m pytest tests/test_league_scorecard_read.py -v` → 11 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 011-league-admin-score-form-a-scorecard --phase 2` → **Result: PASSED** (scope: all inside the targets; frozen: none touched; contract matches the approved tag; whole suite and the Phase 1 and 2 Verify blocks passed)
- Transport check outside the suite: the real `_post_ollama_generate` against a local stand-in server on `127.0.0.1` sent `POST /api/generate` with `Authorization: Bearer <key>`, `stream: false` and the default model, and parsed the answer; a 401 gave `http 401`, a 3 s reply with a 1 s cap gave `timeout`, and a refused connection gave `network error`, none raising. Ollama Cloud itself isn't reachable from the build machine, so no call to `ollama.com` was made.

**Deviations from the plan:**
1. **No `num_predict` in the payload's `options`; it is `{"temperature": 0}`.** The plan capped output at 512 tokens. Ollama counts a thinking model's reasoning towards `num_predict`, so the cap can end a vision read before it writes the JSON, turning every read into `unparseable response`; the call proven in ideas-playground#16 sets no cap. No Definition of done test checks `options`.
2. **Tests isolate model and key resolution.** `tests/test_league_scorecard_read.py` has an autouse fixture that clears `OLLAMA_SCORECARD_MODEL`, `OLLAMA_MODEL`, `OLLAMA_API_KEY` and `OLLAMA_KEY` and replaces `streamlit.secrets` with `{}`, so `test_request_payload_and_timeout` checks the default model even on a machine whose `.streamlit/secrets.toml` sets `OLLAMA_MODEL`. The plan's tests are otherwise as written.
