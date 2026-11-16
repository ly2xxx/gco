## Phase 1: Lock remediation and dependency-floor guard

Status: done. Files changed: `pyproject.toml`, `uv.lock`, `tests/test_dependency_floors.py`.

Raised `requires-python` to `>=3.11.5` and narrowed `markitdown[all]` to `markitdown[docx,pdf,pptx,xlsx,xls]`, then regenerated `uv.lock` with the approved `uv lock --upgrade-package ...` command. The new test reads the lock and manifest and checks every alerted package is absent or at its `fix_to`.

Lock result: streamlit 1.55.0 -> 1.67.0, pillow 13.0.0, certifi 2026.10.23, soupsieve 4.1.1 (single entry), cryptography 50.0.2, urllib3 2.8.0, lxml 6.1.3, idna 3.20, pytest 9.2.0, pygments 2.21.0; pyjwt, gitpython and tornado removed (with msal, azure-*, gitdb, speechrecognition and others).

Commands and results (Python 3.12, `uv pip install -r requirements.txt pytest`):
- `python -m pytest tests/test_dependency_floors.py -v`: 6 passed
- `python -m pytest -q`: 333 passed
- `behave --format progress`: 6 features, 17 scenarios, 58 steps passed
- `sdlc_stage.py verify --feature 016-dependabot-remediation-lock-upgrade --phase 1 --full`: exit 0

Deviations: none.
