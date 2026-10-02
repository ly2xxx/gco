<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@ed3ef1e -->
## Approach
Add a single static `docs/index.html` that introduces the GCO club with only repository-backed facts, link it from the `## 🎯 Live Dashboard` section of `README.md`, and publish `docs/` through a new `.github/workflows/pages.yml`. Each change is proved by offline pytest tests using stdlib HTML parsing and git comparison against the approved tag, with no new dependencies.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| Visiting https://ly2xxx.github.io/gco/ in a browser returns a rendered page (not a 404) without any login. | 1, 2, 15 | Phase 1, Phase 3 |
| The page contains a short introduction to the Chinese golf community, readable in a couple of minutes, with no dead links or missing images. | 2, 3, 4, 5, 6, 7, 12, 13 | Phase 1 |
| The page renders usably on both a desktop and a phone-width viewport. | 8, 9 | Phase 1 |
| README.md contains a visible link to https://ly2xxx.github.io/gco/. | 10, 11 | Phase 2 |
| The page content is consistent with the club facts already stated in the repository (charter, tournaments, players) and does not contradict them. | 12, 13 | Phase 1 |
| The existing tests still pass. | 14 | All phases (suite re-run in final verification) |

## Phase 1: Static landing page at `docs/index.html`

<!-- phase: 1 -->
<!-- targets: docs/index.html, tests/test_pages_site.py -->
<!-- frozen: README.md, .github/workflows/ci.yml, .github/workflows/sdlc-phase.yml, .github/workflows/sdlc.yml, features/**, test_streamlit_app.py, tests/test_ai_*.py, tests/test_announcement_page_wiring.py, tests/test_league_*.py, tests/test_pinned_*.py, tests/test_theme_button_styles.py, tests/test_upcoming_section_visibility.py, docs/GCO 2026章程.md, docs/GCO 2026章程.docx, docs/gco-2026.pdf, docs/images/** -->

**Goal:** A browser can open `docs/index.html` and see a short, self-contained, offline-safe GCO introduction with valid relative assets.

**Changes:**
- `docs/index.html`: create exactly this static page. It uses only inline CSS, one local image, one relative PDF link, one relative percent-encoded charter link, and exactly one absolute URL (`https://github.com/ly2xxx/gco`).

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GCO Golf Club — Chinese Golf Community</title>
<style>
  :root { color-scheme: light dark; }
  body { margin: 0 auto; padding: 1.25rem; max-width: 46rem; font-family: system-ui, sans-serif; line-height: 1.55; }
  header { padding: 1rem 0; }
  section { margin: 1.5rem 0; }
  h1, h2 { line-height: 1.2; }
  img { max-width: 100%; height: auto; border-radius: 0.5rem; }
  a { color: #0b5d1e; }
</style>
</head>
<body>
<header>
  <h1>GCO Golf Club</h1>
  <p>A friendly Chinese golf community playing competitive and social rounds in 2026.</p>
</header>
<main>
  <section id="who-we-are">
    <h2>Who We Are</h2>
    <p>GCO Golf Club is a Chinese golf community built around friendship, friendly competition, and a shared love of the game. We bring together players who enjoy regular rounds, league play, and the chance to improve together. The club is open to members and guests who want a welcoming place to play, whether they are new to golf or have years of experience.</p>
    <p>Our community is international in spirit while keeping its Chinese roots at the centre. Names, traditions, and the joy of playing together matter to us as much as the scores.</p>
  </section>
  <section id="what-we-play">
    <h2>What We Play</h2>
    <p>In 2026 the club season includes 3 main tournaments: the 提提卡卡杯 (Titicaca Cup), the 暖男杯 (Warm Man Cup), and the 凯尔特人杯 (Celtic Cup). Each tournament has its own period and leaderboard, and players compete across the season for pride and the club title.</p>
    <p>Our 12 players are 刘北南, Jacky, 赵鲲, 杨子初, Neo, 徐峥, 杨明, 曹振波, 李扬, 王文龙, 曾诚, and Justin. We track net scores, birdies, pars, bogeys, and double bogeys so every round adds to the story of the season.</p>
    <img src="images/gco-2026.pdf-0-49.png" alt="GCO 2026 season scorecard and results">
  </section>
  <section id="how-the-season-works">
    <h2>How the Season Works</h2>
    <p>The season runs through 2026 with league rounds and cup matches. Players earn points and compare net scores across games. The league table and tournament standings update as results come in, so members can follow the race all year.</p>
    <p>Every round is recorded and shared through the club's dashboard and data. The goal is simple: play often, enjoy the company, and see who rises to the top by the end of the season.</p>
  </section>
  <section id="learn-more">
    <h2>Learn More</h2>
    <p>Read the club charter and season rules in the <a href="GCO%202026%E7%AB%A0%E7%A8%8B.md">2026 charter</a> and the <a href="gco-2026.pdf">season PDF</a>. For the code and data behind the club, visit the <a href="https://github.com/ly2xxx/gco">GCO repository on GitHub</a>.</p>
  </section>
</main>
</body>
</html>
```

- `tests/test_pages_site.py`: create stdlib-only pytest tests. No new dependency. Constants:
  - `REPO_ROOT = Path(__file__).resolve().parents[1]`
  - `DOCS_DIR = REPO_ROOT / "docs"`
  - `INDEX_PATH = DOCS_DIR / "index.html"`
  - `APPROVED_TAG = "sdlc/010-add-a-github-pages-page-at/approved"`
- Helper `_IndexParser(HTMLParser)`:
  - `convert_charrefs=True`
  - collects `headings: list[tuple[str, str]]` for `h1`/`h2` in document order
  - collects `section_ids: list[str]`
  - collects `attrs: list[tuple[str, str]]` for every `href` and `src`
  - collects `images: list[str]` from every `<img src>`
  - collects `scripts: list[str]` from every `<script src>` and sets `_in_script`
  - collects `meta_viewport: str | None` from `<meta name="viewport" content="...">`
  - collects `style_text: list[str]`
  - collects `visible_text: list[str]` only while inside `<body>`, excluding `<style>` and `<script>`
  - teardown: none; all parsing is in-process and file-backed.
- Helper `_parse_index() -> _IndexParser`: reads `INDEX_PATH` as UTF-8, feeds the parser, returns it.
- Helper `_live_dashboard_section(text: str) -> list[str]`: splitlines; find the line whose stripped value is `## 🎯 Live Dashboard`; collect lines until the next line starting with `## `; return those lines.
- `test_index_structure()`:
  - asserts `INDEX_PATH.is_file()`
  - asserts raw text contains `<body` case-insensitively
  - asserts `<title>` content is non-empty
  - asserts `parser.headings == [("h1", "GCO Golf Club"), ("h2", "Who We Are"), ("h2", "What We Play"), ("h2", "How the Season Works"), ("h2", "Learn More")]`
  - asserts `parser.section_ids == ["who-we-are", "what-we-play", "how-the-season-works", "learn-more"]`
  - proves spec 1 and 2.
- `test_visible_text_word_count()`:
  - joins `parser.visible_text` with spaces
  - counts words with `re.findall(r"[\w'’-]+", text)`
  - asserts `150 <= len(words) <= 600`
  - proves spec 3.
- `test_relative_links_and_images_exist()`:
  - for every `(tag, value)` in `parser.attrs`:
    - skip absolute `http://` and `https://` values
    - assert `not value.startswith("/")`
    - `decoded = urllib.parse.unquote(value)`
    - `path_part = decoded.split("#", 1)[0].split("?", 1)[0]`
    - `target = (DOCS_DIR / path_part).resolve()`
    - assert `target.is_file()`
    - assert `value == urllib.parse.quote(decoded, safe="/")`
  - proves spec 4 and 7.
- `test_absolute_urls_allowlist()`:
  - collects every `href`/`src` value starting with `http://` or `https://`
  - asserts exact list `["https://github.com/ly2xxx/gco"]`
  - proves spec 5.
- `test_at_least_one_local_image()`:
  - asserts `parser.images` is non-empty
  - for every `src`, assert it is relative and `(DOCS_DIR / urllib.parse.unquote(src)).resolve().is_file()`
  - assert each resolved image is relative to `DOCS_DIR.resolve()`
  - proves spec 6.
- `test_viewport_and_no_wide_pixel_widths()`:
  - asserts `parser.meta_viewport == "width=device-width, initial-scale=1"`
  - joins `parser.style_text`
  - for every regex match `(?:^|[;{])\s*(?:min-)?width\s*:\s*(\d+)px`, assert `int(match.group(1)) <= 320`
  - proves spec 8.
- `test_no_script_or_external_resources()`:
  - asserts raw text has no `<script` element
  - asserts `parser.scripts == []`
  - for any `<link ...>` or `<script>` attribute starting with `http://`/`https://`, assert it is absent from `parser.attrs`
  - proves spec 9.
- `test_content_matches_repository_facts()`:
  - builds `source_text` from the `## 🏌️ League Information` section of `README.md` plus `docs/GCO 2026章程.md`
  - `tournaments = ["提提卡卡杯", "Titicaca Cup", "暖男杯", "Warm Man Cup", "凯尔特人杯", "Celtic Cup"]`
  - `players = ["刘北南", "Jacky", "赵鲲", "杨子初", "Neo", "徐峥", "杨明", "曹振波", "李扬", "王文龙", "曾诚", "Justin"]`
  - asserts every tournament and player name appears in the page visible text and in `source_text`
  - asserts page text contains `2026`, regex `\b12\b`, and regex `\b3\b`
  - proves spec 12 and 13.
- `test_existing_test_files_unmodified()`:
  - runs `git ls-tree -r --name-only <APPROVED_TAG> -- tests features test_streamlit_app.py`
  - runs `git diff --name-only <APPROVED_TAG> -- tests features test_streamlit_app.py`
  - asserts the intersection of baseline and changed paths is empty
  - proves no existing test file was modified/deleted, supporting spec 14.

**Definition of done:**
- [ ] `tests/test_pages_site.py::test_index_structure`: proves spec 1 and 2 by parsing headings and section ids in document order.
- [ ] `tests/test_pages_site.py::test_visible_text_word_count`: proves spec 3 with a 150–600 word bound on body text excluding `<style>`.
- [ ] `tests/test_pages_site.py::test_relative_links_and_images_exist`: proves spec 4 and 7 by decoding every relative `href`/`src` to an existing file under `docs/` and requiring percent-encoded values for paths containing spaces or non-ASCII characters.
- [ ] `tests/test_pages_site.py::test_absolute_urls_allowlist`: proves spec 5 with the single allowed absolute URL.
- [ ] `tests/test_pages_site.py::test_at_least_one_local_image`: proves spec 6 by resolving at least one `<img src>` to a file under `docs/images/`.
- [ ] `tests/test_pages_site.py::test_viewport_and_no_wide_pixel_widths`: proves spec 8 with the exact viewport meta tag and no `width`/`min-width` pixel value above 320px.
- [ ] `tests/test_pages_site.py::test_no_script_or_external_resources`: proves spec 9 by rejecting `<script>` and absolute external `src`/stylesheet URLs.
- [ ] `tests/test_pages_site.py::test_content_matches_repository_facts`: proves spec 12 and 13 by checking 2026, 12 players, 3 tournaments, and all stated tournament/player names against `README.md` and the charter.
- [ ] `tests/test_pages_site.py::test_existing_test_files_unmodified`: proves no existing test file was touched.
- [ ] Observable: `docs/index.html` exists after the phase and the prescribed test command exits 0.

**Verify:**
```bash
uv run pytest tests/test_pages_site.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: README link to the Pages site

<!-- phase: 2 -->
<!-- targets: README.md, tests/test_readme_pages_link.py -->
<!-- frozen: docs/index.html, .github/workflows/ci.yml, .github/workflows/sdlc-phase.yml, .github/workflows/sdlc.yml, features/**, test_streamlit_app.py, tests/test_ai_*.py, tests/test_announcement_page_wiring.py, tests/test_league_*.py, tests/test_pinned_*.py, tests/test_theme_button_styles.py, tests/test_upcoming_section_visibility.py -->

**Goal:** `README.md` contains exactly one new visible Pages link inside the existing `## 🎯 Live Dashboard` section and no other README change.

**Changes:**
- `README.md`: in the `## 🎯 Live Dashboard` section, after the existing line
  `**📈 [Google Sheets Data](https://docs.google.com/spreadsheets/d/1ZvtWd8zHMI0k2GQGMWhtFHl5xuDbciOW/htmlview)** - View raw data`
  and before the following blank line, insert exactly this one line:
  ```
  **🏠 [GCO Golf Club Introduction](https://ly2xxx.github.io/gco/)** - Learn about the club and the Chinese golf community
  ```
  Do not change headings, line order, or any other text.
- `tests/test_readme_pages_link.py`: create stdlib-only pytest tests. Constants:
  - `REPO_ROOT = Path(__file__).resolve().parents[1]`
  - `README = REPO_ROOT / "README.md"`
  - `APPROVED_TAG = "sdlc/010-add-a-github-pages-page-at/approved"`
  - `EXPECTED_LINE = "**🏠 [GCO Golf Club Introduction](https://ly2xxx.github.io/gco/)** - Learn about the club and the Chinese golf community"`
- Helper `_read_baseline() -> str`: `subprocess.run(["git", "show", f"{APPROVED_TAG}:README.md"], check=True, text=True, capture_output=True).stdout`.
- Helper `_live_dashboard_section(text: str) -> list[str]`: splitlines; find stripped line `## 🎯 Live Dashboard`; return following lines until the next line starting with `## `.
- `test_live_dashboard_section_contains_pages_link()`:
  - reads current `README.md`
  - asserts `re.search(r"\[[^\]]+\]\(https://ly2xxx\.github\.io/gco/\)", section_text)` succeeds
  - asserts the line before `EXPECTED_LINE` is the existing Google Sheets link line
  - proves spec 10.
- `test_only_added_line_inside_live_dashboard()`:
  - baseline lines from `_read_baseline().splitlines(keepends=True)`
  - current lines from `README.read_text(encoding="utf-8").splitlines(keepends=True)`
  - uses `difflib.SequenceMatcher(None, baseline, current)`
  - asserts every opcode tag is `equal` or `insert`
  - collects all inserted lines; asserts exactly one inserted line
  - asserts `inserted[0].rstrip("\n") == EXPECTED_LINE`
  - asserts the sequence of heading lines is identical and in the same order between baseline and current
  - asserts `EXPECTED_LINE` appears in `_live_dashboard_section(current_text)`
  - proves spec 11.
- Teardown: none; tests read files and invoke local `git` only.

**Definition of done:**
- [ ] `tests/test_readme_pages_link.py::test_live_dashboard_section_contains_pages_link`: proves spec 10 by finding the exact Pages URL inside the Live Dashboard section, directly after the Google Sheets link line.
- [ ] `tests/test_readme_pages_link.py::test_only_added_line_inside_live_dashboard`: proves spec 11 by diffing against the approved tag and allowing only one inserted line with no heading changes.
- [ ] Observable: `git diff --unified=0 <APPROVED_TAG> -- README.md` shows only the one added line inside `## 🎯 Live Dashboard`; this is a reviewer check, not a separate command in Verify.

**Verify:**
```bash
uv run pytest tests/test_readme_pages_link.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 3: GitHub Pages workflow for `docs/`

<!-- phase: 3 -->
<!-- targets: .github/workflows/pages.yml, tests/test_pages_workflow.py -->
<!-- frozen: README.md, docs/index.html, .github/workflows/ci.yml, .github/workflows/sdlc-phase.yml, .github/workflows/sdlc.yml, features/**, test_streamlit_app.py, tests/test_ai_*.py, tests/test_announcement_page_wiring.py, tests/test_league_*.py, tests/test_pinned_*.py, tests/test_theme_button_styles.py, tests/test_upcoming_section_visibility.py -->

**Goal:** A push to `main` touching `docs/**` publishes `docs/` as the Pages artifact with `docs/index.html` at the site root.

**Changes:**
- `.github/workflows/pages.yml`: create exactly this workflow:

```yaml
name: Deploy GitHub Pages
on:
  push:
    branches: [main]
    paths: ['docs/**']
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
        with:
          enablement: true
      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- `tests/test_pages_workflow.py`: create stdlib-only pytest tests. Constants:
  - `REPO_ROOT = Path(__file__).resolve().parents[1]`
  - `WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pages.yml"`
  - `INDEX = REPO_ROOT / "docs" / "index.html"`
- `test_workflow_publishes_docs_root_index()`:
  - asserts `WORKFLOW.is_file()`
  - reads `WORKFLOW` as UTF-8 into `text`
  - asserts `"name: Deploy GitHub Pages"` in `text`
  - asserts `"push:"` in `text`
  - asserts `"paths: ['docs/**']"` in `text`
  - asserts `"workflow_dispatch:"` in `text`
  - asserts `"contents: read"`, `"pages: write"`, and `"id-token: write"` are in `text`
  - asserts `"concurrency:"` and `"group: pages"` are in `text`
  - asserts `"build:"` and `"deploy:"` are in `text`
  - asserts `"actions/checkout@v4"` in `text`
  - asserts `"actions/configure-pages@v5"` and `"enablement: true"` in `text`
  - asserts `"actions/upload-pages-artifact@v3"` and `"path: docs"` in `text`
  - asserts `"needs: build"` in `text`
  - asserts `"environment:"` and `"name: github-pages"` in `text`
  - asserts `"actions/deploy-pages@v4"` in `text`
  - asserts `INDEX.is_file()`, so the artifact root has an index file
  - proves spec 15.
- Teardown: none; pure file parsing and assertions.

**Definition of done:**
- [ ] `tests/test_pages_workflow.py::test_workflow_publishes_docs_root_index`: proves spec 15 by checking the Pages workflow uploads `docs/`, deploys it, and `docs/index.html` exists as the root index.
- [ ] Observable: `.github/workflows/pages.yml` exists and is valid YAML to the builder’s GitHub Actions parser; the prescribed test command exits 0.

**Verify:**
```bash
uv run pytest tests/test_pages_workflow.py -v
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- Word count falls outside 150–600, a heading/id is renamed, or an extra absolute URL is introduced: Phase 1 `test_visible_text_word_count`, `test_index_structure`, and `test_absolute_urls_allowlist` catch it.
- A relative `href`/`src` has a typo, misses percent-encoding, or points to a missing file: Phase 1 `test_relative_links_and_images_exist` and `test_at_least_one_local_image` catch it.
- CSS uses a `width`/`min-width` pixel value above 320px or adds a `<script>`/external stylesheet: Phase 1 `test_viewport_and_no_wide_pixel_widths` and `test_no_script_or_external_resources` catch it.
- README change lands outside `## 🎯 Live Dashboard`, modifies another line, or alters headings: Phase 2 `test_only_added_line_inside_live_dashboard` and `test_live_dashboard_section_contains_pages_link` catch it.
- Pages workflow has the wrong trigger, permissions, artifact path, or deploy job wiring: Phase 3 `test_workflow_publishes_docs_root_index` catches it.
- The live URL is not reachable until GitHub Pages runs after merge; this cannot be proven offline. Phase 3 proves the publishing configuration, and Open questions records the assumption.
- Any existing test file is modified: Phase 1 `test_existing_test_files_unmodified` and the final whole-suite run catch it.

## Open questions
- Live URL reachability at `https://ly2xxx.github.io/gco/` cannot be verified without network or a running GitHub Pages deployment. Assumed the repository is public, Pages is enabled by `actions/configure-pages@v5` with `enablement: true`, and the workflow deploys from `main` after merge.
- Default branch: assumed `main`, matching the clone URL already in `README.md`.
- Image choice: assumed `docs/images/gco-2026.pdf-0-49.png`; the spec allows any existing image under `docs/images/`, but this plan fixes that one for deterministic tests.
- Test baseline: assumed the approved tag `sdlc/010-add-a-github-pages-page-at/approved` exists in the verification checkout, as stated in the Feature section, because Phase 1 and Phase 2 compare against it.

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/010-add-a-github-pages-page-at/build-log.md` with one section per phase, in order. Head each
   one `## Phase <n>: <title>`, then list the files changed, the Verify command
   you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/010-add-a-github-pages-page-at`.

Commit only this plan's targets and `build-log.md`. Leave every other file alone,
including other features' documents under `sdlc/features/`, even for formatting;
verification fails on any file outside the targets.

The pipeline waits for this file. Once it has a section for every phase, it
verifies the whole branch and opens the pull request.

