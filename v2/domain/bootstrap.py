"""Bootstrap import paths for framework-neutral domain modules."""

from __future__ import annotations

import sys
from pathlib import Path

_V2 = Path(__file__).resolve().parent.parent
_DOMAIN = _V2 / "domain"
_MODULES = _DOMAIN / "modules"
_BOOTSTRAPPED = False


def ensure_domain_paths() -> None:
    """Register ``v2/`` and ``v2/domain/modules/`` on ``sys.path`` once."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    for path in (_V2, _MODULES):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)
    _BOOTSTRAPPED = True
