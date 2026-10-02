<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@d8bc04e -->
# Intent: Move the League AI summary download button above the follow-up Q&A

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
On the League page, the League AI summary's 下载/Download button currently sits below the follow-up Q&A, so a reader who answers a follow-up question and immediately downloads gets a file that may not contain the answer they just received. The gap between "ask a follow-up" and "get the file with the answer in it" makes the downloadable transcript feel stale and unreliable, and makes the user scroll past the Q&A to reach the control they want.

## Outcome
The 下载/Download button for the League AI summary appears between the summary text and the follow-up Q&A area, so it reads as the download for the whole fragment and is reachable without scrolling past the Q&A. The downloaded `.txt` still contains the summary plus every answered follow-up question and answer, including a follow-up answered during the current run — the button's new position does not cost the file any content. This belongs to the League page's AI summary/follow-up fragment (`pages/3_🏆_League.py`, with summary and follow-up logic in `ai_summary.py`).

## Done when
- On the League page, the League AI summary's 下载/Download button renders between the summary content and the follow-up Q&A section.
- Downloading immediately after submitting a new follow-up question yields a `.txt` that contains that just-answered question and its answer, alongside the summary and all previously answered follow-ups.
- The downloaded `.txt` still contains the summary and every previously answered follow-up — nothing present before the move is missing after it.
- The button remains visible and correctly labelled (bilingual 下载/Download) whether or not any follow-up has been answered yet.
- No other page or section's layout or download behaviour changes.
- The existing tests still pass.

## Not in scope
- Any change to how the AI summary or follow-up answers are generated, prompted, or worded.
- Any change to the `.txt` file format, filename, or contents beyond ensuring nothing is lost by the move.
- Moving or restyling download controls anywhere other than the League AI summary fragment (e.g. Cup, Outing, API data export).
- Adding new download formats (PDF, Markdown, copy-to-clipboard) or additional buttons.
- Streamlit-wide layout or theming changes.

## Open questions
- Existing intent for feature 008 is revised rather than replaced: the goal of offering a 下载/Download for the League AI summary is kept, and the change applied is the button's position — moved up to sit between the summary and the follow-up Q&A. Everything else the idea does not touch is retained.
- Where exactly does the button sit when the Q&A area is empty? Assumption: it still renders in the same position between the summary and the (possibly empty) Q&A area, so the control does not appear or disappear as follow-ups are added.
- Does the button need to stay live after a new follow-up is answered in the same run? Assumption: yes — the download reflects the state at the moment it is clicked, so a just-answered follow-up is included.
- Should the summary itself be downloadable before any follow-up exists? Assumption: yes, unchanged from current behaviour — the summary alone is a valid download.
- The idea mentions implementation mechanics (an `st.empty` placeholder filled after the form); those are recorded as the product owner's suggestion only and are not treated as a requirement.
