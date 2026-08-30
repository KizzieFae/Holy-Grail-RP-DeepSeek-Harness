"""Production localhost HTTP transport for the Holy Grail Domain API."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from .contract import (
    CommitRequest,
    ContextPrepareRequest,
    DirectorContextPrepareRequest,
    DirectorDecisionValidationRequest,
    DirectorSemanticQaContextPrepareRequest,
    EligibleActorsRequest,
    OpeningContextPrepareRequest,
    OpeningPersistRequest,
    NarratorContextPrepareRequest,
    NarratorEnvironmentCognitionFinalizeRequest,
    NarratorEnvironmentCognitionPrepareRequest,
    NarratorPresentationValidationRequest,
    NarratorSemanticQaContextPrepareRequest,
    ParticipationDecisionRequest,
    RoundStartRequest,
    SessionCreateRequest,
    SessionOpenRequest,
    UserTurnRecordRequest,
    PlayerSkipRecordRequest,
    UserProfileSetRequest,
    PresentationRecordRequest,
    SemanticEvaluationContextPrepareRequest,
    ValidationRequest,
)
from .kernel import DomainKernel
from .session_repository import PersistenceError


def _to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, tuple):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(v) for v in obj]
    return obj


class DomainApiHandler(BaseHTTPRequestHandler):
    kernel: DomainKernel

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(_to_jsonable(payload), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            data = self._read_json()
            if path == "/v1/sessions/create":
                req = SessionCreateRequest(
                    cast=tuple(data["cast"]) if data.get("cast") else None,
                    characters=tuple(data["characters"]) if data.get("characters") else None,
                    scene_template_id=data.get("scene_template_id"),
                    role_assignments=dict(data.get("role_assignments") or {}),
                    opening=dict(data.get("opening") or {}) if data.get("opening") else None,
                    location=str(data.get("location", "Workshop")),
                    hg_session_id=data.get("hg_session_id"),
                    memory_scope_id=data.get("memory_scope_id"),
                    player_character_file_id=data.get("player_character_file_id"),
                    user_persona_id=data.get("user_persona_id"),
                )
                self._send_json(
                    201,
                    self.kernel.create_session(
                        cast=list(req.cast) if req.cast else None,
                        characters=list(req.characters) if req.characters else None,
                        scene_template_id=req.scene_template_id,
                        role_assignments=req.role_assignments,
                        opening=req.opening,
                        location=req.location,
                        hg_session_id=req.hg_session_id,
                        memory_scope_id=req.memory_scope_id,
                        player_character_file_id=req.player_character_file_id,
                        user_persona_id=req.user_persona_id,
                    ),
                )
                return
            if path == "/v1/sessions/open":
                req = SessionOpenRequest(hg_session_id=str(data["hg_session_id"]))
                self._send_json(200, self.kernel.open_session(req.hg_session_id))
                return
            if path == "/v1/rounds/start":
                req = RoundStartRequest(hg_scene_id=str(data["hg_scene_id"]))
                self._send_json(200, self.kernel.start_round(req))
                return
            if path == "/v1/rounds/eligible-actors":
                req = EligibleActorsRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                )
                self._send_json(200, self.kernel.eligible_actors(req))
                return
            if path == "/v1/rounds/participation-decision":
                req = ParticipationDecisionRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    eligibility_snapshot_id=str(data["eligibility_snapshot_id"]),
                    forced_designation=data.get("forced_designation"),
                )
                self._send_json(200, self.kernel.participation_decision(req))
                return
            if path == "/v1/director/context/prepare":
                req = DirectorContextPrepareRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    inference_id=str(data["inference_id"]),
                    turn_index=int(data.get("turn_index", 0)),
                    attempt_index=int(data.get("attempt_index", 0)),
                    actors_used_this_round=tuple(data.get("actors_used_this_round") or ()),
                    correction_context=(
                        dict(data["correction_context"])
                        if isinstance(data.get("correction_context"), dict)
                        else None
                    ),
                )
                self._send_json(200, self.kernel.prepare_director_context(req))
                return
            if path == "/v1/director/semantic-qa/context/prepare":
                req = DirectorSemanticQaContextPrepareRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    inference_id=str(data["inference_id"]),
                    turn_index=int(data.get("turn_index", 0)),
                    evaluation_pass_id=str(data["evaluation_pass_id"]),
                    candidate_decision=dict(data.get("candidate_decision") or {}),
                    actors_used_this_round=tuple(data.get("actors_used_this_round") or ()),
                    raw_model_output=data.get("raw_model_output"),
                )
                self._send_json(200, self.kernel.prepare_director_semantic_qa_context(req))
                return
            if path == "/v1/director/decisions/validate":
                req = DirectorDecisionValidationRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    inference_id=str(data["inference_id"]),
                    turn_index=int(data.get("turn_index", 0)),
                    attempt_index=int(data.get("attempt_index", 0)),
                    proposed_decision=dict(data.get("proposed_decision") or {}),
                    raw_model_output=data.get("raw_model_output"),
                    eligibility_snapshot_id=data.get("eligibility_snapshot_id"),
                    director_constraint_actor=data.get("director_constraint_actor"),
                    continuation_c2_skip=bool(data.get("continuation_c2_skip", False)),
                )
                self._send_json(200, self.kernel.validate_director_decision(req))
                return
            if path == "/v1/context/prepare":
                req = ContextPrepareRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    inference_id=str(data["inference_id"]),
                    character_id=str(data["character_id"]),
                    role=str(data.get("role", "guest")),
                    turn_index=int(data.get("turn_index", 0)),
                    attempt_index=int(data.get("attempt_index", 0)),
                    correction_context=(
                        dict(data["correction_context"])
                        if isinstance(data.get("correction_context"), dict)
                        else None
                    ),
                    director_decision=(
                        dict(data["director_decision"])
                        if isinstance(data.get("director_decision"), dict)
                        else None
                    ),
                    librarian_bundle=(
                        dict(data["librarian_bundle"])
                        if isinstance(data.get("librarian_bundle"), dict)
                        else None
                    ),
                    librarian_knowledge_audit=(
                        dict(data["librarian_knowledge_audit"])
                        if isinstance(data.get("librarian_knowledge_audit"), dict)
                        else None
                    ),
                    plot_cognition_projection_batch_id=data.get("plot_cognition_projection_batch_id"),
                    plot_cognition_projection_semantic_results=(
                        list(data["plot_cognition_projection_semantic_results"])
                        if isinstance(data.get("plot_cognition_projection_semantic_results"), list)
                        else None
                    ),
                    plot_cognition_finalized_projection=(
                        dict(data["plot_cognition_finalized_projection"])
                        if isinstance(data.get("plot_cognition_finalized_projection"), dict)
                        else None
                    ),
                )
                self._send_json(200, self.kernel.prepare_context(req))
                return
            if path == "/v1/character/orientation/prepare":
                body = dict(data)
                self._send_json(
                    200,
                    self.kernel.prepare_character_orientation_context(
                        hg_scene_id=str(body["hg_scene_id"]),
                        hg_round_id=str(body["hg_round_id"]),
                        inference_id=str(body["inference_id"]),
                        character_id=str(body["character_id"]),
                        role=str(body.get("role", "guest")),
                        turn_index=int(body.get("turn_index", 0)),
                        director_decision=(
                            dict(body["director_decision"])
                            if isinstance(body.get("director_decision"), dict)
                            else None
                        ),
                        correction_context=(
                            dict(body["correction_context"])
                            if isinstance(body.get("correction_context"), dict)
                            else None
                        ),
                    ),
                )
                return
            if path == "/v1/character/orientation/finalize":
                body = dict(data)
                self._send_json(
                    200,
                    self.kernel.finalize_character_orientation(
                        hg_scene_id=str(body["hg_scene_id"]),
                        hg_round_id=str(body["hg_round_id"]),
                        inference_id=str(body["inference_id"]),
                        character_id=str(body["character_id"]),
                        turn_index=int(body.get("turn_index", 0)),
                        orientation_result=body.get("orientation_result") or {},
                        upstream_fingerprint=str(body.get("upstream_fingerprint") or ""),
                        director_decision=(
                            dict(body["director_decision"])
                            if isinstance(body.get("director_decision"), dict)
                            else None
                        ),
                        correction_context=(
                            dict(body["correction_context"])
                            if isinstance(body.get("correction_context"), dict)
                            else None
                        ),
                        storyteller_package_id=body.get("storyteller_package_id"),
                        storyteller_valid=body.get("storyteller_valid"),
                    ),
                )
                return
            if path == "/v1/context/prepare-semantic-evaluation":
                req = SemanticEvaluationContextPrepareRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    inference_id=str(data["inference_id"]),
                    character_id=str(data["character_id"]),
                    role=str(data.get("role", "guest")),
                    turn_index=int(data.get("turn_index", 0)),
                    evaluation_pass_id=str(data["evaluation_pass_id"]),
                    candidate_move=dict(data.get("candidate_move") or {}),
                    raw_model_output=data.get("raw_model_output"),
                )
                self._send_json(200, self.kernel.prepare_semantic_evaluation_context(req))
                return
            if path == "/v1/librarian/mediation/prepare":
                body = dict(data)
                self._send_json(
                    200,
                    self.kernel.prepare_librarian_mediation_context(
                        hg_scene_id=str(body["hg_scene_id"]),
                        inference_id=str(body["inference_id"]),
                        knowledge_access_request=dict(body.get("knowledge_access_request") or body),
                    ),
                )
                return
            if path == "/v1/librarian/mediation/finalize":
                body = dict(data)
                self._send_json(
                    200,
                    self.kernel.finalize_librarian_mediation(
                        hg_scene_id=str(body["hg_scene_id"]),
                        inference_id=str(body["inference_id"]),
                        knowledge_access_request=dict(body.get("knowledge_access_request") or body),
                        mediation_result=(
                            dict(body["mediation_result"])
                            if isinstance(body.get("mediation_result"), dict)
                            else None
                        ),
                        allow_deterministic_fallback=body.get("allow_deterministic_fallback"),
                    ),
                )
                return
            if path == "/v1/librarian/proposals/prepare":
                body = dict(data)
                self._send_json(
                    200,
                    self.kernel.prepare_librarian_proposal_context(
                        hg_scene_id=str(body["hg_scene_id"]),
                        inference_id=str(body["inference_id"]),
                        proposal_context_request=dict(body.get("proposal_context_request") or body),
                    ),
                )
                return
            if path == "/v1/librarian/proposals/finalize":
                body = dict(data)
                self._send_json(
                    200,
                    self.kernel.finalize_librarian_proposals(
                        hg_scene_id=str(body["hg_scene_id"]),
                        inference_id=str(body["inference_id"]),
                        proposal_context_request=dict(body.get("proposal_context_request") or body),
                        proposal_result=(
                            dict(body["proposal_result"])
                            if isinstance(body.get("proposal_result"), dict)
                            else None
                        ),
                        evidence_catalog=body.get("evidence_catalog"),
                        proposal_generation_failure=body.get("proposal_generation_failure"),
                    ),
                )
                return
            if path == "/v1/storyteller/orientation/prepare":
                body = dict(data)
                self._send_json(
                    200,
                    self.kernel.prepare_storyteller_orientation_context(
                        hg_scene_id=str(body["hg_scene_id"]),
                        hg_round_id=str(body["hg_round_id"]),
                        inference_id=str(body["inference_id"]),
                    ),
                )
                return
            if path == "/v1/storyteller/orientation/finalize":
                body = dict(data)
                self._send_json(
                    200,
                    self.kernel.finalize_storyteller_orientation(
                        hg_scene_id=str(body["hg_scene_id"]),
                        hg_round_id=str(body["hg_round_id"]),
                        inference_id=str(body["inference_id"]),
                        orientation_result=dict(body.get("orientation_result") or {}),
                    ),
                )
                return
            if path == "/v1/storyteller/assessment/prepare":
                body = dict(data)
                self._send_json(
                    200,
                    self.kernel.prepare_storyteller_assessment_context(
                        hg_scene_id=str(body["hg_scene_id"]),
                        inference_id=str(body["inference_id"]),
                        orientation=dict(body.get("orientation") or {}),
                        bundle=dict(body.get("bundle") or {}),
                    ),
                )
                return
            if path == "/v1/storyteller/assessment/finalize":
                body = dict(data)
                self._send_json(
                    200,
                    self.kernel.finalize_storyteller_assessment(
                        hg_scene_id=str(body["hg_scene_id"]),
                        hg_round_id=str(body["hg_round_id"]),
                        inference_id=str(body["inference_id"]),
                        orientation=dict(body.get("orientation") or {}),
                        bundle=dict(body.get("bundle") or {}),
                        assessment_result=dict(body.get("assessment_result") or {}),
                        orientation_inference_id=str(body.get("orientation_inference_id") or body["inference_id"]),
                        assessment_inference_id=str(body.get("assessment_inference_id") or body["inference_id"]),
                        follow_up_request_ids=list(body.get("follow_up_request_ids") or ()),
                    ),
                )
                return
            if path == "/v1/storyteller/round/bind":
                body = dict(data)
                self._send_json(
                    200,
                    self.kernel.bind_storyteller_advisory_package(
                        hg_scene_id=str(body["hg_scene_id"]),
                        hg_round_id=str(body["hg_round_id"]),
                        package=dict(body.get("package") or {}),
                        audit=dict(body.get("audit")) if body.get("audit") else None,
                    ),
                )
                return
            if path == "/v1/moves/validate":
                req = ValidationRequest(
                    inference_id=str(data["inference_id"]),
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    character_id=str(data["character_id"]),
                    role=str(data.get("role", "guest")),
                    turn_index=int(data.get("turn_index", 0)),
                    attempt_index=int(data.get("attempt_index", 0)),
                    proposed_move=dict(data.get("proposed_move") or {}),
                    raw_model_output=data.get("raw_model_output"),
                )
                self._send_json(200, self.kernel.validate_move(req))
                return
            if path == "/v1/moves/commit":
                req = CommitRequest(
                    inference_id=str(data["inference_id"]),
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    character_id=str(data["character_id"]),
                    validated_move=dict(data["validated_move"]),
                    director_decision=dict(data["director_decision"]),
                    expected_turn_index=int(data["expected_turn_index"]),
                )
                self._send_json(200, self.kernel.commit_move(req))
                return
            if path == "/v1/plot-cognition/projection/prepare":
                self._send_json(200, self.kernel.prepare_plot_cognition_projection(data))
                return
            if path == "/v1/plot-cognition/projection/register-semantic-result":
                self._send_json(
                    200,
                    self.kernel.register_plot_cognition_projection_semantic_result(data),
                )
                return
            if path == "/v1/plot-cognition/projection/regeneration/prepare":
                self._send_json(
                    200,
                    self.kernel.prepare_plot_cognition_projection_regeneration(data),
                )
                return
            if path == "/v1/plot-cognition/projection/regeneration/finalize":
                self._send_json(
                    200,
                    self.kernel.finalize_plot_cognition_projection_regeneration(data),
                )
                return
            if path == "/v1/plot-cognition/projection/finalize":
                self._send_json(200, self.kernel.finalize_plot_cognition_projection(data))
                return
            if path == "/v1/plot-cognition/freshness/assess":
                self._send_json(
                    200,
                    self.kernel.assess_plot_cognition_freshness(str(data["hg_scene_id"])),
                )
                return
            if path == "/v1/plot-cognition/pending-work/plan":
                self._send_json(
                    200,
                    self.kernel.plan_post_commit_plot_cognition_work(str(data["hg_scene_id"])),
                )
                return
            if path == "/v1/plot-cognition/reconciliation/finalize":
                self._send_json(200, self.kernel.finalize_plot_cognition_reconciliation(data))
                return
            if path == "/v1/plot-cognition/authority-advance/finalize":
                self._send_json(200, self.kernel.finalize_plot_cognition_authority_advance(data))
                return
            if path == "/v1/plot-cognition/pending-work/clear":
                self._send_json(
                    200,
                    self.kernel.clear_plot_cognition_pending_work(str(data["hg_scene_id"])),
                )
                return
            if path == "/v1/plot-cognition/init/prepare":
                self._send_json(200, self.kernel.prepare_plot_cognition_init(data))
                return
            if path == "/v1/plot-cognition/init/finalize":
                self._send_json(200, self.kernel.finalize_plot_cognition_init(data))
                return
            if path == "/v1/plot-cognition/update/prepare":
                self._send_json(200, self.kernel.prepare_plot_cognition_update(data))
                return
            if path == "/v1/plot-cognition/update/finalize":
                self._send_json(200, self.kernel.finalize_plot_cognition_update(data))
                return
            if path == "/v1/plot-cognition/replan/prepare":
                self._send_json(200, self.kernel.prepare_plot_cognition_replan(data))
                return
            if path == "/v1/plot-cognition/replan/finalize":
                self._send_json(200, self.kernel.finalize_plot_cognition_replan(data))
                return
            if path == "/v1/plot-cognition/advisory-generation/prepare":
                self._send_json(200, self.kernel.prepare_character_advisory_generation(data))
                return
            if path == "/v1/plot-cognition/advisory-generation/finalize":
                self._send_json(200, self.kernel.finalize_character_advisory_generation(data))
                return
            if path == "/v1/narrator/context/prepare":
                req = NarratorContextPrepareRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    inference_id=str(data["inference_id"]),
                    character_id=str(data["character_id"]),
                    domain_commit_id=str(data["domain_commit_id"]),
                    continuity_turn_index=int(data["continuity_turn_index"]),
                    attempt_index=int(data.get("attempt_index", 0)),
                    correction_context=(
                        dict(data["correction_context"])
                        if isinstance(data.get("correction_context"), dict)
                        else None
                    ),
                    environment_cognition_audit=(
                        dict(data["environment_cognition_audit"])
                        if isinstance(data.get("environment_cognition_audit"), dict)
                        else None
                    ),
                )
                self._send_json(200, self.kernel.prepare_narrator_context(req))
                return
            if path == "/v1/narrator/environment/cognition/prepare":
                req = NarratorEnvironmentCognitionPrepareRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    inference_id=str(data["inference_id"]),
                    character_id=str(data["character_id"]),
                    domain_commit_id=str(data["domain_commit_id"]),
                    continuity_turn_index=int(data["continuity_turn_index"]),
                )
                result = self.kernel.prepare_narrator_environment_cognition_context(req)
                self._send_json(200, _to_jsonable(result))
                return
            if path == "/v1/narrator/environment/cognition/finalize":
                req = NarratorEnvironmentCognitionFinalizeRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    inference_id=str(data["inference_id"]),
                    character_id=str(data["character_id"]),
                    domain_commit_id=str(data["domain_commit_id"]),
                    continuity_turn_index=int(data["continuity_turn_index"]),
                    cognition_result=dict(data.get("cognition_result") or {}),
                    librarian_outcomes=(
                        list(data.get("librarian_outcomes") or [])
                        if isinstance(data.get("librarian_outcomes"), list)
                        else None
                    ),
                    cognition_id=(
                        str(data["cognition_id"]) if data.get("cognition_id") else None
                    ),
                )
                self._send_json(
                    200,
                    self.kernel.finalize_narrator_environment_cognition_result(req),
                )
                return
            if path == "/v1/narrator/environment/knowledge-requests/build":
                req = NarratorEnvironmentCognitionPrepareRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    inference_id=str(data["inference_id"]),
                    character_id=str(data["character_id"]),
                    domain_commit_id=str(data["domain_commit_id"]),
                    continuity_turn_index=int(data["continuity_turn_index"]),
                )
                n1_raw = dict(data.get("n1_result") or {})
                self._send_json(
                    200,
                    {
                        "knowledge_access_requests": self.kernel.build_narrator_environment_knowledge_requests(
                            req,
                            n1_raw=n1_raw,
                        )
                    },
                )
                return
            if path == "/v1/narrator/semantic-qa/context/prepare":
                req = NarratorSemanticQaContextPrepareRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    inference_id=str(data["inference_id"]),
                    character_id=str(data["character_id"]),
                    domain_commit_id=str(data["domain_commit_id"]),
                    continuity_turn_index=int(data["continuity_turn_index"]),
                    evaluation_pass_id=str(data["evaluation_pass_id"]),
                    candidate_presentation=str(data.get("candidate_presentation") or ""),
                    raw_model_output=data.get("raw_model_output"),
                )
                self._send_json(200, self.kernel.prepare_narrator_semantic_qa_context(req))
                return
            if path == "/v1/narrator/presentation/validate":
                req = NarratorPresentationValidationRequest(
                    hg_scene_id=str(data["hg_scene_id"]),
                    domain_commit_id=str(data["domain_commit_id"]),
                    presentation_text=str(data.get("presentation_text") or ""),
                )
                self._send_json(200, self.kernel.validate_narrator_presentation(req))
                return
            if path == "/v1/sessions/history/user-turn":
                req = UserTurnRecordRequest(
                    hg_session_id=str(data["hg_session_id"]),
                    content=str(data["content"]),
                    speaker=str(data.get("speaker", "Player")),
                    forced_designation=data.get("forced_designation"),
                    hg_round_id=data.get("hg_round_id"),
                )
                self._send_json(201, self.kernel.record_user_turn(req))
                return
            if path == "/v1/sessions/history/player-skip":
                req = PlayerSkipRecordRequest(
                    hg_session_id=str(data["hg_session_id"]),
                    speaker=str(data.get("speaker", "Player")),
                )
                self._send_json(201, self.kernel.record_player_skip(req))
                return
            if path == "/v1/sessions/user-profile":
                req = UserProfileSetRequest(
                    hg_session_id=str(data["hg_session_id"]),
                    profile_key=str(data["profile_key"]),
                    content=str(data["content"]),
                    user_persona_id=str(data.get("user_persona_id", "Player")),
                )
                self._send_json(200, self.kernel.set_user_profile_fact(req))
                return
            if path == "/v1/sessions/history/presentation":
                req = PresentationRecordRequest(
                    hg_session_id=str(data["hg_session_id"]),
                    domain_commit_id=str(data["domain_commit_id"]),
                    hg_round_id=str(data["hg_round_id"]),
                    character_id=str(data["character_id"]),
                    presentation_text=data.get("presentation_text"),
                    presentation_failed=bool(data.get("presentation_failed", False)),
                    inference_outcome=data.get("inference_outcome"),
                )
                self._send_json(201, self.kernel.record_presentation(req))
                return
            if path == "/v1/opening/context/prepare":
                req = OpeningContextPrepareRequest(
                    hg_session_id=str(data["hg_session_id"]),
                    inference_id=str(data["inference_id"]),
                )
                self._send_json(200, self.kernel.prepare_opening_context(req))
                return
            if path == "/v1/sessions/opening/persist":
                req = OpeningPersistRequest(
                    hg_session_id=str(data["hg_session_id"]),
                    inference_id=str(data["inference_id"]),
                    presentation_text=str(data.get("presentation_text", "")),
                    presentation_failed=bool(data.get("presentation_failed", False)),
                    manifest_id=data.get("manifest_id"),
                )
                self._send_json(201, self.kernel.persist_opening_presentation(req))
                return
            self._send_json(404, {"error": "not found"})
        except PersistenceError as exc:
            self._send_json(503, {"error": str(exc), "error_kind": "persistence_failure"})
        except (KeyError, TypeError, ValueError, FileNotFoundError) as exc:
            self._send_json(400, {"error": str(exc)})

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            healthy = getattr(self.kernel.store, "health_ok", lambda: True)()
            self._send_json(
                200 if healthy else 503,
                {
                    "status": "ok" if healthy else "degraded",
                    "service": "holy-grail-domain-host",
                },
            )
            return
        if path == "/v1/catalog/memory-scopes":
            self._send_json(200, {"memory_scopes": self.kernel.list_memory_scopes()})
            return
        if path == "/v1/catalog/characters":
            self._send_json(200, {"characters": self.kernel.list_characters()})
            return
        if path == "/v1/catalog/scene-templates":
            self._send_json(200, {"scene_templates": self.kernel.list_scene_templates()})
            return
        if path.startswith("/v1/catalog/scene-templates/") and path.endswith("/openers"):
            template_id = path.removeprefix("/v1/catalog/scene-templates/").removesuffix(
                "/openers"
            )
            self._send_json(
                200,
                {"template_id": template_id, "openers": self.kernel.list_template_openers(template_id)},
            )
            return
        if path.startswith("/v1/sessions/") and path.endswith("/state"):
            hg_session_id = path.removeprefix("/v1/sessions/").removesuffix("/state")
            try:
                self._send_json(200, self.kernel.scene_snapshot(hg_session_id))
            except KeyError:
                self._send_json(404, {"error": "unknown session"})
            return
        if path.startswith("/v1/sessions/") and path.endswith("/history"):
            hg_session_id = path.removeprefix("/v1/sessions/").removesuffix("/history")
            try:
                self._send_json(200, self.kernel.get_session_history(hg_session_id))
            except KeyError:
                self._send_json(404, {"error": "unknown session"})
            return
        if path == "/v1/storyteller/round/state":
            query = parse_qs(urlparse(self.path).query)
            hg_scene_id = (query.get("hg_scene_id") or [""])[0]
            hg_round_id = (query.get("hg_round_id") or [""])[0]
            try:
                self._send_json(
                    200,
                    self.kernel.get_storyteller_round_state(
                        hg_scene_id=str(hg_scene_id),
                        hg_round_id=str(hg_round_id),
                    ),
                )
            except KeyError:
                self._send_json(404, {"error": "unknown round"})
            return
        self._send_json(404, {"error": "not found"})


def serve(
    kernel: DomainKernel,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> ThreadingHTTPServer:
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("Domain API host must be localhost-only")
    handler = type(
        "BoundDomainApiHandler",
        (DomainApiHandler,),
        {"kernel": kernel},
    )
    server = ThreadingHTTPServer((host, port), handler)
    return server
