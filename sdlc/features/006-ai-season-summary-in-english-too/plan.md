<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@293fa2a -->
## Approach
Add a `normalize_language` helper plus the English constants to `ai_summary.py`, and give `build_summary_prompt`, `_call_ollama_chat` and `summarize_season` an optional `language` argument that defaults to 中文, so every existing caller and stub keeps the byte-identical Chinese path (still called with three positional arguments) while the English path reuses the exact same round lines and swaps only `SYSTEM_MESSAGE_EN`, the fixed labels and `PROMPT_INSTRUCTION_EN`. Then change only `render_season_summary` to draw `st.radio(LANGUAGE_SELECTOR_LABEL, options=LANGUAGE_OPTIONS, index=0, key=LANGUAGE_SELECTOR_KEY, horizontal=True)` in a left-hand `st.columns` cell beside the unchanged `🤖 AI 赛季总结` button, pass the selected value straight into `summarize_season`, and render the result with `st.markdown` — with no caching, so changing the selector without pressing the button shows nothing.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| A 中文 / English choice appears immediately beside the 🤖 AI 赛季总结 button in the season summary section, with 中文 pre-selected. | 1 (selector options/order/default/position beside button), 2 (empty player name renders nothing), 12 (change without press does nothing) | Phase 2 |
| Generating a summary with 中文 selected yields the same Chinese summary behaviour as before this change. | 3 (Chinese request uses `SYSTEM_MESSAGE` + `build_summary_prompt(...)`), 13 (no-language call unchanged), 5 (English prompt shares Chinese round data), 14 (unsupported language falls back to 中文) | Phase 1 (prompt/logic + byte-identical Chinese prompt), Phase 2 (render path) |
| Generating a summary with English selected yields a season summary written in English. | 4 (`SYSTEM_MESSAGE_EN` + English prompt + `st.markdown`), 5 (same round data), 6 (DataFrame rows), 9 (no rounds), 10 (missing config), 11 (call failure / empty response) | Phase 1 (4, 5, 6, 9, 10, 11 at logic level), Phase 2 (4 and error paths at render level) |
| Changing the choice and generating again produces the summary in the newly selected language. | 7 (switch without press shows nothing), 8 (press after switch uses new language) | Phase 2 |
| The existing tests still pass. | 13, 14, and all Chinese-path behaviours (1–12) preserved for the default selection | Phase 1, Phase 2 |

## Phase 1: Bilingual prompt and summary logic

<!-- phase: 1 -->
<!-- targets: ai_summary.py, tests/test_ai_summary_language_logic.py -->
<!-- frozen: tests/test_ai_season_summary.py, tests/test_ai_summary_logic.py, tests/test_league_deep_dive_wiring.py, streamlit_app.py, pages/** -->

**Goal:** `build_summary_prompt` and `summarize_season` produce byte-identical Chinese output when no language is given and an English prompt/system message when `language="English"`, with every other pre-existing public function unchanged.

**Changes:**

- `ai_summary.py`: insert these new module constants immediately after the existing `CALL_FAILED_MESSAGE` definition and before `class AISummaryError`, keeping `SYSTEM_MESSAGE`, `PROMPT_INSTRUCTION`, `AI_SUMMARY_BUTTON_LABEL`, `OLLAMA_CHAT_URL`, `OLLAMA_API_KEY_SECRET`, `OLLAMA_MODEL_SECRET`, `REQUEST_TIMEOUT_SECONDS`, `MISSING_CONFIG_MESSAGE`, `NO_ROUNDS_MESSAGE`, `EMPTY_RESPONSE_MESSAGE` and `CALL_FAILED_MESSAGE` exactly as they are:

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

- `ai_summary.py`: add this new function directly above `build_summary_prompt`:

```python
def normalize_language(language: str | None) -> str:
    """Return LANGUAGE_ENGLISH only for LANGUAGE_ENGLISH, otherwise LANGUAGE_CHINESE. Never raises."""
    if language == LANGUAGE_ENGLISH:
        return LANGUAGE_ENGLISH
    return LANGUAGE_CHINESE
```

- `ai_summary.py`: replace `build_summary_prompt` with the following. The Chinese branch must keep the existing literal strings, order and `"；"` field separator character-for-character, so its output is byte-identical to before; the English branch must keep the same `key=value` pairs, the same separator and the same number of round lines, changing only the player-name label, the rounds header, the `Round {n}: ` prefix and the trailing instruction:

```python
def build_summary_prompt(
    player_name: str,
    season_rounds: list[dict],
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Return the chat prompt containing only this player's name and rounds, written in the selected language."""
    rounds = season_rounds
    if hasattr(rounds, "to_dict"):
        rounds = rounds.to_dict(orient="records")
    english = normalize_language(language) == LANGUAGE_ENGLISH
    if english:
        lines = [
            f"Player name: {player_name}",
            "This player's rounds this season (one line per round):",
        ]
    else:
        lines = [f"球员姓名：{player_name}", "该球员本赛季的比赛轮次数据（每一行是一轮）："]
    for index, record in enumerate(rounds, start=1):
        fields = "；".join(f"{key}={value}" for key, value in dict(record).items())
        lines.append(f"Round {index}: {fields}" if english else f"第 {index} 轮：{fields}")
    lines.append(PROMPT_INSTRUCTION_EN if english else PROMPT_INSTRUCTION)
    return "\n".join(lines)
```

- `ai_summary.py`: change `_call_ollama_chat` to take a fourth keyword-only-in-practice parameter and use it for the system message; the payload dict, URL, headers, timeout handling, JSON parsing and exception messages are otherwise unchanged:

```python
def _call_ollama_chat(
    api_key: str,
    model: str,
    prompt: str,
    system_message: str = SYSTEM_MESSAGE,
) -> str:
    """Single seam for the outbound Ollama Cloud chat request; never reads secrets."""
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
    }
```

  Keep the rest of the function body (the `urllib.request.Request`, the `AISummaryError` re-raise, `json.loads`, the emptiness check and `return content.strip()`) exactly as it is today.

- `ai_summary.py`: replace `summarize_season` with the following, preserving the existing config → round-count → request → empty-response ordering and the double `.strip()` guard. The Chinese branch must call `_call_ollama_chat` with exactly three positional arguments (no `system_message` keyword) so existing stubs such as `lambda api_key, model, prompt: ...` keep working:

```python
def summarize_season(
    player_name: str,
    season_rounds: list[dict],
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Return the season summary for one player in the selected language, or raise AISummaryError."""
    api_key, model = get_ai_config()
    if not api_key or not model:
        raise AISummaryError(MISSING_CONFIG_MESSAGE)
    if _round_count(season_rounds) == 0:
        raise AISummaryError(NO_ROUNDS_MESSAGE)
    selected = normalize_language(language)
    prompt = build_summary_prompt(player_name, season_rounds, selected)
    if selected == LANGUAGE_ENGLISH:
        text = _call_ollama_chat(api_key, model, prompt, system_message=SYSTEM_MESSAGE_EN)
    else:
        text = _call_ollama_chat(api_key, model, prompt)
    if not text or not text.strip():
        raise AISummaryError(EMPTY_RESPONSE_MESSAGE)
    return text.strip()
```

- `ai_summary.py`: do **not** touch `get_ai_config`, `is_ai_configured`, `_round_count`, `AISummaryError` or `render_season_summary` in this phase. `render_season_summary` keeps calling `summarize_season(player_name, season_rounds)`, i.e. the Chinese default.
- `tests/test_ai_summary_language_logic.py` (new file): add `from __future__ import annotations`, `import pandas as pd`, `import pytest`, `import ai_summary`, then the module-level fixture data and tests below. Every test stubs `ai_summary._call_ollama_chat` and `ai_summary.get_ai_config` with `monkeypatch.setattr`; nothing reads `st.secrets`, touches the network or starts a thread, and `monkeypatch` restores all attributes automatically, so no other teardown is needed.

  Shared data at module level:

```python
ROUNDS: list[dict] = [{"score": 80, "birdies": 2}, {"score": 75, "birdies": 3}]
CHINESE_PROMPT: str = (
    "球员姓名：Jacky\n"
    "该球员本赛季的比赛轮次数据（每一行是一轮）：\n"
    "第 1 轮：score=80；birdies=2\n"
    "第 2 轮：score=75；birdies=3\n"
    + ai_summary.PROMPT_INSTRUCTION
)
```

  A recording stub helper used by the `summarize_season` tests:

```python
@pytest.fixture
def ollama_stub(monkeypatch):
    calls: list[tuple[tuple, dict]] = []

    def fake_call(*args, **kwargs):
        calls.append((args, kwargs))
        return "  中文总结  "

    monkeypatch.setattr(ai_summary, "_call_ollama_chat", fake_call)
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("key", "model"))
    return calls
```

**Definition of done:**

- [ ] `tests/test_ai_summary_language_logic.py::test_chinese_prompt_unchanged_without_language_argument`: asserts `ai_summary.build_summary_prompt("Jacky", ROUNDS) == CHINESE_PROMPT` and `ai_summary.build_summary_prompt("Jacky", ROUNDS, language="中文") == CHINESE_PROMPT` (spec 3, 13 — proves the no-language call is byte-identical to the pre-change output, taken from the literal approved-tag behaviour).
- [ ] `tests/test_ai_summary_language_logic.py::test_english_prompt_keeps_chinese_round_lines_and_english_labels`: builds `zh = ai_summary.build_summary_prompt("Jacky", ROUNDS)` and `en = ai_summary.build_summary_prompt("Jacky", ROUNDS, language="English")`; asserts `en.split("\n")[0] == "Player name: Jacky"`, `len(en.split("\n")) == len(zh.split("\n"))`, `en.split("\n")[-1] == ai_summary.PROMPT_INSTRUCTION_EN`, `zh.split("\n")[-1] == ai_summary.PROMPT_INSTRUCTION`, and that for each round line the field text is identical: `zh.split("\n")[2 + i].split("：", 1)[1] == en.split("\n")[2 + i].split(": ", 1)[1]` for `i in range(2)`, which equals `"score=80；birdies=2"` and `"score=75；birdies=3"` (spec 5).
- [ ] `tests/test_ai_summary_language_logic.py::test_english_prompt_from_dataframe_has_one_line_per_row`: builds `df = pd.DataFrame([{"score": 80, "birdies": 2}, {"score": 78, "birdies": 1}, {"score": 82, "birdies": 0}])`, calls `ai_summary.build_summary_prompt("Jacky", df, language="English")`, asserts exactly three lines start with `"Round "`, that `"Round 2: score=78；birdies=1"` is in the prompt, and that the number of lines equals the header lines plus three round lines plus the instruction (6 lines total) (spec 6).
- [ ] `tests/test_ai_summary_language_logic.py::test_unsupported_language_falls_back_to_chinese`: asserts `ai_summary.normalize_language("English") == "English"` and `ai_summary.normalize_language(value) == "中文"` for `"fr"`, `""`, `None`; and that `ai_summary.build_summary_prompt("Jacky", ROUNDS, language="fr") == CHINESE_PROMPT` and `ai_summary.summarize_season("Jacky", ROUNDS, language="fr")` (with the stub installed) returns the stubbed Chinese text rather than raising (spec 14).
- [ ] `tests/test_ai_summary_language_logic.py::test_summarize_season_chinese_calls_ollama_with_three_positional_arguments`: with the `ollama_stub` fixture, asserts `ai_summary.summarize_season("Jacky", ROUNDS) == "中文总结"` (the stub's value stripped), `ollama_stub == [(("key", "model", ai_summary.build_summary_prompt("Jacky", ROUNDS)), {})]` — proving exactly three positional arguments and no `system_message` keyword (spec 3, 13).
- [ ] `tests/test_ai_summary_language_logic.py::test_summarize_season_english_uses_english_system_message`: with the `ollama_stub` fixture, asserts `ai_summary.summarize_season("Jacky", ROUNDS, language="English") == "中文总结"`, `ollama_stub[0][0] == ("key", "model", ai_summary.build_summary_prompt("Jacky", ROUNDS, language="English"))` and `ollama_stub[0][1] == {"system_message": ai_summary.SYSTEM_MESSAGE_EN}` (spec 4).
- [ ] `tests/test_ai_summary_language_logic.py::test_summarize_season_no_rounds_raises_before_request`: parametrized over `([], None, pd.DataFrame(columns=["score"]))` × `("中文", "English")`; with `ai_summary.get_ai_config` monkeypatched to `lambda: ("key", "model")` and a call-recording `_call_ollama_chat`, asserts `pytest.raises(ai_summary.AISummaryError)` with `str(exc.value) == ai_summary.NO_ROUNDS_MESSAGE` and zero recorded calls (spec 9).
- [ ] `tests/test_ai_summary_language_logic.py::test_summarize_season_missing_config_raises_missing_config_message`: parametrized over `(("", ""), ("key", ""), ("", "model"))`, monkeypatches `get_ai_config` to return that pair, calls `summarize_season("Jacky", ROUNDS, language="English")`, asserts `AISummaryError` with message `ai_summary.MISSING_CONFIG_MESSAGE` and zero recorded `_call_ollama_chat` calls (spec 10).
- [ ] `tests/test_ai_summary_language_logic.py::test_summarize_season_propagates_call_failure`: stubs `get_ai_config` → `("key", "model")` and `_call_ollama_chat` to `raise ai_summary.AISummaryError(ai_summary.CALL_FAILED_MESSAGE.format(detail="HTTP 500"))`; asserts `pytest.raises(ai_summary.AISummaryError)` with exactly that message for `language="English"` (spec 11).
- [ ] `tests/test_ai_summary_language_logic.py::test_summarize_season_empty_response_raises`: same config stub, `_call_ollama_chat` returns `"   "`; asserts `pytest.raises(ai_summary.AISummaryError)` with message `ai_summary.EMPTY_RESPONSE_MESSAGE` for `language="English"` (spec 11).
- [ ] Observable: the frozen pre-existing AI tests still pass unchanged: `python -m pytest tests/test_ai_summary_logic.py tests/test_ai_season_summary.py -v` exits 0 without this phase editing either file (spec 13).

**Verify:**
```bash
python -m pytest tests/test_ai_summary_language_logic.py -v
python -m pytest tests/test_ai_summary_logic.py tests/test_ai_season_summary.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Language selector beside the AI button

<!-- phase: 2 -->
<!-- targets: ai_summary.py, tests/test_ai_summary_language_ui.py -->
<!-- frozen: tests/test_ai_summary_language_logic.py, tests/test_ai_season_summary.py, tests/test_ai_summary_logic.py, tests/test_league_deep_dive_wiring.py, streamlit_app.py, pages/** -->

**Goal:** `render_season_summary` draws the 中文/English selector to the left of the unchanged button with 中文 selected, and a button press renders the summary in the currently selected language or the matching readable error.

**Changes:**

- `ai_summary.py`: replace only the body of `render_season_summary` with the version below. The signature stays `render_season_summary(player_name: str, season_rounds: list[dict]) -> None`, the early `return` for an empty `player_name` stays before any rendering, and the button keeps the label `AI_SUMMARY_BUTTON_LABEL` and `key="ai_summary_season_summary_button"`… precisely: `key="ai_season_summary_button"`. Nothing is cached, so a rerun triggered by changing the radio re-renders nothing until the button is pressed again:

```python
def render_season_summary(player_name: str, season_rounds: list[dict]) -> None:
    """Render the language selector beside the '🤖 AI 赛季总结' button and, after a press, the summary or a readable error."""
    if not player_name:
        return
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
        return
    if _round_count(season_rounds) == 0:
        st.warning(NO_ROUNDS_MESSAGE)
        return
    with st.spinner("正在生成赛季总结…"):
        try:
            summary = summarize_season(player_name, season_rounds, language)
        except AISummaryError as exc:
            st.error(str(exc))
        else:
            st.markdown(summary)
```

- `tests/test_ai_summary_language_ui.py` (new file): `from __future__ import annotations`, `import pytest`, `import ai_summary`. Because the app's rendering entry point takes plain arguments, the tests drive `render_season_summary` directly with a hand-rolled fake `st` module, so no Streamlit runtime, server, secrets, network or threads are involved; `monkeypatch.setattr` restores `ai_summary.st`, `ai_summary.get_ai_config` and `ai_summary._call_ollama_chat` after every test.

  Fake Streamlit helpers (verbatim):

```python
class Recorder:
    def __init__(self, button_pressed: bool = False, radio_value: str | None = None) -> None:
        self.calls: list[dict] = []
        self.button_pressed = button_pressed
        self.radio_value = radio_value
        self.current_column: int | None = None

    def record(self, method: str, args: tuple, kwargs: dict) -> None:
        self.calls.append(
            {"column": self.current_column, "method": method, "args": args, "kwargs": kwargs}
        )

    def all(self, method: str) -> list[dict]:
        return [call for call in self.calls if call["method"] == method]


class FakeColumn:
    def __init__(self, recorder: Recorder, index: int) -> None:
        self._recorder = recorder
        self._index = index

    def __enter__(self):
        self._recorder.current_column = self._index
        return self

    def __exit__(self, exc_type, exc, tb):
        self._recorder.current_column = None
        return False


class FakeSpinner:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeStreamlit:
    def __init__(self, recorder: Recorder) -> None:
        self._recorder = recorder

    def columns(self, spec, gap=None):
        count = spec if isinstance(spec, int) else len(spec)
        self._recorder.record("columns", (spec,), {})
        return tuple(FakeColumn(self._recorder, index) for index in range(count))

    def radio(self, label, options=None, index=0, key=None, horizontal=False):
        value = self._recorder.radio_value
        if value is None:
            value = options[index]
        self._recorder.record(
            "radio",
            (label,),
            {
                "options": options,
                "index": index,
                "key": key,
                "horizontal": horizontal,
                "value": value,
            },
        )
        return value

    def button(self, label, key=None, **kwargs):
        self._recorder.record("button", (label,), {"key": key})
        return self._recorder.button_pressed

    def spinner(self, text):
        self._recorder.record("spinner", (text,), {})
        return FakeSpinner()

    def markdown(self, text, **kwargs):
        self._recorder.record("markdown", (text,), kwargs)

    def warning(self, text, **kwargs):
        self._recorder.record("warning", (text,), kwargs)

    def error(self, text, **kwargs):
        self._recorder.record("error", (text,), kwargs)
```

  Fixtures and shared data:

```python
ROUNDS: list[dict] = [{"score": 80, "birdies": 2}, {"score": 75, "birdies": 3}]


@pytest.fixture
def install_fake_st(monkeypatch):
    def _install(button_pressed: bool = False, radio_value: str | None = None) -> Recorder:
        recorder = Recorder(button_pressed=button_pressed, radio_value=radio_value)
        monkeypatch.setattr(ai_summary, "st", FakeStreamlit(recorder))
        return recorder

    return _install


@pytest.fixture
def ollama_stub(monkeypatch):
    calls: list[tuple[tuple, dict]] = []

    def fake_get_ai_config():
        return ("key", "model")

    def fake_call(*args, **kwargs):
        calls.append((args, kwargs))
        if kwargs.get("system_message") == ai_summary.SYSTEM_MESSAGE_EN:
            return "EN-SUMMARY"
        return "ZH-SUMMARY"

    monkeypatch.setattr(ai_summary, "get_ai_config", fake_get_ai_config)
    monkeypatch.setattr(ai_summary, "_call_ollama_chat", fake_call)
    return calls
```

**Definition of done:**

- [ ] `tests/test_ai_summary_language_ui.py::test_selector_renders_beside_button_with_chinese_preselected`: `recorder = install_fake_st(button_pressed=False)` then `ai_summary.render_season_summary("Jacky", ROUNDS)`; asserts exactly one `radio` call with `args == (ai_summary.LANGUAGE_SELECTOR_LABEL,)`, `kwargs["options"] == ("中文", "English")`, `kwargs["index"] == 0`, `kwargs["key"] == ai_summary.LANGUAGE_SELECTOR_KEY`, `kwargs["horizontal"] is True`, `kwargs["value"] == "中文"`, and `column == 0`; exactly one `button` call with `args == (ai_summary.AI_SUMMARY_BUTTON_LABEL,)`, `kwargs["key"] == "ai_season_summary_button"` and `column == 1` (proving the same-row cell immediately to the left); and `recorder.all("markdown") == []` (spec 1).
- [ ] `tests/test_ai_summary_language_ui.py::test_empty_player_name_renders_nothing`: `recorder = install_fake_st(button_pressed=True)` then `ai_summary.render_season_summary("", ROUNDS)`; asserts `recorder.calls == []` — no selector, no button, no summary (spec 2).
- [ ] `tests/test_ai_summary_language_ui.py::test_english_summary_rendered_with_markdown`: with `ollama_stub`, `install_fake_st(button_pressed=True, radio_value="English")`, `ai_summary.render_season_summary("Jacky", ROUNDS)`; asserts `recorder.all("markdown")[0]["args"] == ("EN-SUMMARY",)`, `recorder.all("error") == []`, and that the single recorded request was `(("key", "model", ai_summary.build_summary_prompt("Jacky", ROUNDS, language="English")), {"system_message": ai_summary.SYSTEM_MESSAGE_EN})` (spec 4).
- [ ] `tests/test_ai_summary_language_ui.py::test_switching_language_without_press_clears_summary_and_skips_request`: with `ollama_stub`, first `install_fake_st(button_pressed=True, radio_value="中文")` and render → `markdown` recorded `"ZH-SUMMARY"` and one request; then install a fresh recorder with `button_pressed=False, radio_value="English"` and render again; asserts the new recorder has no `markdown` call and that the `ollama_stub` request count is still 1, proving no request and nothing displayed after a pure selector change (spec 7, 12).
- [ ] `tests/test_ai_summary_language_ui.py::test_pressing_after_switching_renders_new_language_summary`: with `ollama_stub`, run the sequence "English + pressed" then "中文 + pressed", reinstalling a fresh recorder (and leaving the shared `ollama_stub`) before each render; asserts the first run rendered `"EN-SUMMARY"` with `system_message=SYSTEM_MESSAGE_EN`, the second rendered `"ZH-SUMMARY"` with `kwargs == {}` and the Chinese prompt argument (spec 8).
- [ ] `tests/test_ai_summary_language_ui.py::test_no_rounds_shows_warning_and_skips_request`: with `ollama_stub`, `install_fake_st(button_pressed=True, radio_value="English")`, `ai_summary.render_season_summary("Jacky", [])`; asserts `recorder.all("warning")[0]["args"] == (ai_summary.NO_ROUNDS_MESSAGE,)`, `recorder.all("markdown") == []` and `ollama_stub == []` (spec 9).
- [ ] `tests/test_ai_summary_language_ui.py::test_missing_config_shows_error_without_request`: monkeypatch `ai_summary.get_ai_config` to `lambda: ("", "")` and `ai_summary._call_ollama_chat` to a recorder, `install_fake_st(button_pressed=True, radio_value="English")`, render with `ROUNDS`; asserts `recorder.all("error")[0]["args"] == (ai_summary.MISSING_CONFIG_MESSAGE,)`, no `markdown` call and zero chat calls (spec 10).
- [ ] `tests/test_ai_summary_language_ui.py::test_call_failure_shows_error_and_no_markdown`: parametrized over `ai_summary.CALL_FAILED_MESSAGE.format(detail="HTTP 500")` and `ai_summary.EMPTY_RESPONSE_MESSAGE`; monkeypatches `get_ai_config` → `("key", "model")`, `_call_ollama_chat` to raise `ai_summary.AISummaryError(message)`, `install_fake_st(button_pressed=True, radio_value="English")`, renders with `ROUNDS`; asserts `recorder.all("error")[0]["args"] == (message,)` and `recorder.all("markdown") == []` (spec 11).
- [ ] Observable: the frozen tests, including the phase-1 logic tests and the pre-existing render/wiring tests, still pass unchanged: `python -m pytest tests/test_ai_summary_language_logic.py tests/test_ai_season_summary.py tests/test_ai_summary_logic.py tests/test_league_deep_dive_wiring.py -v` exits 0 without any of those files being edited.

**Verify:**
```bash
python -m pytest tests/test_ai_summary_language_ui.py -v
python -m pytest tests/test_ai_summary_language_logic.py tests/test_ai_season_summary.py tests/test_ai_summary_logic.py tests/test_league_deep_dive_wiring.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- **The existing `st`-faking tests break on `st.columns`/`st.radio`.** `tests/test_ai_season_summary.py` may stub `streamlit` with an object that lacks `columns` or `radio`, or assert a fixed call sequence. Caught by the frozen-test command in Phase 2's Verify block; if it fails, stop and revise this plan rather than editing the frozen test.
- **Chinese path stops being byte-identical.** Any reordering of the Chinese prompt lines, a changed separator, or passing `system_message` explicitly on the Chinese path would change behaviour or break stubs written as `lambda api_key, model, prompt: ...`. Caught by Phase 1's exact-string test, the three-positional-argument assertion, and the frozen tests.
- **Summary caching sneaks in.** Storing a generated summary in `st.session_state` would leave stale text on screen after a selector change (spec 7). Caught by Phase 2's `test_switching_language_without_press_clears_summary_and_skips_request`.
- **A language value leaks past `normalize_language`.** Passing the raw radio value (or an unsupported string) into the English branch could select the wrong prompt. Caught by Phase 1's fallback test and Phase 2's recorded request payloads.
- **DataFrame input regresses.** Moving the `to_dict(orient="records")` conversion or renaming the `season_rounds` parameter would break dashboard callers that pass a DataFrame. Caught by Phase 1's DataFrame prompt test and the frozen `tests/test_league_deep_dive_wiring.py`.
- **pandas import in the test file.** The DataFrame test needs pandas; it is an existing app dependency, and a missing install fails the phase loudly instead of being skipped.

## Open questions
None. The spec's assumptions are adopted verbatim: the selector applies only inside `render_season_summary`, it resets to 中文 on reload or a new session, the English prompt reuses the Chinese data lines and round count, a selector change without a button press displays nothing, unsupported language values fall back to 中文, and the selector sits in the cell to the left of the button.

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/006-ai-season-summary-in-english-too/build-log.md` with one section per phase, in order. Head each one `## Phase <n>: <title>`, then list the files changed, the Verify command you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/006-ai-season-summary-in-english-too`.

Commit only this plan's targets and `build-log.md`. Leave every other file alone, including other features' documents under `sdlc/features/`, even for formatting; verification fails on any file outside the targets.
