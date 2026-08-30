import assert from 'node:assert/strict';
import test from 'node:test';

import { runInferenceWithContractCorrection } from '../src/lib/contract-correction-substrate.mjs';
import {
  buildMinimalInitProposal,
  buildPlotCognitionInitCorrectionPrompt,
  buildPlotCognitionInitPrompt,
  parsePlotCognitionInitProposal,
  PLOT_COGNITION_INIT_PROPOSAL_SCHEMA,
} from '../src/lib/plot-cognition-init-envelope.mjs';
import {
  buildNoChangeUpdateInference,
  buildPlotCognitionUpdateCorrectionPrompt,
  buildPlotCognitionUpdatePrompt,
  parsePlotCognitionUpdateInference,
  PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA,
} from '../src/lib/plot-cognition-update-envelope.mjs';
import {
  buildEpistemicProjectionEvalCorrectionPrompt,
  buildEpistemicProjectionEvalPrompt,
  parseEpistemicProjectionEvalResult,
  EPISTEMIC_PROJECTION_EVAL_SCHEMA,
} from '../src/plugins/hg-phase-executors/character-epistemic-projection-eval.mjs';
import {
  analyzeLayerBAccounting,
  HARD_BLOCKER_CODES,
  LAYER_B_CHAIN_CEILING,
  LAYER_B_CORRECTION_CEILING,
  LAYER_B_EVAL_CEILING,
  LAYER_B_REGEN_CEILING,
} from '../src/scenario-harness/hard-blockers.mjs';
import { epistemicPass } from '../tests/helpers/plot-cognition-projection-fixtures.mjs';

const INIT_PREPARE = {
  source_snapshot_fingerprint: 'fp-init-1',
  source_snapshot: {
    snapshot_id: 'snap-init-1',
    fingerprint: 'fp-init-1',
    plot_cognition_scope_id: 'scope-authoritative-1',
  },
};

const UPDATE_PREPARE = {
  manifest_id: 'manifest-update',
  authority_source_fingerprint: 'fp-update-1',
  prior_store_revision: 2,
  source_snapshot: {
    snapshot_id: 'snap-update-1',
    plot_cognition_scope_id: 'scope-authoritative-1',
    prior_store_revision: 2,
    authority_source_fingerprint: 'fp-update-1',
    canonical_body: {},
  },
};

function mockRunEphemeralInference(responses) {
  let index = 0;
  return async ({ inferenceId, prompt }) => {
    const raw = responses[index] ?? responses[responses.length - 1];
    index += 1;
    return {
      failed: false,
      raw,
      evidenceId: `evidence-${inferenceId}`,
      prompt,
    };
  };
}

test('init prompt contains exact schema contract', () => {
  const prompt = buildPlotCognitionInitPrompt(INIT_PREPARE);
  assert.ok(prompt.includes(PLOT_COGNITION_INIT_PROPOSAL_SCHEMA));
  assert.ok(prompt.includes('scope-authoritative-1'));
  assert.ok(prompt.includes('plot_cognition_initialize_proposal'));
  assert.ok(prompt.includes('adoption_rationale'));
});

test('update prompt contains exact schema contract and enums', () => {
  const prompt = buildPlotCognitionUpdatePrompt(UPDATE_PREPARE);
  assert.ok(prompt.includes(PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA));
  assert.ok(prompt.includes('accept, revise, reject, no_change'));
  assert.ok(prompt.includes('scope-authoritative-1'));
  assert.ok(prompt.includes('prior_operative_cognition'));
  assert.ok(prompt.includes('no_change'));
  assert.ok(prompt.includes('replan_required'));
  assert.ok(prompt.includes('invalidation replan'));
  assert.ok(prompt.includes('not keyword lists'));
});

test('update prompt does not prescribe deterministic trigger mechanisms', () => {
  const prompt = buildPlotCognitionUpdatePrompt(UPDATE_PREPARE);
  assert.ok(!/\bregex\b/i.test(prompt));
  assert.ok(!/\bkeyword trigger\b/i.test(prompt));
  assert.ok(!prompt.includes('treaty'));
  assert.ok(!prompt.includes('T2-R'));
});

test('update prompt distinguishes package revise from strategic revision', () => {
  const prompt = buildPlotCognitionUpdatePrompt(UPDATE_PREPARE);
  assert.ok(prompt.includes('does NOT mean the old strategy should be revised'));
  assert.ok(prompt.includes('generated JSON package is incomplete'));
  assert.ok(prompt.includes('MAY coexist with replan_required=true'));
});

test('update prompt requires complete replan envelope when replan_required', () => {
  const prompt = buildPlotCognitionUpdatePrompt(UPDATE_PREPARE);
  assert.ok(prompt.includes('complete replan_proposal and replan_evaluation'));
  assert.ok(prompt.includes('replan_evaluation.overall_result must be accept'));
});

test('update correction explains replan envelope repair without deciding semantics', () => {
  const prompt = buildPlotCognitionUpdateCorrectionPrompt({
    priorRaw: JSON.stringify({
      schema: PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA,
      update_proposal: { replan_required: true },
      update_evaluation: { overall_result: 'revise' },
    }),
    structuralError: 'replan_required_without_accept',
    context: UPDATE_PREPARE,
  });
  assert.ok(prompt.includes('replan_required_without_accept'));
  assert.ok(prompt.includes('complete replan_proposal and replan_evaluation'));
  assert.ok(prompt.includes('not revise'));
  assert.ok(prompt.includes('Do not flip replan_required'));
  assert.ok(!prompt.includes('you must replan'));
  assert.ok(!prompt.includes('set replan_required to true'));
});

test('update parser still rejects replan_required without accepted replan envelope', () => {
  const parsed = parsePlotCognitionUpdateInference(
    JSON.stringify({
      schema: PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA,
      update_proposal: {
        schema: 'hg_plot_cognition_update_proposal_v1',
        proposal_id: 'p1',
        source_snapshot_id: 'snap-update-1',
        source_snapshot_fingerprint: 'fp-update-1',
        plot_cognition_scope_id: 'scope-authoritative-1',
        prior_store_revision: 2,
        assimilation_rationale: 'Invalidation requires replan.',
        replan_required: true,
      },
      update_evaluation: {
        schema: 'hg_plot_cognition_update_eval_v1',
        evaluation_id: 'e1',
        proposal_id: 'p1',
        overall_result: 'revise',
        revision_brief: 'needs work',
      },
    }),
    UPDATE_PREPARE,
  );
  assert.equal(parsed.ok, false);
  assert.equal(parsed.error, 'replan_required_without_accept');
});

test('update parser accepts replan_required with accept update and accept replan evaluation', () => {
  const parsed = parsePlotCognitionUpdateInference(
    JSON.stringify({
      schema: PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA,
      update_proposal: {
        schema: 'hg_plot_cognition_update_proposal_v1',
        proposal_id: 'p-replan',
        source_snapshot_id: 'snap-update-1',
        source_snapshot_fingerprint: 'fp-update-1',
        plot_cognition_scope_id: 'scope-authoritative-1',
        prior_store_revision: 2,
        assimilation_rationale: 'Prior direction invalidated; replan required.',
        replan_required: true,
      },
      update_evaluation: {
        schema: 'hg_plot_cognition_update_eval_v1',
        evaluation_id: 'e-replan',
        proposal_id: 'p-replan',
        overall_result: 'accept',
      },
      replan_proposal: {
        schema: 'hg_plot_cognition_replan_proposal_v1',
        proposal_id: 'rp1',
        source_snapshot_id: 'snap-update-1',
        source_snapshot_fingerprint: 'fp-update-1',
        plot_cognition_scope_id: 'scope-authoritative-1',
        prior_store_revision: 2,
        replan_rationale: 'Replace invalidated pursuit.',
        trigger_summary: 'Authority invalidated prior direction.',
        goals: [],
        pressures: [],
      },
      replan_evaluation: {
        schema: 'hg_plot_cognition_replan_eval_v1',
        evaluation_id: 're1',
        proposal_id: 'rp1',
        overall_result: 'accept',
      },
    }),
    UPDATE_PREPARE,
  );
  assert.equal(parsed.ok, true);
  assert.equal(parsed.result.update_proposal.replan_required, true);
  assert.equal(parsed.result.update_evaluation.overall_result, 'accept');
  assert.equal(parsed.result.replan_evaluation.overall_result, 'accept');
});

test('Layer-B prompt contains exact verdict contract', () => {
  const prompt = buildEpistemicProjectionEvalPrompt();
  assert.ok(prompt.includes(EPISTEMIC_PROJECTION_EVAL_SCHEMA));
  assert.ok(prompt.includes('pass, withhold, rewrite_required, evaluator_unavailable'));
  assert.ok(prompt.includes('allowed, permitted, leakage, or epistemic_leakage'));
});

test('init parser rejects alternate wrapper and schema', () => {
  const malformed = JSON.stringify({
    plot_cognition_initialize_proposal: {
      schema: 'hg_plot_cognition_initialize_proposal_v1',
      plot_cognition_scope_id: 'scope-authoritative-1',
    },
  });
  const parsed = parsePlotCognitionInitProposal(malformed, INIT_PREPARE);
  assert.equal(parsed.ok, false);
  assert.ok(parsed.error.includes('forbidden_wrapper'));
});

test('init parser accepts conformant proposal with authoritative scope', () => {
  const parsed = parsePlotCognitionInitProposal(buildMinimalInitProposal(INIT_PREPARE), INIT_PREPARE);
  assert.equal(parsed.ok, true);
  assert.equal(parsed.result.plot_cognition_scope_id, 'scope-authoritative-1');
});

test('init parser rejects scope mismatch', () => {
  const bad = JSON.stringify({
    schema: PLOT_COGNITION_INIT_PROPOSAL_SCHEMA,
    proposal_id: 'p1',
    source_snapshot_id: 'snap-init-1',
    source_snapshot_fingerprint: 'fp-init-1',
    plot_cognition_scope_id: 'wrong-scope',
    adoption_rationale: 'test',
  });
  const parsed = parsePlotCognitionInitProposal(bad, INIT_PREPARE);
  assert.equal(parsed.ok, false);
  assert.equal(parsed.error, 'plot_cognition_scope_id_mismatch');
});

test('update parser continues rejecting malformed envelope', () => {
  const parsed = parsePlotCognitionUpdateInference(
    JSON.stringify({ update_evaluation: { overall_result: 'no_change' }, update_proposal: { replan_required: false } }),
    UPDATE_PREPARE,
  );
  assert.equal(parsed.ok, false);
  assert.equal(parsed.error, 'schema_mismatch');
});

test('Layer-B parser rejects synonym fields', () => {
  assert.equal(parseEpistemicProjectionEvalResult('{"leakage": false}').ok, false);
  assert.equal(parseEpistemicProjectionEvalResult('{"allowed": false}').ok, false);
  assert.equal(parseEpistemicProjectionEvalResult('{"permitted": false}').ok, false);
  assert.equal(parseEpistemicProjectionEvalResult('{"epistemic_leakage": true}').ok, false);
});

test('Layer-B parser accepts conformant pass verdict', () => {
  const parsed = parseEpistemicProjectionEvalResult(epistemicPass());
  assert.equal(parsed.ok, true);
  assert.equal(parsed.result.verdict, 'pass');
});

test('correction request contains prior response and structural error', () => {
  const prompt = buildPlotCognitionInitCorrectionPrompt({
    priorRaw: '{"bad": true}',
    structuralError: 'schema_mismatch',
    context: INIT_PREPARE,
  });
  assert.ok(prompt.includes('Previous response'));
  assert.ok(prompt.includes('schema_mismatch'));
  assert.ok(prompt.includes(PLOT_COGNITION_INIT_PROPOSAL_SCHEMA));
  assert.ok(prompt.includes('Preserve the semantic judgment'));
});

test('update correction request contains required contract', () => {
  const prompt = buildPlotCognitionUpdateCorrectionPrompt({
    priorRaw: '{"partial": true}',
    structuralError: 'schema_mismatch',
    context: UPDATE_PREPARE,
  });
  assert.ok(prompt.includes(PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA));
});

test('Layer-B correction request contains required contract', () => {
  const prompt = buildEpistemicProjectionEvalCorrectionPrompt({
    priorRaw: '{"leakage": false}',
    structuralError: 'forbidden_synonym_field:leakage',
  });
  assert.ok(prompt.includes(EPISTEMIC_PROJECTION_EVAL_SCHEMA));
});

test('contract correction succeeds on second conformant response', async () => {
  const conformant = buildMinimalInitProposal(INIT_PREPARE);
  const run = mockRunEphemeralInference([
    JSON.stringify({ plot_cognition_initialize_proposal: { schema: 'wrong' } }),
    conformant,
  ]);
  const result = await runInferenceWithContractCorrection({
    runEphemeralInference: run,
    primaryInferenceId: 'inf-init-primary',
    primaryInferenceKind: 'plot_cognition_init',
    correctionInferenceKind: 'plot_cognition_init_contract_correction',
    buildPrimaryPrompt: () => buildPlotCognitionInitPrompt(INIT_PREPARE),
    buildCorrectionPrompt: buildPlotCognitionInitCorrectionPrompt,
    parseFn: parsePlotCognitionInitProposal,
    parseContext: INIT_PREPARE,
    manifest: { contributions: [] },
    maxCorrections: 1,
  });
  assert.equal(result.ok, true);
  assert.equal(result.correctionUsed, true);
  assert.equal(result.inferRuns.length, 2);
  assert.equal(result.lineage.primary.inference_id, 'inf-init-primary');
  assert.ok(result.lineage.correction.inference_id.includes('contract-correction'));
});

test('second malformed correction fails closed', async () => {
  const run = mockRunEphemeralInference([
    '{"bad":1}',
    '{"still":"bad"}',
  ]);
  const result = await runInferenceWithContractCorrection({
    runEphemeralInference: run,
    primaryInferenceId: 'inf-init-fail',
    primaryInferenceKind: 'plot_cognition_init',
    correctionInferenceKind: 'plot_cognition_init_contract_correction',
    buildPrimaryPrompt: () => 'primary',
    buildCorrectionPrompt: buildPlotCognitionInitCorrectionPrompt,
    parseFn: parsePlotCognitionInitProposal,
    parseContext: INIT_PREPARE,
    manifest: { contributions: [] },
    maxCorrections: 1,
  });
  assert.equal(result.ok, false);
  assert.equal(result.correctionUsed, true);
  assert.equal(result.inferRuns.length, 2);
});

test('conformant first-pass incurs no correction call', async () => {
  const conformant = buildMinimalInitProposal(INIT_PREPARE);
  let callCount = 0;
  const run = async () => {
    callCount += 1;
    return { failed: false, raw: conformant, evidenceId: 'ev-1' };
  };
  const result = await runInferenceWithContractCorrection({
    runEphemeralInference: run,
    primaryInferenceId: 'inf-init-ok',
    primaryInferenceKind: 'plot_cognition_init',
    correctionInferenceKind: 'plot_cognition_init_contract_correction',
    buildPrimaryPrompt: () => 'primary',
    buildCorrectionPrompt: buildPlotCognitionInitCorrectionPrompt,
    parseFn: parsePlotCognitionInitProposal,
    parseContext: INIT_PREPARE,
    manifest: { contributions: [] },
    maxCorrections: 1,
  });
  assert.equal(result.ok, true);
  assert.equal(result.correctionUsed, false);
  assert.equal(callCount, 1);
});

test('update conformant no_change passes without correction', () => {
  const parsed = parsePlotCognitionUpdateInference(
    buildNoChangeUpdateInference(UPDATE_PREPARE),
    UPDATE_PREPARE,
  );
  assert.equal(parsed.ok, true);
});

test('correction uses distinct inference kinds', async () => {
  const kinds = [];
  const run = async ({ evidenceContext }) => {
    kinds.push(evidenceContext?.inferenceKind);
    return {
      failed: false,
      raw: kinds.length === 1 ? '{"bad":1}' : buildMinimalInitProposal(INIT_PREPARE),
      evidenceId: `ev-${kinds.length}`,
    };
  };
  await runInferenceWithContractCorrection({
    runEphemeralInference: run,
    primaryInferenceId: 'inf-kind-test',
    primaryInferenceKind: 'plot_cognition_init',
    correctionInferenceKind: 'plot_cognition_init_contract_correction',
    buildPrimaryPrompt: () => 'p',
    buildCorrectionPrompt: buildPlotCognitionInitCorrectionPrompt,
    parseFn: parsePlotCognitionInitProposal,
    parseContext: INIT_PREPARE,
    manifest: { contributions: [] },
    maxCorrections: 1,
    evidenceContextBase: {},
  });
  assert.deepEqual(kinds, ['plot_cognition_init', 'plot_cognition_init_contract_correction']);
});

test('Layer-B accounting: correction does not count as semantic eval', () => {
  const calls = [
    { inference_kind: 'plot_cognition_epistemic_eval' },
    { inference_kind: 'plot_cognition_epistemic_eval_contract_correction' },
    { inference_kind: 'character_advisory_generation' },
    { inference_kind: 'plot_cognition_epistemic_eval' },
    { inference_kind: 'plot_cognition_epistemic_eval_contract_correction' },
  ];
  const analysis = analyzeLayerBAccounting(calls);
  assert.equal(analysis.evalCount, 2);
  assert.equal(analysis.correctionCount, 2);
  assert.equal(analysis.regenCount, 1);
  assert.equal(analysis.layerBCount, 5);
  assert.equal(analysis.violations.length, 0);
});

test('Layer-B absolute chain ceiling is 5', () => {
  assert.equal(LAYER_B_CHAIN_CEILING, 5);
  assert.equal(LAYER_B_EVAL_CEILING, 2);
  assert.equal(LAYER_B_REGEN_CEILING, 1);
  assert.equal(LAYER_B_CORRECTION_CEILING, 2);
});

test('Layer-B chain exceeding 5 is blocked', () => {
  const calls = [
    { inference_kind: 'plot_cognition_epistemic_eval' },
    { inference_kind: 'plot_cognition_epistemic_eval_contract_correction' },
    { inference_kind: 'character_advisory_generation' },
    { inference_kind: 'plot_cognition_epistemic_eval' },
    { inference_kind: 'plot_cognition_epistemic_eval_contract_correction' },
    { inference_kind: 'plot_cognition_epistemic_eval' },
  ];
  const analysis = analyzeLayerBAccounting(calls);
  assert.ok(analysis.violations.some((v) => v.code === HARD_BLOCKER_CODES.INFERENCE_CHAIN_EXCEEDED));
});

test('correction does not consume regeneration budget', () => {
  const calls = [
    { inference_kind: 'plot_cognition_epistemic_eval_contract_correction' },
    { inference_kind: 'plot_cognition_epistemic_eval_contract_correction' },
  ];
  const analysis = analyzeLayerBAccounting(calls);
  assert.equal(analysis.regenCount, 0);
  assert.equal(analysis.evalCount, 0);
});

test('evidence lineage links primary to correction', async () => {
  const run = mockRunEphemeralInference(['{"bad":1}', buildMinimalInitProposal(INIT_PREPARE)]);
  const result = await runInferenceWithContractCorrection({
    runEphemeralInference: run,
    primaryInferenceId: 'inf-lineage',
    primaryInferenceKind: 'plot_cognition_init',
    correctionInferenceKind: 'plot_cognition_init_contract_correction',
    buildPrimaryPrompt: () => 'p',
    buildCorrectionPrompt: buildPlotCognitionInitCorrectionPrompt,
    parseFn: parsePlotCognitionInitProposal,
    parseContext: INIT_PREPARE,
    manifest: { contributions: [] },
    maxCorrections: 1,
  });
  assert.equal(result.lineage.primary.evidence_id, 'evidence-inf-lineage');
  assert.equal(result.lineage.correction.parent_inference_id, 'inf-lineage');
  assert.equal(result.lineage.correction.structural_error, result.lineage.primary.parse_error);
});

test('maxCorCorrections=0 fails closed without correction attempt', async () => {
  let calls = 0;
  const run = async () => {
    calls += 1;
    return { failed: false, raw: '{"bad":1}', evidenceId: 'ev' };
  };
  const result = await runInferenceWithContractCorrection({
    runEphemeralInference: run,
    primaryInferenceId: 'inf-no-correct',
    primaryInferenceKind: 'plot_cognition_init',
    correctionInferenceKind: 'plot_cognition_init_contract_correction',
    buildPrimaryPrompt: () => 'p',
    buildCorrectionPrompt: buildPlotCognitionInitCorrectionPrompt,
    parseFn: parsePlotCognitionInitProposal,
    parseContext: INIT_PREPARE,
    manifest: { contributions: [] },
    maxCorrections: 0,
  });
  assert.equal(result.ok, false);
  assert.equal(calls, 1);
});
