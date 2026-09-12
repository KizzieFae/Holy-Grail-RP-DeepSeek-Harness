import crypto from 'node:crypto';

import {
  executionEvidenceRoot,
  isExecutionEvidenceEnabled,
  NI_FORENSICS_CONTRACT,
} from './config.mjs';
import { buildAssembledRequest } from './assembled-request.mjs';
import { buildInferenceHealth } from './inference-health.mjs';
import { buildModelResponse } from './model-response.mjs';
import { participationDecisionPatch } from './participation-decision.mjs';
import { ExecutionEvidenceStore } from './store.mjs';

function correlationFromContext(context, manifest, contextRegistration, inferenceSessionId) {
  const correlation = {
    evidence_id: null,
    hg_session_id: context.hgSessionId ?? manifest?.hg_scene_id ?? null,
    hg_scene_id: context.hgSceneId ?? manifest?.hg_scene_id ?? null,
    hg_round_id: context.hgRoundId ?? manifest?.hg_round_id ?? null,
    role: context.role ?? manifest?.role ?? null,
    character_id: context.characterId ?? manifest?.character_id ?? null,
    inference_id: context.inferenceId ?? manifest?.inference_id ?? null,
    attempt_index: Number(context.attemptIndex ?? manifest?.attempt_index ?? 0),
    dsh_inference_session_id: inferenceSessionId ?? null,
    manifest_id: contextRegistration?.manifestId ?? manifest?.manifest_id ?? null,
    contribution_ids: [...(contextRegistration?.contributionIds ?? [])],
    domain_commit_id: context.domainCommitId ?? null,
    rp_history_entry_id: context.rpHistoryEntryId ?? null,
    continuity_turn_index: context.continuityTurnIndex ?? null,
    prior_attempt_id: context.priorAttemptId ?? null,
    evaluation_pass_id: context.evaluationPassId ?? null,
    participation_decision_id: context.participationDecisionId ?? null,
    character_turn_index: context.characterTurnIndex ?? null,
  };
  if (context.operationId) {
    correlation.operation_id = context.operationId;
  }
  if (context.inferenceKind) {
    correlation.inference_kind = context.inferenceKind;
  } else if (manifest?.inference_kind) {
    correlation.inference_kind = String(manifest.inference_kind);
  }
  if (context.characterizationMode === true) {
    correlation.characterization_mode = true;
  }
  if (context.calibrationMode === true) {
    correlation.calibration_mode = true;
  }
  if (context.parentInferenceId) {
    correlation.parent_inference_id = context.parentInferenceId;
  }
  if (context.effectiveConfigurationEpochId) {
    correlation.effective_configuration_epoch_id = context.effectiveConfigurationEpochId;
  }
  return correlation;
}

/**
 * Observational execution-evidence recorder (not continuity authority).
 */
export class ExecutionEvidenceRecorder {
  /**
   * @param {object} [options]
   * @param {boolean} [options.enabled]
   * @param {string} [options.root]
   * @param {string} [options.systemPersona]
   */
  constructor(options = {}) {
    this.enabled = options.enabled ?? isExecutionEvidenceEnabled();
    this.systemPersona = options.systemPersona ?? 'Holy Grail RP runtime.';
    this.store = new ExecutionEvidenceStore(options.root ?? executionEvidenceRoot());
  }

  isEnabled() {
    return this.enabled;
  }

  /**
   * Persist one inference attempt (request + response). Returns evidence_id or null.
   */
  recordInferenceAttempt({
    evidenceContext,
    manifest,
    contextRegistration,
    prompt,
    profile,
    trace,
    assistantText,
    inferenceSessionId,
    inferenceWallClockMs = null,
    turnBoundaryTiming = null,
    idleBoundaryDiagnostic = null,
  }) {
    if (!this.enabled) return null;
    const hgSessionId = evidenceContext?.hgSessionId;
    if (!hgSessionId) return null;

    const evidenceId = crypto.randomUUID();
    const correlation = correlationFromContext(
      evidenceContext,
      manifest,
      contextRegistration,
      inferenceSessionId,
    );
    correlation.evidence_id = evidenceId;

    const request = buildAssembledRequest({
      manifest,
      userInstruction: prompt,
      systemPersona: this.systemPersona,
      profile,
      manifestId: contextRegistration?.manifestId,
      contributionIds: contextRegistration?.contributionIds,
    });
    const response = buildModelResponse({ trace, assistantText });
    const attempt = {
      evidence_id: evidenceId,
      correlation,
      request,
      response,
      decision: evidenceContext?.initialDecision ?? null,
      associations: evidenceContext?.associations ?? {},
      inference_health: buildInferenceHealth({
        profile,
        requestProfile: request.inference_profile,
        trace,
        response,
        assistantText,
        evidenceContext,
        correlation,
        decision: evidenceContext?.initialDecision ?? null,
        turnBoundaryTiming,
        idleBoundaryDiagnostic,
        inferenceWallClockMs,
      }),
    };
    if (evidenceContext?.inferenceKind || evidenceContext?.niForensics) {
      attempt.evidence_contract = NI_FORENSICS_CONTRACT;
    }

    this.store.writeAttempt(attempt);
    return evidenceId;
  }

  /**
   * Record a participation-direct deterministic selection (#28).
   */
  recordPostCommitSemanticDisposition({
    hgSessionId,
    hgSceneId = null,
    hgRoundId = null,
    domainCommitId,
    continuityTurnIndex = null,
    postCommitSemanticInferenceId,
    batch = null,
    eligibilityOutcome = null,
    degradationMode = 'eligibility_skipped',
    orchestrationStatus = 'finalized',
    effectiveConfigurationEpochId = null,
  }) {
    if (!this.enabled || !hgSessionId || !domainCommitId) return null;
    const evidenceId = crypto.randomUUID();
    const attempt = {
      evidence_id: evidenceId,
      correlation: {
        evidence_id: evidenceId,
        hg_session_id: hgSessionId,
        hg_scene_id: hgSceneId ?? hgSessionId,
        hg_round_id: hgRoundId,
        role: 'post_commit_semantic_disposition',
        inference_kind: 'post_commit_semantic_disposition',
        record_class: 'deterministic_disposition',
        domain_commit_id: domainCommitId,
        continuity_turn_index: continuityTurnIndex,
        post_commit_semantic_inference_id: postCommitSemanticInferenceId ?? null,
        effective_configuration_epoch_id: effectiveConfigurationEpochId,
        attempt_index: 0,
      },
      request: null,
      response: null,
      decision: {
        post_commit_semantic_disposition: {
          schema: 'hg_post_commit_semantic_disposition_v1',
          inference_required: false,
          eligibility_outcome: eligibilityOutcome ?? batch?.degradation_mode ?? null,
          degradation_mode: degradationMode,
          semantic_producer_role: 'storyteller',
          orchestration_status: orchestrationStatus,
          post_commit_semantic_batch_id: batch?.batch_id ?? batch?.post_commit_semantic_batch_id ?? null,
          request_id: batch?.request_id ?? null,
          terminal: true,
        },
      },
      associations: {
        domain_commit_id: domainCommitId,
        post_commit_semantic_inference_id: postCommitSemanticInferenceId ?? null,
      },
    };
    this.store.writeAttempt(attempt);
    return evidenceId;
  }

  recordParticipationDecision({
    hgSessionId,
    hgSceneId,
    hgRoundId,
    characterTurnIndex,
    participation,
    eligibilitySnapshot,
    selectedCharacterId,
    characterInferenceId,
  }) {
    if (!this.enabled || !hgSessionId) return null;
    const evidenceId = crypto.randomUUID();
    const participationDecisionId =
      `participation-${hgRoundId}-${characterTurnIndex}`;
    const attempt = {
      evidence_id: evidenceId,
      correlation: {
        evidence_id: evidenceId,
        hg_session_id: hgSessionId,
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        role: 'participation',
        character_turn_index: characterTurnIndex,
        participation_decision_id: participationDecisionId,
        inference_id: null,
        attempt_index: 0,
      },
      request: null,
      response: null,
      decision: participationDecisionPatch({
        participation,
        eligibilitySnapshot,
      }).decision,
      associations: {
        selected_character_id: selectedCharacterId ?? null,
        character_inference_id: characterInferenceId ?? null,
        character_evidence_id: null,
      },
    };
    this.store.writeAttempt(attempt);
    return evidenceId;
  }

  /**
   * Bidirectional participation ↔ Character navigation links.
   */
  linkParticipationCharacter(
    hgSessionId,
    participationEvidenceId,
    {
      characterEvidenceId,
      characterInferenceId = null,
      selectedCharacterId = null,
    },
  ) {
    if (!this.enabled || !hgSessionId || !participationEvidenceId || !characterEvidenceId) {
      return;
    }
    this.store.patchAttempt(hgSessionId, participationEvidenceId, {
      associations: {
        character_evidence_id: characterEvidenceId,
        character_inference_id: characterInferenceId,
        selected_character_id: selectedCharacterId,
      },
    });
    this.store.patchAttempt(hgSessionId, characterEvidenceId, {
      associations: {
        participation_evidence_id: participationEvidenceId,
      },
    });
  }

  /**
   * Record a Narrator-phase failure that occurred before a normal inference attempt
   * could be retained (e.g. context prepare throw, inference-boundary throw).
   */
  /**
   * Application/turn lifecycle milestone (#86). Observational only.
   */
  recordApplicationLifecycleMilestone({
    hgSessionId,
    hgRoundId = null,
    operationId = null,
    milestone,
    details = {},
  }) {
    if (!this.enabled || !hgSessionId || !milestone) return null;
    const evidenceId = crypto.randomUUID();
    const attempt = {
      evidence_id: evidenceId,
      correlation: {
        evidence_id: evidenceId,
        hg_session_id: hgSessionId,
        hg_scene_id: hgSessionId,
        hg_round_id: hgRoundId,
        role: 'application_lifecycle',
        operation_id: operationId,
        milestone,
        attempt_index: 0,
      },
      request: null,
      response: null,
      decision: {
        milestone,
        operation_id: operationId,
        hg_round_id: hgRoundId,
        ...details,
      },
      associations: {
        operation_id: operationId,
        hg_round_id: hgRoundId,
      },
    };
    this.store.writeAttempt(attempt);
    return evidenceId;
  }

  /**
   * Durable orchestration/non-LLM execution span (#158).
   */
  recordExecutionSpan({
    hgSessionId,
    spanId,
    parentSpanId = null,
    operationId = null,
    hgRoundId = null,
    phaseId,
    role = null,
    startedAt,
    endedAt,
    wallMs,
    evidenceIds = [],
    triggerInferenceId = null,
    orchestrationGraph = null,
  }) {
    if (!this.enabled || !hgSessionId || !spanId || !phaseId) return null;
    const evidenceId = spanId;
    const decision = {
      phase_id: phaseId,
      role,
      operation_id: operationId,
      hg_round_id: hgRoundId,
    };
    if (orchestrationGraph) {
      decision.orchestration_graph = orchestrationGraph;
    }
    const attempt = {
      evidence_id: evidenceId,
      correlation: {
        evidence_id: evidenceId,
        span_id: spanId,
        parent_span_id: parentSpanId,
        hg_session_id: hgSessionId,
        hg_scene_id: hgSessionId,
        hg_round_id: hgRoundId,
        role: 'execution_span',
        operation_id: operationId,
        phase_id: phaseId,
        attempt_index: 0,
      },
      request: null,
      response: null,
      execution: {
        started_at: startedAt,
        ended_at: endedAt,
        wall_ms: wallMs,
      },
      decision,
      associations: {
        operation_id: operationId,
        hg_round_id: hgRoundId,
        evidence_ids: [...evidenceIds],
        trigger_inference_id: triggerInferenceId,
      },
    };
    this.store.writeAttempt(attempt);
    return evidenceId;
  }

  patchOperationRoundAssociation(hgSessionId, operationId, hgRoundId) {
    if (!this.enabled || !hgSessionId || !operationId || !hgRoundId) return;
    this.store.patchOperationRoundAssociation(hgSessionId, operationId, hgRoundId);
  }

  recordNarratorPhaseFailure({
    hgSessionId,
    hgSceneId,
    hgRoundId,
    characterId,
    inferenceId,
    attemptIndex = 0,
    domainCommitId = null,
    continuityTurnIndex = null,
    manifestId = null,
    failureClass,
    boundary,
    stage,
    patch,
  }) {
    if (!this.enabled || !hgSessionId) return null;
    const evidenceId = crypto.randomUUID();
    const attempt = {
      evidence_id: evidenceId,
      correlation: {
        evidence_id: evidenceId,
        hg_session_id: hgSessionId,
        hg_scene_id: hgSceneId ?? hgSessionId,
        hg_round_id: hgRoundId ?? null,
        role: 'narrator',
        character_id: characterId ?? null,
        inference_id: inferenceId ?? null,
        attempt_index: Number(attemptIndex ?? 0),
        manifest_id: manifestId,
        domain_commit_id: domainCommitId,
        continuity_turn_index: continuityTurnIndex,
      },
      request: null,
      response: null,
      decision: {
        ...(patch?.decision ?? {}),
        forensic_attribution: {
          failure_class: failureClass,
          boundary,
          stage,
          pre_inference_record: true,
        },
      },
      associations: {
        ...(patch?.associations ?? {}),
      },
    };
    this.store.writeAttempt(attempt);
    return evidenceId;
  }

  /**
   * @param {string|null} evidenceId
   * @param {string} hgSessionId
   * @param {object} patch
   */
  patchDecision(evidenceId, hgSessionId, patch) {
    if (!this.enabled || !evidenceId || !hgSessionId) return;
    this.store.patchAttempt(hgSessionId, evidenceId, patch);
  }

  /**
   * Bidirectional NI association links (#45).
   */
  linkNiAssociation(hgSessionId, leftEvidenceId, rightEvidenceId, {
    leftKey,
    rightKey,
  }) {
    if (!this.enabled || !hgSessionId || !leftEvidenceId || !rightEvidenceId) return;
    this.store.patchAttempt(hgSessionId, leftEvidenceId, {
      associations: { [leftKey]: rightEvidenceId },
    });
    this.store.patchAttempt(hgSessionId, rightEvidenceId, {
      associations: { [rightKey]: leftEvidenceId },
    });
  }

  indexTagForensicScope(hgSessionId, tagId, forensicScope) {
    if (!this.enabled || !hgSessionId || !tagId || !forensicScope) return;
    this.store.indexTagForensicScope(hgSessionId, tagId, forensicScope);
  }

  readAttempt(hgSessionId, evidenceId) {
    return this.store.readAttempt(hgSessionId, evidenceId);
  }

  readIndex(hgSessionId) {
    return this.store.readIndex(hgSessionId);
  }

  rebuildSemanticNavigationIndexes(hgSessionId) {
    return this.store.rebuildSemanticNavigationIndexes(hgSessionId);
  }

  deleteSessionEvidence(hgSessionId) {
    this.store.deleteSession(hgSessionId);
  }
}

export function createExecutionEvidenceRecorder(options = {}) {
  return new ExecutionEvidenceRecorder(options);
}
