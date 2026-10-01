<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@9b951c3 -->
## Approach
Make `render_season_summary` return the summary text it rendered (or `""`), add the follow-up constants, the pure prompt/answer/history helpers, and a `@st.fragment` `render_follow_up_questions` to `ai_summary.py`, then change the League page to hand the returned summary to that fragment inside an `if summary:` guard. Everything else — existing widgets, prompts, error messages, session keys — stays as it is.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| `render_season_summary` returns the summary text, and the League page passes that value to `ai_summary.render_follow_up_questions`. | 1, 2, 3 | 1, 4 |
| A question box appears under the season summary on the League page. | 4, 5 | 3, 4 |
| Asking a question produces an Ollama-generated answer grounded in the rounds data, the summary, and prior Q&A. | 7, 8, 10, 13 | 2, 3 |
| Earlier questions and answers remain visible and are included as context in later answers, surviving reruns within the session. | 9, 14, 15 | 2, 3 |
| If Ollama is unavailable or the question is empty, the page degrades gracefully with a visible message instead of erroring. | 6, 11, 12 | 2, 3 |
| The existing tests still pass. | 16 | 1, 2, 3, 4 |

## Phase 1: `render_season_summary` returns the summary text
<!-- phase: 1 -->
<!-- targets: ai_summary.py, tests/test_ai_season_summary_return.py -->
<!-- frozen: pages/3_🏆_League.py, tests/test_ai_season_summary.py, tests/test_ai_summary_logic.py, tests/test_ai_summary_language_logic.py, tests/test_ai_summary_language_ui.py, tests/test_league_deep_dive_wiring.py, streamlit_app.py, test_streamlit_app.py -->

**Goal:** `render_season_summary` returns the generated summary string when it renders one and `""` in every no-summary path, with unchanged widgets and messages.

**Changes:**
- `ai_summary.py`: replace the existing `render_season_summary` (signature `def render_season_summary(player_name: str, season_rounds: list[dict]) -> str:`) with exactly:

```python
def render_season_summary(player_name: str, season_rounds: list[dict]) -> str:
    """Render the language selector beside the '🤖 AI 赛季总结' button and, after a press,
    the summary or a readable error. Returns the summary text that was rendered, or ""
    when no summary was produced."""
    if not player_name:
        return ""
    language_column, button_column = st.columns([1, 1])
    with language_column:
        language = st.radio(
            LANGUAGE_SELECTOR_LABEL,
            options=LANGUAGE_OPTIONS,
            index=0,
            key=LANGUAGE_SELECTOR_KEY,
            horizontal=True,
        )
    with button_column:
        pressed = st.button(AI_SUMMARY_BUTTON_LABEL, key="ai_season_summary_button")
    if not pressed:
        return ""
    if _round_count(season_rounds) == 0:
        st.warning(NO_ROUNDS_MESSAGE)
        return ""
    with st.spinner("正在生成赛季总结…"):
        try:
            summary = summarize_season(player_name, season_rounds, language)
        except AISummaryError as exc:
            st.error(str(exc))
            return ""
        st.markdown(summary)
        return summary
```

- No other symbol, constant, import, widget, key or message changes. The League page keeps ignoring the return value until Phase 4.
- `tests/test_ai_season_summary_return.py` (new): module-level helper, reused by later assertions in this file:

```python
from unittest.mock import MagicMock

import pytest

import ai_summary


def make_fake_streamlit(*, pressed: bool = False, language: str = ai_summary.DEFAULT_LANGUAGE) -> MagicMock:
    fake = MagicMock(name="st")
    fake.session_state = {}
    fake.columns.return_value = [MagicMock(name="language_column"), MagicMock(name="button_column")]
    fake.radio.return_value = language
    fake.button.return_value = pressed
    fake.spinner.return_value = MagicMock(name="spinner")
    return fake


def exploding(*args, **kwargs):
    raise AssertionError("summarize_season must not be called in this scenario")
```

Tests in that file:
- `test_returns_summary_text_when_button_pressed`: fake with `pressed=True`, `monkeypatch.setattr(ai_summary, "st", fake)`, `monkeypatch.setattr(ai_summary, "summarize_season", lambda player, rounds, language: "SUMMARY_SENTINEL")`; assert `ai_summary.render_season_summary("杨明", [{"date": "ROUND_ONE"}]) == "SUMMARY_SENTINEL"`, `fake.markdown.assert_called_once_with("SUMMARY_SENTINEL")`, `fake.warning.assert_not_called()`, `fake.error.assert_not_called()` (spec behaviour 1).
- `test_returns_empty_when_player_name_is_empty`: `render_season_summary("", [{"date": "ROUND_ONE"}]) == ""`, `fake.columns.assert_not_called()` (spec 2).
- `test_returns_empty_when_button_not_pressed`: `pressed=False`, `summarize_season` patched to `exploding`; assert `== ""` and `fake.markdown.assert_not_called()` (spec 2).
- `test_returns_empty_when_no_rounds`: `pressed=True`, `season_rounds=[]`, `summarize_season` patched to `exploding`; assert `== ""` and `fake.warning.assert_called_once_with(ai_summary.NO_ROUNDS_MESSAGE)` (spec 2).
- `test_returns_empty_when_summarize_raises`: `pressed=True`, `monkeypatch.setattr(ai_summary, "summarize_season", raising_summarize)` where `raising_summarize` raises `ai_summary.AISummaryError(ai_summary.MISSING_CONFIG_MESSAGE)`; assert `== ""`, `fake.error.assert_called_once_with(ai_summary.MISSING_CONFIG_MESSAGE)`, `fake.markdown.assert_not_called()` (spec 2).
- `test_selected_language_is_passed_to_summarize_season`: fake with `language=ai_summary.LANGUAGE_ENGLISH`, recorder `summarize_season(player_name, season_rounds, language)` appending to a list and returning `"S"`; assert the recorded call is `("杨明", [{"date": "ROUND_ONE"}], ai_summary.LANGUAGE_ENGLISH)` and the function returns `"S"` (spec 2, unchanged language behaviour).

**Definition of done:**
- [ ] `tests/test_ai_season_summary_return.py::test_returns_summary_text_when_button_pressed`: spec behaviour 1 — pressing the button returns and renders the same summary text; `monkeypatch.setattr(ai_summary, "st", make_fake_streamlit(pressed=True))`, no teardown needed.
- [ ] `tests/test_ai_season_summary_return.py::test_returns_empty_when_player_name_is_empty`: spec behaviour 2 — `""` and no widgets when `player_name` is empty.
- [ ] `tests/test_ai_season_summary_return.py::test_returns_empty_when_button_not_pressed`: spec behaviour 2 — `""` and no summary call when the button was not pressed.
- [ ] `tests/test_ai_season_summary_return.py::test_returns_empty_when_no_rounds`: spec behaviour 2 — `""` plus the existing `NO_ROUNDS_MESSAGE` warning when `season_rounds` is empty.
- [ ] `tests/test_ai_season_summary_return.py::test_returns_empty_when_summarize_raises`: spec behaviour 2 — `""` plus the existing error message on `AISummaryError`.
- [ ] `tests/test_ai_season_summary_return.py::test_selected_language_is_passed_to_summarize_season`: spec behaviour 2 — the radio value still reaches `summarize_season` unchanged.
- [ ] The pre-existing AI-summary tests still pass unmodified: `tests/test_ai_season_summary.py`, `tests/test_ai_summary_logic.py`, `tests/test_ai_summary_language_logic.py`, `tests/test_ai_summary_language_ui.py`.

**Verify:**
```bash
uv run pytest tests/test_ai_season_summary_return.py tests/test_ai_season_summary.py tests/test_ai_summary_logic.py tests/test_ai_summary_language_logic.py tests/test_ai_summary_language_ui.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Follow-up constants, prompt builder, answer call and session history
<!-- phase: 2 -->
<!-- targets: ai_summary.py, tests/test_ai_follow_up_logic.py -->
<!-- frozen: pages/3_🏆_League.py, tests/test_ai_season_summary_return.py, tests/test_ai_season_summary.py, tests/test_ai_summary_logic.py, tests/test_ai_summary_language_logic.py, tests/test_ai_summary_language_ui.py -->

**Goal:** The follow-up prompt, the Ollama answer call and the session-scoped history helpers exist and behave per spec, without any Streamlit rendering.

**Changes:**
- `ai_summary.py`: add these module-level constants directly after `PROMPT_INSTRUCTION_EN`, exactly as named:

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

- `ai_summary.py`: add these four functions after `summarize_season`, using the existing `get_ai_config`, `normalize_language`, `AISummaryError`, `_call_ollama_chat`, `SYSTEM_MESSAGE` and `SYSTEM_MESSAGE_EN`. No new imports and no dependency changes (`pandas` is already a project dependency).

```python
def build_follow_up_prompt(
    player_name: str,
    season_rounds: list[dict],
    summary: str,
    history: list[dict],
    question: str,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Return the chat prompt with the summary, the supplied rounds records, the newest
    FOLLOW_UP_HISTORY_MAX_TURNS history turns, the question and the language instruction.
    Accepts a DataFrame for season_rounds. Never raises."""
    english = normalize_language(language) == LANGUAGE_ENGLISH
    try:
        rounds = season_rounds
        if hasattr(rounds, "to_dict"):
            rounds = rounds.to_dict(orient="records")
        records = [dict(record) for record in ([] if rounds is None else rounds)]
        turns = [dict(turn) for turn in ([] if history is None else history)][-FOLLOW_UP_HISTORY_MAX_TURNS:]
        if english:
            lines = [
                f"Player name: {player_name}",
                "Season summary:",
                str(summary or ""),
                "This player's rounds this season (one line per round):",
            ]
        else:
            lines = [
                f"球员姓名：{player_name}",
                "赛季总结：",
                str(summary or ""),
                "该球员本赛季的比赛轮次数据（每一行是一轮）：",
            ]
        if not records:
            lines.append(MISSING_ROUNDS_NOTE_EN if english else MISSING_ROUNDS_NOTE)
        for index, record in enumerate(records, start=1):
            fields = "；".join(f"{key}={value}" for key, value in record.items())
            lines.append(f"Round {index}: {fields}" if english else f"第 {index} 轮：{fields}")
        if turns:
            lines.append("Earlier Q&A:" if english else "之前的问答：")
            for turn in turns:
                lines.append(f"Q: {turn.get('question', '')}" if english else f"问：{turn.get('question', '')}")
                lines.append(f"A: {turn.get('answer', '')}" if english else f"答：{turn.get('answer', '')}")
        lines.append("Follow-up question:" if english else "追问：")
        lines.append(str(question or ""))
        lines.append(FOLLOW_UP_INSTRUCTION_EN if english else FOLLOW_UP_INSTRUCTION)
        return "\n".join(lines)
    except Exception:
        fallback = [str(summary or ""), str(question or "")]
        fallback.append(FOLLOW_UP_INSTRUCTION_EN if english else FOLLOW_UP_INSTRUCTION)
        return "\n".join(fallback)


def answer_follow_up_question(
    player_name: str,
    season_rounds: list[dict],
    summary: str,
    history: list[dict],
    question: str,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Return one Ollama-generated answer, or raise AISummaryError (missing config,
    empty question, transport failure, empty response)."""
    if not question or not str(question).strip():
        raise AISummaryError(EMPTY_QUESTION_MESSAGE)
    api_key, model = get_ai_config()
    if not api_key or not model:
        raise AISummaryError(MISSING_CONFIG_MESSAGE)
    selected = normalize_language(language)
    prompt = build_follow_up_prompt(player_name, season_rounds, summary, history, question, selected)
    if selected == LANGUAGE_ENGLISH:
        text = _call_ollama_chat(api_key, model, prompt, system_message=SYSTEM_MESSAGE_EN)
    else:
        text = _call_ollama_chat(api_key, model, prompt)
    if not text or not text.strip():
        raise AISummaryError(EMPTY_RESPONSE_MESSAGE)
    return text.strip()


def get_follow_up_history(summary: str) -> list[dict]:
    """Return the stored turns ({"question": str, "answer": str}) for this summary; returns []
    and resets the stored value when the stored summary differs from the given one, or when
    nothing is stored. Never raises."""
    try:
        stored = st.session_state.get(FOLLOW_UP_HISTORY_KEY)
        if not isinstance(stored, dict) or stored.get("summary") != summary or not isinstance(stored.get("turns"), list):
            st.session_state[FOLLOW_UP_HISTORY_KEY] = {"summary": summary, "turns": []}
            return []
        return [turn for turn in stored["turns"] if isinstance(turn, dict)]
    except Exception:
        return []


def append_follow_up_turn(summary: str, question: str, answer: str) -> None:
    """Append one turn to st.session_state[FOLLOW_UP_HISTORY_KEY] under this summary. Never raises."""
    try:
        stored = st.session_state.get(FOLLOW_UP_HISTORY_KEY)
        if not isinstance(stored, dict) or stored.get("summary") != summary or not isinstance(stored.get("turns"), list):
            stored = {"summary": summary, "turns": []}
        stored["turns"].append({"question": str(question), "answer": str(answer)})
        st.session_state[FOLLOW_UP_HISTORY_KEY] = stored
    except Exception:
        return
```

- `tests/test_ai_follow_up_logic.py` (new): module-level helpers:

```python
from unittest.mock import MagicMock

import pandas as pd
import pytest

import ai_summary


def fake_st() -> MagicMock:
    fake = MagicMock(name="st")
    fake.session_state = {}
    return fake


def chat_recorder(result: str = "ANSWER_SENTINEL", error: Exception | None = None):
    calls: list[dict] = []

    def _chat(api_key, model, prompt, system_message=ai_summary.SYSTEM_MESSAGE):
        calls.append({"api_key": api_key, "model": model, "prompt": prompt, "system_message": system_message})
        if error is not None:
            raise error
        return result

    _chat.calls = calls
    return _chat


def exploding(*args, **kwargs):
    raise AssertionError("_call_ollama_chat must not be called in this scenario")
```

Tests in that file:
- `test_prompt_contains_summary_rounds_history_and_question`: build with `[{"date": "ROUND_ONE_DATE", "net": 72}, {"date": "ROUND_TWO_DATE", "net": 80}]`, `"SUMMARY_SENTINEL"`, `[{"question": "Q1_SENTINEL", "answer": "A1_SENTINEL"}]`, `"QUESTION_SENTINEL"`, Chinese default; assert all five sentinels plus `"72"` are substrings, `ai_summary.FOLLOW_UP_INSTRUCTION in prompt`, and `"ROUND_THREE_DATE" not in prompt` (spec 8).
- `test_prompt_keeps_only_the_newest_history_turns`: history `[{"question": f"turn-{i}-q", "answer": f"turn-{i}-a"} for i in range(1, 9)]`; assert `"turn-8-q" in prompt` and `"turn-3-q" in prompt` and `"turn-1-q" not in prompt` and `"turn-2-a" not in prompt` (spec 9).
- `test_prompt_accepts_a_dataframe_and_lists_each_row`: `pd.DataFrame([{"date": "DF_ROW_ONE"}, {"date": "DF_ROW_TWO"}])`; assert both markers in the prompt (spec 8).
- `test_prompt_notes_missing_rounds`: `build_follow_up_prompt("p", [], "s", [], "q")` contains `ai_summary.MISSING_ROUNDS_NOTE`; English variant (`language=ai_summary.LANGUAGE_ENGLISH`) contains `ai_summary.MISSING_ROUNDS_NOTE_EN` and not `ai_summary.MISSING_ROUNDS_NOTE` (spec 13).
- `test_prompt_uses_english_instruction_for_english`: English prompt contains `FOLLOW_UP_INSTRUCTION_EN` and not `FOLLOW_UP_INSTRUCTION`; Chinese default is the reverse (spec 10).
- `test_prompt_never_raises`: `build_follow_up_prompt("p", None, None, None, None)` and `build_follow_up_prompt("p", object(), "s", object(), "q")` each return a `str` (interface guarantee).
- `test_answer_raises_for_empty_question_without_calling_chat`: `monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("key", "model"))`, `monkeypatch.setattr(ai_summary, "_call_ollama_chat", exploding)`; for `""` and `"   "` assert `pytest.raises(ai_summary.AISummaryError)` with `str(exc.value) == ai_summary.EMPTY_QUESTION_MESSAGE` (spec 6).
- `test_answer_raises_when_config_is_missing`: `get_ai_config` → `("", "")`, `_call_ollama_chat` → `exploding`; assert `pytest.raises(ai_summary.AISummaryError)` with `str(exc.value) == ai_summary.MISSING_CONFIG_MESSAGE` (spec 11).
- `test_answer_uses_the_selected_language_system_message`: `get_ai_config` → `("key", "model")`, `_call_ollama_chat` patched to `chat_recorder("A")`; English call returns `"A"` and last recorded `system_message == ai_summary.SYSTEM_MESSAGE_EN`; Chinese call records `ai_summary.SYSTEM_MESSAGE` (spec 10).
- `test_answer_propagates_chat_error`: chat recorder raises `ai_summary.AISummaryError(ai_summary.CALL_FAILED_MESSAGE.format(detail="HTTP 500"))`; assert `pytest.raises(ai_summary.AISummaryError)` and the message matches (spec 12).
- `test_answer_raises_on_empty_response`: chat returns `"   "` → `pytest.raises(ai_summary.AISummaryError)` with `str(exc.value) == ai_summary.EMPTY_RESPONSE_MESSAGE` (spec 12).
- `test_history_starts_empty_and_records_the_summary`: `monkeypatch.setattr(ai_summary, "st", fake_st())`; `get_follow_up_history("S1") == []` and `st.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY] == {"summary": "S1", "turns": []}` (spec 14 foundation).
- `test_append_and_get_round_trip`: `append_follow_up_turn("S1", "q1", "a1")`, `append_follow_up_turn("S1", "q2", "a2")`; `get_follow_up_history("S1") == [{"question": "q1", "answer": "a1"}, {"question": "q2", "answer": "a2"}]` (spec 14).
- `test_history_is_discarded_when_summary_differs`: after the round trip, `get_follow_up_history("S2") == []`, `st.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY]["summary"] == "S2"`, and a later `get_follow_up_history("S1") == []` (spec 15).
- `test_history_helpers_never_raise_without_session_state`: patch `ai_summary.st` with `class _Broken: @property\n def session_state(self): raise RuntimeError("no session state")` instance; `get_follow_up_history("S") == []` and `append_follow_up_turn("S", "q", "a") is None` (interface guarantee).

**Definition of done:**
- [ ] `tests/test_ai_follow_up_logic.py::test_prompt_contains_summary_rounds_history_and_question`: spec behaviour 8 — prompt holds summary, every supplied round, every supplied turn's question and answer and the question, and nothing else.
- [ ] `tests/test_ai_follow_up_logic.py::test_prompt_keeps_only_the_newest_history_turns`: spec behaviour 9 — only the newest 6 turns survive.
- [ ] `tests/test_ai_follow_up_logic.py::test_prompt_accepts_a_dataframe_and_lists_each_row`: spec behaviour 8 — DataFrame input works.
- [ ] `tests/test_ai_follow_up_logic.py::test_prompt_notes_missing_rounds`: spec behaviour 13 — `MISSING_ROUNDS_NOTE` / `MISSING_ROUNDS_NOTE_EN` appear when rounds are absent.
- [ ] `tests/test_ai_follow_up_logic.py::test_prompt_uses_english_instruction_for_english`: spec behaviour 10 — English instruction vs Chinese instruction.
- [ ] `tests/test_ai_follow_up_logic.py::test_prompt_never_raises`: interface guarantee — arbitrary input still returns a string.
- [ ] `tests/test_ai_follow_up_logic.py::test_answer_raises_for_empty_question_without_calling_chat`: spec behaviour 6 — empty question never reaches the chat seam.
- [ ] `tests/test_ai_follow_up_logic.py::test_answer_raises_when_config_is_missing`: spec behaviour 11 — `MISSING_CONFIG_MESSAGE` and no request.
- [ ] `tests/test_ai_follow_up_logic.py::test_answer_uses_the_selected_language_system_message`: spec behaviour 10 — `SYSTEM_MESSAGE_EN` / `SYSTEM_MESSAGE` selection.
- [ ] `tests/test_ai_follow_up_logic.py::test_answer_propagates_chat_error` and `::test_answer_raises_on_empty_response`: spec behaviour 12 — transport and empty-response failures surface as `AISummaryError`.
- [ ] `tests/test_ai_follow_up_logic.py::test_history_starts_empty_and_records_the_summary`, `::test_append_and_get_round_trip`, `::test_history_is_discarded_when_summary_differs`, `::test_history_helpers_never_raise_without_session_state`: spec behaviours 14 and 15 — turns are stored, returned, reset on a summary change, and never raise.
- [ ] Phase 1's tests still pass unmodified.

**Verify:**
```bash
uv run pytest tests/test_ai_follow_up_logic.py tests/test_ai_season_summary_return.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 3: The `render_follow_up_questions` fragment
<!-- phase: 3 -->
<!-- targets: ai_summary.py, tests/test_ai_follow_up_ui.py -->
<!-- frozen: pages/3_🏆_League.py, tests/test_ai_follow_up_logic.py, tests/test_ai_season_summary_return.py, tests/test_ai_season_summary.py, tests/test_ai_summary_logic.py, tests/test_ai_summary_language_logic.py, tests/test_ai_summary_language_ui.py -->

**Goal:** Calling `ai_summary.render_follow_up_questions(player_name, season_rounds, summary)` renders stored Q&A plus the labelled form, answers a submitted question or shows the right message, and mutates session state only on success.

**Changes:**
- `ai_summary.py`: add one constant next to the other `FOLLOW_UP_*` constants:

```python
FOLLOW_UP_FORM_KEY: str = "ai_season_follow_up_form"
```

- `ai_summary.py`: add directly below `render_season_summary` (decorator on its own line, immediately above the `def`):

```python
@st.fragment
def render_follow_up_questions(
    player_name: str,
    season_rounds: list[dict],
    summary: str,
) -> None:
    """Render the stored Q&A turns, the question input and its submit button for this
    summary, and on submit display the answer or a readable message."""
    if not summary:
        return
    history = get_follow_up_history(summary)
    for turn in history:
        st.markdown(f"**{turn.get('question', '')}**")
        st.markdown(str(turn.get("answer", "")))
    with st.form(FOLLOW_UP_FORM_KEY, clear_on_submit=True):
        question = st.text_input(FOLLOW_UP_INPUT_LABEL, key=FOLLOW_UP_INPUT_KEY)
        submitted = st.form_submit_button(FOLLOW_UP_BUTTON_LABEL)
    if not submitted:
        return
    if not question or not str(question).strip():
        st.warning(EMPTY_QUESTION_MESSAGE)
        return
    language = st.session_state.get(LANGUAGE_SELECTOR_KEY, DEFAULT_LANGUAGE)
    with st.spinner("正在生成回答…"):
        try:
            answer = answer_follow_up_question(
                player_name, season_rounds, summary, history, question, language
            )
        except AISummaryError as exc:
            st.error(str(exc))
            return
    append_follow_up_turn(summary, question, answer)
    st.markdown(answer)
```

- `tests/test_ai_follow_up_ui.py` (new): module-level helpers:

```python
import inspect
import re
from unittest.mock import MagicMock

import pytest

import ai_summary

SUMMARY = "SUMMARY_SENTINEL"


def fake_st(*, submitted: bool = False, question: str = "", language: str | None = None) -> MagicMock:
    fake = MagicMock(name="st")
    fake.session_state = {}
    if language is not None:
        fake.session_state[ai_summary.LANGUAGE_SELECTOR_KEY] = language
    fake.form_submit_button.return_value = submitted
    fake.text_input.return_value = question
    fake.form.return_value = MagicMock(name="form")
    fake.spinner.return_value = MagicMock(name="spinner")
    return fake


def render_follow_up(*args, **kwargs):
    target = getattr(
        ai_summary.render_follow_up_questions,
        "__wrapped__",
        ai_summary.render_follow_up_questions,
    )
    return target(*args, **kwargs)


def markdowns(fake: MagicMock) -> list[str]:
    return [str(call.args[0]) for call in fake.markdown.call_args_list]


def chat_recorder(result: str = "ANSWER_SENTINEL", error: Exception | None = None):
    calls: list[dict] = []

    def _chat(api_key, model, prompt, system_message=ai_summary.SYSTEM_MESSAGE):
        calls.append({"prompt": prompt, "system_message": system_message})
        if error is not None:
            raise error
        return result

    _chat.calls = calls
    return _chat


def exploding(*args, **kwargs):
    raise AssertionError("_call_ollama_chat must not be called in this scenario")
```

Each test patches `ai_summary.st` with the fake, `ai_summary.get_ai_config` with `lambda: ("key", "model")` unless it is testing missing config, and `ai_summary._call_ollama_chat` with a recorder or `exploding`. No background threads, servers or fixtures to tear down; `monkeypatch` restores everything.

Tests in that file:
- `test_fragment_decorator_is_present`: `assert re.search(r"@st\.fragment\s*\ndef render_follow_up_questions\(", inspect.getsource(ai_summary))` (interface requirement).
- `test_form_uses_expected_labels`: `submitted=False`; `render_follow_up("杨明", [{"date": "ROUND_ONE"}], SUMMARY)`; assert `fake.text_input.assert_called_once_with(ai_summary.FOLLOW_UP_INPUT_LABEL, key=ai_summary.FOLLOW_UP_INPUT_KEY)`, `fake.form_submit_button.assert_called_once_with(ai_summary.FOLLOW_UP_BUTTON_LABEL)`, `fake.form.assert_called_once_with(ai_summary.FOLLOW_UP_FORM_KEY, clear_on_submit=True)` (spec 4).
- `test_empty_summary_renders_nothing`: `summary=""`, `_call_ollama_chat` → `exploding`; assert `fake.text_input.assert_not_called()`, `fake.form_submit_button.assert_not_called()`, `fake.markdown.assert_not_called()`, `ai_summary.FOLLOW_UP_HISTORY_KEY not in fake.session_state` (spec 5).
- `test_empty_question_shows_message_and_keeps_history`: `question="   "`, `submitted=True`, `_call_ollama_chat` → `exploding`; assert `fake.warning.assert_called_once_with(ai_summary.EMPTY_QUESTION_MESSAGE)`, `markdowns(fake) == []`, `fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY]["turns"] == []` (spec 6).
- `test_answer_is_displayed_and_stored`: `question="为什么他上升了？"`, `submitted=True`, chat recorder returns `"ANSWER_SENTINEL"`; assert `markdowns(fake)[-1] == "ANSWER_SENTINEL"`, `fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY] == {"summary": SUMMARY, "turns": [{"question": "为什么他上升了？", "answer": "ANSWER_SENTINEL"}]}`, and `"SUMMARY_SENTINEL" in chat.calls[0]["prompt"]` and `"为什么他上升了？" in chat.calls[0]["prompt"]` (spec 7, spec 8 grounding).
- `test_stored_turns_are_rendered_on_rerun`: seed `fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY] = {"summary": SUMMARY, "turns": [{"question": "q1", "answer": "a1"}, {"question": "q2", "answer": "a2"}]}` before the call, `submitted=False`; assert `"q1"`, `"a1"`, `"q2"`, `"a2"` all appear in `"\n".join(markdowns(fake))` (spec 14).
- `test_turns_from_another_summary_are_discarded`: seed `{"summary": "OLD_SUMMARY", "turns": [{"question": "OLD_Q", "answer": "OLD_A"}]}`, call with `SUMMARY`; assert `"OLD_Q" not in "\n".join(markdowns(fake))`, `fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY] == {"summary": SUMMARY, "turns": []}` (spec 15).
- `test_missing_config_shows_message_and_keeps_history`: `get_ai_config` → `("", "")`, `_call_ollama_chat` → `exploding`, `question="q"`, `submitted=True`; assert `fake.error.assert_called_once_with(ai_summary.MISSING_CONFIG_MESSAGE)` and `fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY]["turns"] == []` (spec 11).
- `test_chat_error_shows_message_and_keeps_history`: chat recorder raises `ai_summary.AISummaryError(ai_summary.CALL_FAILED_MESSAGE.format(detail="HTTP 500"))`; assert `render_follow_up(...) is None`, `fake.error.assert_called_once_with(ai_summary.CALL_FAILED_MESSAGE.format(detail="HTTP 500"))`, `fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY]["turns"] == []` (spec 12).
- `test_empty_response_shows_message`: chat recorder returns `"   "`; assert `fake.error.assert_called_once_with(ai_summary.EMPTY_RESPONSE_MESSAGE)` and turns stay `[]` (spec 12).
- `test_missing_rounds_note_is_sent_and_answer_displayed`: `season_rounds=None`, `question="q"`, `submitted=True`, chat recorder returns `"A"`; assert `ai_summary.MISSING_ROUNDS_NOTE in chat.calls[0]["prompt"]` and `"A" in markdowns(fake)` (spec 13).
- `test_english_language_uses_english_system_message`: `language=ai_summary.LANGUAGE_ENGLISH`, `question="q"`, `submitted=True`, chat recorder returns `"A"`; assert `chat.calls[0]["system_message"] == ai_summary.SYSTEM_MESSAGE_EN` and `ai_summary.FOLLOW_UP_INSTRUCTION_EN in chat.calls[0]["prompt"]` (spec 10).

**Definition of done:**
- [ ] `tests/test_ai_follow_up_ui.py::test_fragment_decorator_is_present`: interface requirement — `render_follow_up_questions` is wrapped by `@st.fragment`.
- [ ] `tests/test_ai_follow_up_ui.py::test_form_uses_expected_labels`: spec behaviour 4 — input labelled `FOLLOW_UP_INPUT_LABEL` (key `FOLLOW_UP_INPUT_KEY`) and submit button labelled `FOLLOW_UP_BUTTON_LABEL` inside `st.form`.
- [ ] `tests/test_ai_follow_up_ui.py::test_empty_summary_renders_nothing`: spec behaviour 5 — no form and no request when the summary is empty.
- [ ] `tests/test_ai_follow_up_ui.py::test_empty_question_shows_message_and_keeps_history`: spec behaviour 6 — `EMPTY_QUESTION_MESSAGE`, no chat call, history unchanged.
- [ ] `tests/test_ai_follow_up_ui.py::test_answer_is_displayed_and_stored`: spec behaviour 7 — answer shown and the `{"question", "answer"}` turn appended, prompt grounded in summary and question (spec 8).
- [ ] `tests/test_ai_follow_up_ui.py::test_stored_turns_are_rendered_on_rerun`: spec behaviour 14 — stored turns render on the next run.
- [ ] `tests/test_ai_follow_up_ui.py::test_turns_from_another_summary_are_discarded`: spec behaviour 15 — stale turns neither rendered nor kept.
- [ ] `tests/test_ai_follow_up_ui.py::test_missing_config_shows_message_and_keeps_history` and `::test_empty_response_shows_message`: spec behaviour 11 and 12 — visible message, no request, no escape, history unchanged.
- [ ] `tests/test_ai_follow_up_ui.py::test_chat_error_shows_message_and_keeps_history`: spec behaviour 12 — `AISummaryError` is caught and shown.
- [ ] `tests/test_ai_follow_up_ui.py::test_missing_rounds_note_is_sent_and_answer_displayed`: spec behaviour 13 — `MISSING_ROUNDS_NOTE` inside the prompt, answer still displayed.
- [ ] `tests/test_ai_follow_up_ui.py::test_english_language_uses_english_system_message`: spec behaviour 10 — English system message and instruction from `LANGUAGE_SELECTOR_KEY`.
- [ ] Phase 1 and Phase 2 tests still pass unmodified.

**Verify:**
```bash
uv run pytest tests/test_ai_follow_up_ui.py tests/test_ai_follow_up_logic.py tests/test_ai_season_summary_return.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 4: League page wiring
<!-- phase: 4 -->
<!-- targets: pages/3_🏆_League.py, tests/test_league_follow_up_wiring.py -->
<!-- frozen: ai_summary.py, tests/test_ai_follow_up_ui.py, tests/test_ai_follow_up_logic.py, tests/test_ai_season_summary_return.py, tests/test_league_deep_dive_wiring.py -->

**Goal:** The League page hands `render_season_summary`'s non-empty return value to `render_follow_up_questions` directly below the summary call and nowhere else.

**Changes:**
- `pages/3_🏆_League.py`: find the single existing call to `render_season_summary(player_name, season_rounds)` and replace just that statement with these three lines, keeping the page's current indentation:

```python
summary = render_season_summary(player_name, season_rounds)
if summary:
    render_follow_up_questions(player_name, season_rounds, summary)
```

- `pages/3_🏆_League.py`: keep the existing import style, extending it with the new name. If the page currently has `from ai_summary import render_season_summary`, change that line to `from ai_summary import render_follow_up_questions, render_season_summary`; if it calls `ai_summary.render_season_summary(...)`, leave the import alone and call `ai_summary.render_follow_up_questions(player_name, season_rounds, summary)` inside the `if summary:` block. Read the page's existing import line and mirror it exactly; change nothing else in the page.
- `tests/test_league_follow_up_wiring.py` (new), source-inspection only, no Streamlit runtime:

```python
import re
from pathlib import Path

LEAGUE_PAGE = Path(__file__).resolve().parents[1] / "pages" / "3_🏆_League.py"
SOURCE = LEAGUE_PAGE.read_text(encoding="utf-8")
LINES = SOURCE.splitlines()


def line_indexes(pattern: str) -> list[int]:
    return [index for index, line in enumerate(LINES) if re.search(pattern, line)]


def follow_up_call_indexes() -> list[int]:
    return [
        index
        for index in line_indexes(r"\brender_follow_up_questions\(")
        if not LINES[index].lstrip().startswith(("from ", "import "))
    ]
```

Tests in that file:
- `test_summary_return_value_is_passed_to_follow_up_fragment`: `assignment = line_indexes(r"^\s*summary\s*=\s*.*render_season_summary\(")`; `calls = follow_up_call_indexes()`; assert both non-empty, `min(calls) > min(assignment)`, and `re.search(r"render_follow_up_questions\(\s*player_name\s*,\s*season_rounds\s*,\s*summary\s*\)", LINES[min(calls)])` (spec 3).
- `test_follow_up_call_is_guarded_by_non_empty_summary`: `guards = line_indexes(r"^if summary:\s*$")`; assert `guards` is non-empty and `min(follow_up_call_indexes()) > min(guards)`, and that the call line's indentation is greater than the guard line's indentation — computed as `len(LINES[i]) - len(LINES[i].lstrip())` for each (spec 3 and spec 5 at page level).

**Definition of done:**
- [ ] `tests/test_league_follow_up_wiring.py::test_summary_return_value_is_passed_to_follow_up_fragment`: spec behaviour 3 — the returned summary is assigned to `summary` and passed as the third argument to `render_follow_up_questions` on a later line.
- [ ] `tests/test_league_follow_up_wiring.py::test_follow_up_call_is_guarded_by_non_empty_summary`: spec behaviours 3 and 5 — the fragment call sits inside `if summary:`, so an empty summary renders nothing and attempts no request.
- [ ] The pre-existing page wiring test still passes unmodified: `tests/test_league_deep_dive_wiring.py` (spec 16).
- [ ] Phase 3's fragment tests still pass unmodified.

**Verify:**
```bash
uv run pytest tests/test_league_follow_up_wiring.py tests/test_league_deep_dive_wiring.py tests/test_ai_follow_up_ui.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- An existing AI-summary test may assert that `render_season_summary` returns `None` instead of `""`. Phase 1's Verify re-runs `tests/test_ai_season_summary.py`, `tests/test_ai_summary_logic.py`, `tests/test_ai_summary_language_logic.py` and `tests/test_ai_summary_language_ui.py`, so this fails at the first gate.
- `@st.fragment`'s wrapper may expect a Streamlit script-run context. Phase 3's tests call the function through its `__wrapped__` attribute when present, and `test_fragment_decorator_is_present` separately proves the decorator is there in the source; no real runtime is needed.
- Real `st.session_state` is not usable outside a Streamlit run. Every fragment/history test replaces `ai_summary.st` with a `MagicMock` whose `session_state` is a plain dict, so no runtime session state is touched.
- Conversations leaking between seasons or growing unbounded. Phase 2's `::test_history_is_discarded_when_summary_differs` and `::test_prompt_keeps_only_the_newest_history_turns` cover the reset and the 6-turn window; Phase 3's `::test_turns_from_another_summary_are_discarded` covers rendering.
- `clear_on_submit=True` dropping the submitted text before it is used. Phase 3's `::test_answer_is_displayed_and_stored` proves the submitted question is the one sent and stored.
- The League page's import style or call-site variable name differing from the assumption. Phase 4's tests assert the assignment, the guard and the argument order by source inspection, and Phase 4's Verify includes the frozen `tests/test_league_deep_dive_wiring.py` so nothing else on the page moves.
- Prompt construction breaking on a DataFrame or on `None` rounds. Phase 2's `::test_prompt_accepts_a_dataframe_and_lists_each_row`, `::test_prompt_notes_missing_rounds` and `::test_prompt_never_raises` cover these.
- Behaviour 16 (whole suite + `behave`) is only fully proven by the pipeline's final whole-suite run; each phase's Verify keeps its own slice green in the meantime.

## Open questions
- `st.form` requires a key but the spec's constant list has none: assumption — add `FOLLOW_UP_FORM_KEY: str = "ai_season_follow_up_form"` to `ai_summary.py` in Phase 3. Nothing else is added beyond the spec's list; the spinner text "正在生成回答…" stays an inline literal.
- The League page's exact import style is not in the approved documents: assumption — the builder extends whatever import form the page already uses, and the wiring test checks the call site, its guard and its arguments rather than the import line.
- The League page's local variable holding the summary is not in the approved documents: assumption — it is named `summary`, matching the spec's call-site snippet, and the Phase 4 test requires that name.
- Persistence across reruns is proven with a plain-dict `session_state` double rather than a live Streamlit session: assumption — that is sufficient evidence that the value is stored under `FOLLOW_UP_HISTORY_KEY` and re-read, since both the real widget reruns and the tests call the same function.

## Hand back

When every phase is built and its Verify block passes:
1. Create `sdlc/features/007-follow-up-q-a-under-the/build-log.md` with one section per phase, in order. Head each one `## Phase <n>: <title>`, then list the files changed, the Verify command you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/007-follow-up-q-a-under-the`.

Commit only this plan's targets and `build-log.md`. Leave every other file alone, including other features' documents under `sdlc/features/`, even for formatting; verification fails on any file outside the targets.

The pipeline waits for this file. Once it has a section for every phase, it verifies the whole branch and opens the pull request.
