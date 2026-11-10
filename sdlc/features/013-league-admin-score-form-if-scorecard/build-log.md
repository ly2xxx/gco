# Build log: 013-league-admin-score-form-if-scorecard

## Phase 1: Saved-scorecard lookup and GitHub URL helpers

**Status:** passed (local `sdlc_stage.py verify --phase 1`, exit 0)

**Files changed:**
- `league_scorecard.py`
- `tests/test_league_saved_scorecard.py` (new)

**What was built:** `find_saved_scorecard` lists `scorecard_images/` and returns the newest file named `league_<tournament>_Game_<N>_<player>_<timestamp>.<ext>` for a selection, reading file names only; `game_number_from_label` turns the page's `"Game 5"` into 5. `scorecard_image_url` builds the original's address on `raw.githubusercontent.com` (default branch through `HEAD`), and `scorecard_github_repo` reads `GITHUB_REPO` from the environment or Streamlit secrets.

**Commands and results:**
- `python -m pytest tests/test_league_saved_scorecard.py -q` → 14 passed (also 14 passed on Streamlit 1.55.0, the version the deployed app runs)
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 013-league-admin-score-form-if-scorecard --phase 1` → **Result: PASSED** (scope: 2 files, all inside the targets; frozen: none touched; contract matches the approved tag; whole suite 255 passed)
- Against the repository's real `scorecard_images/`: 李扬 · Game 5 gives `league_2026个人联赛_Game_5_李扬_20261109172833.jpg`; 赵鲲 · Game 1, which has two uploads, gives the newer `…_20260621135412.jpg`; 李扬 · Game 6 gives `None`.

**Deviations from the plan:**
1. **The file name is URL-quoted in `scorecard_image_url`.** The plan says "no URL encoding". The saved names contain Chinese characters, and a name with `#`, `?` or `%` would give a wrong address; `data.github_upload_image` quotes the same name when it uploads. `foo.jpg` is unchanged by quoting, so the plan's test holds, and the quoted address of `league_2026个人联赛_Game_5_李扬_20261109172833.jpg` returns HTTP 200 `image/jpeg`.
2. **Spaces in the tournament and player are matched as `_`.** The League page names uploads with `.replace(" ", "_")`, so a "Li Yang" round is saved as `…_Li_Yang_…`; the plan's prefix, built from the original strings, would never find it. No current name has a space. Matching is otherwise exact and case-sensitive, as planned.
3. **The suffix check ignores case** (`.JPG` counts), since phones save upper-case extensions.
4. **Tests beyond the Definition of done:** the constants, an unlistable folder (`OSError`), other tournaments, players and non-timestamp names, Chinese and spaced names, quoting, file names only (no `open`), and the Streamlit-secrets fallback of `scorecard_github_repo`. The repo test replaces `streamlit.secrets` with `{}` so a developer's own `.streamlit/secrets.toml` can't change its result.

## Phase 2: League page preview and View dialog helpers

**Status:** passed (local `sdlc_stage.py verify --phase 2`, exit 0)

**Files changed:**
- `pages/3_🏆_League.py`
- `tests/test_league_saved_scorecard_preview.py` (new)

**What was built:** `render_league_scorecard_preview` looks up the round's saved scorecard and, when there is one, shows the saved file as it is at 160 pixels wide with `st.image`, a one-line caption and a View button; the button calls `show_saved_scorecard_dialog`, which shows the same path in an `st.dialog`. With `GITHUB_REPO` configured the thumbnail carries the raw GitHub address as its link, so a click opens the original in a new tab. Nothing is rendered when no file matches.

**Commands and results:**
- `python -m pytest tests/test_league_saved_scorecard_preview.py -q` → 9 passed
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 013-league-admin-score-form-if-scorecard --phase 2` → **Result: PASSED** (scope: 2 files, all inside the targets; frozen: none touched; contract matches the approved tag; whole suite 264 passed; Phase 1 and 2 Verify blocks passed)
- Whole suite on Streamlit 1.55.0, the version the deployed app runs → 254 passed, 10 skipped. The 10 are the existing admin-form tests of features 011 and 012, which need `AppTest`'s file-uploader support; they were skipped on 1.55.0 before this feature too.

**Deviations from the plan:**
1. **The linked thumbnail is `st.image(scorecard.path, width=160, link=url)`, not a hand-written `<a><img src="{url}"></a>` in `st.markdown`.** One call covers both cases (`link` is `None` without `GITHUB_REPO`).
   - The plan's HTML loads the thumbnail from GitHub, so it is not the saved file path that spec behaviours 14 and 18 ask for, and the thumbnail itself would break if GitHub were unreachable or the repository private.
   - It also builds HTML from a file name with `unsafe_allow_html=True`.
   - `st.image(link=…)` exists in Streamlit 1.55.0 and 1.67.0; in Chromium it renders `<a href="…" target="_blank" rel="noreferrer">` on both (spec behaviour 21).
   - The plan's test `test_render_preview_links_thumbnail_when_github_repo_set` therefore asserts the image call `("scorecard_images/foo.jpg", 160, <raw URL>)` and no markdown, instead of the anchor text.
2. **A file Streamlit can't display doesn't break the form.** `st.image` raises on an empty or non-image file (`PIL.UnidentifiedImageError`), which stops the page before the score form renders. The thumbnail call is wrapped; on failure the preview shows nothing and logs a `[scorecard]` warning.
3. **Bilingual labels and a caption, like the rest of the form.** The button is `🔍 查看大图 View` and the dialog title `已存计分卡 Saved scorecard` (the plan: `View`, `Saved scorecard`). A caption under the thumbnail reads `已存计分卡 Saved scorecard · <date from the file name>`, plus `点击缩略图打开原图 Click the thumbnail to open the original` when it is linked. Without a caption the thumbnail sits unlabelled next to the scorecard upload box. The tests check that the labels contain `View` and `Saved scorecard`.
4. **The dialog is `width="large"`.** The default small dialog is 500 px wide, too narrow to read a scorecard.
5. **Tests beyond the Definition of done:** an undisplayable file, the page never opening the image itself, and the page's import list.

## Phase 3: Wire preview into the league admin score form

**Status:** passed (local `sdlc_stage.py verify --phase 3`, exit 0)

**Files changed:**
- `pages/3_🏆_League.py`
- `tests/test_league_saved_scorecard_wiring.py` (new)

**What was built:** The admin 录入或修改成绩 block calls `render_league_scorecard_preview(tournament, game_label, player)` once, right after the round's existing-score notice and above the scorecard upload box, with the form's own selections (`t_sel`, `g_sel`, `p_sel`). It runs on every rerun outside `st.form`, so changing the player or game updates or removes the thumbnail, and only admins reach it.

**Commands and results:**
- `python -m pytest tests/test_league_saved_scorecard_wiring.py -q` → 10 passed on Streamlit 1.67.0 and 10 passed on Streamlit 1.55.0
- `python ../.github/actions/sdlc-stage/sdlc_stage.py verify --test-command 'python -m pytest -q && behave --format progress' --feature 013-league-admin-score-form-if-scorecard --phase 3` → **Result: PASSED** (scope: 2 files, all inside the targets; frozen: none touched; contract matches the approved tag; whole suite 274 passed and 17 behave scenarios passed; Phase 1-3 Verify blocks passed)
- Whole suite on Streamlit 1.55.0 → 264 passed, 10 skipped (the same existing file-upload tests as in Phase 2).
- Mutation check: with the guard around the thumbnail removed, `test_saved_file_that_cannot_be_displayed_does_not_break_the_form` and `test_file_streamlit_cannot_display_shows_nothing_and_does_not_raise` fail; both pass with the code as committed.
- Browser check on Streamlit 1.55.0 (the version the deployed app runs): `streamlit run streamlit_app.py` with admin secrets and `GITHUB_REPO = "ly2xxx/gco"` kept outside the repository, the repository's real `scorecard_images/`, driven by Playwright in Chromium.
  - 李扬 · Game 6, which has no saved card, shows no thumbnail, caption or button.
  - 李扬 · Game 5 shows the thumbnail 160 px wide, the caption `已存计分卡 Saved scorecard · 2026-11-09 — 点击缩略图打开原图 Click the thumbnail to open the original`, and the `🔍 查看大图 View` button.
  - Clicking the thumbnail opens a new tab at `https://raw.githubusercontent.com/ly2xxx/gco/HEAD/scorecard_images/league_2026个人联赛_Game_5_李扬_20261109172833.jpg` (that address returns HTTP 200 `image/jpeg`).
  - View opens the `已存计分卡 Saved scorecard` dialog with the card at 960×1280.
  - 杨明 · Game 6, a photo saved with EXIF orientation 6, shows as stored (a 160×120 landscape thumbnail), which is the accepted "as it is" behaviour.
  - No exception on the page.

**Deviations from the plan:**
1. **Tests beyond the Definition of done.** Besides the plan's two source tests, `tests/test_league_saved_scorecard_wiring.py` has a third source test (the call is in the admin block and above `st.form`) and seven runs of the real page with `AppTest` against a temporary scorecard folder:
   - the newest card shown as one thumbnail;
   - the GitHub link when the repository is configured;
   - View opening the dialog;
   - changing the selection;
   - a round with no card;
   - a visitor who is not an admin;
   - a file that can't be displayed.

   They use no file upload, so unlike the admin-form tests of features 011 and 012 they also run on Streamlit 1.55.0.
