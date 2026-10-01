<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@b1ba221 -->
## Approach
Add one new module `ai_summary.py` at the repository root that reads `OLLAMA_API_KEY`/`OLLAMA_MODEL` from `st.secrets` with the guarded pattern from `auth.py`, builds a Chinese-prose prompt from the selected player's own season rounds, calls the Ollama Cloud chat endpoint over stdlib `urllib.request` (no new dependency), and renders a `🤖 AI 赛季总结` button plus the resulting summary or a readable error; then call it from `pages/3_🏆_League.py` immediately after the deep-dive's four metrics, passing the already-selected player and their already-loaded rounds, with pytest coverage that mocks the outbound call so no credentials or network are needed.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| The "🤖 AI 赛季总结" button is rendered in the League Player Deep-Dive view, below the four metrics. | 1, 13 | Phase 2, Phase 3 |
| Pressing it shows a written season summary for the player currently selected in the deep-dive. | 2, 4, 8, 9, 10, 11, 12 | Phase 1, Phase 2, Phase 3 |
| The content sent for summarization is that player's own season rounds, not other players' data. | 5 | Phase 1, Phase 3 |
| API key and model come from `st.secrets`; no credentials are hard-coded and the app runs normally when the button is never pressed. | 3, 6, 7 | Phase 1, Phase 2 |
| Tests cover the button flow with the Ollama call mocked, and pass without credentials. | 1–13 | Phase 1, Phase 2, Phase 3 |
| The existing tests still pass. | 14 | Phase 3 |

## Phase 1: AI summary core (no UI)
<!-- phase: 1 -->
<!-- targets: ai_summary.py, tests/test_ai_summary_logic.py -->
<!-- frozen: auth.py, data.py, pages/3_🏆_League.py, test_streamlit_app.py, tests/test_announcement_page_wiring.py, tests/test_pinned_announcements.py, tests/test_pinned_winners_announcement.py, tests/test_upcoming_section_visibility.py -->

**Goal:** `ai_summary.py` produces a Chinese prompt from one player's rounds and talks to Ollama Cloud through one mockable seam, with no UI and no credential literals.

**Changes:**
- `ai_summary.py` (new file, repository root). Create exactly this module content (docstrings may be kept verbatim):

```python
"""AI season summary for the League Player Deep-Dive (Ollama Cloud chat API).

Credentials and model come from st.secrets, read with the same guarded
st.secrets.get(..., default) pattern as auth._allowed_tokens().
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

import streamlit as st

OLLAMA_CHAT_URL: str = "https://ollama.com/api/chat"
OLLAMA_API_KEY_SECRET: str = "OLLAMA_API_KEY"
OLLAMA_MODEL_SECRET: str = "OLLAMA_MODEL"
AI_SUMMARY_BUTTON_LABEL: str = "🤖 AI 赛季总结"
REQUEST_TIMEOUT_SECONDS: int = 30

SYSTEM_MESSAGE: str = "你是一名高尔夫球会的数据分析助理，请始终用简体中文写作。"
PROMPT_INSTRUCTION: str = (
    "请只根据上面这位球员自己的数据，用简体中文写一段赛季总结，"
    "2-3 个自然段，分析整体表现、亮点和需要改进的地方。"
    "不要编造数据，不要提及其他球员。"
)
MISSING_CONFIG_MESSAGE: str = "AI 服务未配置：请在 secrets 中设置 OLLAMA_API_KEY 和 OLLAMA_MODEL。"
NO_ROUNDS_MESSAGE: str = "该球员本赛季暂无比赛轮次，无法生成赛季总结。"
EMPTY_RESPONSE_MESSAGE: str = "AI 服务未返回有效内容，请稍后重试。"
CALL_FAILED_MESSAGE: str = "生成赛季总结失败，请稍后重试。（{detail}）"


class AISummaryError(Exception):
    """Raised when a season summary cannot be produced: missing config, transport failure, or empty response."""


def get_ai_config() -> tuple[str, str]:
    """Return (api_key, model) read from st.secrets; ("", "") when unavailable. Never raises."""
    try:
        api_key = st.secrets.get(OLLAMA_API_KEY_SECRET, "")
        model = st.secrets.get(OLLAMA_MODEL_SECRET, "")
    except Exception:
        return "", ""
    return str(api_key or ""), str(model or "")


def is_ai_configured() -> bool:
    """Return True only when both the API key and the model name are non-empty."""
    api_key, model = get_ai_config()
    return bool(api_key) and bool(model)


def _round_count(season_rounds) -> int:
    try:
        return len(season_rounds)
    except TypeError:
        return 0


def build_summary_prompt(player_name: str, season_rounds: list[dict]) -> str:
    """Return the chat prompt containing only this player's name and rounds."""
    rounds = season_rounds
    if hasattr(rounds, "to_dict"):
        rounds = rounds.to_dict(orient="records")
    lines = [f"球员姓名：{player_name}", "该球员本赛季的比赛轮次数据（每一行是一轮）："]
    for index, record in enumerate(rounds, start=1):
        fields = "；".join(f"{key}={value}" for key, value in dict(record).items())
        lines.append(f"第 {index} 轮：{fields}")
    lines.append(PROMPT_INSTRUCTION)
    return "\n".join(lines)


def _call_ollama_chat(api_key: str, model: str, prompt: str) -> str:
    """Single seam for the outbound Ollama Cloud chat request; never reads secrets."""
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        OLLAMA_CHAT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            status = int(getattr(response, "status", 200))
            raw = response.read()
        if status not in (200, 201):
            raise AISummaryError(CALL_FAILED_MESSAGE.format(detail=f"HTTP {status}"))
    except AISummaryError:
        raise
    except Exception as exc:  # HTTPError, URLError, timeout, socket errors
        raise AISummaryError(CALL_FAILED_MESSAGE.format(detail=str(exc))) from exc

    try:
        body = json.loads(raw.decode("utf-8"))
        content = body["message"]["content"]
    except Exception as exc:
        raise AISummaryError(CALL_FAILED_MESSAGE.format(detail="响应格式无法解析")) from exc
    if not isinstance(content, str) or not content.strip():
        raise AISummaryError(EMPTY_RESPONSE_MESSAGE)
    return content.strip()


def summarize_season(player_name: str, season_rounds: list[dict]) -> str:
    """Return the Chinese season summary for one player, or raise AISummaryError."""
    api_key, model = get_ai_config()
    if not api_key or not model:
        raise AISummaryError(MISSING_CONFIG_MESSAGE)
    if _round_count(season_rounds) == 0:
        raise AISummaryError(NO_ROUNDS_MESSAGE)
    prompt = build_summary_prompt(player_name, season_rounds)
    text = _call_ollama_chat(api_key, model, prompt)
    if not text or not text.strip():
        raise AISummaryError(EMPTY_RESPONSE_MESSAGE)
    return text.strip()
```

- No dependency change: the HTTP client is stdlib `urllib.request` (already used by `data.py`), so `pyproject.toml` and `requirements.txt` stay untouched.
- `tests/test_ai_summary_logic.py` (new file). Module-level helpers to copy verbatim into the test file:

```python
import json
import re
import urllib.error
from pathlib import Path

import pandas as pd
import pytest

import ai_summary

KEY = "key-1"
MODEL = "model-1"
ROUNDS = [
    {"Game": "Game 1", "Net_Score": -8, "Birdies": 3, "Pars": 8},
    {"Game": "Game 2", "Net_Score": 3, "Birdies": 2, "Pars": 10},
]


class _StubSecrets:
    def __init__(self, data=None, raises=False):
        self._data = data or {}
        self._raises = raises

    def get(self, key, default=None):
        if self._raises:
            raise RuntimeError("no secrets file")
        return self._data.get(key, default)


class _StubStreamlit:
    def __init__(self, secrets):
        self.secrets = secrets


class _FakeResponse:
    def __init__(self, payload: bytes, status: int = 200):
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeUrlOpen:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        if self.error is not None:
            raise self.error
        return self.response


def _use_secrets(monkeypatch, data=None, raises=False):
    secrets = _StubSecrets(data, raises=raises)
    monkeypatch.setattr(ai_summary, "st", _StubStreamlit(secrets))
```

- Tests to implement (patch `ai_summary.st` with the stub for config tests; patch `ai_summary.urllib.request.urlopen` with `_FakeUrlOpen` for transport tests; patch `ai_summary._call_ollama_chat` for `summarize_season` tests):
  - `test_get_ai_config_reads_secrets`: `_use_secrets(monkeypatch, {"OLLAMA_API_KEY": KEY, "OLLAMA_MODEL": MODEL})`; `assert ai_summary.get_ai_config() == (KEY, MODEL)`.
  - `test_get_ai_config_returns_empty_pair_when_secrets_unavailable`: `_use_secrets(monkeypatch, raises=True)`; `assert ai_summary.get_ai_config() == ("", "")`.
  - `test_get_ai_config_defaults_missing_keys_to_empty_strings`: `_use_secrets(monkeypatch, {})`; `assert ai_summary.get_ai_config() == ("", "")`.
  - `test_is_ai_configured_requires_both_values`: model only → `False`; both → `True`.
  - `test_build_summary_prompt_contains_only_this_players_name_and_fields`: `prompt = ai_summary.build_summary_prompt("刘北南", ROUNDS)`; assert `"刘北南" in prompt`; for each record, `all(str(value) in prompt for value in record.values())` and `all(str(key) in prompt for key in record)`; assert `"Jacky" not in prompt`; assert `"赛季总结" in prompt` and `"简体中文" in prompt`.
  - `test_build_summary_prompt_accepts_dataframe_input`: `prompt = ai_summary.build_summary_prompt("刘北南", pd.DataFrame(ROUNDS))`; assert `"Game 1" in prompt` and `"-8" in prompt`.
  - `test_summarize_season_passes_secrets_values_and_prompt_to_transport`: `_use_secrets(monkeypatch, {"OLLAMA_API_KEY": "key-2", "OLLAMA_MODEL": "model-2"})`; record args with a `calls: list[tuple]` fake `monkeypatch.setattr(ai_summary, "_call_ollama_chat", lambda api_key, model, prompt: calls.append((api_key, model, prompt)) or "总结文本")`; `assert ai_summary.summarize_season("刘北南", ROUNDS) == "总结文本"`; `assert calls[0][0] == "key-2"` and `calls[0][1] == "model-2"` and `calls[0][2] == ai_summary.build_summary_prompt("刘北南", ROUNDS)`.
  - `test_summarize_season_raises_when_config_missing`: secrets stub with `{}`; counting fake for `_call_ollama_chat`; `pytest.raises(ai_summary.AISummaryError)`; assert `ai_summary.MISSING_CONFIG_MESSAGE in str(excinfo.value)`; assert fake not called.
  - `test_summarize_season_raises_and_skips_transport_when_no_rounds`: configured secrets; counting fake; `summarize_season("刘北南", [])` raises with `NO_ROUNDS_MESSAGE`; fake not called.
  - `test_summarize_season_raises_on_blank_transport_response`: configured secrets; `_call_ollama_chat` returns `"   "`; raises with `EMPTY_RESPONSE_MESSAGE`.
  - `test_summarize_season_propagates_transport_error`: configured secrets; `_call_ollama_chat` raises `ai_summary.AISummaryError(ai_summary.CALL_FAILED_MESSAGE.format(detail="boom"))`; assert `"boom" in str(excinfo.value)`.
  - `test_call_ollama_chat_posts_expected_payload_and_returns_content`: `fake = _FakeUrlOpen(response=_FakeResponse(json.dumps({"message": {"content": "你好"}}).encode("utf-8"), status=200))`; `monkeypatch.setattr(ai_summary.urllib.request, "urlopen", fake)`; assert return `== "你好"`; decode `fake.requests[0][0].data` as JSON and assert `payload["model"] == MODEL`, `payload["stream"] is False`, `payload["messages"][0]["role"] == "system"`, `payload["messages"][-1]["content"] == "提示"`; assert `fake.requests[0][0].full_url == ai_summary.OLLAMA_CHAT_URL`, `fake.requests[0][0].get_method() == "POST"`, header `Authorization == f"Bearer {KEY}"` and `Content-Type == "application/json"`, and `fake.requests[0][1] == ai_summary.REQUEST_TIMEOUT_SECONDS`.
  - `test_call_ollama_chat_raises_on_http_error`: `_FakeUrlOpen(error=urllib.error.HTTPError(ai_summary.OLLAMA_CHAT_URL, 401, "Unauthorized", {}, None))` → `pytest.raises(ai_summary.AISummaryError)`.
  - `test_call_ollama_chat_raises_on_non_success_status`: `_FakeResponse(b"{}", status=500)` → `AISummaryError`.
  - `test_call_ollama_chat_raises_on_malformed_json`: `_FakeResponse(b"not json", status=200)` → `AISummaryError`.
  - `test_call_ollama_chat_raises_on_empty_content`: `_FakeResponse(json.dumps({"message": {"content": "  "}}).encode("utf-8"), status=200)` → `AISummaryError` with `EMPTY_RESPONSE_MESSAGE`.
  - `test_module_has_no_hardcoded_credentials`: `src = Path(ai_summary.__file__).read_text(encoding="utf-8")`; assert `"sk-" not in src`; assert `re.search(r"(?i)\b(api_key|token|secret)\b\s*=\s*[\"'][^\"']{16,}[\"']", src) is None`; assert `'st.secrets.get(OLLAMA_API_KEY_SECRET' in src` and `'st.secrets.get(OLLAMA_MODEL_SECRET' in src`.

**Definition of done:**
- [ ] `tests/test_ai_summary_logic.py::test_get_ai_config_reads_secrets`, `::test_get_ai_config_returns_empty_pair_when_secrets_unavailable`, `::test_is_ai_configured_requires_both_values`: prove spec behaviour 6 (values come from `st.secrets`, nothing hard-coded) and behaviour 3/7 (guarded lookup returns `("", "")` instead of raising).
- [ ] `tests/test_ai_summary_logic.py::test_build_summary_prompt_contains_only_this_players_name_and_fields`: proves spec behaviour 5 — prompt holds the selected player's name plus every key/value of that player's rounds and no other player's name or data.
- [ ] `tests/test_ai_summary_logic.py::test_summarize_season_passes_secrets_values_and_prompt_to_transport`: proves spec behaviours 6 and 5 end-to-end through the mocked seam (api_key/model equal the secrets values; prompt equals `build_summary_prompt(...)`).
- [ ] `tests/test_ai_summary_logic.py::test_summarize_season_raises_when_config_missing`, `::test_summarize_season_raises_and_skips_transport_when_no_rounds`, `::test_summarize_season_raises_on_blank_transport_response`, `::test_summarize_season_propagates_transport_error`: prove spec behaviours 7, 9, 10, 8 and that no outbound call is made when config or rounds are missing.
- [ ] `tests/test_ai_summary_logic.py::test_call_ollama_chat_posts_expected_payload_and_returns_content`, `::test_call_ollama_chat_raises_on_http_error`, `::test_call_ollama_chat_raises_on_non_success_status`, `::test_call_ollama_chat_raises_on_malformed_json`, `::test_call_ollama_chat_raises_on_empty_content`: prove the endpoint contract and every failure path of the single network seam; `urllib.request.urlopen` is monkeypatched, so no network is touched in any test.
- [ ] `tests/test_ai_summary_logic.py::test_module_has_no_hardcoded_credentials`: proves spec behaviour 6's "no credential literal" half.
- [ ] Importing `ai_summary` performs no secrets lookup and no network call (module import happens inside the test process only; all tests patch `urlopen`).

**Verify:**
```bash
uv run pytest tests/test_ai_summary_logic.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Summary button component
<!-- phase: 2 -->
<!-- targets: ai_summary.py, tests/test_ai_season_summary.py -->
<!-- frozen: auth.py, data.py, pages/3_🏆_League.py, test_streamlit_app.py, tests/test_announcement_page_wiring.py, tests/test_pinned_announcements.py, tests/test_pinned_winners_announcement.py, tests/test_upcoming_section_visibility.py -->

**Goal:** `ai_summary.render_season_summary` renders the exact button label when a player is given, renders nothing before a press, and after a press shows either the mocked summary text or a readable message — never an escaping exception.

**Changes:**
- `ai_summary.py`: append exactly this function (no other line of the module changes):

```python
def render_season_summary(player_name: str, season_rounds: list[dict]) -> None:
    """Render the '🤖 AI 赛季总结' button and, after a press, the summary or a readable error."""
    if not player_name:
        return
    if not st.button(AI_SUMMARY_BUTTON_LABEL, key="ai_season_summary_button"):
        return
    if _round_count(season_rounds) == 0:
        st.warning(NO_ROUNDS_MESSAGE)
        return
    with st.spinner("正在生成赛季总结…"):
        try:
            summary = summarize_season(player_name, season_rounds)
        except AISummaryError as exc:
            st.error(str(exc))
        else:
            st.markdown(summary)
```

- `tests/test_ai_season_summary.py` (new file). Use `from streamlit.testing.v1 import AppTest`; the test process is the same interpreter as the AppTest script thread, so `monkeypatch.setattr(ai_summary, "get_ai_config", ...)` and `monkeypatch.setattr(ai_summary, "_call_ollama_chat", ...)` are seen by the rendered script. Helpers to copy verbatim:

```python
import ai_summary
from streamlit.testing.v1 import AppTest

ROUNDS = [
    {"Game": "Game 1", "Net_Score": -8, "Birdies": 3, "Pars": 8},
    {"Game": "Game 2", "Net_Score": 3, "Birdies": 2, "Pars": 10},
]
SUMMARY_TEXT = "本赛季你的整体表现稳定，第 1 轮净杆 -8 是亮点。"
SECOND_TEXT = "第二次生成：整体发挥稳定。"


def _harness_script(player_name: str, rounds) -> str:
    return (
        "import streamlit as st\n"
        "import ai_summary\n"
        'st.metric("场均净杆", "-2.5")\n'
        'st.metric("总小鸟球", "5")\n'
        'st.metric("平均保帕", "9")\n'
        'st.metric("比赛轮次", "2")\n'
        f"ai_summary.render_season_summary({player_name!r}, {rounds!r})\n"
    )


def _run(player_name: str = "刘北南", rounds=ROUNDS, timeout: float = 10) -> AppTest:
    return AppTest.from_string(_harness_script(player_name, rounds), default_timeout=timeout).run()


def _configure(monkeypatch, api_key: str = "test-key", model: str = "test-model") -> None:
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: (api_key, model))
```

- Tests to implement:
  - `test_button_rendered_below_metrics_with_nothing_shown_before_press` (behaviours 1, 2, 3): `_configure(monkeypatch)`; count calls with `calls: list = []` and `monkeypatch.setattr(ai_summary, "summarize_season", lambda *args: calls.append(args) or SUMMARY_TEXT)`; `at = _run()`; assert `len(at.metric) == 4`; assert `[b.label for b in at.button] == [ai_summary.AI_SUMMARY_BUTTON_LABEL]`; assert `calls == []`; assert `at.error == []` and `at.warning == []` and `at.exception == []`; assert `all(SUMMARY_TEXT not in m.value for m in at.markdown)`.
  - `test_page_renders_without_ai_secrets_before_press` (behaviour 3): no monkeypatching of `get_ai_config` at all (the real guarded `st.secrets` lookup runs); `at = _run()`; assert `len(at.metric) == 4`, button label present, `at.error == []`, `at.warning == []`, `at.exception == []`.
  - `test_button_not_rendered_without_player` (behaviour 13): `_configure(monkeypatch)`; `at = _run(player_name="")`; assert `len(at.button) == 0`; assert `at.error == []` and `at.warning == []` and `at.exception == []`.
  - `test_press_renders_exact_summary_text` (behaviours 4, 12): `_configure(monkeypatch)`; recorder `calls: list[dict] = []` and `monkeypatch.setattr(ai_summary, "_call_ollama_chat", lambda api_key, model, prompt: calls.append({"api_key": api_key, "model": model, "prompt": prompt}) or SUMMARY_TEXT)`; `at = _run()`; `at.button[0].click().run()`; assert `len(calls) == 1`, `calls[0]["api_key"] == "test-key"`, `calls[0]["model"] == "test-model"`, `"刘北南" in calls[0]["prompt"]`, `SUMMARY_TEXT in [m.value for m in at.markdown]`, `at.error == []`, `at.exception == []`.
  - `test_summary_flow_needs_no_admin_token` (behaviour 12): `_configure(monkeypatch)`; `monkeypatch.setattr(ai_summary, "_call_ollama_chat", lambda *args: SUMMARY_TEXT)`; assert `"import auth" not in Path(ai_summary.__file__).read_text(encoding="utf-8")` and `"is_admin_user" not in` the same source; run a fresh `_run()` (no admin query param, no admin token in session state), click, assert `SUMMARY_TEXT in [m.value for m in at.markdown]` and `at.exception == []`.
  - `test_press_twice_issues_two_independent_requests` (behaviour 11): `_configure(monkeypatch)`; texts iterator `["第一期总结", "第二期总结"]` via `responses = iter([SUMMARY_TEXT, SECOND_TEXT])` and `monkeypatch.setattr(ai_summary, "_call_ollama_chat", lambda *args: next(responses))` with a counter list appended in the same lambda; `at.button[0].click().run()`; assert first text in `[m.value for m in at.markdown]`; then `at.button[0].click().run()`; assert call count `== 2` and `SECOND_TEXT in [m.value for m in at.markdown]`.
  - `test_press_without_secrets_shows_error_and_makes_no_request` (behaviour 7): `monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("", ""))`; `calls: list = []` with `_call_ollama_chat` recorder; `at.button[0].click().run()`; assert `calls == []`, `ai_summary.MISSING_CONFIG_MESSAGE in [e.value for e in at.error]`, `at.exception == []`, and no markdown containing `SUMMARY_TEXT`.
  - `test_press_with_failing_call_shows_error_and_no_exception` (behaviour 8): `_configure(monkeypatch)`; `_call_ollama_chat` raises `ai_summary.AISummaryError(ai_summary.CALL_FAILED_MESSAGE.format(detail="HTTP 500"))`; click; assert `at.exception == []` and `any("HTTP 500" in e.value for e in at.error)`.
  - `test_press_with_zero_rounds_shows_no_rounds_message` (behaviour 9): `_configure(monkeypatch)`; recorder for `_call_ollama_chat`; `at = _run(rounds=[])`; click; assert calls `== []`, `[w.value for w in at.warning] == [ai_summary.NO_ROUNDS_MESSAGE]`, `at.error == []`, `at.exception == []`.
  - `test_press_with_blank_response_shows_error` (behaviour 10): `_configure(monkeypatch)`; `_call_ollama_chat` returns `"   "`; click; assert `ai_summary.EMPTY_RESPONSE_MESSAGE in [e.value for e in at.error]` and `at.exception == []`.

**Definition of done:**
- [ ] `tests/test_ai_season_summary.py::test_button_rendered_below_metrics_with_nothing_shown_before_press`: proves spec behaviour 1 at component level (exact label `🤖 AI 赛季总结`, four metrics rendered alongside) and behaviour 2 (no call, no text before press).
- [ ] `tests/test_ai_season_summary.py::test_page_renders_without_ai_secrets_before_press`: proves spec behaviour 3 — no secrets present, metrics and button still render, no exception.
- [ ] `tests/test_ai_season_summary.py::test_button_not_rendered_without_player`: proves spec behaviour 13.
- [ ] `tests/test_ai_season_summary.py::test_press_renders_exact_summary_text` and `::test_summary_flow_needs_no_admin_token`: prove spec behaviours 4 and 12 (exact mocked text shown; no admin gating).
- [ ] `tests/test_ai_season_summary.py::test_press_twice_issues_two_independent_requests`: proves spec behaviour 11 (two requests, no caching).
- [ ] `tests/test_ai_season_summary.py::test_press_without_secrets_shows_error_and_makes_no_request`, `::test_press_with_failing_call_shows_error_and_no_exception`, `::test_press_with_zero_rounds_shows_no_rounds_message`, `::test_press_with_blank_response_shows_error`: prove spec behaviours 7, 8, 9, 10 with the Ollama seam mocked and no network.
- [ ] Every test uses `AppTest.from_string` with the module-level harness script; no test starts a server, and all monkeypatches are undone by pytest's `monkeypatch` fixture teardown.

**Verify:**
```bash
uv run pytest tests/test_ai_summary_logic.py tests/test_ai_season_summary.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 3: Wire into the League deep-dive
<!-- phase: 3 -->
<!-- targets: pages/3_🏆_League.py, tests/test_league_deep_dive_wiring.py -->
<!-- frozen: ai_summary.py, auth.py, data.py, test_streamlit_app.py, tests/test_announcement_page_wiring.py, tests/test_ai_summary_logic.py, tests/test_ai_season_summary.py, tests/test_pinned_announcements.py, tests/test_pinned_winners_announcement.py, tests/test_upcoming_section_visibility.py -->

**Goal:** the League Player Deep-Dive renders the `🤖 AI 赛季总结` button for the selected player, immediately below the four metrics, with no other line of the page changed.

**Changes:**
- `pages/3_🏆_League.py`: exactly two insertions, nothing else.
  1. Add `from ai_summary import render_season_summary` in the existing top-of-file import block (directly after the existing `from data import ...` style import line).
  2. In the League Player Deep-Dive section, insert one call as the statement immediately after the block that renders the four metrics for the selected player:

```python
    render_season_summary(<selected player>, <that player's season rounds>)
```

  Rules for the two arguments (no exploratory shell probing needed — read the page file you are editing):
  - `<selected player>`: the existing local variable/expression that holds the deep-dive's currently selected player name as a `str` (the same value the four metrics are computed from). Do not re-query `data.py`.
  - `<that player's season rounds>`: the existing local that already holds that player's season rounds for the season. If it is a `pandas.DataFrame`, pass `df.to_dict(orient="records")` so the argument is `list[dict]`; if it is already a list of dicts, pass it unchanged. The rows must be only the selected player's rows.
  - Insertion point must leave no other Streamlit call between the last metric of the four and this call (dedents/blank lines are fine). Everything else in the file — the four metrics and their calculations — is unchanged.
- `tests/test_league_deep_dive_wiring.py` (new file). Tests to implement exactly:

```python
import ast
from pathlib import Path

import ai_summary
from streamlit.testing.v1 import AppTest

PAGE_PATH = Path("pages/3_🏆_League.py")
PLAYER = "刘北南"


def test_league_page_imports_and_calls_summary_once_after_metrics():
    source = PAGE_PATH.read_text(encoding="utf-8")
    assert "from ai_summary import render_season_summary" in source
    tree = ast.parse(source)
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "render_season_summary"
    ]
    assert len(calls) == 1, "the deep-dive must call render_season_summary exactly once"
    call = calls[0]
    assert len(call.args) == 2, "must pass the selected player and that player's season rounds"
    metric_lines = sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "metric"
    )
    preceding = [line for line in metric_lines if line < call.lineno]
    assert len(preceding) >= 4, "the four deep-dive metrics must be rendered above the button"
    lines = source.splitlines()
    between = lines[preceding[-1] : call.lineno - 1]
    assert not any("st." in line for line in between), (
        "no other Streamlit call may sit between the deep-dive metrics and the summary button"
    )


def test_league_page_renders_summary_button_for_selected_player(monkeypatch):
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("test-key", "test-model"))
    at = AppTest.from_file(str(PAGE_PATH), default_timeout=60).run()
    if ai_summary.AI_SUMMARY_BUTTON_LABEL not in [button.label for button in at.button]:
        for widget in list(at.selectbox) + list(at.radio) + list(at.multiselect):
            options = list(getattr(widget, "options", []) or [])
            if PLAYER in options:
                widget.select(PLAYER)
                at.run()
                break
    assert ai_summary.AI_SUMMARY_BUTTON_LABEL in [button.label for button in at.button]
    assert len(at.metric) >= 4
    assert at.exception == []
```

  This second test never presses the button, so no outbound request is made; it proves the deep-dive renders the button for a selected player and that the page still works with no secrets (`get_ai_config` is stubbed only to keep the render deterministic; nothing is called).

**Definition of done:**
- [ ] `tests/test_league_deep_dive_wiring.py::test_league_page_imports_and_calls_summary_once_after_metrics`: proves spec behaviour 1's "below the four metrics" placement statically — one import, exactly one call with two arguments, at least four `st.metric` calls above it, and no other Streamlit call between the last metric and the summary button.
- [ ] `tests/test_league_deep_dive_wiring.py::test_league_page_renders_summary_button_for_selected_player`: proves spec behaviour 1 and 13 dynamically on the real page — with a player selected, the exact label `🤖 AI 赛季总结` is among the page's buttons, at least four metrics are rendered, and the page raises nothing.
- [ ] `git diff --stat` for this phase touches only `pages/3_🏆_League.py` (two added lines) and `tests/test_league_deep_dive_wiring.py`.
- [ ] Existing suites still pass (spec behaviour 14): run the pre-existing unit tests and the BDD suite unchanged.

**Verify:**
```bash
uv run pytest tests/test_league_deep_dive_wiring.py -v
uv run pytest tests/test_ai_summary_logic.py tests/test_ai_season_summary.py -q
uv run pytest test_streamlit_app.py tests/test_announcement_page_wiring.py tests/test_pinned_announcements.py tests/test_pinned_winners_announcement.py tests/test_upcoming_section_visibility.py -q
uv run behave --format progress
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- **Unknown variable names in `pages/3_🏆_League.py`.** The deep-dive's selected-player and rounds locals are not enumerated in the approved docs. Mitigation: Phase 3 inserts one call next to the existing four-metric block using those existing locals, and its static test fails loudly if the call is missing, duplicated, or separated from the metrics by another Streamlit call.
- **The deep-dive player selector may not be a `selectbox`/`radio`/`multiselect`.** Then Phase 3's dynamic test cannot select a player and the button may be absent. Mitigation: the static test still proves wiring; the builder adapts the selection step to the page's actual selection mechanism (e.g. `at.session_state` or `st.query_params`) and records the deviation in the build log.
- **Page-level AppTest fragility (heavy `data.py` import, backup hydration writes to `data/`).** Caught by Phase 3's dynamic test (`at.exception == []`); the same import already happens in the existing announcement-page wiring test.
- **Streamlit AppTest element API differences** (`.select`, `.options`, `.error`, `.warning`, `.markdown`). Caught by Phase 2/3 Verify runs; all element access is by collection rather than by type-specific helpers that may not exist.
- **Secrets present on a developer machine** would change `get_ai_config` results. Caught by pinning `get_ai_config` with monkeypatch in every test whose outcome depends on config, and by leaving only render-only assertions unpinned.
- **Leaking a real network call into tests.** Caught in Phase 1: `urllib.request.urlopen` is monkeypatched in every transport test, and `_call_ollama_chat` is monkeypatched in every `summarize_season`/UI test.
- **Accidentally changing other pages, `auth.py`, `data.py`, or the existing tests.** Caught by the `frozen` markers per phase and by `git diff --stat` in Phase 3's Definition of done.

## Open questions
- Exact secret key names: assumed `OLLAMA_API_KEY` and `OLLAMA_MODEL` (spec's assumption), read via `st.secrets.get(..., "")` inside a `try/except` like `auth._allowed_tokens()`.
- Exact endpoint and payload: assumed `https://ollama.com/api/chat`, `POST`, JSON body `{"model", "stream": False, "messages": [...]}`, response `{"message": {"content": ...}}`; the URL is a module constant, never a secret.
- Exact per-round fields: assumed the deep-dive's already-loaded rows for the selected player, passed through unmodified, with a `to_dict(orient="records")` conversion if the view holds a DataFrame.
- Whether the deep-dive's four metrics live in a function scope or at module level: the Phase 3 static ordering test only relies on the file's line order, so both layouts work.
- Whether the deep-dive's selection widget is a `selectbox`/`radio`/`multiselect`: assumed one of these; if not, the builder adapts the dynamic test's selection step as noted in Risks and logs the deviation.
- Summary persistence: assumed none — each press issues exactly one request, and nothing is cached or stored.

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/005-league-player-deep-dive-under-the/build-log.md` with one section per phase, in order. Head each one `## Phase <n>: <title>`, then list the files changed, the Verify command you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/005-league-player-deep-dive-under-the`.

Commit only this plan's targets and `build-log.md`. Leave every other file alone, including other features' documents under `sdlc/features/`, even for formatting; verification fails on any file outside the targets.
