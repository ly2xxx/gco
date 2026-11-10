<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@b3dec5d -->
## Summary
The league admin score form will show the newest saved scorecard thumbnail for the selected tournament, game and player, with an optional GitHub link and a View dialog. When the selection is incomplete, no matching file exists, or the image cannot be read, the form keeps its current behaviour without showing an image or raising an error.

## Behaviour
1. Given a tournament, game and player are all non-empty and at least one file in `scorecard_images/` matches `league_<tournament>_Game_<N>_<player>_<timestamp>.<ext>`, when the league admin score form renders that selection, then a scorecard thumbnail is displayed.
2. Given more than one file matches the same tournament, game and player, when the form renders, then the displayed thumbnail is from the matching file with the greatest numeric timestamp segment in its filename.
3. Given the selected game label is `Game 5`, when saved scorecards are matched, then filenames containing `Game_5` are treated as game number 5.
4. Given any of tournament, game or player is missing, blank, or has no positive game number, when the form renders, then no thumbnail, no GitHub link and no View button are shown and no error is raised.
5. Given no file matches the selection, when the form renders, then no thumbnail, no GitHub link and no View button are shown and no error is raised.
6. Given `scorecard_images/` is missing or cannot be listed, when the form renders, then no thumbnail, no GitHub link and no View button are shown and no error is raised.
7. Given a matching saved file is a non-JPEG image such as `.png`, when its thumbnail is generated, then the returned thumbnail bytes are JPEG.
8. Given a matching saved file has EXIF orientation metadata, when its thumbnail or View image is generated, then the returned JPEG is upright with the orientation applied.
9. Given a matching saved file is converted into a thumbnail or View image, when the operation completes, then the stored file’s bytes are unchanged.
10. Given a matching saved file is corrupt or not a readable image, when the form renders, then no thumbnail, no GitHub link and no View button are shown and no error is raised.
11. Given the same matched file, unchanged modification time, unchanged size and the same thumbnail parameters, when the thumbnail is requested twice, then identical JPEG bytes are returned and the file is decoded at most once.
12. Given the matched file changes on disk or the selection changes to a different matched file, when the thumbnail is requested, then the cached old thumbnail is not returned.
13. Given `GITHUB_REPO` is set and a match exists, when the thumbnail is rendered, then the thumbnail is wrapped in an anchor whose `href` is the GitHub URL for the original file in `scorecard_images/` and whose target opens a new tab.
14. Given `GITHUB_REPO` is not set and a match exists, when the form renders, then the thumbnail has no GitHub anchor and the View button is still available.
15. Given a match is displayed, when the user activates View, then a dialog displays an upright, larger JPEG version of the same saved scorecard.
16. Given any scorecard image is displayed, when the page rendering calls are inspected, then the page has not constructed or passed a `data:` URL for that image.
17. Given a match is displayed and the selection changes to another tournament, game or player with a match, when the form rerenders, then the thumbnail and dialog image update to the new match.
18. Given a match is displayed and the selection changes so that nothing matches, when the form rerenders, then the thumbnail, GitHub link and View button are removed.
19. Given the repository’s existing test suite, when it runs after the change, then all pre-existing tests pass.

## Interfaces

`league_scorecard.py`
```python
from pathlib import Path

SCORECARD_IMAGES_DIR: str = "scorecard_images"


@dataclass(frozen=True)
class LeagueScorecardImageMatch:
    path: Path
    timestamp: int


def game_number_from_selection(selection: object) -> int | None: ...


def find_league_scorecard_image(
    tournament: object,
    game: object,
    player: object,
    *,
    directory: str | os.PathLike[str] = SCORECARD_IMAGES_DIR,
) -> LeagueScorecardImageMatch | None: ...


def cached_scorecard_thumbnail_jpeg(
    path: str | os.PathLike[str],
    *,
    max_edge: int = 320,
    quality: int = 85,
) -> bytes | None: ...


def cached_scorecard_view_jpeg(
    path: str | os.PathLike[str],
    *,
    max_edge: int = 1600,
    quality: int = 90,
) -> bytes | None: ...


def scorecard_github_url(
    repo: str | None,
    file_name: str,
    *,
    branch: str = "main",
) -> str | None: ...
```

`pages/3_🏆_League.py`
```python
def render_saved_league_scorecard(
    *,
    tournament: object,
    game: object,
    player: object,
    scorecard_images_dir: str | os.PathLike[str] = SCORECARD_IMAGES_DIR,
    github_repo: str | None = None,
) -> None: ...
```

## Out of scope
- Uploading, replacing, deleting or rotating stored scorecard image files.
- Reading scores from the image or auto-filling the form from it.
- Cup, outing or other non-league scorecards.
- Showing scorecards anywhere other than the league admin score form.
- Image conversion or resizing on disk.
- Changing how scorecards are named or stored.
- `data:` URL image embedding or a fallback that puts image bytes directly into the page.
- Changing the GitHub repository layout or adding another image host.

## Open questions
- Does “selected” require all three of tournament, game and player? Assumed yes: any missing value means nothing is shown.
- When `GITHUB_REPO` is not set, should the thumbnail itself open a larger image? Assumed no: the View dialog is the in-app enlargement.
- Are non-JPEG saved scorecards in scope? Assumed yes; thumbnails and View images are produced as JPEG in memory, and the original file is untouched.
- What is the cache lifetime? Assumed the cache is keyed by path, modification time, size, max edge and quality; eviction details are left to implementation.
- What counts as “newest”? Assumed the timestamp segment in the filename, not file modification time.
- What happens when two files share the same filename timestamp? Assumed a deterministic choice is acceptable; tests avoid depending on which file wins.
- What format does `GITHUB_REPO` use and which branch? Assumed `owner/repo` with branch `main`, producing a GitHub blob URL for the original file.
- What thumbnail and View sizes should be used? Assumed 320 px max edge for thumbnails and 1600 px max edge for the View image.
- Does “not supplied as `data:` URLs” forbid using the framework’s standard image element with JPEG bytes? Assumed the application code must not construct or pass `data:` URLs, while using Streamlit’s image API with JPEG bytes is acceptable.
- What if a matching filename exists but the image cannot be decoded? Assumed the form behaves as if no scorecard matched, with no error.
