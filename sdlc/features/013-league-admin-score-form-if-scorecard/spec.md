<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@a1cadb0 -->
## Summary
The league admin score form now looks up the scorecard image saved for the currently selected tournament, game number and player, and shows a clickable thumbnail when a match exists. Matching stays in `league_scorecard.py` and the league admin score form in `pages/3_🏆_League.py` is the only page changed.

## Behaviour
1. Given a selected tournament, game number and player for which exactly one file in `scorecard_images/` matches `league_<tournament>_Game_<game>_<player>_<14-digit timestamp>.<ext>`, when the league admin score form renders, then it shows a thumbnail of that file.
2. Given more than one file matches the selected tournament, game number and player, when the form resolves the scorecard image, then it uses the matching file whose filename timestamp segment is greatest.
3. Given matching files have filenames whose timestamps disagree with filesystem modification times, when the form resolves the scorecard image, then the filename timestamp decides which file is shown.
4. Given a thumbnail is shown, when the admin activates the thumbnail, then the full-size image for that same file is opened.
5. Given a thumbnail is shown for one selection, when the selected tournament changes to another value with a matching file, then the form shows the thumbnail for the new tournament.
6. Given a thumbnail is shown for one selection, when the selected game number changes to another value with a matching file, then the form shows the thumbnail for the new game number.
7. Given a thumbnail is shown for one selection, when the selected player changes to another value with a matching file, then the form shows the thumbnail for the new player.
8. Given a thumbnail is shown, when any of the selected tournament, game number or player changes to a combination with no matching file, then the form shows no thumbnail and shows no error.
9. Given any of the selected tournament, game number or player is missing or empty, when the form renders, then no thumbnail is shown and no error is shown.
10. Given no file matches the selected tournament, game number and player, when the form renders, then no thumbnail is shown and no error is shown.
11. Given the scorecard images directory is empty or does not exist, when the form renders with three selected values, then no thumbnail is shown and no error is shown.
12. Given a matching file has a non-empty extension other than `.jpg`, when its tournament, game number and player match, then it is treated as a matching scorecard.
13. Given a file in `scorecard_images/` does not have the exact selected tournament, exact `Game_<game>` segment, exact selected player, and a 14-digit timestamp before its extension, when the form resolves the scorecard image, then that file is ignored.
14. Given two matching files share the greatest timestamp, when the form resolves the scorecard image repeatedly, then it returns the same one of those files each time and does not error.
15. Given the existing test suite, when it runs, then it still passes.

## Interfaces
In `league_scorecard.py`:

```python
SCORECARD_IMAGES_DIR: str = os.path.join(os.path.dirname(__file__), "scorecard_images")

def find_league_scorecard_image(
    tournament: str | None,
    game_number: int | str | None,
    player: str | None,
    *,
    images_dir: str | os.PathLike[str] = SCORECARD_IMAGES_DIR,
) -> str | None:
    ...
```

`find_league_scorecard_image` returns the joined path to the newest matching image, or `None` when any input is missing, no file matches, or the directory cannot be read. It reads directory entries only; it does not read image bytes, write files, resize images or make network calls.

In `pages/3_🏆_League.py`:

```python
def render_league_scorecard_thumbnail(image_path: str | None) -> None:
    ...
```

`render_league_scorecard_thumbnail` shows nothing when `image_path` is `None`. When a path is supplied, it shows a clickable thumbnail that opens the same full-size image path. The league admin score form calls `find_league_scorecard_image` with the selected tournament, selected game number and selected player after those values are known, then passes the result to `render_league_scorecard_thumbnail`.

## Out of scope
- Uploading, replacing, deleting or rotating scorecard images.
- Reading scores from the image or auto-filling the form from the image.
- Cup, outing or other non-league scorecards.
- Showing scorecards anywhere other than the league admin score form.
- Image conversion, resizing on disk, thumbnail generation or caching.
- Any change to how scorecard images are named or stored.
- Any network, secret or manual-step dependency for the automated tests.

## Open questions
- Filename matching for tournament and player is assumed to be exact and case-sensitive, because the intent specifies a filename pattern rather than a fuzzy match.
- Game numbers are assumed to be matched as the decimal number in `Game_<game>` with no extra leading-zero handling; the page passes the selected numeric game value.
- “Any extension” is assumed to mean any non-empty extension segment after the 14-digit timestamp; formats that Streamlit itself cannot display are not converted by this change.
- A tie on the greatest timestamp is assumed to be resolved by a deterministic filename ordering, because the intent only requires a stable arbitrary choice.
