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
