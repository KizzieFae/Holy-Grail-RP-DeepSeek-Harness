import crypto from 'node:crypto';

import { buildNoChangeUpdateInference } from './plot-cognition-update-envelope.mjs';
import { runPlotCognitionUpdateGeneration } from './plot-cognition-update-substrate.mjs';

function operationRequiresInference(operation) {
  return operation === 'semantic_update';
}

function operationClearsOnSuccess(operation) {
  return [
    'semantic_update',
    'authority_advance',
    'reconciliation',
    'clear_pending',
    'initialization',
  ].includes(operation);
}

/**
 * Discover and service Domain-owned Plot Cognition pending work (#63).
 * Uses only Domain state — safe across orchestrator restart.
 */
export async function runPlotCognitionPendingWorkLifecycle({
  domainApi,
  trace,
  sceneAgent,
  scope,
  hgSceneId,
  inferenceId,
  runEphemeralInference,
  mockUpdateResponse = null,
  mockInitResponse = null,
  modelProfile = null,
  evidenceContextBase = null,
  delayMs = 0,
}) {
  const correlation = {
    inference_id: inferenceId,
    hg_scene_id: hgSceneId,
    hg_round_id: scope?.hgRoundId ?? null,
  };

  trace?.emit?.(sceneAgent?.session, 'hg/plot-cognition-started', scope, correlation);

  if (delayMs > 0) {
    await new Promise((resolve) => {
      setTimeout(resolve, delayMs);
    });
  }

  const plan = await domainApi.planPostCommitPlotCognitionWork({ hg_scene_id: hgSceneId });
  const operation = plan?.operation ?? 'blocked';

  if (!plan?.accepted && operation === 'none') {
    trace?.emit?.(sceneAgent?.session, 'hg/plot-cognition-completed', scope, {
      ...correlation,
      operation: 'none',
      ok: true,
      skipped: true,
    });
    return {
      ok: true,
      skipped: true,
      operation: 'none',
      plan,
      stage: 'none',
      freshAfter: true,
    };
  }

  if (operation === 'none') {
    trace?.emit?.(sceneAgent?.session, 'hg/plot-cognition-completed', scope, {
      ...correlation,
      operation: 'none',
      ok: true,
      skipped: true,
    });
    return {
      ok: true,
      skipped: true,
      operation: 'none',
      plan,
      stage: 'none',
      freshAfter: true,
    };
  }

  if (operation === 'clear_pending') {
    const cleared = await domainApi.clearPlotCognitionPendingWork({ hg_scene_id: hgSceneId });
    const freshAfter = await domainApi.assessPlotCognitionFreshness({ hg_scene_id: hgSceneId });
    trace?.emit?.(sceneAgent?.session, 'hg/plot-cognition-completed', scope, {
      ...correlation,
      operation,
      ok: cleared?.cleared === true,
      fresh_after: freshAfter?.fresh === true,
    });
    return {
      ok: cleared?.cleared === true,
      operation,
      plan,
      stage: 'clear_pending',
      freshAfter: freshAfter?.fresh === true,
    };
  }

  if (operation === 'reconciliation') {
    const finalize = await domainApi.finalizePlotCognitionReconciliation({ hg_scene_id: hgSceneId });
    const freshAfter = await domainApi.assessPlotCognitionFreshness({ hg_scene_id: hgSceneId });
    trace?.emit?.(sceneAgent?.session, 'hg/plot-cognition-completed', scope, {
      ...correlation,
      operation,
      ok: finalize?.accepted === true,
      code: finalize?.code ?? null,
      fresh_after: freshAfter?.fresh === true,
    });
    return {
      ok: finalize?.accepted === true,
      operation,
      plan,
      stage: 'reconciliation',
      finalizeResponse: finalize,
      freshAfter: freshAfter?.fresh === true,
      pendingPreserved: finalize?.accepted !== true,
    };
  }

  if (operation === 'authority_advance') {
    const finalize = await domainApi.finalizePlotCognitionAuthorityAdvance({
      hg_scene_id: hgSceneId,
      source_snapshot: plan.source_snapshot ?? null,
    });
    const freshAfter = await domainApi.assessPlotCognitionFreshness({ hg_scene_id: hgSceneId });
    trace?.emit?.(sceneAgent?.session, 'hg/plot-cognition-completed', scope, {
      ...correlation,
      operation,
      ok: finalize?.accepted === true,
      code: finalize?.code ?? null,
      fresh_after: freshAfter?.fresh === true,
    });
    return {
      ok: finalize?.accepted === true,
      operation,
      plan,
      stage: 'authority_advance',
      finalizeResponse: finalize,
      freshAfter: freshAfter?.fresh === true,
      pendingPreserved: finalize?.accepted !== true,
    };
  }

  if (operation === 'initialization') {
    const initPrepare = await domainApi.preparePlotCognitionInit({
      hg_scene_id: hgSceneId,
      manifest_id: `manifest-plot-init-${inferenceId}`,
    });
    if (!initPrepare?.accepted) {
      trace?.emit?.(sceneAgent?.session, 'hg/plot-cognition-failed', scope, {
        ...correlation,
        operation,
        stage: 'init_prepare',
        reason: initPrepare?.reason ?? 'init_not_eligible',
      });
      return {
        ok: false,
        operation,
        plan,
        stage: 'init_prepare',
        initPrepare,
        pendingPreserved: true,
      };
    }
    let initPayload;
    if (mockInitResponse) {
      initPayload = typeof mockInitResponse === 'string'
        ? JSON.parse(mockInitResponse)
        : mockInitResponse;
    } else {
      const initInferenceId = `${inferenceId}-plot-init`;
      const inferRun = await runEphemeralInference({
        inferenceId: initInferenceId,
        prompt: 'Initialize Plot Cognition overlay. Output JSON proposal only.',
        manifest: {
          contributions: [{
            contribution_id: `${initPrepare.manifest_id}-sources`,
            source_kind: 'active_constraints',
            authority_class: 'derived',
            knowledge_ids: ['plot_cognition:init_sources'],
            priority: 10,
            content: JSON.stringify(initPrepare.source_snapshot ?? {}).slice(0, 8000),
            provenance: {},
          }],
        },
        mockResponses: [],
        modelProfile,
        evidenceContext: {
          ...evidenceContextBase,
          inferenceId: initInferenceId,
          inferenceKind: 'plot_cognition_init',
        },
      });
      if (inferRun.failed) {
        trace?.emit?.(sceneAgent?.session, 'hg/plot-cognition-failed', scope, {
          ...correlation,
          operation,
          stage: 'init_inference',
        });
        return {
          ok: false,
          operation,
          plan,
          stage: 'init_inference',
          pendingPreserved: true,
        };
      }
      try {
        initPayload = typeof inferRun.raw === 'string' ? JSON.parse(inferRun.raw) : inferRun.raw;
      } catch {
        trace?.emit?.(sceneAgent?.session, 'hg/plot-cognition-failed', scope, {
          ...correlation,
          operation,
          stage: 'init_parse',
        });
        return {
          ok: false,
          operation,
          plan,
          stage: 'init_parse',
          pendingPreserved: true,
        };
      }
    }
    const initFinalize = await domainApi.finalizePlotCognitionInit({
      hg_scene_id: hgSceneId,
      proposal: initPayload?.proposal ?? initPayload,
    });
    const freshAfter = await domainApi.assessPlotCognitionFreshness({ hg_scene_id: hgSceneId });
    trace?.emit?.(sceneAgent?.session, 'hg/plot-cognition-completed', scope, {
      ...correlation,
      operation,
      ok: initFinalize?.accepted === true,
      fresh_after: freshAfter?.fresh === true,
    });
    return {
      ok: initFinalize?.accepted === true,
      operation,
      plan,
      stage: 'initialization',
      initFinalize,
      freshAfter: freshAfter?.fresh === true,
      pendingPreserved: initFinalize?.accepted !== true,
    };
  }

  if (operationRequiresInference(operation)) {
    const updateResult = await runPlotCognitionUpdateGeneration({
      domainApi,
      hgSceneId,
      inferenceId,
      runEphemeralInference,
      mockResponse: mockUpdateResponse,
      modelProfile,
      evidenceContextBase,
    });
    const freshAfter = await domainApi.assessPlotCognitionFreshness({ hg_scene_id: hgSceneId });
    trace?.emit?.(sceneAgent?.session, 'hg/plot-cognition-completed', scope, {
      ...correlation,
      operation,
      ok: updateResult.ok === true,
      stage: updateResult.stage ?? null,
      code: updateResult.finalizeResponse?.code ?? null,
      fresh_after: freshAfter?.fresh === true,
    });
    return {
      ok: updateResult.ok === true,
      operation,
      plan,
      stage: updateResult.stage ?? 'semantic_update',
      updateResult,
      freshAfter: freshAfter?.fresh === true,
      pendingPreserved: updateResult.ok !== true,
    };
  }

  trace?.emit?.(sceneAgent?.session, 'hg/plot-cognition-failed', scope, {
    ...correlation,
    operation,
    reason: plan?.reason ?? 'blocked',
  });
  return {
    ok: false,
    operation,
    plan,
    stage: 'blocked',
    pendingPreserved: true,
  };
}

export async function runPostCommitPlotCognitionLifecycle(params) {
  return runPlotCognitionPendingWorkLifecycle({
    ...params,
    inferenceId: params.inferenceId ?? `inf-plot-cog-${crypto.randomUUID()}`,
  });
}

export { buildNoChangeUpdateInference };
