<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@cc46541 -->
## Approach
Add one pure lookup in `league_scorecard.py` that scans `scorecard_images/` and returns the newest matching path, then add a clickable thumbnail renderer plus a small selection wrapper in the league admin page and call it where the form’s tournament, game and player values are known. Tests use temporary image directories for the lookup and AST-extracted page functions for the UI behaviour, so no Streamlit server or network is needed.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| With a tournament, game and player selected that have a matching saved scorecard, the form displays a thumbnail of that image. | 1, 12 | Phase 2 |
| When more than one file matches, the thumbnail shown is the one with the newest timestamp in its filename. | 2, 3, 14 | Phase 1 |
| Clicking the thumbnail opens the full-size image. | 4 | Phase 2 |
| Changing the selected tournament, game or player updates the thumbnail to match, or removes it when nothing matches. | 5, 6, 7, 8 | Phase 2 |
| When no file matches, or no player is selected yet, the form shows no thumbnail and no error. | 9, 10, 11 | Phase 1, Phase 2 |
| The existing tests still pass. | 15 | Phase 1, Phase 2 |

## Phase 1: Find the newest saved scorecard image
<!-- phase: 1 -->
<!-- targets: league_scorecard.py, tests/test_league_scorecard_image_lookup.py -->
<!-- frozen: pages/3_🏆_League.py, tests/test_league_scorecard_fields.py, tests/test_league_scorecard_logging.py, tests/test_league_scorecard_player_selection.py, tests/test_league_scorecard_player_selector_wiring.py, tests/test_league_scorecard_players.py, tests/test_league_scorecard_players_read.py, tests/test_league_scorecard_read.py, tests/test_league_scorecard_state.py, tests/test_league_scorecard_wiring.py, tests/test_league_page_reloads_stale_scorecard_module.py, test_streamlit_app.py -->

**Goal:** `league_scorecard.find_league_scorecard_image` returns the newest exact-match scorecard path, or `None` without raising.

**Changes:**
- `league_scorecard.py`: add, after the existing imports and before the logging section:
  ```python
  SCORECARD_IMAGES_DIR: str = os.path.join(os.path.dirname(__file__), "scorecard_images")
  ```
- `league_scorecard.py`: add private helper:
  ```python
  def _league_scorecard_game_segment(game_number: int | str | None) -> str | None:
      ...
  ```
  Rules: `None` and `bool` return `None`; non-negative `int` returns `str(game_number)`; `str` is stripped, must fully match `r"\d+"`, and is returned unchanged so leading zeros are not normalised; all other types return `None`.
- `league_scorecard.py`: add the public function exactly:
  ```python
  def find_league_scorecard_image(
      tournament: str | None,
      game_number: int | str | None,
      player: str | None,
      *,
      images_dir: str | os.PathLike[str] = SCORECARD_IMAGES_DIR,
  ) -> str | None:
      ...
  ```
  Implementation rules:
  - Return `None` if `tournament` or `player` is `None`, or after `str(value).strip()` is empty.
  - Return `None` if `_league_scorecard_game_segment(game_number)` is `None`.
  - Build `pattern = re.compile(rf"^league_{re.escape(tournament_text)}_Game_{re.escape(game_text)}_{re.escape(player_text)}_(\d{{14}})\.[^.]+$")`.
  - Use `os.scandir(images_dir)` and inspect directory entries only. Catch `OSError` from opening the directory and return `None`. Skip entries whose `is_file()` is false or raises `OSError`.
  - For each entry whose `pattern.fullmatch(entry.name)` succeeds, record `(int(match.group(1)), entry.name)`.
  - Choose the greatest `(timestamp, entry.name)` tuple. This makes timestamp ties deterministic by filename and stable across repeated calls.
  - Return `os.path.join(os.fspath(images_dir), best_name)` or `None` if no entry matched.
  - Do not open, read, write, resize, hash, or network-fetch image files.

**Definition of done:**
- [ ] `tests/test_league_scorecard_image_lookup.py`, `test_find_league_scorecard_image_returns_exactly_one_match`: create `league_2026个人联赛_Game_1_Neo_20260623172057.jpg` under `tmp_path`; assert `find_league_scorecard_image("2026个人联赛", 1, "Neo", images_dir=tmp_path) == str(card)`. Also assert the same result when `game_number` is `"1"`.
- [ ] `tests/test_league_scorecard_image_lookup.py`, `test_find_league_scorecard_image_uses_filename_timestamp_not_mtime`: create an older filename stamp and a newer filename stamp; call `os.utime` so the older filename has the newer mtime and vice versa; assert the newer filename wins.
- [ ] `tests/test_league_scorecard_image_lookup.py`, `test_find_league_scorecard_image_accepts_any_nonempty_extension`: for each of `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.bmp`, create one matching file in a separate subdirectory and assert it is returned.
- [ ] `tests/test_league_scorecard_image_lookup.py`, `test_find_league_scorecard_image_ignores_nonmatching_names`: create files with wrong tournament, wrong `Game_` segment, wrong player, 13-digit timestamp, 15-digit timestamp, missing extension, and extra `.bak` suffix; assert `None`.
- [ ] `tests/test_league_scorecard_image_lookup.py`, `test_find_league_scorecard_image_returns_none_for_missing_inputs_or_directory`: assert `None` for each of `(None, 1, "Neo")`, `("", 1, "Neo")`, `("T", None, "Neo")`, `("T", "", "Neo")`, `("T", 1, None)`, `("T", 1, "")`, a valid selection against an empty directory, and a valid selection against a non-existent directory.
- [ ] `tests/test_league_scorecard_image_lookup.py`, `test_find_league_scorecard_image_tie_is_stable`: create two files with the same 14-digit timestamp and different extensions; call twice and assert both calls return the same path from that pair.
- [ ] `tests/test_league_scorecard_image_lookup.py`, `test_find_league_scorecard_image_does_not_open_image_files`: create one matching file, monkeypatch `builtins.open` to raise `AssertionError`, call the lookup, and assert it still returns the path.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_image_lookup.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Render the clickable scorecard thumbnail on the league admin form
<!-- phase: 2 -->
<!-- targets: pages/3_🏆_League.py, tests/test_league_scorecard_thumbnail.py -->
<!-- frozen: league_scorecard.py, tests/test_league_scorecard_image_lookup.py, tests/test_league_scorecard_fields.py, tests/test_league_scorecard_logging.py, tests/test_league_scorecard_player_selection.py, tests/test_league_scorecard_player_selector_wiring.py, tests/test_league_scorecard_players.py, tests/test_league_scorecard_players_read.py, tests/test_league_scorecard_read.py, tests/test_league_scorecard_state.py, tests/test_league_scorecard_wiring.py, tests/test_league_page_reloads_stale_scorecard_module.py, test_streamlit_app.py -->

**Goal:** The league admin score form shows a clickable thumbnail for the current tournament/game/player selection and shows nothing when no image matches.

**Changes:**
- `pages/3_🏆_League.py`: ensure `import base64`, `import os`, `import streamlit as st`, and `import league_scorecard` are present (add only the missing imports; keep existing aliases and imports unchanged).
- `pages/3_🏆_League.py`: add this top-level function:
  ```python
  def render_league_scorecard_thumbnail(image_path: str | None) -> None:
      ...
  ```
  Implementation rules:
  - Return immediately when `image_path` is falsy.
  - `open(image_path, "rb")` inside `try`; return on `OSError`.
  - Return if the read payload is empty.
  - Map extension with `os.path.splitext(image_path)[1].lower()`: `.jpg`/`.jpeg` -> `image/jpeg`, `.png` -> `image/png`, `.webp` -> `image/webp`, `.gif` -> `image/gif`, anything else -> `application/octet-stream`.
  - Build `data_uri = f"data:{mime_type};base64,{base64.b64encode(payload).decode('ascii')}"`.
  - Call `st.markdown` exactly once with:
    ```python
    f'<a href="{data_uri}" target="_blank" rel="noopener"><img src="{data_uri}" width="160" alt="Saved scorecard thumbnail"></a>'
    ```
    and `unsafe_allow_html=True`.
  - Do not write files, resize images, generate cache files, or call the network.
- `pages/3_🏆_League.py`: add this top-level wrapper:
  ```python
  def render_league_scorecard_for_selection(
      tournament: str | None,
      game_number: int | str | None,
      player: str | None,
  ) -> None:
      ...
  ```
  It must call `league_scorecard.find_league_scorecard_image(tournament, game_number, player)` and pass the result to `render_league_scorecard_thumbnail`.
- `pages/3_🏆_League.py`: in the existing league admin score form block, after the tournament, game-number and player widgets have produced their current values and before the score-entry widgets, add exactly these three local aliases and the call:
  ```python
  _scorecard_tournament = <the tournament widget's current value>
  _scorecard_game_number = <the game widget's current value>
  _scorecard_player = <the player widget's current value>
  render_league_scorecard_for_selection(
      _scorecard_tournament,
      _scorecard_game_number,
      _scorecard_player,
  )
  ```
  Use the existing variables already produced by those widgets; do not create duplicate widgets, do not read widget values twice, and do not cache the resolved path in session state. The call must execute on every form rerun so changing any of the three widgets updates or removes the thumbnail.

**Definition of done:**
- [ ] `tests/test_league_scorecard_thumbnail.py`, `test_render_league_scorecard_thumbnail_does_nothing_without_path`: load `render_league_scorecard_thumbnail` from the page source with an AST function extractor and fake `st`; call it with `None`; assert `st.markdown_calls == []`.
- [ ] `tests/test_league_scorecard_thumbnail.py`, `test_render_league_scorecard_thumbnail_links_full_size_image`: create `tmp_path/"card.jpg"` with bytes `b"\xff\xd8\xff\xe0fake"`; call the extracted function; assert one `st.markdown` call with `unsafe_allow_html=True`; regex-extract `href` and `src`; assert both are the same `data:image/jpeg;base64,...` URI, the body contains `width="160"` and `target="_blank"`.
- [ ] `tests/test_league_scorecard_thumbnail.py`, `test_render_league_scorecard_thumbnail_does_nothing_for_unreadable_file`: call the extracted function with `tmp_path/"missing.jpg"`; assert no `st.markdown` call.
- [ ] `tests/test_league_scorecard_thumbnail.py`, `test_render_league_scorecard_for_selection_updates_for_each_selection`: extract `render_league_scorecard_for_selection` with a fake `league_scorecard` module whose `find_league_scorecard_image` records `(tournament, game_number, player)` and returns a configured path; use a fake renderer recording paths; call with `("T1", 1, "P1")`, `("T2", 2, "P2")`, `(None, 1, "P1")`, `("T1", None, "P1")`, and `("T1", 1, None)`; assert the lookup calls match exactly and the renderer receives the returned path or `None`.
- [ ] `tests/test_league_scorecard_thumbnail.py`, `test_league_page_calls_thumbnail_helper_in_form`: parse the page with `ast`; assert top-level functions `render_league_scorecard_thumbnail` and `render_league_scorecard_for_selection` exist; assert an `ast.Call` to `render_league_scorecard_for_selection` exists with three positional arguments; assert the page source contains `league_scorecard.find_league_scorecard_image`.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_thumbnail.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- Filename matching is exact and case-sensitive; a wrong regex or unescaped tournament/player text would silently return `None`. Phase 1’s exact-match and nonmatching-name tests catch this.
- Timestamp comparison could accidentally use filesystem mtimes. Phase 1’s mtime-conflict test catches this.
- Tie handling could be unstable. Phase 1’s repeated-call tie test catches this.
- The thumbnail may not be clickable if `href` and `src` are not the same full-size data URI. Phase 2’s link test catches this.
- The page may resolve the image before all three selections are known or only once. Phase 2’s selection-wrapper test and AST call test catch the helper-level behaviour; the form call must remain inside the rerun path.
- Embedding a large image as a data URI increases page payload size. This is accepted by the spec because no thumbnail cache or disk resize is allowed.
- Phase 2 assumes the three widget values are in scope in the league admin score form block; the implementation reuses those existing values and only adds the `_scorecard_*` aliases at the call site.

## Open questions
None.

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/013-league-admin-score-form-if-scorecard/build-log.md` with one section per phase, in order. Head each
   one `## Phase <n>: <title>`, then list the files changed, the Verify command
   you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/013-league-admin-score-form-if-scorecard`.

Commit only this plan's targets and `build-log.md`. Leave every other file alone,
including other features' documents under `sdlc/features/`, even for formatting;
verification fails on any file outside the targets.

The pipeline waits for this file. Once it has a section for every phase, it
verifies the whole branch and opens the pull request.

