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
