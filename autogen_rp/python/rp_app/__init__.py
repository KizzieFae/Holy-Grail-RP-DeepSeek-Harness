"""Domain-module shims only — V1 orchestration moved to legacy/v1_orchestration.

DEPRECATED (M12.3): This directory no longer contains substantive runtime code.
Production Holy Grail uses V2 (Launch-Holy-Grail-V2.bat).

Remaining contents:
  - M12.2 shims forwarding to v2/domain/modules (domain semantics)
  - See legacy/v1_orchestration/ for fenced V1 Streamlit/AutoGen runtime
"""

from __future__ import annotations


def _deprecated_namespace_notice() -> None:
    """No-op marker; import side effects handled by legacy bootstrap in tests."""


__all__ = ["_deprecated_namespace_notice"]
