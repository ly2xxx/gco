<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@ff88398 -->
## Summary
The league admin score form will show the saved scorecard image for the selected tournament, game and player when a matching file exists in `scorecard_images/`. The thumbnail is the saved file shown at 160 pixels wide, can link to the raw GitHub URL when `GITHUB_REPO` is set, and can be opened as-is in a View dialog. Incomplete selections and missing matches render nothing and do not error.

## Behaviour
1. Given a selected tournament, a selected `Game <N>` label and a selected player with exactly one matching saved file, when the league admin score form renders, then the form renders that saved file as a thumbnail at 160 pixels wide.
2. Given multiple saved files match the selected tournament, game number and player, when the form renders, then the thumbnail is the matching file whose filename timestamp segment is greatest.
3. Given the selected game label is `"Game 5"`, when saved scorecard lookup runs, then it matches filenames containing `_Game_5_`.
4. Given the selected game label is `"Game 5"`, when saved scorecard lookup runs, then it does not match filenames containing `_Game_1_` or `_Game_15_`.
5. Given the selected game label cannot be parsed as `Game <number>`, when saved scorecard lookup runs, then the lookup returns no saved scorecard and raises no exception.
6. Given any one of tournament, game label or player is missing or empty, when the form renders, then no scorecard thumbnail is rendered.
7. Given any one of tournament, game label or player is missing or empty, when the form renders, then no View button is rendered.
8. Given any one of tournament, game label or player is missing or empty, when the form renders, then no Streamlit error is rendered.
9. Given no saved file matches the selected tournament, game number and player, when the form renders, then no scorecard thumbnail is rendered.
10. Given no saved file matches, when the form renders, then no View button is rendered.
11. Given no saved file matches, when the form renders, then no Streamlit error is rendered.
12. Given the `scorecard_images/` directory is absent, when saved scorecard lookup runs, then the lookup returns no saved scorecard and raises no exception.
13. Given a matching saved file has a Streamlit-displayable non-JPEG extension such as `.png`, `.jpeg`, `.webp` or `.gif`, when the form renders, then the thumbnail uses that saved file path with no conversion.
14. Given a matching saved image contains EXIF orientation metadata, when the form renders the thumbnail, then the image source is the original saved file path and no rotated, transformed or cached image path is used.
15. Given a matching saved image contains EXIF orientation metadata, when the View dialog renders the image, then the image source is the same original saved file path and no rotated, transformed or cached image path is used.
16. Given a matching saved image is displayed, when the thumbnail renders, then no image source passed to Streamlit begins with `data:`.
17. Given a matching saved image is displayed, when the View dialog renders the image, then no image source passed to Streamlit begins with `data:`.
18. Given a matching saved image is displayed, when the same selection is rendered again, then the thumbnail still uses the saved file path from `scorecard_images/<file>` rather than a cached thumbnail path.
19. Given `GITHUB_REPO` is set to `owner/repo` and the matching filename is `foo.jpg`, when the GitHub URL helper is called, then it returns `https://raw.githubusercontent.com/owner/repo/HEAD/scorecard_images/foo.jpg`.
20. Given `GITHUB_REPO` is unset or blank, when the GitHub URL helper is called, then it returns no URL.
21. Given `GITHUB_REPO` is set and a match exists, when the thumbnail renders, then the thumbnail is a link to the raw GitHub URL and the link target is `_blank`.
22. Given `GITHUB_REPO` is unset and a match exists, when the thumbnail renders, then no external link is rendered around the thumbnail.
23. Given a match exists, when the View button is activated, then the dialog renders the same saved file path as the thumbnail as-is.
24. Given a match is displayed, when the selected tournament, game or player changes to a different match, then the thumbnail and View dialog image use the newly matched saved file path.
25. Given a match is displayed, when the selection changes to one with no match, then no scorecard thumbnail and no View button are rendered.
26. Given the existing test suite, when the full suite runs, then all existing tests pass.

## Interfaces

**`league_scorecard.py`**

```python
SCORECARD_IMAGES_DIR: str = "scorecard_images"
SCORECARD_THUMBNAIL_WIDTH: int = 160
SCORECARD_IMAGE_SUFFIXES: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp", ".gif")


@dataclass(frozen=True)
class SavedScorecard:
    filename: str
    path: str
    timestamp: str


def game_number_from_label(game_label: object) -> int | None: ...


def find_saved_scorecard(
    tournament: object,
    game_label: object,
    player: object,
    *,
    directory: str = SCORECARD_IMAGES_DIR,
) -> SavedScorecard | None: ...


def scorecard_image_url(repo: str | None, filename: str) -> str | None: ...


def scorecard_github_repo() -> str | None: ...
```

`scorecard_github_repo` reads `GITHUB_REPO` using the module’s existing configured-value behaviour, treating blank as unset.

**`pages/3_🏆_League.py`**

```python
def render_league_scorecard_preview(
    tournament: object,
    game_label: object,
    player: object,
) -> None: ...


def show_saved_scorecard_dialog(scorecard: SavedScorecard) -> None: ...
```

## Out of scope
- Uploading, replacing, deleting or rotating stored scorecard image files.
- Applying EXIF orientation, rotating, converting or resizing scorecard images for display.
- Pillow-based image processing, generated thumbnails or caching of scorecard images.
- Reading scores from the image or auto-filling the score form.
- Cup, outing or other non-league scorecards.
- Showing saved scorecards anywhere other than the league admin score form.
- Changing how scorecards are named or stored.
- `data:` URL image embedding or any fallback that puts image bytes directly into the page.
- Changing the GitHub repository layout or adding another image host.
- Fetching or validating the raw GitHub URL server-side.

## Open questions
- Displayable saved files are assumed to be `.jpg`, `.jpeg`, `.png`, `.webp` and `.gif`; other extensions are ignored.
- Tournament and player matching is assumed to be exact and case-sensitive, with no name normalisation.
- `Game 5` parsing is assumed to accept `Game` followed by whitespace and digits, case-insensitively; other label forms do not match.
- When multiple matching files share the same filename timestamp, an arbitrary but stable choice is assumed; no additional tie-break rule is required.
- The View dialog is assumed to show the saved file as-is without the 160-pixel thumbnail width constraint.
- When `GITHUB_REPO` is unset, the thumbnail is assumed to have no separate enlarge action; the View dialog is the in-app enlargement.
- `scorecard_images/` is assumed to be resolved relative to the application/repository working directory.
- The raw GitHub URL is assumed to use the `https://` scheme and to insert the filename into the path without application-level URL encoding.
