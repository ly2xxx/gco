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

## Phase 3: Render the verification table beside the image

**Status:** passed (local `sdlc_stage.py verify --phase 3`, exit 0)

**Files changed:**
- `pages/3_🏆_League.py`
- `tests/test_league_verification_table_wiring.py` (new)

**What was built:** The page keeps each read under `LEAGUE_SCORECARD_READ_RESULT_KEY`. Inside the score form, directly above Save, one `st.columns` row shows the uploaded image on the left and, once a card player is picked, that player's Par and Score rows on the right, built only from the stored read. Nothing in Save, storage or the form's fields changes.

**Commands and results:**
- `python -m pytest tests/test_league_verification_table_wiring.py -v` → 9 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 014-league-scorecard-auto-fill-also-reads --phase 3` → **Result: PASSED** (scope: 2 files, all inside the targets; frozen: none touched; contract matches the approved tag; whole suite 304 passed, 17 behave scenarios passed)
- Whole suite on Streamlit 1.55.0, the version the deployed app runs → 288 passed, 16 skipped. The 16 are admin-form tests that need `AppTest`'s file-uploader support, which 1.55.0 lacks: the 10 from features 011 and 012, and this phase's 6.
- Browser check on Streamlit 1.55.0, driven by Playwright in Chromium with a local stand-in for Ollama and the real card photo from ly2xxx/gco#50:
  - after the upload and before a pick, the image shows and no table;
  - picking 王 shows the front nine with Out 36/49 and the back nine with In 35/44 and Total 71/93, every column visible;
  - picking 李杨, whose hole 17 the stand-in leaves out, shows "-" for that hole, In and Total, with the note explaining the dash;
  - no exception on the page.
  Ollama Cloud itself isn't reachable from the build machine, so how well the model reads holes is untested.

**Deviations from the plan:**
1. **Two tables instead of one 21-column table.** The frame is built as planned, then shown as the front nine with Out and the back nine with In and Total, the layout of the reference screenshot in ly2xxx/gco#67. A 21-column table needs sideways scrolling in two thirds of the form. Columns get a fixed 42 px width; at the default width the Total column was clipped.
2. **Cells are text, with "-" for an unread hole.** A numeric frame holding `None` shows scores as `5.0` and blanks as `None`.
3. **The page had no image to "replace".** The plan assumes an existing `st.image` of the uploaded card in the form; there was none (the uploader only lists the file name). `st.image(uploaded_scorecard)` is new, shown as it is, and wrapped so a file Streamlit can't display doesn't break the form.
4. **The row appears only while a card is uploaded.** With no upload there is no image and no read, so the block is inside `if uploaded_scorecard is not None:`; clearing the upload also drops the stored read.
5. **`_scorecard_players_for_form` passes `pars` through.** It rebuilds the result for venue matching and would otherwise have dropped the pars.
6. **`width='stretch'` is not used on the tables; the plan's `use_container_width=True` is deprecated** in current Streamlit. Fixed column widths are used instead (see 1).
7. **A caption and a mismatch warning.** The caption names the picked player. If every hole was read and the holes add up to a different number from the gross read off the card, a warning says so; if some holes are unread, a note explains the dash. ly2xxx/gco#67 asked for the mismatch hint.
8. **Tests beyond the Definition of done:** six `AppTest` runs of the real admin form (no table before a pick, both tables' values, the dash and totals, switching player, Save storing the form and not the table, a card with no hole data).
