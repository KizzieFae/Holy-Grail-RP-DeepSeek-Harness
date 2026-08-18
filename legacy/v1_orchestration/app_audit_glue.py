"""Audit logging kwargs seam: scene kwargs + cross-session injection report (Issue #174)."""

from typing import Any, Mapping

from cross_session_memory_policy import compact_report_for_audit
from summary_audit_helpers import get_scene_audit_logging_kwargs


def build_scene_audit_logging_kwargs_for_audit(
    scene_state: Any | None,
    session_state: Mapping[str, Any],
) -> dict[str, Any]:
    base = get_scene_audit_logging_kwargs(scene_state)
    report = session_state.get("cross_session_injection_report")
    if isinstance(report, dict):
        base = dict(base)
        base["cross_session_injection_report"] = compact_report_for_audit(report)
    return base
