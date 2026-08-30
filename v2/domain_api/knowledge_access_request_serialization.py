"""JSON-safe serialization for KnowledgeAccessRequest payloads."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

_KAR_COLLECTION_KEYS = (
    "requested_information_classes",
    "exclude_source_tiers",
    "host_allowed_information_classes",
)


def knowledge_access_request_to_dict(request: Any) -> dict[str, Any]:
    """Convert a KnowledgeAccessRequest dataclass to a JSON-serializable dict."""
    payload = asdict(request)
    for key in _KAR_COLLECTION_KEYS:
        value = payload.get(key)
        if isinstance(value, (set, frozenset)):
            payload[key] = sorted(value)
    return payload
