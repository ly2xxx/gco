<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@7fa15e7 -->
## Summary
The 下载/Download button for the League AI summary moves from below the follow-up Q&A to between the summary text and the follow-up Q&A area, so the summary fragment reads as one downloadable unit. The button keeps its bilingual label, its contents (summary plus every answered follow-up) and its filename/mime, and it still includes a follow-up answered in the current run.

## Behaviour
1. Given the League page's AI summary fragment with a non-empty summary and zero stored follow-up turns, when the fragment renders, then exactly one download button is rendered and it appears in the rendered output after the summary content and before the follow-up form.
2. Given a non-empty summary and one or more stored follow-up turns, when the fragment renders, then the download button appears after the summary content and before the first rendered follow-up question and before the follow-up form.
3. Given a non-empty summary, when the fragment renders with zero turns and again with one or more turns, then the button's label is exactly `DOWNLOAD_BUTTON_LABEL` (`⬇️ 下载 / Download`) and its widget key is `DOWNLOAD_BUTTON_KEY` in both cases.
4. Given a non-empty summary and stored history `H`, when the fragment renders, then the data given to the download button equals `build_transcript_text(player_name, summary, H)` — summary heading, sanitized summary, Q&A heading, then every stored turn with a non-empty question and answer, in stored order, deduplicated as before.
5. Given a non-empty summary and no stored turns, when the fragment renders, then the data given to the download button still contains the summary heading, the sanitized summary and the Q&A heading, so the summary alone is downloadable.
6. Given the follow-up form is submitted with a non-empty question and answer generation returns an answer, when the fragment renders, then the data given to the download button in that same render run contains that question and that answer together with the summary and every previously stored turn, and the turn is stored exactly once.
7. Given the form is submitted with an empty or whitespace-only question, when the fragment renders, then `EMPTY_QUESTION_MESSAGE` is displayed, no turn is stored, and the download button is still rendered with the same data as before the submission.
8. Given answer generation raises `AISummaryError`, when the fragment renders, then the error text is displayed, no turn is stored, and the download button is still rendered with the same data as before the submission.
9. Given the summary is empty, `None`, or whitespace-only, when the fragment renders, then no download button, no follow-up turn and no follow-up form are rendered.
10. Given a non-empty summary, when the fragment renders, then the button's `file_name` is the value of `build_transcript_filename(player_name, <current time>)` (prefix `gco_league_ai_summary`, `.txt` extension) and its `mime` is `TRANSCRIPT_MIME_TYPE` (`text/plain`), unchanged from before the move.
11. Given the pre-existing automated test suite, when it is run against the changed code, then every test that passed before passes unchanged.
12. Given the Cup, Outing, API Data and Announcements pages, when they render, then their download controls, labels and layout are identical to before this change (their existing tests pass unmodified).

## Interfaces

### `ai_summary.py`

Changed (signature and decorator unchanged; only the rendered order inside the fragment changes):

```python
@st.fragment
def render_follow_up_questions(
    player_name: str,
    season_rounds: list[dict],
    summary: str,
) -> None:
    """Render the download button, the stored Q&A turns and the question form, in that
    order, for the given summary. Returns None."""
```

- Rendered order inside the fragment becomes: download button → stored Q&A turns → follow-up form.
- The button keeps `label=DOWNLOAD_BUTTON_LABEL`, `key=DOWNLOAD_BUTTON_KEY`, `mime=TRANSCRIPT_MIME_TYPE`, `file_name=build_transcript_filename(player_name, datetime.now())`, and `data=build_transcript_text(player_name, summary, history)`, where `history` is read with `get_follow_up_history(summary)` after any turn appended in the same run.
- Placement mechanism (design note, so visible order and data freshness can both hold): the button's visible position is reserved with an empty placeholder created before the Q&A output and filled once the run's submitted question (if any) has been answered and stored. The visible position is the reserved one; the write happens last.
- No new public names. `build_transcript_text`, `build_transcript_filename`, `get_follow_up_history`, `append_follow_up_turn`, `answer_follow_up_question` and all `DOWNLOAD_*` / `TRANSCRIPT_*` constants keep their current signatures and values.

### `pages/3_🏆_League.py`

No new or changed signatures. The existing call `render_follow_up_questions(player_name, season_rounds, summary)` must remain after the summary content is rendered (the `render_season_summary(...)` result) and before any other League AI output, so the reserved button position falls between the summary and the Q&A area.

## Out of scope
- Any change to how the AI summary or follow-up answers are generated, prompted, or worded.
- Any change to the `.txt` file format, filename, mime type, key, label or contents beyond ensuring nothing is lost by the move.
- Moving or restyling download controls anywhere other than the League AI summary fragment (Cup, Outing, API Data export).
- New download formats (PDF, Markdown, copy-to-clipboard) or additional buttons.
- Streamlit-wide layout, fragment-boundary or theming changes.

## Open questions
- Does the button render when there is no summary at all? Assumption: unchanged — the fragment still returns early when the summary is empty/`None`/whitespace, so no button, no turns and no form render, since there is no transcript to download.
- Where exactly does the button sit when the Q&A area has no turns? Assumption: it still renders in the same slot between the summary and the (possibly empty) Q&A area, so it neither appears nor disappears as turns are added.
- Should the button live outside the follow-up fragment (for example in the page body) so it is not re-rendered by follow-up interactions? Assumption: it stays inside the existing fragment, which is the only place its data can reflect a turn answered in the same run without a full page rerun.
- Does the button need to keep its current widget key and label so pre-existing wiring tests still identify it? Assumption: yes — `DOWNLOAD_BUTTON_KEY` and `DOWNLOAD_BUTTON_LABEL` are reused exactly.
