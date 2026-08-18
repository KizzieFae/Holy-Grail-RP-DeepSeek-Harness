#!/usr/bin/env python3
"""M12.3 fence legacy V1 orchestration into legacy/v1_orchestration/."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RP_APP = REPO / "autogen_rp" / "python" / "rp_app"
V1 = REPO / "legacy" / "v1_orchestration"

KEEP_IN_RP_APP = {
    "__init__.py",
    "README.md",
    "DEPRECATED.md",
}


def is_domain_shim(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")[:700]
    return (
        "Legacy V1 import shim" in text
        or "Legacy V1 memory_layer shim" in text
    )


def move_tree(src: Path, dest: Path) -> None:
    if not src.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if dest.is_dir():
            shutil.rmtree(dest)
        else:
            dest.unlink()
    shutil.move(str(src), str(dest))


def main() -> int:
    V1.mkdir(parents=True, exist_ok=True)

    moved_py = 0
    for path in sorted(RP_APP.rglob("*.py")):
        rel = path.relative_to(RP_APP)
        if rel.parts[0] == "memory_layer" and is_domain_shim(path):
            continue
        if path.name in KEEP_IN_RP_APP:
            continue
        if is_domain_shim(path):
            continue
        dest = V1 / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(dest))
        moved_py += 1

    # Move orchestration-local data (rp_app/data, not autogen_rp/python/data).
    move_tree(RP_APP / "data", V1 / "data")

    # Move legacy docs co-located with runtime.
    for name in (
        "ARCHITECTURE.md",
        "AUDIT_DOCUMENTATION.md",
        "CHARACTER_MIGRATION_GUIDE.md",
        "README.md",
    ):
        src = RP_APP / name
        if src.is_file():
            dest = V1 / name
            if not dest.exists():
                shutil.move(str(src), str(dest))

    # Move v1_autogen_agents from legacy/ root.
    old_agents = REPO / "legacy" / "v1_autogen_agents.py"
    if old_agents.is_file():
        shutil.move(str(old_agents), str(V1 / "v1_autogen_agents.py"))

    print(f"Moved {moved_py} Python modules + data/docs to {V1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
