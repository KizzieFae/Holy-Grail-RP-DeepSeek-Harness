"""Retrieval env + logging helpers (Issue #166)."""

from __future__ import annotations

import logging
import os

from runtime_packet_types import RetrievedContextBundle

_LOG = logging.getLogger("rp_app.retrieved_context")


def get_index_path_from_env() -> str | None:
    v = os.environ.get("RP_RETRIEVED_CONTEXT_INDEX", "")
    s = str(v or "").strip()
    return s or None


def log_retrieval_if_active(bundle: RetrievedContextBundle, *, char_name: str) -> None:
    if not bundle.items:
        return
    refs = [it.source_ref for it in bundle.items]
    n_chars = sum(len(it.text) for it in bundle.items)
    _LOG.info(
        "retrieved_context char=%s items=%d chars=%d source_refs=%s",
        char_name,
        len(bundle.items),
        n_chars,
        refs,
    )
