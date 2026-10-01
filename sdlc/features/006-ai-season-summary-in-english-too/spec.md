<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@95bc6e9 -->
## Summary

The AI season summary in the League Player Deep-Dive gains a 中文 / English selector placed beside the existing 🤖 AI 赛季总结 button, defaulting to 中文. Chinese output is byte-identical to today's behaviour; selecting English produces the same season recap written in English. All changes are confined to `ai_summary.py`; no other page, config or prompt for the Chinese path changes.

## Behaviour

1. Given a non-empty player name and at least one season round, when the season summary section renders, then a language selector appears immediately beside the "🤖 AI 赛季总结" button, offering exactly the options "中文" and "English" in that order with "中文" selected before any interaction.
2. Given the season summary section renders for a player whose name is empty, when it renders, then no language selector, no AI button and no summary text are rendered.
3. Given "中文" is selected, when the AI button is pressed, then the outbound chat request uses the unchanged `SYSTEM_MESSAGE` as the system message and a prompt built by `build_summary_prompt(player_name, season_rounds)` with no English instruction, and the returned text is rendered with `st.markdown`.
4. Given "English" is selected, when the AI button is pressed, then the outbound chat request uses `SYSTEM_MESSAGE_EN` as the system message and a prompt built by `build_summary_prompt(player_name, season_rounds, language="English")`, and the returned text is rendered with `st.markdown`.
5. Given the same player and rounds, when the prompt is built for English, then it contains the player name and, for every round, the same `key=value` pairs that the Chinese prompt contains, with the same number of round lines, and only the fixed labels and instruction text differ in language.
6. Given `season_rounds` is supplied as a pandas DataFrame, when the prompt is built for English, then it contains one line per DataFrame row with that row's `key=value` pairs.
7. Given a summary in one language is displayed, when the user switches the selector to the other language without pressing the AI button, then no summary text is displayed.
8. Given a summary is displayed for English, when the user switches back to "中文" and presses the AI button, then a Chinese summary generated from the Chinese prompt is displayed (and symmetrically for English after switching from 中文).
9. Given the player has no season rounds (empty list, `None`, or a DataFrame with no rows), when the AI button is pressed with either language selected, then `NO_ROUNDS_MESSAGE` is shown and no chat request is made.
10. Given the AI configuration is missing (empty API key or empty model in `st.secrets`), when the AI button is pressed with English selected, then `MISSING_CONFIG_MESSAGE` is shown and no chat request is made.
11. Given the chat request raises `AISummaryError` (transport/HTTP failure, unparsable response, or empty content), when the AI button is pressed with English selected, then the corresponding `CALL_FAILED_MESSAGE` or `EMPTY_RESPONSE_MESSAGE` text is shown and no summary is rendered.
12. Given the selector is rendered, when the user changes the selection and does not press the AI button, then no chat request is made and no summary is generated.
13. Given the pre-existing public API, when `build_summary_prompt(player_name, season_rounds)` or `summarize_season(player_name, season_rounds)` is called with no language argument, then the call behaves exactly as before this change (Chinese instruction, `SYSTEM_MESSAGE`).
14. Given an unsupported language value such as `"fr"`, `""` or `None`, when `build_summary_prompt` or `summarize_season` is called with it, then the call behaves exactly as the 中文 selection and does not raise.

## Interfaces

All additions and changes below belong in `ai_summary.py`. Every network-touching test stubs `_call_ollama_chat`, so no secrets or network are required.

New module constants (same file):

```python
LANGUAGE_CHINESE: str = "中文"
LANGUAGE_ENGLISH: str = "English"
LANGUAGE_OPTIONS: tuple[str, str] = (LANGUAGE_CHINESE, LANGUAGE_ENGLISH)
DEFAULT_LANGUAGE: str = LANGUAGE_CHINESE
LANGUAGE_SELECTOR_LABEL: str = "语言 / Language"
LANGUAGE_SELECTOR_KEY: str = "ai_season_summary_language"
SYSTEM_MESSAGE_EN: str = (
    "You are a golf club data analysis assistant. Always write in English."
)
PROMPT_INSTRUCTION_EN: str = (
    "Using only this player's own data above, write a season summary in English, "
    "2-3 paragraphs, analysing overall performance, highlights and areas to improve. "
    "Do not invent data and do not mention other players."
)
```

Unchanged constants (must keep their current values): `SYSTEM_MESSAGE`, `PROMPT_INSTRUCTION`, `AI_SUMMARY_BUTTON_LABEL`, `OLLAMA_CHAT_URL`, `OLLAMA_API_KEY_SECRET`, `OLLAMA_MODEL_SECRET`, `REQUEST_TIMEOUT_SECONDS`, `MISSING_CONFIG_MESSAGE`, `NO_ROUNDS_MESSAGE`, `EMPTY_RESPONSE_MESSAGE`, `CALL_FAILED_MESSAGE`.

New helper:

```python
def normalize_language(language: str | None) -> str:
    """Return LANGUAGE_ENGLISH only for LANGUAGE_ENGLISH, otherwise LANGUAGE_CHINESE. Never raises."""
```

Changed functions:

```python
def build_summary_prompt(
    player_name: str,
    season_rounds: list[dict],
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Return the chat prompt containing only this player's name and rounds, written in the selected language."""
```

- For `language="中文"` (the default) the returned string is identical to the pre-change output.
- The English variant uses the same round data lines and the same `key=value` formatting; only the fixed labels and trailing instruction are English.

```python
def _call_ollama_chat(
    api_key: str,
    model: str,
    prompt: str,
    system_message: str = SYSTEM_MESSAGE,
) -> str:
    """Single seam for the outbound Ollama Cloud chat request; never reads secrets."""
```

- The Chinese path calls it with exactly the three legacy positional arguments so existing stubs keep working; the English path passes `system_message=SYSTEM_MESSAGE_EN`.

```python
def summarize_season(
    player_name: str,
    season_rounds: list[dict],
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Return the season summary for one player in the selected language, or raise AISummaryError."""
```

- Normalizes `language` with `normalize_language`, keeps the existing config → round-count → request → empty-response ordering, and passes the selected language to `build_summary_prompt`.

```python
def render_season_summary(player_name: str, season_rounds: list[dict]) -> None:
    """Render the language selector beside the '🤖 AI 赛季总结' button and, after a press, the summary or a readable error."""
```

- Signature unchanged; callers in the dashboard do not change.
- Internally renders `st.radio(LANGUAGE_SELECTOR_LABEL, options=LANGUAGE_OPTIONS, index=0, key=LANGUAGE_SELECTOR_KEY, horizontal=True)` in a column immediately to the left of the existing button column (`key="ai_season_summary_button"` unchanged), then passes the selected value to `summarize_season`.
- The early `return` for an empty `player_name` stays before any rendering.

Unchanged functions: `get_ai_config`, `is_ai_configured`, `_round_count`, and the `AISummaryError` class.

## Out of scope

- Translating or localising anything outside the AI season summary (announcements, events, league/cup pages, other AI features).
- Making the language choice an app-wide or persisted locale setting; the choice resets to 中文 in a new session or page reload.
- Changing the Chinese prompt, the Chinese system message, the Chinese output, or the Ollama/model configuration.
- Any language beyond 中文 and English.
- Caching or persisting generated summaries, or auto-regenerating a summary when the selector changes (a summary is only produced by a button press, in the language selected at that press).
- Changes to any file other than `ai_summary.py`, including the button label, error messages and existing test files.

## Open questions

- Where exactly does the choice apply? Assumption: only the season summary rendered by `ai_summary.render_season_summary`; the selectable value is not read anywhere else.
- Does the selection survive a reload or new session? Assumption: no — it resets to 中文 (default index 0) each time, matching the stated default.
- Must the English summary keep the same sections and figures as the Chinese one? Assumption: yes — same structure and stats, English wording; this is why the English prompt reuses the same data lines and round count.
- What happens to a displayed summary when the language changes? Assumption: it must match the currently selected language, so switching the selector without pressing the button displays nothing until a fresh summary is generated.
- The English prompt and system-message wording are not fixed by the intent. Assumption: the exact `SYSTEM_MESSAGE_EN` and `PROMPT_INSTRUCTION_EN` strings above are used, mirroring the Chinese instructions.
- How should an unsupported language value be handled? Assumption: fall back to 中文 rather than raising, since only 中文 and English are supported.
- Which side of the button does the selector sit on? Assumption: left of the button, on the same row, so the AI button keeps its right-hand position.
