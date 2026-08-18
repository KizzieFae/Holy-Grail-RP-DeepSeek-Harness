"""Compile and filter authored knowledge from M9 session setup snapshots."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from canonical_compile_adapters import resolve_adapter_row  # noqa: E402

MAX_AUTHORED_CHARACTER_ITEMS = 4
MAX_SCENE_REFERENCE_ITEMS = 3
MAX_LORE_EXCERPT_CHARS = 600

CANONICAL_TO_V2_AUTHORITY: dict[str, str] = {
    "reference_only": "suggestive",
    "setup_truth": "suggestive",
    "behavioral_guidance": "suggestive",
    "interpretive_guidance": "suggestive",
    "foundational_truth": "suggestive",
}

SCENE_REFERENCE_FIELDS = ("premise", "tone", "opening_text")


@dataclass(frozen=True)
class AuthoredKnowledgeRecord:
    knowledge_id: str
    knowledge_kind: str
    content: str
    authority_class: str
    visibility: str
    subject_character_file_id: str | None
    source_kind: str
    source_asset_id: str
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "knowledge_kind": self.knowledge_kind,
            "content": self.content,
            "authority_class": self.authority_class,
            "visibility": self.visibility,
            "subject_character_file_id": self.subject_character_file_id,
            "source_kind": self.source_kind,
            "source_asset_id": self.source_asset_id,
            "provenance": dict(self.provenance),
        }


def setup_snapshot_hash(snapshot: dict[str, Any]) -> str:
    payload = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def compute_knowledge_id(*, source_ref: str, text: str, knowledge_kind: str) -> str:
    norm = re.sub(r"\s+", " ", str(text or "").strip().lower())
    payload = f"v1|{source_ref}|{norm}|{knowledge_kind}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _truncate_lore(text: str) -> str:
    raw = str(text or "").strip()
    if len(raw) <= MAX_LORE_EXCERPT_CHARS:
        return raw
    if MAX_LORE_EXCERPT_CHARS <= 1:
        return "…"
    return raw[: MAX_LORE_EXCERPT_CHARS - 1] + "…"


def _v2_authority(canonical_authority: str) -> str:
    return CANONICAL_TO_V2_AUTHORITY.get(canonical_authority, "suggestive")


def _compile_lore_facts(
    *,
    card: dict[str, Any],
    character_file_id: str,
    snapshot_hash: str,
) -> list[AuthoredKnowledgeRecord]:
    row, _fallback = resolve_adapter_row("character", "lore_facts")
    lore_items = card.get("lore_facts") or []
    if not isinstance(lore_items, list):
        return []

    records: list[AuthoredKnowledgeRecord] = []
    for index, item in enumerate(lore_items):
        text = str(item or "").strip()
        if not text:
            continue
        source_ref = f"snapshot:{character_file_id}:lore_facts:{index}"
        knowledge_kind = row.knowledge_type
        records.append(
            AuthoredKnowledgeRecord(
                knowledge_id=compute_knowledge_id(
                    source_ref=source_ref,
                    text=text,
                    knowledge_kind=knowledge_kind,
                ),
                knowledge_kind=knowledge_kind,
                content=_truncate_lore(text),
                authority_class=_v2_authority(row.authority_class),
                visibility=row.visibility,
                subject_character_file_id=character_file_id,
                source_kind="character_card",
                source_asset_id=character_file_id,
                provenance={
                    "knowledge_lane": "authored_character_knowledge",
                    "source_field": "lore_facts",
                    "source_ref": source_ref,
                    "source_index": index,
                    "canonical_authority_class": row.authority_class,
                    "setup_snapshot_hash": snapshot_hash,
                },
            )
        )
    return records


def _compile_scene_template_reference(
    *,
    template: dict[str, Any],
    template_id: str,
    snapshot_hash: str,
) -> list[AuthoredKnowledgeRecord]:
    records: list[AuthoredKnowledgeRecord] = []
    for field_index, field_name in enumerate(SCENE_REFERENCE_FIELDS):
        raw = template.get(field_name)
        text = str(raw or "").strip()
        if not text:
            continue
        row, _fallback = resolve_adapter_row("template", field_name)
        source_ref = f"snapshot:{template_id}:{field_name}"
        knowledge_kind = row.knowledge_type
        records.append(
            AuthoredKnowledgeRecord(
                knowledge_id=compute_knowledge_id(
                    source_ref=source_ref,
                    text=text,
                    knowledge_kind=knowledge_kind,
                ),
                knowledge_kind=knowledge_kind,
                content=text,
                authority_class=_v2_authority(row.authority_class),
                visibility=row.visibility,
                subject_character_file_id=None,
                source_kind="scene_template",
                source_asset_id=template_id,
                provenance={
                    "knowledge_lane": "scene_reference",
                    "source_field": field_name,
                    "source_ref": source_ref,
                    "source_index": field_index,
                    "canonical_authority_class": row.authority_class,
                    "setup_snapshot_hash": snapshot_hash,
                    "source_scene_template_id": template_id,
                },
            )
        )
    return records


def compile_authored_records_from_snapshot(
    snapshot: dict[str, Any],
) -> list[AuthoredKnowledgeRecord]:
    if not snapshot:
        return []
    snap_hash = setup_snapshot_hash(snapshot)
    records: list[AuthoredKnowledgeRecord] = []

    cards = snapshot.get("character_cards") or {}
    if isinstance(cards, dict):
        for file_id, card in sorted(cards.items()):
            if not isinstance(card, dict):
                continue
            records.extend(
                _compile_lore_facts(
                    card=card,
                    character_file_id=str(file_id),
                    snapshot_hash=snap_hash,
                )
            )

    template = snapshot.get("scene_template")
    template_id = str(snapshot.get("scene_template_id") or "").strip()
    if template_id and isinstance(template, dict):
        records.extend(
            _compile_scene_template_reference(
                template=template,
                template_id=template_id,
                snapshot_hash=snap_hash,
            )
        )

    return records


def _visibility_allows(
    record: AuthoredKnowledgeRecord,
    *,
    character_file_id: str | None,
    session_template_id: str | None,
) -> bool:
    visibility = str(record.visibility or "").strip()
    if visibility == "character_scoped":
        return bool(character_file_id) and record.subject_character_file_id == character_file_id
    if visibility == "template_participants":
        if not session_template_id:
            return False
        return record.source_asset_id == session_template_id
    if visibility in {"public", "scope_global"}:
        return True
    return False


def select_authored_records(
    records: list[AuthoredKnowledgeRecord],
    *,
    character_file_id: str | None,
    session_template_id: str | None,
) -> tuple[list[AuthoredKnowledgeRecord], list[AuthoredKnowledgeRecord]]:
    character_records: list[AuthoredKnowledgeRecord] = []
    scene_records: list[AuthoredKnowledgeRecord] = []
    seen_ids: set[str] = set()

    for record in records:
        if record.knowledge_id in seen_ids:
            continue
        if not _visibility_allows(
            record,
            character_file_id=character_file_id,
            session_template_id=session_template_id,
        ):
            continue
        seen_ids.add(record.knowledge_id)
        lane = str(record.provenance.get("knowledge_lane", "") or "")
        if lane == "scene_reference":
            scene_records.append(record)
        else:
            character_records.append(record)

    character_records.sort(
        key=lambda item: int(item.provenance.get("source_index", 0) or 0)
    )
    scene_records.sort(
        key=lambda item: int(item.provenance.get("source_index", 0) or 0)
    )

    character_records = character_records[:MAX_AUTHORED_CHARACTER_ITEMS]
    scene_records = scene_records[:MAX_SCENE_REFERENCE_ITEMS]
    return character_records, scene_records


def format_knowledge_content(records: list[AuthoredKnowledgeRecord], *, title: str) -> str:
    if not records:
        return ""
    lines = [f"{title}:"]
    for record in records:
        lines.append(f"  • {record.content}")
    return "\n".join(lines)
