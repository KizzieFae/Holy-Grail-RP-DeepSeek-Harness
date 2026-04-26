"""CLI for user callout review (GitHub #125)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_PY = Path(__file__).resolve().parent.parent
_SCRIPT = _PY / "scripts" / "user_callout_review.py"


def _run(
    *args: str, cwd: Path, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *args],
        cwd=cwd,
        check=check,
        text=True,
        capture_output=True,
    )


def test_cli_help_exits_zero() -> None:
    p = _run("list", "--help", cwd=_PY, check=False)
    assert p.returncode == 0
    assert "list" in p.stdout.lower() or "unresolved" in p.stdout.lower()


def test_cli_list_empty_base(tmp_path: Path) -> None:
    p = _run("list", "--base-dir", str(tmp_path), cwd=_PY, check=True)
    assert p.returncode == 0
    assert "no unresolved" in p.stdout.lower() or "No unresolved" in p.stdout


def test_cli_show_not_found(tmp_path: Path) -> None:
    p = _run(
        "show",
        "--callout-id",
        "00000000-0000-0000-0000-000000000000",
        "--base-dir",
        str(tmp_path),
        cwd=_PY,
        check=False,
    )
    assert p.returncode == 1
    assert "not found" in p.stderr.lower() or "not found" in p.stdout.lower()
