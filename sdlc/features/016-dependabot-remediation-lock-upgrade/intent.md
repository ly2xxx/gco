<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea,docs/dependabot-remediation.md#rules-for-every-piece,docs/dependabot-remediation.md#facts-the-plan-must-not-guess,docs/dependabot-remediation.md#piece-1@3a30764 -->
# Intent: Dependabot Lock Upgrade

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
The GCO project's lock file currently carries 151 open Dependabot alerts across 12 transitive packages, including critical alerts in pillow, gitpython, and pyjwt. Maintainers cannot clear tracking issue #76 while those vulnerable versions remain in `uv.lock`, and the security and compliance exposure persists even though no application code imports the alerted packages.

## Outcome
Every alerted package in `uv.lock` is either absent or at least the highest approved `fix_to` version, with `pyjwt`, `gitpython`, and `tornado` removed from the lock. `pyproject.toml` reflects the approved Python floor and the reduced MarkItDown extra set, and a dependency-floor test guards these conditions against regression. Application behavior and non-dependency files remain unchanged.

## Done when
- `uv.lock` has no `pyjwt`, `gitpython`, or `tornado` entries, and each alerted package name appears at most once.
- Every present lock entry for pillow, certifi, soupsieve, cryptography, urllib3, lxml, idna, pytest, or pygments is at or above its approved `fix_to` version; absent packages pass.
- `pyproject.toml` declares `requires-python = ">=3.11.5"` and exactly `markitdown[docx,pdf,pptx,xlsx,xls]>=0.1.5`.
- `tests/test_dependency_floors.py` exists and verifies the lock and manifest conditions above.
- The existing behave features pass unchanged.
- The existing tests still pass.

## Not in scope
- Application code, UI, pages, utilities, features, or refactoring; `streamlit_app.py`, `pages/`, `utilities/`, and `features/` are untouched.
- `requirements.txt`, `.github/`, and `sdlc/features/` of earlier features.
- Hand-editing `uv.lock`; lock resolution is produced by the approved package-manager workflow.
- Packages not named by the Dependabot tracking issue, and any dependency-range changes beyond the two approved `pyproject.toml` lines.

## Open questions
None.

## Design
Written from these approved sections, which the spec and plan stages read word for word:
- `docs/dependabot-remediation.md#rules-for-every-piece`
- `docs/dependabot-remediation.md#facts-the-plan-must-not-guess`
- `docs/dependabot-remediation.md#piece-1`

