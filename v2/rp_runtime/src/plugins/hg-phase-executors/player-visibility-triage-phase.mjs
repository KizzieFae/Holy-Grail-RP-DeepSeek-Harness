import { parsePlayerVisibilityTriageEnvelope } from '../../lib/perceptual-visibility-parse.mjs';
import { buildUniformProjectionDecomposition } from '../../lib/player-uniform-projection.mjs';

export const PLAYER_VISIBILITY_TRIAGE_FAILURE_CLASS_CONTEXT_PREPARE = 'context_prepare';

export const PLAYER_VISIBILITY_TRIAGE_TASK_PROMPT =
  'Evaluate whether the player-authored turn is affirmatively safe for uniform projection to all present Characters without semantic decomposition. When any span may be internal, concealed, directed, private, authorial exposition, or ambiguous, answer false.';

export function buildPlayerVisibilityTriageUserPrompt(playerContent) {
  return `${PLAYER_VISIBILITY_TRIAGE_TASK_PROMPT}\n\nPLAYER SOURCE:\n${playerContent}`;
}

export function isAffirmativeUniformProjectionSafe(parsed) {
  return parsed?.uniformProjectionSafe === true && !parsed?.parseError;
}

export async function runPlayerVisibilityTriagePhase({
  runEphemeralInference,
  trace,
  api,
  sceneAgent,
  hgSessionId,
  hgSceneId,
  hgRoundId,
  inferenceId,
  playerContent,
  mockResponses,
  modelProfile,
}) {
  const scope = {
    hgSessionId,
    hgSceneId,
    hgRoundId,
    role: 'player_visibility_triage',
  };

  trace?.emit?.(sceneAgent?.session, 'hg/player-visibility-triage-started', scope, {
    inference_id: inferenceId,
    role: 'player_visibility_triage',
  });

  let manifest;
  try {
    manifest = await api.preparePlayerVisibilityTriageContext({
      hg_session_id: hgSessionId,
      inference_id: inferenceId,
      hg_round_id: hgRoundId,
    });
  } catch (err) {
    trace?.emit?.(sceneAgent?.session, 'hg/player-visibility-triage-failed', scope, {
      inference_id: inferenceId,
      failure_class: PLAYER_VISIBILITY_TRIAGE_FAILURE_CLASS_CONTEXT_PREPARE,
      reason: err instanceof Error ? err.message : String(err),
    });
    return {
      route: 'full_pvr',
      checkerResult: {
        uniform_projection_safe: false,
        reason: 'checker_context_prepare_failed',
        failure_class: PLAYER_VISIBILITY_TRIAGE_FAILURE_CLASS_CONTEXT_PREPARE,
      },
      evidenceId: null,
    };
  }

  try {
    const mockFallback =
      modelProfile?.kind === 'mock'
        ? [JSON.stringify({ uniform_projection_safe: false, reason: 'mock_default_full_pvr' })]
        : [];
    const inferRun = await runEphemeralInference({
      inferenceId,
      prompt: buildPlayerVisibilityTriageUserPrompt(playerContent),
      manifest,
      mockResponses: mockResponses?.length ? mockResponses : mockFallback,
      modelProfile,
      evidenceContext: {
        hgSessionId,
        hgSceneId,
        hgRoundId,
        role: 'player_visibility_triage',
        inferenceId,
        inferenceKind: 'player_visibility_triage',
        attemptIndex: 0,
      },
    });

    if (inferRun.failed) {
      trace?.emit?.(sceneAgent?.session, 'hg/player-visibility-triage-failed', scope, {
        inference_id: inferenceId,
        failure_class: 'inference_unavailable',
        reason: inferRun.failure?.message ?? 'checker inference failed',
      });
      return {
        route: 'full_pvr',
        checkerResult: {
          uniform_projection_safe: false,
          reason: 'checker_inference_unavailable',
          failure_class: 'inference_unavailable',
        },
        evidenceId: inferRun.evidenceId,
      };
    }

    const parsed = parsePlayerVisibilityTriageEnvelope(inferRun.raw ?? '');
    if (parsed.parseError) {
      trace?.emit?.(sceneAgent?.session, 'hg/player-visibility-triage-failed', scope, {
        inference_id: inferenceId,
        failure_class: 'malformed_output',
        reason: parsed.parseError,
      });
      return {
        route: 'full_pvr',
        checkerResult: {
          uniform_projection_safe: false,
          reason: 'checker_malformed_output',
          failure_class: 'malformed_output',
          parse_error: parsed.parseError,
        },
        evidenceId: inferRun.evidenceId,
      };
    }

    if (!isAffirmativeUniformProjectionSafe(parsed)) {
      trace?.emit?.(sceneAgent?.session, 'hg/player-visibility-triage-completed', scope, {
        inference_id: inferenceId,
        route: 'full_pvr',
        checker_reason: parsed.reason,
      });
      return {
        route: 'full_pvr',
        checkerResult: {
          uniform_projection_safe: false,
          reason: parsed.reason ?? 'requires_semantic_decomposition',
          inference_id: inferenceId,
        },
        evidenceId: inferRun.evidenceId,
      };
    }

    const uniformDecomposition = buildUniformProjectionDecomposition(playerContent, {
      checkerAudit: {
        uniform_projection_safe: true,
        reason: parsed.reason ?? 'affirmative_uniform_present',
        inference_id: inferenceId,
      },
      inferenceId,
    });

    trace?.emit?.(sceneAgent?.session, 'hg/player-visibility-triage-completed', scope, {
      inference_id: inferenceId,
      route: 'uniform_projection',
      checker_reason: parsed.reason,
    });

    return {
      route: 'uniform_projection',
      playerDecomposition: uniformDecomposition,
      checkerResult: {
        uniform_projection_safe: true,
        reason: parsed.reason ?? 'affirmative_uniform_present',
        inference_id: inferenceId,
      },
      evidenceId: inferRun.evidenceId,
    };
  } catch (err) {
    trace?.emit?.(sceneAgent?.session, 'hg/player-visibility-triage-failed', scope, {
      inference_id: inferenceId,
      failure_class: 'inference_unavailable',
      reason: err instanceof Error ? err.message : String(err),
    });
    return {
      route: 'full_pvr',
      checkerResult: {
        uniform_projection_safe: false,
        reason: 'checker_exception',
        failure_class: 'inference_unavailable',
      },
      evidenceId: null,
    };
  }
}
