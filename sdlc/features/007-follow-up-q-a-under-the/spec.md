<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@1978e4a -->
## Summary

Adds a follow-up Q&A box directly under the AI season summary on the League page. `render_season_summary` now returns the summary text it produced, and the League page hands that value to a new session-scoped `@st.fragment`, `ai_summary.render_follow_up_questions`, which answers reader questions through Ollama using the season's rounds data, the summary itself, and the earlier questions and answers as context. Readers who never ask a question see exactly the summary behaviour they see today.

## Behaviour

1. Given AI is configured and the player has at least one season round, when the reader presses the `🤖 AI 赛季总结` button, then `render_season_summary` returns the generated summary text and renders that same text with `st.markdown`.
2. Given no summary is produced — the button was not pressed, `player_name` is empty, `season_rounds` is empty, or `summarize_season` raised `AISummaryError` — when `render_season_summary` returns, then it returns `""` and renders the same selector, button, warning or error message it renders today.
3. Given the League page source, when a season summary is produced, then the value returned by `render_season_summary` is passed to `ai_summary.render_follow_up_questions`, and that call sits below the summary call in the page.
4. Given a non-empty summary was produced, when the League page renders, then a text input labelled `FOLLOW_UP_INPUT_LABEL` with a submit button labelled `FOLLOW_UP_BUTTON_LABEL` appears below the rendered summary markdown.
5. Given `render_season_summary` returned `""`, when the League page renders, then no follow-up text input or submit button appears and no Q&A request is attempted.
6. Given the follow-up form is submitted with a question that is empty or only whitespace, when the fragment reruns, then `EMPTY_QUESTION_MESSAGE` is displayed, `_call_ollama_chat` is not called, and the stored history is unchanged.
7. Given a non-empty question, configured AI and season rounds, when the reader submits the question, then the text returned by `_call_ollama_chat` is displayed as the answer and the `{"question": ..., "answer": ...}` turn is appended to the history stored in `st.session_state`.
8. Given a summary, season rounds, history and question, when `build_follow_up_prompt` builds the prompt, then the prompt contains the summary text, every supplied rounds record, every supplied history turn's question and answer, the question itself, and no rounds records outside those supplied.
9. Given more than `FOLLOW_UP_HISTORY_MAX_TURNS` turns are stored, when the prompt is built, then only the most recent `FOLLOW_UP_HISTORY_MAX_TURNS` turns are included and older turns are dropped from the prompt.
10. Given the language selector (`LANGUAGE_SELECTOR_KEY`) is `English`, when a question is answered, then the request uses the English system message and English instruction; given any other value, then it uses the Chinese system message and Chinese instruction.
11. Given AI is not configured, when the reader submits a non-empty question, then `MISSING_CONFIG_MESSAGE` is displayed, no chat request is made, and the history is unchanged.
12. Given AI is configured but the chat request raises `AISummaryError` (transport failure, non-2xx status, unparseable body, or empty content), when the reader submits a non-empty question, then the corresponding error message is displayed, no exception escapes the fragment, and the history is unchanged.
13. Given `season_rounds` is empty or `None`, when the reader submits a non-empty question, then a chat request is still made, the prompt contains `MISSING_ROUNDS_NOTE` (or `MISSING_ROUNDS_NOTE_EN` in English mode), and the resulting answer is displayed.
14. Given at least one stored turn for the current summary, when the fragment reruns within the same session, then all stored questions and answers are still rendered in the fragment and are included in `build_follow_up_prompt`'s history argument.
15. Given the summary text handed to the follow-up fragment differs from the summary the stored turns were recorded against, when the fragment renders, then the stored turns are discarded and are neither rendered nor sent as context.
16. Given the reader never submits a question, when the League page renders, then the summary section's widgets and output are unchanged from before this change and the existing test suite passes unmodified.

## Interfaces

All new symbols live in `ai_summary.py`; the only page change is in `pages/3_🏆_League.py`.

`ai_summary.py` — changed signature:

```python
def render_season_summary(player_name: str, season_rounds: list[dict]) -> str:
    """Render the language selector and the '🤖 AI 赛季总结' button and, after a press,
    the summary or a readable error. Returns the summary text that was rendered,
    or "" when no summary was produced."""
```

`ai_summary.py` — new constants:

```python
FOLLOW_UP_INPUT_LABEL: str = "追问赛季总结 / Ask a follow-up question"
FOLLOW_UP_BUTTON_LABEL: str = "提问 / Ask"
FOLLOW_UP_INPUT_KEY: str = "ai_season_follow_up_question"
FOLLOW_UP_HISTORY_KEY: str = "ai_season_follow_up_history"
FOLLOW_UP_HISTORY_MAX_TURNS: int = 6
EMPTY_QUESTION_MESSAGE: str = "请先输入问题再提交。"
FOLLOW_UP_INSTRUCTION: str = (
    "请只根据上面的赛季总结、球员轮次数据和之前的问答，用简体中文回答下面的追问。"
    "不要编造数据，如果数据不足以回答，请直接说明。"
)
FOLLOW_UP_INSTRUCTION_EN: str = (
    "Answer the follow-up question below in English, using only the season summary, "
    "the player's round data and the earlier Q&A above. Do not invent data; say so "
    "if the available data cannot answer the question."
)
MISSING_ROUNDS_NOTE: str = "注意：本次追问没有可用的轮次数据，请只依据赛季总结和之前的问答作答。"
MISSING_ROUNDS_NOTE_EN: str = (
    "Note: no round data is available for this question; answer from the season "
    "summary and the earlier Q&A only."
)
```

`ai_summary.py` — new functions:

```python
@st.fragment
def render_follow_up_questions(
    player_name: str,
    season_rounds: list[dict],
    summary: str,
) -> None:
    """Render the persistent Q&A list, the question input and its submit button for this
    summary, and on submit display the answer or a readable message. Reads and writes
    st.session_state[FOLLOW_UP_HISTORY_KEY]; resolves the answer language from
    st.session_state.get(LANGUAGE_SELECTOR_KEY, DEFAULT_LANGUAGE) via normalize_language."""

def build_follow_up_prompt(
    player_name: str,
    season_rounds: list[dict],
    summary: str,
    history: list[dict],
    question: str,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Return the chat prompt containing the summary, the supplied rounds records, the most
    recent FOLLOW_UP_HISTORY_MAX_TURNS history turns and the question, with the instruction
    for the selected language. Accepts a DataFrame for season_rounds. Never raises."""

def answer_follow_up_question(
    player_name: str,
    season_rounds: list[dict],
    summary: str,
    history: list[dict],
    question: str,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Return one Ollama-generated answer, or raise AISummaryError (missing config, empty
    question, transport failure, empty response). Calls _call_ollama_chat with
    SYSTEM_MESSAGE_EN / SYSTEM_MESSAGE for the selected language."""

def get_follow_up_history(summary: str) -> list[dict]:
    """Return the stored turns ({"question": str, "answer": str}) for this summary; returns []
    and resets the stored value when the stored summary differs from the given one, or when
    nothing is stored. Never raises."""

def append_follow_up_turn(summary: str, question: str, answer: str) -> None:
    """Append one turn to st.session_state[FOLLOW_UP_HISTORY_KEY] under this summary. Never raises."""
```

`pages/3_🏆_League.py` — call site change (module-qualified here; adjust to the page's existing import style):

```python
summary = render_season_summary(player_name, season_rounds)
if summary:
    render_follow_up_questions(player_name, season_rounds, summary)
```

`season_rounds` is the same value already passed to `render_season_summary` on the League page.

## Out of scope

- Changing the season summary prompt, its content or the language-selection behaviour shipped previously.
- Follow-up Q&A on any page or feature other than the League page season summary (Cup, Outing, player deep dive, announcements).
- Persisting Q&A history beyond the browser session or sharing it between users.
- Streaming responses, citations, feedback controls, or exporting the conversation.

## Open questions

- Where `render_follow_up_questions` lives — assumption: a new function in `ai_summary.py`, next to the existing summary rendering.
- Which `st.session_state` keys hold the history and whether it is keyed per season — assumption: one key, `FOLLOW_UP_HISTORY_KEY`, whose value records the summary the turns belong to, so a summary regenerated for a different season cannot mix conversations.
- Whether the conversation is cleared when the summary is regenerated — assumption: it is cleared, identified by the summary text handed to the fragment; a retry that produces different text also starts a fresh conversation.
- How much history is fed back to Ollama — assumption: the most recent `FOLLOW_UP_HISTORY_MAX_TURNS` (6) turns, older ones dropped.
- Which language answers come back in — assumption: the language currently selected in `LANGUAGE_SELECTOR_KEY`, normalised with the existing `normalize_language`.
- What happens when rounds data is unavailable — assumption: the question is still sent, with `MISSING_ROUNDS_NOTE` in the prompt.
- What `render_season_summary` returns when nothing was produced — assumption: `""` rather than `None`, so the League page can use a simple truthiness check and existing callers ignore the value.
- Where the follow-up box appears when summary generation failed — assumption: not at all; only a non-empty summary enables the question box.
- The exact widget labels and control shape — assumption: a text input plus a submit button inside an `st.form`, labelled with the bilingual constants above.
- How the selected player is identified on the League page — assumption: the same player/rounds values the page already passes to `render_season_summary` are reused unchanged.
