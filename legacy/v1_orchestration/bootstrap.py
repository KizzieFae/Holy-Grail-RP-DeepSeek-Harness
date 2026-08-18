"""Bootstrap import paths for fenced legacy V1 orchestration."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_V1 = Path(__file__).resolve().parent
_RP_APP = _REPO / "autogen_rp" / "python" / "rp_app"
_V2 = _REPO / "v2"
_BOOTSTRAPPED = False


def ensure_v1_orchestration_paths() -> None:
    """Register legacy orchestration, domain shims, and neutral domain paths."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    if str(_REPO) not in sys.path:
        sys.path.insert(0, str(_REPO))
    for path in (_V1, _RP_APP):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)
    if str(_V2) not in sys.path:
        sys.path.insert(0, str(_V2))

    from domain.bootstrap import ensure_domain_paths  # noqa: WPS433

    ensure_domain_paths()
    _BOOTSTRAPPED = True
