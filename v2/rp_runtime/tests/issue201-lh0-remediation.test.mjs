import assert from 'node:assert/strict';
import test from 'node:test';

import { runLh0RemediationValidationSuite } from '../scripts/lib/issue201-lh0-remediation-lib.mjs';
import { runDeterministicValidationSuite } from '../scripts/lib/issue201-lh0-lib.mjs';
import {
  buildLh0FinalizedProjection,
} from '../scripts/lib/issue201-lh0-persistent-store.mjs';
import { validateLh0FinalizedProjectionPackage } from '../scripts/lib/issue201-lh0-consumer-evidence.mjs';
import {
  adjudicateLh0ArmSequence,
  buildFirstRunFalsePositiveTrace,
} from '../scripts/lib/issue201-lh0-live-adjudication.mjs';
import { loadLh0FixtureManifest } from '../scripts/lib/issue201-lh0-fixtures.mjs';
import { LH0_ARMS } from '../scripts/lib/issue201-lh0-arms.mjs';

test('LH-0 remediation validation suite passes', () => {
  const report = runLh0RemediationValidationSuite();
  if (!report.all_pass) {
    const failed = report.checks.filter((c) => !c.pass);
    assert.fail(`remediation checks failed: ${failed.map((f) => f.name).join(', ')}`);
  }
  assert.equal(report.readiness_for_corrective_live_execution, true);
});

test('LH-0 apparatus deterministic validation still passes', () => {
  const report = runDeterministicValidationSuite();
  assert.equal(report.all_pass, true);
});

test('LH-C/LH-D projection packages are manifest-valid', () => {
  const fixture = loadLh0FixtureManifest();
  for (const ob of fixture.obligations.filter((o) => !o.negative_control)) {
    const projection = buildLh0FinalizedProjection([ob], {
      batchId: `batch-${ob.obligation_id}`,
      consumer: ob.authorized_consumer === 'director_turn' ? 'director_turn' : 'character_move',
      characterId: 'kizzie',
      hgRoundId: 'hg-round-1',
      turnIndex: 5,
    });
    const result = validateLh0FinalizedProjectionPackage(projection, {
      consumer: ob.authorized_consumer === 'director_turn' ? 'director_turn' : 'character_move',
    });
    assert.equal(result.valid, true);
  }
});

test('first-run false-positive trace fails strengthened adjudication C-H', () => {
  const fixture = loadLh0FixtureManifest();
  const adjudication = adjudicateLh0ArmSequence({
    arm: LH0_ARMS.LH_B,
    turns: buildFirstRunFalsePositiveTrace(),
    lh0Store: buildFirstRunFalsePositiveTrace()[0].lh0_store,
    fixture,
  });
  assert.equal(adjudication.criteria.C_projection.pass, false);
  assert.equal(adjudication.criteria.D_consumer_receipt.pass, false);
  assert.equal(adjudication.criteria.E_consumer_use.pass, false);
  assert.equal(adjudication.criteria.F_decision_influence.pass, false);
  assert.equal(adjudication.criteria.G_consequential_activation.pass, false);
  assert.equal(adjudication.criteria.H_deferred_later_activation.pass, false);
});
