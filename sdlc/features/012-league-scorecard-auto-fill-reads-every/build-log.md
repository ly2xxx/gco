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

## Phase 4: Wire the player selector above the League score form

**Status:** passed (local `sdlc_stage.py verify --phase 4`, exit 0; whole suite 232 passed)

**Files changed:**
- `pages/3_🏆_League.py`
- `tests/test_league_scorecard_player_selector_wiring.py` (new)
- `tests/test_league_scorecard_wiring.py`

**What was built:** An uploaded card is read once with `read_league_scorecard_players` and the result is kept in session state. A "Player" selectbox above the form then lists every player read off the card, labelled as printed, with nobody preselected. Picking one applies only that player's fields through `apply_selected_player_scorecard_updates`; fields that player lacks show the round's own values. Feature 011's behaviour stays: one read per upload, the fallback notice, the reset on round switch, and Save uploading the image.

**Commands and results:**
- `python -m pytest tests/test_league_scorecard_player_selector_wiring.py tests/test_league_scorecard_wiring.py -v` → 24 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 012-league-scorecard-auto-fill-reads-every --phase 4` → **Result: PASSED** (scope: 3 files, all inside the targets; frozen: none touched; contract matches the approved tag; Phase 1-4 Verify blocks and the whole suite passed)
- Mutation checks:
  - Applying the pick on every rerun fails `test_save_keeps_the_admins_corrections_and_uploads_the_card_once`.
  - Dropping the duplicate-label suffix fails `test_duplicate_printed_labels_stay_separately_selectable`.
  - Going back to removing the keys on reset fails 3 tests: both round-switch tests and the card-player switch.

  All pass with the code as committed.
- Browser check: `streamlit run` with admin secrets outside the repository and the scorecard URL pointed at a local stand-in returning the card from ly2xxx/gco#50 (`王` and `李杨`), driven by Playwright in Chromium with the real card photo.
  - On 李扬 · Game 5 the form showed that round's defaults (0/72/36/0).
  - After the read, the picker offered `王` and `李杨`, and nothing was filled before a pick.
  - Picking `李杨` filled net 13, gross 100, par 4, bogey 8 and double bogey+ 6, plus the card's date and venue. Stableford stayed 36.
  - Ollama Cloud itself isn't reachable from the build machine.

**Deviations from the plan:**
1. **The pick is applied only when it changes (or a new card is read), not on every run.** The plan's snippet calls `apply_selected_player_scorecard_updates` unguarded. A form submit is a rerun, so the call would clear the inputs and rewrite the card's values before the form returns them, and Save would store the card's values instead of the admin's corrections. The call itself is as the plan gives it, inside `if st.session_state.get(LEAGUE_SCORECARD_APPLIED_PICK_KEY) != _pick:`.
2. **The read is guarded by feature 011's upload fingerprint, and its result is kept in `st.session_state`.** The selector needs the players on every later rerun without a second Ollama call (feature 011's one read per upload). A new card resets the pick to nobody and the form to the round's values.
3. **Reset by writing values, not by removing keys.** This also fixes a feature 011 bug that is live on the deployed app: after switching round, the form kept showing the previous round's numbers. Keyed widgets keep their browser value unless it is set through `st.session_state`. Removing a key sends the browser `set_value=False`, while writing a value sends `set_value=True`; AppTest's `.value` reads session state and hid the difference. Three places now write values instead of removing keys:
   - a round switch or a save writes the round's own values;
   - a new card does the same;
   - fields the picked player lacks get the round's values.

   The pick's selectbox is reset to `None` the same way. The 011 test `test_snapshot_reset_guard_present` accepts the new `st.session_state[_key] = _base_values[_field]` line as well as the old `pop`. New assertions (`_sent_to_browser`) check the value the browser is sent.
4. **The date is converted to a date value.** `apply_selected_player_scorecard_updates` writes the ISO string, but `st.date_input` needs a `date`, so the page converts it, as feature 011's prefill did.
5. **Venue matching, plus the card's date and venue for every player.** `_scorecard_players_for_form` re-runs `scorecard_field_updates` with the league's known venues, as feature 011 did. A player read without a date or venue takes the card's, from the first player that has them. Only these two card-level fields are shared; a player's scores are never borrowed. On the card from ly2xxx/gco#50 the model may attach the date to the first player only.
6. **Repeated printed labels get a " (n)" suffix.** Streamlit 1.67 maps a selectbox choice back by its shown text, so two `Neo` options would both select the first. Unique labels are shown exactly as printed, and `format_func` still starts with `players_result.players[index].label`.
7. **The selectbox has a bilingual placeholder** (`选择记分卡上的球员 / Choose the player on the card`). The unavailable notice keeps feature 011's `st.info` text, which the plan allows ("If the existing block already renders the unavailable reason with a different call, keep that call").
8. **Feature 011's AppTests in `tests/test_league_scorecard_wiring.py` are updated for the pick step, and some are added.** The fixture now stubs `read_league_scorecard_players`, and the tests pick a player before checking values. The assertions on values, Save and the single image upload are kept, plus browser-value checks.
   - New: switching the card player, Save keeping corrections, manual entry with no card, and duplicate labels.
   - `test_prefill_is_applied_from_session_state` names the new apply call (the plan's rename instruction).
   - `test_read_and_filter_helpers_are_used` names `read_league_scorecard_players(`.
