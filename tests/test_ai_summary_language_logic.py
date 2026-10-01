from __future__ import annotations

import pandas as pd
import pytest

import ai_summary

ROUNDS: list[dict] = [{"score": 80, "birdies": 2}, {"score": 75, "birdies": 3}]
CHINESE_PROMPT: str = (
    "球员姓名：Jacky\n"
    "该球员本赛季的比赛轮次数据（每一行是一轮）：\n"
    "第 1 轮：score=80；birdies=2\n"
    "第 2 轮：score=75；birdies=3\n"
    + ai_summary.PROMPT_INSTRUCTION
)


@pytest.fixture
def ollama_stub(monkeypatch):
    calls: list[tuple[tuple, dict]] = []

    def fake_call(*args, **kwargs):
        calls.append((args, kwargs))
        return "  中文总结  "

    monkeypatch.setattr(ai_summary, "_call_ollama_chat", fake_call)
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("key", "model"))
    return calls


def _recording_call(monkeypatch) -> list:
    calls: list = []
    monkeypatch.setattr(ai_summary, "_call_ollama_chat", lambda *args, **kwargs: calls.append((args, kwargs)))
    return calls


def test_chinese_prompt_unchanged_without_language_argument():
    """Spec behaviours 3, 13."""
    assert ai_summary.build_summary_prompt("Jacky", ROUNDS) == CHINESE_PROMPT
    assert ai_summary.build_summary_prompt("Jacky", ROUNDS, language="中文") == CHINESE_PROMPT


def test_english_prompt_keeps_chinese_round_lines_and_english_labels():
    """Spec behaviour 5."""
    zh = ai_summary.build_summary_prompt("Jacky", ROUNDS)
    en = ai_summary.build_summary_prompt("Jacky", ROUNDS, language="English")
    zh_lines, en_lines = zh.split("\n"), en.split("\n")

    assert en_lines[0] == "Player name: Jacky"
    assert len(en_lines) == len(zh_lines)
    assert en_lines[-1] == ai_summary.PROMPT_INSTRUCTION_EN
    assert zh_lines[-1] == ai_summary.PROMPT_INSTRUCTION
    expected_fields = ["score=80；birdies=2", "score=75；birdies=3"]
    for i in range(2):
        zh_fields = zh_lines[2 + i].split("：", 1)[1]
        en_fields = en_lines[2 + i].split(": ", 1)[1]
        assert zh_fields == en_fields == expected_fields[i]


def test_english_prompt_from_dataframe_has_one_line_per_row():
    """Spec behaviour 6."""
    df = pd.DataFrame([{"score": 80, "birdies": 2}, {"score": 78, "birdies": 1}, {"score": 82, "birdies": 0}])

    prompt = ai_summary.build_summary_prompt("Jacky", df, language="English")
    lines = prompt.split("\n")

    assert sum(1 for line in lines if line.startswith("Round ")) == 3
    assert "Round 2: score=78；birdies=1" in prompt
    assert len(lines) == 6


def test_unsupported_language_falls_back_to_chinese(ollama_stub):
    """Spec behaviour 14."""
    assert ai_summary.normalize_language("English") == "English"
    for value in ("fr", "", None):
        assert ai_summary.normalize_language(value) == "中文"

    assert ai_summary.build_summary_prompt("Jacky", ROUNDS, language="fr") == CHINESE_PROMPT
    assert ai_summary.summarize_season("Jacky", ROUNDS, language="fr") == "中文总结"


def test_summarize_season_chinese_calls_ollama_with_three_positional_arguments(ollama_stub):
    """Spec behaviours 3, 13."""
    assert ai_summary.summarize_season("Jacky", ROUNDS) == "中文总结"
    assert ollama_stub == [(("key", "model", ai_summary.build_summary_prompt("Jacky", ROUNDS)), {})]


def test_summarize_season_english_uses_english_system_message(ollama_stub):
    """Spec behaviour 4."""
    assert ai_summary.summarize_season("Jacky", ROUNDS, language="English") == "中文总结"
    assert ollama_stub[0][0] == ("key", "model", ai_summary.build_summary_prompt("Jacky", ROUNDS, language="English"))
    assert ollama_stub[0][1] == {"system_message": ai_summary.SYSTEM_MESSAGE_EN}


@pytest.mark.parametrize("language", ["中文", "English"])
@pytest.mark.parametrize("rounds", [[], None, pd.DataFrame(columns=["score"])], ids=["empty-list", "none", "empty-frame"])
def test_summarize_season_no_rounds_raises_before_request(monkeypatch, rounds, language):
    """Spec behaviour 9."""
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("key", "model"))
    calls = _recording_call(monkeypatch)

    with pytest.raises(ai_summary.AISummaryError) as exc:
        ai_summary.summarize_season("Jacky", rounds, language=language)
    assert str(exc.value) == ai_summary.NO_ROUNDS_MESSAGE
    assert calls == []


@pytest.mark.parametrize("config", [("", ""), ("key", ""), ("", "model")])
def test_summarize_season_missing_config_raises_missing_config_message(monkeypatch, config):
    """Spec behaviour 10."""
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: config)
    calls = _recording_call(monkeypatch)

    with pytest.raises(ai_summary.AISummaryError) as exc:
        ai_summary.summarize_season("Jacky", ROUNDS, language="English")
    assert str(exc.value) == ai_summary.MISSING_CONFIG_MESSAGE
    assert calls == []


def test_summarize_season_propagates_call_failure(monkeypatch):
    """Spec behaviour 11."""
    message = ai_summary.CALL_FAILED_MESSAGE.format(detail="HTTP 500")
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("key", "model"))

    def failing(*args, **kwargs):
        raise ai_summary.AISummaryError(message)

    monkeypatch.setattr(ai_summary, "_call_ollama_chat", failing)

    with pytest.raises(ai_summary.AISummaryError) as exc:
        ai_summary.summarize_season("Jacky", ROUNDS, language="English")
    assert str(exc.value) == message


def test_summarize_season_empty_response_raises(monkeypatch):
    """Spec behaviour 11."""
    monkeypatch.setattr(ai_summary, "get_ai_config", lambda: ("key", "model"))
    monkeypatch.setattr(ai_summary, "_call_ollama_chat", lambda *args, **kwargs: "   ")

    with pytest.raises(ai_summary.AISummaryError) as exc:
        ai_summary.summarize_season("Jacky", ROUNDS, language="English")
    assert str(exc.value) == ai_summary.EMPTY_RESPONSE_MESSAGE
