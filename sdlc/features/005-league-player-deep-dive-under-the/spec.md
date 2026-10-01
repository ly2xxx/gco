<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@9f177e5 -->
## Summary
Adds an "🤖 AI 赛季总结" button directly below the four metrics in the League Player Deep-Dive view of `pages/3_🏆_League.py`. Pressing it calls Ollama Cloud's chat API via a new `ai_summary.py` module (credentials and model read from `st.secrets` like `auth.py`) and renders a Chinese season summary for the currently selected player. Tests cover the flow with the outbound call mocked, so no credentials or network are required.

## Behaviour
1. Given the League Player Deep-Dive for a selected player is displayed, when the view renders, then a button labelled exactly `🤖 AI 赛季总结` is rendered directly below the four existing metric elements.
2. Given the deep-dive is displayed and the button has not been pressed, when the view renders, then `ai_summary.summarize_season` has not been called and no summary or error text is shown.
3. Given the AI secrets are absent, when the app imports `ai_summary` and renders the deep-dive without pressing the button, then the four metrics and the button render and no exception is raised.
4. Given the button is pressed and the mocked AI call returns non-empty text, when the render completes, then that exact text is displayed below the button.
5. Given the button is pressed, when the outbound prompt is built, then it contains the selected player's name and every per-round field of that player's loaded season rounds, and contains no other player's name or round data.
6. Given both AI secrets are present, when the button is pressed, then the API key and model passed to the outbound call equal the values read from `st.secrets`, and no credential literal appears in `ai_summary.py`.
7. Given the API key or model is missing from `st.secrets`, when the button is pressed, then a readable error message is displayed in place of the summary and no outbound request is made.
8. Given the mocked outbound call raises an exception or returns a non-success response, when the button is pressed, then a readable error message is displayed in place of the summary and no exception escapes the view render.
9. Given the selected player has zero season rounds loaded, when the button is pressed, then no outbound request is made and a readable "no rounds" message is displayed in place of the summary.
10. Given the mocked outbound call returns an empty or whitespace-only string, when the button is pressed, then a readable error message is displayed in place of the summary.
11. Given the button is pressed and completes, when it is pressed a second time, then a second independent outbound request is made (mock call count becomes 2), with no caching between presses.
12. Given a visitor with no admin token, when they press the button, then the summary flow runs without any admin gating.
13. Given no player is selected in the deep-dive, when the view renders, then the `🤖 AI 赛季总结` button is not rendered.
14. Given the change is applied, when the existing unit and BDD test suites run, then they pass unchanged.

## Interfaces

**New file: `ai_summary.py`** (repository root, alongside `auth.py`)

```python
AI_SUMMARY_BUTTON_LABEL: str = "🤖 AI 赛季总结"
"""Exact label rendered on the button in the League Player Deep-Dive."""


class AISummaryError(Exception):
    """Raised when a season summary cannot be produced: missing config, transport failure, or empty response."""


def get_ai_config() -> tuple[str, str]:
    """Return (api_key, model) read from st.secrets.

    Uses the guarded `st.secrets.get(..., "")` pattern from auth._allowed_tokens(),
    catching any exception and falling back to ("", "") so a missing secrets file
    cannot break the page. Does not raise.
    """


def is_ai_configured() -> bool:
    """Return True only when both the API key and the model name are non-empty."""


def build_summary_prompt(player_name: str, season_rounds: list[dict]) -> str:
    """Return the chat prompt instructing a Chinese, few-short-paragraph season summary.

    The prompt contains only `player_name` and `season_rounds`; it must not include
    data from any other player.
    """


def _call_ollama_chat(api_key: str, model: str, prompt: str) -> str:
    """Perform the outbound Ollama Cloud chat request and return the assistant message text.

    Single seam for the network call; raises AISummaryError on transport error,
    non-success status, malformed JSON, or empty content. Never reads secrets itself.
    """


def summarize_season(player_name: str, season_rounds: list[dict]) -> str:
    """Return the Chinese season summary for one player.

    Raises AISummaryError when the config is missing, when `season_rounds` is empty,
    or when the outbound call fails or returns empty text.
    """


def render_season_summary(player_name: str, season_rounds: list[dict]) -> None:
    """Render the '🤖 AI 赛季总结' button and, after a press, the summary or a readable error.

    Renders nothing when `player_name` is falsy. Catches AISummaryError and renders
    its message in place of the summary so the rest of the page keeps working.
    Called from the League Player Deep-Dive view.
    """
```

**Changed file: `pages/3_🏆_League.py`**
- Add `from ai_summary import render_season_summary`.
- In the League Player Deep-Dive section, call `render_season_summary(selected_player, season_rounds)` immediately after the four existing metric elements are rendered, passing the already-selected player name and the already-loaded season-round records for that player. No other line in this file changes.

**Secrets contract (`.streamlit/secrets.toml`, not committed)**
- `OLLAMA_API_KEY: str` — API key.
- `OLLAMA_MODEL: str` — model name.

**New file: `tests/test_ai_season_summary.py`**
- Drives the deep-dive with Streamlit's `AppTest` (pattern of `tests/test_announcement_page_wiring.py`), monkeypatching `ai_summary._call_ollama_chat` (or `ai_summary.summarize_season`) and `st.secrets`; no network, no credentials, no manual steps.

**No change to `auth.py`, `data.py`, `streamlit_app.py`, `theme.py`, or `requirements.txt` unless the chosen HTTP client is not already a dependency.**

## Out of scope
- Any change to the four existing metrics or how they are calculated.
- AI summaries anywhere else (Cup, Outing, Events, or a league-wide/whole-club summary).
- Persisting, caching or showing a history of previously generated summaries.
- Making the button admin-only or adding new admin/auth behaviour.
- Streaming output, retries, cost control or prompt-quality tuning beyond one usable summary.
- Changes to `auth.py` or to how secrets are otherwise managed.

## Open questions
- Secret key names are not specified in the intent. **Assumption:** `OLLAMA_API_KEY` and `OLLAMA_MODEL` in `st.secrets`, read with the same guarded `st.secrets.get(..., default)` pattern as `auth.py`.
- The exact Ollama Cloud endpoint and HTTP method are not specified. **Assumption:** the chat endpoint `https://ollama.com/api/chat` with a JSON body carrying `model` and a `messages` list, called with a repository-approved HTTP client; the URL is a module constant, not a secret.
- The exact per-round fields the deep-dive already loads are not enumerated here. **Assumption:** pass the round records exactly as the view already holds them, unmodified, without re-querying the data layer.
- Whether the summary survives Streamlit re-runs after the button press. **Assumption:** the summary is rendered for the run produced by the press only; each press issues exactly one fresh request and nothing is cached or persisted.
- Whether the button is disabled or shows a spinner while the request is in flight. **Assumption:** a spinner is shown during the call; the button stays enabled and concurrent clicks are not coordinated.
- Prompt content beyond name, rounds and a Chinese-prose instruction. **Assumption:** one system message and one user message, no few-shot examples, no tuning.
- Behaviour when no player is selected. **Assumption:** the button is not rendered, since there are no metrics to sit below and no player to summarize.
