"""Automated clean-architecture dependency boundary checks."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = BACKEND_ROOT / "src" / "app"
MODULES_ROOT = SOURCE_ROOT / "modules"


def python_files(root: Path) -> Iterator[Path]:
    """Yield source files while ignoring generated caches."""

    yield from sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def imported_modules(path: Path) -> set[str]:
    """Extract absolute and relative import targets from a Python source file."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            modules.add(node.module)
    return modules


def module_layer_files(layer: str) -> Iterator[Path]:
    """Yield files in every future module that implements the requested layer."""

    for module_directory in MODULES_ROOT.iterdir():
        candidate = module_directory / layer
        if module_directory.is_dir() and candidate.is_dir():
            yield from python_files(candidate)


def assert_no_import_prefixes(path: Path, forbidden_prefixes: tuple[str, ...]) -> None:
    """Fail with a readable path when a forbidden package crosses a boundary."""

    imports = imported_modules(path)
    violations = sorted(
        imported
        for imported in imports
        if any(
            imported == prefix or imported.startswith(f"{prefix}.") for prefix in forbidden_prefixes
        )
    )
    assert not violations, (
        f"{path.relative_to(BACKEND_ROOT)} imports forbidden packages: {violations}"
    )


@pytest.mark.architecture
def test_domain_never_imports_delivery_or_orm_frameworks() -> None:
    """Future domain code remains transport and persistence independent."""

    for path in module_layer_files("domain"):
        assert_no_import_prefixes(path, ("fastapi", "starlette", "sqlalchemy"))


@pytest.mark.architecture
def test_application_never_imports_fastapi() -> None:
    """Future application handlers stay callable outside HTTP."""

    for path in module_layer_files("application"):
        assert_no_import_prefixes(path, ("fastapi", "starlette"))


@pytest.mark.architecture
def test_core_never_imports_business_modules() -> None:
    """Technical core code cannot grow implicit business knowledge."""

    for path in python_files(SOURCE_ROOT / "core"):
        assert_no_import_prefixes(path, ("app.modules",))


@pytest.mark.architecture
def test_presentation_never_imports_sqlalchemy_orm() -> None:
    """Module HTTP adapters must return schemas, not ORM entities."""

    for path in module_layer_files("presentation"):
        assert_no_import_prefixes(path, ("sqlalchemy",))
