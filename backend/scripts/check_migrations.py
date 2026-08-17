"""Run Alembic's metadata consistency check as an explicit operational command."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    """Return Alembic's process status without swallowing migration failures."""

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "check"],
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
