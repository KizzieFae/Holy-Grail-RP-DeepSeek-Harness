import { runLibrarianMediation } from './librarian-mediation-substrate.mjs';
import {
  buildStorytellerAssessmentPrompt,
  manifestFromStorytellerAssessmentPrepareResponse,
  parseStorytellerAssessment,
  STORYTELLER_ASSESSMENT_SCHEMA,
} from './storyteller-assessment-envelope.mjs';
import {
  buildStorytellerOrientationPrompt,
  manifestFromStorytellerPrepareResponse,
  parseStorytellerOrientation,
  STORYTELLER_ORIENTATION_SCHEMA,
} from './storyteller-orientation-envelope.mjs';

/**
 * DSH-side Storyteller cognition substrate (#32 S3a).
 * Orientation → KAR → Librarian bundle → informed assessment → validated package.
 * Does not inject advisory output into role manifests.
 */
export async function runStorytellerCognition({
  domainApi,
  hgSceneId,
  hgRoundId,
  inferenceId,
  runEphemeralInference,
  mockOrientationResponse = null,
  mockMediationResponse = null,
  mockAssessmentResponse = null,
  modelProfile = null,
  evidenceContextBase = null,
  allowDeterministicFallback = true,
  allowHostDefaultOnOrientationFailure = false,
}) {
  const evidenceBase = {
    ...evidenceContextBase,
    role: 'storyteller',
    inferenceId,
    hgSceneId,
    hgRoundId,
  };

  const orientationPrepare = await domainApi.prepareStorytellerOrientationContext({
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    inference_id: inferenceId,
  });
  const orientationManifest = manifestFromStorytellerPrepareResponse(orientationPrepare);
  const orientationInferenceId = `${inferenceId}-storyteller-orientation`;

  const orientationRun = await runEphemeralInference({
    inferenceId: orientationInferenceId,
    prompt: buildStorytellerOrientationPrompt({ schema: STORYTELLER_ORIENTATION_SCHEMA }),
    manifest: orientationManifest,
    mockResponses: mockOrientationResponse ? [mockOrientationResponse] : [],
    modelProfile,
    evidenceContext: {
      ...evidenceBase,
      storytellerPhase: 'orientation',
    },
  });

  if (orientationRun.failed) {
    return {
      ok: false,
      stage: 'orientation_inference',
      package: null,
      orientationPrepare,
      orientationRun,
      audit: { orientation_inference_id: orientationInferenceId, failure: orientationRun.failure },
    };
  }

  const parsedOrientation = parseStorytellerOrientation(orientationRun.raw);
  const orientationFinalize = await domainApi.finalizeStorytellerOrientation({
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    inference_id: inferenceId,
    orientation_result: parsedOrientation.ok
      ? parsedOrientation.result
      : orientationRun.raw,
  });

  if (!orientationFinalize.accepted || !orientationFinalize.knowledge_access_request) {
    if (!allowHostDefaultOnOrientationFailure) {
      return {
        ok: false,
        stage: 'orientation_finalize',
        package: null,
        orientationPrepare,
        orientationRun,
        orientationFinalize,
        audit: {
          orientation_inference_id: orientationInferenceId,
          reason: orientationFinalize.reason,
        },
      };
    }
  }

  const knowledgeAccessRequest = orientationFinalize.knowledge_access_request;
  if (!knowledgeAccessRequest) {
    return {
      ok: false,
      stage: 'orientation_finalize',
      package: null,
      orientationPrepare,
      orientationRun,
      orientationFinalize,
    };
  }

  const mediation = await runLibrarianMediation({
    domainApi,
    hgSceneId,
    inferenceId: `${inferenceId}-storyteller-librarian`,
    knowledgeAccessRequest,
    runEphemeralInference,
    mockResponse: mockMediationResponse,
    modelProfile,
    allowDeterministicFallback,
    evidenceContextBase: evidenceBase,
  });

  if (!mediation.bundle) {
    return {
      ok: false,
      stage: 'librarian',
      package: null,
      orientationPrepare,
      orientationRun,
      orientationFinalize,
      mediation,
    };
  }

  const assessmentPrepare = await domainApi.prepareStorytellerAssessmentContext({
    hg_scene_id: hgSceneId,
    inference_id: inferenceId,
    orientation: orientationFinalize.orientation,
    bundle: mediation.bundle,
  });
  const assessmentManifest = manifestFromStorytellerAssessmentPrepareResponse(assessmentPrepare);
  const assessmentInferenceId = `${inferenceId}-storyteller-assessment`;

  const assessmentRun = await runEphemeralInference({
    inferenceId: assessmentInferenceId,
    prompt: buildStorytellerAssessmentPrompt({ schema: STORYTELLER_ASSESSMENT_SCHEMA }),
    manifest: assessmentManifest,
    mockResponses: mockAssessmentResponse ? [mockAssessmentResponse] : [],
    modelProfile,
    evidenceContext: {
      ...evidenceBase,
      storytellerPhase: 'assessment',
      bundleId: mediation.bundle.bundle_id,
    },
  });

  if (assessmentRun.failed) {
    return {
      ok: false,
      stage: 'assessment_inference',
      package: null,
      orientationPrepare,
      orientationRun,
      orientationFinalize,
      mediation,
      assessmentPrepare,
      assessmentRun,
    };
  }

  const parsedAssessment = parseStorytellerAssessment(assessmentRun.raw);
  const assessmentFinalize = await domainApi.finalizeStorytellerAssessment({
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    inference_id: inferenceId,
    orientation: orientationFinalize.orientation,
    bundle: mediation.bundle,
    assessment_result: parsedAssessment.ok ? parsedAssessment.result : assessmentRun.raw,
    orientation_inference_id: orientationInferenceId,
    assessment_inference_id: assessmentInferenceId,
    follow_up_request_ids: [],
  });

  return {
    ok: Boolean(assessmentFinalize.accepted),
    stage: assessmentFinalize.accepted ? 'finalized' : 'assessment_finalize',
    package: assessmentFinalize.package ?? null,
    orientationPrepare,
    orientationRun,
    orientationFinalize,
    mediation,
    assessmentPrepare,
    assessmentRun,
    assessmentFinalize,
    audit: {
      orientation_inference_id: orientationInferenceId,
      assessment_inference_id: assessmentInferenceId,
      librarian_request_id: mediation.bundle?.request_id ?? null,
      librarian_bundle_id: mediation.bundle?.bundle_id ?? null,
      host_validation: assessmentFinalize.reason ?? null,
    },
  };
}
