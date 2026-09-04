import { parsePlayerDecompositionEnvelope } from '../../lib/perceptual-visibility-parse.mjs';

const MAX_PLAYER_DECOMPOSITION_ATTEMPTS = 2;

export const PLAYER_DECOMPOSITION_TASK_PROMPT =
  'Decompose the player-authored turn into semantic perceptual units with complete source accounting.';

export const PLAYER_DECOMPOSITION_RETRY_HEADER = 'ATTEMPT_2_OUTPUT_RETRY:';

export function buildPlayerDecompositionUserPrompt(playerContent, { priorFailureCode = null } = {}) {
  let prompt = `${PLAYER_DECOMPOSITION_TASK_PROMPT}\n\nPLAYER SOURCE:\n${playerContent}`;
  if (priorFailureCode) {
    prompt += (
      `\n\n${PLAYER_DECOMPOSITION_RETRY_HEADER}\n` +
      `Prior attempt failed output contract (${priorFailureCode}).\n` +
      'Respond with ONLY a single JSON object matching the OUTPUT FORMAT in context.\n' +
      'No markdown fences, headings, or explanatory prose.'
    );
  }
  return prompt;
}

function normalizeForIndexing(content) {
  return String(content ?? '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
}

function buildMockPlayerDecomposition(playerContent) {
  const normalized = normalizeForIndexing(playerContent);
  const length = normalized.length;
  if (!length) {
    return {
      perceptual_visibility: { units: [] },
      source_accounting: {
        segments: [{ segment_id: 's1', char_start: 0, char_end: 0, disposition: 'non_projects', unit_ids: [] }],
      },
    };
  }
  return {
    perceptual_visibility: {
      units: [
        {
          unit_id: 'u1',
          kind: 'speech',
          text: normalized,
          recipients: { scope: 'public', characters: [], roles: [] },
          source_provenance: { segment_ids: ['s1'], order_index: 0 },
          source: 'player_decomposition',
        },
      ],
    },
    source_accounting: {
      segments: [
        {
          segment_id: 's1',
          char_start: 0,
          char_end: length,
          disposition: 'projects',
          unit_ids: ['u1'],
        },
      ],
    },
  };
}

export async function runPlayerDecompositionPhase({
  runEphemeralInference,
  recorder,
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
    role: 'player_decomposition',
  };

  trace?.emit?.(sceneAgent?.session, 'hg/player-decomposition-started', scope, {
    inference_id: inferenceId,
    role: 'player_decomposition',
  });

  let priorEvidenceId = null;
  let priorFailureCode = null;
  for (let attempt = 0; attempt < MAX_PLAYER_DECOMPOSITION_ATTEMPTS; attempt += 1) {
    const attemptInferenceId =
      attempt === 0 ? inferenceId : `${inferenceId}-retry-${attempt}`;
    try {
      const manifest = await api.preparePlayerDecompositionContext({
        hg_session_id: hgSessionId,
        inference_id: attemptInferenceId,
        hg_round_id: hgRoundId,
        attempt_index: attempt,
      });
      const mockFallback =
        modelProfile?.kind === 'mock'
          ? [
              JSON.stringify(buildMockPlayerDecomposition(playerContent)),
            ]
          : [];
      const inferRun = await runEphemeralInference({
        inferenceId: attemptInferenceId,
        prompt: buildPlayerDecompositionUserPrompt(playerContent, {
          priorFailureCode: attempt > 0 ? priorFailureCode : null,
        }),
        manifest,
        mockResponses: mockResponses?.length ? mockResponses : mockFallback,
        modelProfile,
        evidenceContext: {
          hgSessionId,
          hgSceneId,
          hgRoundId,
          role: 'player_decomposition',
          inferenceId: attemptInferenceId,
          attemptIndex: attempt,
          priorAttemptId: priorEvidenceId,
        },
      });

      if (inferRun.failed) {
        priorFailureCode = 'inference_unavailable';
        priorEvidenceId = inferRun.evidenceId;
        if (attempt + 1 >= MAX_PLAYER_DECOMPOSITION_ATTEMPTS) {
          return {
            playerDecomposition: {
              failure_class: 'inference_unavailable',
              reason: inferRun.failure?.message ?? 'player decomposition inference failed',
              generation: { inference_id: attemptInferenceId, attempt_index: attempt },
            },
            evidenceId: inferRun.evidenceId,
          };
        }
        continue;
      }

      const parsed = parsePlayerDecompositionEnvelope(inferRun.raw ?? '');
      if (parsed.parseError) {
        priorFailureCode = parsed.parseError;
        priorEvidenceId = inferRun.evidenceId;
        if (attempt + 1 >= MAX_PLAYER_DECOMPOSITION_ATTEMPTS) {
          return {
            playerDecomposition: {
              failure_class: 'malformed_output',
              reason: parsed.parseError,
              generation: { inference_id: attemptInferenceId, attempt_index: attempt },
            },
            evidenceId: inferRun.evidenceId,
          };
        }
        continue;
      }

      return {
        playerDecomposition: {
          perceptual_visibility: parsed.perceptualVisibility,
          source_accounting: parsed.sourceAccounting,
          generation: {
            inference_id: attemptInferenceId,
            attempt_index: attempt,
            provider: modelProfile?.provider ?? null,
            model: modelProfile?.model ?? null,
          },
        },
        evidenceId: inferRun.evidenceId,
      };
    } catch (err) {
      priorFailureCode = 'inference_unavailable';
      if (attempt + 1 >= MAX_PLAYER_DECOMPOSITION_ATTEMPTS) {
        return {
          playerDecomposition: {
            failure_class: 'inference_unavailable',
            reason: err instanceof Error ? err.message : String(err),
            generation: { inference_id: attemptInferenceId, attempt_index: attempt },
          },
          evidenceId: priorEvidenceId,
        };
      }
    }
  }

  return {
    playerDecomposition: {
      failure_class: 'inference_unavailable',
      reason: 'player decomposition exhausted retries',
      generation: { inference_id: inferenceId },
    },
    evidenceId: priorEvidenceId,
  };
}
