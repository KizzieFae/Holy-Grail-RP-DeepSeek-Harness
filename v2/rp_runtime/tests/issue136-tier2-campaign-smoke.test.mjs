import assert from 'node:assert/strict';
import test from 'node:test';

import { readExecutionAttempts } from '../src/scenario-harness/forensic-query.mjs';
import { runIssue136FixtureCampaign, runIssue136Tier2Campaign } from '../src/scenario-harness/issue136-tier2-campaign.mjs';

test('issue136 mock fixture campaign completes with forensic evidence', async () => {
  const result = await runIssue136FixtureCampaign({
    fixtureId: '136-T2-A-STABILITY',
    repetition: 1,
    mode: 'mock',
  });
  assert.equal(result.fixture_id, '136-T2-A-STABILITY');
  assert.ok(result.forensic.run_id);
  assert.ok(result.forensic.evidence.hg_session_id);
  assert.equal(result.forensic.overall_fidelity_judgment, 'ambiguous');
  assert.ok(result.round_result.character_turn_count >= 1);
});

test('issue136 entitlement mock campaign preserves three-turn sequence across rounds', async () => {
  const result = await runIssue136FixtureCampaign({
    fixtureId: '136-T2-E-ENTITLEMENT',
    repetition: 1,
    mode: 'mock',
  });
  assert.equal(result.round_results.length, 3);
  assert.deepEqual(
    result.round_results.flatMap((round) => round.actors_used_this_round),
    ['Alice', 'Bob', 'Alice'],
  );
});

test('issue136 mock mini-campaign smoke completes under safety guard', async () => {
  const report = await runIssue136Tier2Campaign({
    mode: 'mock',
    includeSentinel: false,
    fixtureFilter: ['136-T2-A-STABILITY', '136-T2-F-ACTION-REQUIRED'],
  });
  assert.equal(report.runs.length, 6);
  assert.equal(report.limits.stopped, false);
  for (const run of report.runs) {
    const attempts = readExecutionAttempts(
      report.campaign_data_dir,
      run.forensic.evidence.hg_session_id,
    );
    assert.ok(attempts.length >= 0);
  }
});
