<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@a2eb70e -->
## Approach
Add a small, dependency-free `scorecard_extraction.py` that validates JPG/PNG bytes, calls a fakeable Ollama vision extractor, and returns only confidently extracted fields; then add one page-level upload helper in `pages/3_🏆_League.py` that renders the uploader above the existing League score form, normalises date/venue, and feeds the draft in as editable widget defaults while the existing save path still saves the visible widget values. Failure paths render only a non-blocking League-page notice and return `None`, leaving today’s manual form intact.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| The League score form shows a JPG/PNG scorecard upload control above the form fields. | 1 | Phase 2 |
| Uploading a readable scorecard fills in date, venue, net, gross, stableford, and each eagle/birdie/par/bogey/double-bogey count for a card that contains them, without the admin retyping them. | 2, 3, 13, 14 | Phase 1, Phase 2 |
| Pre-filled values stay editable, and saving stores what the admin sees on screen after any corrections. | 5, 6, 7 | Phase 2 |
| If there is no upload, the image is unreadable, the file type is unsupported, or the vision service errors or times out, the form still renders with empty manual entry fields, the admin is told auto-fill was unavailable, and no error is shown to players or other pages. | 8, 9, 10, 11, 12 | Phase 1, Phase 2, Phase 3 |
| Any field the extraction could not determine is left blank for manual entry rather than guessed or defaulted. | 4 | Phase 1 |
| The existing tests still pass. | 15 | Phase 3 |

## Phase 1: Core scorecard extraction and normalisation
<!-- phase: 1 -->
<!-- targets: scorecard_extraction.py, tests/test_scorecard_extraction.py -->
<!-- frozen: tests/test_league_deep_dive_wiring.py, tests/test_league_follow_up_wiring.py -->

**Goal:** A reviewer can prove that JPG/PNG validation, partial extraction, date normalisation, venue matching and every failure path are implemented without network access or page code.

**Changes:**
- `scorecard_extraction.py` (new): standard-library module using `dataclasses.dataclass`, `collections.abc.Callable, Mapping, Sequence`, `typing.TypeAlias`, `datetime`, `base64`, `json`, `re`, `urllib.request`, and guarded `streamlit` secret reads.
- Define exactly:
  - `VisionExtractor: TypeAlias = Callable[[bytes, str], Mapping[str, object]]`
  - `@dataclass(frozen=True) class ScorecardDraft` with fields and defaults exactly matching the spec: `date: str | None = None`, `venue: str | None = None`, `net: int | None = None`, `gross: int | None = None`, `stableford: int | None = None`, `eagle_count: int | None = None`, `birdie_count: int | None = None`, `par_count: int | None = None`, `bogey_count: int | None = None`, `double_bogey_or_worse_count: int | None = None`.
  - `extract_scorecard_fields(image_bytes: bytes | None, mime_type: str | None, *, vision_extractor: VisionExtractor | None = None) -> ScorecardDraft | None`
  - `normalise_scorecard_date(raw_date: str | None) -> str | None`
  - `match_scorecard_venue(raw_venue: str | None, known_venues: Sequence[str]) -> str | None`
  - Internal `class ScorecardExtractionError(Exception)`.
- Constants: `OLLAMA_CHAT_URL = "https://ollama.com/api/chat"`, `OLLAMA_API_KEY_SECRET = "OLLAMA_API_KEY"`, `SCORECARD_VISION_MODEL = "glm-5.3-flash:cloud"`, `REQUEST_TIMEOUT_SECONDS = 30`, `SUPPORTED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png"}`, `SCORECARD_PROMPT` asking for one JSON object with keys `date`, `venue`, `net`, `gross`, `stableford`, `eagle_count`, `birdie_count`, `par_count`, `bogey_count`, `double_bogey_or_worse_count`, using `null` for uncertain fields.
- `normalise_scorecard_date`: strip; accept `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD`, `YYYY年MM月DD日`, and `YYYYMMDD`; validate with `datetime(year, month, day).date().isoformat()`; return `None` on blank, non-string, invalid month/day, or unparseable input; never raise.
- `match_scorecard_venue`: return `None` for blank/None; strip raw text; compare `casefold()` against each `known.strip().casefold()`; return the exact known spelling on match, otherwise the stripped raw text; never raise.
- `_is_supported_mime(mime_type)`: lower/strip and accept only `image/jpeg`, `image/jpg`, `image/png`.
- `_has_valid_image_signature(image_bytes, mime_type)`: JPEG must start with `b"\xff\xd8\xff"`; PNG must start with `b"\x89PNG\r\n\x1a\n"`; return `False` otherwise.
- `_coerce_int(value)`: `None`/blank/unparseable -> `None`; reject `bool`; `int` -> itself; integral `float` -> `int`; string -> `int(str.strip())`; never raise.
- `_coerce_text(value)`: `None` -> `None`; otherwise stripped `str(value)` or `None` when empty.
- `_draft_from_mapping(raw: Mapping[str, object]) -> ScorecardDraft`: read only the ten supported keys; ignore unknown keys; missing or invalid per-field values become `None`.
- `_default_vision_extractor(image_bytes: bytes, mime_type: str) -> Mapping[str, object]`: read `st.secrets.get("OLLAMA_API_KEY", "")` inside `try/except Exception`; missing key raises `ScorecardExtractionError`; base64-encode image; POST JSON to `OLLAMA_CHAT_URL` with headers `Content-Type: application/json` and `Authorization: Bearer <key>`, payload `{"model": SCORECARD_VISION_MODEL, "stream": False, "messages": [{"role": "system", "content": "You extract golf scorecard fields. Return only a JSON object."}, {"role": "user", "content": SCORECARD_PROMPT, "images": [<base64>]}]}`, timeout `30`; require HTTP 200/201; read `body["message"]["content"]`; strip Markdown fences and take the first `{` to last `}` before `json.loads`; return the parsed `dict`. Any HTTP, timeout, JSON, shape or empty-content exception raises `ScorecardExtractionError` from the original exception.
- `extract_scorecard_fields`: return `None` when `image_bytes` is falsy, MIME is unsupported/None, or the bytes do not match the MIME signature. Choose `vision_extractor or _default_vision_extractor`; call inside `try/except Exception` and return `None` on any exception. Return `None` when the result is not a `Mapping`. Build the draft with `_draft_from_mapping`; return `None` when every draft field is `None`; otherwise return the draft. No exception escapes.
- `tests/test_scorecard_extraction.py` (new): pytest tests only, no network, no Streamlit app execution, no teardown fixtures needed.

**Definition of done:**
- [ ] `tests/test_scorecard_extraction.py`, test `test_draft_defaults_are_all_none`: `ScorecardDraft()` has all ten fields `None`.
- [ ] `tests/test_scorecard_extraction.py`, test `test_normalise_scorecard_date_accepts_common_formats_and_rejects_invalid`: assert `"2026-06-23"`, `"2026/6/23"`, `"2026.06.23"`, `"2026年6月23日"`, `" 2026-6-3 "` all become `"2026-06-23"`/`"2026-06-03"` as appropriate; assert `None` for `None`, `""`, `"not a date"`, `"2026-02-31"`.
- [ ] `tests/test_scorecard_extraction.py`, test `test_match_scorecard_venue_is_case_and_whitespace_insensitive`: with `["Pine Valley", "Augusta National"]`, `" pine valley "` returns `"Pine Valley"`, `"Unknown Course"` returns `"Unknown Course"`, `None` returns `None`.
- [ ] `tests/test_scorecard_extraction.py`, test `test_extract_returns_none_for_no_upload_unsupported_mime_or_bad_signature`: assert `None` for `(None, "image/png")`, `(b"", "image/png")`, `(b"abc", "image/gif")`, `(b"abc", None)`, and `(b"not a png", "image/png")`; assert the fake extractor is never called in those cases.
- [ ] `tests/test_scorecard_extraction.py`, test `test_extract_returns_partial_draft_for_supported_png`: use valid PNG magic bytes plus arbitrary trailing bytes; fake extractor returns `{"date": "2026/6/23", "venue": " Pine Valley ", "net": "-2", "gross": 75, "stableford": None, "eagle_count": 1, "birdie_count": "2", "par_count": 10, "bogey_count": 4, "double_bogey_or_worse_count": 1, "ignored": "x"}`; assert `draft.net == -2`, `draft.stableford is None`, `draft.birdie_count == 2`, and no `ignored` attribute.
- [ ] `tests/test_scorecard_extraction.py`, test `test_extract_returns_none_when_extractor_raises_times_out_or_is_malformed`: fake extractor raises `RuntimeError`, raises `TimeoutError`, returns `None`, returns `[]`, returns `{}`, and returns `{"date": None, "gross": "abc"}`; each call returns `None` and does not raise.
- [ ] `tests/test_scorecard_extraction.py`, test `test_extract_returns_none_when_mime_or_bytes_missing`: assert `extract_scorecard_fields(b"\x89PNG\r\n\x1a\n", None, vision_extractor=pytest.fail) is None`.
- [ ] No `requirements.txt`, `pyproject.toml`, `uv.lock`, `data.py`, `ai_summary.py`, or existing test file is changed.

**Verify:**
```bash
python -m pytest tests/test_scorecard_extraction.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: League upload control and editable prefill
<!-- phase: 2 -->
<!-- targets: pages/3_🏆_League.py, tests/test_league_scorecard_upload_wiring.py -->
<!-- frozen: scorecard_extraction.py, data.py, ai_summary.py, tests/test_league_deep_dive_wiring.py, tests/test_league_follow_up_wiring.py -->

**Goal:** A reviewer can prove the League page renders the uploader above the score form, feeds successful extraction into editable widget defaults, and still saves the widget values the admin sees.

**Changes:**
- `pages/3_🏆_League.py`: add imports `hashlib`, `os`, `from collections.abc import Sequence`, `from dataclasses import replace`, and `from scorecard_extraction import ScorecardDraft, VisionExtractor, extract_scorecard_fields, match_scorecard_venue, normalise_scorecard_date`.
- Add page constants:
  - `SCORECARD_UPLOAD_LABEL = "记分卡图片 / Scorecard image (JPG/PNG)"`
  - `SCORECARD_UPLOAD_KEY = "league_scorecard_upload"`
  - `SCORECARD_UPLOAD_REVISION_KEY = "_league_scorecard_upload_revision"`
  - `SCORECARD_UPLOAD_NOTICE = "自动填充不可用：请上传 JPG/PNG 记分卡图片，或手动填写。"`
  - `SCORECARD_UPLOAD_FAILED_NOTICE = "自动填充不可用：无法读取该记分卡，请手动填写。"`
  - `SCORECARD_UPLOAD_SUCCESS_NOTICE = "已识别记分卡，请核对并修改下方数值。"`
- Add exactly:
  ```python
  def render_league_scorecard_upload(
      known_venues: Sequence[str],
      *,
      key: str = "league_scorecard_upload",
      vision_extractor: VisionExtractor | None = None,
  ) -> ScorecardDraft | None:
  ```
  Behaviour: call `st.file_uploader(SCORECARD_UPLOAD_LABEL, type=["jpg", "jpeg", "png"], key=key)`; if no upload, `st.info(SCORECARD_UPLOAD_NOTICE)`, set `st.session_state[SCORECARD_UPLOAD_REVISION_KEY] = "manual"`, return `None`. If upload exists, read `file_name = str(getattr(uploaded_file, "name", "") or "")`, `extension = os.path.splitext(file_name)[1].lower()`, `mime_type = getattr(uploaded_file, "type", None)`, `image_bytes = uploaded_file.getvalue()`; if extension not in `{".jpg", ".jpeg", ".png"}` or MIME not in `{"image/jpeg", "image/jpg", "image/png"}` or `image_bytes` is falsy, `st.info(SCORECARD_UPLOAD_FAILED_NOTICE)`, set revision `"manual"`, return `None`. Call `extract_scorecard_fields(image_bytes, mime_type, vision_extractor=vision_extractor)`; if `None`, same failed notice/revision/return. On success, `draft = replace(draft, date=normalise_scorecard_date(draft.date), venue=match_scorecard_venue(draft.venue, known_venues))`, call `st.caption(SCORECARD_UPLOAD_SUCCESS_NOTICE)`, set `st.session_state[SCORECARD_UPLOAD_REVISION_KEY] = hashlib.sha256(image_bytes).hexdigest()[:12]`, return `draft`.
- Add page-local `def _league_known_venues() -> list[str]:` using `from data import load_scores`; return `sorted({str(v).strip() for v in scores["Venue"].dropna() if str(v).strip()})` when `scores` has a `Venue` column, otherwise `[]`; wrap the import/load in `try/except Exception` and return `[]` on failure.
- Add page-local `def _draft_date(value: str | None) -> date | None:` returning `datetime.strptime(value, "%Y-%m-%d").date()` when `value` is truthy and matches, otherwise `None`.
- Give the existing League score-entry form the stable form key `"league_score_entry"`; keep its label and submit button unchanged.
- Immediately before `with st.form("league_score_entry", ...):`, insert `scorecard_draft = render_league_scorecard_upload(_league_known_venues())`.
- In the form widgets, use the draft only as initial/editable values and keep editing enabled:
  - date input key `league_score_date`, value `_draft_date(scorecard_draft.date) if scorecard_draft else None`;
  - venue text input key `league_score_venue`, value `scorecard_draft.venue if scorecard_draft and scorecard_draft.venue is not None else ""`;
  - net/gross/stableford number inputs keys `league_score_net`, `league_score_gross`, `league_score_stableford`, value `scorecard_draft.<field> if scorecard_draft and scorecard_draft.<field> is not None else None`;
  - count number inputs keys `league_score_eagle`, `league_score_birdie`, `league_score_par`, `league_score_bogey`, `league_score_double_bogey_or_worse`, value from the matching `ScorecardDraft` field or `None`.
- In the existing submit block, keep using the local widget variables returned by the widgets, never `scorecard_draft`. For the five count widgets, convert `None` to `0` before building the saved row to preserve the existing default-zero count behaviour; for date/venue/net/gross/stableford, keep the existing validation/error path and do not save when a required value is blank.
- `tests/test_league_scorecard_upload_wiring.py` (new): use `pathlib.Path`, `ast`, `dataclasses.replace`, `hashlib`, `os`, `re`, and pytest. It must not run Streamlit, start servers, or touch the network.

**Definition of done:**
- [ ] `tests/test_league_scorecard_upload_wiring.py`, test `test_league_score_form_renders_upload_above_form`: read `pages/3_🏆_League.py` as UTF-8 text; assert `"def render_league_scorecard_upload("` exists, `st.file_uploader` is called with `type=["jpg", "jpeg", "png"]`, and `source.index("scorecard_draft = render_league_scorecard_upload(") < source.index('with st.form("league_score_entry"')`. This proves spec 1.
- [ ] `tests/test_league_scorecard_upload_wiring.py`, test `test_league_score_form_uses_draft_as_editable_defaults`: read the page source and assert it contains `scorecard_draft.date`, `.venue`, `.net`, `.gross`, `.stableford`, `.eagle_count`, `.birdie_count`, `.par_count`, `.bogey_count`, `.double_bogey_or_worse_count`, plus keys `league_score_date`, `league_score_venue`, `league_score_net`, `league_score_gross`, `league_score_stableford`, `league_score_eagle`, `league_score_birdie`, `league_score_par`, `league_score_bogey`, `league_score_double_bogey_or_worse`. This proves specs 2, 4 and 5.
- [ ] `tests/test_league_scorecard_upload_wiring.py`, test `test_league_score_form_submit_does_not_read_stale_draft`: isolate the source from `source.index("if submitted:")` onward and assert `"scorecard_draft" not in submit_source`; assert the submit source contains the five count widget variable conversions to zero and no assignment from `scorecard_draft`. This proves specs 6 and 7.
- [ ] `tests/test_league_scorecard_upload_wiring.py`, test helper loader `_load_page_helper()`: parse the page source with `ast.parse`, find the `FunctionDef` named `render_league_scorecard_upload`, compile it as a module containing only that function, and exec it with globals for `st`, `extract_scorecard_fields`, `normalise_scorecard_date` (real), `match_scorecard_venue` (real), `replace` (real), `hashlib`, `os`, `ScorecardDraft`, `VisionExtractor`, and the six page notice/key constants. The fake `st` object records `.info()`, `.caption()`, `.file_uploader()`, and uses a plain dict for `.session_state`.
- [ ] `tests/test_league_scorecard_upload_wiring.py`, test `test_upload_helper_returns_none_without_upload`: fake `file_uploader` returns `None`; assert helper returns `None`, `fake_st.info` received `SCORECARD_UPLOAD_NOTICE`, and `session_state[SCORECARD_UPLOAD_REVISION_KEY] == "manual"`. This proves spec 8.
- [ ] `tests/test_league_scorecard_upload_wiring.py`, test `test_upload_helper_rejects_unsupported_extension_or_mime`: fake upload has `name="card.gif"`, `type="image/gif"`, `getvalue()` returns `b"abc"`; assert helper returns `None`, `st.info` received `SCORECARD_UPLOAD_FAILED_NOTICE`, and `extract_scorecard_fields` was not called. This proves spec 9.
- [ ] `tests/test_league_scorecard_upload_wiring.py`, test `test_upload_helper_returns_none_when_extraction_fails`: fake upload has valid `.png` name, `type="image/png"`, and valid PNG magic bytes; injected extractor returns `None`; assert helper returns `None` and `st.info` received `SCORECARD_UPLOAD_FAILED_NOTICE`. This proves specs 10 and 11 at the page seam.
- [ ] `tests/test_league_scorecard_upload_wiring.py`, test `test_upload_helper_normalises_successful_draft`: fake upload has valid `.png` name/type/bytes; injected extractor returns `ScorecardDraft(date="2026/6/23", venue=" pine valley ", net=2, gross=80, stableford=30, eagle_count=None, birdie_count=1, par_count=8, bogey_count=5, double_bogey_or_worse_count=2)`; call helper with `known_venues=["Pine Valley"]`; assert returned `date == "2026-06-23"`, `venue == "Pine Valley"`, `net == 2`, `eagle_count is None`, `st.caption` received `SCORECARD_UPLOAD_SUCCESS_NOTICE`, and `session_state[SCORECARD_UPLOAD_REVISION_KEY] == hashlib.sha256(valid_png_bytes).hexdigest()[:12]`. This proves specs 2, 13 and 14.
- [ ] No change to `scorecard_extraction.py`, `data.py`, `ai_summary.py`, or any existing test file; no background threads, servers, `st.rerun`, or network access in tests.

**Verify:**
```bash
python -m pytest tests/test_league_scorecard_upload_wiring.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 3: Cross-page fallback isolation and regression guard
<!-- phase: 3 -->
<!-- targets: tests/test_scorecard_scope_isolation.py -->
<!-- frozen: pages/3_🏆_League.py, pages/4_🥊_Cup.py, pages/5_⛳_Outing.py, streamlit_app.py, scorecard_extraction.py -->

**Goal:** A reviewer can prove the auto-fill notice and extraction code are confined to the League page and cannot appear on player-facing or other tournament pages.

**Changes:**
- `tests/test_scorecard_scope_isolation.py` (new): pytest source-level regression test using `pathlib.Path` only.
- Test `test_other_pages_do_not_reference_scorecard_autofill`: for each of `pages/4_🥊_Cup.py`, `pages/5_⛳_Outing.py`, and `streamlit_app.py`, read UTF-8 text and assert none of these strings occur: `"scorecard_extraction"`, `"render_league_scorecard_upload"`, `"league_scorecard_upload"`, `"自动填充不可用"`, `"SCORECARD_UPLOAD_FAILED_NOTICE"`.
- Test `test_league_page_owns_the_scorecard_upload_control`: read `pages/3_🏆_League.py` and assert it contains `"def render_league_scorecard_upload("`, `"st.file_uploader("`, and `"SCORECARD_UPLOAD_FAILED_NOTICE"`.
- No production file is modified in this phase.

**Definition of done:**
- [ ] `tests/test_scorecard_scope_isolation.py`, test `test_other_pages_do_not_reference_scorecard_autofill`: Cup, Outing and root app sources contain no scorecard-extraction imports, no League upload key, and no auto-fill-unavailable notice text. This proves spec 12.
- [ ] `tests/test_scorecard_scope_isolation.py`, test `test_league_page_owns_the_scorecard_upload_control`: the League page contains the upload helper and failure notice. This guards the Phase 2 wiring.
- [ ] The pipeline’s final `python -m pytest -q && behave --format progress` run collects and passes all pre-existing tests; this phase does not edit any existing test file. This proves spec 15.
- [ ] No source file other than `tests/test_scorecard_scope_isolation.py` is changed in this phase.

**Verify:**
```bash
python -m pytest tests/test_scorecard_scope_isolation.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- Ollama Cloud may not accept the native `messages[].images` payload for `glm-5.3-flash:cloud`; Phase 1 catches every transport/shape failure and returns `None`, and the page test injects a fake extractor, so production failure degrades to manual entry rather than raising.
- Streamlit widget state can retain old defaults after a new upload; Phase 2 gives every score widget a stable key and records an upload revision hash, and the wiring test checks the helper sets that revision. If the page does not actually rebuild widgets on revision change, Phase 2’s save test plus manual check of a second upload will expose it.
- `st.number_input(value=None)` availability depends on the installed Streamlit version; Phase 2’s source/wiring tests will show whether the blank-default approach is present, and the final regression run catches import/render failures.
- `data.load_scores()` or a `Venue` column may not exist; Phase 2’s `_league_known_venues()` fails closed to `[]`, so extracted venue text is kept and the unit-tested matching still works when a list is supplied.
- The existing save block may require non-`None` numeric values; Phase 2 explicitly converts blank count widgets to `0` and keeps existing required-field validation for date/venue/net/gross/stableford, and the submit-source test prevents saving the stale draft object.

## Open questions
- Assumed `data.load_scores()` exists and returns a DataFrame with a `Venue` column for known-venue matching; if not, `_league_known_venues()` returns `[]` and venue matching keeps the extracted text.
- Assumed the installed Streamlit supports `st.number_input(..., value=None)` so undetermined fields render blank; if it does not, the Phase 2 blank-field tests will fail and this plan should be revised to use empty text inputs parsed on submit.
- Assumed Ollama Cloud uses the native `/api/chat` `images` field for `glm-5.3-flash:cloud`; production failures are intentionally swallowed by `extract_scorecard_fields` and covered by injected-fake tests.

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

