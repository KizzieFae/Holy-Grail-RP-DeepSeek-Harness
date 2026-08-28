import { runLibrarianMediation } from './librarian-mediation-substrate.mjs';

const COGNITION_SCHEMA = {
  type: 'object',
  properties: {
    baseline_sufficient: { type: 'boolean' },
    information_needs: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          need_id: { type: 'string' },
          question: { type: 'string' },
          referent_refs: { type: 'array', items: { type: 'string' } },
        },
        required: ['question'],
      },
    },
    resolutions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          need_id: { type: 'string' },
          category: {
            type: 'string',
            enum: ['A', 'B1', 'B2', 'C', 'cannot_safely_resolve'],
          },
          detail: { type: 'string' },
          property_key: { type: 'string' },
          value: { type: 'string' },
          stable_refs: { type: 'array', items: { type: 'string' } },
          mediation_outcome: { type: 'string' },
          reasoning_summary: { type: 'string' },
        },
        required: ['category', 'detail'],
      },
    },
    assessment_notes: { type: 'string' },
  },
  required: ['baseline_sufficient', 'resolutions'],
};

function buildCognitionPrompt() {
  return [
    'Perform Narrator environmental cognition (#49).',
    'Return JSON only matching the provided schema.',
    'Assess whether the environmental baseline suffices; if not, list semantic information needs.',
    'Resolve each need into category A, B1, B2, C, or cannot_safely_resolve.',
    'Only no_match mediation permits bounded origination.',
    JSON.stringify(COGNITION_SCHEMA, null, 2),
  ].join('\n');
}

function parseCognitionResult(raw) {
  if (!raw) {
    return { ok: false, result: null, error: 'empty cognition output' };
  }
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
    if (!parsed || typeof parsed !== 'object') {
      return { ok: false, result: null, error: 'cognition output not an object' };
    }
    return { ok: true, result: parsed, error: null };
  } catch (error) {
    return { ok: false, result: null, error: String(error?.message ?? error) };
  }
}

function manifestFromPrepareResponse(prepareResponse) {
  const manifest = prepareResponse?.manifest ?? prepareResponse;
  return manifest;
}

/**
 * Pre-render Narrator environmental cognition (#49).
 * Returns audit payload for prepareNarratorContext.environment_cognition_audit.
 */
export async function runNarratorEnvironmentCognition({
  api,
  runEphemeralInference,
  hgSceneId,
  hgRoundId,
  inferenceId,
  characterId,
  domainCommitId,
  continuityTurnIndex,
  modelProfile = null,
  mockCognitionResponse = null,
  allowDeterministicFallback = true,
}) {
  const prepare = await api.prepareNarratorEnvironmentCognitionContext({
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    inference_id: inferenceId,
    character_id: characterId,
    domain_commit_id: domainCommitId,
    continuity_turn_index: continuityTurnIndex,
  });

  const cognitionInferenceId = `${inferenceId}-narrator-env-cog`;
  const manifest = manifestFromPrepareResponse(prepare);

  let cognitionRaw = mockCognitionResponse;
  if (!cognitionRaw) {
    const run = await runEphemeralInference({
      inferenceId: cognitionInferenceId,
      prompt: buildCognitionPrompt(),
      manifest,
      mockResponses: [],
      modelProfile,
      evidenceContext: {
        hgSceneId,
        hgRoundId,
        role: 'narrator',
        characterId,
        inferenceId: cognitionInferenceId,
        inferenceKind: 'narrator_environment_cognition',
      },
    });
    if (run.failed) {
      if (!allowDeterministicFallback) {
        return {
          ok: false,
          stage: 'cognition_inference',
          failureReason: run.failure?.reason ?? 'cognition_inference_failed',
          audit: null,
          prepare,
        };
      }
      cognitionRaw = JSON.stringify({
        baseline_sufficient: true,
        information_needs: [],
        resolutions: [],
        assessment_notes: 'deterministic_fallback_baseline_sufficient',
      });
    } else {
      cognitionRaw = run.raw;
    }
  }

  const parsed = parseCognitionResult(cognitionRaw);
  const cognitionResult = parsed.ok
    ? parsed.result
    : {
      baseline_sufficient: true,
      information_needs: [],
      resolutions: [],
      assessment_notes: 'parse_fallback_baseline_sufficient',
    };

  const karResponse = await api.buildNarratorEnvironmentKnowledgeRequests({
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    inference_id: inferenceId,
    character_id: characterId,
    domain_commit_id: domainCommitId,
    continuity_turn_index: continuityTurnIndex,
    n1_result: cognitionResult,
  });

  const librarianOutcomes = [];
  const requests = karResponse?.knowledge_access_requests ?? [];
  for (const [index, kar] of requests.entries()) {
    const needId = cognitionResult.information_needs?.[index]?.need_id ?? `need-${index + 1}`;
    const mediation = await runLibrarianMediation({
      domainApi: api,
      hgSceneId,
      inferenceId: `${cognitionInferenceId}-lib-${index}`,
      knowledgeAccessRequest: kar,
      runEphemeralInference,
      allowDeterministicFallback,
      modelProfile,
      evidenceContextBase: {
        hgSceneId,
        hgRoundId,
        role: 'narrator',
        characterId,
        inferenceId: cognitionInferenceId,
      },
    });
    librarianOutcomes.push({
      need_id: needId,
      mediation_outcome: mediation?.bundle?.mediation_outcome ?? 'mediation_failure',
      request_id: kar?.request_id ?? null,
    });
    const resolution = (cognitionResult.resolutions ?? []).find((item) => item.need_id === needId);
    if (resolution && !resolution.mediation_outcome) {
      resolution.mediation_outcome = librarianOutcomes[librarianOutcomes.length - 1].mediation_outcome;
    }
  }

  const finalize = await api.finalizeNarratorEnvironmentCognition({
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    inference_id: inferenceId,
    character_id: characterId,
    domain_commit_id: domainCommitId,
    continuity_turn_index: continuityTurnIndex,
    cognition_result: cognitionResult,
    librarian_outcomes: librarianOutcomes,
  });

  return {
    ok: Boolean(finalize?.accepted),
    audit: finalize?.audit ?? null,
    finalize,
    prepare,
    cognitionResult,
    librarianOutcomes,
  };
}

export { COGNITION_SCHEMA, buildCognitionPrompt, parseCognitionResult };
