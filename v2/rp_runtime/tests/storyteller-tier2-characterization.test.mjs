import assert from 'node:assert/strict';
import test from 'node:test';

import { classifyReplanJudgment, summarizePhaseDMetrics } from '../src/scenario-harness/phase-d-analysis.mjs';
import { loadTier2TruthFixture, listTruthFixtures } from '../src/scenario-harness/fixture-truth.mjs';
import {
  estimatePhaseDCallCeiling,
  PHASE_D_CASES,
  PHASE_D_ESTIMATED_CALLS,
  PHASE_D_INFERENCE_CEILING,
} from '../src/scenario-harness/tier2-characterization.mjs';

test('tier2 truth fixtures load', () => {
  const ids = listTruthFixtures(2);
  assert.ok(ids.length >= 8);
  for (const id of ids) {
    const truth = loadTier2TruthFixture(id);
    assert.ok(truth.fixture_id);
    assert.ok(truth.scenario_id);
  }
});

test('phase D call ceiling stays within governance maximum', () => {
  const estimate = estimatePhaseDCallCeiling();
  assert.equal(estimate.ceiling, PHASE_D_INFERENCE_CEILING);
  assert.equal(PHASE_D_INFERENCE_CEILING, 40);
  assert.ok(estimate.estimated <= PHASE_D_INFERENCE_CEILING);
  assert.equal(estimate.estimated, PHASE_D_ESTIMATED_CALLS);
  assert.equal(PHASE_D_CASES.length, 8);
});

test('classifyReplanJudgment marks likely missed replan', () => {
  const truth = loadTier2TruthFixture('t2-r1-treaty-breach');
  const result = classifyReplanJudgment(truth, {
    replan_required: false,
    overall_result: 'no_change',
    replan_committed: false,
  });
  assert.equal(result.label, 'likely_missed_replan');
});

test('classifyReplanJudgment marks defensible no replan for control', () => {
  const truth = loadTier2TruthFixture('t2-r4-viable-control');
  const result = classifyReplanJudgment(truth, {
    replan_required: false,
    overall_result: 'no_change',
    replan_committed: false,
  });
  assert.equal(result.label, 'defensible_no_replan');
});

test('summarizePhaseDMetrics aggregates latency and replan labels', () => {
  const summary = summarizePhaseDMetrics([
    {
      case_id: 'T2-R1',
      result: {
        phase_durations_ms: { total: 1000 },
        campaign: {
          live_inference_summary: {
            calls: [{ live: true, inference_kind: 'plot_cognition_update', duration_ms: 500 }],
          },
        },
        characterization: {
          semantic: { label: 'likely_missed_replan' },
        },
      },
      blockerAnalysis: { layer_b_accounting: { correctionCount: 0, regenCount: 0 } },
    },
    {
      case_id: 'T2-R4',
      result: {
        phase_durations_ms: { total: 2000 },
        campaign: {
          live_inference_summary: {
            calls: [{ live: true, inference_kind: 'storyteller_certification_eval', duration_ms: 300 }],
          },
        },
        characterization: {
          semantic: { label: 'defensible_no_replan' },
        },
      },
      blockerAnalysis: { layer_b_accounting: { correctionCount: 0, regenCount: 0 } },
    },
  ]);
  assert.equal(summary.live_calls, 2);
  assert.equal(summary.replan_characterization.missed_replan_count, 1);
  assert.equal(summary.concurrency_assessment.determination, 'NO CONCURRENCY WORK JUSTIFIED');
});
