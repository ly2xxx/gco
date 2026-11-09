<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@88fb6d9 -->
## Approach

Add one new dependency-free helper module, `league_scorecard.py`, that owns every piece of scorecard logic (field filtering/normalisation, the single Ollama Cloud `generate` call with a 120 s cap, and the `st.session_state` application step), so each piece can be unit-tested in-process without Streamlit or network. Then wire `pages/3_🏆_League.py` minimally: a `st.file_uploader` above the ten target fields, one read per selected file (fingerprint-guarded, no retry), a one-shot prefill written into the existing widgets' session-state keys plus an `st.info` notice on any failure, leaving the existing fields, defaults, layout and the Save/`github_upload_image` path untouched.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| The League score form shows a scorecard image picker above its fields and is otherwise unchanged in layout, fields and defaults. | 1 | 4 |
| Reading a scorecard fills only the date, venue, net, gross, stableford and eagle/birdie/par/bogey/double-bogey-or-worse fields the service reports as found, and leaves every other field holding the value it already had (existing score when editing, otherwise the current default). | 2, 3, 4, 5, 6, 17 | 1, 2, 3, 4 |
| Pre-filled values remain editable, and saving stores what the admin sees on screen after any corrections. | 7, 8 | 3, 4 |
| Saving still uploads the scorecard image via `github_upload_image`, and a save with no image or a failed upload behaves as it does today. | 9, 10, 11 | 4 |
| With no upload, an unreadable image, an unsupported file type, a service error, or no response within 120 seconds, the form renders with its existing values (the round's current score if editing, else 72/36/0), the admin is told auto-fill was unavailable, and no error surfaces to players or other pages. | 2, 12, 13, 14, 15, 16, 18 | 2, 3, 4 |
| The existing tests still pass. | 19 | 1, 2, 3, 4 |

## Phase 1: Field filtering and normalisation module
<!-- phase: 1 -->
<!-- targets: league_scorecard.py, tests/test_league_scorecard_fields.py -->
<!-- frozen: pages/3_🏆_League.py, pages/4_🥊_Cup.py, pages/5_⛳_Outing.py, streamlit_app.py, data.py, ai_summary.py, requirements.txt, pyproject.toml, uv.lock, test_streamlit_app.py, tests/test_league_deep_dive_wiring.py, tests/test_league_follow_up_wiring.py, features/** -->

**Goal:** `scorecard_field_updates` returns exactly the parseable, found target fields, normalised to ISO dates / ints / closest known venue, and drops everything else.

**Changes:**
- `league_scorecard.py` (new file, standard library only — do **not** touch `requirements.txt`, `pyproject.toml` or `uv.lock`). Module docstring `"""Scorecard auto-fill helpers for the League admin score form."""`, then `from __future__ import annotations` and these imports: `import math`, `import re`, `from collections.abc import Mapping as AbcMapping`, `from dataclasses import dataclass`, `from datetime import date, datetime`, `from difflib import get_close_matches`, `from typing import Any, Iterable, Mapping, Sequence`.
- `league_scorecard.py` constants (exact values):
  - `ScorecardFieldValue = str | int`
  - `LEAGUE_SCORECARD_FIELD_KEYS: tuple[str, ...] = ("date", "venue", "net", "gross", "stableford", "eagles", "birdies", "pars", "bogeys", "double_bogeys_or_worse")`
  - `DATE_FIELD_KEY = "date"`, `VENUE_FIELD_KEY = "venue"`
  - `COUNT_FIELD_KEYS: tuple[str, ...] = ("eagles", "birdies", "pars", "bogeys", "double_bogeys_or_worse")`
  - `NUMERIC_FIELD_KEYS: tuple[str, ...] = ("net", "gross", "stableford", "eagles", "birdies", "pars", "bogeys", "double_bogeys_or_worse")`
  - `ISO_DATE_FORMAT = "%Y-%m-%d"`
  - `DATE_INPUT_FORMATS: tuple[str, ...] = ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d", "%Y年%m月%d日", "%m/%d/%Y", "%d/%m/%Y", "%d.%m.%Y", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y")`
  - `SCORE_MIN, SCORE_MAX = -200, 200`; `COUNT_MIN, COUNT_MAX = 0, 40`; `VENUE_MATCH_CUTOFF = 0.8`
  - `SCORECARD_FIELD_ALIASES: dict[str, str]` mapping normalised names to canonical keys: `"date"/"round_date"/"played_on"/"日期" → "date"`; `"venue"/"course"/"location"/"场地"/"球场" → "venue"`; `"net"/"net_score"/"net_score_to_par"/"净杆" → "net"`; `"gross"/"gross_score"/"total"/"total_score"/"总杆"/"总成绩" → "gross"`; `"stableford"/"stableford_points"/"points"/"稳定分"/"史特伯福特分" → "stableford"`; `"eagle"/"eagles"/"eagles_or_better"/"老鹰" → "eagles"`; `"birdie"/"birdies"/"小鸟" → "birdies"`; `"par"/"pars"/"标准杆" → "pars"`; `"bogey"/"bogeys"/"柏忌" → "bogeys"`; `"double_bogey_or_worse"/"double_bogeys_or_worse"/"double_bogeys"/"double_bogey"/"worse"/"双柏忌"/"双柏忌以上" → "double_bogeys_or_worse"`.
- `league_scorecard.py`, frozen dataclass exactly as the spec's interface:
  ```python
  @dataclass(frozen=True)
  class ScorecardReadResult:
      found_fields: dict[str, ScorecardFieldValue]
      unavailable_reason: str | None = None
  ```
- `league_scorecard.py` function `normalize_field_name(name: object) -> str | None`: `text = str(name).strip().casefold().replace("-", "_").replace(" ", "_").replace("／", "_")`; return `SCORECARD_FIELD_ALIASES.get(text)`.
- `league_scorecard.py` function `parse_date_value(value: object, *, date_format: str = ISO_DATE_FORMAT) -> str | None`: `datetime` → its `.date()`; `date` → itself; `str` → `strip()`, empty returns `None`, then try each of `DATE_INPUT_FORMATS` with `datetime.strptime(text, fmt)`, first success wins; anything else `None`; successful value returned as `parsed.strftime(date_format)`.
- `league_scorecard.py` function `coerce_int_value(value: object, *, minimum: int = SCORE_MIN, maximum: int = SCORE_MAX) -> int | None`: return `None` for `bool`; `int` kept as-is; `float` kept only when `math.isfinite(value) and value.is_integer()`; `str` stripped must match `re.fullmatch(r"[+-]?\d{1,3}", text)`; then return the int only when `minimum <= number <= maximum`, else `None`; every other type returns `None`.
- `league_scorecard.py` function `match_venue_name(raw_venue: str, known_venues: Sequence[str], *, cutoff: float = VENUE_MATCH_CUTOFF) -> str`: `cleaned = " ".join(str(raw_venue).split())`; return `""` if empty; build `options = [v for v in known_venues if str(v).strip()]`; return `cleaned` if `options` is empty; if any option casefolds equal to `cleaned.casefold()` return that option verbatim; else `matches = get_close_matches(cleaned.casefold(), [v.casefold() for v in options], n=1, cutoff=cutoff)` and return the first original option whose casefold equals `matches[0]`, otherwise `cleaned`.
- `league_scorecard.py` function `venue_names_from_records(records: Iterable[Mapping[str, object]]) -> list[str]`: for each record read `record.get("venue") or record.get("Venue") or record.get("场地") or record.get("球场")`, `str(...).strip()`, skip empties, de-duplicate preserving first-seen order, return the list.
- `league_scorecard.py` function `scorecard_field_updates(extracted_fields: Mapping[str, object], *, known_venues: Sequence[str] = ()) -> dict[str, ScorecardFieldValue]` (the spec signature plus a defaulted keyword-only `known_venues`): for each `(raw_key, raw_value)` — resolve `field = normalize_field_name(raw_key)`, skip when `None`; if `raw_value` is an `AbcMapping`, skip when `raw_value.get("found", raw_value.get("confident", True))` is `False`, `None`, or a string in `{"", "false", "no", "0"}` (casefolded/stripped), then take `raw_value.get("value")`; skip `None`, and skip `list`/`tuple`/`set`/`dict` values; convert with `parse_date_value` for `date`, `match_venue_name(str(value), known_venues)` (skip if the result is empty) for `venue`, else `coerce_int_value(value, minimum=COUNT_MIN, maximum=COUNT_MAX)` for `COUNT_FIELD_KEYS` and `coerce_int_value(value)` otherwise; skip `None`; keep the first value seen per field. Return `{k: found[k] for k in LEAGUE_SCORECARD_FIELD_KEYS if k in found}` (fixed order, only target keys).
- `tests/test_league_scorecard_fields.py` (new file): `from league_scorecard import (...)` at module top so the repo root is on `sys.path` via pytest's rootdir; no fixtures needed beyond `pytest.mark.parametrize`; no teardown required (pure functions, no files or threads).

**Definition of done:**
- [ ] `tests/test_league_scorecard_fields.py`, test `test_league_scorecard_field_keys_and_result_contract`: asserts `LEAGUE_SCORECARD_FIELD_KEYS == ("date", "venue", "net", "gross", "stableford", "eagles", "birdies", "pars", "bogeys", "double_bogeys_or_worse")`, `ScorecardReadResult({}).unavailable_reason is None`, and `pytest.raises(dataclasses.FrozenInstanceError)` around `result.found_fields = {}`.
- [ ] `tests/test_league_scorecard_fields.py`, test `test_scorecard_field_updates_keeps_only_found_target_fields`: input `{"date": "2026/06/23", "venue": "Pine Valley", "net": 5, "gross": 77, "stableford": 36, "eagles": 1, "birdies": 2, "pars": 3, "bogeys": 4, "double_bogeys_or_worse": 5}` returns all ten keys in `LEAGUE_SCORECARD_FIELD_KEYS` order, `result["date"] == "2026-06-23"`, and every non-date value is an `int`.
- [ ] `tests/test_league_scorecard_fields.py`, test `test_scorecard_field_updates_drops_missing_empty_and_unparseable`: `{"net": None, "gross": "", "stableford": "n/a", "date": "unknown", "venue": "   ", "birdies": []}` returns `{}`.
- [ ] `tests/test_league_scorecard_fields.py`, test `test_scorecard_field_updates_drops_not_found_markers`: `{"net": {"value": 5, "found": False}, "gross": {"value": 77, "found": True}, "stableford": {"value": 36, "found": "no"}}` returns `{"gross": 77}`.
- [ ] `tests/test_league_scorecard_fields.py`, test `test_scorecard_field_updates_parses_numeric_forms`: `"+5"`, `" 12 "`, `7.0` become ints; `7.5`, `True`, `"five"`, `object()` are dropped; `{"eagles": -1}` and `{"gross": 250}` dropped; `{"net": -12}` kept.
- [ ] `tests/test_league_scorecard_fields.py`, test `test_scorecard_field_updates_normalises_dates` (`pytest.mark.parametrize` over `("2026-06-23", "2026/06/23", "2026.06.23", "2026年6月23日", "20260623", date(2026, 6, 23), datetime(2026, 6, 23, 18, 0))`): every case yields `{"date": "2026-06-23"}`.
- [ ] `tests/test_league_scorecard_fields.py`, test `test_match_venue_name_prefers_known_venue`: case-insensitive exact match returns the known option's own casing; `match_venue_name("Pine Valey Golf Club", ["Pine Valley Golf Club", "Augusta National"])` returns `"Pine Valley Golf Club"`; `match_venue_name("Somewhere Else", ["Augusta National"])` returns `"Somewhere Else"`; `match_venue_name("  Pine   Valley ", [])` returns `"Pine Valley"`.
- [ ] `tests/test_league_scorecard_fields.py`, test `test_venue_names_from_records`: `[{"venue": "A"}, {"venue": " A "}, {"Venue": "B"}, {"venue": ""}, {}]` returns `["A", "B"]`.
- [ ] `tests/test_league_scorecard_fields.py`, test `test_scorecard_field_updates_aliases_and_unknown_keys`: `{"Total": "77", "net_score": "5", "Double Bogey or Worse": "6", "player": "Neo"}` returns keys `("gross", "net", "double_bogeys_or_worse")` in `LEAGUE_SCORECARD_FIELD_KEYS` order with int values.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_fields.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: One Ollama Cloud scorecard read with a 120 s cap
<!-- phase: 2 -->
<!-- targets: league_scorecard.py, tests/test_league_scorecard_read.py -->
<!-- frozen: pages/3_🏆_League.py, pages/4_🥊_Cup.py, pages/5_⛳_Outing.py, streamlit_app.py, data.py, ai_summary.py, requirements.txt, pyproject.toml, uv.lock, test_streamlit_app.py, tests/test_league_scorecard_fields.py, tests/test_league_deep_dive_wiring.py, features/** -->

**Goal:** `read_league_scorecard` makes at most one POST to `https://ollama.com/api/generate`, converts every failure mode into an `unavailable_reason`, and never raises.

**Changes:**
- `league_scorecard.py`: extend the import block with `import base64`, `import json`, `import os`, `import socket`, `import urllib.error`, `import urllib.request`.
- `league_scorecard.py` constants: `OLLAMA_GENERATE_URL = "https://ollama.com/api/generate"`, `DEFAULT_SCORECARD_MODEL = "glm-5.3-flash:cloud"`, `DEFAULT_TIMEOUT_SECONDS = 120.0`, `SUPPORTED_IMAGE_MIME_TYPES: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp", "image/gif")`, `MIME_ALIASES: dict[str, str] = {"image/jpg": "image/jpeg", "image/pjpeg": "image/jpeg"}`, `MODEL_ENV_NAMES: tuple[str, ...] = ("OLLAMA_SCORECARD_MODEL", "OLLAMA_MODEL")`, `API_KEY_ENV_NAMES: tuple[str, ...] = ("OLLAMA_API_KEY", "OLLAMA_KEY")`.
- `league_scorecard.py` exception `class ScorecardRequestError(RuntimeError): """Transport-level failure of the scorecard generate request."""`.
- `league_scorecard.py` constant `SCORECARD_PROMPT: str` holding exactly:
  ```
  You read one photographed golf scorecard for a single player. The card may be printed or handwritten, in Chinese, English, or both.
  Return a single JSON object and nothing else.
  Allowed keys: "date", "venue", "net", "gross", "stableford", "eagles", "birdies", "pars", "bogeys", "double_bogeys_or_worse".
  Rules:
  - "date": the round date as an ISO string "YYYY-MM-DD".
  - "venue": the venue/course name exactly as printed on the card.
  - "net", "gross", "stableford": integers.
  - "eagles", "birdies", "pars", "bogeys", "double_bogeys_or_worse": non-negative integer counts for this one player only.
  - Use null for any value you cannot read with confidence. Never guess and never invent a value.
  - Do not add extra keys.
  ```
- `league_scorecard.py` function `sniff_image_mime(image_bytes: bytes) -> str | None`: JPEG when `data.startswith(b"\xff\xd8\xff")`; PNG when `data.startswith(b"\x89PNG\r\n\x1a\n")`; WebP when `data[:4] == b"RIFF" and data[8:12] == b"WEBP"`; GIF when `data[:6] in (b"GIF87a", b"GIF89a")`; else `None` (guard `bytes(image_bytes or b"")`).
- `league_scorecard.py` function `normalize_mime_type(mime_type: str | None, image_bytes: bytes) -> str | None`: `candidate = (mime_type or "").split(";")[0].strip().lower()`, mapped through `MIME_ALIASES`; return it when in `SUPPORTED_IMAGE_MIME_TYPES`, else `sniff_image_mime(image_bytes)`.
- `league_scorecard.py` function `build_scorecard_payload(image_bytes: bytes, *, model: str) -> dict[str, Any]` returning exactly `{"model": model, "prompt": SCORECARD_PROMPT, "images": [base64.b64encode(image_bytes).decode("ascii")], "stream": False, "format": "json", "options": {"temperature": 0, "num_predict": 512}}`.
- `league_scorecard.py` function `_scorecard_model() -> str`: first non-empty `os.environ` value among `MODEL_ENV_NAMES`; then, inside `try: import streamlit as st … except Exception: pass`, the first non-empty `st.secrets[name]` among the same names (`str(...).strip()`); else `DEFAULT_SCORECARD_MODEL`.
- `league_scorecard.py` function `_ollama_api_key() -> str | None`: same resolution order using `API_KEY_ENV_NAMES`, returning `None` when nothing is configured.
- `league_scorecard.py` function `_post_ollama_generate(payload: dict[str, Any], timeout_seconds: float) -> str`: build `headers = {"Content-Type": "application/json", "Accept": "application/json"}`, add `"Authorization": f"Bearer {api_key}"` when `_ollama_api_key()` is truthy; `urllib.request.Request(OLLAMA_GENERATE_URL, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")`; `with urllib.request.urlopen(request, timeout=timeout_seconds) as response: return response.read().decode("utf-8", errors="replace")`; map `urllib.error.HTTPError` to `raise ScorecardRequestError(f"http {exc.code}") from exc` and `(urllib.error.URLError, TimeoutError, socket.timeout, OSError)` to `raise ScorecardRequestError("timeout" if isinstance(exc, (TimeoutError, socket.timeout)) else "network error") from exc`. No retry loop anywhere.
- `league_scorecard.py` function `extract_json_object(text: str) -> dict[str, Any] | None`: return `None` for non-`str`; strip; if it starts with ```` ``` ````, strip backticks, drop a leading `json` (case-insensitive), strip again; take the slice from the first `{` to the last `}` (`None` when absent/reversed); `json.loads` inside `try` catching `(json.JSONDecodeError, TypeError, ValueError)`; return the dict only when it is an `AbcMapping`-compatible `dict`.
- `league_scorecard.py` function `parse_ollama_response(body: str) -> dict[str, Any] | None`: `json.loads(body)` in the same `try`/`except`; `None` when the result is not a dict; when `outer.get("response")` is a `str` return `extract_json_object(inner)`; when it is an `AbcMapping` return `dict(inner)`; when `"error" in outer` return `None`; otherwise return `outer`.
- `league_scorecard.py` function `read_league_scorecard(image_bytes: bytes, mime_type: str | None, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> ScorecardReadResult`: empty data → `ScorecardReadResult({}, "empty image")`; `normalize_mime_type(...) is None` → `ScorecardReadResult({}, "unsupported file type")`; then inside `try` build the payload and call `_post_ollama_generate(payload, timeout_seconds)` (positional second argument), catching `ScorecardRequestError` → `ScorecardReadResult({}, str(exc) or "service error")` and bare `Exception` → `ScorecardReadResult({}, "service error")`; unparseable body → `ScorecardReadResult({}, "unparseable response")`; `found = scorecard_field_updates(parsed)` (no `known_venues` here — the page applies the venue list afterwards) with `except Exception` → `"unparseable response"`; empty `found` → `ScorecardReadResult({}, "no readable fields")`; else `ScorecardReadResult(found)`.
- `tests/test_league_scorecard_read.py` (new file): `import json`, `from unittest.mock import Mock`, `import pytest`, `import league_scorecard as ls`. No real network: every test that reaches HTTP monkeypatches `ls._post_ollama_generate`; no fixtures need teardown beyond `monkeypatch` (`monkeypatch.delenv("OLLAMA_API_KEY", raising=False)`, `monkeypatch.delenv("OLLAMA_MODEL", raising=False)` where model/key resolution matters); no threads, servers or temp files.

**Definition of done:**
- [ ] `tests/test_league_scorecard_read.py`, test `test_read_success_returns_found_fields`: `monkeypatch.setattr(ls, "_post_ollama_generate", stub)` where `stub` records calls and returns `json.dumps({"response": "```json\n{\"date\": \"2026-06-23\", \"net\": \"5\", \"gross\": 77, \"player\": \"Neo\"}\n```"})`; asserts one call, `result.unavailable_reason is None`, `result.found_fields == {"date": "2026-06-23", "net": 5, "gross": 77}`.
- [ ] `tests/test_league_scorecard_read.py`, test `test_request_payload_and_timeout`: stub captures `(payload, timeout_seconds)`; asserts `payload["model"] == "glm-5.3-flash:cloud"` with no env/secrets set, `payload["stream"] is False`, `payload["format"] == "json"`, `payload["images"] == [base64.b64encode(b"\xff\xd8\xff\xe0card").decode("ascii")]`, `payload["prompt"] == ls.SCORECARD_PROMPT`, and `timeout_seconds == 120.0`; a second call with `timeout_seconds=5.0` asserts `timeout_seconds == 5.0`.
- [ ] `tests/test_league_scorecard_read.py`, test `test_model_env_override`: `monkeypatch.setenv("OLLAMA_SCORECARD_MODEL", "custom:cloud")` → `payload["model"] == "custom:cloud"`.
- [ ] `tests/test_league_scorecard_read.py`, test `test_endpoint_constant`: `ls.OLLAMA_GENERATE_URL == "https://ollama.com/api/generate"`.
- [ ] `tests/test_league_scorecard_read.py`, test `test_unsupported_mime_sends_no_request`: stub raises `AssertionError("must not be called")`; `read_league_scorecard(b"%PDF-1.4", "application/pdf")` returns `unavailable_reason == "unsupported file type"` and `found_fields == {}`.
- [ ] `tests/test_league_scorecard_read.py`, test `test_empty_image_sends_no_request`: `read_league_scorecard(b"", "image/jpeg")` → `unavailable_reason == "empty image"`, stub never called.
- [ ] `tests/test_league_scorecard_read.py`, test `test_mime_sniffed_from_magic_bytes`: `read_league_scorecard(b"\x89PNG\r\n\x1a\n" + b"x" * 8, None)` reaches the stub exactly once and parses a `{"response": "{\"net\": 3}"}` body to `found_fields == {"net": 3}`.
- [ ] `tests/test_league_scorecard_read.py`, test `test_http_error_becomes_unavailable`: stub raises `ls.ScorecardRequestError("http 500")` → `unavailable_reason == "http 500"`, `found_fields == {}`, one call only.
- [ ] `tests/test_league_scorecard_read.py`, test `test_timeout_becomes_unavailable`: stub raises `ls.ScorecardRequestError("timeout")` → `unavailable_reason == "timeout"`, one call only.
- [ ] `tests/test_league_scorecard_read.py`, test `test_unparseable_and_fieldless_responses`: stub returns `"not json"` → `"unparseable response"`; stub returns `json.dumps({"response": "{}"})` → `"no readable fields"`; stub returns `json.dumps({"error": "boom"})` → not `None` and `found_fields == {}`.
- [ ] `tests/test_league_scorecard_read.py`, test `test_unexpected_exception_is_swallowed`: stub raises `RuntimeError("kaboom")` → `unavailable_reason == "service error"` (no exception escapes).

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_read.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 3: Session-state application and upload fingerprint
<!-- phase: 3 -->
<!-- targets: league_scorecard.py, tests/test_league_scorecard_state.py -->
<!-- frozen: pages/3_🏆_League.py, streamlit_app.py, data.py, ai_summary.py, requirements.txt, pyproject.toml, uv.lock, test_streamlit_app.py, tests/test_league_scorecard_fields.py, tests/test_league_scorecard_read.py, features/** -->

**Goal:** A found-field update set can be written into an arbitrary mapping of widget keys exactly once, and the same selected image can be recognised so no second read is attempted.

**Changes:**
- `league_scorecard.py`: extend imports with `import hashlib` and `from collections.abc import MutableMapping as AbcMutableMapping`.
- `league_scorecard.py` function `apply_scorecard_updates(updates: Mapping[str, ScorecardFieldValue], widget_keys: Mapping[str, str], session_state: MutableMapping[str, Any]) -> list[str]` (annotate the third parameter with the typing `MutableMapping`; do not import Streamlit): iterate `LEAGUE_SCORECARD_FIELD_KEYS` in order; when `field in updates` **and** `field in widget_keys`, assign `session_state[widget_keys[field]] = updates[field]` and append `field` to the returned list; every other key in `updates` (unknown fields, fields without a widget key) is ignored; return the applied fields in `LEAGUE_SCORECARD_FIELD_KEYS` order. Must be idempotent — calling twice with the same arguments yields the same session state and the same returned list.
- `league_scorecard.py` function `scorecard_upload_fingerprint(file_name: str, payload: bytes) -> str`: `hashlib.sha256(str(file_name).encode("utf-8") + b"\x00" + bytes(payload or b"")).hexdigest()`.
- `tests/test_league_scorecard_state.py` (new file): `import hashlib`, `import pytest`, `from league_scorecard import LEAGUE_SCORECARD_FIELD_KEYS, apply_scorecard_updates, scorecard_upload_fingerprint`. Session state is a plain `dict` created per test — no Streamlit runtime, no fixtures to tear down.

**Definition of done:**
- [ ] `tests/test_league_scorecard_state.py`, test `test_apply_writes_only_found_fields_with_widget_keys`: `state = {"league_sc_net": 99, "league_sc_venue": "Old"}`; `widget_keys = {"date": "league_sc_date", "venue": "league_sc_venue", "net": "league_sc_net"}`; calling with `{"venue": "New", "gross": 77}` returns `["venue"]`, sets `state["league_sc_venue"] == "New"`, leaves `state["league_sc_net"] == 99`, and does not create `league_sc_gross`.
- [ ] `tests/test_league_scorecard_state.py`, test `test_apply_ignores_unknown_fields_and_missing_widget_keys`: updates `{"eagles": 2, "player": "Neo"}` with `widget_keys == {}` returns `[]` and leaves `state == {}`.
- [ ] `tests/test_league_scorecard_state.py`, test `test_apply_returns_fields_in_key_order_and_is_idempotent`: updates for all ten fields with a matching full `widget_keys` map returns `list(LEAGUE_SCORECARD_FIELD_KEYS)`; a second identical call returns the same list and leaves `state` byte-identical (`state == dict(state_copy)`).
- [ ] `tests/test_league_scorecard_state.py`, test `test_fingerprint_is_stable_and_payload_sensitive`: same name/payload gives equal 64-char lowercase hex strings matching `hashlib.sha256(b"a.jpg\x00" + b"x").hexdigest()`; changing the payload or the file name changes the value.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_state.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 4: Wire the picker, prefill and notice into the League page
<!-- phase: 4 -->
<!-- targets: pages/3_🏆_League.py, tests/test_league_scorecard_wiring.py -->
<!-- frozen: league_scorecard.py, streamlit_app.py, data.py, ai_summary.py, requirements.txt, pyproject.toml, uv.lock, test_streamlit_app.py, tests/test_league_scorecard_fields.py, tests/test_league_scorecard_read.py, tests/test_league_scorecard_state.py, features/** -->

**Goal:** The League score form shows a scorecard picker above its ten target fields, pre-fills only found fields into those widgets' session-state keys with an `st.info` notice on failure, and leaves the fields, defaults and Save path otherwise untouched.

**Changes:**
- `pages/3_🏆_League.py`: add `import` at the top after the existing imports: `from league_scorecard import (LEAGUE_SCORECARD_FIELD_KEYS, ScorecardReadResult, apply_scorecard_updates, read_league_scorecard, scorecard_field_updates, scorecard_upload_fingerprint, venue_names_from_records)`. Keep every existing import and `st.set_page_config` call as-is.
- `pages/3_🏆_League.py` module constants near the top (after imports, before the page body):
  ```python
  LEAGUE_SCORECARD_WIDGET_KEYS: dict[str, str] = {
      "date": "league_sc_date",
      "venue": "league_sc_venue",
      "net": "league_sc_net",
      "gross": "league_sc_gross",
      "stableford": "league_sc_stableford",
      "eagles": "league_sc_eagles",
      "birdies": "league_sc_birdies",
      "pars": "league_sc_pars",
      "bogeys": "league_sc_bogeys",
      "double_bogeys_or_worse": "league_sc_double_bogeys_or_worse",
  }
  LEAGUE_SCORECARD_UPLOAD_KEY = "league_scorecard_upload"
  LEAGUE_SCORECARD_LAST_READ_KEY = "league_scorecard_last_read"
  LEAGUE_SCORECARD_NOTICE_KEY = "league_scorecard_notice"
  LEAGUE_SCORECARD_PREFILL_KEY = "league_scorecard_prefill"
  LEAGUE_SCORECARD_SNAPSHOT_KEY = "league_sc_defaults_snapshot"
  AUTOFILL_UNAVAILABLE_NOTICE = "Auto-fill from the scorecard image was unavailable — please enter the values manually."
  ```
  For each of the ten fields, if the existing widget already passes `key=`, use that existing key string in `LEAGUE_SCORECARD_WIDGET_KEYS`; otherwise use the names above.
- `pages/3_🏆_League.py`: add three module-level helpers before the page body:
  - `def _scorecard_widget_default(field: str, fallback: Any) -> dict[str, Any]` — returns `{"key": LEAGUE_SCORECARD_WIDGET_KEYS[field]}` when that key is already in `st.session_state`, else `{"key": LEAGUE_SCORECARD_WIDGET_KEYS[field], "value": fallback}` (use `"index": fallback` instead of `"value"` for `st.selectbox`/`st.radio` widgets, passing the existing index expression as `fallback`).
  - `def _scorecard_known_venues() -> list[str]` — `try: return venue_names_from_records(<the league round records this page has already loaded for the round selector>)` / `except Exception: return []`; pass a list of dicts directly and a pandas DataFrame as `<name>.to_dict("records")`; if no league records are in scope at that point in the script, return `[]` (venue then keeps the text as read).
  - `def _scorecard_defaults_snapshot(**base: object) -> tuple[str, ...]` — `return tuple(f"{name}={value!r}" for name, value in sorted(base.items()))`.
- `pages/3_🏆_League.py`: hoist the ten existing default expressions into locals named `_base_date`, `_base_venue`, `_base_net`, `_base_gross`, `_base_stableford`, `_base_eagles`, `_base_birdies`, `_base_pars`, `_base_bogeys`, `_base_double_bogeys_or_worse` — a pure refactor, the values must be identical to today's (`72/36/0` defaults when creating, the selected round's stored values when editing).
- `pages/3_🏆_League.py`: immediately above the first target widget (that is, above the date/venue/net fields; outside any `st.form` block, so above the `with st.form(...)` line when the score widgets are inside a form), insert in this order:
  1. `_base_values = {"date": _base_date, "venue": _base_venue, "net": _base_net, "gross": _base_gross, "stableford": _base_stableford, "eagles": _base_eagles, "birdies": _base_birdies, "pars": _base_pars, "bogeys": _base_bogeys, "double_bogeys_or_worse": _base_double_bogeys_or_worse}` then `_snapshot = _scorecard_defaults_snapshot(**_base_values)`; when `st.session_state.get(LEAGUE_SCORECARD_SNAPSHOT_KEY) != _snapshot`, loop `for _key in LEAGUE_SCORECARD_WIDGET_KEYS.values(): st.session_state.pop(_key, None)` and store `st.session_state[LEAGUE_SCORECARD_SNAPSHOT_KEY] = _snapshot` (this only pops keys *before* their widgets are created, so switching the round/player still refreshes the form).
  2. `uploaded_scorecard = st.file_uploader("Scorecard image / 记分卡图片（自动填写）", type=None, key=LEAGUE_SCORECARD_UPLOAD_KEY)`.
  3. When `uploaded_scorecard is not None`: `payload = uploaded_scorecard.getvalue()`, `fingerprint = scorecard_upload_fingerprint(uploaded_scorecard.name, payload)`; only when `st.session_state.get(LEAGUE_SCORECARD_LAST_READ_KEY) != fingerprint` do: store the fingerprint, call `result = read_league_scorecard(payload, uploaded_scorecard.type)`, then `updates = scorecard_field_updates(result.found_fields, known_venues=_scorecard_known_venues())`, then either `st.session_state[LEAGUE_SCORECARD_NOTICE_KEY] = AUTOFILL_UNAVAILABLE_NOTICE` and `st.session_state[LEAGUE_SCORECARD_PREFILL_KEY] = {}` when `result.unavailable_reason is not None or not updates`, or `st.session_state.pop(LEAGUE_SCORECARD_NOTICE_KEY, None)` and `st.session_state[LEAGUE_SCORECARD_PREFILL_KEY] = dict(updates)` on success; finish that branch with `st.rerun()` (use `st.experimental_rerun()` only if the pinned Streamlit in `requirements.txt` predates 1.27). Exactly one `read_league_scorecard` call per fingerprint — no retry, cache or queue.
  4. When `uploaded_scorecard is None`: `st.session_state[LEAGUE_SCORECARD_NOTICE_KEY] = AUTOFILL_UNAVAILABLE_NOTICE`.
  5. When `st.session_state.get(LEAGUE_SCORECARD_NOTICE_KEY)`: `st.info(st.session_state[LEAGUE_SCORECARD_NOTICE_KEY])` — never `st.error`, never `st.stop`, no traceback.
  6. `_prefill = st.session_state.pop(LEAGUE_SCORECARD_PREFILL_KEY, {}) or {}` then `for _field, _value in _prefill.items(): if _field in LEAGUE_SCORECARD_WIDGET_KEYS: st.session_state[LEAGUE_SCORECARD_WIDGET_KEYS[_field]] = _value` (applies each prefill exactly once; `apply_scorecard_updates` is exercised by the Phase 3 tests and may be used here instead of the loop, passing `LEAGUE_SCORECARD_WIDGET_KEYS` and `st.session_state`).
- `pages/3_🏆_League.py`: for each of the ten target widgets, keep the existing label, order, container/column layout, `min_value`/`max_value`/`step`/`help` arguments and add `**_scorecard_widget_default("<field>", _base_<field>)`. Do **not** change widget types, labels, ordering, or the ten defaults; when the date widget is `st.date_input`, convert a pre-filled ISO string with `date.fromisoformat(...)` inside a `try/except ValueError` before writing it into session state, and when the venue/date widget is a `st.selectbox`, drop that update instead of writing a value that is not among its options.
- `pages/3_🏆_League.py`: do not touch anything below the ten widgets — the Save button, the round mutation code and the existing `github_upload_image(...)` call stay byte-identical.
- `tests/test_league_scorecard_wiring.py` (new file): `import pathlib`, `import re`, `import pytest`, `from league_scorecard import LEAGUE_SCORECARD_FIELD_KEYS`. Read the page with `LEAGUE_PAGE = pathlib.Path("pages/3_🏆_League.py").read_text(encoding="utf-8")` in a module-level constant (no fixtures, no imports of the page module, no Streamlit runtime, nothing to tear down).

**Definition of done:**
- [ ] `tests/test_league_scorecard_wiring.py`, test `test_picker_is_rendered_with_its_own_key`: asserts `"st.file_uploader("` in the page source, `"LEAGUE_SCORECARD_UPLOAD_KEY"` in it, `'type=None'` in it, and that the `st.file_uploader(` call's character offset is smaller than the offset of `"_base_net"` (the picker renders above the fields).
- [ ] `tests/test_league_scorecard_wiring.py`, test `test_all_ten_widget_keys_are_wired`: for every field in `LEAGUE_SCORECARD_FIELD_KEYS`, asserts `f'"{field}": "league_sc_'` appears in the page (the `LEAGUE_SCORECARD_WIDGET_KEYS` entry) and that `f'_scorecard_widget_default("{field}"'` appears at least once.
- [ ] `tests/test_league_scorecard_wiring.py`, test `test_read_and_filter_helpers_are_used`: asserts `"read_league_scorecard("`, `"scorecard_field_updates("`, `"scorecard_upload_fingerprint("`, `"venue_names_from_records("` and `"st.rerun()"` all appear in the page source.
- [ ] `tests/test_league_scorecard_wiring.py`, test `test_unavailable_notice_is_informational_only`: asserts `"AUTOFILL_UNAVAILABLE_NOTICE"` and `"st.info("` appear, and that neither `"st.error(AUTOFILL_UNAVAILABLE_NOTICE"` nor `"st.stop("` appears anywhere in the page.
- [ ] `tests/test_league_scorecard_wiring.py`, test `test_save_path_still_uploads_exactly_once`: asserts `page_source.count("github_upload_image(") == 1` and that the offset of `"github_upload_image("` is greater than the offset of `"st.file_uploader("` (the upload call remains in the unchanged Save path).
- [ ] `tests/test_league_scorecard_wiring.py`, test `test_no_other_page_leaks_the_notice`: for every `pathlib.Path("pages").glob("*.py")` other than `3_🏆_League.py`, asserts `"AUTOFILL_UNAVAILABLE_NOTICE" not in text` and `"read_league_scorecard" not in text` (spec behaviour 15: nothing from a failed read is visible on other pages).
- [ ] `tests/test_league_scorecard_wiring.py`, test `test_autofill_never_persists_without_save`: asserts `"github_upload_image"` and `"read_league_scorecard"` never appear on the same line (`assert not any("github_upload_image" in line and "read_league_scorecard" in line for line in LEAGUE_PAGE.splitlines())`), proving the extraction result is never saved independently of Save.
- [ ] `tests/test_league_scorecard_wiring.py`, test `test_existing_field_defaults_unchanged`: asserts the literal default expressions still in the source: `"72"` and `"36"` and `"0"` each appear in the hoisted base-value lines (`_base_` substring present in the same line) so the today-defaults are intact.
- [ ] `tests/test_league_scorecard_wiring.py`, test `test_snapshot_reset_guard_present`: asserts `"LEAGUE_SCORECARD_SNAPSHOT_KEY"` and `"st.session_state.pop(_key, None)"` (or the equivalent `st.session_state.pop(LEAGUE_SCORECARD_WIDGET_KEYS[_field], None)`) appear in the page, so a switched round clears stale widget state.
- [ ] `tests/test_league_scorecard_wiring.py`, test `test_prefill_is_applied_from_session_state`: asserts the substring `"_prefill = st.session_state.pop(LEAGUE_SCORECARD_PREFILL_KEY"` (or `apply_scorecard_updates(updates, LEAGUE_SCORECARD_WIDGET_KEYS, st.session_state)`) appears, so found fields reach `st.session_state` before Save.
- [ ] Manual reviewer check (not part of Verify): `git diff sdlc/011-league-admin-score-form-a-scorecard/approved -- "pages/3_🏆_League.py"` shows only the import block, the new constants/helpers, the picker/notice/prefill block and `key=`/default plumbing on the ten widgets — no change to labels, ordering, `min_value`/`max_value`/`step`, the Save button, the round mutation code or the `github_upload_image` call.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_wiring.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks

- **Existing widget types/keys are not known when writing this plan.** If the League form uses `st.selectbox` for date or venue, or already assigns different `key=` values, Phase 4's `_scorecard_widget_default` and `LEAGUE_SCORECARD_WIDGET_KEYS` must follow the real widgets; the Phase 4 test `test_all_ten_widget_keys_are_wired` and the manual diff check catch a mismatch.
- **Writing `st.session_state` after a widget is created raises `StreamlitAPIException`.** All prefill writes and the snapshot `pop` are specified to happen before the ten widgets are instantiated in the same run; the picker block ends in `st.rerun()`, so the write and the widget render never share a run. Any reordering shows up as a runtime exception during the reviewer's manual check.
- **Session-state keys freezing the form when the admin switches player/round.** Mitigated by the `LEAGUE_SCORECARD_SNAPSHOT_KEY` reset (Phase 4, `test_snapshot_reset_guard_present`); if the base-value expressions are computed from anything other than the selected round, the reset will fire too often and silently blank the auto-fill — Phase 4's manual check covers it.
- **Venue matching has no data source in `read_league_scorecard`.** The page supplies `known_venues` via `_scorecard_known_venues()`; if it returns `[]`, venues stay as read (the documented fallback) and behaviour 6's "closest existing venue" silently degrades. Phase 3's `test_match_venue_name_prefers_known_venue` proves the matcher itself; the wiring test only proves the call exists.
- **Model/secret names.** `_scorecard_model()` prefers `OLLAMA_SCORECARD_MODEL`/`OLLAMA_MODEL` env/secrets and falls back to `glm-5.3-flash:cloud`; if the app already stores the model under a different secrets key, the request is still well-formed but may target the default model. Phase 2's `test_request_payload_and_timeout` and `test_model_env_override` pin the behaviour.
- **Network flakiness or accidental real calls in tests.** Every Phase 2 test monkeypatches `_post_ollama_generate`; a missing monkeypatch makes `test_unsupported_mime_sends_no_request` fail fast rather than hang.
- **`st.rerun()` availability.** Streamlit 1.27+ provides it; Phase 4 instructs the fallback to `st.experimental_rerun()` for older pins, and any wrong call surfaces immediately in the manual run.
- **Existing source-assertion tests.** `tests/test_league_deep_dive_wiring.py`, `tests/test_league_follow_up_wiring.py` and `tests/test_theme_button_styles.py` read page sources; they are frozen and re-run by the final `python -m pytest -q` job, which catches any accidental removal of an existing string.

## Open questions

- Date format: assumed the app's existing date format is ISO `YYYY-MM-DD`, and that the date widget is `st.date_input` or `st.text_input`. If it is a select box of dates, the prefill drops the date update rather than guessing (assumption: safer to keep the prior value).
- Known venue list source: assumed the page can pass the league round records it already loads (`list[dict]` or `DataFrame.to_dict("records")`); when it cannot, `_scorecard_known_venues()` returns `[]` and venues are kept as read.
- Model and credentials: assumed the model name comes from `OLLAMA_SCORECARD_MODEL`/`OLLAMA_MODEL` (env or Streamlit secrets) and that `glm-5.3-flash:cloud` is the correct default; assumed `OLLAMA_API_KEY`/`OLLAMA_KEY` is the bearer token name. If the app's existing key differs, only `_ollama_api_key()`/`_scorecard_model()` need changing (Phase 2).
- Image type handling: assumed `st.file_uploader(type=None)` (all file types) is acceptable so the unsupported-type path in behaviour 12 is reachable; the reader sniffs magic bytes and treats anything else as "unsupported file type".
- Widget keys: assumed adding `key=` values to the ten target widgets only, leaving every other widget untouched, is an acceptable change under "otherwise unchanged in layout, fields and defaults".

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/011-league-admin-score-form-a-scorecard/build-log.md` with one section per phase, in order. Head each
   one `## Phase <n>: <title>`, then list the files changed, the Verify command
   you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/011-league-admin-score-form-a-scorecard`.

Commit only this plan's targets and `build-log.md`. Leave every other file alone,
including other features' documents under `sdlc/features/`, even for formatting;
verification fails on any file outside the targets.

The pipeline waits for this file. Once it has a section for every phase, it
verifies the whole branch and opens the pull request.

