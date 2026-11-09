<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@33a3219 -->
# Intent: League Scorecard Auto-fill Picks One Player from the Card

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
When a league scorecard image is auto-filled today, the admin cannot say which player on the card the scores belong to, so the form can be filled with the wrong player's numbers or the admin has to correct it by hand. Scorecards vary in how players are identified — some print names, some print only column headers — so any assumed A/B/C/Marker labelling is unreliable and silently mismatches the card to the admin's intent.

## Outcome
After a league scorecard is read, every player on the card appears as a selectable entry, each labelled exactly as printed on the card (the player's name, or the column header when no name is printed) — never an assumed A/B/C/Marker. The admin sees a selector above the score form and chooses one of those entries; only the chosen player's scores are filled into the form. This most likely belongs in `league_scorecard.py` with the existing League admin score form wiring.

## Done when
- Reading a league scorecard produces a list containing one entry per player on the card, with no players dropped or duplicated.
- Each entry is labelled with the text as printed on the card — the player's name where one is printed, otherwise the column header — and no entry is labelled A/B/C/Marker by assumption.
- A selector listing those entries is presented above the score form.
- Choosing an entry fills the form with that player's scores only; scores belonging to other players on the card do not appear in the form.
- Choosing a different entry changes the filled scores to that player's.
- The existing tests still pass.

## Not in scope
- Changing how scorecards are read or how well the reading performs (no OCR/parsing accuracy work).
- Cup or outing scorecards, or any scorecard types other than league.
- Matching or reconciling the card's printed player labels against the club's player roster, or auto-selecting a player on the admin's behalf.
- Filling more than one player's scores at a time.
- Changing the layout or fields of the score form itself.

## Open questions
- What the selector shows before the admin picks anything — assumed: no player is pre-selected, so no scores are filled until a choice is made.
- What happens when the card contains only one player — assumed: the single entry is still listed and still requires an explicit pick, keeping behaviour identical for all cards.
- Whether the chosen player's entry stays selected after the form is filled or submitted — assumed: it stays selected for the current card so a mis-pick can be corrected by choosing another entry.
- Whether duplicate printed labels on one card are disambiguated — assumed: each player on the card remains a separate entry labelled as printed, even if two labels match.
- No prior intent document was supplied, so this is a new intent rather than a revision.
