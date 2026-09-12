import {
  buildEpistemicProjectionEvalCorrectionPrompt,
  buildEpistemicProjectionEvalPrompt,
  parseEpistemicProjectionEvalResult,
} from './character-epistemic-projection-eval.mjs';
import { parseJsonObject } from '../../lib/inference-utils.mjs';
import { bridgeManifestFromHostPrepare } from '../../lib/bridge-manifest.mjs';
import { runInferenceWithContractCorrection } from '../../lib/contract-correction-substrate.mjs';

function orderedBatchItems(prepare) {
  const items = Array.isArray(prepare?.items) ? [...prepare.items] : [];
  return items.sort((a, b) => String(a.candidate_id).localeCompare(String(b.candidate_id)));
}

async function runEpistemicEval({
  api,
  runEphemeralInference,
  scope,
  hgSceneId,
  hgRoundId,
  inferenceId,
  evaluationPassId,
  manifestContributions,
  modelProfile,
  mockResponse,
  parentEvidenceId = null,
  evaluationAttempt = 1,
}) {
  const attemptSuffix = evaluationAttempt > 1 ? `-attempt-${evaluationAttempt}` : '';
  const baseInferenceId = `${inferenceId}-epistemic-${evaluationPassId}${attemptSuffix}`;
  const mockList = mockResponse
    ? (Array.isArray(mockResponse) ? mockResponse : [mockResponse])
    : [];

  const inference = await runInferenceWithContractCorrection({
    runEphemeralInference,
    primaryInferenceId: baseInferenceId,
    primaryInferenceKind: 'plot_cognition_epistemic_eval',
    correctionInferenceKind: 'plot_cognition_epistemic_eval_contract_correction',
    buildPrimaryPrompt: () => buildEpistemicProjectionEvalPrompt(),
    buildCorrectionPrompt: buildEpistemicProjectionEvalCorrectionPrompt,
    parseFn: parseEpistemicProjectionEvalResult,
    parseContext: null,
    manifest: { contributions: manifestContributions },
    mockResponses: mockList,
    modelProfile,
    evidenceContextBase: {
      ...scope,
      hgSceneId,
      hgRoundId,
      inferenceId,
      evaluationPassId,
      parentInferenceId: parentEvidenceId ?? inferenceId,
      evaluationAttempt,
    },
    maxCorrections: 1,
  });

  const inferRun = inference.inferRun;
  const lineage = inference.lineage ?? null;

  if (!inference.ok) {
    return {
      ok: false,
      verdict: 'evaluator_unavailable',
      semantic: {
        verdict: 'evaluator_unavailable',
        rationale: inference.structuralError ?? inference.parsed?.error ?? 'malformed_evaluator_output',
        forensic_rationale: inference.structuralError ?? inference.parsed?.error ?? 'malformed_evaluator_output',
        leak_indicators: [],
      },
      evidenceId: inferRun?.evidenceId ?? null,
      raw: inferRun?.raw ?? null,
      contractLineage: lineage,
      correctionUsed: inference.correctionUsed === true,
      inferRuns: inference.inferRuns ?? [],
    };
  }

  return {
    ok: true,
    verdict: inference.parsed.result.verdict,
    semantic: inference.parsed.result,
    evidenceId: inferRun?.evidenceId ?? null,
    raw: inferRun?.raw ?? null,
    contractLineage: lineage,
    correctionUsed: inference.correctionUsed === true,
    inferRuns: inference.inferRuns ?? [],
  };
}

async function runRegenerationGeneration({
  runEphemeralInference,
  scope,
  hgSceneId,
  hgRoundId,
  inferenceId,
  evaluationPassId,
  regenerationPrepareId,
  generatorManifest,
  modelProfile,
  mockResponse,
  parentEvidenceId,
}) {
  const inferRun = await runEphemeralInference({
    inferenceId: `${inferenceId}-advisory-gen-${evaluationPassId}`,
    prompt: 'Regenerate Character advisory text per the bounded manifest. Output plain revised text only.',
    manifest: generatorManifest,
    mockResponses: mockResponse ? [mockResponse] : [],
    modelProfile,
    evidenceContext: {
      ...scope,
      hgSceneId,
      hgRoundId,
      inferenceId,
      inferenceKind: 'character_advisory_generation',
      evaluationPassId,
      regenerationPrepareId,
      parentInferenceId: parentEvidenceId ?? inferenceId,
    },
  });
  if (inferRun.failed) {
    return { ok: false, text: '', evidenceId: inferRun.evidenceId ?? null };
  }
  const raw = String(inferRun.raw ?? '').trim();
  let text = raw;
  try {
    const parsed = parseJsonObject(raw);
    text = String(parsed?.text ?? parsed?.candidate_text ?? parsed?.revised_text ?? raw).trim();
  } catch {
    text = raw;
  }
  if (!text) {
    return { ok: false, text: '', evidenceId: inferRun.evidenceId ?? null };
  }
  return { ok: true, text, evidenceId: inferRun.evidenceId ?? null };
}

export async function runCharacterProjectionLifecycle({
  api,
  runEphemeralInference,
  scope,
  hgSceneId,
  hgRoundId,
  characterId,
  inferenceId,
  turnIndex,
  modelProfile = null,
  mockEpistemicResponses = [],
  mockRegenerationResponses = [],
}) {
  const prepare = await api.preparePlotCognitionProjection({
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    character_id: characterId,
    manifest_id: `manifest-proj-${inferenceId}`,
  });
  if (!prepare?.accepted) {
    return { ok: false, stage: 'prepare', prepare, finalized: null, callLog: ['prepare'] };
  }
  const batchId = String(prepare.batch_id ?? prepare.batch?.batch_id ?? '');
  const items = orderedBatchItems(prepare);
  const callLog = ['prepare'];
  if (!items.length) {
    const finalizeEmpty = await api.finalizePlotCognitionProjection({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      batch_id: batchId,
      use_registered_results: true,
    });
    callLog.push('finalize');
    if (!finalizeEmpty?.accepted) {
      return { ok: false, stage: 'finalize', prepare, finalized: null, callLog };
    }
    return {
      ok: true,
      stage: 'complete',
      prepare,
      finalized: {
        batch_id: batchId,
        binding_digest: finalizeEmpty.binding?.binding_digest ?? prepare.batch?.binding_digest,
        binding: finalizeEmpty.binding ?? null,
        contributions: finalizeEmpty.contributions ?? [],
        forensic: finalizeEmpty.forensic ?? null,
      },
      callLog,
    };
  }

  let mockEpistemicIndex = 0;
  let mockRegenIndex = 0;
  for (const item of items) {
    const evaluationPassId = String(item.evaluation_pass_id);
    const candidateId = String(item.candidate_id);
    const manifest = prepare.evaluator_manifests?.[evaluationPassId] ?? [];
    const reuseResolve = await api.resolvePlotCognitionLayerBEpistemicReuse({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      batch_id: batchId,
      evaluation_pass_id: evaluationPassId,
      evaluation_attempt: 1,
    });
    callLog.push(`resolve_layer_b:${evaluationPassId}:1`);
    let firstEval;
    if (reuseResolve?.accepted && reuseResolve.action === 'reuse' && reuseResolve.semantic) {
      firstEval = {
        ok: true,
        verdict: reuseResolve.semantic.verdict ?? 'pass',
        semantic: reuseResolve.semantic,
        evidenceId: reuseResolve.prior_inference_evidence_id ?? null,
        raw: null,
        contractLineage: null,
        correctionUsed: false,
        inferRuns: [],
        reused: true,
        reuseKeyDigest: reuseResolve.reuse_key_digest ?? null,
      };
      callLog.push(`reuse:${evaluationPassId}:1`);
    } else {
      firstEval = await runEpistemicEval({
        api,
        runEphemeralInference,
        scope,
        hgSceneId,
        hgRoundId,
        inferenceId,
        evaluationPassId,
        manifestContributions: manifest,
        modelProfile,
        mockResponse: mockEpistemicResponses[mockEpistemicIndex++] ?? null,
      });
      callLog.push(`eval:${evaluationPassId}:1`);
    }
    const registerFirst = await api.registerPlotCognitionProjectionSemanticResult({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      batch_id: batchId,
      evaluation_pass_id: evaluationPassId,
      candidate_id: candidateId,
      evaluation_attempt: 1,
      inference_evidence_id: firstEval.evidenceId,
      semantic: firstEval.semantic,
    });
    callLog.push(`register:${evaluationPassId}:1`);
    if (!registerFirst?.accepted) {
      return { ok: false, stage: 'register_first', prepare, finalized: null, callLog };
    }

    if (firstEval.verdict === 'rewrite_required') {
      const regenPrepare = await api.preparePlotCognitionProjectionRegeneration({
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        batch_id: batchId,
        evaluation_pass_id: evaluationPassId,
      });
      callLog.push(`regen_prepare:${evaluationPassId}`);
      if (!regenPrepare?.accepted) {
        return { ok: false, stage: 'regen_prepare', prepare, finalized: null, callLog };
      }
      const generation = await runRegenerationGeneration({
        runEphemeralInference,
        scope,
        hgSceneId,
        hgRoundId,
        inferenceId,
        evaluationPassId,
        regenerationPrepareId: regenPrepare.regeneration_prepare_id,
        generatorManifest: bridgeManifestFromHostPrepare(
          regenPrepare,
          regenPrepare.generator_manifest?.contributions ?? [],
        ),
        modelProfile,
        mockResponse: mockRegenerationResponses[mockRegenIndex++] ?? null,
        parentEvidenceId: firstEval.evidenceId,
      });
      callLog.push(`regen_infer:${evaluationPassId}`);
      if (!generation.ok) {
        return { ok: false, stage: 'regen_infer', prepare, finalized: null, callLog };
      }
      const regenFinalize = await api.finalizePlotCognitionProjectionRegeneration({
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        batch_id: batchId,
        evaluation_pass_id: evaluationPassId,
        regeneration_prepare_id: regenPrepare.regeneration_prepare_id,
        candidate_id: candidateId,
        regenerated_text: generation.text,
        generator_inference_evidence_id: generation.evidenceId,
      });
      callLog.push(`regen_finalize:${evaluationPassId}`);
      if (!regenFinalize?.accepted) {
        return { ok: false, stage: 'regen_finalize', prepare, finalized: null, callLog };
      }
      const secondManifest = regenFinalize.second_pass_evaluator_manifest ?? [];
      const secondEval = await runEpistemicEval({
        api,
        runEphemeralInference,
        scope,
        hgSceneId,
        hgRoundId,
        inferenceId,
        evaluationPassId,
        manifestContributions: secondManifest,
        modelProfile,
        mockResponse: mockEpistemicResponses[mockEpistemicIndex++] ?? null,
        parentEvidenceId: generation.evidenceId,
        evaluationAttempt: 2,
      });
      callLog.push(`eval:${evaluationPassId}:2`);
      const registerSecond = await api.registerPlotCognitionProjectionSemanticResult({
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        batch_id: batchId,
        evaluation_pass_id: evaluationPassId,
        candidate_id: candidateId,
        evaluation_attempt: 2,
        inference_evidence_id: secondEval.evidenceId,
        semantic: secondEval.semantic,
      });
      callLog.push(`register:${evaluationPassId}:2`);
      if (!registerSecond?.accepted) {
        return { ok: false, stage: 'register_second', prepare, finalized: null, callLog };
      }
    }
  }

  const finalize = await api.finalizePlotCognitionProjection({
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    batch_id: batchId,
    use_registered_results: true,
  });
  callLog.push('finalize');
  if (!finalize?.accepted) {
    return { ok: false, stage: 'finalize', prepare, finalized: null, callLog };
  }
  return {
    ok: true,
    stage: 'complete',
    prepare,
    finalized: {
      batch_id: batchId,
      binding_digest: finalize.binding?.binding_digest ?? prepare.batch?.binding_digest,
      binding: finalize.binding ?? null,
      contributions: finalize.contributions ?? [],
      forensic: finalize.forensic ?? null,
    },
    callLog,
  };
}
