"""Deterministic player source indexing and accounting validation (#91)."""

from __future__ import annotations

import hashlib
import unicodedata
from typing import Any

SOURCE_ACCOUNTING_NORMALIZATION = "nfc_crlf_to_lf"
VALID_DISPOSITIONS = frozenset({"projects", "non_projects"})


def normalize_source_for_indexing(content: str) -> str:
    """Indexing view only — stored ``content`` is not mutated."""
    text = unicodedata.normalize("NFC", str(content or ""))
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalized_source_sha256(normalized_source: str) -> str:
    return hashlib.sha256(normalized_source.encode("utf-8")).hexdigest()


def validate_source_accounting(
    *,
    normalized_source: str,
    accounting: dict[str, Any] | None,
    unit_ids: set[str],
) -> tuple[bool, str]:
    if not isinstance(accounting, dict):
        return False, "source_accounting missing or not an object"

    source_length = len(normalized_source)
    declared_length = accounting.get("source_length")
    if declared_length is not None and int(declared_length) != source_length:
        return False, "source_length mismatch"

    declared_hash = str(accounting.get("source_sha256", "") or "").strip()
    actual_hash = normalized_source_sha256(normalized_source)
    if declared_hash and declared_hash != actual_hash:
        return False, "source_sha256 mismatch"

    segments_raw = accounting.get("segments")
    if not isinstance(segments_raw, list):
        return False, "source_accounting.segments not a list"

    if source_length == 0:
        if len(segments_raw) != 1:
            return False, "empty source requires exactly one accounting segment"
        segment = segments_raw[0]
        if not isinstance(segment, dict):
            return False, "invalid empty-source segment"
        start = int(segment.get("char_start", -1))
        end = int(segment.get("char_end", -1))
        if start != 0 or end != 0:
            return False, "empty source segment must be [0,0)"
        disposition = str(segment.get("disposition", "") or "").strip().lower()
        if disposition not in VALID_DISPOSITIONS:
            return False, "invalid empty-source segment disposition"
        if disposition == "projects" and segment.get("unit_ids"):
            return False, "empty source cannot project units"
        return True, ""

    if not segments_raw:
        return False, "source_accounting.segments empty"

    seen_segment_ids: set[str] = set()
    cursor = 0
    for index, segment in enumerate(segments_raw):
        if not isinstance(segment, dict):
            return False, f"segment {index} not an object"
        segment_id = str(segment.get("segment_id", "") or "").strip()
        if not segment_id or segment_id in seen_segment_ids:
            return False, f"segment {index} invalid or duplicate segment_id"
        seen_segment_ids.add(segment_id)

        try:
            start = int(segment["char_start"])
            end = int(segment["char_end"])
        except (KeyError, TypeError, ValueError):
            return False, f"segment {segment_id} invalid bounds"

        if start < 0 or end < start or end > source_length:
            return False, f"segment {segment_id} out of bounds"
        if start != cursor:
            return False, f"segment {segment_id} gap or misordered coverage"
        cursor = end

        disposition = str(segment.get("disposition", "") or "").strip().lower()
        if disposition not in VALID_DISPOSITIONS:
            return False, f"segment {segment_id} invalid disposition"

        linked_units = segment.get("unit_ids")
        if not isinstance(linked_units, list):
            return False, f"segment {segment_id} unit_ids not a list"
        linked_unit_ids = [str(item).strip() for item in linked_units if str(item).strip()]

        if disposition == "projects" and not linked_unit_ids:
            return False, f"segment {segment_id} projects without unit_ids"
        if disposition == "non_projects" and linked_unit_ids:
            return False, f"segment {segment_id} non_projects must not reference units"

        for unit_id in linked_unit_ids:
            if unit_id not in unit_ids:
                return False, f"segment {segment_id} references unknown unit {unit_id}"

    if cursor != source_length:
        return False, "source_accounting incomplete coverage"

    return True, ""
