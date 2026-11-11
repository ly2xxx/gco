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
