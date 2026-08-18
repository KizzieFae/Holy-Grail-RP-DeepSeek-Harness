#!/usr/bin/env python3
"""Regenerate rp_app shims with correct sys.modules registration."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RP_APP = REPO / "autogen_rp" / "python" / "rp_app"
MODULES = REPO / "v2" / "domain" / "modules"

SHIM = '''\
"""Legacy V1 import shim — implementation in v2/domain/modules/{relpath}."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MOD_NAME = {modname!r}
_MODULES = Path(__file__).resolve().parents[3] / "v2" / "domain" / "modules"
_IMPL = _MODULES / {relpath!r}
if str(_MODULES) not in sys.path:
    sys.path.insert(0, str(_MODULES))

_existing = sys.modules.get(_MOD_NAME)
if _existing is None or Path(getattr(_existing, "__file__", "")).resolve() != _IMPL.resolve():
    _spec = importlib.util.spec_from_file_location(_MOD_NAME, _IMPL)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"Cannot load domain module: {{_IMPL}}")
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules[_MOD_NAME] = _mod
    _spec.loader.exec_module(_mod)
else:
    _mod = _existing

globals().update({{k: v for k, v in _mod.__dict__.items() if not k.startswith("_")}})
'''


def main() -> None:
    count = 0
    for path in sorted(RP_APP.glob("*.py")):
        name = path.stem
        if name == "character_loader":
            continue
        impl = MODULES / f"{name}.py"
        if not impl.is_file():
            continue
        path.write_text(SHIM.format(relpath=f"{name}.py", modname=name), encoding="utf-8")
        count += 1

    ml_dir = RP_APP / "memory_layer"
    ml_init = ml_dir / "__init__.py"
    ml_init.write_text(
        '''\
"""Legacy V1 memory_layer shim — implementation in v2/domain/modules/memory_layer/."""

from __future__ import annotations

import sys
from pathlib import Path

_MODULES = Path(__file__).resolve().parents[4] / "v2" / "domain" / "modules"
if str(_MODULES) not in sys.path:
    sys.path.insert(0, str(_MODULES))

from memory_layer.facade import *  # noqa: F403
''',
        encoding="utf-8",
    )
    for fname in ("retrieval.py", "storage.py", "writes.py", "facade.py"):
        shim = ml_dir / fname
        modname = f"memory_layer.{fname[:-3]}"
        shim.write_text(
            SHIM.format(relpath=f"memory_layer/{fname}", modname=modname),
            encoding="utf-8",
        )
        count += 1
    print(f"Regenerated {count} shims")


if __name__ == "__main__":
    main()
