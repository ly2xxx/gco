<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@0b0d8ae -->
## Approach
Add image lookup, GitHub URL, and cached Pillow JPEG helpers to `league_scorecard.py`, then add a thin Streamlit renderer in `league_scorecard_ui.py` that `pages/3_🏆_League.py` calls after the tournament/game/player selection. The renderer shows a thumbnail from JPEG bytes, an optional GitHub link, and a View dialog; it never constructs or passes a `data:` URL, and every failure path returns without rendering.

## Coverage
| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| With a tournament, game and player selected that have a matching saved scorecard, the form displays a small upright thumbnail; when more than one file matches, the thumbnail is the one with the newest timestamp in its filename. | 1, 2 | 1, 2, 3 |
| When `GITHUB_REPO` is set, the thumbnail links to the original file on GitHub and opens in a new tab. | 13, 14 | 1, 3 |
| The View button opens an upright version of the image in a dialog, and no displayed scorecard image is supplied as a `data:` URL. | 8, 15, 16 | 2, 3 |
| Changing the selected tournament, game or player updates the thumbnail and dialog image to match, or removes them when nothing matches; no match or incomplete selection shows no thumbnail and no error, and selecting "Game 5" matches game 5 filenames. | 3, 4, 5, 6, 10, 17, 18 | 1, 2, 3 |
| The existing tests still pass. | 19 | 1, 2, 3 |

## Phase 1: League scorecard image lookup and GitHub URL
<!-- phase: 1 -->
<!-- targets: league_scorecard.py, tests/test_league_scorecard_images.py -->
<!-- frozen: tests/test_league_scorecard_read.py, tests/test_league_scorecard_fields.py, tests/test_league_scorecard_players.py, tests/test_league_scorecard_players_read.py -->

**Goal:** A reviewer can run the new lookup tests and see that incomplete selections, missing directories and no-match cases return `None`, newest filename timestamp wins, and GitHub URLs are correctly quoted.

**Changes:**
- `league_scorecard.py`: add `from pathlib import Path` and `from urllib.parse import quote`; keep existing imports.
- `league_scorecard.py`: add `SCORECARD_IMAGES_DIR: str = "scorecard_images"`.
- `league_scorecard.py`: add:
  ```python
  @dataclass(frozen=True)
  class LeagueScorecardImageMatch:
      path: Path
      timestamp: int
  ```
- `league_scorecard.py`: add private `_selection_text(value: object) -> str` returning `""` for `None`/`bool`, otherwise `str(value).strip()`.
- `league_scorecard.py`: add `def game_number_from_selection(selection: object) -> int | None:`
  - Reject `bool` and `None`.
  - If `isinstance(selection, int)`, return it only when `selection > 0`, else `None`.
  - Otherwise use `_selection_text`; fullmatch with `re.fullmatch(r"(?i)\s*(?:game[\s_-]*)?(\d+)\s*", text)`; return `int(group)` only when `> 0`, else `None`.
  - `"Game 5"`, `"Game_5"`, `"  Game 05  "` and `"5"` return `5`; `""`, `"Game 0"`, `"Game X"`, `0`, `-1` return `None`.
- `league_scorecard.py`: add:
  ```python
  def find_league_scorecard_image(
      tournament: object,
      game: object,
      player: object,
      *,
      directory: str | os.PathLike[str] = SCORECARD_IMAGES_DIR,
  ) -> LeagueScorecardImageMatch | None:
  ```
  - `tournament_text = _selection_text(tournament)`, `player_text = _selection_text(player)`; return `None` if either is empty.
  - `game_no = game_number_from_selection(game)`; return `None` if `None`.
  - `root = Path(directory)`; return `None` if `not root.is_dir()`.
  - Iterate `root.iterdir()` inside `try/except OSError`; skip entries where `entry.is_file()` raises `OSError` or returns `False`.
  - Match `entry.name` with `re.fullmatch(rf"league_{re.escape(tournament_text)}_Game_{game_no}_(?P<player>.+?)_(?P<timestamp>\d+)\.(?P<ext>[^.]+)", entry.name)`; skip if no match or `match.group("player") != player_text`.
  - Track best by `(timestamp, entry.name)` so ties are deterministic; return `LeagueScorecardImageMatch(path=entry, timestamp=timestamp)`.
  - Return `None` for missing directory, unreadable directory, or no match.
- `league_scorecard.py`: add:
  ```python
  def scorecard_github_url(
      repo: str | None,
      file_name: str,
      *,
      branch: str = "main",
  ) -> str | None:
  ```
  - Return `None` when `repo` or `file_name` is blank after stripping.
  - Strip slashes from `repo`; use `branch or "main"`.
  - Return `https://github.com/{quote(repo_text, safe="/")}/blob/{quote(branch_text, safe="/")}/scorecard_images/{quote(file_text, safe="")}`.

**Definition of done:**
- [ ] `tests/test_league_scorecard_images.py`, test `test_game_number_from_selection_parses_game_labels`: asserts the positive and rejected values listed above; no fixtures beyond `pytest`.
- [ ] `tests/test_league_scorecard_images.py`, test `test_find_league_scorecard_image_picks_newest_timestamp`: create `tmp_path` files named `league_2026个人联赛_Game_5_Alice_20260101000000.jpg`, `league_2026个人联赛_Game_5_Alice_20270101000000.jpg`, `league_2026个人联赛_Game_5_Alice_20250101000000.png`, `league_2026个人联赛_Game_4_Alice_20990101000000.jpg`, and `league_other_Game_5_Alice_20990101000000.jpg`; assert the returned `path.name` ends with `20270101000000.jpg` and `timestamp == 20270101000000`.
- [ ] `tests/test_league_scorecard_images.py`, test `test_find_league_scorecard_image_returns_none_for_incomplete_or_missing`: assert `None` for blank tournament, blank player, `"Game 0"`, missing directory, and no matching player; no teardown needed because `tmp_path` is pytest-managed.
- [ ] `tests/test_league_scorecard_images.py`, test `test_scorecard_github_url_builds_quoted_blob_url`: assert `scorecard_github_url("owner/repo", "league_2026个人联赛_Game_5_Alice_20260101000000.jpg")` equals `https://github.com/owner/repo/blob/main/scorecard_images/league_2026%E4%B8%AA%E4%BA%BA%E8%81%94%E8%B5%9B_Game_5_Alice_20260101000000.jpg`; assert `None` for blank repo/file and assert a custom `branch="release/2026"` preserves its slash.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_images.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Cached upright thumbnail and View JPEGs
<!-- phase: 2 -->
<!-- targets: league_scorecard.py, requirements.txt, uv.lock, tests/test_league_scorecard_images_jpeg.py -->
<!-- frozen: tests/test_league_scorecard_read.py, tests/test_league_scorecard_fields.py, tests/test_league_scorecard_players.py, tests/test_league_scorecard_players_read.py, tests/test_league_scorecard_images.py -->

**Goal:** A reviewer can verify from tests that PNG files become JPEG bytes, EXIF orientation is applied, the source file is unchanged, corrupt files return `None`, and identical requests reuse cached bytes without decoding twice.

**Changes:**
- `requirements.txt`: ensure `Pillow>=10.0,<12` is listed exactly once.
- `uv.lock`: refresh the lockfile after the `requirements.txt` change using `uv lock`; do not run this from the Verify block.
- `league_scorecard.py`: add `import io`, `from threading import Lock`, `from PIL import Image, ImageOps`.
- `league_scorecard.py`: add module-level cache:
  ```python
  _SCORECARD_JPEG_CACHE: dict[tuple[str, int, int, int, int], bytes] = {}
  _SCORECARD_JPEG_CACHE_LOCK = Lock()
  _SCORECARD_JPEG_CACHE_MAX_ENTRIES = 64
  ```
- `league_scorecard.py`: add private:
  ```python
  def _cached_scorecard_jpeg(
      path: str | os.PathLike[str],
      *,
      max_edge: int,
      quality: int,
  ) -> bytes | None:
  ```
  - Return `None` when `max_edge <= 0`.
  - Clamp `quality` to `1..95` with `int`.
  - `p = Path(path)`; `stat = p.stat()` inside `try/except OSError` returning `None`.
  - Key is `(str(p.resolve()), stat.st_mtime_ns, stat.st_size, max_edge, clamped_quality)`.
  - Under `_SCORECARD_JPEG_CACHE_LOCK`: return cached bytes if key exists; otherwise decode with `Image.open(p)` as a context manager, apply `ImageOps.exif_transpose`, `convert("RGB")`, `thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)`, save to `io.BytesIO()` with `format="JPEG", quality=clamped_quality, optimize=True`.
  - Catch `Exception` during open/convert/save and return `None`.
  - If cache has `>= _SCORECARD_JPEG_CACHE_MAX_ENTRIES`, `clear()` before inserting; return `buffer.getvalue()`.
  - Hold the lock during decode so the same key is decoded at most once.
- `league_scorecard.py`: add:
  ```python
  def cached_scorecard_thumbnail_jpeg(
      path: str | os.PathLike[str],
      *,
      max_edge: int = 320,
      quality: int = 85,
  ) -> bytes | None:
      return _cached_scorecard_jpeg(path, max_edge=max_edge, quality=quality)
  ```
- `league_scorecard.py`: add:
  ```python
  def cached_scorecard_view_jpeg(
      path: str | os.PathLike[str],
      *,
      max_edge: int = 1600,
      quality: int = 90,
  ) -> bytes | None:
      return _cached_scorecard_jpeg(path, max_edge=max_edge, quality=quality)
  ```

**Definition of done:**
- [ ] `tests/test_league_scorecard_images_jpeg.py`, test `test_cached_scorecard_thumbnail_jpeg_converts_png_to_jpeg_and_preserves_file`: create a 20x10 PNG with Pillow, read `before = path.read_bytes()`, call `cached_scorecard_thumbnail_jpeg(path)`, assert returned bytes start with `b"\xff\xd8\xff"`, `Image.open(io.BytesIO(result)).format == "JPEG"`, size `(20, 10)`, and `path.read_bytes() == before`; no teardown needed because `tmp_path` is pytest-managed.
- [ ] `tests/test_league_scorecard_images_jpeg.py`, test `test_cached_scorecard_thumbnail_jpeg_applies_exif_orientation`: create a 10x20 JPEG, set EXIF tag `274` to `6`, save with `exif=exif`; call thumbnail with `max_edge=320`; assert decoded size is `(20, 10)`.
- [ ] `tests/test_league_scorecard_images_jpeg.py`, test `test_cached_scorecard_thumbnail_jpeg_is_cached_by_stat_and_parameters`: monkeypatch `league_scorecard.Image.open` to a wrapper that increments `calls`; call `cached_scorecard_thumbnail_jpeg(path, max_edge=320, quality=85)` twice; assert `calls == 1` and both returned byte strings are identical.
- [ ] `tests/test_league_scorecard_images_jpeg.py`, test `test_cached_scorecard_thumbnail_jpeg_invalidates_on_file_change`: create image A, call thumbnail, overwrite the same path with image B, bump `st_mtime_ns` by `1_000_000_000` with `os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))`, call again; assert the second bytes differ from the first.
- [ ] `tests/test_league_scorecard_images_jpeg.py`, test `test_cached_scorecard_view_jpeg_uses_larger_edge`: create a 2000x1000 JPEG; assert thumbnail decoded size `(320, 160)` and view decoded size `(1600, 800)`.
- [ ] `tests/test_league_scorecard_images_jpeg.py`, test `test_cached_scorecard_thumbnail_jpeg_returns_none_for_corrupt_or_missing`: write `b"not an image"` to a `.jpg` file and call both helpers; assert both return `None`; assert a missing path returns `None`; no teardown needed because monkeypatch restores `Image.open` automatically.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_images_jpeg.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 3: Streamlit thumbnail, GitHub link and View dialog
<!-- phase: 3 -->
<!-- targets: league_scorecard_ui.py, pages/3_🏆_League.py, tests/test_league_scorecard_ui.py, tests/test_league_scorecard_page_wiring.py -->
<!-- frozen: tests/test_league_scorecard_read.py, tests/test_league_scorecard_fields.py, tests/test_league_scorecard_players.py, tests/test_league_scorecard_players_read.py, tests/test_league_scorecard_images.py, tests/test_league_scorecard_images_jpeg.py, tests/test_league_scorecard_wiring.py, tests/test_league_scorecard_player_selector_wiring.py, tests/test_league_page_reloads_stale_scorecard_module.py, tests/test_league_scorecard_state.py -->

**Goal:** A reviewer can run the UI tests and see that a matched selection renders JPEG bytes, `GITHUB_REPO` adds the GitHub link, View opens the larger upright JPEG, no match/incomplete selection renders nothing, selection changes replace the image, and no `data:` URL is passed.

**Changes:**
- New `league_scorecard_ui.py`:
  ```python
  """Streamlit rendering for saved league scorecards."""
  from __future__ import annotations

  import os
  from pathlib import Path

  import streamlit as st

  from league_scorecard import (
      SCORECARD_IMAGES_DIR,
      cached_scorecard_thumbnail_jpeg,
      cached_scorecard_view_jpeg,
      find_league_scorecard_image,
      scorecard_github_url,
  )
  ```
- New `league_scorecard_ui.py`: add:
  ```python
  def _render_scorecard_thumbnail(thumbnail_jpeg: bytes, github_url: str | None) -> None:
  ```
  - Build `kwargs: dict[str, object] = {"width": 160, "output_format": "JPEG"}`.
  - If `github_url` is truthy, add `kwargs["link"] = github_url`.
  - Call `st.image(thumbnail_jpeg, **kwargs)` inside `try`; on `TypeError`, remove `"link"` from `kwargs`, call `st.image(thumbnail_jpeg, **kwargs)`, and if `github_url` is truthy call `st.link_button("Open original on GitHub", github_url)`.
- New `league_scorecard_ui.py`: add:
  ```python
  def _show_scorecard_view_dialog(view_jpeg: bytes, file_name: str) -> None:
  ```
  - `dialog_factory = getattr(st, "dialog", None)`.
  - If `None`, call `st.image(view_jpeg, width=800, output_format="JPEG")` and return.
  - Otherwise define `@dialog_factory(f"Scorecard: {file_name}")` on an inner zero-argument function that calls `st.image(view_jpeg, use_container_width=True, output_format="JPEG")`, then call the inner function.
- New `league_scorecard_ui.py`: add:
  ```python
  def render_saved_league_scorecard(
      *,
      tournament: object,
      game: object,
      player: object,
      scorecard_images_dir: str | os.PathLike[str] = SCORECARD_IMAGES_DIR,
      github_repo: str | None = None,
  ) -> None:
  ```
  - `match = find_league_scorecard_image(tournament, game, player, directory=scorecard_images_dir)`; if `None`, return.
  - `thumbnail = cached_scorecard_thumbnail_jpeg(match.path)`; if `None`, return.
  - `view = cached_scorecard_view_jpeg(match.path)`; if `None`, return.
  - `github_url = scorecard_github_url(github_repo, match.path.name)`.
  - Call `_render_scorecard_thumbnail(thumbnail, github_url)`.
  - If `st.button("View", key=f"league_scorecard_view_{match.path.name}")`, call `_show_scorecard_view_dialog(view, match.path.name)`.
  - Do not build or pass any string beginning with `"data:"`.
- `pages/3_🏆_League.py`: add `import os` if missing; add `from league_scorecard import SCORECARD_IMAGES_DIR` if missing; add `from league_scorecard_ui import render_saved_league_scorecard`.
- `pages/3_🏆_League.py`: inside the existing league admin score form, immediately after the existing player selection widget is assigned to its local variable and before the score input widgets, call:
  ```python
  render_saved_league_scorecard(
      tournament=selected_tournament,
      game=selected_game,
      player=selected_player,
      scorecard_images_dir=SCORECARD_IMAGES_DIR,
      github_repo=os.environ.get("GITHUB_REPO"),
  )
  ```
  Use the page’s existing local names for the selected tournament, game label and player; if the page uses different names, pass those exact existing values to the same keyword arguments.

**Definition of done:**
- [ ] `tests/test_league_scorecard_ui.py`, test `test_render_shows_thumbnail_and_github_link`: create a real JPEG under `tmp_path` named `league_2026个人联赛_Game_5_Alice_20260101000000.jpg`; monkeypatch `league_scorecard_ui.st.image` to append `(args, kwargs)`, `league_scorecard_ui.st.button` to return `False`, and `league_scorecard_ui.st.link_button` to record calls; call `render_saved_league_scorecard(tournament="2026个人联赛", game="Game 5", player="Alice", scorecard_images_dir=tmp_path, github_repo="owner/repo")`; assert one image call whose first arg is `bytes` starting `b"\xff\xd8\xff"` and whose `kwargs["link"]` equals the expected GitHub blob URL; monkeypatch restores automatically.
- [ ] `tests/test_league_scorecard_ui.py`, test `test_render_without_github_repo_shows_view_without_link`: same fixture with `github_repo=None`; assert the image kwargs contain no `"link"`, `st.button` was called with `"View"`, and no `st.link_button` call occurred.
- [ ] `tests/test_league_scorecard_ui.py`, test `test_render_incomplete_or_no_match_does_nothing`: call with blank player and with a real empty `tmp_path`; assert `st.image`, `st.button` and `st.link_button` were never called.
- [ ] `tests/test_league_scorecard_ui.py`, test `test_view_dialog_uses_upright_view_jpeg`: monkeypatch `league_scorecard_ui.st.button` to return `True`; monkeypatch `league_scorecard_ui.st.dialog` to a factory returning a decorator that immediately calls the wrapped function; monkeypatch `league_scorecard_ui.st.image` to record calls; create a 2000x1000 JPEG; call renderer; assert two image calls, the thumbnail decoded max dimension `320` and the dialog image decoded max dimension `1600`, both JPEG bytes, and no `str` argument starts with `"data:"`.
- [ ] `tests/test_league_scorecard_ui.py`, test `test_render_updates_on_selection_change_and_removes_when_no_match`: monkeypatch `league_scorecard_ui.find_league_scorecard_image` with side effects `[match_a, match_b, None]`, `league_scorecard_ui.cached_scorecard_thumbnail_jpeg` with side effects `[b"\xff\xd8A", b"\xff\xd8B", None]`, `league_scorecard_ui.cached_scorecard_view_jpeg` with side effects `[b"\xff\xd8viewA", b"\xff\xd8viewB", None]`, and `league_scorecard_ui.st.button` to return `False`; call renderer three times; assert image calls used `b"\xff\xd8A"` then `b"\xff\xd8B"` and no third image call; no background resources to clean up.
- [ ] `tests/test_league_scorecard_page_wiring.py`, test `test_league_page_imports_and_calls_render_saved_scorecard`: read `Path("pages/3_🏆_League.py").read_text(encoding="utf-8")`; assert `"from league_scorecard_ui import render_saved_league_scorecard"` appears, `"render_saved_league_scorecard("` appears, `"github_repo=os.environ.get(\"GITHUB_REPO\")"` appears, and `"scorecard_images_dir=SCORECARD_IMAGES_DIR"` appears.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_ui.py tests/test_league_scorecard_page_wiring.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- Streamlit may not accept `link=` on `st.image` in the installed version. Phase 3 catches `TypeError` and falls back to `st.image` plus `st.link_button("Open original on GitHub", ...)`; the primary linked-thumbnail path is asserted by `test_render_shows_thumbnail_and_github_link`.
- Unicode tournament/player names can break GitHub URLs if not quoted. Phase 1 `test_scorecard_github_url_builds_quoted_blob_url` catches this.
- Filename matching can accidentally pick a stale or wrong file. Phase 1 `test_find_league_scorecard_image_picks_newest_timestamp` and the other-player/other-game cases catch this.
- Cache keys can fail to invalidate when a file changes. Phase 2 `test_cached_scorecard_thumbnail_jpeg_invalidates_on_file_change` catches this.
- EXIF orientation can be lost or applied twice. Phase 2 `test_cached_scorecard_thumbnail_jpeg_applies_exif_orientation` and Phase 3 `test_view_dialog_uses_upright_view_jpeg` catch this.
- The page can call the renderer with incomplete names or not call it at all. Phase 3 `test_render_incomplete_or_no_match_does_nothing` and `test_league_page_imports_and_calls_render_saved_scorecard` catch this.
- Existing scorecard behaviour could regress. Phase 1/2 frozen tests and the final full suite catch this.

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

