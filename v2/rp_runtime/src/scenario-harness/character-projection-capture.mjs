import { parseEpistemicProjectionEvalResult } from '../plugins/hg-phase-executors/character-epistemic-projection-eval.mjs';
import { runCharacterProjectionLifecycle } from '../plugins/hg-phase-executors/plot-cognition-character-projection.mjs';
import {
  createCharacterProjectionCapture,
  extractCandidateTextFromManifest,
  recordCharacterLayerBEval,
} from './production-capture.mjs';

export async function runCharacterProjectionLifecycleCaptured({
  capture: existingCapture = null,
  candidateText = null,
  ...params
}) {
  const capture = existingCapture ?? createCharacterProjectionCapture();
  capture.candidate_text = candidateText ?? capture.candidate_text;
  capture.source_cognition_ref = params.inferenceId ?? null;

  const layerBEvals = [];
  const regenRuns = [];

  const wrappedInference = async (inferParams) => {
    const result = await params.runEphemeralInference(inferParams);
    const kind = inferParams.evidenceContext?.inferenceKind ?? null;
    if (kind === 'plot_cognition_epistemic_eval') {
      const parsed = parseEpistemicProjectionEvalResult(result.raw);
      layerBEvals.push({
        evaluationPassId: inferParams.evidenceContext?.evaluationPassId ?? null,
        evaluationAttempt: inferParams.evidenceContext?.evaluationAttempt ?? 1,
        inferRun: {
          inferenceId: inferParams.inferenceId,
          evidenceId: result.evidenceId ?? null,
          raw: result.raw,
          failed: result.failed === true,
        },
        parsed,
      });
    }
    if (kind === 'character_advisory_generation') {
      regenRuns.push({
        inferenceId: inferParams.inferenceId,
        evidenceId: result.evidenceId ?? null,
        raw: result.raw,
        failed: result.failed === true,
      });
    }
    return result;
  };

  const projection = await runCharacterProjectionLifecycle({
    ...params,
    runEphemeralInference: wrappedInference,
  });

  const prepare = projection.prepare ?? null;
  if (prepare?.evaluator_manifests && !capture.candidate_text) {
    const manifests = Object.values(prepare.evaluator_manifests);
    for (const manifest of manifests) {
      const extracted = extractCandidateTextFromManifest(manifest);
      if (extracted) {
        capture.candidate_text = extracted;
        break;
      }
    }
  }
  if (prepare?.items?.[0]?.candidate_id) {
    capture.candidate_id = prepare.items[0].candidate_id;
  }

  const firstEval = layerBEvals.find((e) => Number(e.evaluationAttempt) <= 1) ?? layerBEvals[0];
  const secondEval = layerBEvals.find((e) => Number(e.evaluationAttempt) > 1);
  if (firstEval) {
    recordCharacterLayerBEval(capture, {
      pass: 'first',
      inferRun: firstEval.inferRun,
      parsed: firstEval.parsed,
    });
  }
  if (secondEval) {
    recordCharacterLayerBEval(capture, {
      pass: 'second',
      inferRun: secondEval.inferRun,
      parsed: secondEval.parsed,
    });
  }
  if (regenRuns[0]) {
    capture.layer_b.regeneration = {
      inference_id: regenRuns[0].inferenceId,
      evidence_id: regenRuns[0].evidenceId,
      raw: regenRuns[0].raw,
      failed: regenRuns[0].failed,
    };
  }

  capture.final_contributions = projection.finalized?.contributions ?? [];
  capture.withheld_reason = (capture.final_contributions ?? []).length === 0
    ? (capture.layer_b.first?.verdict === 'withhold' ? 'semantic_withhold' : 'no_admitted_contribution')
    : null;

  return { projection, capture, layerBEvals, regenRuns };
}
