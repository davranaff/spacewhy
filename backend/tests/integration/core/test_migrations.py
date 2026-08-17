"""Alembic integration verification against the real PostgreSQL service."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.integration
def test_alembic_upgrade_and_consistency_check(test_database_url: str) -> None:
    """Alembic uses central metadata and reports no ungenerated schema changes."""

    environment = {**os.environ, "DATABASE__URL": test_database_url}
    upgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert upgrade.returncode == 0, upgrade.stderr

    consistency = subprocess.run(
        [sys.executable, "-m", "alembic", "check"],
        cwd=BACKEND_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert consistency.returncode == 0, consistency.stderr
