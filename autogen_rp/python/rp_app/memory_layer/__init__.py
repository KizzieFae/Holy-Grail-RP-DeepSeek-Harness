"""Legacy V1 memory_layer shim — implementation in v2/domain/modules/memory_layer/."""

from __future__ import annotations

import sys
from pathlib import Path

_MODULES = Path(__file__).resolve().parents[4] / "v2" / "domain" / "modules"
if str(_MODULES) not in sys.path:
    sys.path.insert(0, str(_MODULES))

from memory_layer.facade import *  # noqa: F403
