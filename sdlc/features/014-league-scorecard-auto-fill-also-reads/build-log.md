# Build log: 014-league-scorecard-auto-fill-also-reads

## Phase 1: Hole data in league scorecard read

**Status:** passed (local `sdlc_stage.py verify --phase 1`, exit 0)

**Files changed:**
- `league_scorecard.py`
- `tests/test_league_scorecard_hole_read.py` (new)

**What was built:** The single players read now also asks for the card's par per hole and each player's score per hole. `read_league_scorecard_players` returns them as `result.pars` and each entry's `hole_scores`, keyed by hole 1-18. Unread, out-of-range (par outside 3-7, score outside 1-20) or badly keyed values are dropped, never turned into 0, and every failure case keeps its existing reason with `pars == {}`.

**Commands and results:**
- `python -m pytest tests/test_league_scorecard_hole_read.py -v` → 11 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 014-league-scorecard-auto-fill-also-reads --phase 1` → **Result: PASSED** (scope: 2 files, all inside the targets; frozen: none touched; contract matches the approved tag; whole suite 289 passed, 17 behave scenarios passed)

**Deviations from the plan:**
1. **One more log line.** Besides the plan's `pars read: N`, the read logs `hole scores read: <label> -> {...}` for each player, so a wrong table can be traced in the app's `[scorecard]` logs. The existing `players read:` line is unchanged.
2. **Two tests beyond the Definition of done:** a reply with no hole data still fills the totals, and the prompt asks for `pars` and `hole_scores` while still being the `players` prompt.

## Phase 2: Verification table and selected scores

**Status:** passed (local `sdlc_stage.py verify --phase 2`, exit 0)

**Files changed:**
- `league_scorecard.py`
- `tests/test_league_scorecard_verification_table.py` (new)

**What was built:** `selected_player_hole_scores` returns a copy of the chosen entry's hole scores, selected by index. `scorecard_verification_table` builds the `Par` and `Score` rows, 21 cells each (holes 1-18, Out, In, Total), where an unread hole is `None` and Out, In and Total are `None` unless every hole they cover was read.

**Commands and results:**
- `python -m pytest tests/test_league_scorecard_verification_table.py -v` → 6 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 014-league-scorecard-auto-fill-also-reads --phase 2` → **Result: PASSED** (scope: 2 files, all inside the targets; frozen: none touched; contract matches the approved tag; whole suite 295 passed)

**Deviations from the plan:** none in the code. One test beyond the Definition of done checks the column order constant.
