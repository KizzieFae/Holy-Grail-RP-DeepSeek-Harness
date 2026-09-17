import test from 'node:test';
import assert from 'node:assert/strict';

import { runLh1bApparatusValidationSuite } from '../scripts/lib/issue201-lh1b-validation-lib.mjs';
import { runLh1bPreflight } from '../scripts/lib/issue201-lh1b-preflight-lib.mjs';
import { runLh1bSyntheticProofs } from '../scripts/lib/issue201-lh1b-synthetic-proofs.mjs';
import { buildLh1bCampaignPlan } from '../scripts/lib/issue201-lh1b-orchestrator.mjs';
import { buildAssembledRequest } from '../src/lib/execution-evidence/assembled-request.mjs';

test('LH-1B apparatus validation suite passes', () => {
  const result = runLh1bApparatusValidationSuite();
  if (!result.pass) {
    const failed = result.checks.filter((c) => !c.pass).map((c) => c.name);
    assert.fail(`LH-1B validation failed: ${failed.join(', ')}`);
  }
  assert.equal(result.pass, true);
  assert.ok(result.frozen_hashes.fixture_hash);
  assert.ok(result.frozen_hashes.causal_design_hash);
});

test('LH-1B preflight ready except live block', () => {
  const preflight = runLh1bPreflight({ blockLive: true });
  assert.equal(preflight.validation.pass, true);
  assert.equal(preflight.stop_conditions.length, 0);
  assert.equal(preflight.live_authorized, false);
});

test('LH-1B synthetic proofs', () => {
  const synthetic = runLh1bSyntheticProofs();
  assert.equal(synthetic.pass, true, synthetic.proofs.filter((p) => !p.pass).map((p) => p.name).join(', '));
});

test('LH-1B campaign plan shape', () => {
  const plan = buildLh1bCampaignPlan();
  assert.equal(plan.sequence_count, 6);
  assert.equal(plan.sequences[4].arm, 'lh_d');
  assert.equal(plan.sequences[4].blind_label, 'S5');
  assert.equal(plan.live_authorized, false);
});

test('provenance preservation in assembled request', () => {
  const request = buildAssembledRequest({
    manifest: {
      contributions: [{
        contribution_id: 'c1',
        source_kind: 'active_constraints',
        authority_class: 'derived',
        priority: 18,
        content: 'trial staff receive only the pantry submaster key',
        provenance: { lh0_obligation_id: 'LH1B-AYA-DEFERRED-KEY' },
        knowledge_ids: ['lh0-obligation:LH1B-AYA-DEFERRED-KEY'],
      }],
    },
    userInstruction: 'test',
    systemPersona: 'test',
    profile: {},
    preserveProvenance: true,
  });
  assert.equal(request.contributions[0].provenance.lh0_obligation_id, 'LH1B-AYA-DEFERRED-KEY');
  assert.deepEqual(request.contributions[0].knowledge_ids, ['lh0-obligation:LH1B-AYA-DEFERRED-KEY']);
});
