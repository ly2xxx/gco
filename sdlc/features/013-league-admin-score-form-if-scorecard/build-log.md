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
