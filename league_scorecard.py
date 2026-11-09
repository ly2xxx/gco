"""Scorecard auto-fill helpers for the League admin score form."""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import re
import socket
import urllib.error
import urllib.request
from collections.abc import Mapping as AbcMapping
from collections.abc import MutableMapping as AbcMutableMapping  # noqa: F401
from dataclasses import dataclass
from datetime import date, datetime
from difflib import get_close_matches
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

ScorecardFieldValue = str | int

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


@dataclass(frozen=True)
class LeagueScorecardPlayersResult:
    players: list[ScorecardPlayerEntry]
    unavailable_reason: str | None = None


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
            ScorecardPlayerEntry(index=len(entries), label=label, found_fields=_player_fields(raw))
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
    '{"players": [{"label": "<text printed for this player>", "fields": {...}}, ...]}\n'
    "Rules:\n"
    '- Return one object in "players" for every player printed on the card, in the order the '
    "players appear on the card. Never drop a player and never list a player twice.\n"
    '- "label": the player\'s printed name. When no name is printed, use the column header printed '
    "above that player's scores, exactly as printed. Never invent a label and never use "
    "A/B/C/Marker.\n"
    '- "fields": an object holding only the scores that belong to this one player, using any of '
    '"date", "venue", "net", "gross", "stableford", "eagles", "birdies", "pars", "bogeys", '
    '"double_bogeys_or_worse".\n'
    '- "date": the round date as an ISO string "YYYY-MM-DD".\n'
    '- "venue": the venue/course name exactly as printed on the card.\n'
    '- "net", "gross", "stableford": integers.\n'
    '- "eagles", "birdies", "pars", "bogeys", "double_bogeys_or_worse": non-negative integer counts.\n'
    "- Omit any field you cannot read with confidence. Never guess and never invent a value.\n"
    "- Do not add keys other than \"players\", \"label\" and \"fields\"."
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


def _post_ollama_generate(payload: dict[str, Any], timeout_seconds: float) -> str:
    """POST one generate request and return the raw body. No retry."""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    api_key = _ollama_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        OLLAMA_GENERATE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise ScorecardRequestError(f"http {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
        reason = "timeout" if isinstance(exc, (TimeoutError, socket.timeout)) else "network error"
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


def read_league_scorecard_players(
    image_bytes: bytes,
    mime_type: str | None,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> LeagueScorecardPlayersResult:
    """Read every player from one league scorecard image. Never raises."""
    if not image_bytes:
        return LeagueScorecardPlayersResult([], "empty image")
    if normalize_mime_type(mime_type, image_bytes) is None:
        return LeagueScorecardPlayersResult([], "unsupported file type")
    try:
        payload = build_scorecard_players_payload(image_bytes, model=_scorecard_model())
        body = _post_ollama_generate(payload, timeout_seconds)
    except ScorecardRequestError as exc:
        return LeagueScorecardPlayersResult([], str(exc) or "service error")
    except Exception:
        return LeagueScorecardPlayersResult([], "service error")
    parsed = parse_ollama_response(body)
    if parsed is None:
        return LeagueScorecardPlayersResult([], "unparseable response")
    try:
        players = scorecard_player_entries(parsed)
    except Exception:
        return LeagueScorecardPlayersResult([], "unparseable response")
    if not players:
        return LeagueScorecardPlayersResult([], "no readable players")
    return LeagueScorecardPlayersResult(players)


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


def scorecard_upload_fingerprint(file_name: str, payload: bytes) -> str:
    """Stable id of one selected file, so the same upload is read only once."""
    return hashlib.sha256(str(file_name).encode("utf-8") + b"\x00" + bytes(payload or b"")).hexdigest()
