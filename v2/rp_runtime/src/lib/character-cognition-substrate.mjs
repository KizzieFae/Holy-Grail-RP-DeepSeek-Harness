import { runLibrarianMediation } from './librarian-mediation-substrate.mjs';
import {
  buildCharacterOrientationPrompt,
  manifestFromCharacterPrepareResponse,
  parseCharacterOrientation,
  CHARACTER_ORIENTATION_SCHEMA,
} from './character-orientation-envelope.mjs';
import {
  getCharacterKnowledgeCacheEntry,
  setCharacterKnowledgeCacheEntry,
} from './character-knowledge-cache.mjs';
import { buildCharacterOrientationDecisionPatch } from './execution-evidence/ni-evidence.mjs';

/**
 * DSH-side Character knowledge cognition (#38).
 * Orientation → KAR → Librarian bundle (ephemeral/request-attached).
 */
export async function runCharacterKnowledgeCognition({
  domainApi,
  hgSceneId,
  hgRoundId,
  characterId,
  role,
  turnIndex,
  inferenceId,
  directorDecision = null,
  correctionContext = null,
  runEphemeralInference,
  mockOrientationResponse = null,
  mockMediationResponse = null,
  modelProfile = null,
  evidenceContextBase = null,
  recorder = null,
  hgSessionId = evidenceContextBase?.hgSessionId ?? null,
}) {
  const evidenceBase = {
    ...evidenceContextBase,
    role: 'character',
    characterId,
    inferenceId,
    hgSceneId,
    hgRoundId,
    parentInferenceId: inferenceId,
  };

  const orientationPrepare = await domainApi.prepareCharacterOrientationContext({
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    inference_id: inferenceId,
    character_id: characterId,
    role,
    turn_index: turnIndex,
    director_decision: directorDecision ?? undefined,
    correction_context: correctionContext ?? undefined,
  });

  const orientationInferenceId = `${inferenceId}-character-orientation`;
  const orientationRun = await runEphemeralInference({
    inferenceId: orientationInferenceId,
    prompt: buildCharacterOrientationPrompt({ schema: CHARACTER_ORIENTATION_SCHEMA }),
    manifest: manifestFromCharacterPrepareResponse(orientationPrepare),
    mockResponses: mockOrientationResponse ? [mockOrientationResponse] : [],
    modelProfile,
    evidenceContext: {
      ...evidenceBase,
      inferenceId: orientationInferenceId,
      inferenceKind: 'character_orientation',
      niForensics: true,
      characterKnowledgePhase: 'orientation',
    },
  });

  if (orientationRun.failed) {
    return {
      ok: false,
      stage: 'orientation_inference',
      bundle: null,
      orientationPrepare,
      orientationRun,
      audit: {
        orientation_inference_id: orientationInferenceId,
        orientation_evidence_id: orientationRun.evidenceId ?? null,
        failure: orientationRun.failure,
      },
    };
  }

  const parsedOrientation = parseCharacterOrientation(orientationRun.raw);
  const orientationFinalize = await domainApi.finalizeCharacterOrientation({
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    inference_id: inferenceId,
    character_id: characterId,
    turn_index: turnIndex,
    orientation_result: parsedOrientation.ok
      ? parsedOrientation.result
      : orientationRun.raw,
    upstream_fingerprint: orientationPrepare.upstream_fingerprint,
    director_decision: directorDecision ?? undefined,
    correction_context: correctionContext ?? undefined,
  });

  if (recorder?.isEnabled?.() && orientationRun.evidenceId && hgSessionId) {
    recorder.patchDecision(
      orientationRun.evidenceId,
      hgSessionId,
      buildCharacterOrientationDecisionPatch({
        accepted: Boolean(orientationFinalize.accepted),
        reason: orientationFinalize.reason ?? null,
        reuseKey: orientationFinalize.reuse_key ?? null,
        knowledgeAccessRequestId: orientationFinalize.knowledge_access_request?.request_id ?? null,
        upstreamFingerprint: orientationPrepare.upstream_fingerprint ?? null,
      }),
    );
  }

  if (!orientationFinalize.accepted || !orientationFinalize.knowledge_access_request) {
    return {
      ok: false,
      stage: 'orientation_finalize',
      bundle: null,
      orientationPrepare,
      orientationRun,
      orientationFinalize,
      audit: {
        orientation_inference_id: orientationInferenceId,
        orientation_evidence_id: orientationRun.evidenceId ?? null,
        reason: orientationFinalize.reason,
      },
    };
  }

  const reuseKey = orientationFinalize.reuse_key;
  const cached = getCharacterKnowledgeCacheEntry(reuseKey);
  if (cached?.bundle) {
    return {
      ok: true,
      stage: 'cache_hit',
      bundle: cached.bundle,
      orientationPrepare,
      orientationRun,
      orientationFinalize,
      mediation: cached.mediation ?? null,
      audit: {
        orientation_inference_id: orientationInferenceId,
        orientation_evidence_id: orientationRun.evidenceId ?? null,
        mediation_evidence_id: cached.mediation?.mediationEvidenceId ?? null,
        reuse_key: reuseKey,
        cache_hit: true,
        librarian_bundle_id: cached.bundle?.bundle_id ?? null,
      },
    };
  }

  const mediation = await runLibrarianMediation({
    domainApi,
    hgSceneId,
    inferenceId: `${inferenceId}-character-librarian`,
    knowledgeAccessRequest: orientationFinalize.knowledge_access_request,
    runEphemeralInference,
    mockResponse: mockMediationResponse,
    modelProfile,
    allowDeterministicFallback: false,
    evidenceContextBase: evidenceBase,
    recorder,
    hgSessionId,
    upstreamEvidenceId: orientationRun.evidenceId ?? null,
    upstreamAssociationKey: 'orientation_evidence_id',
  });

  const bundle = mediation.bundle ?? null;
  const contextualOk = bundle?.mediation_mode === 'contextual_semantic';
  if (bundle && contextualOk) {
    setCharacterKnowledgeCacheEntry(reuseKey, { bundle, mediation });
  }

  return {
    ok: Boolean(bundle && contextualOk),
    stage: bundle && contextualOk ? 'finalized' : 'librarian',
    bundle: bundle && contextualOk ? bundle : null,
    orientationPrepare,
    orientationRun,
    orientationFinalize,
    mediation,
    audit: {
      orientation_inference_id: orientationInferenceId,
      orientation_evidence_id: orientationRun.evidenceId ?? null,
      mediation_evidence_id: mediation.mediationEvidenceId ?? null,
      reuse_key: reuseKey,
      cache_hit: false,
      librarian_request_id: bundle?.request_id ?? null,
      librarian_bundle_id: bundle?.bundle_id ?? null,
      mediation_mode: bundle?.mediation_mode ?? null,
      librarian_stage: mediation.stage,
      librarian_ok: mediation.ok,
    },
  };
}
