# Build log: 012-league-scorecard-auto-fill-reads-every

## Phase 1: Parse every player into labelled entries

**Status:** passed (local `sdlc_stage.py verify --phase 1`, exit 0)

**Files changed:**
- `league_scorecard.py`
- `tests/test_league_scorecard_players.py` (new)

**What was built:** `scorecard_player_entries` turns a parsed `{"players": [...]}` response into one `ScorecardPlayerEntry` per printed player, in card order. Each entry's label is the text as read (a name, or a column header such as `Player 2`) and its fields go through the existing normaliser. A record with no printed label is skipped rather than given an invented A/B/C/Marker label, and duplicate labels stay separate entries told apart by `index`.

**Commands and results:**
- `python -m pytest tests/test_league_scorecard_players.py -q` → 6 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 012-league-scorecard-auto-fill-reads-every --phase 1` → **Result: PASSED** (scope: 2 files, all inside the targets; frozen: none touched; contract matches the approved tag)

**Deviations from the plan:** none.
