<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@850ff2d -->
## Summary
League scorecard auto-fill now reads every player on a card into selectable entries labelled exactly as printed, rather than assuming an A/B/C/Marker layout. The League admin score form shows a player selector above the existing form and applies only the chosen player’s found fields. Existing single-player read and field-application helpers remain unchanged for compatibility with existing callers and tests.

## Behaviour
1. Given a parsed league scorecard response containing N player records, when `scorecard_player_entries` is called, then it returns exactly N entries in printed order, with each player represented once.
2. Given a parsed player record whose printed label is `"Neo"`, when entries are built, then that entry’s label is exactly `"Neo"`.
3. Given a parsed player record with no printed name and a column header `"Player 2"`, when entries are built, then that entry’s label is exactly `"Player 2"` and no A/B/C/Marker label is synthesized.
4. Given an empty image, when `read_league_scorecard_players` is called, then it returns `players == []` and `unavailable_reason == "empty image"`.
5. Given an unsupported file type, when `read_league_scorecard_players` is called, then it returns `players == []` and `unavailable_reason == "unsupported file type"`.
6. Given a successful read with one player, when the League admin score form first renders, then the selector lists that one player’s label and uses no preselected value, so no scores are filled until an explicit choice is made.
7. Given a successful read with multiple players, when the League admin score form renders, then a player selector is presented above the score form with one option per entry, each labelled as printed on the card.
8. Given no selected player (`selected_index is None`), when `selected_player_scorecard_updates` is called, then it returns an empty mapping.
9. Given a selected entry index, when `selected_player_scorecard_updates` is called, then it returns exactly that entry’s `found_fields` and no fields from any other entry.
10. Given player A’s fields have been applied, when the admin selects player B, then the scorecard widget keys contain only B’s present fields and no field retains A’s value.
11. Given two entries with the same printed label, when selector options are built, then both entries remain separately selectable by their distinct `index`, and choosing one applies only that entry’s fields.
12. Given the selected player has some missing score fields, when the selection is applied, then only the present fields are written and absent fields are cleared rather than populated from another player.
13. Given the admin has selected an entry for the current card, when the form reruns for the same card, then that entry remains selected.
14. Given the existing test suite, when it is run, then all pre-existing tests pass.

## Interfaces

In `league_scorecard.py`:

```python
@dataclass(frozen=True)
class ScorecardPlayerEntry:
    index: int
    label: str
    found_fields: dict[str, ScorecardFieldValue]


@dataclass(frozen=True)
class LeagueScorecardPlayersResult:
    players: list[ScorecardPlayerEntry]
    unavailable_reason: str | None = None


SCORECARD_PLAYERS_PROMPT: str
LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY: str = "league_scorecard_selected_player"


def scorecard_player_entries(parsed: Mapping[str, object]) -> list[ScorecardPlayerEntry]:
    """Players from a parsed multi-player league-scorecard response, in printed order.

    Each parsed player supplies a label and score fields. Labels are preserved exactly
    as read. Duplicate labels remain separate entries with distinct indexes.
    Missing or malformed ``players`` data returns an empty list.
    """


def read_league_scorecard_players(
    image_bytes: bytes,
    mime_type: str | None,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> LeagueScorecardPlayersResult:
    """Read every player from one league scorecard image. Never raises."""


def selected_player_scorecard_updates(
    result: LeagueScorecardPlayersResult,
    selected_index: int | None,
) -> dict[str, ScorecardFieldValue]:
    """Fields for exactly the selected entry, or {} when no valid entry is selected."""


def apply_selected_player_scorecard_updates(
    result: LeagueScorecardPlayersResult,
    selected_index: int | None,
    widget_keys: Mapping[str, str],
    session_state: MutableMapping[str, Any],
) -> list[str]:
    """Clear the league scorecard widget keys, then write the selected player's present fields.

    Returns the fields written. With no valid selection, all league scorecard widget
    keys are cleared and an empty list is returned.
    """
```

Unchanged in `league_scorecard.py`: `ScorecardReadResult`, `read_league_scorecard`, `scorecard_field_updates`, and `apply_scorecard_updates` remain available for existing callers and tests.

In `pages/3_🏆_League.py`, in the existing League admin score form section:

```python
# Use the new reader for league scorecard auto-fill.
players_result: LeagueScorecardPlayersResult = read_league_scorecard_players(image_bytes, mime_type)

# Place this selectbox immediately above the existing League score form.
selected_index: int | None = st.selectbox(
    "Player",
    options=[player.index for player in players_result.players],
    format_func=lambda index: players_result.players[index].label,
    index=None,
    key=LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY,
)

# Apply exactly the chosen player's fields to the existing score form widget keys.
apply_selected_player_scorecard_updates(
    players_result,
    selected_index,
    widget_keys,
    st.session_state,
)
```

## Out of scope
- Changing OCR/model choice, transport, timeout, retry behaviour, or scorecard reading accuracy.
- Cup, outing, or any non-league scorecard types.
- Matching printed player labels against the club player roster, or auto-selecting a player.
- Filling more than one player’s scores at a time.
- Changing the layout, fields, validation, or submission behaviour of the existing score form.
- Changing the existing single-player `read_league_scorecard` / `ScorecardReadResult` contract.

## Open questions
- Preselection before the admin chooses: assumed none; the selector uses `index=None` and no scores are applied until an explicit choice.
- Cards containing only one player: assumed the single entry is still listed and still requires an explicit pick.
- Selection persistence after fill/submit: assumed the chosen entry stays selected for the current card so a mis-pick can be corrected.
- Duplicate printed labels on one card: assumed each remains a separate entry labelled as printed, disambiguated by `index`.
- Missing printed labels: assumed the reader provides the printed name or a column-header label; this change never synthesizes A/B/C/Marker or roster names.
- Missing score fields for the chosen player: assumed absent fields are cleared rather than inherited from a previously selected player.
- Cards with zero readable players: assumed `players` is empty, `unavailable_reason` is set, and no selector option or score fill is produced.
