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

## Phase 2: Read every player from one image

**Status:** passed (local `sdlc_stage.py verify --phase 2`, exit 0)

**Files changed:**
- `league_scorecard.py`
- `tests/test_league_scorecard_players_read.py` (new)

**What was built:** `read_league_scorecard_players` sends one image with `SCORECARD_PLAYERS_PROMPT` and returns a `LeagueScorecardPlayersResult` listing every player as `{"label", "fields"}`. It reuses feature 011's transport (`/api/generate`, Bearer key, 120 s, `format: json`) and never raises. Empty or unsupported input, transport errors, an unparseable body and a card with no readable players all come back as an `unavailable_reason`. The single-player `read_league_scorecard` is unchanged.

**Commands and results:**
- `python -m pytest tests/test_league_scorecard_players_read.py -q` → 8 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 012-league-scorecard-auto-fill-reads-every --phase 2` → **Result: PASSED** (scope: all inside the targets; frozen: none touched; contract matches the approved tag; Phase 1-2 Verify blocks and the whole suite passed)

**Deviations from the plan:** none.

## Phase 3: Apply only the selected player's fields

**Status:** passed (local `sdlc_stage.py verify --phase 3`, exit 0)

**Files changed:**
- `league_scorecard.py`
- `tests/test_league_scorecard_player_selection.py` (new)

**What was built:** `selected_player_scorecard_updates` returns exactly the chosen entry's fields, selected by `index` so duplicate labels stay distinct, or `{}` with no valid choice. `apply_selected_player_scorecard_updates` clears every scorecard widget key and then writes only the chosen player's present fields. Switching from one player to another therefore never leaves the first player's values behind.

**Commands and results:**
- `python -m pytest tests/test_league_scorecard_player_selection.py -q` → 8 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 012-league-scorecard-auto-fill-reads-every --phase 3` → **Result: PASSED** (scope: all inside the targets; frozen: none touched; contract matches the approved tag; Phase 1-3 Verify blocks and the whole suite passed)

**Deviations from the plan:** none.
