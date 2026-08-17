"""Additional architectural guardrails for future modular vertical slices."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = BACKEND_ROOT / "src" / "app"
MODULES_ROOT = SOURCE_ROOT / "modules"
MAIN_PATH = SOURCE_ROOT / "main.py"


def imported_modules(path: Path) -> set[str]:
    """Return absolute import module strings from a source file."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            modules.add(node.module)
    return modules


@pytest.mark.architecture
def test_main_is_a_minimal_asgi_entry_point() -> None:
    """main.py must only import the factory and instantiate its app."""

    tree = ast.parse(MAIN_PATH.read_text(encoding="utf-8"), filename=str(MAIN_PATH))

    assert len(tree.body) == 2
    first, second = tree.body
    assert isinstance(first, ast.ImportFrom)
    assert first.module == "app.bootstrap.app_factory"
    assert [alias.name for alias in first.names] == ["create_app"]
    assert isinstance(second, ast.Assign)
    assert len(second.targets) == 1
    assert isinstance(second.targets[0], ast.Name)
    assert second.targets[0].id == "app"
    assert isinstance(second.value, ast.Call)
    assert isinstance(second.value.func, ast.Name)
    assert second.value.func.id == "create_app"
    assert not second.value.args
    assert not second.value.keywords


@pytest.mark.architecture
def test_one_module_cannot_import_another_modules_infrastructure() -> None:
    """Cross-module calls are limited to explicit public contracts."""

    violations: list[str] = []
    for module_directory in MODULES_ROOT.iterdir():
        if not module_directory.is_dir() or module_directory.name.startswith("_"):
            continue
        current_module = module_directory.name
        for path in module_directory.rglob("*.py"):
            for imported in imported_modules(path):
                parts = imported.split(".")
                if (
                    len(parts) >= 4
                    and parts[0:2] == ["app", "modules"]
                    and parts[2] != current_module
                    and parts[3] == "infrastructure"
                ):
                    violations.append(f"{path.relative_to(BACKEND_ROOT)} imports {imported}")

    assert not violations, "Cross-module infrastructure imports are forbidden: " + "; ".join(
        violations
    )
