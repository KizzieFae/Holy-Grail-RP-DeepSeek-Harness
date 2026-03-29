"""Guard: bare `pytest` from autogen_rp/python must not collect vendored packages/* by default."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_default_pytest_collect_only_targets_only_rp_tests_tree() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
        env=os.environ.copy(),
    )
    combined = proc.stdout + proc.stderr
    assert proc.returncode == 0, combined
    assert "ERROR collecting packages" not in combined
    assert "ImportPathMismatchError" not in combined

    for line in proc.stdout.splitlines():
        s = line.strip()
        if not s or s.startswith("="):
            continue
        if "::" not in s:
            continue
        path_part = s.split("::", 1)[0].replace("\\", "/")
        assert path_part.startswith("tests/"), (
            f"expected node ids under tests/, got {s!r} "
            "(check [tool.pytest.ini_options] testpaths in pyproject.toml)"
        )
