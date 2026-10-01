<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@fb95948 -->
# Intent: Download the League AI summary and follow-up Q&A

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
League page visitors can read the AI season summary and ask follow-up questions, but everything lives only in the browser session. Anyone who wants to keep, share, or review that conversation with players or organisers has to copy it out by hand, and any reload loses it. The AI summary and the secondary buttons that drive it also don't match the rest of the app's green styling, so the flow looks unfinished next to the League page's other controls.

## Outcome
Under the follow-up Q&A on the League page, inside the same fragment that renders the Q&A, there is a 下载 / Download button that saves the AI season summary together with every follow-up question and its answer as a single `.txt` file the user can keep or share. The follow-up form's submit button and this new download button render in the app's green button style, consistent with other primary actions. This most likely belongs in `pages/3_🏆_League.py` and the shared button styling in `theme.py`, with any summary/Q&A text assembly living alongside `ai_summary.py`.

## Done when
- A 下载 / Download control is visible directly under the follow-up Q&A in the League page, within the same fragment, and is discoverable without scrolling past unrelated sections.
- Clicking it produces a file download whose name ends in `.txt` and whose contents include the AI season summary text.
- The downloaded file contains every follow-up question that was asked, each paired with its answer, in the order asked, and contains no duplicated or empty Q&A entries.
- The file is legible as plain text — no HTML tags, markdown fences, or other rendering artefacts from the on-screen display.
- The follow-up form submit button and the download button render in the theme's green button style and are visually consistent with the app's other primary buttons; other pages are unaffected.
- The existing tests still pass.

## Not in scope
- Any change to the AI summary prompt, language options, or the follow-up Q&A behaviour itself.
- Additional export formats (PDF, CSV, DOCX) or emailing/sharing the file.
- Server-side storage, persistence of the summary or Q&A across sessions, or any new data files written by the app.
- Restyling buttons app-wide beyond making these two match the theme, and any redesign of the League page layout.
- Changing the on-screen presentation of the summary or the Q&A transcript.

## Open questions
- **File name**: the idea doesn't specify one. Assumption: derive it from the league/season context plus a timestamp, and keep it stable enough that users can tell which summary they downloaded.
- **Label language**: the idea writes "下载/Download". Assumption: show both languages on the button, consistent with the app's existing bilingual labels.
- **Nothing to download yet**: it's unclear whether the button should appear before any follow-up question has been asked. Assumption: show it whenever the summary exists, even with zero follow-ups, so the summary alone can be saved.
- **Green style scope**: the idea names only the form submit and download buttons, but `theme.py` currently styles Streamlit's standard buttons only. Assumption: the theme's green treatment is extended to cover submit and download button types wherever they appear, since that is a shared theme helper rather than a page-local override.
- **Transcript completeness**: it's unclear whether unanswered or in-flight questions count. Assumption: include only questions that have an answer, so the file never contains a dangling question.
