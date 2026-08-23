import { SessionId } from '@deepseek-ai/dsh-session';

import { agentOptionsFromProfile, mockInferenceProfile } from '../../lib/inference-profile.mjs';
import { characterDecisionPatch } from '../../lib/execution-evidence/phase-decision.mjs';
import { parseJsonObject } from '../../lib/inference-utils.mjs';
import { resolveRoundSession } from '../../lib/resolve-round-session.mjs';

const DEFAULT_CHARACTER_PROMPT = (
  'Respond with a single JSON object only (no markdown). '
  + 'Schema: {"move_schema_version":2,"beats":[{"type":"action","action":"..."}],'
  + '"motivation":{"goal":"...","tactic":"...","emotional_driver":"...","risk_level":"low"},'
  + '"semantic_evaluation":{"decision":"no_covered_change"}}'
);

/**
 * Standalone character inference + optional commit — phase execution, not round orchestration.
 */
export async function runCharacterInferenceSlice({
  ctx,
  trace,
  runEphemeralInference,
  recorder,
  api,
  options,
}) {
  const characterId = options.characterId ?? 'Alice';
  const role = options.role ?? 'guest';
  const inferenceId = options.inferenceId ?? `inf-char-${crypto.randomUUID()}`;

  let hgSessionId = options.hgSessionId;
  let hgSceneId = options.hgSceneId;
  let hgRoundId = options.hgRoundId;
  if (!hgSceneId) {
    const sessionInfo = await resolveRoundSession(api, {
      session: options.session ?? { mode: 'create', cast: ['Alice', 'Bob'] },
    });
    hgSessionId = sessionInfo.hgSessionId;
    hgSceneId = sessionInfo.hgSceneId;
  } else if (!hgSessionId) {
    hgSessionId = hgSceneId;
  }
  if (!hgRoundId) {
    const round = await api.startRound({ hg_scene_id: hgSceneId });
    hgRoundId = String(round.hg_round_id);
  }

  const beforeState = await api.getSceneState(hgSceneId);
  const expectedTurnIndex = Number(beforeState.turn_counter ?? 0);
  const sceneSessionId = SessionId(`hg-scene-${hgSceneId}`);
  const sceneAgent = ctx.agentLoop.create(
    sceneSessionId,
    agentOptionsFromProfile(mockInferenceProfile()),
  );
  const scope = { hgSessionId, hgSceneId, hgRoundId, sceneSessionId };

  const directorDecision = options.directorDecision ?? {
    next_actor: characterId,
    end_round: false,
    reason: 'character-only slice',
    environment_event: '',
    tension_shift: '',
  };

  let attemptIndex = 0;
  let committed = false;
  let continuityTurnIndex = null;
  let domainCommitId = null;
  let manifestId = '';
  let inferenceTrace = null;
  let providerFailure = null;
  const mockResponses = options.mockResponses ?? [];
  const modelProfile = options.modelProfile ?? options.model_profile ?? null;
  const maxAttempts = mockResponses.length > 0 ? mockResponses.length : 1;
  let priorEvidenceId = null;

  while (attemptIndex < maxAttempts && !committed) {
    const manifest = await api.prepareCharacterContext({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      inference_id: inferenceId,
      character_id: characterId,
      role,
      turn_index: expectedTurnIndex,
      attempt_index: attemptIndex,
    });
    manifestId = String(manifest.manifest_id);

    const inferenceRun = await runEphemeralInference({
      inferenceId: `${inferenceId}-${attemptIndex}`,
      prompt: options.prompt ?? DEFAULT_CHARACTER_PROMPT,
      manifest,
      mockResponses: mockResponses.length ? [mockResponses[attemptIndex]] : [],
      modelProfile,
      evidenceContext: {
        hgSessionId,
        hgSceneId,
        hgRoundId,
        role: 'character',
        characterId,
        inferenceId,
        attemptIndex,
        priorAttemptId: priorEvidenceId,
      },
    });
    inferenceTrace = inferenceRun.trace;

    if (inferenceRun.failed) {
      providerFailure = inferenceRun.failure;
      recorder?.patchDecision(
        inferenceRun.evidenceId,
        hgSessionId,
        characterDecisionPatch({ proposed: null, outcome: 'inference_failed' }),
      );
      priorEvidenceId = inferenceRun.evidenceId ?? priorEvidenceId;
      trace.emit(sceneAgent.session, 'hg/inference-failed', scope, {
        inference_id: inferenceId,
        role: 'character',
        character_id: characterId,
        attempt_index: attemptIndex,
        manifest_id: manifestId,
        provider: inferenceTrace?.provider ?? null,
        model: inferenceTrace?.model ?? null,
        failure: providerFailure,
        inference_trace: inferenceTrace,
      });
      break;
    }

    let proposed;
    let parseError = null;
    try {
      proposed = parseJsonObject(inferenceRun.raw);
    } catch (error) {
      parseError = String(error);
      proposed = { parse_error: parseError };
    }

    trace.emit(sceneAgent.session, 'hg/move-proposed', scope, {
      inference_id: inferenceId,
      role: 'character',
      character_id: characterId,
      attempt_index: attemptIndex,
      manifest_id: manifestId,
      proposed_move: proposed,
      raw_model_output: inferenceRun.raw,
    });

    const validation = await api.validateMove({
      inference_id: inferenceId,
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      character_id: characterId,
      role,
      turn_index: expectedTurnIndex,
      attempt_index: attemptIndex,
      proposed_move: proposed,
      raw_model_output: inferenceRun.raw,
    });

    if (!validation.accepted) {
      recorder?.patchDecision(
        inferenceRun.evidenceId,
        hgSessionId,
        characterDecisionPatch({
          proposed,
          parseError,
          validation,
          outcome: 'rejected',
        }),
      );
      priorEvidenceId = inferenceRun.evidenceId ?? priorEvidenceId;
      trace.emit(sceneAgent.session, 'hg/move-rejected', scope, {
        inference_id: inferenceId,
        role: 'character',
        character_id: characterId,
        attempt_index: attemptIndex,
        validation_class: String(validation.validation_class ?? 'unknown'),
        reason: String(validation.reason ?? ''),
        retryable: Boolean(validation.retryable),
      });
      attemptIndex += 1;
      continue;
    }

    const commit = await api.commitMove({
      inference_id: inferenceId,
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      character_id: characterId,
      validated_move: validation.normalized_move ?? proposed,
      director_decision: directorDecision,
      expected_turn_index: expectedTurnIndex,
    });

    if (!commit.committed) {
      recorder?.patchDecision(
        inferenceRun.evidenceId,
        hgSessionId,
        characterDecisionPatch({
          proposed,
          parseError,
          validation,
          outcome: 'commit_rejected',
          commit,
        }),
      );
      priorEvidenceId = inferenceRun.evidenceId ?? priorEvidenceId;
      trace.emit(sceneAgent.session, 'hg/move-rejected', scope, {
        inference_id: inferenceId,
        role: 'character',
        character_id: characterId,
        attempt_index: attemptIndex,
        validation_class: 'continuity_anchor',
        reason: String(commit.reason ?? 'commit rejected'),
        retryable: false,
      });
      attemptIndex += 1;
      continue;
    }

    committed = true;
    continuityTurnIndex = Number(commit.continuity_turn_index);
    domainCommitId = String(commit.domain_commit_id ?? '');
    recorder?.patchDecision(
      inferenceRun.evidenceId,
      hgSessionId,
      characterDecisionPatch({
        proposed,
        parseError,
        validation,
        outcome: 'accepted',
        commit,
      }),
    );
    priorEvidenceId = inferenceRun.evidenceId ?? priorEvidenceId;
    trace.emit(sceneAgent.session, 'hg/move-committed', scope, {
      inference_id: inferenceId,
      role: 'character',
      character_id: characterId,
      attempt_index: attemptIndex,
      manifest_id: manifestId,
      continuity_turn_index: continuityTurnIndex,
      domain_commit_id: domainCommitId,
    });
  }

  return {
    committed,
    hg_session_id: hgSessionId,
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    inference_id: inferenceId,
    character_id: characterId,
    dsh_scene_session_id: String(sceneSessionId),
    continuity_turn_index: continuityTurnIndex,
    domain_commit_id: domainCommitId,
    inference_trace: inferenceTrace,
    provider_failure: providerFailure,
    scene_events: [...sceneAgent.session.events],
    boundary_metrics: api.metrics,
  };
}
