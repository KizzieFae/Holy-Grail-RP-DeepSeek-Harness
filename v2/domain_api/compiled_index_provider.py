"""Compiled retrieval index provider for KnowledgeService (M12.7)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .authored_knowledge import (
    AuthoredKnowledgeRecord,
    CANONICAL_TO_V2_AUTHORITY,
    compute_knowledge_id,
)
from .retrieval_selection import RetrievalQueryContext

PROVIDER_ID = "compiled-index-v3"


def _v2_authority(canonical_authority: str) -> str:
    return CANONICAL_TO_V2_AUTHORITY.get(canonical_authority, "suggestive")


def _format_role_slot_text(payload: dict[str, Any] | None, fallback_text: str) -> str:
    if not isinstance(payload, dict) or not payload:
        return str(fallback_text or "").strip()
    role_name = str(payload.get("role_name", "") or "").strip()
    parts = [f"role={role_name}"] if role_name else []
    for key in ("required", "authority", "presence_constraint"):
        if key in payload and payload[key] is not None:
            parts.append(f"{key}={payload[key]}")
    return ", ".join(parts) if parts else str(fallback_text or "").strip()


def _lane_for_chunk(chunk: dict[str, Any]) -> str:
    source_kind = str(chunk.get("source_kind", "") or "")
    knowledge_type = str(chunk.get("knowledge_type", "") or "")
    if source_kind == "scene_template" or knowledge_type in {
        "scene_setup_fact",
        "role_constraint",
    }:
        return "scene_reference"
    return "authored_character_knowledge"


def _chunk_to_record(
    chunk: dict[str, Any],
    *,
    source_index: int,
    subject_character_file_id: str | None,
    source_asset_id: str,
) -> AuthoredKnowledgeRecord | None:
    text = str(chunk.get("text", "") or "").strip()
    structured = chunk.get("structured_payload")
    if isinstance(structured, dict) and str(chunk.get("knowledge_type", "")) == "role_constraint":
        text = _format_role_slot_text(structured, text)
    if not text:
        return None

    source_ref = str(chunk.get("source_ref", "") or f"index:{source_index}")
    knowledge_kind = str(chunk.get("knowledge_type", "") or "lore_reference")
    knowledge_id = str(chunk.get("knowledge_id", "") or "").strip()
    if not knowledge_id:
        knowledge_id = compute_knowledge_id(
            source_ref=source_ref,
            text=text,
            knowledge_kind=knowledge_kind,
        )

    lane = _lane_for_chunk(chunk)
    return AuthoredKnowledgeRecord(
        knowledge_id=knowledge_id,
        knowledge_kind=knowledge_kind,
        content=text,
        authority_class=_v2_authority(str(chunk.get("authority_class", "") or "reference_only")),
        visibility=str(chunk.get("visibility", "") or "public"),
        subject_character_file_id=subject_character_file_id,
        source_kind=str(chunk.get("source_kind", "") or "compiled_index"),
        source_asset_id=source_asset_id,
        provenance={
            "knowledge_lane": lane,
            "source_ref": source_ref,
            "source_index": source_index,
            "canonical_authority_class": chunk.get("authority_class"),
            "retrieval_provider": PROVIDER_ID,
            "index_schema_version": chunk.get("schema_version"),
        },
    )


class CompiledIndexRetrievalProvider:
    """Backend-independent provider for precompiled authored retrieval indexes."""

    def __init__(self, index_path: str | Path | None = None) -> None:
        env_path = os.environ.get("HG_RETRIEVAL_INDEX_PATH", "").strip()
        legacy_path = os.environ.get("RP_RETRIEVED_CONTEXT_INDEX", "").strip()
        resolved = str(index_path or env_path or legacy_path or "").strip()
        self.index_path = resolved or None
        self._cache: dict[str, Any] | None = None

    @property
    def provider_id(self) -> str:
        return PROVIDER_ID

    def is_configured(self) -> bool:
        return bool(self.index_path)

    def load_index(self) -> dict[str, Any]:
        if self._cache is not None:
            return self._cache
        if not self.index_path:
            self._cache = {}
            return self._cache
        path = Path(self.index_path)
        if not path.is_file():
            raise FileNotFoundError(f"retrieval index not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("retrieval index root must be an object")
        self._cache = payload
        return payload

    def clear_cache(self) -> None:
        self._cache = None

    def query(self, ctx: RetrievalQueryContext) -> list[AuthoredKnowledgeRecord]:
        if not self.is_configured():
            return []
        index = self.load_index()
        records: list[AuthoredKnowledgeRecord] = []

        characters = index.get("characters") or {}
        if isinstance(characters, dict):
            for key in ctx.character_index_keys:
                chunks = characters.get(key)
                if not isinstance(chunks, list):
                    continue
                for source_index, chunk in enumerate(chunks):
                    if not isinstance(chunk, dict):
                        continue
                    record = _chunk_to_record(
                        chunk,
                        source_index=source_index,
                        subject_character_file_id=ctx.character_file_id,
                        source_asset_id=str(ctx.character_file_id or key),
                    )
                    if record is not None:
                        records.append(record)

        templates = index.get("templates") or {}
        template_id = str(ctx.session_template_id or "").strip()
        if template_id and isinstance(templates, dict):
            chunks = templates.get(template_id)
            if isinstance(chunks, list):
                for source_index, chunk in enumerate(chunks):
                    if not isinstance(chunk, dict):
                        continue
                    record = _chunk_to_record(
                        chunk,
                        source_index=source_index,
                        subject_character_file_id=None,
                        source_asset_id=template_id,
                    )
                    if record is not None:
                        records.append(record)

        lore = index.get("lore") or []
        if isinstance(lore, list):
            for source_index, chunk in enumerate(lore):
                if not isinstance(chunk, dict):
                    continue
                record = _chunk_to_record(
                    chunk,
                    source_index=source_index,
                    subject_character_file_id=None,
                    source_asset_id="global_lore",
                )
                if record is not None:
                    records.append(record)

        setup_notes = index.get("setup_notes") or []
        if isinstance(setup_notes, list):
            for source_index, chunk in enumerate(setup_notes):
                if not isinstance(chunk, dict):
                    continue
                record = _chunk_to_record(
                    chunk,
                    source_index=source_index,
                    subject_character_file_id=None,
                    source_asset_id=template_id or "setup",
                )
                if record is not None:
                    records.append(record)

        return records
