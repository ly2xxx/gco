<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@0bb98a9 -->
## Summary
The League scorecard auto-fill read is extended so that, in the same single read it already performs, it returns the par for each hole 1–18 and every player's hole-by-hole scores instead of summary figures only. The League admin score form then shows a read-only verification table (holes 1–18 plus Out/In/Total, a Par row and the selected player's Score row) next to the uploaded scorecard image, so the admin can compare the read against the photo before pressing Save.

## Behaviour

1. Given a stubbed generate reply `{"pars": {"1": 4, …, "18": 5}, "players": [...]}`, when `read_league_scorecard_players` returns, then `result.pars` maps every hole 1–18 to the par value in that reply.
2. Given the same stubbed reply where the player labelled `"张纬"` has `"hole_scores": {"1": 5, …, "18": 4}`, when `read_league_scorecard_players` returns, then the entry labelled `"张纬"` has `hole_scores` equal to those 18 hole→score pairs.
3. Given a stubbed reply listing three players in printed order, when the read returns, then `result.players` has three entries with `index` 0, 1, 2 in printed order and each entry's `hole_scores` contains only that player's values.
4. Given a stubbed reply in which a player's `hole_scores` omits hole 7 and `pars` omits hole 12, when the read returns, then hole 7 is absent from that entry's `hole_scores`, hole 12 is absent from `result.pars`, and neither dict contains a `0` entry for those holes.
5. Given a stubbed reply whose hole values are `0`, `21`, `"x"`, `null`, or whose keys are `"0"`, `"19"`, `"hole 3"`, when the read returns, then each of those entries is absent from the returned dict and every in-range, well-keyed entry is still present.
6. Given a stubbed reply whose `"pars"` (or a player's `"hole_scores"`) is a string, a list or a number, when the read returns, then the corresponding dict is `{}` and no exception is raised.
7. Given empty image bytes, an unsupported file type, a transport error, or a body whose reply has no players, when `read_league_scorecard_players` returns, then `players == []`, `pars == {}`, and `unavailable_reason` is the same string the current implementation returns for that case (`"empty image"`, `"unsupported file type"`, the transport error text, `"unparseable response"`, `"no readable players"`).
8. Given a read result and the index of one of its entries, when `selected_player_hole_scores(result, index)` is called, then it returns a dict equal to that entry's `hole_scores`, and mutating the returned dict leaves the entry's `hole_scores` unchanged.
9. Given `None`, a `bool`, a non-`int`, or an index no entry carries, when `selected_player_hole_scores` is called, then it returns `{}`.
10. Given any pars mapping and hole-scores mapping, when `scorecard_verification_table(pars, hole_scores)` is called, then its keys are exactly `["Par", "Score"]` in that order and each value is a list of 21 cells whose positions are holes `"1"`–`"18"`, then `"Out"`, `"In"`, `"Total"` (the order in `VERIFICATION_TABLE_COLUMNS`).
11. Given pars with hole 5 read as 4 and hole 9 unread, and hole scores with hole 5 read as 6 and hole 9 unread, when the table is built, then `table["Par"][4] == 4`, `table["Par"][8] is None`, `table["Score"][4] == 6` and `table["Score"][8] is None`.
12. Given all 18 holes read, when a row is built, then its Out cell equals the sum of holes 1–9, its In cell the sum of holes 10–18, and its Total cell the sum of holes 1–18; given any hole of a segment is unread, then that segment's cell and the Total cell are `None` (never a partial sum).
13. Given a read result stored under `LEAGUE_SCORECARD_READ_RESULT_KEY` and a selected player index, when the League page source is inspected, then the scorecard block emits the uploaded image and `st.dataframe` of the verification table inside one `st.columns` row, and both calls appear before the `st.form_submit_button` for Save.
14. Given no valid player is selected, when the scorecard block renders, then no verification table is emitted while the image is still emitted.
15. Given the admin has typed a different value into an existing score form field after the read, when the table is built, then the Score row still shows the values from the stored `LeagueScorecardPlayersResult` and no league scorecard widget key is read or written to build it.
16. Given the whole existing test suite, when it is run without network access, then every test that passed before this change still passes.

## Interfaces

**`league_scorecard.py`**

Import change: `from dataclasses import dataclass, field`.

New module constants:

```python
HOLE_NUMBERS: tuple[int, ...] = tuple(range(1, 19))
OUT_HOLES: tuple[int, ...] = tuple(range(1, 10))
IN_HOLES: tuple[int, ...] = tuple(range(10, 19))
HOLE_SCORE_MIN, HOLE_SCORE_MAX = 1, 20
PAR_MIN, PAR_MAX = 3, 7
VERIFICATION_TABLE_COLUMNS: tuple[str, ...] = tuple(str(h) for h in HOLE_NUMBERS) + ("Out", "In", "Total")
VERIFICATION_ROW_LABELS: tuple[str, str] = ("Par", "Score")
LEAGUE_SCORECARD_READ_RESULT_KEY: str = "league_scorecard_read_result"
```

Changed dataclass (new field last, defaulted so existing positional construction keeps working):

```python
@dataclass(frozen=True)
class ScorecardPlayerEntry:
    index: int
    label: str
    found_fields: dict[str, ScorecardFieldValue]
    hole_scores: dict[int, int] = field(default_factory=dict)


@dataclass(frozen=True)
class LeagueScorecardPlayersResult:
    players: list[ScorecardPlayerEntry]
    unavailable_reason: str | None = None
    pars: dict[int, int] = field(default_factory=dict)
```

Changed constant: `SCORECARD_PLAYERS_PROMPT` keeps its name and is extended so the reply shape is
`{"pars": {"1": <int>, …, "18": <int>}, "players": [{"label": <str>, "fields": {...}, "hole_scores": {"1": <int>, …, "18": <int>}}]}`,
with the existing "omit what you cannot read, never guess" rule applying to `pars` and `hole_scores` too.
`build_scorecard_players_payload` keeps its signature and `_prompt_kind` keeps mapping this prompt to `"players"`.

New functions:

```python
def normalize_hole_number(key: object) -> int | None:
    """1-18 for an int or a digit-only string naming a hole, else None."""

def coerce_hole_values(raw: object, *, minimum: int, maximum: int) -> dict[int, int]:
    """Hole number -> int for each readable, in-range entry of a hole mapping; {} for non-mappings."""

def coerce_par_values(raw: object) -> dict[int, int]:
    """coerce_hole_values with PAR_MIN..PAR_MAX."""

def coerce_hole_scores(raw: object) -> dict[int, int]:
    """coerce_hole_values with HOLE_SCORE_MIN..HOLE_SCORE_MAX."""

def selected_player_hole_scores(
    result: LeagueScorecardPlayersResult,
    selected_index: int | None,
) -> dict[int, int]:
    """Hole scores for exactly the selected entry, or {} when no valid entry is selected."""

def scorecard_hole_totals(values: Mapping[int, int]) -> dict[str, int | None]:
    """Out/In/Total sums, each None unless every hole it covers was read."""

def scorecard_verification_row(values: Mapping[int, int]) -> list[int | None]:
    """21 cells in VERIFICATION_TABLE_COLUMNS order for one hole-values mapping."""

def scorecard_verification_table(
    pars: Mapping[int, int],
    hole_scores: Mapping[int, int],
) -> dict[str, list[int | None]]:
    """{"Par": [...], "Score": [...]}, 21 cells each in VERIFICATION_TABLE_COLUMNS order."""
```

Changed functions (signatures unchanged, behaviour extended):

- `scorecard_player_entries(parsed)` — also reads each player record's top-level `"hole_scores"` through `coerce_hole_scores`; records without it still yield an entry with `hole_scores == {}`.
- `_read_league_scorecard_players(...) -> LeagueScorecardPlayersResult` — fills `pars` from `parsed.get("pars")` via `coerce_par_values`, and logs the number of read pars alongside the existing per-player log line.

**`pages/3_🏆_League.py`**

- Stores the most recent read under `st.session_state[LEAGUE_SCORECARD_READ_RESULT_KEY]` (a `LeagueScorecardPlayersResult`) so the table can be rendered without re-reading.
- In the existing scorecard auto-fill block, reads the selection from `st.session_state[LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY]`, then in a single `st.columns` row renders the uploaded image (unchanged) and, when the selection is valid, `st.dataframe` of `selected_player_hole_scores(result, index)` combined with `result.pars` through `scorecard_verification_table`, indexed by `VERIFICATION_TABLE_COLUMNS` and labelled with `VERIFICATION_ROW_LABELS`. The block sits above the Save `st.form_submit_button`.
- Imports `pandas` at page level to build the frame, and imports `LEAGUE_SCORECARD_READ_RESULT_KEY`, `selected_player_hole_scores`, `scorecard_verification_table` and `VERIFICATION_TABLE_COLUMNS` from `league_scorecard`.

## Out of scope
- Editing scores inside the verification table; corrections stay in the existing form fields.
- Any change to what Save writes, to score storage, or to league standings calculations.
- Cup scorecards and any non-league scorecard flow.
- Re-reading or repairing scorecards that were already saved.
- Changes to how the image is uploaded, stored or displayed.
- Changing the single-player `read_league_scorecard` path or its prompt.
- A second network request per upload; the hole data comes from the existing one read.

## Open questions
- **Totals when a hole is unread.** Assumed Out/In/Total are blank as soon as any hole they cover is unread, rather than summing the holes that were read.
- **Value ranges.** Assumed pars outside 3–7 and scores outside 1–20 are treated as unread (dropped), so a misread `0` or `21` never reaches the table.
- **Alternative model shapes.** Assumed `"pars"` and `"hole_scores"` must be JSON objects keyed by hole; an 18-element array or any other shape is treated as unread rather than converted.
- **Prompt edit.** Assumed the existing tests around `scorecard_player_entries` and the players read assert parsed behaviour, not the literal prompt text, so extending `SCORECARD_PLAYERS_PROMPT` keeps them passing.
- **Empty Par row.** Assumed the table still appears (Par row blank) when the read produced a selected player's hole scores but no pars, rather than suppressing the table.
- **Duplicate labels.** Assumed players whose printed labels are identical stay as separate entries selected by index, since the table shows the selected entry's own numbers.
- **Layout specifics.** Assumed image on the left and table on the right of one `st.columns` row; exact width ratios are left to the implementer.
- **Stored read vs. widget state.** Assumed the page already keeps the read result in session state; the constant name `LEAGUE_SCORECARD_READ_RESULT_KEY` is the spec's choice and may replace an existing equivalent key.
