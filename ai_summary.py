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
