"""Fenced legacy V1 orchestration runtime (DEPRECATED — retirement-only).

Production Holy Grail uses V2:
  Launch-Holy-Grail-V2.bat  /  cd v2/rp_runtime && npm run app

This package retains V1 Streamlit/AutoGen/turn_runner orchestration for
regression validation until M12.4 deletion. It consumes permanent domain
semantics from ``v2/domain`` — do not duplicate domain logic here.
"""

from legacy.v1_orchestration.bootstrap import ensure_v1_orchestration_paths

__all__ = ["ensure_v1_orchestration_paths"]
