<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@5047b80 -->
## Summary
Adds a bilingual 下载 / Download control to the League page's follow-up Q&A fragment, inside `ai_summary.py`, that saves the AI season summary plus every answered follow-up question and its answer as one plain-text `.txt` download. It also extends the shared button styling in `theme.py` so the follow-up form's submit button and the new download button use the app's green primary-button treatment. Nothing about the AI prompts, the Q&A behaviour, or the on-screen transcript changes.

## Behaviour

1. Given a non-empty season summary, when `render_follow_up_questions(player_name, season_rounds, summary)` renders, then it renders exactly one download control labelled `下载 / Download`, inside the same fragment, positioned after the follow-up question form and after every rendered Q&A turn.
2. Given `summary` is empty or whitespace-only, when `render_follow_up_questions` renders, then it creates no download control, no question form and no Q&A turns, and writes nothing to session state.
3. Given a non-empty summary and zero stored follow-up turns, when the fragment renders, then the download control is still created and its content contains the summary text.
4. Given the fragment renders the download control, when it is created, then its MIME type is `text/plain`, its file name ends with `.txt`, and its data is exactly the string returned by `build_transcript_text(player_name, summary, history)` for the history read at that point in the render.
5. Given a stored turn with a non-empty question and a non-empty answer, when `build_transcript_text` builds the transcript, then that question appears before its answer, the question line is prefixed `问 / Q:` and the answer line is prefixed `答 / A:`.
6. Given several stored turns, when `build_transcript_text` builds the transcript, then the answered turns appear in stored (asked) order and each question appears exactly once.
7. Given a turn whose question is missing, empty or whitespace-only, or whose answer is missing, empty or whitespace-only, when `build_transcript_text` builds the transcript, then that turn contributes no text.
8. Given the stored history contains two turns with identical question text and identical answer text, when `build_transcript_text` builds the transcript, then that question/answer pair appears exactly once.
9. Given `history` is `None`, is not a list, or is a list containing non-dict entries, when `build_transcript_text` is called, then it returns the summary-only transcript and does not raise.
10. Given `summary`, a question or an answer contains HTML tags (for example `<b>`, `<br/>`) or markdown code fences (```), when `build_transcript_text` builds the transcript, then the returned text contains no HTML tag and no fence marker.
11. Given a player name and a fixed `datetime`, when `build_transcript_filename` is called, then the result starts with the league prefix constant, contains the sanitized player name, contains the timestamp formatted `YYYYMMDD_HHMMSS`, ends with `.txt`, and contains none of `/ \ : * ? " < > |`.
12. Given the same player name and timestamp, when `build_transcript_filename` is called twice, then both calls return identical strings.
13. Given a player name that is empty or consists only of characters that must be sanitized away, when `build_transcript_filename` is called, then it still returns a name ending in `.txt` whose stem is non-empty.
14. Given a question is submitted and answered during the current run, when the fragment finishes rendering, then the download control's data includes that new question and its answer.
15. Given the user activates the download control, when the fragment reruns, then no AI request is issued (neither `summarize_season` nor `answer_follow_up_question` is called) and the rendered summary and Q&A turns are unchanged.
16. Given `theme.py`'s `THEME_CSS` is injected into a page, when a follow-up form submit button is rendered, then a CSS rule applying the same green gradient background, white text and border-radius as `.stButton > button` targets that submit button element.
17. Given `theme.py`'s `THEME_CSS` is injected into a page, when a download button is rendered, then a CSS rule applying the same green gradient background, white text and border-radius as `.stButton > button` targets that download button element.
18. Given the theme change, when `THEME_CSS` is inspected, then the `.stButton > button` declarations and every non-button rule are unchanged from before the change.
19. Given the existing test suite, when it is run after the change, then every test that passed before still passes.

## Interfaces

### `ai_summary.py`

New module-level constants:

```python
DOWNLOAD_BUTTON_LABEL: str = "⬇️ 下载 / Download"
DOWNLOAD_BUTTON_KEY: str = "ai_season_summary_download"
TRANSCRIPT_MIME_TYPE: str = "text/plain"
TRANSCRIPT_FILE_EXTENSION: str = ".txt"
TRANSCRIPT_FILENAME_PREFIX: str = "gco_league_ai_summary"
TRANSCRIPT_SUMMARY_HEADING: str = "AI 赛季总结 / AI Season Summary"
TRANSCRIPT_QA_HEADING: str = "追问与回答 / Follow-up Q&A"
```

New functions:

```python
def build_transcript_text(
    player_name: str,
    summary: str,
    history: list[dict] | None,
) -> str:
    """Return the plain-text transcript: the summary heading followed by the summary,
    then the Q&A heading followed by each answered, de-duplicated turn in order, with
    HTML tags and markdown code-fence markers removed. Never raises."""


def build_transcript_filename(player_name: str, timestamp: datetime) -> str:
    """Return '<TRANSCRIPT_FILENAME_PREFIX>_<sanitized player name>_<YYYYMMDD_HHMMSS>.txt';
    a non-empty stem is always produced. Never raises."""
```

(`datetime` here is `datetime.datetime`; add the import to the module.)

Changed function (same name, parameters and return type, additional rendered output):

```python
@st.fragment
def render_follow_up_questions(
    player_name: str,
    season_rounds: list[dict],
    summary: str,
) -> None:
    """Render the stored Q&A turns, the question input and submit button, then a
    st.download_button built from build_transcript_text/build_transcript_filename for the
    current history. Returns None as before."""
```

### `theme.py`

No new names. `THEME_CSS` keeps its type (`str`) and its existing rules; the button rule and its `:hover` rule have their selector lists extended from `.stButton > button` to also cover the form-submit button element and the download button element rendered by Streamlit, so both receive the existing green gradient background, white text, border-radius and hover treatment.

## Out of scope
- Any change to the AI summary prompt, language options, or the follow-up Q&A behaviour itself.
- Additional export formats (PDF, CSV, DOCX) or emailing/sharing the file.
- Server-side storage, persistence of the summary or Q&A across sessions, or any new data files written by the app.
- Restyling buttons app-wide beyond making submit and download buttons match the theme, and any redesign of the League page layout.
- Changing the on-screen presentation of the summary or the Q&A transcript.

## Open questions
- **File name**: the intent names no scheme. Assumption: `gco_league_ai_summary_<sanitized player name>_<YYYYMMDD_HHMMSS>.txt`, stable for fixed inputs and identifiable by player and time.
- **Label language**: assumption: the button shows both languages as `⬇️ 下载 / Download`, matching the app's existing bilingual labels.
- **Nothing to download yet**: assumption: the control is shown whenever the summary exists, including with zero follow-ups; it is absent only when the summary is empty.
- **Duplicate turns**: the intent forbids duplicated entries but does not define duplication. Assumption: two turns with identical question *and* identical answer text collapse to one entry; same question with a different answer is kept.
- **Unanswered questions**: assumption: only turns with a non-empty answer are written, so the file never ends on a dangling question.
- **Green style scope**: assumption (from the intent): the theme's green treatment is extended to submit and download button types everywhere, since `theme.py` is a shared helper; the change is limited to the button selector lists so no other page styling moves.
- **Download placement inside the fragment**: assumption: the control sits after the form (bottom of the fragment), which is what "under the follow-up Q&A" describes; it re-reads the stored history at render time so a just-answered question is included without an extra reload.
