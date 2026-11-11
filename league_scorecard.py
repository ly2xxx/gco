"""Scorecard auto-fill helpers for the League admin score form."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import math
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping as AbcMapping
from collections.abc import MutableMapping as AbcMutableMapping  # noqa: F401
from dataclasses import dataclass, field
from datetime import date, datetime
from difflib import get_close_matches
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

# The file this module was loaded from, by modification time. A redeploy replaces the
# file but a running Streamlit app keeps the imported module, so pages compare this
# with the file on disk and reload the module when they differ.
LOADED_FROM_MTIME: float = os.path.getmtime(__file__)

# ---------------------------------------------------------------- logging
# Every Ollama scorecard read logs what it sent, how long it took and what came back,
# so a failed auto-fill can be traced in the app's logs (Streamlit Cloud: Manage app).
# The API key is never logged; the model's reply is logged up to LOG_EXCERPT_CHARS.
LOGGER_NAME = "gco.scorecard"
LOG_EXCERPT_CHARS = 2000


def _scorecard_logger() -> logging.Logger:
    """INFO-level logger writing to stderr, which Streamlit Cloud shows in the app's logs."""
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:  # the logger outlives module reloads: add the handler once
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(asctime)s [scorecard] %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


log = _scorecard_logger()


def _excerpt(text: object, limit: int = LOG_EXCERPT_CHARS) -> str:
    """``text`` on one line, cut to ``limit`` characters with a note of how much was cut."""
    flat = " ".join(str(text).split())
    if len(flat) <= limit:
        return flat
    return f"{flat[:limit]}… (+{len(flat) - limit} chars)"

ScorecardFieldValue = str | int

# Saved scorecard images: the folder the League page's Save uploads to (through GitHub),
# the width of the thumbnail shown for one, and the file types Streamlit can display.
SCORECARD_IMAGES_DIR: str = "scorecard_images"
SCORECARD_THUMBNAIL_WIDTH: int = 160
SCORECARD_IMAGE_SUFFIXES: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp", ".gif")

# Hole-by-hole read: the card's par and each player's score per hole, shown to the
# admin as a check table beside the uploaded image.
HOLE_NUMBERS: tuple[int, ...] = tuple(range(1, 19))
OUT_HOLES: tuple[int, ...] = tuple(range(1, 10))
IN_HOLES: tuple[int, ...] = tuple(range(10, 19))
HOLE_SCORE_MIN, HOLE_SCORE_MAX = 1, 20
PAR_MIN, PAR_MAX = 3, 7
VERIFICATION_TABLE_COLUMNS: tuple[str, ...] = tuple(str(h) for h in HOLE_NUMBERS) + ("Out", "In", "Total")
VERIFICATION_ROW_LABELS: tuple[str, str] = ("Par", "Score")
LEAGUE_SCORECARD_READ_RESULT_KEY: str = "league_scorecard_read_result"

LEAGUE_SCORECARD_FIELD_KEYS: tuple[str, ...] = (
    "date",
    "venue",
    "net",
    "gross",
    "stableford",
    "eagles",
    "birdies",
    "pars",
    "bogeys",
    "double_bogeys_or_worse",
)
DATE_FIELD_KEY = "date"
VENUE_FIELD_KEY = "venue"
COUNT_FIELD_KEYS: tuple[str, ...] = ("eagles", "birdies", "pars", "bogeys", "double_bogeys_or_worse")
NUMERIC_FIELD_KEYS: tuple[str, ...] = (
    "net",
    "gross",
    "stableford",
    "eagles",
    "birdies",
    "pars",
    "bogeys",
    "double_bogeys_or_worse",
)
ISO_DATE_FORMAT = "%Y-%m-%d"
DATE_INPUT_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%Y%m%d",
    "%Y年%m月%d日",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%d.%m.%Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d %b %Y",
    "%d %B %Y",
)
SCORE_MIN, SCORE_MAX = -200, 200
COUNT_MIN, COUNT_MAX = 0, 40
VENUE_MATCH_CUTOFF = 0.8

SCORECARD_FIELD_ALIASES: dict[str, str] = {
    "date": "date",
    "round_date": "date",
    "played_on": "date",
    "日期": "date",
    "venue": "venue",
    "course": "venue",
    "location": "venue",
    "场地": "venue",
    "球场": "venue",
    "net": "net",
    "net_score": "net",
    "net_score_to_par": "net",
    "净杆": "net",
    "gross": "gross",
    "gross_score": "gross",
    "total": "gross",
    "total_score": "gross",
    "总杆": "gross",
    "总成绩": "gross",
    "stableford": "stableford",
    "stableford_points": "stableford",
    "points": "stableford",
    "稳定分": "stableford",
    "史特伯福特分": "stableford",
    "eagle": "eagles",
    "eagles": "eagles",
    "eagles_or_better": "eagles",
    "老鹰": "eagles",
    "birdie": "birdies",
    "birdies": "birdies",
    "小鸟": "birdies",
    "par": "pars",
    "pars": "pars",
    "标准杆": "pars",
    "bogey": "bogeys",
    "bogeys": "bogeys",
    "柏忌": "bogeys",
    "double_bogey_or_worse": "double_bogeys_or_worse",
    "double_bogeys_or_worse": "double_bogeys_or_worse",
    "double_bogeys": "double_bogeys_or_worse",
    "double_bogey": "double_bogeys_or_worse",
    "worse": "double_bogeys_or_worse",
    "双柏忌": "double_bogeys_or_worse",
    "双柏忌以上": "double_bogeys_or_worse",
}

_NOT_FOUND_STRINGS = {"", "false", "no", "0"}


@dataclass(frozen=True)
class ScorecardReadResult:
    found_fields: dict[str, ScorecardFieldValue]
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class ScorecardPlayerEntry:
    index: int
    label: str
    found_fields: dict[str, ScorecardFieldValue]
    hole_scores: dict[int, int] = field(default_factory=dict)


@dataclass(frozen=True)
class LeagueScorecardPlayersResult:
    players: list[ScorecardPlayerEntry]
    unavailable_reason: str | None = None
    pars: dict[int, int] = field(default_factory=dict)


def normalize_field_name(name: object) -> str | None:
    """Map a raw extracted key (English, Chinese or a common alias) to its canonical field."""
    text = str(name).strip().casefold().replace("-", "_").replace(" ", "_").replace("／", "_")
    return SCORECARD_FIELD_ALIASES.get(text)


def parse_date_value(value: object, *, date_format: str = ISO_DATE_FORMAT) -> str | None:
    """Return the date formatted with ``date_format``, or None when it can't be read."""
    parsed: date | None = None
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        for fmt in DATE_INPUT_FORMATS:
            try:
                parsed = datetime.strptime(text, fmt).date()
            except ValueError:
                continue
            break
    if parsed is None:
        return None
    return parsed.strftime(date_format)


def coerce_int_value(value: object, *, minimum: int = SCORE_MIN, maximum: int = SCORE_MAX) -> int | None:
    """Return an int within [minimum, maximum], or None for anything else."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        number = value
    elif isinstance(value, float):
        if not (math.isfinite(value) and value.is_integer()):
            return None
        number = int(value)
    elif isinstance(value, str):
        text = value.strip()
        if not re.fullmatch(r"[+-]?\d{1,3}", text):
            return None
        number = int(text)
    else:
        return None
    if minimum <= number <= maximum:
        return number
    return None


def match_venue_name(raw_venue: str, known_venues: Sequence[str], *, cutoff: float = VENUE_MATCH_CUTOFF) -> str:
    """Return the known venue closest to ``raw_venue``, else the cleaned text as read."""
    cleaned = " ".join(str(raw_venue).split())
    if not cleaned:
        return ""
    options = [v for v in known_venues if str(v).strip()]
    if not options:
        return cleaned
    for option in options:
        if option.casefold() == cleaned.casefold():
            return option
    matches = get_close_matches(cleaned.casefold(), [v.casefold() for v in options], n=1, cutoff=cutoff)
    if matches:
        for option in options:
            if option.casefold() == matches[0]:
                return option
    return cleaned


def venue_names_from_records(records: Iterable[Mapping[str, object]]) -> list[str]:
    """Distinct, non-empty venue names from round records, in first-seen order."""
    names: list[str] = []
    seen: set[str] = set()
    for record in records:
        raw = record.get("venue") or record.get("Venue") or record.get("场地") or record.get("球场")
        name = str(raw).strip() if raw is not None else ""
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def _is_not_found(marker: object) -> bool:
    if marker is False or marker is None:
        return True
    return isinstance(marker, str) and marker.strip().casefold() in _NOT_FOUND_STRINGS


def scorecard_field_updates(
    extracted_fields: Mapping[str, object],
    *,
    known_venues: Sequence[str] = (),
) -> dict[str, ScorecardFieldValue]:
    """Keep only found, parseable target fields, normalised, in LEAGUE_SCORECARD_FIELD_KEYS order."""
    found: dict[str, ScorecardFieldValue] = {}
    for raw_key, raw_value in extracted_fields.items():
        field = normalize_field_name(raw_key)
        if field is None or field in found:
            continue
        value: Any = raw_value
        if isinstance(value, AbcMapping):
            if _is_not_found(value.get("found", value.get("confident", True))):
                continue
            value = value.get("value")
        if value is None or isinstance(value, (list, tuple, set, dict)):
            continue
        converted: ScorecardFieldValue | None
        if field == DATE_FIELD_KEY:
            converted = parse_date_value(value)
        elif field == VENUE_FIELD_KEY:
            converted = match_venue_name(str(value), known_venues) or None
        elif field in COUNT_FIELD_KEYS:
            converted = coerce_int_value(value, minimum=COUNT_MIN, maximum=COUNT_MAX)
        else:
            converted = coerce_int_value(value)
        if converted is None:
            continue
        found[field] = converted
    return {k: found[k] for k in LEAGUE_SCORECARD_FIELD_KEYS if k in found}


_PLAYER_LABEL_KEYS: tuple[str, ...] = (
    "label",
    "player",
    "name",
    "player_name",
    "printed_label",
    "column_header",
    "header",
    "column",
    "text",
)


def normalize_hole_number(key: object) -> int | None:
    """1-18 for an int or a digit-only string naming a hole, else None."""
    if isinstance(key, bool):
        return None
    if isinstance(key, int):
        return key if 1 <= key <= 18 else None
    if isinstance(key, str):
        text = key.strip()
        if text.isdigit():
            number = int(text)
            return number if 1 <= number <= 18 else None
    return None


def coerce_hole_values(raw: object, *, minimum: int, maximum: int) -> dict[int, int]:
    """Hole number -> int for each readable, in-range entry of a hole mapping; {} for non-mappings."""
    if not isinstance(raw, AbcMapping):
        return {}
    values: dict[int, int] = {}
    for raw_key, raw_value in raw.items():
        hole = normalize_hole_number(raw_key)
        if hole is None:
            continue
        value = coerce_int_value(raw_value, minimum=minimum, maximum=maximum)
        if value is None:
            continue
        values[hole] = value
    return {hole: values[hole] for hole in HOLE_NUMBERS if hole in values}


def coerce_par_values(raw: object) -> dict[int, int]:
    """coerce_hole_values with PAR_MIN..PAR_MAX."""
    return coerce_hole_values(raw, minimum=PAR_MIN, maximum=PAR_MAX)


def coerce_hole_scores(raw: object) -> dict[int, int]:
    """coerce_hole_values with HOLE_SCORE_MIN..HOLE_SCORE_MAX."""
    return coerce_hole_values(raw, minimum=HOLE_SCORE_MIN, maximum=HOLE_SCORE_MAX)


def _player_label(record: Mapping[str, object]) -> str | None:
    """The printed label for one parsed player record, or None when it has none."""
    for key in _PLAYER_LABEL_KEYS:
        raw = record.get(key)
        if raw is None or isinstance(raw, (list, tuple, set, dict)):
            continue
        text = str(raw).strip()
        if text:
            return text
    return None


def _player_fields(record: Mapping[str, object]) -> dict[str, ScorecardFieldValue]:
    """Normalised score fields for one parsed player record."""
    for key in ("fields", "found_fields", "scores"):
        nested = record.get(key)
        if isinstance(nested, AbcMapping):
            return scorecard_field_updates(nested)
    return scorecard_field_updates(record)


def scorecard_player_entries(parsed: Mapping[str, object]) -> list[ScorecardPlayerEntry]:
    """Players from a parsed multi-player league-scorecard response, in printed order.

    Each parsed player supplies a label and score fields. Labels are preserved exactly
    as read. Duplicate labels remain separate entries with distinct indexes.
    Missing or malformed ``players`` data returns an empty list.
    """
    if not isinstance(parsed, AbcMapping):
        return []
    raw_players = parsed.get("players")
    if not isinstance(raw_players, (list, tuple)):
        return []
    entries: list[ScorecardPlayerEntry] = []
    for raw in raw_players:
        if not isinstance(raw, AbcMapping):
            continue
        label = _player_label(raw)
        if label is None:
            continue
        entries.append(
            ScorecardPlayerEntry(
                index=len(entries),
                label=label,
                found_fields=_player_fields(raw),
                hole_scores=coerce_hole_scores(raw.get("hole_scores")),
            )
        )
    return entries


# ---------------------------------------------------------------- Ollama Cloud read

OLLAMA_GENERATE_URL = "https://ollama.com/api/generate"
DEFAULT_SCORECARD_MODEL = "glm-5.3-flash:cloud"
DEFAULT_TIMEOUT_SECONDS = 120.0
SUPPORTED_IMAGE_MIME_TYPES: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp", "image/gif")
MIME_ALIASES: dict[str, str] = {"image/jpg": "image/jpeg", "image/pjpeg": "image/jpeg"}
MODEL_ENV_NAMES: tuple[str, ...] = ("OLLAMA_SCORECARD_MODEL", "OLLAMA_MODEL")
API_KEY_ENV_NAMES: tuple[str, ...] = ("OLLAMA_API_KEY", "OLLAMA_KEY")

SCORECARD_PROMPT: str = (
    "You read one photographed golf scorecard for a single player. "
    "The card may be printed or handwritten, in Chinese, English, or both.\n"
    "Return a single JSON object and nothing else.\n"
    'Allowed keys: "date", "venue", "net", "gross", "stableford", "eagles", "birdies", "pars", '
    '"bogeys", "double_bogeys_or_worse".\n'
    "Rules:\n"
    '- "date": the round date as an ISO string "YYYY-MM-DD".\n'
    '- "venue": the venue/course name exactly as printed on the card.\n'
    '- "net", "gross", "stableford": integers.\n'
    '- "eagles", "birdies", "pars", "bogeys", "double_bogeys_or_worse": '
    "non-negative integer counts for this one player only.\n"
    "- Use null for any value you cannot read with confidence. Never guess and never invent a value.\n"
    "- Do not add extra keys."
)
SCORECARD_PLAYERS_PROMPT: str = (
    "You read one photographed golf league scorecard that may show several players' scores. "
    "The card may be printed or handwritten, in Chinese, English, or both.\n"
    "Return a single JSON object and nothing else, shaped as:\n"
    '{"pars": {"1": <int>, ..., "18": <int>}, '
    '"players": [{"label": "<text printed for this player>", "fields": {...}, '
    '"hole_scores": {"1": <int>, ..., "18": <int>}}, ...]}\n'
    "Rules:\n"
    '- Return one object in "players" for every player printed on the card, in the order the '
    "players appear on the card. Never drop a player and never list a player twice.\n"
    '- "pars": one numeric par for each hole 1-18 printed on the card, keyed by the hole number '
    'as a string. Omit any hole whose par you cannot read with confidence.\n'
    '- "label": the player\'s printed name. When no name is printed, use the column header printed '
    "above that player's scores, exactly as printed. Never invent a label and never use "
    "A/B/C/Marker.\n"
    '- "fields": an object holding only the scores that belong to this one player, using any of '
    '"date", "venue", "net", "gross", "stableford", "eagles", "birdies", "pars", "bogeys", '
    '"double_bogeys_or_worse".\n'
    '- "hole_scores": one numeric score for each hole 1-18 for this player only, keyed by the hole '
    'number as a string. Omit any hole whose score you cannot read with confidence.\n'
    '- "date": the round date as an ISO string "YYYY-MM-DD".\n'
    '- "venue": the venue/course name exactly as printed on the card.\n'
    '- "net", "gross", "stableford": integers.\n'
    '- "eagles", "birdies", "pars", "bogeys", "double_bogeys_or_worse": non-negative integer counts.\n'
    "- Omit any field you cannot read with confidence. Never guess and never invent a value.\n"
    '- Do not add keys other than "pars", "players", "label", "fields" and "hole_scores".'
)


class ScorecardRequestError(RuntimeError):
    """Transport-level failure of the scorecard generate request."""


def sniff_image_mime(image_bytes: bytes) -> str | None:
    """Image MIME type from the file's magic bytes, or None when it isn't a supported image."""
    data = bytes(image_bytes or b"")
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return None


def normalize_mime_type(mime_type: str | None, image_bytes: bytes) -> str | None:
    candidate = (mime_type or "").split(";")[0].strip().lower()
    candidate = MIME_ALIASES.get(candidate, candidate)
    if candidate in SUPPORTED_IMAGE_MIME_TYPES:
        return candidate
    return sniff_image_mime(image_bytes)


def build_scorecard_payload(image_bytes: bytes, *, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "prompt": SCORECARD_PROMPT,
        "images": [base64.b64encode(image_bytes).decode("ascii")],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }


def build_scorecard_players_payload(image_bytes: bytes, *, model: str) -> dict[str, Any]:
    """Request body for reading every player on one league scorecard."""
    return {
        "model": model,
        "prompt": SCORECARD_PLAYERS_PROMPT,
        "images": [base64.b64encode(image_bytes).decode("ascii")],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }


def _configured_value(names: Sequence[str]) -> str | None:
    """First non-empty value among ``names``: environment variables, then Streamlit secrets."""
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    try:
        import streamlit as st

        for name in names:
            value = str(st.secrets.get(name, "") or "").strip()
            if value:
                return value
    except Exception:
        pass
    return None


def _scorecard_model() -> str:
    return _configured_value(MODEL_ENV_NAMES) or DEFAULT_SCORECARD_MODEL


def _ollama_api_key() -> str | None:
    return _configured_value(API_KEY_ENV_NAMES)


def _prompt_kind(payload: Mapping[str, Any]) -> str:
    prompt = payload.get("prompt")
    if prompt == SCORECARD_PLAYERS_PROMPT:
        return "players"
    if prompt == SCORECARD_PROMPT:
        return "single"
    return "custom"


def _describe_ollama_body(body: str) -> str:
    """Ollama's completion stats and the model's reply text, for the log. Never raises."""
    try:
        outer = json.loads(body)
    except (json.JSONDecodeError, TypeError, ValueError):
        return f"body is not JSON: {_excerpt(body)}"
    if not isinstance(outer, dict):
        return f"body is JSON but not an object: {_excerpt(body)}"
    stats = []
    for key in ("model", "done", "done_reason", "prompt_eval_count", "eval_count"):
        if key in outer:
            stats.append(f"{key}={outer[key]}")
    for key in ("total_duration", "load_duration", "eval_duration"):
        if isinstance(outer.get(key), (int, float)):
            stats.append(f"{key}={outer[key] / 1e9:.1f}s")
    thinking = outer.get("thinking")
    if isinstance(thinking, str) and thinking:
        stats.append(f"thinking_chars={len(thinking)}")
    if "error" in outer:
        stats.append(f"error={_excerpt(outer['error'], 500)}")
    reply = outer.get("response")
    reply_text = reply if isinstance(reply, str) else json.dumps(reply, ensure_ascii=False)
    return f"{' '.join(stats) or 'no stats'} | reply ({len(str(reply_text))} chars): {_excerpt(reply_text)}"


def _post_ollama_generate(payload: dict[str, Any], timeout_seconds: float) -> str:
    """POST one generate request and return the raw body. No retry."""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    api_key = _ollama_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_GENERATE_URL,
        data=data,
        headers=headers,
        method="POST",
    )
    images = payload.get("images") or []
    log.info(
        "ollama request: POST %s model=%s prompt=%s image_b64_chars=%s body_bytes=%s timeout=%ss api_key=%s",
        OLLAMA_GENERATE_URL, payload.get("model"), _prompt_kind(payload),
        sum(len(i) for i in images if isinstance(i, str)), len(data), timeout_seconds,
        "set" if api_key else "MISSING",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
            log.info(
                "ollama response: status=%s after %.1fs, %s chars | %s",
                getattr(response, "status", "?"), time.monotonic() - started, len(body),
                _describe_ollama_body(body),
            )
            return body
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = ""
        log.warning(
            "ollama error: http %s after %.1fs: %s",
            exc.code, time.monotonic() - started, _excerpt(detail, 1000) or exc.reason,
        )
        raise ScorecardRequestError(f"http {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
        reason = "timeout" if isinstance(exc, (TimeoutError, socket.timeout)) else "network error"
        log.warning(
            "ollama error: %s after %.1fs (limit %ss): %r",
            reason, time.monotonic() - started, timeout_seconds, exc,
        )
        raise ScorecardRequestError(reason) from exc


def extract_json_object(text: str) -> dict[str, Any] | None:
    """The JSON object in ``text``, tolerating Markdown fences and surrounding prose."""
    if not isinstance(text, str):
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned[:4].lower() == "json":
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        parsed = json.loads(cleaned[start:end + 1])
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_ollama_response(body: str) -> dict[str, Any] | None:
    """The scorecard fields from a generate response body, or None when there are none."""
    try:
        outer = json.loads(body)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(outer, dict):
        return None
    inner = outer.get("response")
    if isinstance(inner, str):
        return extract_json_object(inner)
    if isinstance(inner, AbcMapping):
        return dict(inner)
    if "error" in outer:
        return None
    return outer


def read_league_scorecard(
    image_bytes: bytes,
    mime_type: str | None,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> ScorecardReadResult:
    """Read one scorecard image with one Ollama Cloud request. Never raises."""
    if not image_bytes:
        return ScorecardReadResult({}, "empty image")
    if normalize_mime_type(mime_type, image_bytes) is None:
        return ScorecardReadResult({}, "unsupported file type")
    try:
        payload = build_scorecard_payload(image_bytes, model=_scorecard_model())
        body = _post_ollama_generate(payload, timeout_seconds)
    except ScorecardRequestError as exc:
        return ScorecardReadResult({}, str(exc) or "service error")
    except Exception:
        return ScorecardReadResult({}, "service error")
    parsed = parse_ollama_response(body)
    if parsed is None:
        return ScorecardReadResult({}, "unparseable response")
    try:
        found = scorecard_field_updates(parsed)
    except Exception:
        return ScorecardReadResult({}, "unparseable response")
    if not found:
        return ScorecardReadResult({}, "no readable fields")
    return ScorecardReadResult(found)


def _explain_unparseable(body: str) -> str:
    """Why a generate body gave no JSON object, for the log. Never raises."""
    try:
        outer = json.loads(body)
    except (json.JSONDecodeError, TypeError, ValueError):
        return "the body is not JSON"
    if not isinstance(outer, dict):
        return f"the body is a JSON {type(outer).__name__}, not an object"
    if "error" in outer:
        return f"Ollama returned an error: {_excerpt(outer['error'], 500)}"
    reply = outer.get("response")
    if isinstance(reply, str):
        if not reply.strip():
            return f"the model's reply is empty (done_reason={outer.get('done_reason')})"
        return "the model's reply holds no JSON object"
    return f"no usable 'response' field (keys: {sorted(outer)})"


def _describe_parsed_shape(parsed: Mapping[str, object]) -> str:
    """The shape of a parsed reply that yielded no players, for the log. Never raises."""
    try:
        players = parsed.get("players")
        shape = f"top-level keys={sorted(map(str, parsed))}, players={type(players).__name__}"
        if isinstance(players, (list, tuple)):
            shape += f"[{len(players)}]"
            if players and isinstance(players[0], AbcMapping):
                shape += f", first record keys={sorted(map(str, players[0]))}"
        return shape
    except Exception as exc:  # pragma: no cover - logging must never break a read
        return f"shape unavailable ({exc!r})"


def read_league_scorecard_players(
    image_bytes: bytes,
    mime_type: str | None,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> LeagueScorecardPlayersResult:
    """Read every player from one league scorecard image. Never raises."""
    result = _read_league_scorecard_players(image_bytes, mime_type, timeout_seconds=timeout_seconds)
    try:
        if result.unavailable_reason is not None:
            log.warning("players read: unavailable (%s)", result.unavailable_reason)
        else:
            log.info("pars read: %s", len(result.pars))
            log.info(
                "players read: %s player(s): %s",
                len(result.players),
                "; ".join(f"{p.label!r} -> {p.found_fields}" for p in result.players),
            )
            log.info(
                "hole scores read: %s",
                "; ".join(f"{p.label!r} -> {p.hole_scores}" for p in result.players),
            )
    except Exception:  # pragma: no cover - logging must never break a read
        pass
    return result


def _read_league_scorecard_players(
    image_bytes: bytes,
    mime_type: str | None,
    *,
    timeout_seconds: float,
) -> LeagueScorecardPlayersResult:
    if not image_bytes:
        return LeagueScorecardPlayersResult([], "empty image")
    if normalize_mime_type(mime_type, image_bytes) is None:
        log.warning("players read: %r is not a supported image (sniffed %r)", mime_type, sniff_image_mime(image_bytes))
        return LeagueScorecardPlayersResult([], "unsupported file type")
    try:
        payload = build_scorecard_players_payload(image_bytes, model=_scorecard_model())
        body = _post_ollama_generate(payload, timeout_seconds)
    except ScorecardRequestError as exc:
        return LeagueScorecardPlayersResult([], str(exc) or "service error")
    except Exception as exc:
        log.exception("players read: unexpected error %r", exc)
        return LeagueScorecardPlayersResult([], "service error")
    parsed = parse_ollama_response(body)
    if parsed is None:
        log.warning("players read: unparseable response: %s", _explain_unparseable(body))
        return LeagueScorecardPlayersResult([], "unparseable response")
    try:
        players = scorecard_player_entries(parsed)
    except Exception as exc:
        log.exception("players read: could not build players from %s: %r", _describe_parsed_shape(parsed), exc)
        return LeagueScorecardPlayersResult([], "unparseable response")
    if not players:
        log.warning("players read: no labelled players in the reply: %s", _describe_parsed_shape(parsed))
        return LeagueScorecardPlayersResult([], "no readable players")
    return LeagueScorecardPlayersResult(players, pars=coerce_par_values(parsed.get("pars")))


# ---------------------------------------------------------------- session state

def apply_scorecard_updates(
    updates: Mapping[str, ScorecardFieldValue],
    widget_keys: Mapping[str, str],
    session_state: MutableMapping[str, Any],
) -> list[str]:
    """Write each found field into its widget's session-state key; return the fields written.

    Fields without a widget key, and keys that aren't target fields, are ignored.
    Calling it twice with the same arguments leaves the same state.
    """
    applied: list[str] = []
    for field in LEAGUE_SCORECARD_FIELD_KEYS:
        if field in updates and field in widget_keys:
            session_state[widget_keys[field]] = updates[field]
            applied.append(field)
    return applied


LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY: str = "league_scorecard_selected_player"


def selected_player_scorecard_updates(
    result: LeagueScorecardPlayersResult,
    selected_index: int | None,
) -> dict[str, ScorecardFieldValue]:
    """Fields for exactly the selected entry, or {} when no valid entry is selected."""
    if selected_index is None or isinstance(selected_index, bool) or not isinstance(selected_index, int):
        return {}
    for entry in result.players:
        if entry.index == selected_index:
            return dict(entry.found_fields)
    return {}


def apply_selected_player_scorecard_updates(
    result: LeagueScorecardPlayersResult,
    selected_index: int | None,
    widget_keys: Mapping[str, str],
    session_state: MutableMapping[str, Any],
) -> list[str]:
    """Clear the league scorecard widget keys, then write the selected player's present fields.

    Returns the fields written. With no valid selection, all league scorecard widget
    keys are cleared and an empty list is returned.
    """
    for field in LEAGUE_SCORECARD_FIELD_KEYS:
        key = widget_keys.get(field)
        if key is not None and key in session_state:
            del session_state[key]
    updates = selected_player_scorecard_updates(result, selected_index)
    return apply_scorecard_updates(updates, widget_keys, session_state)


def selected_player_hole_scores(
    result: LeagueScorecardPlayersResult,
    selected_index: int | None,
) -> dict[int, int]:
    """Hole scores for exactly the selected entry, or {} when no valid entry is selected."""
    if result is None or isinstance(selected_index, bool) or not isinstance(selected_index, int):
        return {}
    for entry in getattr(result, "players", ()) or ():
        if getattr(entry, "index", None) == selected_index:
            scores = getattr(entry, "hole_scores", {})
            return dict(scores) if isinstance(scores, AbcMapping) else {}
    return {}


def scorecard_hole_totals(values: Mapping[int, int]) -> dict[str, int | None]:
    """Out/In/Total sums, each None unless every hole it covers was read."""
    data = values if isinstance(values, AbcMapping) else {}
    out_total = sum(data[h] for h in OUT_HOLES) if all(h in data for h in OUT_HOLES) else None
    in_total = sum(data[h] for h in IN_HOLES) if all(h in data for h in IN_HOLES) else None
    total = out_total + in_total if out_total is not None and in_total is not None else None
    return {"Out": out_total, "In": in_total, "Total": total}


def scorecard_verification_row(values: Mapping[int, int]) -> list[int | None]:
    """21 cells in VERIFICATION_TABLE_COLUMNS order for one hole-values mapping."""
    data = values if isinstance(values, AbcMapping) else {}
    totals = scorecard_hole_totals(data)
    return [data.get(h) for h in HOLE_NUMBERS] + [totals["Out"], totals["In"], totals["Total"]]


def scorecard_verification_table(
    pars: Mapping[int, int],
    hole_scores: Mapping[int, int],
) -> dict[str, list[int | None]]:
    """{"Par": [...], "Score": [...]}, 21 cells each in VERIFICATION_TABLE_COLUMNS order."""
    return {
        VERIFICATION_ROW_LABELS[0]: scorecard_verification_row(pars),
        VERIFICATION_ROW_LABELS[1]: scorecard_verification_row(hole_scores),
    }


def scorecard_upload_fingerprint(file_name: str, payload: bytes) -> str:
    """Stable id of one selected file, so the same upload is read only once."""
    return hashlib.sha256(str(file_name).encode("utf-8") + b"\x00" + bytes(payload or b"")).hexdigest()


# ---------------------------------------------------------------- saved scorecard images

@dataclass(frozen=True)
class SavedScorecard:
    filename: str
    path: str
    timestamp: str


def game_number_from_label(game_label: object) -> int | None:
    """5 for "Game 5"; None for anything that is not "Game <number>". Never raises."""
    if game_label is None:
        return None
    try:
        match = re.fullmatch(r"game\s+(\d+)", str(game_label).strip(), re.IGNORECASE | re.ASCII)
    except Exception:
        return None
    return int(match.group(1)) if match else None


def find_saved_scorecard(
    tournament: object,
    game_label: object,
    player: object,
    *,
    directory: str = SCORECARD_IMAGES_DIR,
) -> SavedScorecard | None:
    """The newest saved scorecard image for one tournament, game and player, or None.

    The League page saves a card as ``league_<tournament>_<game>_<player>_<timestamp>.<ext>``
    with spaces written as ``_`` (``league_2026个人联赛_Game_5_李扬_20261109172833.jpg``).
    Names are matched exactly; the greatest timestamp in the file name wins. Only file
    names are read, never the images, and nothing is raised for a missing folder.
    """
    if tournament is None or player is None:
        return None
    tournament_text, player_text = str(tournament), str(player)
    game_number = game_number_from_label(game_label)
    if not tournament_text.strip() or not player_text.strip() or game_number is None:
        return None
    if not os.path.isdir(directory):
        return None
    prefix = f"league_{tournament_text}_Game_{game_number}_{player_text}_".replace(" ", "_")
    try:
        filenames = os.listdir(directory)
    except OSError:
        return None
    candidates: list[SavedScorecard] = []
    for filename in filenames:
        stem, suffix = os.path.splitext(filename)
        if suffix.lower() not in SCORECARD_IMAGE_SUFFIXES or not stem.startswith(prefix):
            continue
        timestamp = stem[len(prefix):]
        # All digits, so "Game 5" never picks up "..._Game_5_<player>_extra_<timestamp>".
        if not (timestamp.isascii() and timestamp.isdigit()):
            continue
        candidates.append(
            SavedScorecard(filename=filename, path=os.path.join(directory, filename), timestamp=timestamp)
        )
    if not candidates:
        return None
    return max(candidates, key=lambda card: (int(card.timestamp), card.filename))


def scorecard_image_url(repo: str | None, filename: str) -> str | None:
    """The saved scorecard's address on GitHub (the original file), or None without a repo.

    ``HEAD`` is the repository's default branch, so no branch name is needed.
    """
    repo_text = "" if repo is None else str(repo).strip()
    filename_text = "" if filename is None else str(filename).strip()
    if not repo_text or not filename_text:
        return None
    return (
        f"https://raw.githubusercontent.com/{repo_text}/HEAD/scorecard_images/"
        f"{urllib.parse.quote(filename_text)}"
    )


def scorecard_github_repo() -> str | None:
    """``owner/repo`` from GITHUB_REPO (environment, then Streamlit secrets); None when unset."""
    return _configured_value(("GITHUB_REPO",))
