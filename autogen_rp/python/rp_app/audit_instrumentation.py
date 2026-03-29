"""Optional diagnostics for audit I/O failures and artifact gaps.

Enable with environment variable RP_AUDIT_INSTRUMENTATION=1 (or true/yes).
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("rp_app.audit")


def audit_instrumentation_enabled() -> bool:
    v = os.environ.get("RP_AUDIT_INSTRUMENTATION", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def log_audit_exception(context: str, exc: BaseException) -> None:
    if audit_instrumentation_enabled():
        logger.error("%s", context, exc_info=exc)


def log_audit_warning(message: str) -> None:
    if audit_instrumentation_enabled():
        logger.warning("%s", message)
