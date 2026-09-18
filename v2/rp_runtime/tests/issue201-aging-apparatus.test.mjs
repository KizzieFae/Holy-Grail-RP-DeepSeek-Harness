import test from 'node:test';
import assert from 'node:assert/strict';

import { buildTrackedItemRegistry, loadAgingFixtureManifest, loadAgingPolicy } from '../scripts/lib/issue201-aging-fixtures.mjs';
import { AGING_STATES } from '../scripts/lib/issue201-aging-contract.mjs';
import { syntheticEstablishedRegistryItem } from '../scripts/lib/issue201-aging-qualification-establishment.mjs';
import {
  classifyTrackedItemAvailability,
  applyAgingObservation,
} from '../scripts/lib/issue201-aging-monitor.mjs';
import { resolvePlayerStimulusForTurn } from '../scripts/lib/issue201-aging-scheduler.mjs';
import { runAgingApparatusQualification, runAgingPantryRegression } from '../scripts/lib/issue201-aging-qualification-lib.mjs';
import { runR5ApparatusQualification } from '../scripts/lib/issue201-r5-qualification-lib.mjs';
import { runLh1bApparatusValidationSuite } from '../scripts/lib/issue201-lh1b-validation-lib.mjs';

test('aging tracked-item registry has three items', () => {
  const reg = buildTrackedItemRegistry();
  assert.equal(reg.tracked_items.length, 3);
  assert.ok(reg.tracked_items.some((t) => t.tracked_item_id === 'TRK-AYA-MEAL-ALCOVE'));
});

test('scheduler withholds gated opportunity when PRESENT_RAW', () => {
  const fixture = loadAgingFixtureManifest();
  const { policy } = loadAgingPolicy();
  const item = fixture.tracked_items[0];
  const obs = classifyTrackedItemAvailability({
    fixture,
    trackedItem: item,
    assembledRequest: {
      contributions: [{
        source_kind: 'recent_scene_transcript',
        content: 'pantry alcove trial week household dining table',
      }],
    },
  });
  assert.equal(obs.availability_state, AGING_STATES.PRESENT_RAW);
  let regItem = syntheticEstablishedRegistryItem(fixture, item.tracked_item_id);
  regItem = applyAgingObservation({
    registryItem: { ...regItem, aging_history: [] },
    observation: obs,
    turnIndex: 14,
  });
  const sched = resolvePlayerStimulusForTurn({
    policy,
    turnIndex: 14,
    registry: { tracked_items: [regItem] },
    lhARegistryItems: [regItem],
  });
  assert.equal(sched.fired, false);
});

test('aging apparatus qualification AG1–AG28 (synthetic)', async () => {
  const report = await runAgingApparatusQualification({ skipPantryRegression: true });
  if (!report.pass) {
    assert.fail(`Aging qualification failed: ${report.failures.join(', ')}`);
  }
  assert.equal(report.gates.length, 28);
});

test('aging pantry T14 regression AG16', { timeout: 2_400_000 }, async () => {
  const pantry = await runAgingPantryRegression();
  assert.equal(pantry.pass, true, JSON.stringify(pantry.t14_observation?.availability_state));
});

test('R5 and LH-1B apparatus regressions', () => {
  assert.equal(runR5ApparatusQualification().pass, true);
  assert.equal(runLh1bApparatusValidationSuite().pass, true);
});
