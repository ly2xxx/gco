<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@ba04bd4 -->
# Intent: League Scorecard Auto-Fill From Hole Results

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
League admins filling out a scorecard currently rely on model-provided counts for Eagle/Birdie/Par/Bogey/Double Bogey+, even when the hole read contains enough information to calculate those counts directly. This can force manual correction and risks inaccurate league scoring statistics. When par and the selected player’s score are available for every hole, the scorecard should use those hole results instead of the model’s counts.

## Outcome
In `league_scorecard.py`, a complete 18-hole read populates the five score-type count fields from score-minus-par: Eagle for <= -2, Birdie for -1, Par for 0, Bogey for +1, and Double Bogey+ for >= +2. Incomplete reads keep the current auto-fill behavior. Admins no longer need to reconcile model counts when complete hole data is available.

## Done when
- When par and the selected player’s score are read for all 18 holes, the five score-type fields reflect the hole-by-hole score-minus-par categories.
- The five computed fields replace the model’s counts for that complete-read case and sum to 18.
- When any hole lacks par or the selected player’s score, the auto-fill behaves exactly as it does now.
- The scorecard form and saved-scorecard behavior remain unchanged apart from the auto-filled count values.
- The existing tests still pass.

## Not in scope
- Changing how scorecard images are read or how the model extracts values.
- Calculating counts from partially complete hole data.
- Adding new score categories beyond Eagle, Birdie, Par, Bogey, and Double Bogey+.
- Handicap, net-score, or other scoring adjustments.
- Backfilling or rewriting previously saved scorecards.
- Redesigning the league score form.

## Open questions
- Does “read for all 18 holes” require both par and the selected player’s score on every hole? Assumption: yes; if either is missing on any hole, the new complete-read rule does not apply.
- Should complete hole-derived counts fully replace the model counts rather than blend with them? Assumption: yes, the five fields are populated from hole results.
- How should the open-ended categories be bounded? Assumption: Eagle is <= -2 and Double Bogey+ is >= +2; Birdie, Par, and Bogey are -1, 0, and +1 respectively.
- What happens if model counts and hole-derived counts disagree? Assumption: hole-derived counts win when the read is complete.
