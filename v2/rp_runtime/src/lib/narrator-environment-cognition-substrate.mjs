import { runBoundedConcurrency } from './bounded-concurrency.mjs';
import { runLibrarianMediation } from './librarian-mediation-substrate.mjs';
import {
  effectiveNarratorMediationParallelism,
  narratorMediationExecutionMode,
  resolveMaxParallelNarratorMediationInferences,
} from './narrator-mediation-concurrency.mjs';
import {
  ENV_COGNITION_STAGES,
  FORENSIC_BOUNDARIES,
  runEnvironmentCognitionStage,
} from './narrator-forensic-attribution.mjs';

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
          response_sufficient: { type: 'boolean' },
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
    'Perform Narrator environmental cognition (#49 / #89 sufficiency).',
    'Return JSON only matching the provided schema.',
    'Assess whether the environmental baseline suffices; if not, list semantic information needs.',
    'Resolve each need into category A, B1, B2, C, or cannot_safely_resolve.',
    'Librarian match means relevant knowledge was found — NOT render sufficiency.',
    'Set response_sufficient per resolution. When insufficient, minimum B2 may follow Host validation.',
    'Never reinterpret match as no_match. Never invent on retrieval/mediation failure.',
    JSON.stringify(COGNITION_SCHEMA, null, 2),
  ].join('\n');
}

function extractComposedGrounding(mediation) {
  const bundle = mediation?.bundle;
  if (!bundle || typeof bundle !== 'object') {
    return '';
  }
  const parts = [];
  for (const entry of bundle.entries ?? []) {
    const text = entry?.content ?? entry?.text ?? '';
    if (text) {
      parts.push(String(text).trim());
    }
  }
  const synthesis = bundle.synthesis_summary ?? bundle.synthesis ?? mediation?.parsed?.rationale;
  if (synthesis) {
    parts.push(String(synthesis).trim());
  }
  return parts.filter(Boolean).join('; ');
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

function buildInferenceEnvelope({
  cognitionInferenceId,
  raw,
  trace,
  failed,
}) {
  const finish = trace?.finish ?? null;
  return {
    raw_assistant_text: raw ?? '',
    inference_failed: Boolean(failed),
    finish_kind: typeof finish === 'object' ? finish?.kind ?? finish : finish,
    inference_attempt_id: cognitionInferenceId,
  };
}

function buildLibrarianOutcome({
  needId,
  needIndex,
  kar,
  mediation,
  parallelGroupId,
  mediationExecutionMode,
}) {
  return {
    need_id: needId,
    need_index: needIndex,
    parallel_group_id: parallelGroupId,
    mediation_execution_mode: mediationExecutionMode,
    mediation_outcome: mediation?.bundle?.mediation_outcome ?? 'mediation_failure',
    request_id: kar?.request_id ?? null,
    composed_grounding: extractComposedGrounding(mediation),
    rationale: mediation?.parsed?.rationale ?? null,
    entries: (mediation?.bundle?.entries ?? []).map((entry) => ({
      content: entry?.content ?? entry?.text ?? '',
    })),
  };
}

function patchResolutionMediationOutcomes(cognitionResult, librarianOutcomes) {
  for (const outcome of librarianOutcomes) {
    const resolution = (cognitionResult.resolutions ?? []).find(
      (item) => item.need_id === outcome.need_id,
    );
    if (resolution && !resolution.mediation_outcome) {
      resolution.mediation_outcome = outcome.mediation_outcome;
    }
  }
}

function environmentCognitionEvidenceFromFinalize(finalize, inferenceEnvelope) {
  const audit = finalize?.audit ?? {};
  return {
    cognition_failed: Boolean(audit.cognition_failed),
    cognition_status: audit.cognition_status ?? finalize?.cognition_status ?? null,
    status_reason: audit.status_reason ?? finalize?.status_reason ?? null,
    baseline_sufficient: audit.n1?.baseline_sufficient ?? finalize?.baseline_sufficient ?? null,
    cognition_id: audit.cognition_id ?? finalize?.cognition_id ?? null,
    domain_commit_id: audit.domain_commit_id ?? null,
    inference_attempt_id: inferenceEnvelope?.inference_attempt_id ?? null,
  };
}

/**
 * Pre-render Narrator environmental cognition (#49 / #151).
 * Returns audit payload for durable turn metadata / execution evidence.
 */
export async function runNarratorEnvironmentCognition({
  api,
  runEphemeralInference,
  hgSessionId,
  hgSceneId,
  hgRoundId,
  inferenceId,
  characterId,
  domainCommitId,
  continuityTurnIndex,
  modelProfile = null,
  mockCognitionResponse = null,
  inferenceConfig = {},
}) {
  const evidenceContextBase = {
    hgSessionId,
    hgSceneId,
    hgRoundId,
    role: 'narrator',
    characterId,
  };

  const prepare = await runEnvironmentCognitionStage(
    ENV_COGNITION_STAGES.PREPARE,
    FORENSIC_BOUNDARIES.DOMAIN_API,
    () => api.prepareNarratorEnvironmentCognitionContext({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      inference_id: inferenceId,
      character_id: characterId,
      domain_commit_id: domainCommitId,
      continuity_turn_index: continuityTurnIndex,
    }),
  );

  const cognitionInferenceId = `${inferenceId}-narrator-env-cog`;
  const manifest = manifestFromPrepareResponse(prepare);

  let cognitionRaw = mockCognitionResponse;
  let inferenceEnvelope = null;
  if (!cognitionRaw) {
    const run = await runEnvironmentCognitionStage(
      ENV_COGNITION_STAGES.INFERENCE,
      FORENSIC_BOUNDARIES.INFERENCE_PROVIDER,
      () => runEphemeralInference({
        inferenceId: cognitionInferenceId,
        prompt: buildCognitionPrompt(),
        manifest,
        mockResponses: [],
        modelProfile,
        evidenceContext: {
          ...evidenceContextBase,
          inferenceId: cognitionInferenceId,
          inferenceKind: 'narrator_environment_cognition',
        },
      }),
    );
    cognitionRaw = run.raw ?? '';
    inferenceEnvelope = buildInferenceEnvelope({
      cognitionInferenceId,
      raw: cognitionRaw,
      trace: run.trace,
      failed: run.failed,
    });
  } else {
    inferenceEnvelope = buildInferenceEnvelope({
      cognitionInferenceId,
      raw: cognitionRaw,
      trace: null,
      failed: false,
    });
  }

  const parsed = parseCognitionResult(cognitionRaw);
  const cognitionResult = parsed.ok ? parsed.result : {};

  const karResponse = await runEnvironmentCognitionStage(
    ENV_COGNITION_STAGES.KAR_BUILD,
    FORENSIC_BOUNDARIES.DOMAIN_API,
    () => api.buildNarratorEnvironmentKnowledgeRequests({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      inference_id: inferenceId,
      character_id: characterId,
      domain_commit_id: domainCommitId,
      continuity_turn_index: continuityTurnIndex,
      cognition_raw: cognitionRaw ?? '',
      inference_envelope: inferenceEnvelope,
    }),
  );

  const requests = karResponse?.knowledge_access_requests ?? [];
  const maxParallel = resolveMaxParallelNarratorMediationInferences(inferenceConfig);
  const parallelGroupId = cognitionInferenceId;
  const mediationExecutionMode = narratorMediationExecutionMode(requests.length, maxParallel);
  const parallelism = effectiveNarratorMediationParallelism(requests.length, maxParallel);

  const mediationResults = requests.length === 0
    ? []
    : await runBoundedConcurrency(
      requests,
      parallelism,
      async (kar, index) => {
        const needId = cognitionResult.information_needs?.[index]?.need_id ?? `need-${index + 1}`;
        const mediation = await runEnvironmentCognitionStage(
          ENV_COGNITION_STAGES.LIBRARIAN_MEDIATION,
          FORENSIC_BOUNDARIES.DOMAIN_API,
          () => runLibrarianMediation({
            domainApi: api,
            hgSceneId,
            hgSessionId,
            inferenceId: `${cognitionInferenceId}-lib-${index}`,
            knowledgeAccessRequest: kar,
            runEphemeralInference,
            allowDeterministicFallback: true,
            modelProfile,
            evidenceContextBase: {
              ...evidenceContextBase,
              inferenceId: cognitionInferenceId,
            },
          }),
        );
        return { needId, index, kar, mediation };
      },
    );

  const librarianOutcomes = mediationResults.map(({ needId, index, kar, mediation }) => (
    buildLibrarianOutcome({
      needId,
      needIndex: index,
      kar,
      mediation,
      parallelGroupId,
      mediationExecutionMode,
    })
  ));
  patchResolutionMediationOutcomes(cognitionResult, librarianOutcomes);

  const finalize = await runEnvironmentCognitionStage(
    ENV_COGNITION_STAGES.FINALIZE,
    FORENSIC_BOUNDARIES.DOMAIN_API,
    () => api.finalizeNarratorEnvironmentCognition({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      inference_id: inferenceId,
      character_id: characterId,
      domain_commit_id: domainCommitId,
      continuity_turn_index: continuityTurnIndex,
      cognition_result: cognitionResult,
      cognition_raw: cognitionRaw ?? '',
      inference_envelope: inferenceEnvelope,
      librarian_outcomes: librarianOutcomes,
    }),
  );

  return {
    ok: Boolean(finalize?.accepted),
    audit: finalize?.audit ?? null,
    finalize,
    prepare,
    cognitionResult,
    librarianOutcomes,
    environmentCognitionEvidence: environmentCognitionEvidenceFromFinalize(finalize, inferenceEnvelope),
  };
}

export { COGNITION_SCHEMA, buildCognitionPrompt, parseCognitionResult };
