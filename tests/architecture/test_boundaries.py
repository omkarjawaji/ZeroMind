"""Architecture fitness tests: the ADR rules, enforced in CI.

- ADR-0001/0002: the read plane and the executor never import each other.
- ADR-0003: the lab imports nothing from the rest of ZeroMind.
- ADR-0002 L1: broker write-tool names appear only in the executor and in the proxy's deny list.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APPS = ROOT / "apps"

FORBIDDEN_IMPORTS = {
    "papertrade": {"zeromind", "zeromind_executor", "kite_readonly_proxy", "announcements_mcp"},
    "zeromind": {"zeromind_executor"},
    "zeromind_executor": {"zeromind"},
    "announcements_mcp": {"zeromind_executor"},
    "kite_readonly_proxy": {"zeromind_executor"},
}

WRITE_TOOL_NAMES = (
    "place_order",
    "modify_order",
    "cancel_order",
    "place_gtt_order",
    "modify_gtt_order",
    "delete_gtt_order",
)

ALLOWED_WRITE_TOOL_PATHS = (
    Path("apps/zeromind_executor"),
    Path("apps/kite_readonly_proxy/src/kite_readonly_proxy/allowlist.py"),
)


def source_files(app: str) -> list[Path]:
    return sorted((APPS / app / "src").rglob("*.py"))


def imported_top_levels(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def is_allowed_write_path(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    return any(rel == allowed or allowed in rel.parents for allowed in ALLOWED_WRITE_TOOL_PATHS)


@pytest.mark.parametrize("app", sorted(FORBIDDEN_IMPORTS))
def test_app_does_not_import_forbidden_packages(app: str) -> None:
    files = source_files(app)
    assert files, f"no source files found for {app}"
    for path in files:
        bad = imported_top_levels(path) & FORBIDDEN_IMPORTS[app]
        assert not bad, f"{path.relative_to(ROOT)} imports forbidden package(s): {sorted(bad)}"


def test_write_tool_names_only_in_executor_and_proxy_denylist() -> None:
    offenders = []
    for app_dir in sorted(p for p in APPS.iterdir() if p.is_dir()):
        for path in sorted((app_dir / "src").rglob("*.py")):
            if is_allowed_write_path(path):
                continue
            text = path.read_text(encoding="utf-8")
            hits = [name for name in WRITE_TOOL_NAMES if name in text]
            if hits:
                offenders.append(f"{path.relative_to(ROOT)}: {hits}")
    assert not offenders, "write-tool names outside the executor:\n" + "\n".join(offenders)


def test_import_scanner_detects_forbidden_import(tmp_path: Path) -> None:
    sample = tmp_path / "bad.py"
    sample.write_text("import zeromind_executor.proposal\nfrom os import path\n", encoding="utf-8")
    assert imported_top_levels(sample) == {"zeromind_executor", "os"}


def test_relative_imports_are_not_treated_as_top_level(tmp_path: Path) -> None:
    sample = tmp_path / "rel.py"
    sample.write_text("from . import sibling\nfrom .pkg import thing\n", encoding="utf-8")
    assert imported_top_levels(sample) == set()
