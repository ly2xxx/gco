<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@9988f62 -->
## Approach
Add a pure `scorecard_score_type_counts` helper that returns the five hole-derived counts only when both `pars` and the selected player’s `hole_scores` contain every hole 1–18, then overlay those five values onto the selected entry’s `found_fields` in `selected_player_scorecard_updates`. Incomplete reads continue to return the existing `found_fields` unchanged, and the existing session-state application path writes the overlaid counts without touching saved-scorecard files.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| When par and the selected player’s score are read for all 18 holes, the five score-type fields reflect the hole-by-hole score-minus-par categories. | 1, 2, 3, 11 | Phase 2 |
| The five computed fields replace the model’s counts for that complete-read case and sum to 18. | 1, 2, 3, 4, 5, 11 | Phase 2 |
| When any hole lacks par or the selected player’s score, the auto-fill behaves exactly as it does now. | 7, 8, 9, 10 | Phase 1, Phase 2 |
| The scorecard form and saved-scorecard behavior remain unchanged apart from the auto-filled count values. | 6, 11, 12, 13 | Phase 2 |
| The existing tests still pass. | 14 | Phase 1, Phase 2 |

## Phase 1: Add hole-derived count helper
<!-- phase: 1 -->
<!-- targets: league_scorecard.py, tests/test_league_scorecard_score_type_counts.py -->
<!-- frozen: tests/test_league_scorecard_player_selection.py, tests/test_league_scorecard_state.py, tests/test_league_scorecard_fields.py, tests/test_league_scorecard_hole_read.py, tests/test_league_saved_scorecard.py -->

**Goal:** A reviewer can call `scorecard_score_type_counts` with complete and incomplete 18-hole mappings and get exact category counts or `None`.

**Changes:**
- `league_scorecard.py`: after `coerce_hole_scores`, add:

```python
def scorecard_score_type_counts(
    pars: Mapping[int, int],
    hole_scores: Mapping[int, int],
) -> dict[str, int] | None:
    """Five score-type counts from score-minus-par for all 18 holes, or None when either mapping lacks any hole 1-18."""
```

Implementation details:
- Return `None` when `pars` or `hole_scores` is not an `AbcMapping`.
- Return `None` when any `hole in HOLE_NUMBERS` is missing from either mapping. This covers empty mappings and partially complete mappings.
- Initialize `counts = {key: 0 for key in COUNT_FIELD_KEYS}` so keys are exactly `eagles`, `birdies`, `pars`, `bogeys`, `double_bogeys_or_worse`.
- For each hole in `HOLE_NUMBERS`, compute `diff = hole_scores[hole] - pars[hole]`:
  - `diff <= -2` increments `eagles`
  - `diff == -1` increments `birdies`
  - `diff == 0` increments `pars`
  - `diff == 1` increments `bogeys`
  - `diff >= 2` increments `double_bogeys_or_worse`
- Return `counts`.
- Do not change `selected_player_scorecard_updates` in this phase.
- No new imports: `Mapping`, `AbcMapping`, `HOLE_NUMBERS`, and `COUNT_FIELD_KEYS` already exist in the module.

**Definition of done:**
- [ ] `tests/test_league_scorecard_score_type_counts.py`, test `test_scorecard_score_type_counts_categorizes_all_differences_and_sums_to_18`: build `pars = {hole: 4 for hole in range(1, 19)}` and `hole_scores` with holes 1–2 scoring 1 and 2 for two eagles, hole 3 scoring 3 for one birdie, holes 4–5 scoring 4 for two pars, hole 6 scoring 5 for one bogey, and holes 7–18 scoring 6 for twelve double-bogeys-or-worse. Assert the result equals `{"eagles": 2, "birdies": 1, "pars": 2, "bogeys": 1, "double_bogeys_or_worse": 12}`, `list(result) == list(COUNT_FIELD_KEYS)`, and `sum(result.values()) == 18`. Proves spec behaviours 1–3.
- [ ] `tests/test_league_scorecard_score_type_counts.py`, test `test_scorecard_score_type_counts_returns_none_for_empty_or_missing_holes`: use `pytest.mark.parametrize` with cases: empty `pars`, empty `hole_scores`, complete `hole_scores` but `pars` missing hole 18, and complete `pars` but `hole_scores` missing hole 1. Assert each call returns `None`. Proves spec behaviours 8–9. No teardown or fixtures needed beyond pytest’s parametrize.
- [ ] `tests/test_league_scorecard_score_type_counts.py`, test `test_scorecard_score_type_counts_returns_none_for_non_mapping_inputs`: call with `None` for `pars` and `None` for `hole_scores`; assert `None` is returned and no exception escapes. Proves the guard used by the incomplete-read path.
- [ ] No CLI, HTTP, or server check is needed for this phase.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_score_type_counts.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Overlay hole-derived counts on selected player
<!-- phase: 2 -->
<!-- targets: league_scorecard.py, tests/test_league_scorecard_derived_counts.py -->
<!-- frozen: tests/test_league_scorecard_score_type_counts.py, tests/test_league_scorecard_player_selection.py, tests/test_league_scorecard_state.py, tests/test_league_scorecard_fields.py, tests/test_league_scorecard_hole_read.py, tests/test_league_saved_scorecard.py, tests/test_league_scorecard_wiring.py -->

**Goal:** A reviewer can select a player from a complete 18-hole read and see the five count fields replaced by hole-derived values through session state, with incomplete reads still returning only `found_fields`.

**Changes:**
- `league_scorecard.py`: change `selected_player_scorecard_updates` behaviour while keeping the signature:

```python
def selected_player_scorecard_updates(
    result: LeagueScorecardPlayersResult,
    selected_index: int | None,
) -> dict[str, ScorecardFieldValue]:
```

Implementation details:
- Keep the existing invalid-selection guard exactly:
  - return `{}` when `selected_index is None`
  - return `{}` when `isinstance(selected_index, bool)`
  - return `{}` when `not isinstance(selected_index, int)`
- Loop over `result.players` and find `entry.index == selected_index`.
- For the matching entry:
  - start with `updates = dict(entry.found_fields)`
  - call `counts = scorecard_score_type_counts(result.pars, entry.hole_scores)`
  - when `counts is not None`, call `updates.update(counts)` so hole-derived counts replace any model count fields already present
  - return `updates`
- Return `{}` when no entry matches.
- Leave `apply_selected_player_scorecard_updates` unchanged: it continues to clear league scorecard widget keys before calling `apply_scorecard_updates`, so the overlaid counts flow into session state only for keys present in `widget_keys`.
- Do not change saved-scorecard image lookup, upload, save, delete, or preview code.

**Definition of done:**
- [ ] `tests/test_league_scorecard_derived_counts.py`, test `test_selected_player_scorecard_updates_adds_hole_derived_counts_when_found_fields_have_none`: use a helper that returns complete `pars = {hole: 4 for hole in range(1, 19)}` and complete `hole_scores` with two eagles, three birdies, four pars, three bogeys, and six double-bogeys-or-worse. Build `ScorecardPlayerEntry(index=0, label="Player A", found_fields={"date": "2026-01-01", "venue": "Course", "net": -1, "gross": 72, "stableford": 36}, hole_scores=complete_hole_scores)` inside `LeagueScorecardPlayersResult(players=[entry], pars=complete_pars)`. Assert `selected_player_scorecard_updates(result, 0)` equals `{**found_fields, **expected_counts}` and that `date`, `venue`, `net`, `gross`, and `stableford` are unchanged. Proves spec behaviours 4 and 6.
- [ ] `tests/test_league_scorecard_derived_counts.py`, test `test_selected_player_scorecard_updates_replaces_model_counts_with_hole_derived_counts`: same complete read, but `found_fields` contains model counts such as `{"eagles": 9, "birdies": 9, "pars": 0, "bogeys": 0, "double_bogeys_or_worse": 0, "date": "2026-01-01", "venue": "Course", "net": -1, "gross": 72, "stableford": 36}`. Assert the returned five count fields equal the expected hole-derived counts, the five counts sum to 18, and all non-count fields are unchanged. Proves spec behaviours 5 and 6.
- [ ] `tests/test_league_scorecard_derived_counts.py`, test `test_selected_player_scorecard_updates_returns_found_fields_when_incomplete`: use `pytest.mark.parametrize` for incomplete cases: `pars` missing hole 18, `hole_scores` missing hole 1, empty `pars`, and empty `hole_scores`. In each case `found_fields` includes model counts. Assert the returned dict equals `found_fields` exactly. Proves spec behaviour 7.
- [ ] `tests/test_league_scorecard_derived_counts.py`, test `test_selected_player_scorecard_updates_returns_empty_for_invalid_selection`: use `pytest.mark.parametrize` with `None`, `True`, `False`, `"0"`, `1.0`, and `99` against a result containing one entry with `index=0`. Assert every call returns `{}`. Proves spec behaviour 10.
- [ ] `tests/test_league_scorecard_derived_counts.py`, test `test_apply_selected_player_scorecard_updates_writes_all_hole_derived_count_widgets`: build `widget_keys = {field: f"count_{field}" for field in COUNT_FIELD_KEYS}` and `session_state` pre-populated with `0` for each key. Call `apply_selected_player_scorecard_updates(result, 0, widget_keys, session_state)`. Assert each session-state value equals the expected hole-derived count and the returned list contains all five count fields in `LEAGUE_SCORECARD_FIELD_KEYS` order. Proves spec behaviour 11.
- [ ] `tests/test_league_scorecard_derived_counts.py`, test `test_apply_selected_player_scorecard_updates_only_writes_present_widget_keys`: set `widget_keys = {"eagles": "count_eagles", "birdies": "count_birdies"}` and `session_state = {"count_eagles": 0, "count_birdies": 0, "count_pars": 99}`. Call `apply_selected_player_scorecard_updates(result, 0, widget_keys, session_state)`. Assert `count_eagles` and `count_birdies` equal the derived counts, `count_pars` remains `99`, and the returned list is `["eagles", "birdies"]`. Proves spec behaviour 12.
- [ ] `tests/test_league_scorecard_derived_counts.py`, test `test_apply_selected_player_scorecard_updates_does_not_touch_saved_scorecard_files`: use `tmp_path` and `monkeypatch.setattr(league_scorecard, "SCORECARD_IMAGES_DIR", str(tmp_path))`; create `existing.jpg` in `tmp_path` with bytes `b"original"` and record its `st_mtime_ns`. Call `apply_selected_player_scorecard_updates` with the complete result and all five count widget keys. Assert `sorted(path.name for path in tmp_path.iterdir()) == ["existing.jpg"]`, the file’s bytes are still `b"original"`, and its `st_mtime_ns` is unchanged. `tmp_path` and `monkeypatch` clean up automatically. Proves spec behaviour 13.
- [ ] Frozen existing tests `tests/test_league_scorecard_player_selection.py`, `tests/test_league_scorecard_state.py`, `tests/test_league_scorecard_fields.py`, `tests/test_league_saved_scorecard.py`, and `tests/test_league_scorecard_wiring.py` remain unmodified and pass in the Verify command. Proves spec behaviour 14 for the directly affected selection, state, and saved-scorecard paths.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_derived_counts.py tests/test_league_scorecard_score_type_counts.py tests/test_league_scorecard_player_selection.py tests/test_league_scorecard_state.py tests/test_league_scorecard_fields.py tests/test_league_saved_scorecard.py tests/test_league_scorecard_wiring.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- An existing test may construct a complete `LeagueScorecardPlayersResult` and expect the old model counts; Phase 2’s frozen selection/state checks and the replacement test catch that.
- `scorecard_score_type_counts` assumes integer values as its signature declares; uncoerced raw mappings could raise during subtraction. Production callers already use `coerce_par_values` and `coerce_hole_scores`, and Phase 1 tests use valid integers plus non-mapping guards.
- A mistake in `apply_selected_player_scorecard_updates` could write count keys absent from `widget_keys`; the Phase 2 subset-widget test catches that.
- Any accidental saved-scorecard file write/delete/modify is caught by the Phase 2 `tmp_path` sentinel test.
- Count-key ordering or missing keys are caught by Phase 1’s exact-key and sum assertions.

## Open questions
None.

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/015-league-scorecard-auto-fill-counts-eagle/build-log.md` with one section per phase, in order. Head each
   one `## Phase <n>: <title>`, then list the files changed, the Verify command
   you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/015-league-scorecard-auto-fill-counts-eagle`.

Commit only this plan's targets and `build-log.md`. Leave every other file alone,
including other features' documents under `sdlc/features/`, even for formatting;
verification fails on any file outside the targets.

The pipeline waits for this file. Once it has a section for every phase, it
verifies the whole branch and opens the pull request.

