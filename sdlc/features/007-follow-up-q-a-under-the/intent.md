<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@45c02bd -->
# Intent: Follow-up Q&A under the AI season summary

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
League page readers get an AI season summary, but it is a dead end: once they read it there is no way to ask about the details behind it, such as why a player moved up, or what happened in a specific round. Today the only way to answer those questions is to go back to the raw rounds table and work it out by hand, which most readers won't bother to do. As a result the summary is consumed once and its insight is not extended to the questions it naturally provokes.

## Outcome
Below the AI season summary on the League page there is a follow-up question box the reader can type into and get an answer from Ollama. The summary becomes a handle rather than a final product: `render_season_summary` returns the summary text so it can be handed to a new `@st.fragment` `ai_summary.render_follow_up_questions`, which the League page calls underneath the summary. Answers are grounded in the season's rounds data, the summary itself, and the earlier questions and answers, so the conversation builds instead of restarting; that Q&A history lives in `st.session_state` and survives Streamlit reruns within the session. Existing summary behaviour on the League page is unchanged for readers who never ask anything.

## Done when
- `render_season_summary` returns the summary text, and the League page passes that value to `ai_summary.render_follow_up_questions`.
- A question box appears under the season summary on the League page.
- Asking a question produces an Ollama-generated answer grounded in the rounds data, the summary, and prior Q&A.
- Earlier questions and answers remain visible and are included as context in later answers, surviving reruns within the session.
- If Ollama is unavailable or the question is empty, the page degrades gracefully with a visible message instead of erroring.
- The existing tests still pass.

## Not in scope
- Changing the season summary prompt, its content, or the language-selection behaviour shipped previously.
- Follow-up Q&A on any page or feature other than the League page season summary (Cup, Outing, player deep dive, announcements).
- Persisting Q&A history beyond the browser session or sharing it between users.
- Streaming responses, citations, feedback controls, or exporting the conversation.

## Open questions
- Where exactly `render_follow_up_questions` should live: assumed a new function in `ai_summary.py`, alongside the existing summary rendering, since the idea names that module.
- What `st.session_state` keys hold the history, and whether the history is keyed per season: assumed a single season-scoped key so a rebuilt summary does not mix conversations from different seasons.
- Whether the conversation is cleared when the summary is regenerated for a new season: assumed it is cleared, so answers never reference a stale summary.
- How much history is fed back to Ollama as context: assumed the recent turns are used and older ones are dropped, so the prompt stays within a workable size.
- Which language the answers come back in: assumed answers follow the same language as the summary the reader is looking at, consistent with the existing summary behaviour.
- What happens when rounds data is unavailable in the session: assumed the answer is still attempted from the summary plus Q&A, with a note that data is missing.
