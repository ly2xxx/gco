<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@68f1750 -->
## Approach
Add pure saved-scorecard filename lookup and raw-GitHub URL helpers to `league_scorecard.py`, then add two thin Streamlit helpers to the league page: one renders the matched file as-is at 160 pixels wide, linking to raw GitHub only when configured, and the other opens the same saved path in a View dialog. Wire the preview to the existing tournament/game/player selections, with no image processing, caching, rotation, or `data:` URLs.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| With a tournament, game and player selected that have a matching saved scorecard, the form displays the saved file as-is at 160 pixels wide; when more than one file matches, the thumbnail is the one with the newest timestamp in its filename. | 1, 2, 3, 4, 5, 13 | 1, 2, 3 |
| The thumbnail and View dialog show the saved file without rotation or EXIF orientation handling, and no cached thumbnail is used. | 14, 15, 18 | 2 |
| When `GITHUB_REPO` is set, the thumbnail links to `raw.githubusercontent.com/<repo>/HEAD/scorecard_images/<file>` and opens in a new tab. | 19, 20, 21, 22 | 1, 2 |
| The View button opens a dialog showing the same saved file as-is, and no displayed scorecard image is supplied as a `data:` URL. | 16, 17, 23 | 2 |
| Changing the selected tournament, game or player updates the thumbnail and dialog image to match, or removes them when nothing matches; no match or incomplete selection shows no thumbnail and no error, and selecting "Game 5" matches game 5 filenames. | 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 24, 25 | 1, 2, 3 |
| The existing tests still pass. | 26 | 3 |

## Phase 1: Saved-scorecard lookup and GitHub URL helpers
<!-- phase: 1 -->
<!-- targets: league_scorecard.py, tests/test_league_saved_scorecard.py -->
<!-- frozen: tests/test_league_scorecard_fields.py, tests/test_league_scorecard_players.py, tests/test_league_scorecard_read.py, tests/test_league_scorecard_state.py, tests/test_league_scorecard_wiring.py -->

**Goal:** Given a tournament, game label and player, the module returns the newest matching saved scorecard or `None`, and builds the exact raw GitHub URL when configured.

**Changes:**
- `league_scorecard.py`: add module constants after `ScorecardFieldValue`:
  - `SCORECARD_IMAGES_DIR: str = "scorecard_images"`
  - `SCORECARD_THUMBNAIL_WIDTH: int = 160`
  - `SCORECARD_IMAGE_SUFFIXES: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp", ".gif")`
- `league_scorecard.py`: add frozen dataclass:
  ```python
  @dataclass(frozen=True)
  class SavedScorecard:
      filename: str
      path: str
      timestamp: str
  ```
- `league_scorecard.py`: add `game_number_from_label(game_label: object) -> int | None`. Convert non-`None` values with `str(...).strip()`, full-match `re.fullmatch(r"game\s+(\d+)", text, re.IGNORECASE)`, and return `int(match.group(1))`. Return `None` for `None`, empty text, or any non-matching label; never raise.
- `league_scorecard.py`: add `find_saved_scorecard(tournament: object, game_label: object, player: object, *, directory: str = SCORECARD_IMAGES_DIR) -> SavedScorecard | None`.
  - Return `None` when `tournament` or `player` is `None`/empty/whitespace, or when `game_number_from_label(game_label)` is `None`.
  - Return `None` when `os.path.isdir(directory)` is false.
  - Build exact prefix `f"league_{tournament}_Game_{game_number}_{player}_"` using the original tournament/player strings; matching is exact and case-sensitive for those names.
  - Iterate `os.listdir(directory)` inside `try/except OSError: return None`.
  - For each filename, use `os.path.splitext(filename)`; keep only suffixes whose lower-case form is in `SCORECARD_IMAGE_SUFFIXES`.
  - Keep only filenames that `startswith(prefix)`; then the stem remainder after `len(prefix)` must be all digits. This ensures `_Game_5_` does not match `_Game_15_`.
  - Return `None` when no candidates exist. Otherwise return `max(candidates, key=lambda card: (int(card.timestamp), card.filename))`.
  - Set `SavedScorecard.path` to `os.path.join(directory, filename)` so default paths are exactly `scorecard_images/<file>`.
- `league_scorecard.py`: add `scorecard_image_url(repo: str | None, filename: str) -> str | None`. Return `None` when stripped repo is empty or filename is empty. Otherwise return exactly `f"https://raw.githubusercontent.com/{repo_text}/HEAD/scorecard_images/{filename_text}"` with no URL encoding.
- `league_scorecard.py`: add `scorecard_github_repo() -> str | None` returning `_configured_value(("GITHUB_REPO",))`.

**Definition of done:**
- [ ] `tests/test_league_saved_scorecard.py`, test `test_game_number_from_label_parses_supported_labels`: assert `"Game 5" -> 5`, `"game 15" -> 15`, `"Game 0" -> 0`, and `"Game5"`, `"5"`, `None` all return `None` without raising. Proves spec behaviours 3, 4, 5.
- [ ] `tests/test_league_saved_scorecard.py`, test `test_find_saved_scorecard_selects_newest_matching_timestamp`: create `league_Cup_Game_2_Alice_20260101000000.jpg` and `league_Cup_Game_2_Alice_20260202000000.png` in `tmp_path`; call with `directory=str(tmp_path)`; assert result equals `SavedScorecard(filename="league_Cup_Game_2_Alice_20260202000000.png", path=str(tmp_path / "league_Cup_Game_2_Alice_20260202000000.png"), timestamp="20260202000000")`. Proves spec behaviour 2.
- [ ] `tests/test_league_saved_scorecard.py`, test `test_find_saved_scorecard_matches_exact_game_number`: create `_Game_1_`, `_Game_5_`, `_Game_15_` files for the same player; lookup `"Game 5"` and assert only `_Game_5_` is returned. Proves spec behaviours 3 and 4.
- [ ] `tests/test_league_saved_scorecard.py`, test `test_find_saved_scorecard_returns_none_for_incomplete_selection_or_missing_directory`: assert `None` when tournament, game label or player is empty/`None`, and when `directory` does not exist. Proves spec behaviours 5, 6 and 12.
- [ ] `tests/test_league_saved_scorecard.py`, test `test_find_saved_scorecard_supports_displayable_suffixes`: create `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif` and `.txt` files; assert an image suffix is returned and `.txt` is ignored. Proves spec behaviour 13.
- [ ] `tests/test_league_saved_scorecard.py`, test `test_scorecard_image_url_builds_raw_github_url`: assert `scorecard_image_url("owner/repo", "foo.jpg") == "https://raw.githubusercontent.com/owner/repo/HEAD/scorecard_images/foo.jpg"` and blank repo returns `None`. Proves spec behaviours 19 and 20.
- [ ] `tests/test_league_saved_scorecard.py`, test `test_scorecard_github_repo_reads_environment_and_blank_is_unset`: use `monkeypatch.setenv("GITHUB_REPO", "owner/repo")` then assert the value; `monkeypatch.setenv("GITHUB_REPO", "   ")` and assert `None`. Proves spec behaviours 19 and 20.
- [ ] No background threads, servers or external resources are started; `tmp_path` and `monkeypatch` handle cleanup.

**Verify:**
```bash
python -m pytest tests/test_league_saved_scorecard.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: League page preview and View dialog helpers
<!-- phase: 2 -->
<!-- targets: pages/3_🏆_League.py, tests/test_league_saved_scorecard_preview.py -->
<!-- frozen: league_scorecard.py, tests/test_league_saved_scorecard.py, tests/test_league_scorecard_player_selection.py, tests/test_league_scorecard_player_selector_wiring.py, tests/test_league_scorecard_wiring.py -->

**Goal:** The league page exposes a preview helper that renders the matched saved file unchanged at 160 pixels wide, links it only when `GITHUB_REPO` is set, and opens the same saved path in a View dialog.

**Changes:**
- `pages/3_🏆_League.py`: add these names to the existing `league_scorecard` import list at the top:
  ```python
  from league_scorecard import (
      SCORECARD_THUMBNAIL_WIDTH,
      SavedScorecard,
      find_saved_scorecard,
      scorecard_github_repo,
      scorecard_image_url,
  )
  ```
  Merge with the existing import statement rather than adding a second conflicting import.
- `pages/3_🏆_League.py`: add near the top of the file, after imports:
  ```python
  @st.dialog("Saved scorecard")
  def _saved_scorecard_dialog(scorecard: SavedScorecard) -> None:
      st.image(scorecard.path)


  def show_saved_scorecard_dialog(scorecard: SavedScorecard) -> None:
      _saved_scorecard_dialog(scorecard)


  def render_league_scorecard_preview(
      tournament: object,
      game_label: object,
      player: object,
  ) -> None:
      scorecard = find_saved_scorecard(tournament, game_label, player)
      if scorecard is None:
          return

      repo = scorecard_github_repo()
      url = scorecard_image_url(repo, scorecard.filename)
      if url is not None:
          st.markdown(
              f'<a href="{url}" target="_blank" rel="noopener noreferrer">'
              f'<img src="{url}" width="{SCORECARD_THUMBNAIL_WIDTH}" alt="Saved scorecard">'
              f'</a>',
              unsafe_allow_html=True,
          )
      else:
          st.image(scorecard.path, width=SCORECARD_THUMBNAIL_WIDTH)

      if st.button("View", key=f"view_saved_scorecard_{scorecard.filename}"):
          show_saved_scorecard_dialog(scorecard)
  ```
- Do not read image bytes, pass a `data:` URL, rotate, transpose, convert, resize or cache the image. For the non-GitHub thumbnail, pass `scorecard.path` directly to `st.image` with `width=SCORECARD_THUMBNAIL_WIDTH`. For the dialog, pass `scorecard.path` directly to `st.image` with no width.
- Do not render the View button or any thumbnail when `find_saved_scorecard` returns `None`; return before any Streamlit output.

**Definition of done:**
- [ ] `tests/test_league_saved_scorecard_preview.py`, fixture `page_preview`: read `pages/3_🏆_League.py` with `Path(...).read_text(encoding="utf-8")`, parse with `ast.parse`, keep the `FunctionDef` nodes named `_saved_scorecard_dialog`, `show_saved_scorecard_dialog` and `render_league_scorecard_preview`, then `exec` them into a namespace containing a `FakeStreamlit` object, `SavedScorecard`, `SCORECARD_THUMBNAIL_WIDTH`, `find_saved_scorecard`, `scorecard_github_repo` and `scorecard_image_url`. `FakeStreamlit` records `image(image, width=None)`, `markdown(body, unsafe_allow_html=False)`, `button(label, key=None)` and `dialog(title)`; `dialog` returns a decorator that records the title and returns the wrapped function. No teardown is needed because no threads, servers or files are opened.
- [ ] `tests/test_league_saved_scorecard_preview.py`, test `test_render_preview_uses_saved_path_at_160px_without_github_repo`: set `find_saved_scorecard` to return `SavedScorecard("foo.jpg", "scorecard_images/foo.jpg", "20260101000000")`, `scorecard_github_repo` to return `None`, and `button_clicked=False`; call `render_league_scorecard_preview(...)`; assert `fake.image_calls == [("scorecard_images/foo.jpg", 160)]`, `fake.markdown_calls == []`, `fake.button_calls[0][0] == "View"`, and no recorded image source or markdown body starts with or contains `data:`. Proves spec behaviours 1, 14, 16, 18 and 22.
- [ ] `tests/test_league_saved_scorecard_preview.py`, test `test_render_preview_links_thumbnail_when_github_repo_set`: set `scorecard_github_repo` to return `"owner/repo"` and `button_clicked=False`; call the helper with `foo.jpg`; assert one markdown body contains `<a href="https://raw.githubusercontent.com/owner/repo/HEAD/scorecard_images/foo.jpg" target="_blank"`, contains `<img src="https://raw.githubusercontent.com/owner/repo/HEAD/scorecard_images/foo.jpg" width="160"`, and `fake.image_calls == []`. Proves spec behaviours 3, 19 and 21.
- [ ] `tests/test_league_saved_scorecard_preview.py`, test `test_show_saved_scorecard_dialog_uses_same_saved_path`: call `show_saved_scorecard_dialog(SavedScorecard("foo.jpg", "scorecard_images/foo.jpg", "20260101000000"))`; assert `fake.dialog_title == "Saved scorecard"`, `fake.image_calls == [("scorecard_images/foo.jpg", None)]`, and no source contains `data:`. Proves spec behaviours 4, 15, 17 and 23.
- [ ] `tests/test_league_saved_scorecard_preview.py`, test `test_view_button_opens_dialog_with_same_path`: set `find_saved_scorecard` to return a card, `scorecard_github_repo` to return `None`, and `button_clicked=True`; call the helper; assert `fake.image_calls == [("scorecard_images/foo.jpg", 160), ("scorecard_images/foo.jpg", None)]` and `fake.dialog_title == "Saved scorecard"`. Proves spec behaviours 4 and 23.
- [ ] `tests/test_league_saved_scorecard_preview.py`, test `test_no_match_renders_nothing`: set `find_saved_scorecard` to return `None` and `button_clicked=True`; call the helper; assert `fake.image_calls == []`, `fake.markdown_calls == []` and `fake.button_calls == []`. Proves spec behaviours 6, 7, 8, 9, 10 and 11.
- [ ] `tests/test_league_saved_scorecard_preview.py`, test `test_preview_changes_with_selection`: use a `find_saved_scorecard` stub returning card A for one selection and card B for another; call the helper twice; assert the last `fake.image_calls[0]` uses card B's path. Proves spec behaviours 24 and 25.

**Verify:**
```bash
python -m pytest tests/test_league_saved_scorecard_preview.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 3: Wire preview into the league admin score form
<!-- phase: 3 -->
<!-- targets: pages/3_🏆_League.py, tests/test_league_saved_scorecard_wiring.py -->
<!-- frozen: league_scorecard.py, tests/test_league_saved_scorecard.py, tests/test_league_saved_scorecard_preview.py, tests/test_league_scorecard_player_selection.py, tests/test_league_scorecard_player_selector_wiring.py, tests/test_league_scorecard_wiring.py -->

**Goal:** The league admin score form calls the preview for its current tournament, game label and player, so a matching selection shows the saved scorecard and changes or missing matches rerender without errors.

**Changes:**
- `pages/3_🏆_League.py`: inside the existing league admin score entry section, immediately after the tournament selectbox, game-label selectbox and player selectbox values for the score record have been read, add exactly one call with three positional arguments:
  ```python
  render_league_scorecard_preview(tournament, game_label, player)
  ```
  Use the same local values that the existing form uses for the score record. If those locals have different names, bind them to `tournament`, `game_label` and `player` immediately before this call. Do not add new session-state keys, widgets, caching, or image processing.
- Place the call outside any `st.form` submission block so Streamlit reruns when the three selections change; do not defer it until a submit button click.

**Definition of done:**
- [ ] `tests/test_league_saved_scorecard_wiring.py`, test `test_league_score_form_calls_saved_scorecard_preview_with_selection_values`: read `pages/3_🏆_League.py`, parse with `ast.parse`, collect all `ast.Call` nodes whose `func` is `ast.Name(id="render_league_scorecard_preview")`; assert exactly one call exists outside the function definition, it has exactly three positional arguments and no keyword arguments, and every argument is a non-constant expression (`ast.Name`, `ast.Attribute` or `ast.Subscript`). Proves the form passes current selection values to the preview. Covers spec behaviours 1, 24 and 25.
- [ ] `tests/test_league_saved_scorecard_wiring.py`, test `test_league_page_compiles_after_preview_wiring`: call `compile(Path("pages/3_🏆_League.py").read_text(encoding="utf-8"), "pages/3_🏆_League.py", "exec")` and assert it does not raise. Proves the page remains syntactically valid after wiring.
- [ ] No background threads, servers or external resources are started; the test only reads and compiles source files.

**Verify:**
```bash
python -m pytest tests/test_league_saved_scorecard_wiring.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- Filename matching could accidentally treat `_Game_1_` as matching `_Game_15_`, or could match the wrong player/tournament. Phase 1’s exact-prefix and exact-game tests catch this.
- A missing `scorecard_images/` directory or an unreadable directory could raise from `os.listdir`. Phase 1 returns `None` on `OSError` and tests the missing-directory path.
- The GitHub link could be rendered with the wrong URL or without `target="_blank"`. Phase 1 tests the URL helper and Phase 2 tests the markdown anchor.
- The preview could accidentally pass bytes or a `data:` URL to Streamlit. Phase 2 tests assert the recorded image source is always `scorecard.path` or the raw GitHub URL and never contains `data:`.
- The View dialog could show a different file from the thumbnail. Phase 2’s button test asserts both the 160-pixel thumbnail and dialog use the same `scorecard.path`.
- Wiring the preview inside an `st.form` would prevent reruns on selection changes. Phase 3 requires the call outside the form submission block; the source test catches a missing call, and the full final suite catches import/run regressions.
- Existing league page tests could break if the new imports shadow existing names. Phase 3’s compile test catches syntax/import-name errors in source, and the final full suite catches runtime regressions.
- Streamlit’s `st.dialog` API could differ from the fake test double. Phase 2 assumes the repository’s Streamlit version supports `st.dialog`; the final full suite and Streamlit verification catch runtime incompatibility.

## Open questions
None. The plan follows the spec assumptions: exact case-sensitive tournament/player matching, supported displayable suffixes only, no URL encoding of the GitHub filename, stable arbitrary tie-break by filename, and no image processing or caching.

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

