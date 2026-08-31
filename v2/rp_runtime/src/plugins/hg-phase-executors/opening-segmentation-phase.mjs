import { openingDecisionPatch } from '../../lib/execution-evidence/phase-decision.mjs';
import { parseNarratorVisibilityEnvelope } from '../../lib/narrative-visibility-parse.mjs';

const OPENING_SEGMENTATION_PROMPT =
  'Segment the authoritative opening prose into narrative visibility units per the instructions.';

export async function runOpeningSegmentationPhase({
  runEphemeralInference,
  recorder,
  trace,
  api,
  sceneAgent,
  sceneSessionId,
  hgSessionId,
  hgSceneId,
  segmentationInferenceId,
  mockOpeningSegmentationResponses,
  modelProfile,
  maxAttempts = 2,
}) {
  const scope = {
    hgSessionId,
    hgSceneId,
    hgRoundId: 'opening-segmentation',
    sceneSessionId,
  };

  const history = await api.getSessionHistory(hgSessionId);
  const openingEntry = (history.entries ?? []).find((entry) => entry.kind === 'opening');
  if (!openingEntry) {
    return { segmented: false, skipped: true, reason: 'no opening entry' };
  }
  const existingNvr = openingEntry.metadata?.narrative_visibility;
  if (existingNvr?.units?.length) {
    return { segmented: true, skipped: true, reason: 'narrative visibility already present' };
  }

  trace.emit(sceneAgent.session, 'hg/opening-segmentation-started', scope, {
    inference_id: segmentationInferenceId,
    role: 'opening_segmentation',
    opening_entry_id: openingEntry.entry_id,
  });

  let lastError = null;
  let manifestId = null;
  let priorEvidenceId = null;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const inferenceId =
      attempt === 0 ? segmentationInferenceId : `${segmentationInferenceId}-retry-${attempt}`;
    let segmentationRun = null;
    try {
      const manifest = await api.prepareOpeningSegmentationContext({
        hg_session_id: hgSessionId,
        inference_id: inferenceId,
      });
      manifestId = String(manifest.manifest_id);
      const mockFallback =
        modelProfile?.kind === 'mock'
          ? [
              JSON.stringify({
                narrative_visibility: {
                  units: [
                    {
                      unit_id: 'u1',
                      kind: 'observable_scene',
                      text: String(openingEntry.content ?? '').trim(),
                      recipients: { scope: 'public' },
                    },
                  ],
                },
              }),
            ]
          : [];
      segmentationRun = await runEphemeralInference({
        inferenceId,
        prompt: OPENING_SEGMENTATION_PROMPT,
        manifest,
        mockResponses: mockOpeningSegmentationResponses?.length
          ? mockOpeningSegmentationResponses
          : mockFallback,
        modelProfile,
        evidenceContext: {
          hgSessionId,
          hgSceneId,
          hgRoundId: 'opening-segmentation',
          role: 'opening_segmentation',
          inferenceId,
          attemptIndex: attempt,
          priorAttemptId: priorEvidenceId,
        },
      });

      if (segmentationRun.failed) {
        throw new Error(segmentationRun.failure?.message ?? 'opening segmentation inference failed');
      }

      const parsedEnvelope = parseNarratorVisibilityEnvelope(segmentationRun.raw ?? '');
      let narrativeVisibility = parsedEnvelope.narrativeVisibility;
      if (!narrativeVisibility?.units?.length) {
        throw new Error('opening segmentation produced no narrative visibility units');
      }

      const nvrValidation = await api.validateNarrativeVisibility({
        hg_session_id: hgSessionId,
        narrative_visibility: narrativeVisibility,
      });
      if (!nvrValidation.accepted || !nvrValidation.record) {
        throw new Error(nvrValidation.reason || 'opening narrative visibility validation failed');
      }
      narrativeVisibility = nvrValidation.record;

      await api.attachOpeningNarrativeVisibility({
        hg_session_id: hgSessionId,
        narrative_visibility: narrativeVisibility,
      });

      recorder?.patchDecision(
        segmentationRun.evidenceId,
        hgSessionId,
        openingDecisionPatch({
          inferenceOutcome: 'succeeded',
          presentationText: String(openingEntry.content ?? ''),
          presentationFailed: false,
          attemptIndex: attempt,
        }),
      );
      priorEvidenceId = segmentationRun.evidenceId ?? priorEvidenceId;

      trace.emit(sceneAgent.session, 'hg/opening-segmentation-completed', scope, {
        inference_id: inferenceId,
        opening_segmentation_inference_session_id: segmentationRun.inferenceSessionId,
        role: 'opening_segmentation',
        manifest_id: manifestId,
        unit_count: narrativeVisibility.units?.length ?? 0,
        attempt_index: attempt,
        inference_trace: segmentationRun.trace,
      });

      return {
        segmented: true,
        skipped: false,
        narrative_visibility: narrativeVisibility,
        opening_segmentation_inference_session_id: segmentationRun.inferenceSessionId,
        opening_segmentation_manifest_id: manifestId,
        inference_id: inferenceId,
      };
    } catch (error) {
      lastError = error;
      recorder?.patchDecision(
        segmentationRun?.evidenceId ?? null,
        hgSessionId,
        openingDecisionPatch({
          inferenceOutcome: segmentationRun?.failed ? 'inference_error' : 'empty_output',
          presentationText: null,
          presentationFailed: true,
          failureReason: String(error?.message ?? error),
          attemptIndex: attempt,
        }),
      );
      priorEvidenceId = segmentationRun?.evidenceId ?? priorEvidenceId;
    }
  }

  trace.emit(sceneAgent.session, 'hg/opening-segmentation-failed', scope, {
    inference_id: segmentationInferenceId,
    role: 'opening_segmentation',
    manifest_id: manifestId,
    reason: String(lastError?.message ?? lastError),
    presentation_failure_class: 'opening_segmentation_failed',
    canon_preserved: true,
  });

  return {
    segmented: false,
    skipped: false,
    segmentation_failed: true,
    segmentation_failure_reason: String(lastError?.message ?? lastError),
    opening_segmentation_manifest_id: manifestId,
  };
}
