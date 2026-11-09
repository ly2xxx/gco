"""Scorecard auto-fill helpers for the League admin score form."""
from __future__ import annotations

import math
import re
from collections.abc import Mapping as AbcMapping
from dataclasses import dataclass
from datetime import date, datetime
from difflib import get_close_matches
from typing import Any, Iterable, Mapping, Sequence

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
