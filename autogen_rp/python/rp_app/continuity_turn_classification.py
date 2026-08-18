"""Legacy V1 import shim — implementation in v2/domain/modules/continuity_turn_classification.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MOD_NAME = 'continuity_turn_classification'
_MODULES = Path(__file__).resolve().parents[3] / "v2" / "domain" / "modules"
_IMPL = _MODULES / 'continuity_turn_classification.py'
if str(_MODULES) not in sys.path:
    sys.path.insert(0, str(_MODULES))

_existing = sys.modules.get(_MOD_NAME)
if _existing is None or Path(getattr(_existing, "__file__", "")).resolve() != _IMPL.resolve():
    _spec = importlib.util.spec_from_file_location(_MOD_NAME, _IMPL)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"Cannot load domain module: {_IMPL}")
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules[_MOD_NAME] = _mod
    _spec.loader.exec_module(_mod)
else:
    _mod = _existing

globals().update({k: v for k, v in _mod.__dict__.items() if not k.startswith("_")})
