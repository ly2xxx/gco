# Build log: 011-league-admin-score-form-a-scorecard

## Phase 1: Field filtering and normalisation module

**Status:** passed (local `sdlc_stage.py verify --phase 1`, exit 0)

**Files changed:**
- `league_scorecard.py` (new)
- `tests/test_league_scorecard_fields.py` (new)

**What was built:** `league_scorecard.py` holds the field contract (`LEAGUE_SCORECARD_FIELD_KEYS`, `ScorecardReadResult`) and `scorecard_field_updates`, which maps English/Chinese aliases to the ten target fields and keeps only found, parseable values: ISO dates, ints within range, and the closest known venue. Missing, empty, unparseable, out-of-range and `found: false` values are dropped, so the page only ever writes fields the read really found.

**Commands and results:**
- `python -m pytest tests/test_league_scorecard_fields.py -v` → 15 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 011-league-admin-score-form-a-scorecard --phase 1` → **Result: PASSED** (scope: 2 files, all inside the targets; frozen: none touched; contract matches the approved tag; whole suite and the Phase 1 Verify block passed)

**Deviations from the plan:** none.

## Phase 2: One Ollama Cloud scorecard read with a 120 s cap

**Status:** passed (local `sdlc_stage.py verify --phase 2`, exit 0)

**Files changed:**
- `league_scorecard.py`
- `tests/test_league_scorecard_read.py` (new)

**What was built:** `read_league_scorecard` makes at most one `POST https://ollama.com/api/generate` with the base64 image, `stream: false`, `format: json`, `Authorization: Bearer <OLLAMA_API_KEY>` and a 120 s timeout (the call proven in ly2xxx/ideas-playground#16), with model `OLLAMA_SCORECARD_MODEL`, else `OLLAMA_MODEL`, else `glm-5.3-flash:cloud`. Empty or non-image input never reaches the network, and every HTTP error, timeout, network error, unparseable body or field-less answer comes back as an `unavailable_reason` instead of an exception.

**Commands and results:**
- `python -m pytest tests/test_league_scorecard_read.py -v` → 11 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 011-league-admin-score-form-a-scorecard --phase 2` → **Result: PASSED** (scope: all inside the targets; frozen: none touched; contract matches the approved tag; whole suite and the Phase 1 and 2 Verify blocks passed)
- Transport check outside the suite: the real `_post_ollama_generate` against a local stand-in server on `127.0.0.1` sent `POST /api/generate` with `Authorization: Bearer <key>`, `stream: false` and the default model, and parsed the answer; a 401 gave `http 401`, a 3 s reply with a 1 s cap gave `timeout`, and a refused connection gave `network error`, none raising. Ollama Cloud itself isn't reachable from the build machine, so no call to `ollama.com` was made.

**Deviations from the plan:**
1. **No `num_predict` in the payload's `options`; it is `{"temperature": 0}`.** The plan capped output at 512 tokens. Ollama counts a thinking model's reasoning towards `num_predict`, so the cap can end a vision read before it writes the JSON, turning every read into `unparseable response`; the call proven in ideas-playground#16 sets no cap. No Definition of done test checks `options`.
2. **Tests isolate model and key resolution.** `tests/test_league_scorecard_read.py` has an autouse fixture that clears `OLLAMA_SCORECARD_MODEL`, `OLLAMA_MODEL`, `OLLAMA_API_KEY` and `OLLAMA_KEY` and replaces `streamlit.secrets` with `{}`, so `test_request_payload_and_timeout` checks the default model even on a machine whose `.streamlit/secrets.toml` sets `OLLAMA_MODEL`. The plan's tests are otherwise as written.

## Phase 3: Session-state application and upload fingerprint

**Status:** passed (local `sdlc_stage.py verify --phase 3`, exit 0)

**Files changed:**
- `league_scorecard.py`
- `tests/test_league_scorecard_state.py` (new)

**What was built:** `apply_scorecard_updates` writes each found field into its widget's session-state key, in `LEAGUE_SCORECARD_FIELD_KEYS` order, and ignores unknown fields and fields without a widget key, so fields the read didn't find keep their value. `scorecard_upload_fingerprint` gives one selected file a stable SHA-256 id, which the page uses to read each upload only once.

**Commands and results:**
- `python -m pytest tests/test_league_scorecard_state.py -v` → 6 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 011-league-admin-score-form-a-scorecard --phase 3` → **Result: PASSED** (scope: all inside the targets; frozen: none touched; contract matches the approved tag; whole suite and the Phase 1-3 Verify blocks passed)

**Deviations from the plan:**
1. **One extra test, `test_fingerprint_accepts_empty_payload`,** covers the `bytes(payload or b"")` guard the plan specifies for an empty or `None` payload. The plan's four tests are as written.

## Phase 4: Wire the picker, prefill and notice into the League page

**Status:** passed (local `sdlc_stage.py verify --phase 4`, exit 0)

**Files changed:**
- `pages/3_🏆_League.py`
- `tests/test_league_scorecard_wiring.py` (new)

**What was built:** The admin 录入或修改成绩 form now has one scorecard picker above its fields. A newly selected image is read once (fingerprint-guarded), and the found fields are written into the inputs' `st.session_state` keys before the form renders, so fields the card didn't show keep today's values (the existing score when editing, else 72/36/0). No upload or a failed read shows the plan's `st.info` notice and leaves the form as it was. Switching player or game, or saving, resets the inputs to that round's values, and Save still uploads the selected image once through the unchanged `github_upload_image` call.

**Commands and results:**
- `python -m pytest tests/test_league_scorecard_wiring.py -v` → 14 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 011-league-admin-score-form-a-scorecard --phase 4` → **Result: PASSED** (scope: all inside the targets; frozen: none touched; contract matches the approved tag; whole suite and the Phase 1-4 Verify blocks passed)
- Mutation checks on the new AppTest tests: without `step=1` (deviation 3) `test_upload_prefills_found_fields_only_and_save_stores_edited_values` fails on `净杆`; without the snapshot reset `test_switching_round_shows_that_rounds_values_not_the_prefill` fails (`109 == 94`). Both pass with the code as committed.
- Browser check (the plan's manual check): `streamlit run streamlit_app.py` with admin secrets outside the repository and `OLLAMA_GENERATE_URL` pointed at a local stand-in, driven by Playwright in Chromium. On 刘北南 · Game 1 (existing score Net 12, Gross 109, Stableford 0, Par 1, Bogey 7) the picker sits above the form, the unavailable notice shows before an upload, and a PNG upload sent one `POST /api/generate` (Bearer key, `glm-5.3-flash:cloud`, one image). The read filled date, venue, net, gross, pars and bogeys, showed them as whole numbers, kept Stableford at 0 (the card's `null`), showed the success line and hid the notice. Save wasn't pressed against real data; the AppTest above covers Save.

**Deviations from the plan:**
1. **One picker instead of two.** The form's old `可选：上传计分卡` uploader (two lines below the ten widgets) is gone, and `scorecard_pic` is now the picker's file when it is a JPG/JPEG/PNG, the types the old uploader accepted. Spec behaviour 9 says the *selected* scorecard image is uploaded on Save; with two uploaders the image picked for auto-fill was never saved unless the admin picked it a second time. The Save button, the round mutation code and the `github_upload_image(...)` call are unchanged, so the plan's manual diff check also shows those two removed lines and the `scorecard_pic` assignment above the form.
2. **The picker renders before the hoisted `_base_*` defaults** (plan steps 1 and 2 swapped). The plan's own `test_picker_is_rendered_with_its_own_key` requires `st.file_uploader(` to come before `_base_net`, and step 1 needs the `_base_*` values. Nothing changes in behaviour: the snapshot reset only touches the ten field widgets, never the picker.
3. **`_scorecard_widget_default` adds `step=1` for whole-number fields.** Once a key is in session state the plan passes only `key=`, and Streamlit 1.67 then makes a `st.number_input` without `value`/`min_value` a float input (`0.00`, step `0.01`), so Net, Gross and Stableford would show `12.00` and Save would store floats. `step=1` keeps them integer inputs and doesn't change their identity (keyed widgets are identified by key alone).
4. **Known venues skip rows with no venue.** `_scorecard_known_venues()` passes `df[df["Venue"].notna()]`: 61 stored rows have a NaN venue, which `venue_names_from_records` would otherwise turn into a known venue named `nan`.
5. **Clearing the picker forgets the last read.** Selecting the same card again after removing it is a new, manual read, so an admin can retry after a timeout. There is still no automatic retry, cache or queue (spec behaviour 18).
6. **A spinner during the read and a success line after it.** A read can take up to 120 s, and the success line (`已根据记分卡自动填写 N 项… / Auto-filled from the scorecard: …`) tells the admin which fields to check before saving. The unavailable notice is the plan's text and stays `st.info`.
7. **Four AppTest tests beyond the Definition of done** run the page as an admin with the read, `save_scores` and `github_upload_image` replaced by recorders: no-upload defaults and notice, prefill of found fields only and Save storing the edited values plus one image upload, a failed read leaving the form unchanged, and a round switch replacing the prefill. They skip if the installed Streamlit's AppTest can't drive `st.file_uploader`. The plan's ten source tests are as written.
