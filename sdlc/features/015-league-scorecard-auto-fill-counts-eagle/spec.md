<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@ebd5331 -->
## Summary
League scorecard auto-fill will calculate Eagle, Birdie, Par, Bogey, and Double Bogey+ counts directly from hole-by-hole par and the selected player’s scores when all 18 holes are readable. Complete hole data replaces the model-provided counts; if any hole is missing par or the selected player’s score, auto-fill keeps today’s behavior.

## Behaviour
1. Given `pars` and the selected player’s `hole_scores` contain every hole 1–18, when `scorecard_score_type_counts` is called, then it returns a dict whose keys are exactly `eagles`, `birdies`, `pars`, `bogeys`, and `double_bogeys_or_worse`.
2. Given a complete 18-hole read, when `scorecard_score_type_counts` categorizes each hole by score minus par, then differences <= -2 count as `eagles`, -1 as `birdies`, 0 as `pars`, +1 as `bogeys`, and >= +2 as `double_bogeys_or_worse`.
3. Given a complete 18-hole read, when `scorecard_score_type_counts` returns counts, then the five counts sum to 18.
4. Given a complete 18-hole read and the selected entry’s `found_fields` has no count fields, when `selected_player_scorecard_updates` is called, then the returned dict contains the five hole-derived count fields.
5. Given a complete 18-hole read and the selected entry’s `found_fields` has model-provided count fields that differ from the hole results, when `selected_player_scorecard_updates` is called, then the returned count fields are the hole-derived values.
6. Given a complete 18-hole read, when `selected_player_scorecard_updates` is called, then `date`, `venue`, `net`, `gross`, and `stableford` from the selected entry are returned unchanged.
7. Given `pars` or the selected entry’s `hole_scores` is missing any hole 1–18, when `selected_player_scorecard_updates` is called, then it returns exactly the selected entry’s `found_fields`, preserving today’s auto-fill behavior.
8. Given `pars` or `hole_scores` is empty, when `scorecard_score_type_counts` is called, then it returns `None`.
9. Given `pars` or `hole_scores` lacks any hole 1–18, when `scorecard_score_type_counts` is called, then it returns `None`.
10. Given `selected_index` is `None`, a bool, a non-int, or matches no entry, when `selected_player_scorecard_updates` is called, then it returns `{}` as it does today.
11. Given a complete 18-hole read and a valid selection, when `apply_selected_player_scorecard_updates` is called, then the session-state values for the five count widget keys are the hole-derived counts.
12. Given a complete 18-hole read and a valid selection, when `apply_selected_player_scorecard_updates` is called, then it writes only widget keys present in the existing `widget_keys` mapping for `LEAGUE_SCORECARD_FIELD_KEYS`.
13. Given a complete 18-hole read, when the scorecard updates are applied, then no saved-scorecard image file or saved-scorecard lookup is created, deleted, or modified.
14. Given the existing test suite, when it is run, then all existing tests still pass.

## Interfaces

### `league_scorecard.py`

Add:

```python
def scorecard_score_type_counts(
    pars: Mapping[int, int],
    hole_scores: Mapping[int, int],
) -> dict[str, int] | None:
    """Five score-type counts from score-minus-par for all 18 holes, or None when either mapping lacks any hole 1-18."""
```

Change behaviour, keeping the existing signature:

```python
def selected_player_scorecard_updates(
    result: LeagueScorecardPlayersResult,
    selected_index: int | None,
) -> dict[str, ScorecardFieldValue]:
    """Fields for the selected entry, with complete hole-derived counts replacing model counts."""
```

`apply_selected_player_scorecard_updates(...)` keeps its current signature and continues to clear the league scorecard widget keys before writing the selected fields. Its written values change only because `selected_player_scorecard_updates` may now return hole-derived count fields.

## Out of scope
- Changing how scorecard images are read or how the model extracts values.
- Calculating counts from partially complete hole data.
- Adding score categories beyond Eagle, Birdie, Par, Bogey, and Double Bogey+.
- Handicap, net-score, or other scoring adjustments.
- Backfilling or rewriting previously saved scorecards.
- Redesigning the league score form.
- Changing saved-scorecard image lookup, upload, or save behavior.

## Open questions
- “Read for all 18 holes” means both `pars` and the selected player’s `hole_scores` contain every hole 1–18. Assumption: yes; if either is missing any hole, the complete-read rule does not apply.
- Complete hole-derived counts fully replace the model’s five count fields rather than blending with them. Assumption: yes.
- Category bounds are Eagle <= -2, Birdie -1, Par 0, Bogey +1, and Double Bogey+ >= +2. Assumption: yes.
- When model counts and hole-derived counts disagree on a complete read, hole-derived counts win. Assumption: yes.
