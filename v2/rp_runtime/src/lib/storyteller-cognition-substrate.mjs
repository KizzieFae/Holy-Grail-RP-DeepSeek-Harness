import {
  buildStorytellerAdvisoryDecisionPatch,
  buildStorytellerOrientationDecisionPatch,
} from './execution-evidence/ni-evidence.mjs';
import { runLibrarianMediation } from './librarian-mediation-substrate.mjs';
import {
  buildStorytellerAssessmentPrompt,
  manifestFromStorytellerAssessmentPrepareResponse,
  parseStorytellerAssessment,
  STORYTELLER_ASSESSMENT_SCHEMA,
} from './storyteller-assessment-envelope.mjs';
import { LIVE_INFERENCE_TRANSPORT_PROMPT } from './live-inference-prompts.mjs';
import { manifestFromStorytellerPrepareResponse } from './storyteller-orientation-envelope.mjs';

/**
 * DSH-side Storyteller cognition substrate (#32 S3a).
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
  recorder = null,
  hgSessionId = evidenceContextBase?.hgSessionId ?? null,
}) {
  const evidenceBase = {
    ...evidenceContextBase,
    role: 'storyteller',
    inferenceId,
    hgSceneId,
    hgRoundId,
    parentInferenceId: inferenceId,
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
    prompt: LIVE_INFERENCE_TRANSPORT_PROMPT,
    manifest: orientationManifest,
    mockResponses: mockOrientationResponse ? [mockOrientationResponse] : [],
    modelProfile,
    evidenceContext: {
      ...evidenceBase,
      inferenceId: orientationInferenceId,
      inferenceKind: 'storyteller_orientation',
      niForensics: true,
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
      audit: {
        orientation_inference_id: orientationInferenceId,
        orientation_evidence_id: orientationRun.evidenceId ?? null,
        failure: orientationRun.failure,
      },
    };
  }

  const orientationFinalize = await domainApi.finalizeStorytellerOrientation({
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    inference_id: inferenceId,
    orientation_result: orientationRun.raw,
  });

  if (recorder?.isEnabled?.() && orientationRun.evidenceId && hgSessionId) {
    recorder.patchDecision(
      orientationRun.evidenceId,
      hgSessionId,
      buildStorytellerOrientationDecisionPatch({
        accepted: Boolean(orientationFinalize.accepted),
        reason: orientationFinalize.reason ?? null,
      }),
    );
  }

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
          orientation_evidence_id: orientationRun.evidenceId ?? null,
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
    recorder,
    hgSessionId,
    upstreamEvidenceId: orientationRun.evidenceId ?? null,
    upstreamAssociationKey: 'orientation_evidence_id',
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
      inferenceId: assessmentInferenceId,
      inferenceKind: 'storyteller_assessment',
      niForensics: true,
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

  if (recorder?.isEnabled?.() && assessmentRun.evidenceId && hgSessionId) {
    recorder.patchDecision(
      assessmentRun.evidenceId,
      hgSessionId,
      buildStorytellerAdvisoryDecisionPatch({
        assessmentAccepted: Boolean(assessmentFinalize.accepted),
        assessmentReason: assessmentFinalize.reason ?? null,
        packageId: assessmentFinalize.package?.package_id ?? null,
        degradationLevel: assessmentFinalize.package?.degradation?.level ?? null,
      }),
    );
    if (orientationRun.evidenceId) {
      recorder.linkNiAssociation(hgSessionId, orientationRun.evidenceId, assessmentRun.evidenceId, {
        leftKey: 'assessment_evidence_id',
        rightKey: 'orientation_evidence_id',
      });
    }
    if (mediation.mediationEvidenceId) {
      recorder.linkNiAssociation(
        hgSessionId,
        mediation.mediationEvidenceId,
        assessmentRun.evidenceId,
        {
          leftKey: 'assessment_evidence_id',
          rightKey: 'mediation_evidence_id',
        },
      );
    }
  }

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
      orientation_evidence_id: orientationRun.evidenceId ?? null,
      mediation_evidence_id: mediation.mediationEvidenceId ?? null,
      assessment_inference_id: assessmentInferenceId,
      assessment_evidence_id: assessmentRun.evidenceId ?? null,
      librarian_request_id: mediation.bundle?.request_id ?? null,
      librarian_bundle_id: mediation.bundle?.bundle_id ?? null,
      host_validation: assessmentFinalize.reason ?? null,
    },
  };
}
