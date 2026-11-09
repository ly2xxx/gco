<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@651f864 -->
## Approach
Add a multi-player parse (`scorecard_player_entries`), a never-raising multi-player reader (`read_league_scorecard_players`) that reuses the existing Ollama request plumbing and `scorecard_field_updates` normalisation, and a selection helper that clears the league scorecard widget keys and then writes only the chosen entry's present fields; finally swap the League admin score form's single-player read/apply for the new reader plus a `st.selectbox` player selector. No OCR/model-prompt accuracy work, no roster matching, no form layout or field changes.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| Reading a league scorecard produces a list containing one entry per player on the card, with no players dropped or duplicated. | 1, 11 | 1, 2 |
| Each entry is labelled with the text as printed on the card — the player's name where one is printed, otherwise the column header — and no entry is labelled A/B/C/Marker by assumption. | 2, 3 | 1 |
| A selector listing those entries is presented above the score form. | 6, 7 | 4 |
| Choosing an entry fills the form with that player's scores only; scores belonging to other players on the card do not appear in the form. | 8, 9, 12 | 3, 4 |
| Choosing a different entry changes the filled scores to that player's. | 10, 12, 13 | 3, 4 |
| The existing tests still pass. | 14 | 1, 2, 3, 4 |

## Phase 1: Parse every player into labelled entries
<!-- phase: 1 -->
<!-- targets: league_scorecard.py, tests/test_league_scorecard_players.py -->
<!-- frozen: pages/3_🏆_League.py, tests/test_league_scorecard_fields.py, tests/test_league_scorecard_read.py, tests/test_league_scorecard_state.py, tests/test_league_scorecard_wiring.py, tests/test_league_scorecard_player_selector_wiring.py -->

**Goal:** `scorecard_player_entries` turns a parsed multi-player response into one `ScorecardPlayerEntry` per printed player, labelled exactly as read.

**Changes:**
- `league_scorecard.py`: immediately after the `ScorecardReadResult` dataclass, add:
  ```python
  @dataclass(frozen=True)
  class ScorecardPlayerEntry:
      index: int
      label: str
      found_fields: dict[str, ScorecardFieldValue]
  ```
- `league_scorecard.py`: immediately after `scorecard_field_updates` (so the normaliser is already defined), add exactly:
  ```python
  _PLAYER_LABEL_KEYS: tuple[str, ...] = (
      "label",
      "player",
      "name",
      "player_name",
      "printed_label",
      "column_header",
      "header",
      "column",
      "text",
  )


  def _player_label(record: Mapping[str, object]) -> str | None:
      """The printed label for one parsed player record, or None when it has none."""
      for key in _PLAYER_LABEL_KEYS:
          raw = record.get(key)
          if raw is None or isinstance(raw, (list, tuple, set, dict)):
              continue
          text = str(raw).strip()
          if text:
              return text
      return None


  def _player_fields(record: Mapping[str, object]) -> dict[str, ScorecardFieldValue]:
      """Normalised score fields for one parsed player record."""
      for key in ("fields", "found_fields", "scores"):
          nested = record.get(key)
          if isinstance(nested, AbcMapping):
              return scorecard_field_updates(nested)
      return scorecard_field_updates(record)


  def scorecard_player_entries(parsed: Mapping[str, object]) -> list[ScorecardPlayerEntry]:
      """Players from a parsed multi-player league-scorecard response, in printed order.

      Each parsed player supplies a label and score fields. Labels are preserved exactly
      as read. Duplicate labels remain separate entries with distinct indexes.
      Missing or malformed ``players`` data returns an empty list.
      """
      if not isinstance(parsed, AbcMapping):
          return []
      raw_players = parsed.get("players")
      if not isinstance(raw_players, (list, tuple)):
          return []
      entries: list[ScorecardPlayerEntry] = []
      for raw in raw_players:
          if not isinstance(raw, AbcMapping):
              continue
          label = _player_label(raw)
          if label is None:
              continue
          entries.append(
              ScorecardPlayerEntry(index=len(entries), label=label, found_fields=_player_fields(raw))
          )
      return entries
  ```
  `index` is the 0-based position in the returned list, so `players_result.players[index].label` is valid for every option value. No file/mime/network code is added in this phase.

**Definition of done:**
- [ ] `tests/test_league_scorecard_players.py`, test `test_entries_one_per_player_in_printed_order` (spec 1): `scorecard_player_entries({"players": [{"label": "Neo", "fields": {"net": 2}}, {"label": "刘北南", "fields": {"gross": 80}}, {"label": "张纬", "fields": {}}]})` → `[e.index for e in entries] == [0, 1, 2]` and `[e.label for e in entries] == ["Neo", "刘北南", "张纬"]`.
- [ ] `tests/test_league_scorecard_players.py`, test `test_labels_are_exactly_as_printed` (spec 2, 3): `{"label": "Neo", "fields": {}}` → label `"Neo"`; `{"column_header": "Player 2", "fields": {}}` → label `"Player 2"`.
- [ ] `tests/test_league_scorecard_players.py`, test `test_no_assumed_labels_are_synthesized` (spec 3): `{"players": [{"fields": {"net": 1}}, {"column_header": "Player 2", "fields": {}}]}` → `[e.label for e in entries] == ["Player 2"]`, `[e.index for e in entries] == [0]`, and `all(e.label not in {"A", "B", "C", "Marker"} for e in entries)`.
- [ ] `tests/test_league_scorecard_players.py`, test `test_duplicate_labels_remain_separate_entries` (spec 11): two records both labelled `"Neo"` with `fields {"net": 1}` and `{"net": 3}` → indexes `[0, 1]`, labels `["Neo", "Neo"]`, `entries[0].found_fields == {"net": 1}`, `entries[1].found_fields == {"net": 3}`.
- [ ] `tests/test_league_scorecard_players.py`, test `test_found_fields_are_normalized_target_fields_only`: `{"label": "Neo", "fields": {"net_score": "+2", "birdie": 3, "bogus": 1}}` → `found_fields == {"net": 2, "birdies": 3}`.
- [ ] `tests/test_league_scorecard_players.py`, test `test_missing_or_malformed_players_returns_empty`: `{}`, `{"players": None}`, `{"players": "nope"}`, `{"players": []}` and `{"players": [1, "x", None]}` each → `[]`.
- [ ] No new third-party dependency is introduced; `requirements.txt` and `pyproject.toml` are untouched.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_players.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Read every player from one image
<!-- phase: 2 -->
<!-- targets: league_scorecard.py, tests/test_league_scorecard_players_read.py -->
<!-- frozen: pages/3_🏆_League.py, tests/test_league_scorecard_players.py, tests/test_league_scorecard_fields.py, tests/test_league_scorecard_read.py, tests/test_league_scorecard_state.py, tests/test_league_scorecard_wiring.py, tests/test_league_scorecard_player_selector_wiring.py -->

**Goal:** `read_league_scorecard_players` returns every player on the card from one Ollama request and reports `unavailable_reason` instead of raising for empty/unsupported/failed input.

**Changes:**
- `league_scorecard.py`: immediately after the `ScorecardPlayerEntry` dataclass, add:
  ```python
  @dataclass(frozen=True)
  class LeagueScorecardPlayersResult:
      players: list[ScorecardPlayerEntry]
      unavailable_reason: str | None = None
  ```
- `league_scorecard.py`: immediately after `SCORECARD_PROMPT`, add `SCORECARD_PLAYERS_PROMPT: str` with exactly this value:
  ```python
  SCORECARD_PLAYERS_PROMPT: str = (
      "You read one photographed golf league scorecard that may show several players' scores. "
      "The card may be printed or handwritten, in Chinese, English, or both.\n"
      "Return a single JSON object and nothing else, shaped as:\n"
      '{"players": [{"label": "<text printed for this player>", "fields": {...}}, ...]}\n'
      "Rules:\n"
      '- Return one object in "players" for every player printed on the card, in the order the '
      "players appear on the card. Never drop a player and never list a player twice.\n"
      '- "label": the player\'s printed name. When no name is printed, use the column header printed '
      "above that player's scores, exactly as printed. Never invent a label and never use "
      "A/B/C/Marker.\n"
      '- "fields": an object holding only the scores that belong to this one player, using any of '
      '"date", "venue", "net", "gross", "stableford", "eagles", "birdies", "pars", "bogeys", '
      '"double_bogeys_or_worse".\n'
      '- "date": the round date as an ISO string "YYYY-MM-DD".\n'
      '- "venue": the venue/course name exactly as printed on the card.\n'
      '- "net", "gross", "stableford": integers.\n'
      '- "eagles", "birdies", "pars", "bogeys", "double_bogeys_or_worse": non-negative integer counts.\n'
      "- Omit any field you cannot read with confidence. Never guess and never invent a value.\n"
      "- Do not add keys other than \"players\", \"label\" and \"fields\"."
  )
  ```
- `league_scorecard.py`: immediately after `build_scorecard_payload`, add:
  ```python
  def build_scorecard_players_payload(image_bytes: bytes, *, model: str) -> dict[str, Any]:
      """Request body for reading every player on one league scorecard."""
      return {
          "model": model,
          "prompt": SCORECARD_PLAYERS_PROMPT,
          "images": [base64.b64encode(image_bytes).decode("ascii")],
          "stream": False,
          "format": "json",
          "options": {"temperature": 0},
      }
  ```
- `league_scorecard.py`: immediately after `read_league_scorecard`, add:
  ```python
  def read_league_scorecard_players(
      image_bytes: bytes,
      mime_type: str | None,
      *,
      timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
  ) -> LeagueScorecardPlayersResult:
      """Read every player from one league scorecard image. Never raises."""
      if not image_bytes:
          return LeagueScorecardPlayersResult([], "empty image")
      if normalize_mime_type(mime_type, image_bytes) is None:
          return LeagueScorecardPlayersResult([], "unsupported file type")
      try:
          payload = build_scorecard_players_payload(image_bytes, model=_scorecard_model())
          body = _post_ollama_generate(payload, timeout_seconds)
      except ScorecardRequestError as exc:
          return LeagueScorecardPlayersResult([], str(exc) or "service error")
      except Exception:
          return LeagueScorecardPlayersResult([], "service error")
      parsed = parse_ollama_response(body)
      if parsed is None:
          return LeagueScorecardPlayersResult([], "unparseable response")
      try:
          players = scorecard_player_entries(parsed)
      except Exception:
          return LeagueScorecardPlayersResult([], "unparseable response")
      if not players:
          return LeagueScorecardPlayersResult([], "no readable players")
      return LeagueScorecardPlayersResult(players)
  ```
  Do not modify `read_league_scorecard`, `scorecard_field_updates`, or `apply_scorecard_updates`.
- `tests/test_league_scorecard_players_read.py`: new file. Module-level constants and a monkeypatch fixture that replaces `league_scorecard._post_ollama_generate` (no network):
  ```python
  import base64
  import json

  import pytest

  import league_scorecard
  from league_scorecard import read_league_scorecard_players

  JPEG = b"\xff\xd8\xff" + b"\x00" * 32


  @pytest.fixture
  def ollama_stub(monkeypatch):
      calls = {"payloads": [], "timeouts": [], "body": ""}

      def _fake(payload, timeout_seconds):
          calls["payloads"].append(payload)
          calls["timeouts"].append(timeout_seconds)
          body = calls["body"]
          if isinstance(body, BaseException):
              raise body
          return str(body)

      monkeypatch.setattr(league_scorecard, "_post_ollama_generate", _fake)
      return calls
  ```
  Each test sets `ollama_stub["body"]` before calling; `monkeypatch` restores the real function automatically (no teardown needed, no background threads or servers).

**Definition of done:**
- [ ] `tests/test_league_scorecard_players_read.py`, test `test_reads_every_player_from_one_card` (spec 1, 7): body `json.dumps({"response": json.dumps({"players": [{"label": "Neo", "fields": {"net": 2, "birdies": 3}}, {"label": "刘北南", "fields": {"gross": 80}}]})})` → `result.unavailable_reason is None`, `[p.label for p in result.players] == ["Neo", "刘北南"]`, `result.players[0].found_fields == {"net": 2, "birdies": 3}`, `result.players[1].found_fields == {"gross": 80}`.
- [ ] `tests/test_league_scorecard_players_read.py`, test `test_request_uses_the_players_prompt` (spec 1): after a successful call, `ollama_stub["payloads"][0]["prompt"] == league_scorecard.SCORECARD_PLAYERS_PROMPT`, `["format"] == "json"`, `["stream"] is False`, `["images"] == [base64.b64encode(JPEG).decode("ascii")]`, and `ollama_stub["timeouts"][0] == league_scorecard.DEFAULT_TIMEOUT_SECONDS`; a call with `timeout_seconds=5.0` records `5.0`.
- [ ] `tests/test_league_scorecard_players_read.py`, test `test_empty_image_is_reported` (spec 4): `read_league_scorecard_players(b"", "image/jpeg")` → `players == []`, `unavailable_reason == "empty image"`, `ollama_stub["payloads"] == []`.
- [ ] `tests/test_league_scorecard_players_read.py`, test `test_unsupported_file_type_is_reported` (spec 5): `read_league_scorecard_players(b"not an image", "text/plain")` → `players == []`, `unavailable_reason == "unsupported file type"`, `ollama_stub["payloads"] == []`.
- [ ] `tests/test_league_scorecard_players_read.py`, test `test_transport_error_is_reported_not_raised`: `ollama_stub["body"] = league_scorecard.ScorecardRequestError("timeout")` → `players == []`, `unavailable_reason == "timeout"`.
- [ ] `tests/test_league_scorecard_players_read.py`, test `test_unexpected_error_is_reported_not_raised`: `ollama_stub["body"] = RuntimeError("boom")` → `players == []`, `unavailable_reason == "service error"`.
- [ ] `tests/test_league_scorecard_players_read.py`, test `test_unparseable_body_is_reported`: `ollama_stub["body"] = "not json"` → `players == []`, `unavailable_reason == "unparseable response"`.
- [ ] `tests/test_league_scorecard_players_read.py`, test `test_card_with_no_readable_players_is_reported`: body `json.dumps({"response": json.dumps({"players": []})})` → `players == []`, `unavailable_reason == "no readable players"`.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_players_read.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 3: Apply only the selected player's fields
<!-- phase: 3 -->
<!-- targets: league_scorecard.py, tests/test_league_scorecard_player_selection.py -->
<!-- frozen: pages/3_🏆_League.py, tests/test_league_scorecard_players.py, tests/test_league_scorecard_players_read.py, tests/test_league_scorecard_fields.py, tests/test_league_scorecard_read.py, tests/test_league_scorecard_state.py, tests/test_league_scorecard_wiring.py, tests/test_league_scorecard_player_selector_wiring.py -->

**Goal:** `selected_player_scorecard_updates` returns exactly the chosen entry's fields (or `{}`), and `apply_selected_player_scorecard_updates` clears then writes only those fields.

**Changes:**
- `league_scorecard.py`: immediately after `apply_scorecard_updates`, add exactly:
  ```python
  LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY: str = "league_scorecard_selected_player"


  def selected_player_scorecard_updates(
      result: LeagueScorecardPlayersResult,
      selected_index: int | None,
  ) -> dict[str, ScorecardFieldValue]:
      """Fields for exactly the selected entry, or {} when no valid entry is selected."""
      if selected_index is None or isinstance(selected_index, bool) or not isinstance(selected_index, int):
          return {}
      for entry in result.players:
          if entry.index == selected_index:
              return dict(entry.found_fields)
      return {}


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
      for field in LEAGUE_SCORECARD_FIELD_KEYS:
          key = widget_keys.get(field)
          if key is not None and key in session_state:
              del session_state[key]
      updates = selected_player_scorecard_updates(result, selected_index)
      return apply_scorecard_updates(updates, widget_keys, session_state)
  ```
  `apply_scorecard_updates` is defined earlier in the module and is not modified; a `dict` returned by `selected_player_scorecard_updates` is safe to hand to it.

**Definition of done:**
- [ ] `tests/test_league_scorecard_player_selection.py`, test `test_no_selection_returns_empty_mapping` (spec 8): with a two-player result, `selected_player_scorecard_updates(result, None) == {}` and `selected_player_scorecard_updates(result, 99) == {}` and `selected_player_scorecard_updates(result, True) == {}`.
- [ ] `tests/test_league_scorecard_player_selection.py`, test `test_selected_entry_returns_only_its_fields` (spec 9): entries `ScorecardPlayerEntry(0, "Neo", {"date": "2026-06-23", "net": 2, "birdies": 3})` and `ScorecardPlayerEntry(1, "刘北南", {"gross": 80})` → index `0` yields `{"date": "2026-06-23", "net": 2, "birdies": 3}`; index `1` yields `{"gross": 80}`.
- [ ] `tests/test_league_scorecard_player_selection.py`, test `test_no_selection_clears_the_scorecard_widget_keys` (spec 8, 12): with `session = {"league_net": 5, "league_gross": 90, "unrelated": 1}` and `WIDGET_KEYS` mapping every `LEAGUE_SCORECARD_FIELD_KEYS` entry to `"league_<field>"`, `apply_selected_player_scorecard_updates(result, None, WIDGET_KEYS, session) == []` and `session == {"unrelated": 1}`.
- [ ] `tests/test_league_scorecard_player_selection.py`, test `test_selecting_a_player_writes_only_its_present_fields` (spec 9, 12, 13): `session = {"league_net": 9, "league_birdies": 9, "league_pars": 9}`, selection `0` → returns `["date", "net", "birdies"]` and `session == {"league_date": "2026-06-23", "league_net": 2, "league_birdies": 3}`.
- [ ] `tests/test_league_scorecard_player_selection.py`, test `test_switching_players_replaces_previous_values` (spec 10): empty `session`; apply index `0` then index `1` → second call returns `["gross"]` and `session == {"league_gross": 80}` (no `league_date`, `league_net` or `league_birdies` retained).
- [ ] `tests/test_league_scorecard_player_selection.py`, test `test_duplicate_labels_are_selected_by_index` (spec 11): entries `ScorecardPlayerEntry(0, "Neo", {"net": 1})` and `ScorecardPlayerEntry(1, "Neo", {"net": 3})` → applying index `1` to an empty `session` leaves `session == {"league_net": 3}`.
- [ ] `tests/test_league_scorecard_player_selection.py`, test `test_applying_the_same_selection_twice_is_stable` (spec 13): applying index `1` twice leaves `session` equal to the snapshot taken after the first call.
- [ ] `LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY == "league_scorecard_selected_player"` asserted in the same test module.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_player_selection.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 4: Wire the player selector above the League score form
<!-- phase: 4 -->
<!-- targets: pages/3_🏆_League.py, tests/test_league_scorecard_player_selector_wiring.py, tests/test_league_scorecard_wiring.py -->
<!-- frozen: league_scorecard.py, tests/test_league_scorecard_players.py, tests/test_league_scorecard_players_read.py, tests/test_league_scorecard_player_selection.py, tests/test_league_scorecard_fields.py, tests/test_league_scorecard_read.py, tests/test_league_scorecard_state.py -->

**Goal:** The League admin score form reads every player from the uploaded card, renders a "Player" selectbox above the form with no preselection, and applies only the chosen player's fields.

**Changes:**
- `pages/3_🏆_League.py`: extend the existing `from league_scorecard import (...)` statement with `LeagueScorecardPlayersResult`, `LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY`, `apply_selected_player_scorecard_updates`, `read_league_scorecard_players`; remove `read_league_scorecard`, `apply_scorecard_updates` and `ScorecardReadResult` from that import if they become unused in the page.
- `pages/3_🏆_League.py`: find the League admin score form auto-fill block — the one that currently calls `read_league_scorecard(image_bytes, mime_type)` and then applies the result to `widget_keys`. Replace that block's read/apply statements with exactly this code (same indentation level as the code it replaces), keeping the surrounding upload widget, `image_bytes`/`mime_type` computation, `widget_keys` mapping and every score-form field untouched:
  ```python
  players_result: LeagueScorecardPlayersResult = read_league_scorecard_players(image_bytes, mime_type)
  if players_result.unavailable_reason:
      st.info(players_result.unavailable_reason)

  selected_index: int | None = st.selectbox(
      "Player",
      options=[player.index for player in players_result.players],
      format_func=lambda index: players_result.players[index].label,
      index=None,
      key=LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY,
  )

  apply_selected_player_scorecard_updates(
      players_result,
      selected_index,
      widget_keys,
      st.session_state,
  )
  ```
  If the existing block already renders the unavailable reason with a different call (e.g. `st.warning`), keep that call and only rename the variable to `players_result.unavailable_reason`. Delete the old `result` / `updates` locals that fed only the replaced calls. The selectbox and the apply call must appear before the score form's widgets are created and must not be wrapped inside `st.form(...)`.
- `tests/test_league_scorecard_player_selector_wiring.py`: new file, source-level wiring test (no Streamlit server):
  ```python
  import re
  from pathlib import Path

  PAGE = Path(__file__).resolve().parents[1] / "pages" / "3_🏆_League.py"
  SOURCE = PAGE.read_text(encoding="utf-8")
  SELECTOR_RE = re.compile(r'st\.selectbox\(\s*"Player",.*?\n\s*\)', re.S)
  ```
  Assertions as listed below; no fixtures, no teardown, no processes started.
- `tests/test_league_scorecard_wiring.py`: update **only** the assertions that name the page's old scorecard calls. Wherever it asserts the page calls `read_league_scorecard` / `apply_scorecard_updates`, change those names to `read_league_scorecard_players` / `apply_selected_player_scorecard_updates`. Leave every other assertion in the file (upload fingerprint, field keys, form wiring, and anything else) exactly as it is; do not delete or loosen any assertion.

**Definition of done:**
- [ ] `tests/test_league_scorecard_player_selector_wiring.py`, test `test_page_imports_the_multi_player_helpers`: parsing every `from league_scorecard import (...)` chunk in `SOURCE` (single-line and parenthesized multi-line, splitting on `,`, stripping and dropping `as ...`) yields a name set containing `read_league_scorecard_players`, `apply_selected_player_scorecard_updates`, `LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY`.
- [ ] `tests/test_league_scorecard_player_selector_wiring.py`, test `test_player_selector_lists_every_entry_labelled_as_printed` (spec 6, 7, 11): `SELECTOR_RE.search(SOURCE)` matches, and with the match whitespace-normalised via `" ".join(match.group(0).split())` the text contains `options=[player.index for player in players_result.players]`, `format_func=lambda index: players_result.players[index].label`, `index=None` and `key=LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY`.
- [ ] `tests/test_league_scorecard_player_selector_wiring.py`, test `test_selector_sits_above_the_selected_player_apply` (spec 6, 13): `read_league_scorecard_players(\s*image_bytes` matches, `apply_selected_player_scorecard_updates(\s*players_result,\s*selected_index,\s*widget_keys,\s*st\.session_state,?\s*\)` matches, and `read_pos < selector_pos < apply_pos` where each position is the `match.start()` of those three regexes (the `SELECTOR_RE` match supplies `selector_pos`).
- [ ] `tests/test_league_scorecard_player_selector_wiring.py`, test `test_page_no_longer_uses_the_single_player_helpers`: `"read_league_scorecard(" not in SOURCE` and `"apply_scorecard_updates(" not in SOURCE`.
- [ ] `tests/test_league_scorecard_wiring.py` (updated names only) still passes with every other assertion unchanged.
- [ ] Manual observable check: `python -m streamlit run streamlit_app.py` is **not** required; the page module is exercised by the whole-suite run at final verification.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_player_selector_wiring.py tests/test_league_scorecard_wiring.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- **Existing page-wiring test asserts the old call names.** `tests/test_league_scorecard_wiring.py` may assert `read_league_scorecard` / `apply_scorecard_updates` on the page. Phase 4 lists that file as a target with a name-only update instruction and its Verify block runs it, so a stale assertion fails inside phase 4 rather than at final verification.
- **Source-text wiring assertions are formatting sensitive.** Phase 4 mandates the exact selectbox/apply snippet; if the builder reformats it, `test_player_selector_lists_every_entry_labelled_as_printed` fails.
- **Wrong label key from the model.** The reader prompt asks for `label`; `_player_label` also accepts `player`, `name`, `player_name`, `printed_label`, `column_header`, `header`, `column`, `text`. A model that invents another key yields fewer entries — caught by phase 2's `test_reads_every_player_from_one_card`.
- **Dropped or duplicated players.** Phase 1 tests entry count, order, duplicate labels and `index` uniqueness; phase 3 tests duplicate labels selected by `index`.
- **Fields leaking between players.** Only `apply_selected_player_scorecard_updates` clears keys before writing; phase 3's `test_switching_players_replaces_previous_values` catches a leak, and phase 4's ordering assertions ensure it runs before the widgets are created.
- **Streamlit session-state ordering at runtime.** If the apply call ends up after widget creation, values will not refresh; the phase 4 ordering assertions plus manual review of the block cover this, and the existing BDD/whole-suite run catches import-level breakage.
- **Single-player behaviour regressions.** `read_league_scorecard`, `ScorecardReadResult`, `scorecard_field_updates` and `apply_scorecard_updates` are untouched (frozen in phase 4); the pre-existing frozen tests guard them in phases 1–3.

## Open questions
- A parsed player record with no label-bearing key at all cannot be labelled as printed; assumption: it is skipped rather than given an invented label, and the reader prompt guarantees a label for real cards. Documented in phase 1's `_player_label`.
- `ScorecardPlayerEntry.index` is assumed to be the 0-based position in `players`, because the spec's page snippet indexes `players_result.players[index]`. Assumed contiguous from `0` even when a malformed record is skipped.
- Failure reasons for the new reader beyond the two specified ones are assumed as `"service error"`, `"timeout"`/`"http N"` (from `ScorecardRequestError`), `"unparseable response"`, and `"no readable players"`.
- Selector persistence across reruns (spec 13) relies on Streamlit's `key=LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY`; in-process tests can only prove idempotency of the apply helper and the presence of that key in the page snippet.
- Resetting the selection when a *different* card is uploaded is not specified; assumption: unchanged existing upload/read handling governs when the reader runs, and the selectbox value persists for the current card as spec 13 requires.
- None otherwise; no item is uncovered.

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/012-league-scorecard-auto-fill-reads-every/build-log.md` with one section per phase, in order. Head each
   one `## Phase <n>: <title>`, then list the files changed, the Verify command
   you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/012-league-scorecard-auto-fill-reads-every`.

Commit only this plan's targets and `build-log.md`. Leave every other file alone,
including other features' documents under `sdlc/features/`, even for formatting;
verification fails on any file outside the targets.

The pipeline waits for this file. Once it has a section for every phase, it
verifies the whole branch and opens the pull request.

