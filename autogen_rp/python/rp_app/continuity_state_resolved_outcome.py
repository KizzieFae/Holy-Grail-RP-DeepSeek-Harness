"""Slot-scoped resolved outcome rows (registry / resolved-outcome pipeline)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ResolvedOutcome:
    """Slot-scoped continuity fact (registry / resolved-outcome pipeline).

    ``status`` on this row is the row lifecycle (``active`` / ``superseded`` /
    ``revoked``), not “story resolved.” Domain phase for transactional work lives
    in ``value`` (e.g. ``phase`` for Issue #127 scene commitments).
    """

    outcome_id: str
    category: str
    key: str
    subject_id: str
    value: dict[str, str]
    status: str = "active"
    source_event_id: str = ""
    source_issue_id: str | None = None
    rule_id: str = ""
    supersedes_outcome_id: str | None = None
    created_turn_index: int | None = None
    superseded_turn_index: int | None = None
    revoked_turn_index: int | None = None
    aspect_id: str = ""
    slot_key: str = ""

    def to_dict(self) -> dict:
        return {
            "outcome_id": self.outcome_id,
            "category": self.category,
            "key": self.key,
            "subject_id": self.subject_id,
            "value": dict(self.value),
            "status": self.status,
            "source_event_id": self.source_event_id,
            "source_issue_id": self.source_issue_id,
            "rule_id": self.rule_id,
            "supersedes_outcome_id": self.supersedes_outcome_id,
            "created_turn_index": self.created_turn_index,
            "superseded_turn_index": self.superseded_turn_index,
            "revoked_turn_index": self.revoked_turn_index,
            "aspect_id": self.aspect_id,
            "slot_key": self.slot_key,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ResolvedOutcome":
        category = str(data.get("category", "") or "")
        key = str(data.get("key", "") or "")
        subject_id = str(data.get("subject_id", "") or "")
        aspect_id = str(data.get("aspect_id") or "").strip()
        slot_key = str(data.get("slot_key") or "").strip()
        if (
            not slot_key
            and category == "assignment"
            and key == "sleeping_surface"
            and subject_id
        ):
            aspect_id = aspect_id or "lodging.sleep_surface"
            slot_key = f"{aspect_id}::{subject_id}"
        if not slot_key and category == "communication_state" and key == "housing_call":
            subject_id = subject_id or "scene"
            aspect_id = aspect_id or "communication.housing_call"
            slot_key = f"{aspect_id}::scene"
        if (
            not slot_key
            and category == "medical"
            and key == "suppressant_formulation"
            and subject_id
        ):
            aspect_id = aspect_id or "medical.suppressant_formulation"
            slot_key = f"{aspect_id}::{subject_id}"
        if (
            not slot_key
            and category == "access"
            and key == "location_entry"
            and subject_id
        ):
            aspect_id = aspect_id or "access.location_entry"
            location_id = str(
                (data.get("value") or {}).get("location_id", "")
                or (data.get("value") or {}).get("location", "")
                or ""
            ).strip()
            if location_id:
                slot_key = f"{aspect_id}::{subject_id}::{location_id}"
        if (
            not slot_key
            and category == "transaction"
            and key == "scene_commitment"
        ):
            vlo = data.get("value") or {}
            if isinstance(vlo, dict):
                k = str(vlo.get("kind", "") or "").strip()
                sc = str(vlo.get("subject_scope", "") or "").strip()
                aspect_id = aspect_id or "transaction.scene_commitment"
                if k and sc:
                    slot_key = f"{aspect_id}::{k}::{sc}"

        return cls(
            outcome_id=str(data.get("outcome_id", "") or ""),
            category=category,
            key=key,
            subject_id=subject_id,
            value={
                str(k): str(v)
                for k, v in (data.get("value") or {}).items()
                if isinstance(k, str)
            },
            status=str(data.get("status", "active") or "active"),
            source_event_id=str(data.get("source_event_id", "") or ""),
            source_issue_id=(
                str(data.get("source_issue_id"))
                if data.get("source_issue_id") is not None
                and str(data.get("source_issue_id")).strip()
                else None
            ),
            rule_id=str(data.get("rule_id", "") or ""),
            supersedes_outcome_id=(
                str(data.get("supersedes_outcome_id"))
                if data.get("supersedes_outcome_id") is not None
                and str(data.get("supersedes_outcome_id")).strip()
                else None
            ),
            created_turn_index=(
                int(data["created_turn_index"])
                if data.get("created_turn_index") is not None
                else None
            ),
            superseded_turn_index=(
                int(data["superseded_turn_index"])
                if data.get("superseded_turn_index") is not None
                else None
            ),
            revoked_turn_index=(
                int(data["revoked_turn_index"])
                if data.get("revoked_turn_index") is not None
                else None
            ),
            aspect_id=aspect_id,
            slot_key=slot_key,
        )
