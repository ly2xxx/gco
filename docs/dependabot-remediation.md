# Dependabot remediation

Clear the Dependabot alerts on `ly2xxx/gco` (`uv.lock`, from `pyproject.toml`) without
breaking the GCO golf league Streamlit dashboard. It is built in 1 piece, one SDLC
feature.

## Rules for every piece

- **Alerts**: the source of truth is the open tracking issue labelled `dependabot`,
  kept up to date by the Dependabot monitor workflow. A piece fixes only the packages
  it names. Every package it keeps must be at least the **highest** `fix_to` version
  the issue lists for it, never the lowest.
- **Pins**: `pyproject.toml` declares lower bounds (`>=`); exact versions live only in
  `uv.lock`, which `uv lock` writes. Never hand-edit `uv.lock`. `requirements.txt` is
  not changed.
- **Code changes**: none. No application code imports any of the alerted packages.
  No refactoring, no new features, no UI changes.
- **Tests**: pytest files in `tests/`, named `test_*.py`, putting the repository root on
  `sys.path` as the existing tests do; plus the behave features in `features/`. Tests
  never use the network or an API key. Read `pyproject.toml` and `uv.lock` with the
  standard library's `tomllib`, and compare versions with `packaging.version.Version`.
- **Install**: the pipeline runs `uv pip install -r requirements.txt` on Python 3.12, so
  its tests see the manifests as files, not as installed packages.
- **Never in scope**: `streamlit_app.py`, `pages/`, `utilities/`, `features/`,
  `requirements.txt`, `.github/`, `sdlc/features/` of earlier features.

## Facts the plan must not guess

Read from the code and the tracking issue on 2026-11-16. Use these exactly.

- Open alerts (issue #76, read 2026-11-16 23:31 UTC, source Dependabot alerts API):
  151 in 12 packages, all in `uv.lock`, none declared directly.
  pillow 12.1.1 (fix 13.0.0; critical, 61); gitpython 3.1.46 (fix 3.2.1; critical, 37);
  pyjwt 2.12.1 (fix 2.15.0; critical, 16); certifi 2026.2.25 (fix 2026.10.18; critical, 1);
  tornado 6.5.5 (fix 6.6.1; high, 14); soupsieve 2.8.3 (fix 4.0.0; high, 8);
  cryptography 46.0.6 (fix 50.0.0; high, 5); urllib3 2.6.3 (fix 2.8.0; high, 5);
  lxml 6.0.2 (fix 6.1.0; high, 1); idna 3.11 (fix 3.15; medium, 1);
  pytest 9.0.2 (fix 9.0.3; medium, 1); pygments 2.19.2 (fix 2.20.0; low, 1).
- Where they come from: pillow, gitpython and tornado from `streamlit` (1.55.0 caps
  `pillow<13`); pyjwt from `markitdown[all]` through `azure-identity`/`msal`;
  soupsieve from `beautifulsoup4`; cryptography from `pdfminer-six` and `msal`; lxml from
  `python-pptx`; certifi, urllib3, idna from `requests`; pygments from `pytest`.
- `streamlit` 1.67.0 runs on `starlette`/`uvicorn` and no longer depends on `tornado` or
  `gitpython`; upgrading it removes both from the lock and lifts the `pillow<13` cap.
- `soupsieve` 4.x needs Python ≥ 3.11.5. With `requires-python = ">=3.11"` the lock keeps
  a second, vulnerable `soupsieve` 2.10 entry for Python < 3.11.5.
- `markitdown` is imported only in `utilities/doc_to_md.py` (`from markitdown import
  MarkItDown`; `MarkItDown().convert(path).text_content`), a stand-alone DOCX/PDF/PPTX/Excel
  converter. It needs the `docx`, `pdf`, `pptx`, `xlsx` and `xls` extras only. Dropping
  the other extras removes `pyjwt`, `msal`, `msal-extensions`, `azure-identity`,
  `azure-core`, `azure-ai-documentintelligence` and 8 more packages from the lock.
- No `.py` file in the repository imports `PIL`, `git`, `jwt`, `tornado`, `bs4`,
  `soupsieve`, `cryptography`, `lxml`, `urllib3`, `idna`, `certifi` or `pygments`.
- Checked in a clean Python 3.12 install of the final lock: `python -m pytest -q`
  326 passed, 1 skipped; `behave` 17 scenarios passed; the app and all six pages
  render under `streamlit.testing.v1.AppTest`; `streamlit run` answers
  `/_stcore/health` with `ok`; `markitdown` converts a DOCX; `pip-audit` finds no
  known vulnerabilities.
- `pyproject.toml` and `uv.lock` are ASCII with LF line endings and no byte-order mark.

## Done

- Piece 1 (feature `016-dependabot-remediation-lock-upgrade`, ly2xxx/gco#80, merged
  2026-11-16): all 151 alerts closed. The monitor read "No open alerts" from the
  Dependabot alerts API at 2026-11-16 23:56 UTC and closed issue #76.
  `.trivyignore`: no entries added. Remediation complete.

## Piece 1: Lock upgrade

Every alerted package is gone from `uv.lock` or at or above its `fix_to` version.

- In `pyproject.toml`, change exactly two lines: `requires-python = ">=3.11"` becomes
  `requires-python = ">=3.11.5"`, and `"markitdown[all]>=0.1.5",` becomes
  `"markitdown[docx,pdf,pptx,xlsx,xls]>=0.1.5",`. Nothing else in the file changes.
- Regenerate the lock with `uv lock --upgrade-package streamlit --upgrade-package pillow
  --upgrade-package certifi --upgrade-package soupsieve --upgrade-package cryptography
  --upgrade-package urllib3 --upgrade-package lxml --upgrade-package idna
  --upgrade-package pytest --upgrade-package pygments`.
  Expected (2026-11-16): streamlit 1.67.0, pillow 13.0.0, certifi 2026.10.23,
  soupsieve 4.1.1, cryptography 50.0.2, urllib3 2.8.0, lxml 6.1.3, idna 3.20,
  pytest 9.2.0, pygments 2.21.0; gitpython, tornado and pyjwt absent.
- Add `tests/test_dependency_floors.py`, reading `uv.lock` and `pyproject.toml`:
  - every `[[package]]` named pillow, gitpython, pyjwt, certifi, tornado, soupsieve,
    cryptography, urllib3, lxml, idna, pytest or pygments has a version at or above
    that package's `fix_to` in the Facts (a package that is absent passes);
  - each of those names appears at most once in the lock;
  - `pyjwt`, `gitpython` and `tornado` are absent;
  - `requires-python` is `">=3.11.5"`, and the `markitdown` dependency is exactly
    `markitdown[docx,pdf,pptx,xlsx,xls]>=0.1.5`.
- The existing pytest suite and behave features pass unchanged.
