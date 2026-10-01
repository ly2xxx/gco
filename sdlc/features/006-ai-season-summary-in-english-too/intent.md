<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@fecc4b5 -->
# Intent: Bilingual (中文 / English) AI Season Summary

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
The GCO dashboard's AI season summary is written only in Chinese, so members who read English more comfortably (e.g. Jacky, Justin, Neo) cannot use it without asking someone to translate. The summary is one of the main ways the club recaps a season, and half the audience is effectively locked out of it. Today there is no way to ask for the recap in another language.

## Outcome
Inside the AI season summary section, a 中文 / English choice sits beside the 🤖 AI 赛季总结 button, pre-selected to 中文. Choosing 中文 produces exactly the Chinese summary members see today; choosing English produces the same season recap written in English. The existing Chinese behaviour is the default and is untouched. This belongs in `ai_summary.py`, in the season summary rendering already used by the dashboard.

## Done when
- A 中文 / English choice appears immediately beside the 🤖 AI 赛季总结 button in the season summary section, with 中文 pre-selected.
- Generating a summary with 中文 selected yields the same Chinese summary behaviour as before this change.
- Generating a summary with English selected yields a season summary written in English.
- Changing the choice and generating again produces the summary in the newly selected language.
- The existing tests still pass.

## Not in scope
- Translating or localising anything outside the AI season summary (announcements, events, league/cup pages, other AI features).
- Making the language choice an app-wide or persisted locale setting.
- Changing the Chinese prompt, the Chinese output, or the Ollama/model configuration.
- Any language beyond 中文 and English.

## Open questions
- Does the choice apply only to the season summary, or to the whole app? Assumption: only the season summary in `ai_summary.render_season_summary`.
- Should the selection survive a page reload or a new session? Assumption: no — it resets to 中文 each time, matching the stated default.
- Must the English summary keep the same sections and figures as the Chinese one, only in English? Assumption: yes, same structure and stats, English wording.
- Is a previously generated summary shown when the language changes, or is a fresh one required? Assumption: the displayed summary always matches the currently selected language.
- Changed from any prior intent: none — no existing `intent.md` for this feature was provided; this is a new intent.
