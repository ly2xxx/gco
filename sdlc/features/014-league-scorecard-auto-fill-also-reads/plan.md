<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@8681038 -->
## Approach
Extend the existing single league-scorecard read to coerce top-level pars and per-player hole scores, add pure copy/table helpers for the 21-column verification table, then wire a read-only image-plus-table `st.columns` block into the League score form from the stored read result. No save, storage, cup, upload, or image-display behavior changes.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| The auto-fill read returns par values for holes 1-18 and hole-by-hole scores for each player on the card, not just a summary. | 1, 2, 3, 4, 5, 6, 7 | Phase 1 |
| After the admin picks the card player, a table appears on the score form alongside the uploaded scorecard image. | 13, 14 | Phase 3 |
| The table has columns for holes 1-18 plus Out, In and Total, with a Par row and a Score row for the selected player. | 10, 11, 12, 13 | Phase 2 for value shape; Phase 3 for rendering |
| The table's Par and Score values match what the auto-fill read produced for that image, without the admin re-entering them. | 8, 9, 11, 15 | Phase 2 for selection/rows; Phase 3 for stored read result |
| The image and the table are visible at the same time, before Save is pressed. | 13, 14 | Phase 3 |
| The existing tests still pass. | 16 | All phases; final full-suite verification |

## Phase 1: Hole data in league scorecard read
<!-- phase: 1 -->
<!-- targets: league_scorecard.py, tests/test_league_scorecard_hole_read.py -->
<!-- frozen: tests/test_league_scorecard_fields.py, tests/test_league_scorecard_logging.py, tests/test_league_scorecard_player_selection.py, tests/test_league_scorecard_player_selector_wiring.py, tests/test_league_scorecard_players.py, tests/test_league_scorecard_players_read.py, tests/test_league_scorecard_read.py, tests/test_league_scorecard_state.py, tests/test_league_scorecard_wiring.py, tests/test_league_page_reloads_stale_scorecard_module.py, tests/test_league_saved_scorecard.py, tests/test_league_saved_scorecard_preview.py, tests/test_league_saved_scorecard_wiring.py -->

**Goal:** A stubbed league-scorecard reply returns `result.pars` for holes 1-18 and each player entry’s `hole_scores`, dropping unreadable or malformed values without raising.

**Changes:**
- `league_scorecard.py`: change `from dataclasses import dataclass` to `from dataclasses import dataclass, field`.
- `league_scorecard.py`: add these module constants next to the existing scorecard constants:
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
- `league_scorecard.py`: change the dataclasses to exactly:
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
- `league_scorecard.py`: replace `SCORECARD_PLAYERS_PROMPT` with an extended prompt that keeps the existing rules and adds top-level pars plus per-player `hole_scores`. The shape must be:
```python
SCORECARD_PLAYERS_PROMPT: str = (
    "You read one photographed golf league scorecard that may show several players' scores. "
    "The card may be printed or handwritten, in Chinese, English, or both.\n"
    "Return a single JSON object and nothing else, shaped as:\n"
    '{"pars": {"1": <int>, ..., "18": <int>}, '
    '"players": [{"label": "<text printed for this player>", "fields": {...}, '
    '"hole_scores": {"1": <int>, ..., "18": <int>}}, ...]}\n'
    "Rules:\n"
    '- Return one object in "players" for every player printed on the card, in the order the '
    "players appear on the card. Never drop a player and never list a player twice.\n"
    '- "pars": one numeric par for each hole 1-18 printed on the card, keyed by the hole number '
    'as a string. Omit any hole whose par you cannot read with confidence.\n'
    '- "label": the player\'s printed name. When no name is printed, use the column header printed '
    "above that player's scores, exactly as printed. Never invent a label and never use "
    "A/B/C/Marker.\n"
    '- "fields": an object holding only the scores that belong to this one player, using any of '
    '"date", "venue", "net", "gross", "stableford", "eagles", "birdies", "pars", "bogeys", '
    '"double_bogeys_or_worse".\n'
    '- "hole_scores": one numeric score for each hole 1-18 for this player only, keyed by the hole '
    'number as a string. Omit any hole whose score you cannot read with confidence.\n'
    '- "date": the round date as an ISO string "YYYY-MM-DD".\n'
    '- "venue": the venue/course name exactly as printed on the card.\n'
    '- "net", "gross", "stableford": integers.\n'
    '- "eagles", "birdies", "pars", "bogeys", "double_bogeys_or_worse": non-negative integer counts.\n'
    "- Omit any field you cannot read with confidence. Never guess and never invent a value.\n"
    '- Do not add keys other than "pars", "players", "label", "fields" and "hole_scores".'
)
```
- `league_scorecard.py`: do not change `build_scorecard_players_payload` or `_prompt_kind`; `_prompt_kind` must continue returning `"players"` for this exact prompt.
- `league_scorecard.py`: add these functions with exact signatures and behaviour:
```python
def normalize_hole_number(key: object) -> int | None:
    if isinstance(key, bool):
        return None
    if isinstance(key, int):
        return key if 1 <= key <= 18 else None
    if isinstance(key, str):
        text = key.strip()
        if text.isdigit():
            number = int(text)
            return number if 1 <= number <= 18 else None
    return None


def coerce_hole_values(raw: object, *, minimum: int, maximum: int) -> dict[int, int]:
    if not isinstance(raw, AbcMapping):
        return {}
    values: dict[int, int] = {}
    for raw_key, raw_value in raw.items():
        hole = normalize_hole_number(raw_key)
        if hole is None:
            continue
        value = coerce_int_value(raw_value, minimum=minimum, maximum=maximum)
        if value is None:
            continue
        values[hole] = value
    return {hole: values[hole] for hole in HOLE_NUMBERS if hole in values}


def coerce_par_values(raw: object) -> dict[int, int]:
    return coerce_hole_values(raw, minimum=PAR_MIN, maximum=PAR_MAX)


def coerce_hole_scores(raw: object) -> dict[int, int]:
    return coerce_hole_values(raw, minimum=HOLE_SCORE_MIN, maximum=HOLE_SCORE_MAX)
```
- `league_scorecard.py`: change `scorecard_player_entries(parsed)` so each accepted player record also reads its top-level `"hole_scores"` through `coerce_hole_scores`. The constructor call must be:
```python
ScorecardPlayerEntry(
    index=len(entries),
    label=label,
    found_fields=_player_fields(raw),
    hole_scores=coerce_hole_scores(raw.get("hole_scores")),
)
```
Records without `"hole_scores"` still yield an entry with `hole_scores == {}`.
- `league_scorecard.py`: in `_read_league_scorecard_players`, after parsing players, return `"no readable players"` before computing pars when no player entry exists, so a reply with pars but no players returns `pars == {}`. When players exist, set `pars = coerce_par_values(parsed.get("pars"))` and return `LeagueScorecardPlayersResult(players, pars=pars)`. Keep all existing unavailable-reason strings unchanged.
- `league_scorecard.py`: in `read_league_scorecard_players`, immediately before the existing available-result `players read: ...` log line, add `log.info("pars read: %s", len(result.pars))`. Leave the existing `players read: ...` line text unchanged so existing logging tests keep matching it.

**Definition of done:**
- [ ] `tests/test_league_scorecard_hole_read.py`, `test_read_returns_all_pars_and_each_players_hole_scores`: stubs `_post_ollama_generate` with a body whose outer JSON is `{"response": json.dumps(reply)}`; `reply` has all 18 pars, three players in order, and distinct full `hole_scores`; asserts `result.unavailable_reason is None`, `result.pars == {1: 4, ..., 18: 4}`, `[p.index for p in result.players] == [0, 1, 2]`, and each label’s `hole_scores` equals only that player’s values. Proves behaviours 1, 2 and 3. Monkeypatch restores `_post_ollama_generate` automatically; no threads or servers.
- [ ] `tests/test_league_scorecard_hole_read.py`, `test_unread_holes_are_absent_not_zero`: stubs pars without hole 12 and player `hole_scores` without hole 7; asserts `7 not in entry.hole_scores`, `12 not in result.pars`, and `0 not in` both dicts. Proves behaviour 4.
- [ ] `tests/test_league_scorecard_hole_read.py`, `test_out_of_range_and_bad_keys_are_dropped`: stubs pars and `hole_scores` containing values `0`, `21`, `"x"`, `None` and keys `"0"`, `"19"`, `"hole 3"`; asserts only the well-keyed in-range entries remain (`{1: 4, 6: 5}` in the fixture) with no exception. Proves behaviour 5.
- [ ] `tests/test_league_scorecard_hole_read.py`, `test_malformed_pars_and_hole_scores_are_empty_mappings`: parametrizes `bad` over `"not-a-map"`, `[1, 2, 3]` and `7`; stubs `reply={"pars": bad, "players": [{"label": "A", "fields": {}, "hole_scores": bad}]}`; asserts `result.pars == {}`, `result.players[0].hole_scores == {}`, and no exception. Proves behaviour 6.
- [ ] `tests/test_league_scorecard_hole_read.py`, `test_empty_image_and_unsupported_type_keep_pars_empty`: calls `read_league_scorecard_players(b"", None)` and `read_league_scorecard_players(b"plain text", "text/plain")`; asserts `players == []`, `pars == {}`, reasons `"empty image"` and `"unsupported file type"`. Proves the empty/unsupported portion of behaviour 7.
- [ ] `tests/test_league_scorecard_hole_read.py`, `test_transport_and_unparseable_failures_keep_pars_empty`: stubs `_post_ollama_generate` to raise `ScorecardRequestError("network error")` and separately to return `"not json"`; asserts `players == []`, `pars == {}`, reasons `"network error"` and `"unparseable response"`. Proves the transport/unparseable portion of behaviour 7.
- [ ] `tests/test_league_scorecard_hole_read.py`, `test_reply_without_players_returns_no_readable_players_and_empty_pars`: stubs `{"pars": {"1": 4}}` and `{"players": []}`; asserts `players == []`, `pars == {}`, reason `"no readable players"`. Proves the no-players portion of behaviour 7.
- [ ] No additional CLI/MCP/HTTP check is needed in this phase; all assertions are library calls in the new pytest file.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_hole_read.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Verification table and selected scores
<!-- phase: 2 -->
<!-- targets: league_scorecard.py, tests/test_league_scorecard_verification_table.py -->
<!-- frozen: tests/test_league_scorecard_hole_read.py, tests/test_league_scorecard_fields.py, tests/test_league_scorecard_logging.py, tests/test_league_scorecard_player_selection.py, tests/test_league_scorecard_player_selector_wiring.py, tests/test_league_scorecard_players.py, tests/test_league_scorecard_players_read.py, tests/test_league_scorecard_read.py, tests/test_league_scorecard_state.py, tests/test_league_scorecard_wiring.py, tests/test_league_page_reloads_stale_scorecard_module.py, tests/test_league_saved_scorecard.py, tests/test_league_saved_scorecard_preview.py, tests/test_league_saved_scorecard_wiring.py -->

**Goal:** The pure helpers return the selected player’s copied hole scores and build a two-row, 21-cell verification table whose Out/In/Total cells are `None` unless the covered segment is fully read.

**Changes:**
- `league_scorecard.py`: add these functions with exact signatures and behaviour:
```python
def selected_player_hole_scores(
    result: LeagueScorecardPlayersResult,
    selected_index: int | None,
) -> dict[int, int]:
    if result is None or isinstance(selected_index, bool) or not isinstance(selected_index, int):
        return {}
    for entry in getattr(result, "players", ()) or ():
        if getattr(entry, "index", None) == selected_index:
            scores = getattr(entry, "hole_scores", {})
            return dict(scores) if isinstance(scores, AbcMapping) else {}
    return {}


def scorecard_hole_totals(values: Mapping[int, int]) -> dict[str, int | None]:
    data = values if isinstance(values, AbcMapping) else {}
    out_total = sum(data[h] for h in OUT_HOLES) if all(h in data for h in OUT_HOLES) else None
    in_total = sum(data[h] for h in IN_HOLES) if all(h in data for h in IN_HOLES) else None
    total = out_total + in_total if out_total is not None and in_total is not None else None
    return {"Out": out_total, "In": in_total, "Total": total}


def scorecard_verification_row(values: Mapping[int, int]) -> list[int | None]:
    data = values if isinstance(values, AbcMapping) else {}
    totals = scorecard_hole_totals(data)
    return [data.get(h) for h in HOLE_NUMBERS] + [totals["Out"], totals["In"], totals["Total"]]


def scorecard_verification_table(
    pars: Mapping[int, int],
    hole_scores: Mapping[int, int],
) -> dict[str, list[int | None]]:
    return {
        VERIFICATION_ROW_LABELS[0]: scorecard_verification_row(pars),
        VERIFICATION_ROW_LABELS[1]: scorecard_verification_row(hole_scores),
    }
```
- `league_scorecard.py`: do not change the Phase 1 coercion, read, prompt, dataclass or logging behavior.
- `tests/test_league_scorecard_verification_table.py`: import `VERIFICATION_TABLE_COLUMNS`, `LeagueScorecardPlayersResult`, `ScorecardPlayerEntry`, `scorecard_hole_totals`, `scorecard_verification_row`, `scorecard_verification_table` and `selected_player_hole_scores` from `league_scorecard`.

**Definition of done:**
- [ ] `tests/test_league_scorecard_verification_table.py`, `test_table_has_exactly_two_rows_and_21_ordered_cells`: calls `scorecard_verification_table` with all 18 pars `4` and all 18 scores `5`; asserts `list(table) == ["Par", "Score"]`, each row is a `list` of length `21`, all first 18 Par cells are `4`, all first 18 Score cells are `5`, and the last three Par cells are `[36, 36, 72]` while the last three Score cells are `[45, 45, 90]`. Proves behaviour 10 plus the all-read totals part of behaviour 12.
- [ ] `tests/test_league_scorecard_verification_table.py`, `test_unread_holes_stay_blank_and_totals_never_partial`: uses pars with hole 9 missing and hole 5 read as `4`, and scores with hole 9 missing and hole 5 read as `6`; asserts `table["Par"][4] == 4`, `table["Par"][8] is None`, `table["Score"][4] == 6`, `table["Score"][8] is None`, the Out cell is `None` for each affected row, the In cell is the full holes 10-18 sum, and the Total cell is `None`. Proves behaviours 11 and 12.
- [ ] `tests/test_league_scorecard_verification_table.py`, `test_totals_are_sums_only_when_each_segment_is_complete`: calls `scorecard_hole_totals` with all 18 holes read, then with hole 5 missing, then with hole 15 missing; asserts `{"Out": 27, "In": 27, "Total": 54}` for all-read, `{"Out": None, "In": 27, "Total": None}` when hole 5 is missing, and `{"Out": 27, "In": None, "Total": None}` when hole 15 is missing. Proves the no-partial-sum rule of behaviour 12.
- [ ] `tests/test_league_scorecard_verification_table.py`, `test_selected_player_scores_are_copied_and_invalid_selection_returns_empty`: builds `LeagueScorecardPlayersResult([ScorecardPlayerEntry(0, "A", {}, {1: 4}), ScorecardPlayerEntry(1, "B", {}, {1: 6})])`; asserts `selected_player_hole_scores(result, 1) == {1: 6}`, mutates the returned dict, asserts `result.players[1].hole_scores == {1: 6}`, and for each bad selector in `(None, True, False, "1", 1.0, 99)` plus `selected_player_hole_scores(None, 0)` asserts `== {}`. Proves behaviours 8 and 9.
- [ ] `tests/test_league_scorecard_verification_table.py`, `test_verification_row_places_values_in_verification_table_column_order`: calls `scorecard_verification_row` with `{1: 4, 2: 5, ..., 18: 3}`; asserts positions `0` and `17` hold the first and last hole values, positions `18`, `19`, `20` hold the three totals, and a row missing hole 7 has `row[6] is None`, Out `None`, and Total `None`. Proves the column-position rule of behaviour 10 together with behaviour 12. No fixtures or cleanup beyond pytest’s own function teardown.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_verification_table.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 3: Render the verification table beside the image
<!-- phase: 3 -->
<!-- targets: pages/3_🏆_League.py, tests/test_league_verification_table_wiring.py -->
<!-- frozen: tests/test_league_scorecard_hole_read.py, tests/test_league_scorecard_verification_table.py, tests/test_league_scorecard_fields.py, tests/test_league_scorecard_logging.py, tests/test_league_scorecard_player_selection.py, tests/test_league_scorecard_player_selector_wiring.py, tests/test_league_scorecard_players.py, tests/test_league_scorecard_players_read.py, tests/test_league_scorecard_read.py, tests/test_league_scorecard_state.py, tests/test_league_scorecard_wiring.py, tests/test_league_page_reloads_stale_scorecard_module.py, tests/test_league_saved_scorecard.py, tests/test_league_saved_scorecard_preview.py, tests/test_league_saved_scorecard_wiring.py -->

**Goal:** In the League score form, the uploaded scorecard image and a read-only 21-column verification table for the selected stored player render together in one `st.columns` row above Save, and no table renders without a valid selected player.

**Changes:**
- `pages/3_🏆_League.py`: add `import pandas as pd` at page level. Merge these names into the existing `league_scorecard` import block, without duplicating existing imports:
```python
from league_scorecard import (
    LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY,
    LEAGUE_SCORECARD_READ_RESULT_KEY,
    VERIFICATION_ROW_LABELS,
    VERIFICATION_TABLE_COLUMNS,
    read_league_scorecard_players,
    scorecard_verification_table,
    selected_player_hole_scores,
)
```
- `pages/3_🏆_League.py`: wherever the existing scorecard auto-fill calls `read_league_scorecard_players(...)`, assign its return value to `scorecard_read_result` if needed and immediately store it:
```python
st.session_state[LEAGUE_SCORECARD_READ_RESULT_KEY] = scorecard_read_result
```
- `pages/3_🏆_League.py`: inside the score form, replace the current standalone scorecard `st.image(...)` rendering with one `st.columns` row, and place this block immediately before the Save `st.form_submit_button(...)` call. Keep the existing scorecard image argument and any existing image keywords unchanged:
```python
scorecard_read_result = st.session_state.get(LEAGUE_SCORECARD_READ_RESULT_KEY)
selected_player_index = st.session_state.get(LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY)
valid_player_selected = (
    isinstance(selected_player_index, int)
    and not isinstance(selected_player_index, bool)
    and scorecard_read_result is not None
    and any(
        getattr(player, "index", None) == selected_player_index
        for player in getattr(scorecard_read_result, "players", ())
    )
)

scorecard_image_column, scorecard_table_column = st.columns([1, 2])
with scorecard_image_column:
    st.image(<existing scorecard image argument and existing keywords unchanged>)
with scorecard_table_column:
    if valid_player_selected:
        verification = scorecard_verification_table(
            scorecard_read_result.pars,
            selected_player_hole_scores(scorecard_read_result, selected_player_index),
        )
        verification_frame = pd.DataFrame(
            [verification[label] for label in VERIFICATION_ROW_LABELS],
            index=list(VERIFICATION_ROW_LABELS),
            columns=list(VERIFICATION_TABLE_COLUMNS),
        )
        st.dataframe(verification_frame, use_container_width=True)
```
- `pages/3_🏆_League.py`: the table block must not read or write any score-form widget key such as `date`, `venue`, `net`, `gross`, `stableford`, `eagles`, `birdies`, `pars`, `bogeys` or `double_bogeys_or_worse`; it uses only the stored read result and the selected player index. Do not change Save, storage, standings, upload, or image handling.

**Definition of done:**
- [ ] `tests/test_league_verification_table_wiring.py`, `test_read_result_is_stored_and_rendered_beside_image_before_save`: reads `pages/3_🏆_League.py` source with `Path`, asserts `st.session_state[LEAGUE_SCORECARD_READ_RESULT_KEY] = scorecard_read_result` is present, slices from `scorecard_read_result = st.session_state.get(LEAGUE_SCORECARD_READ_RESULT_KEY)` to the next `st.form_submit_button`, asserts exactly one `st.columns(` in that slice, both `with scorecard_image_column:` and `with scorecard_table_column:`, `st.image(` before `st.dataframe(`, and the slice contains `scorecard_verification_table(` and `VERIFICATION_TABLE_COLUMNS`. Proves behaviour 13.
- [ ] `tests/test_league_verification_table_wiring.py`, `test_invalid_selection_keeps_image_and_skips_dataframe`: uses the same source slice; asserts `st.image(` appears before `if valid_player_selected:`, `st.dataframe(` appears after that `if`, and the `st.dataframe(` line is indented at least one level deeper than the `if valid_player_selected:` line. Also asserts the guard contains `any(` and `getattr(player, "index", None) == selected_player_index`, so the table is keyed on a valid entry rather than on non-empty scores. Proves behaviour 14.
- [ ] `tests/test_league_verification_table_wiring.py`, `test_table_uses_stored_result_not_score_form_keys`: slices the `scorecard_verification_table(...)` call from the same block and asserts it contains `scorecard_read_result.pars` and `selected_player_hole_scores(scorecard_read_result, selected_player_index)`, and contains no `st.session_state` reference. For each score-form key `("date", "venue", "net", "gross", "stableford", "eagles", "birdies", "pars", "bogeys", "double_bogeys_or_worse")`, asserts neither `st.session_state.get("<key>")` nor `st.session_state["<key>"]` appears in the table call. Proves behaviour 15. These are source-inspection tests only; they start no Streamlit server and need no teardown.

**Verify:**
```bash
python -m pytest tests/test_league_verification_table_wiring.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- If the model returns `pars` or `hole_scores` as an 18-element array or any non-object shape, Phase 1 deliberately drops it to `{}` per spec; the table will show blanks. Phase 1 malformed-container tests and Phase 2 blank-cell tests catch the code path, but not model behaviour.
- Existing logging or page-wiring tests may assert exact source/log shapes. Phase 1 leaves the existing `players read: ...` line text unchanged and Phase 3 keeps the existing `st.image(...)` call; the final full suite catches any remaining exact-match regression.
- The page could accidentally build the frame from live form fields instead of the stored read result. Phase 3’s source test asserts the table call uses `scorecard_read_result.pars` and `selected_player_hole_scores(...)`, and the final suite re-runs it.
- A valid selected player with an empty `hole_scores` is treated as valid and renders a blank Score row; only an invalid index suppresses the table. Phase 3’s guard test checks the entry index, not the emptiness of the score dict.
- Out/In/Total could become partial sums. Phase 2’s `test_totals_are_sums_only_when_each_segment_is_complete` and `test_unread_holes_stay_blank_and_totals_never_partial` catch this.
- Duplicate printed labels could collapse players. The plan uses stored indexes, and Phase 2’s selected-score test proves selection by entry index.

## Open questions
- Assumption: a validly selected player whose `hole_scores` is empty still shows the verification table with a blank Score row; only an invalid selected index suppresses the table, matching behaviour 14. The exact image/table width ratio is chosen as `[1, 2]`, with the existing image call unchanged inside the left column.

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/014-league-scorecard-auto-fill-also-reads/build-log.md` with one section per phase, in order. Head each
   one `## Phase <n>: <title>`, then list the files changed, the Verify command
   you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/014-league-scorecard-auto-fill-also-reads`.

Commit only this plan's targets and `build-log.md`. Leave every other file alone,
including other features' documents under `sdlc/features/`, even for formatting;
verification fails on any file outside the targets.

The pipeline waits for this file. Once it has a section for every phase, it
verifies the whole branch and opens the pull request.

