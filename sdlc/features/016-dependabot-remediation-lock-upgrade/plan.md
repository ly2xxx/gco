<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md,docs/dependabot-remediation.md#rules-for-every-piece,docs/dependabot-remediation.md#facts-the-plan-must-not-guess,docs/dependabot-remediation.md#piece-1@41ac576 -->
## Approach
The smallest change is a single phase: edit exactly the two approved `pyproject.toml` lines, regenerate `uv.lock` with the approved `uv lock` command, and add one read-only pytest module that validates the manifest and lock with `tomllib` and `packaging.version.Version`. The phase Verify block runs the new guard plus the existing pytest and behave suites so the dependency change is proven without touching application code.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| `uv.lock` has no `pyjwt`, `gitpython`, or `tornado` entries, and each alerted package name appears at most once. | 3, 4 | Phase 1 |
| Every present lock entry for pillow, certifi, soupsieve, cryptography, urllib3, lxml, idna, pytest, or pygments is at or above its approved `fix_to` version; absent packages pass. | 1, 2 | Phase 1 |
| `pyproject.toml` declares `requires-python = ">=3.11.5"` and exactly `markitdown[docx,pdf,pptx,xlsx,xls]>=0.1.5`. | 5, 6 | Phase 1 |
| `tests/test_dependency_floors.py` exists and verifies the lock and manifest conditions above. | 7, 8 | Phase 1 |
| The existing behave features pass unchanged. | 9 | Phase 1 |
| The existing tests still pass. | 10 | Phase 1 |

## Phase 1: Lock remediation and dependency-floor guard
<!-- phase: 1 -->
<!-- targets: pyproject.toml, uv.lock, tests/test_dependency_floors.py -->
<!-- frozen: streamlit_app.py, pages/**, utilities/**, features/**, requirements.txt, .github/**, sdlc/features/**, test_streamlit_app.py, tests/test_ai_*.py, tests/test_announcement_page_wiring.py, tests/test_league_*.py, tests/test_pinned_*.py, tests/test_state_backup_on_save.py, tests/test_theme_button_styles.py, tests/test_upcoming_section_visibility.py -->

**Goal:** After the approved lock upgrade, `uv.lock` has no `pyjwt`, `gitpython`, or `tornado`, each alerted package is unique and at or above its floor, and the manifest and new guard match the approved values.

**Changes:**
- `pyproject.toml`: make exactly these two line edits and no others:
  - Change `requires-python = ">=3.11"` to `requires-python = ">=3.11.5"`.
  - Change `"markitdown[all]>=0.1.5",` to `"markitdown[docx,pdf,pptx,xlsx,xls]>=0.1.5",`.
- `uv.lock`: do not hand-edit. From the repository root, run the approved package-manager workflow:
  ```bash
  uv lock --upgrade-package streamlit --upgrade-package pillow --upgrade-package certifi --upgrade-package soupsieve --upgrade-package cryptography --upgrade-package urllib3 --upgrade-package lxml --upgrade-package idna --upgrade-package pytest --upgrade-package pygments
  ```
  Keep the resulting `uv.lock`. The expected result is `streamlit` 1.67.0 or newer, the alerted packages at or above their `fix_to` floors, and `gitpython`, `tornado`, and `pyjwt` absent.
- `tests/test_dependency_floors.py`: create the file with this exact content:
  ```python
  import sys
  import tomllib
  from pathlib import Path

  from packaging.version import Version

  ROOT = Path(__file__).resolve().parents[1]
  if str(ROOT) not in sys.path:
      sys.path.insert(0, str(ROOT))

  FIX_TO = {
      "pillow": "13.0.0",
      "gitpython": "3.2.1",
      "pyjwt": "2.15.0",
      "certifi": "2026.10.18",
      "tornado": "6.6.1",
      "soupsieve": "4.0.0",
      "cryptography": "50.0.0",
      "urllib3": "2.8.0",
      "lxml": "6.1.0",
      "idna": "3.15",
      "pytest": "9.0.3",
      "pygments": "2.20.0",
  }
  REMOVED = ("pyjwt", "gitpython", "tornado")


  def _read_toml(filename: str) -> dict:
      with (ROOT / filename).open("rb") as handle:
          return tomllib.load(handle)


  def _alerted_lock_versions() -> dict[str, list[str]]:
      versions: dict[str, list[str]] = {}
      for package in _read_toml("uv.lock").get("package", []):
          name = package.get("name")
          if name in FIX_TO:
              versions.setdefault(name, []).append(package["version"])
      return versions


  def test_alerted_packages_at_or_above_fix_to() -> None:
      for name, versions in _alerted_lock_versions().items():
          for version in versions:
              assert Version(version) >= Version(FIX_TO[name]), (
                  f"{name} {version} is below fix_to {FIX_TO[name]}"
              )


  def test_alerted_packages_appear_at_most_once() -> None:
      for name, versions in _alerted_lock_versions().items():
          assert len(versions) <= 1, f"{name} appears {len(versions)} times in uv.lock"


  def test_removed_packages_absent() -> None:
      versions = _alerted_lock_versions()
      for name in REMOVED:
          assert name not in versions, f"{name} is still present in uv.lock"


  def test_requires_python_floor() -> None:
      project = _read_toml("pyproject.toml")["project"]
      assert project["requires-python"] == ">=3.11.5"


  def test_markitdown_dependency_exact() -> None:
      dependencies = _read_toml("pyproject.toml")["project"]["dependencies"]
      markitdown_dependencies = [dep for dep in dependencies if dep.startswith("markitdown")]
      assert markitdown_dependencies == ["markitdown[docx,pdf,pptx,xlsx,xls]>=0.1.5"]


  def test_dependency_floors_test_file_exists() -> None:
      assert (ROOT / "tests" / "test_dependency_floors.py").is_file()
  ```
- No application callable, route, UI, page, or utility is added or changed. `utilities/doc_to_md.py` signatures remain exactly `DocToMarkdownConverter.__init__(self)`, `DocToMarkdownConverter.convert(self, input_doc: str | Path, output_md: str | Path | None = None) -> str`, and `main()`.

**Definition of done:**
- [ ] `tests/test_dependency_floors.py`, test `test_alerted_packages_at_or_above_fix_to`: proves spec behaviours 1 and 2. It reads `uv.lock`, collects only `[[package]]` entries whose `name` is in `FIX_TO`, and asserts `packaging.version.Version(version) >= Version(FIX_TO[name])` for every present version. Absent packages are not iterated and therefore pass. No fixtures or teardown; pure read-only file parsing.
- [ ] `tests/test_dependency_floors.py`, test `test_alerted_packages_appear_at_most_once`: proves spec behaviour 3. It groups alerted lock entries by name and asserts `len(versions) <= 1` for each present name. No fixtures or teardown.
- [ ] `tests/test_dependency_floors.py`, test `test_removed_packages_absent`: proves spec behaviour 4. It asserts `pyjwt`, `gitpython`, and `tornado` are not keys in the collected alerted versions. No fixtures or teardown.
- [ ] `tests/test_dependency_floors.py`, test `test_requires_python_floor`: proves spec behaviour 5. It reads `pyproject.toml` with `tomllib` and asserts `project["requires-python"] == ">=3.11.5"`. No fixtures or teardown.
- [ ] `tests/test_dependency_floors.py`, test `test_markitdown_dependency_exact`: proves spec behaviour 6. It filters `project["dependencies"]` for entries starting with `markitdown` and asserts the result is exactly `["markitdown[docx,pdf,pptx,xlsx,xls]>=0.1.5"]`. No fixtures or teardown.
- [ ] `tests/test_dependency_floors.py`, test `test_dependency_floors_test_file_exists`: proves spec behaviour 7. It asserts `(ROOT / "tests" / "test_dependency_floors.py").is_file()`. No fixtures or teardown.
- [ ] New module passes offline with `python -m pytest tests/test_dependency_floors.py -v`, proving spec behaviour 8.
- [ ] Existing pytest suite passes unchanged with `python -m pytest -q`, proving spec behaviour 10.
- [ ] Existing behave features pass unchanged with `behave --format progress`, proving spec behaviour 9.

**Verify:**
```bash
python -m pytest tests/test_dependency_floors.py -v
python -m pytest -q
behave --format progress
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- `uv lock` may fail or resolve a package below its approved floor if the package index or constraints differ. `test_alerted_packages_at_or_above_fix_to` catches any present version below `fix_to`.
- The lock may retain a duplicate alerted entry or a removed package. `test_alerted_packages_appear_at_most_once` and `test_removed_packages_absent` catch those cases.
- The two `pyproject.toml` edits may be misapplied or another `markitdown` dependency may remain. `test_requires_python_floor` and `test_markitdown_dependency_exact` catch both.
- Upgraded dependencies may break existing application behaviour or tests. `python -m pytest -q` and `behave --format progress` catch regressions in the phase Verify block.
- The approved `uv lock` step needs package-index access during the build. If that access is unavailable, the lock cannot be regenerated and the phase must stop rather than hand-edit `uv.lock`.

## Open questions
None.

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/016-dependabot-remediation-lock-upgrade/build-log.md` with one section per phase, in order. Head each
   one `## Phase <n>: <title>`, then list the files changed, the Verify command
   you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/016-dependabot-remediation-lock-upgrade`.

Commit only this plan's targets and `build-log.md`. Leave every other file alone,
including other features' documents under `sdlc/features/`, even for formatting;
verification fails on any file outside the targets.

The pipeline waits for this file. Once it has a section for every phase, it
verifies the whole branch and opens the pull request.

