# Build log: 015-league-scorecard-auto-fill-counts-eagle

## Phase 1: Add hole-derived count helper

**Status:** passed (local `sdlc_stage.py verify --phase 1`, exit 0)

**Files changed:**
- `league_scorecard.py`
- `tests/test_league_scorecard_score_type_counts.py` (new)

**What was built:** `scorecard_score_type_counts(pars, hole_scores)` buckets each hole's score minus par into eagles (<= -2), birdies (-1), pars (0), bogeys (+1) and double_bogeys_or_worse (>= +2), keyed in `COUNT_FIELD_KEYS` order. It returns `None` unless both mappings are mappings holding every hole 1-18, so the counts it returns always add up to 18.

**Commands and results:**
- `python -m pytest tests/test_league_scorecard_score_type_counts.py -v` → 7 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 015-league-scorecard-auto-fill-counts-eagle --phase 1` → **Result: PASSED** (scope: 2 files, all inside the targets; frozen: none touched; contract matches the approved tag; whole suite 311 passed, 17 behave scenarios passed)

**Deviations from the plan:**
1. **One test beyond the Definition of done:** `test_scorecard_score_type_counts_real_card` uses the pars and 李扬's hole scores read from the real card in ly2xxx/gco#72 (`league_2026个人联赛_Game_5_李扬_20261109172833.jpg`) and expects 0/0/2/7/9, the counts the admin entered by hand for that round.
2. The non-mapping test checks `None` for each argument in turn (two calls) rather than one call, so both guards are exercised.

## Phase 2: Overlay hole-derived counts on selected player

**Status:** passed (local `sdlc_stage.py verify --phase 2`, exit 0)

**Files changed:**
- `league_scorecard.py`
- `tests/test_league_scorecard_derived_counts.py` (new)

**What was built:** `selected_player_scorecard_updates` now starts from the selected entry's found fields and, when `scorecard_score_type_counts(result.pars, entry.hole_scores)` returns counts, overwrites the five count fields with them; date, venue, net, gross and stableford are untouched, and an incomplete read returns the found fields exactly as before. `apply_selected_player_scorecard_updates` and the League page are unchanged: the page already keeps `pars` and each entry's `hole_scores` through `_scorecard_players_for_form`, so the derived counts reach the form's widgets and the success notice through the existing path.

**Commands and results:**
- `python -m pytest tests/test_league_scorecard_derived_counts.py tests/test_league_scorecard_score_type_counts.py tests/test_league_scorecard_player_selection.py tests/test_league_scorecard_state.py tests/test_league_scorecard_fields.py tests/test_league_saved_scorecard.py tests/test_league_scorecard_wiring.py -v` → 86 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 015-league-scorecard-auto-fill-counts-eagle --phase 2` → **Result: PASSED** (scope: 2 files, all inside the targets; frozen: none touched; contract matches the approved tag; whole suite 327 passed, 17 behave scenarios passed)
- `flake8 league_scorecard.py tests/test_league_scorecard_derived_counts.py tests/test_league_scorecard_score_type_counts.py --count --select=E9,F63,F7,F82` → 0
- End-to-end check through `scorecard_player_entries` → `apply_selected_player_scorecard_updates` with a reply shaped like the real one in ly2xxx/gco#72 (only `date` and `gross` in `fields`, all 18 pars and hole scores for 李扬, two holes for 王): 李扬 fills `date, gross, eagles, birdies, pars, bogeys, double_bogeys_or_worse` = 0/0/2/7/9; 王 fills `date, gross` as before.

**Deviations from the plan:**
1. **One test beyond the Definition of done:** `test_helper_hole_scores_match_expected_counts` checks that the test's own hole scores really give 2/3/4/3/6 on par 4s, so the expected counts are not just restated.
2. The docstring of `selected_player_scorecard_updates` says when the counts are derived; the plan gives only its one-line summary.
