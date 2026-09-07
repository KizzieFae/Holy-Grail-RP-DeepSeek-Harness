"""Storyteller cognition orchestration (#32 S3a).

Host-side service coordinating orientation, Librarian read path, and informed assessment.
Does not wire advisory output into role manifests.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .knowledge_access_request_serialization import knowledge_access_request_to_dict
from .librarian_authoritative_input import authoritative_snapshot_id
from .librarian_contract import (
    ALL_INFORMATION_CLASSES,
    LibrarianKnowledgeBundle,
    QuestionOutcome,
    knowledge_access_request_from_dict,
    new_request_id,
    validate_knowledge_access_request,
)
from .librarian_service import LibrarianService
from .session_state import LiveSession, RoundFixture
from .storyteller_assessment_context import build_storyteller_assessment_context
from .storyteller_contract import (
    STORYTELLER_ASSESSMENT_SCHEMA,
    STORYTELLER_ORIENTATION_SCHEMA,
    StorytellerAdvisoryPackage,
    StorytellerAuditRecord,
    StorytellerBundleRefs,
    StorytellerDegradation,
    StorytellerOrientationAssessment,
    advisory_package_to_dict,
    build_storyteller_advisory_package,
    invalidate_storyteller_package,
    orientation_to_knowledge_access_request,
    parse_storyteller_assessment,
    parse_storyteller_orientation,
)
from .storyteller_orientation_context import build_storyteller_orientation_context


def _bundle_field(bundle: LibrarianKnowledgeBundle | dict[str, Any], name: str, default: Any = None) -> Any:
    if isinstance(bundle, dict):
        return bundle.get(name, default)
    return getattr(bundle, name, default)


def _bundle_degradation(bundle: LibrarianKnowledgeBundle | dict[str, Any]) -> tuple[str, str]:
    degradation = _bundle_field(bundle, "degradation", {})
    if isinstance(degradation, dict):
        return str(degradation.get("level") or "none"), str(degradation.get("mode") or "none")
    return degradation.level, degradation.mode


class StorytellerService:
    """Bounded Storyteller cognition — advisory only, optional to core RP loop."""

    def __init__(self, librarian_service: LibrarianService | None = None) -> None:
        self._librarian = librarian_service or LibrarianService()

    def prepare_orientation_context(
        self,
        fixture: LiveSession,
        rnd: RoundFixture,
        *,
        inference_id: str,
    ) -> dict[str, Any]:
        manifest_id, contributions, authority_refs, envelope = build_storyteller_orientation_context(
            fixture,
            rnd,
            inference_id=inference_id,
        )
        from .manifest_validation import validate_contribution_package

        validate_contribution_package("storyteller_orientation", contributions)
        return {
            "manifest_id": manifest_id,
            "inference_id": inference_id,
            "inference_kind": "storyteller_orientation",
            "hg_scene_id": fixture.hg_scene_id,
            "hg_round_id": rnd.hg_round_id,
            "turn_index": int(rnd.turn_index),
            "schema": STORYTELLER_ORIENTATION_SCHEMA,
            "visibility_envelope": envelope,
            "host_allowed_information_classes": sorted(ALL_INFORMATION_CLASSES),
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
            "authority_references": list(authority_refs),
        }

    def finalize_orientation(
        self,
        fixture: LiveSession,
        rnd: RoundFixture,
        *,
        inference_id: str,
        orientation_result: dict[str, Any] | str,
    ) -> dict[str, Any]:
        orientation, error = parse_storyteller_orientation(orientation_result)
        if orientation is None:
            return {
                "accepted": False,
                "reason": error or "orientation_invalid",
                "knowledge_access_request": None,
            }
        if orientation.hg_round_id and orientation.hg_round_id != rnd.hg_round_id:
            return {
                "accepted": False,
                "reason": "round_mismatch",
                "knowledge_access_request": None,
            }
        normalized = StorytellerOrientationAssessment(
            orientation_id=orientation.orientation_id,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            trigger=orientation.trigger,
            information_gaps=orientation.information_gaps,
            entity_attention=orientation.entity_attention,
            relationship_focus=orientation.relationship_focus,
            temporal_focus=orientation.temporal_focus,
            breadth_preference=orientation.breadth_preference,
            requested_classes=orientation.requested_classes,
            narrative_hypothesis=orientation.narrative_hypothesis,
            degradation=orientation.degradation,
        )
        _, _, _, envelope = build_storyteller_orientation_context(fixture, rnd, inference_id=inference_id)
        request = orientation_to_knowledge_access_request(
            normalized,
            hg_scene_id=fixture.hg_scene_id,
            request_id=new_request_id("hg-storyteller-kar"),
            visibility_envelope=envelope,
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
            }
        return {
            "accepted": True,
            "reason": "ok",
            "orientation": asdict(normalized),
            "knowledge_access_request": knowledge_access_request_to_dict(request),
        }

    def prepare_assessment_context(
        self,
        orientation: StorytellerOrientationAssessment,
        bundle: LibrarianKnowledgeBundle | dict[str, Any],
        *,
        inference_id: str,
    ) -> dict[str, Any]:
        manifest_id, contributions = build_storyteller_assessment_context(
            orientation,
            bundle,
            inference_id=inference_id,
        )
        from .manifest_validation import validate_contribution_package

        validate_contribution_package("storyteller_assessment", contributions)
        return {
            "manifest_id": manifest_id,
            "inference_id": inference_id,
            "inference_kind": "storyteller_assessment",
            "orientation_id": orientation.orientation_id,
            "bundle_id": _bundle_field(bundle, "bundle_id"),
            "schema": STORYTELLER_ASSESSMENT_SCHEMA,
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
        }

    def finalize_assessment(
        self,
        fixture: LiveSession,
        rnd: RoundFixture,
        *,
        orientation: StorytellerOrientationAssessment,
        bundle: LibrarianKnowledgeBundle | dict[str, Any],
        assessment_result: dict[str, Any] | str,
        orientation_inference_id: str,
        assessment_inference_id: str,
        follow_up_request_ids: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        parsed, error = parse_storyteller_assessment(assessment_result)
        if parsed is None:
            return {
                "accepted": False,
                "reason": error or "assessment_invalid",
                "package": None,
            }
        snapshot_id = authoritative_snapshot_id(
            fixture,
            knowledge_access_request_from_dict(
                {
                    "request_id": str(_bundle_field(bundle, "request_id")),
                    "consumer_role": "storyteller",
                    "audit_reason": "storyteller_finalize",
                    "hg_scene_id": fixture.hg_scene_id,
                    "hg_round_id": rnd.hg_round_id,
                    "turn_index": int(rnd.turn_index),
                    "pipeline_stage": "host_default",
                    "visibility_envelope": {
                        "viewer_role": "orchestration",
                        "authority_ceiling_enforced": "derived",
                    },
                    "information_need": {"focus_questions": ("finalize",)},
                }
            ),
        )
        level, mode = _bundle_degradation(bundle)
        degradation = StorytellerDegradation(
            level="partial" if level != "none" else "none",  # type: ignore[arg-type]
            mode="librarian_degraded" if level != "none" else "none",
            detail=mode,
        )
        audit = StorytellerAuditRecord(
            orientation_inference_id=orientation_inference_id,
            assessment_inference_id=assessment_inference_id,
            inference_ids=(orientation_inference_id, assessment_inference_id),
            librarian_request_ids=(str(_bundle_field(bundle, "request_id")), *follow_up_request_ids),
            librarian_bundle_ids=(str(_bundle_field(bundle, "bundle_id")),),
            host_validation={"accepted": True, "reason": "ok"},
        )
        package = build_storyteller_advisory_package(
            assessment=parsed,
            orientation=orientation,
            hg_scene_id=fixture.hg_scene_id,
            bundle_refs=StorytellerBundleRefs(
                primary_request_id=str(_bundle_field(bundle, "request_id")),
                primary_bundle_id=str(_bundle_field(bundle, "bundle_id")),
                follow_up_request_ids=follow_up_request_ids,
                bundle_validity=(
                    bundle.validity
                    if isinstance(bundle, LibrarianKnowledgeBundle)
                    else None
                ),
            ),
            authoritative_snapshot_id=snapshot_id,
            audit=audit,
            degradation=degradation,
        )
        return {
            "accepted": True,
            "reason": "ok",
            "package": advisory_package_to_dict(package),
        }

    def access_librarian_bundle(
        self,
        fixture: LiveSession,
        request_payload: dict[str, Any],
        *,
        inference_id: str,
        mediation_result: dict[str, Any] | None = None,
        allow_deterministic_fallback: bool = True,
    ) -> LibrarianKnowledgeBundle:
        request = knowledge_access_request_from_dict(
            {**request_payload, "hg_scene_id": fixture.hg_scene_id}
        )
        validate_knowledge_access_request(request)
        return self._librarian.access_knowledge(
            request,
            fixture,
            mediation_result=mediation_result,
            inference_id=inference_id,
            allow_deterministic_fallback=allow_deterministic_fallback,
        )

    def maybe_follow_up_request(
        self,
        fixture: LiveSession,
        rnd: RoundFixture,
        *,
        orientation: StorytellerOrientationAssessment,
        bundle: LibrarianKnowledgeBundle,
        primary_request_id: str,
        inference_id: str,
    ) -> dict[str, Any] | None:
        unanswered = [
            outcome.question
            for outcome in bundle.satisfaction.focus_questions
            if outcome.status in {"unanswered", "partial"}
        ]
        if not unanswered:
            return None
        gaps = tuple(unanswered[:3])
        follow_orientation = StorytellerOrientationAssessment(
            orientation_id=orientation.orientation_id,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            trigger="follow_up_gap",
            information_gaps=gaps,
            entity_attention=orientation.entity_attention,
            relationship_focus=orientation.relationship_focus,
            temporal_focus=orientation.temporal_focus,
            breadth_preference="focused",
        )
        _, _, _, envelope = build_storyteller_orientation_context(fixture, rnd, inference_id=inference_id)
        request = orientation_to_knowledge_access_request(
            follow_orientation,
            hg_scene_id=fixture.hg_scene_id,
            request_id=new_request_id("hg-storyteller-kar-followup"),
            visibility_envelope=envelope,
            host_allowed_information_classes=ALL_INFORMATION_CLASSES,
            correlation_inference_id=inference_id,
            parent_request_id=primary_request_id,
        )
        validate_knowledge_access_request(request)
        return knowledge_access_request_to_dict(request)

    @staticmethod
    def invalidate_package(package: StorytellerAdvisoryPackage, *, reason: str) -> dict[str, Any]:
        return advisory_package_to_dict(invalidate_storyteller_package(package, reason=reason))

    @staticmethod
    def unanswered_questions(bundle: LibrarianKnowledgeBundle) -> tuple[str, ...]:
        return tuple(
            outcome.question
            for outcome in bundle.satisfaction.focus_questions
            if outcome.status in {"unanswered", "partial"}
        )
