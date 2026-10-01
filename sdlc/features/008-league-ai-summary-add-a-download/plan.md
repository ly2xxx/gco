<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@f8c1146 -->
## Approach
Keep every change inside the two shared modules this feature already owns. Add two pure helpers to `ai_summary.py` — one that assembles the plain-text transcript (sanitized, answered-only, de-duplicated, in stored order) and one that builds a stable, filesystem-safe `.txt` name — then extend the existing `render_follow_up_questions` fragment so it renders exactly one `st.download_button` after the form and after every Q&A turn, built from those helpers on the history read at that point in the render. Finally widen `theme.py`'s existing `.stButton > button` rule and its `:hover` rule to also cover Streamlit's form-submit and download button elements, leaving every other rule and declaration byte-identical. No page file, prompt, Q&A behaviour, or on-screen transcript changes.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| A 下载 / Download control is visible directly under the follow-up Q&A in the League page, within the same fragment, and is discoverable without scrolling past unrelated sections. | 1, 2, 3 | Phase 2 |
| Clicking it produces a file download whose name ends in `.txt` and whose contents include the AI season summary text. | 4, 11, 12, 14 | Phase 2 (helpers land in Phase 1) |
| The downloaded file contains every follow-up question that was asked, each paired with its answer, in the order asked, and contains no duplicated or empty Q&A entries. | 5, 6, 7, 8, 14 | Phase 2 (assembly in Phase 1) |
| The file is legible as plain text — no HTML tags, markdown fences, or other rendering artefacts from the on-screen display. | 10 | Phase 1 (sanitizer; observable in the Phase 2 download data) |
| The follow-up form submit button and the download button render in the theme's green button style and are visually consistent with the app's other primary buttons; other pages are unaffected. | 16, 17, 18 | Phase 3 |
| The existing tests still pass. | 19 | Phases 1–3 |

## Phase 1: Transcript text and file-name helpers
<!-- phase: 1 -->
<!-- targets: ai_summary.py, tests/test_ai_transcript_text.py -->
<!-- frozen: theme.py, pages/3_🏆_League.py, tests/test_ai_follow_up_logic.py, tests/test_ai_follow_up_ui.py, tests/test_league_follow_up_wiring.py -->

**Goal:** `build_transcript_text` and `build_transcript_filename` exist in `ai_summary.py` and return sanitized, ordered, de-duplicated plain text and a stable, filesystem-safe `.txt` name, proven by new unit tests with no UI involved.

**Changes:**
- `ai_summary.py` — imports: keep `from __future__ import annotations` first, then extend the stdlib group to exactly
  ```python
  import json
  import re
  import urllib.error
  import urllib.request
  from datetime import datetime

  import streamlit as st
  ```
- `ai_summary.py` — add these module-level constants immediately after `MISSING_ROUNDS_NOTE_EN` and before `class AISummaryError` (exact names, values and annotations from the spec):
  ```python
  DOWNLOAD_BUTTON_LABEL: str = "⬇️ 下载 / Download"
  DOWNLOAD_BUTTON_KEY: str = "ai_season_summary_download"
  TRANSCRIPT_MIME_TYPE: str = "text/plain"
  TRANSCRIPT_FILE_EXTENSION: str = ".txt"
  TRANSCRIPT_FILENAME_PREFIX: str = "gco_league_ai_summary"
  TRANSCRIPT_SUMMARY_HEADING: str = "AI 赛季总结 / AI Season Summary"
  TRANSCRIPT_QA_HEADING: str = "追问与回答 / Follow-up Q&A"
  ```
- `ai_summary.py` — add these private module-level regexes next to the constants:
  ```python
  _HTML_BREAK_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
  _HTML_TAG_RE = re.compile(r"<[^>]+>")
  _UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')
  _FILENAME_WHITESPACE_RE = re.compile(r"\s+")
  ```
- `ai_summary.py` — add the following four definitions immediately after `append_follow_up_turn` and before `render_season_summary`, verbatim in behaviour:
  ```python
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
      The stem is never empty and the result never contains / \ : * ? " < > |. Never raises."""
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
  ```
- `tests/test_ai_transcript_text.py` (new): imports `datetime` and `import ai_summary as m`; no fixtures, no monkeypatching, no teardown needed — every function under test is pure.

**Definition of done:**
- [ ] `tests/test_ai_transcript_text.py::test_transcript_contains_headings_and_summary`: proves behaviours 3, 4 (assembly) — `m.build_transcript_text("Neo", "SUMMARY_BODY_MARKER", None)`; assert `m.TRANSCRIPT_SUMMARY_HEADING in text`, `"SUMMARY_BODY_MARKER" in text`, `m.TRANSCRIPT_QA_HEADING in text`, `text.endswith("\n")`, `"<" not in text`.
- [ ] `tests/test_ai_transcript_text.py::test_question_before_answer_with_bilingual_prefixes`: proves behaviour 5 — history `[{"question": "Q1", "answer": "A1"}]`; assert `"问 / Q: Q1" in text`, `"答 / A: A1" in text`, `text.index("问 / Q: Q1") < text.index("答 / A: A1")`.
- [ ] `tests/test_ai_transcript_text.py::test_turns_keep_stored_order_and_appear_once`: proves behaviour 6 — three sequential turns; assert the three `text.index(f"问 / Q: Q{i}")` values are ascending and each of `问 / Q: Q1..Q3` and `答 / A: A1..A3` occurs exactly once via `text.count(...) == 1`.
- [ ] `tests/test_ai_transcript_text.py::test_incomplete_turns_contribute_nothing`: proves behaviour 7 — history `[{"question": "   ", "answer": "A-ignored"}, {"question": "Q-ignored", "answer": ""}, {"answer": "A-ignored-2"}, {"question": "Q-ignored-2"}, {"question": "", "answer": "   "}]`; assert `"问 / Q:" not in text`, `"答 / A:" not in text`, `"A-ignored" not in text`, `"Q-ignored" not in text`.
- [ ] `tests/test_ai_transcript_text.py::test_identical_turn_pairs_collapse_but_same_question_with_new_answer_does_not`: proves behaviour 8 — history `[{"question": "same?", "answer": "yes"}, {"question": "same?", "answer": "yes"}, {"question": "same?", "answer": "no"}]`; assert `text.count("问 / Q: same?") == 2`, `text.count("答 / A: yes") == 1`, `text.count("答 / A: no") == 1`.
- [ ] `tests/test_ai_transcript_text.py::test_bad_history_returns_summary_only`: proves behaviour 9 — loop over `(None, "nope", 42, {"question": "Q", "answer": "A"}, [1, "x", None, object()])` with summary `"SUMMARY_BODY_MARKER"`; assert no exception, `"问 / Q:" not in text`, `m.TRANSCRIPT_SUMMARY_HEADING in text`, `"SUMMARY_BODY_MARKER" in text`.
- [ ] `tests/test_ai_transcript_text.py::test_html_and_fences_are_stripped`: proves behaviour 10 — `m.build_transcript_text("Neo", "<b>bold</b><br/>next line", [{"question": "<i>q</i>", "answer": "```code```"}])`; assert `"<" not in text`, `">" not in text`, `"```" not in text`, `"bold" in text`, `"next line" in text`, `"问 / Q: q" in text`, `"答 / A: code" in text`.
- [ ] `tests/test_ai_transcript_text.py::test_filename_is_stable_and_safe`: proves behaviours 11 and 12 — with `stamp = datetime.datetime(2026, 1, 2, 3, 4, 5)`, assert `m.build_transcript_filename("Neo / 赵鲲", stamp) == "gco_league_ai_summary_Neo_赵鲲_20260102_030405.txt"`, that it `startswith(m.TRANSCRIPT_FILENAME_PREFIX)`, `endswith(m.TRANSCRIPT_FILE_EXTENSION)`, contains `"20260102_030405"`, repeats identically on a second call, and contains none of `/ \ : * ? " < > |`.
- [ ] `tests/test_ai_transcript_text.py::test_filename_always_has_a_stem`: proves behaviour 13 — loop over `("", "   ", "///", "...")`; assert `name.endswith(".txt")`, `name.startswith(m.TRANSCRIPT_FILENAME_PREFIX + "_")`, and the stem (`name[:-4]`.strip("_")) is non-empty.
- [ ] Observable check: the `uv run python -c` assertion in the Verify block exits 0 with no output.

**Verify:**
```bash
uv run pytest tests/test_ai_transcript_text.py tests/test_ai_follow_up_logic.py -v
uv run python -c "import datetime, ai_summary; assert ai_summary.build_transcript_filename('Neo', datetime.datetime(2026, 1, 2, 3, 4, 5)) == 'gco_league_ai_summary_Neo_20260102_030405.txt', 'unexpected filename'"
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Render the download control inside the follow-up fragment
<!-- phase: 2 -->
<!-- targets: ai_summary.py, tests/test_ai_follow_up_download_ui.py -->
<!-- frozen: theme.py, pages/3_🏆_League.py, tests/test_ai_transcript_text.py, tests/test_ai_follow_up_logic.py, tests/test_ai_follow_up_ui.py, tests/test_league_follow_up_wiring.py -->

**Goal:** One render of `render_follow_up_questions` on an existing summary produces exactly one download button, placed after the form and after every rendered Q&A turn, whose `data` equals `build_transcript_text(...)` for the history read at that point — including a question answered in the same run — and produces nothing at all for a blank summary.

**Changes:**
- `ai_summary.py` — replace the body of `render_follow_up_questions` (same decorator, name, parameters, `-> None` return type) with exactly:
  ```python
  @st.fragment
  def render_follow_up_questions(
      player_name: str,
      season_rounds: list[dict],
      summary: str,
  ) -> None:
      """Render the stored Q&A turns, the question form, then a download button for the
      summary plus every answered turn read at that point in the render. Returns None."""
      if not str(summary or "").strip():
          return
      history = get_follow_up_history(summary)
      for turn in history:
          st.markdown(f"**{turn.get('question', '')}**")
          st.markdown(str(turn.get("answer", "")))
      with st.form(FOLLOW_UP_FORM_KEY, clear_on_submit=True):
          question = st.text_input(FOLLOW_UP_INPUT_LABEL, key=FOLLOW_UP_INPUT_KEY)
          submitted = st.form_submit_button(FOLLOW_UP_BUTTON_LABEL)
      if submitted:
          if not question or not str(question).strip():
              st.warning(EMPTY_QUESTION_MESSAGE)
          else:
              language = st.session_state.get(LANGUAGE_SELECTOR_KEY, DEFAULT_LANGUAGE)
              with st.spinner("正在生成回答…"):
                  try:
                      answer = answer_follow_up_question(
                          player_name, season_rounds, summary, history, question, language
                      )
                  except AISummaryError as exc:
                      st.error(str(exc))
                  else:
                      append_follow_up_turn(summary, question, answer)
                      st.markdown(answer)
      history = get_follow_up_history(summary)
      st.download_button(
          label=DOWNLOAD_BUTTON_LABEL,
          data=build_transcript_text(player_name, summary, history),
          file_name=build_transcript_filename(player_name, datetime.now()),
          mime=TRANSCRIPT_MIME_TYPE,
          key=DOWNLOAD_BUTTON_KEY,
      )
  ```
  Key points to preserve: the blank-summary guard runs **before** `get_follow_up_history` (so no session-state write); the blank-question branch warns and falls through instead of returning (so the button still renders); `st.download_button` is called with keyword arguments `label`, `data`, `file_name`, `mime`, `key`; the history is re-read after the submit branch so a just-answered turn is included.
- `tests/test_ai_follow_up_download_ui.py` (new): `import contextlib`, `import pytest`, `import ai_summary`; a `FakeStreamlit` class and a `make_fake_st` fixture, plus module-level helpers `_call(fake, name)` and `_render(player_name, summary)`:
  ```python
  class FakeStreamlit:
      """Minimal stand-in for the streamlit module used by ai_summary's fragment."""

      def __init__(self, *, submit: bool = False, download: bool = False) -> None:
          self.session_state: dict = {}
          self.calls: list[tuple[str, dict]] = []
          self._submit = submit
          self._download = download

      def form(self, *args, **kwargs):
          self.calls.append(("form", {"args": args, "kwargs": kwargs}))
          return contextlib.nullcontext()

      def spinner(self, *args, **kwargs):
          self.calls.append(("spinner", {"args": args, "kwargs": kwargs}))
          return contextlib.nullcontext()

      def columns(self, spec, **kwargs):
          return [contextlib.nullcontext() for _ in spec]

      def fragment(self, func=None, **kwargs):
          return func if func is not None else (lambda inner: inner)

      def text_input(self, label, **kwargs):
          self.calls.append(("text_input", {"label": label, **kwargs}))
          return self.session_state.get(kwargs.get("key"), "")

      def form_submit_button(self, label, **kwargs):
          self.calls.append(("form_submit_button", {"label": label, **kwargs}))
          return self._submit

      def download_button(self, label, data, file_name, mime, key=None, **kwargs):
          self.calls.append(("download_button", {"label": label, "data": data,
                                                 "file_name": file_name, "mime": mime, "key": key}))
          return self._download

      def button(self, label, **kwargs):
          self.calls.append(("button", {"label": label, **kwargs}))
          return False

      def radio(self, label, options, index=0, **kwargs):
          return options[index]

      def markdown(self, body, **kwargs):
          self.calls.append(("markdown", {"body": body}))

      def warning(self, message, **kwargs):
          self.calls.append(("warning", {"message": message}))

      def error(self, message, **kwargs):
          self.calls.append(("error", {"message": message}))
  ```
  ```python
  @pytest.fixture
  def make_fake_st(monkeypatch):
      def _make(*, submit: bool = False, download: bool = False) -> FakeStreamlit:
          fake = FakeStreamlit(submit=submit, download=download)
          monkeypatch.setattr(ai_summary, "st", fake)
          return fake
      return _make


  def _call(fake: FakeStreamlit, name: str) -> dict:
      matches = [payload for called, payload in fake.calls if called == name]
      assert len(matches) == 1, f"expected exactly one {name} call, got {len(matches)}"
      return matches[0]


  def _render(player_name: str, summary: str) -> None:
      func = getattr(
          ai_summary.render_follow_up_questions,
          "__wrapped__",
          ai_summary.render_follow_up_questions,
      )
      func(player_name, [{"round": 1}], summary)
  ```
  `__wrapped__` (set by `functools.wraps` inside `@st.fragment`) calls the undecorated function with no Streamlit script-run context; if it is ever absent, the fallback wrapper calls through to the same function outside a runtime. Teardown is fully handled by `monkeypatch`; the fake holds no threads, files or servers.

**Definition of done:**
- [ ] `tests/test_ai_follow_up_download_ui.py::test_download_button_is_rendered_once_after_the_turns_and_form`: proves behaviours 1, 3, 4, 11 — `fake = make_fake_st()`; seed `fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY] = {"summary": summary, "turns": [{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}]}` with `summary = "AI 总结正文"`; render. `_call(fake, "download_button")` asserts exactly one call; assert `label == ai_summary.DOWNLOAD_BUTTON_LABEL`, `key == ai_summary.DOWNLOAD_BUTTON_KEY`, `mime == ai_summary.TRANSCRIPT_MIME_TYPE`, `file_name.startswith(ai_summary.TRANSCRIPT_FILENAME_PREFIX)`, `file_name.endswith(ai_summary.TRANSCRIPT_FILE_EXTENSION)`, `data == ai_summary.build_transcript_text("Neo", summary, turns)`, and `"问 / Q: Q1" in data`. Ordering: build `names = [name for name, _ in fake.calls]` and assert `names.index("form_submit_button") < names.index("download_button")` and `max(i for i, n in enumerate(names) if n == "markdown") < names.index("download_button")`.
- [ ] `tests/test_ai_follow_up_download_ui.py::test_no_download_control_for_blank_summary_and_no_session_state_write`: proves behaviour 2 — `@pytest.mark.parametrize("summary", ["", "   ", "\n\t "])`; after render assert `fake.calls == []` (no form, no text input, no markdown, no download button) and `fake.session_state == {}`.
- [ ] `tests/test_ai_follow_up_download_ui.py::test_download_control_exists_with_zero_turns_and_contains_the_summary`: proves behaviour 3 — fresh fake, summary `"只有总结 SUMMARY_BODY_MARKER"`, no seeded history; assert one download call, `"SUMMARY_BODY_MARKER" in data`, and `"问 / Q:" not in data`.
- [ ] `tests/test_ai_follow_up_download_ui.py::test_submitted_question_lands_in_the_download_data_in_the_same_render`: proves behaviour 14 — `fake = make_fake_st(submit=True)`, `fake.session_state[ai_summary.FOLLOW_UP_INPUT_KEY] = "新问题?"`, `monkeypatch.setattr(ai_summary, "answer_follow_up_question", lambda *a, **k: "新回答")`; assert `data` contains `"问 / Q: 新问题?"` and `"答 / A: 新回答"` and equals `ai_summary.build_transcript_text("Neo", summary, [{"question": "新问题?", "answer": "新回答"}])`.
- [ ] `tests/test_ai_follow_up_download_ui.py::test_download_activation_issues_no_ai_request_and_keeps_the_transcript`: proves behaviour 15 — record calls from `monkeypatch.setattr(ai_summary, "summarize_season", ...)` and `... "answer_follow_up_question", ...`; render twice, once with `make_fake_st(download=False)` and once with `download=True`, each seeded with `{"question": "Q1", "answer": "A1"}`; assert no AI call happened and that the two `markdown` body lists are equal to `["**Q1**", "A1"]`.
- [ ] `tests/test_ai_follow_up_download_ui.py::test_empty_submission_warns_and_still_offers_the_download`: proves behaviour 1 with a submitted-but-empty question — `make_fake_st(submit=True)`, `fake.session_state[ai_summary.FOLLOW_UP_INPUT_KEY] = "   "`, `answer_follow_up_question` patched to `pytest.fail`; assert the single `warning` call has `message == ai_summary.EMPTY_QUESTION_MESSAGE` and that one download button is still rendered whose `data` has no `"问 / Q:"`.
- [ ] Observable check: the frozen `tests/test_league_follow_up_wiring.py` still passes, proving `pages/3_🏆_League.py` renders this fragment (and therefore the download control) under the League page's Q&A section.

**Verify:**
```bash
uv run pytest tests/test_ai_follow_up_download_ui.py tests/test_ai_follow_up_ui.py tests/test_ai_follow_up_logic.py tests/test_league_follow_up_wiring.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 3: Green styling for submit and download buttons
<!-- phase: 3 -->
<!-- targets: theme.py, tests/test_theme_button_styles.py -->
<!-- frozen: ai_summary.py, pages/3_🏆_League.py, tests/test_ai_transcript_text.py, tests/test_ai_follow_up_download_ui.py, tests/test_ai_follow_up_ui.py, tests/test_ai_follow_up_logic.py, tests/test_league_follow_up_wiring.py -->

**Goal:** `theme.THEME_CSS` applies the existing green button declarations to Streamlit's form-submit and download button elements, with every other rule and both declaration blocks byte-identical to the approved version.

**Changes:**
- `theme.py` — inside `THEME_CSS`, replace **only** these two selector lines (the comment `/* ── Buttons ─────… */` and both declaration blocks stay exactly as they are, byte for byte):
  - `.stButton > button {` becomes
    ```
    .stButton > button,
    [data-testid="stFormSubmitButton"] button,
    [data-testid="stDownloadButton"] button,
    [data-testid="stBaseButton-secondaryFormSubmit"],
    button[kind="formSubmit"],
    button[kind="secondaryFormSubmit"] {
    ```
  - `.stButton > button:hover {` becomes
    ```
    .stButton > button:hover,
    [data-testid="stFormSubmitButton"] button:hover,
    [data-testid="stDownloadButton"] button:hover,
    [data-testid="stBaseButton-secondaryFormSubmit"]:hover,
    button[kind="formSubmit"]:hover,
    button[kind="secondaryFormSubmit"]:hover {
    ```
  The extra selectors are only alternative spellings of the same two Streamlit button elements across versions (`st.form_submit_button` renders a wrapper test id plus a base-button test id/`kind`, and `st.download_button` renders the `stDownloadButton` wrapper); `.stButton > button` stays first in both lists and no other rule, comment, declaration or blank line changes. No new names are added to `theme.py`.
- `tests/test_theme_button_styles.py` (new): `import re`, `import subprocess`, `import pytest`, `import theme`; module constants
  ```python
  APPROVED_TAG = "sdlc/008-league-ai-summary-add-a-download/approved"
  RULE_RE = re.compile(r"(?P<selector>[^{}]+)\{(?P<body>[^{}]*)\}")
  BUTTON_DECLARATIONS = (
      "background: linear-gradient(135deg, var(--green-mid), var(--green-light)) !important;",
      "color: #fff !important;",
      "border: none !important;",
      "border-radius: 8px !important;",
      "font-weight: 600 !important;",
      "transition: transform .15s, box-shadow .15s;",
  )
  HOVER_DECLARATIONS = (
      "transform: translateY(-2px);",
      "box-shadow: 0 6px 20px rgba(82,183,136,.35) !important;",
  )
  ```
  plus helpers:
  ```python
  def _rules(css: str) -> list[tuple[str, str]]:
      return [
          (match.group("selector").strip(), match.group("body").strip())
          for match in RULE_RE.finditer(css)
      ]


  def _rule_for(css: str, selector_fragment: str, *, hover: bool) -> tuple[str, str]:
      found = [
          (selector, body)
          for selector, body in _rules(css)
          if selector_fragment in selector and ("hover" in selector) == hover
      ]
      assert len(found) == 1, f"expected exactly one rule for {selector_fragment}"
      return found[0]


  def _approved_theme_css() -> str | None:
      result = subprocess.run(
          ["git", "show", f"{APPROVED_TAG}:theme.py"],
          capture_output=True, text=True, check=False,
      )
      if result.returncode != 0:
          return None
      match = re.search(r'THEME_CSS = """(.*?)"""', result.stdout, re.DOTALL)
      return match.group(1) if match else None
  ```
  No fixtures, servers or teardown are needed.

**Definition of done:**
- [ ] `tests/test_theme_button_styles.py::test_form_submit_and_download_selectors_share_the_green_button_rule`: proves behaviours 16 and 17 — for each fragment in `('[data-testid="stFormSubmitButton"] button', '[data-testid="stDownloadButton"] button')`, take `_rule_for(theme.THEME_CSS, fragment, hover=False)` and assert `.stButton > button` is in that selector list, that every entry of `BUTTON_DECLARATIONS` is in its body, and do the same for `hover=True` against `HOVER_DECLARATIONS`.
- [ ] `tests/test_theme_button_styles.py::test_button_declarations_are_unchanged`: proves behaviour 18 for the button rules — the non-hover `.stButton > button` rule still contains every `BUTTON_DECLARATIONS` string and the hover rule still contains every `HOVER_DECLARATIONS` string (this assertion always runs, with no git dependency).
- [ ] `tests/test_theme_button_styles.py::test_non_button_rules_are_unchanged`: proves behaviour 18 for everything else — read the approved file with `git show sdlc/008-league-ai-summary-add-a-download/approved:theme.py` via `_approved_theme_css()`; `pytest.skip(f"approved tag {APPROVED_TAG} is not available in this checkout")` if it returns `None`; otherwise assert `len(_rules(theme.THEME_CSS)) == len(_rules(old_css))` and that every old `(selector, body)` pair whose selector does not contain `stButton` is present verbatim in the new rules list.
- [ ] Observable check: `uv run pytest -q` runs the whole existing pytest suite (including root `test_streamlit_app.py`) and exits 0, proving behaviour 19.

**Verify:**
```bash
uv run pytest tests/test_theme_button_styles.py -v
uv run pytest -q
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- The frozen `tests/test_ai_follow_up_ui.py` may assert an exact call sequence for the fragment and break when the download button is added. Caught by the `tests/test_ai_follow_up_ui.py` entry in Phase 2's Verify. If it fails, stop and revise this plan — never edit the frozen test.
- Behaviour 18's strongest check reads the approved tag with `git show`; if the tag is absent from a checkout that test skips. Caught by the skip message; the always-on `test_button_declarations_are_unchanged` still covers the rules this feature touches.
- The CSS selectors can only be proven textually (no browser test), so a selector that does not match the installed Streamlit version would not fail any phase. Mitigated by covering the wrapper test ids, the base-button test id and the `kind` attribute for submit buttons, and the `stDownloadButton` wrapper for downloads; the pinned version is whatever `uv.lock` installs.
- `@st.fragment` wraps the render function at import; the Phase 2 tests take the plain function via `__wrapped__` and fall back to the wrapper (which calls through outside a script run) if that attribute ever disappears. Caught immediately by Phase 2's tests failing to call the fragment.
- Because the download control lives in `pages/3_🏆_League.py`'s fragment, no page change is needed; if a future edit moves the Q&A out of the fragment, `tests/test_league_follow_up_wiring.py` (frozen) stops passing.
- Phase 3's `uv run pytest -q` is a full-suite run, so an unrelated pre-existing failure blocks the phase gate; the pipeline's final verification would fail on it anyway. The `behave` suite is untouched by this feature and is run by the pipeline's final verification.

## Open questions
- **Approved tag availability**: the behaviour-18 comparison test needs `sdlc/008-league-ai-summary-add-a-download/approved`. Assumption: the pipeline creates it before the build and the phase-check checkout can read it; otherwise the test skips and the declarations are still asserted.
- **`player_name` in the transcript text**: the approved interface passes it to `build_transcript_text` but the approved docstring describes only summary + Q&A. Assumption: the transcript body stays summary + Q&A, and the player's identity travels in the file name.
- **Streamlit DOM test ids**: the plan targets `[data-testid="stFormSubmitButton"] button`, `[data-testid="stDownloadButton"] button`, `[data-testid="stBaseButton-secondaryFormSubmit"]` and `button[kind="formSubmit"]`/`button[kind="secondaryFormSubmit"]`. Assumption: at least one selector per button matches the pinned Streamlit version; no exploratory probe of the installed version is performed.

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/008-league-ai-summary-add-a-download/build-log.md` with one section per phase, in order. Head each one `## Phase <n>: <title>`, then list the files changed, the Verify command you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/008-league-ai-summary-add-a-download`.

Commit only this plan's targets and `build-log.md`. Leave every other file alone, including other features' documents under `sdlc/features/`, even for formatting; verification fails on any file outside the targets.
