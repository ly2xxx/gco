import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pinned_announcements import PINNED_ANNOUNCEMENTS, get_display_announcements  # noqa: E402

HOME_PAGE = REPO_ROOT / "streamlit_app.py"
ANNOUNCEMENTS_PAGE = REPO_ROOT / "pages" / "1_📢_Announcements.py"
APP_FILES = [
    REPO_ROOT / "streamlit_app.py",
    REPO_ROOT / "data.py",
    REPO_ROOT / "auth.py",
    REPO_ROOT / "theme.py",
    REPO_ROOT / "pinned_announcements.py",
    *sorted((REPO_ROOT / "pages").glob("*.py")),
    *sorted((REPO_ROOT / "utilities").glob("*.py")),
]
RELOCATED_NAMES = {"PINNED_ANNOUNCEMENTS", "get_display_announcements"}


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _import_sources(tree: ast.Module) -> dict[str, set[str]]:
    """Map local name -> set of modules it is imported from."""
    sources: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                sources.setdefault(alias.asname or alias.name, set()).add(node.module)
    return sources


def _defines_helper(tree: ast.Module) -> bool:
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "get_display_announcements"
        for node in ast.walk(tree)
    )


def _has_module_level_pinned_literal(tree: ast.Module) -> bool:
    """True for a module-level list/tuple literal of dicts that all have pinned=True."""
    def is_all_pinned(value: ast.AST) -> bool:
        if not isinstance(value, (ast.List, ast.Tuple)) or not value.elts:
            return False
        for element in value.elts:
            if not isinstance(element, ast.Dict):
                return False
            # AST nodes compare by identity, so match the "pinned" key by its value.
            pairs = {
                k.value: v for k, v in zip(element.keys, element.values) if isinstance(k, ast.Constant)
            }
            key = pairs.get("pinned")
            if not (isinstance(key, ast.Constant) and key.value is True):
                return False
        return True

    for node in tree.body:
        if isinstance(node, ast.Assign) and is_all_pinned(node.value):
            return True
        if isinstance(node, ast.AnnAssign) and node.value is not None and is_all_pinned(node.value):
            return True
    return False


def _calls_helper(tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "get_display_announcements"
        for node in ast.walk(tree)
    )


def _record(ann_id: str, pinned: bool) -> dict:
    return {
        "id": ann_id,
        "title": f"title-{ann_id}",
        "date": "2026-01-01",
        "author": "author",
        "pinned": pinned,
        "body": "body",
        "tags": [],
    }


def test_home_page_imports_shared_helper():
    """Spec behaviour 3."""
    assert "pinned_announcements" in _import_sources(_tree(HOME_PAGE)).get("get_display_announcements", set())


def test_home_page_has_no_local_pinned_records_or_helper():
    """Spec behaviour 3."""
    tree = _tree(HOME_PAGE)
    assert _has_module_level_pinned_literal(tree) is False
    assert _defines_helper(tree) is False


def test_home_page_calls_the_shared_helper():
    """Spec behaviour 11 (home side)."""
    assert _calls_helper(_tree(HOME_PAGE))


def test_home_page_selection_is_the_shared_selection():
    """Spec behaviours 5, 6: the 最新动态 cap keeps the first two module pinned records."""
    sample = [_record("n-1", False), _record("p-extra", True)]

    assert [a["id"] for a in get_display_announcements(sample)[:2]] == [
        record["id"] for record in PINNED_ANNOUNCEMENTS
    ][:2]


def test_no_file_imports_relocated_names_from_old_locations():
    """Spec behaviour 12."""
    paths = [
        *APP_FILES,
        *sorted(REPO_ROOT.glob("test_*.py")),
        *sorted((REPO_ROOT / "tests").glob("*.py")),
        *sorted((REPO_ROOT / "features").rglob("*.py")),
    ]
    violations = []
    for path in paths:
        for name, modules in _import_sources(_tree(path)).items():
            if name in RELOCATED_NAMES and modules != {"pinned_announcements"}:
                violations.append(f"{path.relative_to(REPO_ROOT)}: {name} from {sorted(modules)}")

    assert violations == []
