import crypto from 'node:crypto';

import {
  executionEvidenceRoot,
  isExecutionEvidenceEnabled,
  NI_FORENSICS_CONTRACT,
} from './config.mjs';
import { buildAssembledRequest } from './assembled-request.mjs';
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
  if (context.inferenceKind) {
    correlation.inference_kind = context.inferenceKind;
  }
  if (context.parentInferenceId) {
    correlation.parent_inference_id = context.parentInferenceId;
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

    const attempt = {
      evidence_id: evidenceId,
      correlation,
      request: buildAssembledRequest({
        manifest,
        userInstruction: prompt,
        systemPersona: this.systemPersona,
        profile,
        manifestId: contextRegistration?.manifestId,
        contributionIds: contextRegistration?.contributionIds,
      }),
      response: buildModelResponse({ trace, assistantText }),
      decision: evidenceContext?.initialDecision ?? null,
      associations: evidenceContext?.associations ?? {},
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
