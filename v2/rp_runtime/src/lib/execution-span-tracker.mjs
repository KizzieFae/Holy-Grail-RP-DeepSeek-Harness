import crypto from 'node:crypto';
import { performance } from 'node:perf_hooks';

/**
 * Lightweight execution-span tracker for observational evidence (#158).
 * Records non-LLM/orchestration intervals in the existing execution-evidence store.
 */
export class ExecutionSpanTracker {
  /**
   * @param {import('./execution-evidence/recorder.mjs').ExecutionEvidenceRecorder|null} recorder
   * @param {object} scope
   */
  constructor(recorder, scope = {}) {
    this.recorder = recorder?.isEnabled?.() ? recorder : null;
    this.hgSessionId = scope.hgSessionId ?? null;
    this.operationId = scope.operationId ?? null;
    this.hgRoundId = scope.hgRoundId ?? null;
    this.parentSpanId = scope.parentSpanId ?? null;
    this.openSpans = new Map();
  }

  setHgRoundId(hgRoundId) {
    if (!hgRoundId) return;
    this.hgRoundId = hgRoundId;
    if (!this.recorder || !this.hgSessionId) return;
    this.recorder.patchOperationRoundAssociation(this.hgSessionId, this.operationId, hgRoundId);
  }

  /**
   * @param {string} phaseId
   * @param {object} [options]
   */
  beginSpan(phaseId, options = {}) {
    if (!this.recorder || !this.hgSessionId || !phaseId) return null;
    const spanId = crypto.randomUUID();
    const startedAt = new Date().toISOString();
    const startedMonotonic = performance.now();
    this.openSpans.set(spanId, {
      phaseId,
      role: options.role ?? null,
      startedAt,
      startedMonotonic,
      parentSpanId: options.parentSpanId ?? this.parentSpanId ?? null,
      evidenceIds: [...(options.evidenceIds ?? [])],
      triggerInferenceId: options.triggerInferenceId ?? null,
    });
    return spanId;
  }

  /**
   * @param {string|null} spanId
   * @param {object} [options]
   */
  endSpan(spanId, options = {}) {
    if (!spanId || !this.recorder || !this.hgSessionId) return null;
    const open = this.openSpans.get(spanId);
    if (!open) return null;
    this.openSpans.delete(spanId);
    const endedMonotonic = performance.now();
    const wallMs = Math.max(0, Math.round(endedMonotonic - open.startedMonotonic));
    const endedAt = new Date().toISOString();
    const evidenceIds = [...new Set([
      ...(open.evidenceIds ?? []),
      ...(options.evidenceIds ?? []),
    ])];
    return this.recorder.recordExecutionSpan({
      hgSessionId: this.hgSessionId,
      spanId,
      parentSpanId: open.parentSpanId,
      operationId: this.operationId,
      hgRoundId: this.hgRoundId,
      phaseId: open.phaseId,
      role: open.role,
      startedAt: open.startedAt,
      endedAt,
      wallMs,
      evidenceIds,
      triggerInferenceId: open.triggerInferenceId ?? options.triggerInferenceId ?? null,
    });
  }

  /**
   * @param {string} phaseId
   * @param {() => Promise<T>|T} fn
   * @param {object} [options]
   * @returns {Promise<T>}
   * @template T
   */
  async measure(phaseId, fn, options = {}) {
    const spanId = this.beginSpan(phaseId, options);
    try {
      const result = await fn();
      if (spanId) {
        this.endSpan(spanId, {
          evidenceIds: options.collectEvidenceIds?.(result) ?? options.evidenceIds,
        });
      }
      return result;
    } catch (err) {
      if (spanId) {
        this.endSpan(spanId, { evidenceIds: options.evidenceIds });
      }
      throw err;
    }
  }

  /**
   * LLM phase reference span — links evidence without duplicate wall_ms.
   */
  linkInferenceEvidence(phaseId, evidenceId, options = {}) {
    if (!evidenceId) return null;
    const spanId = this.beginSpan(phaseId, {
      ...options,
      evidenceIds: [evidenceId],
    });
    if (spanId) {
      return this.endSpan(spanId, { evidenceIds: [evidenceId] });
    }
    return null;
  }
}

/**
 * @param {import('./execution-evidence/recorder.mjs').ExecutionEvidenceRecorder|null} recorder
 * @param {object} scope
 */
export function createExecutionSpanTracker(recorder, scope = {}) {
  if (!recorder?.isEnabled?.() || !scope.hgSessionId) return null;
  return new ExecutionSpanTracker(recorder, scope);
}

const DOMAIN_SPAN_PHASES = {
  getSessionState: 'domain_get_session_state',
  recordUserTurn: 'domain_record_user_turn',
  recordPlayerSkip: 'domain_record_player_skip',
  getSessionHistory: 'domain_get_session_history',
  recordPresentation: 'domain_record_presentation',
  startRound: 'domain_start_round',
  getEligibleActors: 'domain_get_eligible_actors',
  getParticipationDecision: 'domain_get_participation_decision',
  prepareDirectorContext: 'domain_prepare_director_context',
  validateDirectorDecision: 'domain_validate_director_decision',
  prepareDirectorSemanticQaContext: 'domain_prepare_director_semantic_qa_context',
  prepareCharacterContext: 'domain_prepare_character_context',
  prepareCharacterOrientationContext: 'domain_prepare_character_orientation_context',
  finalizeCharacterOrientation: 'domain_finalize_character_orientation',
  prepareSemanticEvaluationContext: 'domain_prepare_semantic_evaluation_context',
  prepareLibrarianMediationContext: 'domain_prepare_librarian_mediation_context',
  finalizeLibrarianMediation: 'domain_finalize_librarian_mediation',
  prepareLibrarianProposalContext: 'domain_prepare_librarian_proposal_context',
  finalizeLibrarianProposals: 'domain_finalize_librarian_proposals',
  prepareStorytellerOrientationContext: 'domain_prepare_storyteller_orientation_context',
  finalizeStorytellerOrientation: 'domain_finalize_storyteller_orientation',
  prepareStorytellerAssessmentContext: 'domain_prepare_storyteller_assessment_context',
  finalizeStorytellerAssessment: 'domain_finalize_storyteller_assessment',
  bindStorytellerAdvisoryPackage: 'domain_bind_storyteller_advisory_package',
  validateMove: 'domain_validate_move',
  commitMove: 'domain_commit_move',
  prepareNarratorContext: 'domain_prepare_narrator_context',
  prepareNarratorEnvironmentCognitionContext: 'domain_prepare_narrator_environment_cognition_context',
  finalizeNarratorEnvironmentCognition: 'domain_finalize_narrator_environment_cognition',
  prepareNarratorSemanticQaContext: 'domain_prepare_narrator_semantic_qa_context',
  validateNarratorPresentation: 'domain_validate_narrator_presentation',
  preparePlayerDecompositionContext: 'domain_prepare_player_decomposition_context',
  preparePlayerVisibilityTriageContext: 'domain_prepare_player_visibility_triage_context',
  preparePlotCognitionInit: 'domain_prepare_plot_cognition_init',
  finalizePlotCognitionInit: 'domain_finalize_plot_cognition_init',
  preparePlotCognitionUpdate: 'domain_prepare_plot_cognition_update',
  finalizePlotCognitionUpdate: 'domain_finalize_plot_cognition_update',
};

/**
 * @param {object} client
 * @param {ExecutionSpanTracker|null} tracker
 */
export function wrapDomainClientWithSpans(client, tracker) {
  if (!tracker || !client) return client;
  const wrapped = { ...client, metrics: client.metrics };
  for (const [methodName, phaseId] of Object.entries(DOMAIN_SPAN_PHASES)) {
    const original = client[methodName];
    if (typeof original !== 'function') continue;
    wrapped[methodName] = (...args) => tracker.measure(phaseId, () => original(...args));
  }
  return wrapped;
}
