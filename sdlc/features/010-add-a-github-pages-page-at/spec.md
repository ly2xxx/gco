<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@6022b91 -->
## Summary

Adds a public, static GitHub Pages landing page for the GCO club so non-developers have a shareable URL, and links that URL from `README.md`. The page is a single self-contained `docs/index.html` served at `https://ly2xxx.github.io/gco/`, published from `docs/` by a new Pages workflow, and it introduces the GCO club and the Chinese golf community using only facts already in the repository. No Python code, Streamlit page, or data flow changes.

## Behaviour

1. Given a checkout of the repository, when the `docs/` directory is inspected, then `docs/index.html` exists and contains a `<head>` with a non-empty `<title>`, a `<body>`, and an `<h1>` element.
2. Given `docs/index.html`, when its headings are read in document order, then they are `GCO Golf Club` (h1), then the h2s `Who We Are`, `What We Play`, `How the Season Works`, `Learn More`, and the four sections carry the ids `who-we-are`, `what-we-play`, `how-the-season-works`, `learn-more`.
3. Given `docs/index.html`, when its visible text is extracted (excluding the contents of `<style>`), then that text is at least 150 words and at most 600 words long.
4. Given `docs/index.html`, when every `href` and `src` attribute value is resolved relative to `docs/`, then each value that is not an absolute `http(s)` URL decodes to a path that exists in the repository, and no such value starts with `/`.
5. Given `docs/index.html`, when all absolute URLs in its `href` and `src` attributes are collected, then the only one is `https://github.com/ly2xxx/gco`.
6. Given `docs/index.html`, when its `<img>` elements are collected, then there is at least one, and every `src` decodes to a file that exists under `docs/`.
7. Given `docs/index.html`, when a `href` or `src` targets a repository file whose name contains a space or a non-ASCII character, then the attribute value is percent-encoded and percent-decoding it yields the exact repository path.
8. Given `docs/index.html`, when its `<head>` and `<style>` are parsed, then `<meta name="viewport" content="width=device-width, initial-scale=1">` is present, and no CSS declaration sets `width` or `min-width` to a pixel value greater than 320px.
9. Given `docs/index.html`, when the markup is scanned, then it contains no `<script>` element and no absolute `http(s)` URL in any `src` or stylesheet link, so the page renders identically with no network access.
10. Given `README.md`, when the lines between the `## 🎯 Live Dashboard` heading and the next `## ` heading are read, then one of those lines contains a Markdown link whose destination is exactly `https://ly2xxx.github.io/gco/`.
11. Given `README.md` after the change, when it is compared with its pre-change content, then the only added lines lie inside the `## 🎯 Live Dashboard` section: no heading is added, removed, renamed or reordered, and no other line is modified.
12. Given `docs/index.html`, when every tournament name and player name appearing in its text is looked up, then each name also appears in `README.md` (League Information section) or `docs/GCO 2026章程.md`.
13. Given `docs/index.html`, when it states a season year, a player count, or a tournament count, then the values stated are 2026, 12, and 3 respectively, matching `README.md`.
14. Given the repository after this change, when the existing suites are run (`uv run pytest`, `uv run behave`), then they pass and no existing test file has been modified.
15. Given the repository, when `.github/workflows/pages.yml` is parsed, then it uploads `docs/` as the Pages artifact and deploys it, and `docs/index.html` is the artifact's root index file.

## Interfaces

No Python module, function signature, or return type changes. New/changed files:

**`docs/index.html`** (new) — static Pages entry point served at the root of `https://ly2xxx.github.io/gco/`. Required structure (ids and heading text are the contract tests target):

- `<!DOCTYPE html>`, `<html lang="en">`
- `<head>`: `<meta charset="utf-8">`, `<meta name="viewport" content="width=device-width, initial-scale=1">`, `<title>GCO Golf Club — Chinese Golf Community</title>`, one inline `<style>` block
- `<body>`:
  - `<h1>GCO Golf Club</h1>` plus a one-line tagline
  - `<section id="who-we-are">` → `<h2>Who We Are</h2>`
  - `<section id="what-we-play">` → `<h2>What We Play</h2>`
  - `<section id="how-the-season-works">` → `<h2>How the Season Works</h2>`
  - `<section id="learn-more">` → `<h2>Learn More</h2>`, linking by relative URL to `gco-2026.pdf` and to `https://github.com/ly2xxx/gco`
- Relative URLs only, rooted at `docs/` (e.g. `images/<existing-file>.png`); at least one `<img>` whose `src` is an existing file under `docs/images/`

**`README.md`** (change) — add exactly one line inside the existing `## 🎯 Live Dashboard` section, directly after the two existing link lines:

```
**🏠 [GCO Golf Club Introduction](https://ly2xxx.github.io/gco/)** - Learn about the club and the Chinese golf community
```

**`.github/workflows/pages.yml`** (new) — publishes `docs/`:

- triggers: `push` to `main` with `paths: ['docs/**']`, plus `workflow_dispatch`
- `permissions`: `contents: read`, `pages: write`, `id-token: write`; `concurrency: group: pages`
- job `build`: `actions/checkout@v4`, `actions/configure-pages@v5` (`enablement: true`), `actions/upload-pages-artifact@v3` with `path: docs`
- job `deploy` (`needs: build`, `environment: github-pages`): `actions/deploy-pages@v4`

## Out of scope

- Any change to the Streamlit app, its pages, `data.py`, `ai_summary.py`, backups, or data flow.
- Restyling, translating, or republishing the charter / PDF documents; the page only links to them.
- A multi-page site, navigation menu, blog, CMS, or Jekyll theme.
- A custom domain or any DNS change.
- Membership signup, contact forms, analytics, or tracking.
- Automating content updates from the app's data sources.
- Rewriting or restructuring the rest of `README.md` beyond adding the link line.
- Fixing any pre-existing test failures unrelated to this change.

## Open questions

- **Page language** — intent is silent. Assumed English as the primary language, matching `README.md`, with Chinese club/tournament/player names kept as-is.
- **Scope of "Chinese golf community"** — assumed the page introduces the GCO club as part of the wider Chinese golf community, using only facts already in the repository (charter, tournaments, player list).
- **How Pages gets enabled** — the repository has no Pages configuration today. Assumed a GitHub Actions Pages workflow using the official Pages actions with `enablement: true`, rather than a manual "Source: main /docs" repository setting; and that the repository is public, so the site is reachable without login.
- **Default branch name** — assumed `main`, matching the clone URL in `README.md`.
- **External links** — assumed the only external link is the repository URL, so the page cannot rot; if a Google Sheets or dashboard link is wanted later, the allowlist in criterion 5 must be extended.
- **Which image the page uses** — assumed any single existing file under `docs/images/`; the spec fixes the requirement (an existing relative image) but not the specific file.
- **Length of "short"** — assumed one landing page of the four sections above, bounded by criterion 3 at 150–600 words, rather than a full club history.
