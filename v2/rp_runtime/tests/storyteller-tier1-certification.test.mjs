import assert from 'node:assert/strict';
import test from 'node:test';

import { runAllTier1Scenarios, TIER1_SCENARIOS } from '../src/scenario-harness/index.mjs';

test('storyteller tier1 harness: registry lists certification core scenarios', () => {
  const ids = TIER1_SCENARIOS.map((scenario) => scenario.id);
  assert.deepEqual(ids, [
    'T1-01', 'T1-02', 'T1-03', 'T1-04', 'T1-05', 'T1-06',
    'T1-07', 'T1-08', 'T1-09', 'T1-10', 'T1-11',
  ]);
  assert.ok(TIER1_SCENARIOS.every((scenario) => scenario.deterministic === true));
});

for (const scenario of TIER1_SCENARIOS) {
  test(`storyteller tier1 harness: ${scenario.id} objective gates pass (deterministic)`, async () => {
    const result = await scenario.run();
    assert.equal(result.schema, 'hg_storyteller_tier1_scenario_result_v1');
    assert.equal(result.scenario_id, scenario.id);
    if (!result.objective_pass) {
      const failed = Object.entries(result.objective_gates ?? {})
        .filter(([, value]) => value.pass !== true)
        .map(([key, value]) => `${key}:${value.detail ?? 'fail'}`);
      assert.fail(`objective gates failed: ${failed.join(', ')}`);
    }
  });
}

test('storyteller tier1 harness: runAllTier1Scenarios returns complete set', async () => {
  const results = await runAllTier1Scenarios();
  assert.equal(results.length, TIER1_SCENARIOS.length);
  assert.ok(results.every((result) => result.objective_pass === true));
});
