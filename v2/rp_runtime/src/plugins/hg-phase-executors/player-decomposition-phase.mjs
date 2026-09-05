import { parseSemanticDecompositionEnvelope } from '../../lib/perceptual-visibility-parse.mjs';

const MAX_PLAYER_DECOMPOSITION_ATTEMPTS = 2;

/** Domain Host context-preparation boundary (matches narrator `context_prepare` convention). */
export const PLAYER_DECOMPOSITION_FAILURE_CLASS_CONTEXT_PREPARE = 'context_prepare';

/** Post-inference Domain Host normalization transport/HTTP failure (not semantic, not retryable). */
export const PLAYER_DECOMPOSITION_FAILURE_CLASS_NORMALIZATION_TRANSPORT =
  'normalization_transport_unavailable';

export const PLAYER_DECOMPOSITION_TASK_PROMPT =
  'Decompose the player-authored turn into semantic perceptual units with verbatim excerpts only.';

export const PLAYER_DECOMPOSITION_RETRY_HEADER = 'ATTEMPT_2_OUTPUT_RETRY:';

const RETRY_GUIDANCE = {
  sir_malformed:
    'Respond with ONLY valid JSON matching the OUTPUT FORMAT in context.',
  sir_invalid_semantics:
    'Correct invalid kind or recipient scope values. Use only allowed kinds and scopes.',
  sir_non_verbatim_excerpt:
    'Each unit excerpt must be a verbatim substring of the player source.',
  sir_substantive_omission:
    'Account for all substantive player source content in semantic unit excerpts.',
  sir_overlap_conflict:
    'Semantic unit excerpts must not overlap and must fit the player source without conflict.',
  fragment_assignment_ambiguous:
    'Your verbatim unit excerpts were insufficiently distinctive for deterministic source matching. '
    + 'Select unambiguous semantic boundaries using naturally distinctive verbatim excerpts. '
    + 'Account for all substantive player source content.',
  normalization_search_budget_exceeded:
    'Your verbatim unit excerpts produced an overly complex matching surface for deterministic normalization. '
    + 'Select clearer semantic boundaries using naturally distinctive verbatim excerpts. '
    + 'Account for all substantive player source content.',
  validation_rejected:
    'Correct semantic kind/recipient choices while preserving verbatim excerpts and completeness.',
};

function resolveNormalizationTransportFailureClass(err) {
  const known = err?.failureClass;
  if (
    known === 'host_internal_error'
    || known === 'api_http_error'
    || known === 'service_unavailable'
    || known === 'transport_error'
  ) {
    return known;
  }
  return PLAYER_DECOMPOSITION_FAILURE_CLASS_NORMALIZATION_TRANSPORT;
}

function buildNormalizationTransportFailure({
  attemptInferenceId,
  attempt,
  evidenceId,
  err,
  semanticDecomposition,
  rawSemanticOutput,
  modelProfile,
}) {
  return {
    playerDecomposition: {
      failure_class: resolveNormalizationTransportFailureClass(err),
      reason: err instanceof Error ? err.message : String(err),
      generation: buildInferenceGenerationForensics({
        attemptInferenceId,
        attempt,
        evidenceId,
        rawSemanticOutput,
        modelProfile,
        extra: {
          semantic_decomposition: semanticDecomposition ?? null,
          normalization_stage: 'transport',
        },
      }),
    },
    evidenceId,
  };
}

function buildInferenceGenerationForensics({
  attemptInferenceId,
  attempt,
  evidenceId = null,
  rawSemanticOutput = null,
  modelProfile = null,
  extra = {},
}) {
  return {
    inference_id: attemptInferenceId,
    attempt_index: attempt,
    evidence_id: evidenceId ?? null,
    provider: modelProfile?.provider ?? null,
    model: modelProfile?.model ?? null,
    ...(rawSemanticOutput != null ? { raw_semantic_output: rawSemanticOutput } : {}),
    ...extra,
  };
}

function attachInferenceEvidenceToDecomposition(decomposition, {
  evidenceId,
  attemptInferenceId,
  attempt,
  rawSemanticOutput,
  modelProfile,
}) {
  if (!decomposition || typeof decomposition !== 'object') return decomposition;
  const generation = decomposition.generation ?? {};
  decomposition.generation = {
    ...generation,
    inference_id: generation.inference_id ?? attemptInferenceId,
    attempt_index: generation.attempt_index ?? attempt,
    evidence_id: evidenceId ?? generation.evidence_id ?? null,
    provider: generation.provider ?? modelProfile?.provider ?? null,
    model: generation.model ?? modelProfile?.model ?? null,
    ...(rawSemanticOutput != null && generation.raw_semantic_output == null
      ? { raw_semantic_output: rawSemanticOutput }
      : {}),
  };
  return decomposition;
}

export function buildPlayerDecompositionUserPrompt(playerContent, { priorFailureCode = null } = {}) {
  let prompt = `${PLAYER_DECOMPOSITION_TASK_PROMPT}\n\nPLAYER SOURCE:\n${playerContent}`;
  if (priorFailureCode) {
    const guidance = RETRY_GUIDANCE[priorFailureCode]
      ?? 'Respond with ONLY a single JSON object matching the OUTPUT FORMAT in context.';
    prompt += (
      `\n\n${PLAYER_DECOMPOSITION_RETRY_HEADER}\n` +
      `Prior attempt failed semantic contract (${priorFailureCode}).\n` +
      `${guidance}\n` +
      'Do not include source positions, indices, occurrence numbers, segment IDs, or accounting fields.'
    );
  }
  return prompt;
}

function normalizeForIndexing(content) {
  return String(content ?? '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
}

function buildMockSemanticDecomposition(playerContent) {
  const normalized = normalizeForIndexing(playerContent);
  if (!normalized.length) {
    return { semantic_decomposition: { units: [] } };
  }
  return {
    semantic_decomposition: {
      units: [
        {
          kind: 'speech',
          text: normalized,
          recipients: { scope: 'public', characters: [], roles: [] },
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
    let manifest;
    try {
      manifest = await api.preparePlayerDecompositionContext({
        hg_session_id: hgSessionId,
        inference_id: attemptInferenceId,
        hg_round_id: hgRoundId,
        attempt_index: attempt,
      });
    } catch (err) {
      return {
        playerDecomposition: {
          failure_class: PLAYER_DECOMPOSITION_FAILURE_CLASS_CONTEXT_PREPARE,
          reason: err instanceof Error ? err.message : String(err),
          generation: { inference_id: attemptInferenceId, attempt_index: attempt },
        },
        evidenceId: null,
      };
    }

    try {
      const mockFallback =
        modelProfile?.kind === 'mock'
          ? [
              JSON.stringify(buildMockSemanticDecomposition(playerContent)),
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
          inferenceKind: 'player_decomposition',
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
              generation: buildInferenceGenerationForensics({
                attemptInferenceId,
                attempt,
                evidenceId: inferRun.evidenceId,
                modelProfile,
              }),
            },
            evidenceId: inferRun.evidenceId,
          };
        }
        continue;
      }

      const parsed = parseSemanticDecompositionEnvelope(inferRun.raw ?? '');
      if (parsed.parseError) {
        priorFailureCode = 'sir_malformed';
        priorEvidenceId = inferRun.evidenceId;
        if (attempt + 1 >= MAX_PLAYER_DECOMPOSITION_ATTEMPTS) {
          return {
            playerDecomposition: {
              failure_class: 'sir_malformed',
              reason: parsed.parseError,
              generation: buildInferenceGenerationForensics({
                attemptInferenceId,
                attempt,
                evidenceId: inferRun.evidenceId,
                rawSemanticOutput: inferRun.raw ?? null,
                modelProfile,
              }),
            },
            evidenceId: inferRun.evidenceId,
          };
        }
        continue;
      }

      let normalizeResult;
      try {
        normalizeResult = await api.normalizePlayerDecomposition({
          hg_session_id: hgSessionId,
          content: playerContent,
          speaker: 'Player',
          semantic_decomposition: parsed.semanticDecomposition,
          generation: buildInferenceGenerationForensics({
            attemptInferenceId,
            attempt,
            evidenceId: inferRun.evidenceId,
            rawSemanticOutput: inferRun.raw ?? null,
            modelProfile,
          }),
          attempt_index: attempt,
        });
      } catch (err) {
        return buildNormalizationTransportFailure({
          attemptInferenceId,
          attempt,
          evidenceId: inferRun.evidenceId,
          err,
          semanticDecomposition: parsed.semanticDecomposition,
          rawSemanticOutput: inferRun.raw ?? null,
          modelProfile,
        });
      }

      if (normalizeResult.accepted && normalizeResult.player_decomposition) {
        return {
          playerDecomposition: attachInferenceEvidenceToDecomposition(
            normalizeResult.player_decomposition,
            {
              evidenceId: inferRun.evidenceId,
              attemptInferenceId,
              attempt,
              rawSemanticOutput: inferRun.raw ?? null,
              modelProfile,
            },
          ),
          evidenceId: inferRun.evidenceId,
          normalizationAudit: normalizeResult.normalization_audit ?? null,
        };
      }

      const failureClass = normalizeResult.failure_class ?? 'normalization_impossible';
      priorFailureCode = failureClass;
      priorEvidenceId = inferRun.evidenceId;
      if (normalizeResult.retry_eligible && attempt + 1 < MAX_PLAYER_DECOMPOSITION_ATTEMPTS) {
        continue;
      }

      return {
        playerDecomposition: {
          failure_class: failureClass,
          reason: normalizeResult.reason ?? failureClass,
          generation: buildInferenceGenerationForensics({
            attemptInferenceId,
            attempt,
            evidenceId: inferRun.evidenceId,
            rawSemanticOutput: inferRun.raw ?? null,
            modelProfile,
            extra: {
              semantic_decomposition: parsed.semanticDecomposition,
              normalization: normalizeResult.normalization_audit ?? null,
            },
          }),
        },
        evidenceId: inferRun.evidenceId,
      };
    } catch (err) {
      priorFailureCode = 'inference_unavailable';
      priorEvidenceId = priorEvidenceId ?? null;
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
