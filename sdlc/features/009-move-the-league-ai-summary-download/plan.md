<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@e695b84 -->
## Approach

Reserve the download button's visible position inside `ai_summary.render_follow_up_questions` with an `st.empty()` placeholder created immediately after the existing empty-summary early return, leave the stored Q&A turns and the follow-up form where they are, re-read `get_follow_up_history(summary)` after any submitted question has been answered and appended, and fill the reserved placeholder **last** with the unchanged `st.download_button(...)` call (label, key, mime, filename, and `build_transcript_text(player_name, summary, history)` data all unchanged). No page file and no other function changes, so the button renders between the summary content (rendered by `render_season_summary` before the fragment call) and the Q&A area while the fresh, just-answered turn is still in the payload.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| On the League page, the League AI summary's 下载/Download button renders between the summary content and the follow-up Q&A section. | 1, 2, 3 | Phase 1 |
| Downloading immediately after submitting a new follow-up question yields a `.txt` that contains that just-answered question and its answer, alongside the summary and all previously answered follow-ups. | 6 | Phase 2 |
| The downloaded `.txt` still contains the summary and every previously answered follow-up — nothing present before the move is missing after it. | 4, 5, 10 | Phase 1 |
| The button remains visible and correctly labelled (bilingual 下载/Download) whether or not any follow-up has been answered yet. | 3, 7, 8, 9 | Phase 1 (zero-turn render, empty summary) and Phase 2 (blank-question / AI-error submissions) |
| No other page or section's layout or download behaviour changes. | 12 | Phase 2 |
| The existing tests still pass. | 11 | Phase 1 and Phase 2 |

## Phase 1: Reserve the download slot above the Q&A

<!-- phase: 1 -->
<!-- targets: ai_summary.py, tests/test_ai_follow_up_download_position.py -->
<!-- frozen: tests/test_ai_follow_up_download_ui.py, tests/test_ai_follow_up_ui.py, tests/test_ai_follow_up_logic.py, tests/test_ai_transcript_text.py, tests/test_league_follow_up_wiring.py, tests/test_league_deep_dive_wiring.py, tests/test_theme_button_styles.py, pages/3_🏆_League.py, pages/4_🥊_Cup.py, pages/5_⛳_Outing.py, pages/6_💾_API_Data.py -->

**Goal:** In `ai_summary.render_follow_up_questions`, the download button's reserved slot is created before the stored turns and the form, and is filled last with the transcript built from the post-submission history, while the label, key, mime, filename prefix and data builder stay exactly as they are.

**Changes:**

- `ai_summary.py`: no import changes (`datetime`, `st` are already imported); no constant, helper or signature changes. Replace the body of `render_follow_up_questions` (keeping the `@st.fragment` decorator and the signature `def render_follow_up_questions(player_name: str, season_rounds: list[dict], summary: str) -> None:`) so that everything after the existing early return reads exactly:

```python
    download_slot = st.empty()
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
    with download_slot:
        st.download_button(
            label=DOWNLOAD_BUTTON_LABEL,
            data=build_transcript_text(player_name, summary, history),
            file_name=build_transcript_filename(player_name, datetime.now()),
            mime=TRANSCRIPT_MIME_TYPE,
            key=DOWNLOAD_BUTTON_KEY,
        )
```

  Docstring of the function becomes: `"""Render the download button, the stored Q&A turns and the question form, in that order, for the given summary. Returns None."""`. The early return (`if not str(summary or "").strip(): return`) is unchanged and stays first. `with download_slot:` is Streamlit's documented way to fill an `st.empty()` placeholder, so the button lands at the placeholder's reserved position while the `st.download_button` call itself stays the final write of the run.

- `pages/3_🏆_League.py`: no change (the existing `render_follow_up_questions(player_name, season_rounds, summary)` call already sits after the `render_season_summary(...)` content).

- `tests/test_ai_follow_up_download_position.py` (new): module-level fake of `st` plus render-order tests. Exact content:

```python
"""Render-order tests for the League AI summary download button (feature 009)."""
from __future__ import annotations

import contextlib

import pytest

import ai_summary

SUMMARY = "本赛季表现稳定，共 6 轮，平均 88 杆。"


class FakeSlot:
    """Stand-in for the DeltaGenerator returned by st.empty()."""

    def __init__(self, fake: "FakeStreamlit", index: int) -> None:
        self._fake = fake
        self.index = index

    def __enter__(self) -> "FakeSlot":
        self._fake.active_slot = self.index
        self._fake.events.append(("enter_slot", self.index))
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._fake.active_slot = None
        self._fake.events.append(("exit_slot", self.index))
        return False


class FakeStreamlit:
    """Records the render calls ai_summary.render_follow_up_questions makes, in order."""

    def __init__(self, *, question: str = "", submitted: bool = False, session_state: dict | None = None) -> None:
        self.events: list[tuple] = []
        self.session_state: dict = {} if session_state is None else session_state
        self.question = question
        self.submitted = submitted
        self.active_slot: int | None = None
        self._slot_count = 0

    def empty(self) -> FakeSlot:
        index = self._slot_count
        self._slot_count += 1
        self.events.append(("empty", index))
        return FakeSlot(self, index)

    def markdown(self, body, **kwargs) -> None:
        self.events.append(("markdown", str(body)))

    def form(self, key, **kwargs):
        self.events.append(("form", key))
        return contextlib.nullcontext()

    def text_input(self, label, **kwargs) -> str:
        self.events.append(("text_input", label))
        return self.question

    def form_submit_button(self, label, **kwargs) -> bool:
        self.events.append(("form_submit_button", label))
        return self.submitted

    def warning(self, body) -> None:
        self.events.append(("warning", str(body)))

    def error(self, body) -> None:
        self.events.append(("error", str(body)))

    def spinner(self, text, **kwargs):
        self.events.append(("spinner", str(text)))
        return contextlib.nullcontext()

    def download_button(self, **kwargs) -> None:
        self.events.append(("download_button", kwargs, self.active_slot))

    def kind(self, name: str) -> int:
        return [event[0] for event in self.events].index(name)

    def download_calls(self) -> list[tuple]:
        return [event for event in self.events if event[0] == "download_button"]


def _render(monkeypatch, fake, summary=SUMMARY, player="张三", rounds=None) -> None:
    monkeypatch.setattr(ai_summary, "st", fake)
    ai_summary.render_follow_up_questions(player, [] if rounds is None else rounds, summary)
```

  followed by the four tests listed under Definition of done. No threads, servers or temporary files are started, so `monkeypatch` (auto-undone) is the only teardown needed.

- No dependency changes: `pyproject.toml` / `requirements.txt` stay untouched (pytest is already used).

**Definition of done:**

- [ ] `tests/test_ai_follow_up_download_position.py::test_button_slot_reserved_above_turns_and_form` — proves spec behaviours 1, 3, 5, 10 for the zero-turn case. Sets up `fake = FakeStreamlit()`, calls `_render(monkeypatch, fake)`, then asserts `fake.events[0] == ("empty", 0)`; exactly one download event (`len(fake.download_calls()) == 1`) whose slot index is `0` (`_, kwargs, slot_index = fake.download_calls()[0]; assert slot_index == 0`); `fake.kind("form") > 0` (the form was rendered after the reserved slot); `fake.events[-1][0] == "download_button"` (the slot was filled last); `kwargs["label"] == ai_summary.DOWNLOAD_BUTTON_LABEL == "⬇️ 下载 / Download"`; `kwargs["key"] == ai_summary.DOWNLOAD_BUTTON_KEY`; `kwargs["mime"] == ai_summary.TRANSCRIPT_MIME_TYPE == "text/plain"`; `kwargs["file_name"].startswith(ai_summary.TRANSCRIPT_FILENAME_PREFIX + "_")` and `.endswith(ai_summary.TRANSCRIPT_FILE_EXTENSION)`; `kwargs["data"] == ai_summary.build_transcript_text("张三", SUMMARY, [])` and that data contains `ai_summary.TRANSCRIPT_SUMMARY_HEADING`, `SUMMARY` and `ai_summary.TRANSCRIPT_QA_HEADING`.
- [ ] `tests/test_ai_follow_up_download_position.py::test_button_slot_above_stored_turns` — proves spec behaviours 2 and 4. Seeds `state = {ai_summary.FOLLOW_UP_HISTORY_KEY: {"summary": SUMMARY, "turns": [{"question": "第一问", "answer": "第一答"}]}}`, builds `FakeStreamlit(session_state=state)`, calls `_render(monkeypatch, fake)`, then asserts `fake.events[0] == ("empty", 0)`, the download event's slot index is `0`, the first `markdown` event equals `("markdown", "**第一问**")` and occurs before `fake.kind("form")`, the download event is last, and `kwargs["data"] == ai_summary.build_transcript_text("张三", SUMMARY, [{"question": "第一问", "answer": "第一答"}])` with `"问 / Q: 第一问"` and `"答 / A: 第一答"` both present.
- [ ] `tests/test_ai_follow_up_download_position.py::test_label_and_key_identical_with_and_without_turns` — proves spec behaviour 3 across both states. Renders twice into two fakes (one with empty session state, one seeded with one turn as above) and asserts both download events carry `label == ai_summary.DOWNLOAD_BUTTON_LABEL` and `key == ai_summary.DOWNLOAD_BUTTON_KEY`, and that both slot indices are `0`.
- [ ] `tests/test_ai_follow_up_download_position.py::test_empty_summary_renders_nothing` — proves spec behaviour 9. `@pytest.mark.parametrize("summary", ["", "   ", None])`; for each value renders into a fresh `FakeStreamlit()` and asserts `fake.events == []` (no placeholder, no markdown, no form, no download button).
- [ ] Frozen pre-existing tests are re-run unchanged (behaviour 11) and the League/Cup/Outing/API Data page files are byte-identical to the approved tag (behaviour 12).

**Verify:**
```bash
uv run pytest tests/test_ai_follow_up_download_position.py -v
uv run pytest tests/test_ai_follow_up_download_ui.py tests/test_ai_follow_up_ui.py tests/test_ai_follow_up_logic.py tests/test_ai_transcript_text.py tests/test_league_follow_up_wiring.py tests/test_league_deep_dive_wiring.py tests/test_theme_button_styles.py -v
git diff --exit-code "sdlc/009-move-the-league-ai-summary-download/approved" -- "pages/3_🏆_League.py" "pages/4_🥊_Cup.py" "pages/5_⛳_Outing.py" "pages/6_💾_API_Data.py" "pages/1_📢_Announcements.py" "pages/2_📅_Events.py"
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Prove same-run freshness and cross-page regression

<!-- phase: 2 -->
<!-- targets: tests/test_ai_follow_up_download_freshness.py, ai_summary.py -->
<!-- frozen: tests/test_ai_follow_up_download_position.py, tests/test_ai_follow_up_download_ui.py, tests/test_ai_follow_up_ui.py, tests/test_ai_follow_up_logic.py, tests/test_ai_transcript_text.py, tests/test_league_follow_up_wiring.py, tests/test_league_deep_dive_wiring.py, tests/test_theme_button_styles.py, pages/3_🏆_League.py, pages/4_🥊_Cup.py, pages/5_⛳_Outing.py, pages/6_💾_API_Data.py -->

**Goal:** A follow-up answered during the current render run appears in that same run's download payload exactly once, blank-question and `AISummaryError` submissions leave the payload and stored history unchanged, and no page other than the League page renders the follow-up fragment.

**Changes:**

- `tests/test_ai_follow_up_download_freshness.py` (new): copy the `FakeSlot`, `FakeStreamlit` and `_render` definitions verbatim from `tests/test_ai_follow_up_download_position.py` (same module-level `SUMMARY = "本赛季表现稳定，共 6 轮，平均 88 杆。"`), then add the four tests below. `monkeypatch` is the only fixture/teardown; no processes, threads or files.

  1. `test_new_answer_lands_in_same_run_transcript` — seeds one stored turn `{"question": "第一问", "answer": "第一答"}`, creates `FakeStreamlit(question="第二问", submitted=True)`, monkeypatches `ai_summary.answer_follow_up_question` with `lambda *args, **kwargs: "第二答"`, calls `_render(monkeypatch, fake)`. Asserts `fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY]["turns"] == [{"question": "第一问", "answer": "第一答"}, {"question": "第二问", "answer": "第二答"}]` (stored exactly once); the single download event's `data` contains `"问 / Q: 第二问"`, `"答 / A: 第二答"`, `"问 / Q: 第一问"`, `"答 / A: 第一答"`, `ai_summary.TRANSCRIPT_SUMMARY_HEADING` and `SUMMARY`; `data.count("问 / Q: 第二问") == 1`; `data == ai_summary.build_transcript_text("张三", SUMMARY, fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY]["turns"])`; the download event is `fake.events[-1]` and its slot index is `0`.
  2. `test_blank_question_keeps_transcript_and_stores_nothing` — `FakeStreamlit(question="   ", submitted=True)`, `monkeypatch.setattr(ai_summary, "answer_follow_up_question", _fail)` where `def _fail(*args, **kwargs): raise AssertionError("must not be called")`. After `_render`, asserts `("warning", ai_summary.EMPTY_QUESTION_MESSAGE) in fake.events`, `fake.session_state[ai_summary.FOLLOW_UP_HISTORY_KEY]["turns"] == []`, the download event's `data == ai_summary.build_transcript_text("张三", SUMMARY, [])`, and the download event is last.
  3. `test_ai_error_keeps_transcript_and_stores_nothing` — `def _boom(*args, **kwargs): raise ai_summary.AISummaryError("生成失败")` patched onto `ai_summary.answer_follow_up_question`; `FakeStreamlit(question="第二问", submitted=True)`. Asserts `("error", "生成失败") in fake.events`, stored turns `== []`, download `data == ai_summary.build_transcript_text("张三", SUMMARY, [])`, download event last.
  4. `test_other_pages_do_not_use_the_follow_up_fragment` — reads each of `pages/4_🥊_Cup.py`, `pages/5_⛳_Outing.py`, `pages/6_💾_API_Data.py`, `pages/1_📢_Announcements.py`, `pages/2_📅_Events.py` with `pathlib.Path(...).read_text(encoding="utf-8")` and asserts `"render_follow_up_questions("` is absent from each; and reads `pages/3_🏆_League.py` asserting `source.index("render_season_summary(") < source.index("render_follow_up_questions(")` (the fragment call still follows the summary render).

- `ai_summary.py`: listed as a target only so a defect found by the freshness test can be fixed inside `render_follow_up_questions`; no change is expected. If the fresh-data assertion fails, fix only the ordering inside `render_follow_up_questions` (slot created first, filled last, history re-read after the append) — never change `build_transcript_text`, `build_transcript_filename`, `get_follow_up_history`, `append_follow_up_turn` or any constant.

- `tests/test_ai_follow_up_download_position.py`: unchanged, and re-run as a frozen regression.

- No dependency changes (`pyproject.toml` / `requirements.txt` untouched).

**Definition of done:**

- [ ] `tests/test_ai_follow_up_download_freshness.py::test_new_answer_lands_in_same_run_transcript` — proves spec behaviour 6 (the just-answered question and answer are in the payload of the same render run, stored exactly once, together with the summary and every earlier turn).
- [ ] `tests/test_ai_follow_up_download_freshness.py::test_blank_question_keeps_transcript_and_stores_nothing` — proves spec behaviour 7 (warning shown, nothing stored, no answer call, download data identical to before the submission).
- [ ] `tests/test_ai_follow_up_download_freshness.py::test_ai_error_keeps_transcript_and_stores_nothing` — proves spec behaviour 8 (error text shown, nothing stored, download button still rendered with unchanged data).
- [ ] `tests/test_ai_follow_up_download_freshness.py::test_other_pages_do_not_use_the_follow_up_fragment` — proves spec behaviour 12 at source level, and that the League page still renders the summary before the follow-up fragment.
- [ ] All earlier phase tests and the frozen page files still hold: Phase 1 tests re-run green and the six page files still match the approved tag.

**Verify:**
```bash
uv run pytest tests/test_ai_follow_up_download_freshness.py -v
uv run pytest tests/test_ai_follow_up_download_position.py tests/test_ai_follow_up_download_ui.py tests/test_ai_follow_up_ui.py tests/test_ai_follow_up_logic.py tests/test_ai_transcript_text.py tests/test_league_follow_up_wiring.py tests/test_announcement_page_wiring.py tests/test_pinned_announcements.py tests/test_pinned_winners_announcement.py tests/test_upcoming_section_visibility.py -v
git diff --exit-code "sdlc/009-move-the-league-ai-summary-download/approved" -- "pages/3_🏆_League.py" "pages/4_🥊_Cup.py" "pages/5_⛳_Outing.py" "pages/6_💾_API_Data.py" "pages/1_📢_Announcements.py" "pages/2_📅_Events.py"
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks

- **A frozen pre-existing test double cannot enter an `st.empty()` placeholder.** The button write moved inside `with download_slot: st.download_button(...)`, so a double that stubs only `download_button`/`markdown`/`form`/… and not `empty()` would raise `AttributeError`. The Phase 1 Verify re-runs `tests/test_ai_follow_up_download_ui.py` and friends, so this surfaces at the Phase 1 gate; the fix is to revise this plan (e.g. give the phase a container-capable double), never to edit frozen tests.
- **Ordering could silently regress** if a later change moves the `st.download_button` call or the placeholder creation. Phase 1's `test_button_slot_reserved_above_turns_and_form` / `test_button_slot_above_stored_turns` assert the placeholder event is the fragment's first render event and the download write is its last, so any reordering fails immediately.
- **Stale transcript** if the history read happens before the append. Phase 2's `test_new_answer_lands_in_same_run_transcript` compares the payload against the post-append stored turns and checks `data.count("问 / Q: 第二问") == 1`.
- **Leakage into other pages** (moving or duplicating a download control). The `git diff --exit-code` checks on all six page files and `test_other_pages_do_not_use_the_follow_up_fragment` catch it.
- **Placeholder rendering differs in a future Streamlit version** (e.g. placeholder content rendered inline rather than at the reserved position). The fake-based ordering tests assert the reserved slot, but only a manual Streamlit run shows the pixels; behaviour 1–3 are otherwise proven by the slot assertions.

## Open questions

- Assumption: the pre-existing tests for the download button locate it through a double (or a real-but-bare Streamlit) that tolerates `st.empty()` plus a `with` block, which is why behaviour 11 can hold unchanged. If a frozen test fails on the placeholder itself, the plan must be revised rather than the frozen test edited — flagged in Risks.
- Assumption: `pages/3_🏆_League.py` calls `render_season_summary(...)` textually before `render_follow_up_questions(...)`; Phase 2's wiring test asserts exactly that order and the page stays frozen, so a mismatch means this plan needs revising, not the page.
- Assumption: no new dependency is needed; both phases rely only on `pytest` and Streamlit, which the project already installs.

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/009-move-the-league-ai-summary-download/build-log.md` with one section per phase, in order. Head each
   one `## Phase <n>: <title>`, then list the files changed, the Verify command
   you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/009-move-the-league-ai-summary-download`.

Commit only this plan's targets and `build-log.md`. Leave every other file alone,
including other features' documents under `sdlc/features/`, even for formatting;
verification fails on any file outside the targets.

The pipeline waits for this file. Once it has a section for every phase, it
verifies the whole branch and opens the pull request.

