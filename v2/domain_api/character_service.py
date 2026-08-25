"""Character knowledge-orientation orchestration (#38)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any

from .character_contract import (
    CHARACTER_ORIENTATION_SCHEMA,
    CharacterOrientationAssessment,
    orientation_to_knowledge_access_request,
    parse_character_orientation,
)
from .character_epistemic import build_character_visibility_envelope
from .character_knowledge_validity import build_character_knowledge_reuse_key
from .character_orientation_context import build_character_orientation_context
from .character_upstream_context import CharacterUpstreamContext, assemble_character_upstream_contributions
from .librarian_contract import ALL_INFORMATION_CLASSES, new_request_id, validate_knowledge_access_request
from .session_state import LiveSession, RoundFixture


def _kar_to_dict(request: Any) -> dict[str, Any]:
    payload = asdict(request)
    for key in ("requested_information_classes", "exclude_source_tiers", "host_allowed_information_classes"):
        value = payload.get(key)
        if isinstance(value, (set, frozenset)):
            payload[key] = sorted(value)
    return payload


class CharacterKnowledgeService:
    def prepare_orientation_context(
        self,
        fixture: LiveSession,
        rnd: RoundFixture,
        *,
        inference_id: str,
        character_id: str,
        role: str,
        turn_index: int,
        director_decision: dict[str, Any] | None,
        correction_context: dict[str, Any] | None,
        memory_projections: list[tuple[str, dict[str, Any]]],
        private_secret: str,
        auth_contributions_fn: Any,
        storyteller_contributions_fn: Any,
    ) -> dict[str, Any]:
        manifest_id = f"manifest-character-orient-{inference_id}"
        upstream = assemble_character_upstream_contributions(
            fixture,
            rnd,
            manifest_id=manifest_id,
            character_id=character_id,
            role=role,
            hg_scene_id=fixture.hg_scene_id,
            hg_round_id=rnd.hg_round_id,
            turn_index=turn_index,
            director_decision=director_decision,
            correction_context=correction_context,
            memory_projections=memory_projections,
            private_secret=private_secret,
            auth_contributions_fn=auth_contributions_fn,
            storyteller_contributions_fn=storyteller_contributions_fn,
            include_correction=True,
        )
        contributions, envelope = build_character_orientation_context(
            upstream,
            manifest_id=manifest_id,
            character_id=character_id,
            inference_id=inference_id,
        )
        visibility = build_character_visibility_envelope(
            fixture,
            character_id=character_id,
            hg_round_id=rnd.hg_round_id,
        )
        return {
            "manifest_id": manifest_id,
            "inference_id": inference_id,
            "character_id": character_id,
            "hg_scene_id": fixture.hg_scene_id,
            "hg_round_id": rnd.hg_round_id,
            "turn_index": int(turn_index),
            "schema": CHARACTER_ORIENTATION_SCHEMA,
            "visibility_envelope": visibility,
            "host_allowed_information_classes": sorted(ALL_INFORMATION_CLASSES),
            "upstream_fingerprint": upstream.upstream_fingerprint,
            "upstream_completeness": upstream.completeness,
            "contributions": [
                {
                    "contribution_id": item.contribution_id,
                    "source_kind": item.source_kind,
                    "authority_class": item.authority_class,
                    "knowledge_ids": list(item.knowledge_ids),
                    "priority": item.priority,
                    "content": item.content,
                    "provenance": dict(item.provenance),
                }
                for item in contributions
            ],
            "orientation_envelope": envelope,
        }

    def finalize_orientation(
        self,
        fixture: LiveSession,
        rnd: RoundFixture,
        *,
        inference_id: str,
        character_id: str,
        turn_index: int,
        orientation_result: dict[str, Any] | str,
        upstream_fingerprint: str,
        director_decision: dict[str, Any] | None,
        correction_context: dict[str, Any] | None,
        storyteller_package_id: str | None = None,
        storyteller_valid: bool | None = None,
    ) -> dict[str, Any]:
        orientation, error = parse_character_orientation(orientation_result)
        if orientation is None:
            return {
                "accepted": False,
                "reason": error or "orientation_invalid",
                "knowledge_access_request": None,
                "reuse_key": None,
            }
        if orientation.character_id != character_id:
            return {
                "accepted": False,
                "reason": "character_mismatch",
                "knowledge_access_request": None,
                "reuse_key": None,
            }
        if orientation.hg_round_id and orientation.hg_round_id != rnd.hg_round_id:
            return {
                "accepted": False,
                "reason": "round_mismatch",
                "knowledge_access_request": None,
                "reuse_key": None,
            }
        normalized = CharacterOrientationAssessment(
            orientation_id=orientation.orientation_id,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(turn_index),
            character_id=character_id,
            information_gaps=orientation.information_gaps,
            entity_attention=orientation.entity_attention,
            relationship_focus=orientation.relationship_focus,
            temporal_focus=orientation.temporal_focus,
            breadth_preference=orientation.breadth_preference,
            requested_classes=orientation.requested_classes,
            situational_hypothesis=orientation.situational_hypothesis,
        )
        visibility = build_character_visibility_envelope(
            fixture,
            character_id=character_id,
            hg_round_id=rnd.hg_round_id,
        )
        request = orientation_to_knowledge_access_request(
            normalized,
            hg_scene_id=fixture.hg_scene_id,
            request_id=new_request_id("hg-character-kar"),
            visibility_envelope=visibility,
            host_allowed_information_classes=ALL_INFORMATION_CLASSES,
            correlation_inference_id=inference_id,
        )
        try:
            validate_knowledge_access_request(request)
        except ValueError as exc:
            return {
                "accepted": False,
                "reason": str(exc),
                "knowledge_access_request": None,
                "reuse_key": None,
            }
        kar_dict = _kar_to_dict(request)
        reuse_key = build_character_knowledge_reuse_key(
            character_id=character_id,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(turn_index),
            continuity_version=int(fixture.continuity_version),
            upstream_fingerprint=upstream_fingerprint,
            director_decision=director_decision,
            correction_context=correction_context,
            kar_fingerprint=_stable_hash(kar_dict),
            storyteller_package_id=storyteller_package_id,
            storyteller_valid=storyteller_valid,
            known_by_snapshot_id=visibility.get("known_by_snapshot_id"),
        )
        return {
            "accepted": True,
            "reason": "ok",
            "orientation": asdict(normalized),
            "knowledge_access_request": kar_dict,
            "reuse_key": reuse_key,
            "visibility_envelope": visibility,
        }


def _stable_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
