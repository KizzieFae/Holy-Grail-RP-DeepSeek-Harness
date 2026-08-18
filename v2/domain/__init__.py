"""Framework-neutral Holy Grail domain library (V2).

Permanent domain code lives under ``domain/`` (cards, paths, bootstrap) and
``domain/modules/`` (continuity, validation, memory, persistence, etc.).
Legacy V1 imports ``rp_app`` shims that delegate here.
"""

from .bootstrap import ensure_domain_paths

__all__ = ["ensure_domain_paths"]
