import test from 'node:test';
import assert from 'node:assert/strict';

import { runR5ApparatusQualification } from '../scripts/lib/issue201-r5-qualification-lib.mjs';
import { runR5RunnerMockQualification } from '../scripts/lib/issue201-r5-runner-qualification-lib.mjs';
import { verifyR5FrozenHashes } from '../scripts/lib/issue201-r5-frozen-hashes.mjs';
import { runLh1bApparatusValidationSuite } from '../scripts/lib/issue201-lh1b-validation-lib.mjs';

test('R5 frozen hashes unchanged', () => {
  const check = verifyR5FrozenHashes();
  assert.equal(check.pass, true, JSON.stringify(check.drift));
});

test('R5 apparatus G1–G8 regression', () => {
  const report = runR5ApparatusQualification();
  assert.equal(report.pass, true, report.failures?.join(', '));
});

test('R5 runner mock qualification through real turn path', { timeout: 2_400_000 }, async () => {
  const qualification = await runR5RunnerMockQualification();
  assert.equal(qualification.sequences?.r5_a1?.turns?.length, 14);
  assert.equal(qualification.sequences?.r5_b1?.turns?.length, 14);
  assert.ok(qualification.t14?.a1?.assembled_request_character?.contributions?.length > 0);
  assert.ok(qualification.t14?.b1?.assembled_request_character?.contributions?.length > 0);
  const rg = qualification.gates.filter((g) => g.name.startsWith('RG'));
  assert.equal(rg.length, 8);
  assert.equal(qualification.apparatus_g1_g8?.pass, true);
  if (!qualification.pass) {
    assert.ok(qualification.failures.length > 0, 'expected named gate failures when qual fails');
  }
});

test('LH-1B apparatus regression', () => {
  const lh1bApparatus = runLh1bApparatusValidationSuite();
  assert.equal(lh1bApparatus.pass, true);
});
