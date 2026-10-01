"""AI season summary for the League Player Deep-Dive (Ollama Cloud chat API).

Credentials and model come from st.secrets, read with the same guarded
st.secrets.get(..., default) pattern as auth._allowed_tokens().
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime

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
FOLLOW_UP_INPUT_LABEL: str = "追问赛季总结 / Ask a follow-up question"
FOLLOW_UP_BUTTON_LABEL: str = "提问 / Ask"
FOLLOW_UP_INPUT_KEY: str = "ai_season_follow_up_question"
FOLLOW_UP_FORM_KEY: str = "ai_season_follow_up_form"
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

DOWNLOAD_BUTTON_LABEL: str = "⬇️ 下载 / Download"
DOWNLOAD_BUTTON_KEY: str = "ai_season_summary_download"
TRANSCRIPT_MIME_TYPE: str = "text/plain"
TRANSCRIPT_FILE_EXTENSION: str = ".txt"
TRANSCRIPT_FILENAME_PREFIX: str = "gco_league_ai_summary"
TRANSCRIPT_SUMMARY_HEADING: str = "AI 赛季总结 / AI Season Summary"
TRANSCRIPT_QA_HEADING: str = "追问与回答 / Follow-up Q&A"

_HTML_BREAK_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')
_FILENAME_WHITESPACE_RE = re.compile(r"\s+")


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


def normalize_language(language: str | None) -> str:
    """Return LANGUAGE_ENGLISH only for LANGUAGE_ENGLISH, otherwise LANGUAGE_CHINESE. Never raises."""
    if language == LANGUAGE_ENGLISH:
        return LANGUAGE_ENGLISH
    return LANGUAGE_CHINESE


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


def _transcript_safe_text(value: object) -> str:
    """None -> "", <br>/<br/> -> newline, every other HTML tag removed, "```" removed,
    surrounding whitespace stripped. Never raises."""
    if value is None:
        return ""
    try:
        text = str(value)
    except Exception:
        return ""
    text = _HTML_BREAK_RE.sub("\n", text)
    text = _HTML_TAG_RE.sub("", text)
    text = text.replace("```", "")
    return text.strip()


def _transcript_turns(history: object) -> list[dict]:
    """The dict entries of history in stored order; [] when history is None, is not a
    list, or holds non-dict entries. Never raises."""
    if not isinstance(history, list):
        return []
    return [turn for turn in history if isinstance(turn, dict)]


def build_transcript_text(
    player_name: str,
    summary: str,
    history: list[dict] | None,
) -> str:
    """Return the plain-text transcript: TRANSCRIPT_SUMMARY_HEADING, the sanitized
    summary, TRANSCRIPT_QA_HEADING, then every turn with a non-empty sanitized question
    and answer that is not an exact (question, answer) duplicate of an earlier turn, in
    stored order, as '问 / Q: <question>' followed by '答 / A: <answer>'. The result ends
    with a single newline. player_name is accepted for interface symmetry with
    build_transcript_filename and is not written into the text. Never raises."""
    parts: list[str] = [
        TRANSCRIPT_SUMMARY_HEADING,
        "",
        _transcript_safe_text(summary),
        "",
        TRANSCRIPT_QA_HEADING,
    ]
    seen: set[tuple[str, str]] = set()
    for turn in _transcript_turns(history):
        question = _transcript_safe_text(turn.get("question"))
        answer = _transcript_safe_text(turn.get("answer"))
        if not question or not answer:
            continue
        key = (question, answer)
        if key in seen:
            continue
        seen.add(key)
        parts.append("")
        parts.append(f"问 / Q: {question}")
        parts.append(f"答 / A: {answer}")
    return "\n".join(parts).rstrip() + "\n"


def build_transcript_filename(player_name: str, timestamp: datetime) -> str:
    """Return '<TRANSCRIPT_FILENAME_PREFIX>_<sanitized player name>_<YYYYMMDD_HHMMSS>.txt'.
    The stem is never empty and the result never contains / \\ : * ? " < > |. Never raises."""
    stem = _UNSAFE_FILENAME_CHARS.sub("", _transcript_safe_text(player_name))
    stem = _FILENAME_WHITESPACE_RE.sub("_", stem).strip("._")
    if not stem:
        stem = "player"
    try:
        stamp = timestamp.strftime("%Y%m%d_%H%M%S")
    except Exception:
        stamp = ""
    if not stamp:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{TRANSCRIPT_FILENAME_PREFIX}_{stem}_{stamp}{TRANSCRIPT_FILE_EXTENSION}"


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
