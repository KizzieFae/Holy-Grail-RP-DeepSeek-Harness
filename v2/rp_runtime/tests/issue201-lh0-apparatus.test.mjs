import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  LIFECYCLE_EVENT_TYPES,
  LIFECYCLE_STATES,
  SEAM_FAILURE_CLASSES,
  TRANSPORT_LEVELS,
} from '../scripts/lib/issue201-lifecycle-states.mjs';
import { validateDeferredValidContract, ObligationLedger, createObligationRecord } from '../scripts/lib/issue201-obligation-ledger.mjs';
import {
  LifecycleTracer,
  enforceConsumptionLifecycleConfig,
  transportLevelFromFlags,
} from '../scripts/lib/issue201-lifecycle-tracer.mjs';
import { classifySeamFailure, detectK6ClassCondition } from '../scripts/lib/issue201-seam-classifier.mjs';
import {
  LH0_ARMS,
  buildLh0ArmConfig,
  resolveLh0BeatOptions,
} from '../scripts/lib/issue201-lh0-arms.mjs';
import {
  runValidateApparatus,
  runDeterministicValidationSuite,
  simulateHappyPathObligation,
  simulatePrematureActivation,
  simulateNegativeControl,
  simulateG3dGapPattern,
  validateArmConfigs,
  validateLh0FairnessControls,
  buildLh0ExecutionProtocol,
} from '../scripts/lib/issue201-lh0-lib.mjs';
import { loadLh0FixtureManifest } from '../scripts/lib/issue201-lh0-fixtures.mjs';

test('LH-0 obligation identity survives lifecycle transitions', () => {
  const { ledger, obligationId } = simulateHappyPathObligation({
    arm: LH0_ARMS.LH_B,
    obligationId: 'ID-STABLE-1',
    fixtureId: 'lh0_seam_micro_v1',
  });
  assert.equal(ledger.get(obligationId).obligation_id, 'ID-STABLE-1');
  assert.equal(ledger.toArchaeologyRecord(obligationId).obligation_id, 'ID-STABLE-1');
});

test('LH-0 generation distinguishable from persistence', () => {
  const seam = classifySeamFailure({ generated: true, persisted: false });
  assert.equal(seam.seam, SEAM_FAILURE_CLASSES.PERSISTENCE);
});

test('LH-0 persistence distinguishable from projection', () => {
  const seam = classifySeamFailure({ generated: true, persisted: true, projected: false });
  assert.equal(seam.seam, SEAM_FAILURE_CLASSES.PROJECTION);
});

test('LH-0 projection distinguishable from consumer receipt', () => {
  const seam = classifySeamFailure({
    generated: true, persisted: true, projected: true, consumerReceived: false,
  });
  assert.equal(seam.seam, SEAM_FAILURE_CLASSES.CONSUMPTION);
});

test('LH-0 receipt distinguishable from consumer use', () => {
  const seam = classifySeamFailure({
    generated: true, persisted: true, projected: true, consumerReceived: true, consumerUsed: false,
  });
  assert.equal(seam.seam, SEAM_FAILURE_CLASSES.CONSUMPTION);
});

test('LH-0 use distinguishable from decision influence', () => {
  const seam = classifySeamFailure({
    generated: true, persisted: true, projected: true, consumerReceived: true,
    consumerUsed: true, decisionInfluenced: false,
  });
  assert.equal(seam.seam, SEAM_FAILURE_CLASSES.DECISION_INFLUENCE);
});

test('LH-0 DEFERRED_VALID requires activation predicate and horizon', () => {
  const invalid = validateDeferredValidContract({
    obligation_id: 'x',
    decision_relevant: false,
    deferral_rationale: null,
    activation_condition: {},
  });
  assert.equal(invalid.valid, false);
  const valid = validateDeferredValidContract({
    obligation_id: 'x',
    decision_relevant: true,
    deferral_rationale: 'predicate not yet satisfied',
    activation_condition: { predicate: { type: 'turn_gte', value: 5 }, horizon_turn: 5 },
  });
  assert.equal(valid.valid, true);
});

test('LH-0 later activation links to original obligation', () => {
  const { ledger, obligationId } = simulateHappyPathObligation({
    arm: LH0_ARMS.LH_C,
    obligationId: 'LINK-1',
    fixtureId: 'lh0_seam_micro_v1',
    withDeferral: true,
    deferUntilTurn: 5,
  });
  const arch = ledger.toArchaeologyRecord(obligationId);
  assert.equal(arch.origin_turn, 1);
  assert.equal(arch.activation_turn, 5);
});

test('LH-0 premature activation detected', () => {
  const { ledger } = simulatePrematureActivation({
    arm: LH0_ARMS.LH_B,
    obligationId: 'PREM-1',
    fixtureId: 'lh0_seam_micro_v1',
  });
  assert.equal(ledger.get('PREM-1').lifecycle_state, LIFECYCLE_STATES.ACTIVATED_PREMATURE);
});

test('LH-0 TRACKED_DEAD representable', () => {
  const ledger = new ObligationLedger();
  const tracer = new LifecycleTracer({ ledger, arm: LH0_ARMS.LH_B });
  ledger.register(createObligationRecord({
    obligationId: 'DEAD-1',
    fixtureId: 'lh0',
    arm: LH0_ARMS.LH_B,
    originTurn: 1,
    mechanism: 'plot_overlay',
    activationCondition: { predicate: { type: 'turn_gte', value: 6 }, horizon_turn: 6 },
    cognitionMechanism: 'plot_cognition_update',
    authorizedConsumer: 'character_move',
  }));
  tracer.recordStage('DEAD-1', LIFECYCLE_EVENT_TYPES.EXPIRED_DEAD, { turn: 6 });
  assert.equal(ledger.get('DEAD-1').lifecycle_state, LIFECYCLE_STATES.TRACKED_DEAD);
});

test('LH-0 entitlement violations detectable', () => {
  const seam = classifySeamFailure({
    generated: true, persisted: true, retrieved: true, entitlementLeak: true,
  });
  assert.equal(seam.seam, SEAM_FAILURE_CLASSES.ENTITLEMENT);
});

test('LH-0 projection omission detectable', () => {
  const gap = simulateG3dGapPattern({});
  assert.equal(gap.gap.detected, true);
  assert.equal(gap.seam.seam, SEAM_FAILURE_CLASSES.PROJECTION);
});

test('LH-0 consumer non-use detectable', () => {
  const seam = simulateNegativeControl('consumer_use');
  assert.equal(seam.seam, SEAM_FAILURE_CLASSES.CONSUMPTION);
});

test('LH-0 synthetic happy path reaches L4', () => {
  const { ledger, obligationId } = simulateHappyPathObligation({
    arm: LH0_ARMS.LH_B,
    obligationId: 'HAPPY-1',
    fixtureId: 'lh0_seam_micro_v1',
  });
  assert.equal(ledger.get(obligationId).lifecycle_state, LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL);
  assert.equal(transportLevelFromFlags({
    generated: true, persisted: true, projected: true, consumer_referenced: true, observable_consequence: true,
  }), TRANSPORT_LEVELS.L4_CONSEQUENTIAL);
});

test('LH-0 negative controls attributed to correct layer', () => {
  assert.equal(simulateNegativeControl('persistence').seam, SEAM_FAILURE_CLASSES.PERSISTENCE);
  assert.equal(simulateNegativeControl('projection').seam, SEAM_FAILURE_CLASSES.PROJECTION);
  assert.equal(simulateNegativeControl('consumer_receipt').seam, SEAM_FAILURE_CLASSES.CONSUMPTION);
});

test('LH-0 B/C/D comparable lifecycle semantics', () => {
  const suite = runDeterministicValidationSuite();
  assert.equal(suite.checks.comparable_arm_semantics, true);
  assert.equal(suite.checks.happy_path_l4_all_persistent_arms, true);
});

test('LH-0 archaeology export compatible', () => {
  const { ledger, obligationId } = simulateHappyPathObligation({
    arm: LH0_ARMS.LH_D,
    obligationId: 'ARCH-1',
    fixtureId: 'lh0_seam_micro_v1',
  });
  const arch = ledger.toArchaeologyRecord(obligationId);
  assert.ok(arch.responsible_cognition_mechanism);
  assert.ok(arch.event_chain.length > 0);
});

test('LH-0 cost accounting attaches to obligation identity', () => {
  const { ledger } = simulateHappyPathObligation({
    arm: LH0_ARMS.LH_B,
    obligationId: 'COST-1',
    fixtureId: 'lh0_seam_micro_v1',
  });
  const cost = ledger.costAttributionSummary();
  assert.ok(cost.persistent_tokens.input > 0);
  assert.equal(cost.activated_consequential_count, 1);
});

test('LH-0 arm configs enforce consumption pathway for persistent arms', () => {
  const result = validateArmConfigs();
  assert.equal(result.all_pass, true);
  assert.equal(result.g3d_gap_prevented, true);
  const bad = enforceConsumptionLifecycleConfig({
    ...buildLh0ArmConfig(LH0_ARMS.LH_B),
    projection_lifecycle_enabled: false,
  });
  assert.equal(bad.pass, false);
});

test('LH-0 LH-D fairness controls', () => {
  const fairness = validateLh0FairnessControls();
  assert.equal(fairness.all_pass, true);
});

test('LH-0 K6-class condition detectable without remediation', () => {
  const manifest = loadLh0FixtureManifest();
  const k6 = detectK6ClassCondition({
    requiredAnchorIds: manifest.k6_probe.required_anchor_ids,
    eligibleAnchorIds: manifest.k6_probe.required_anchor_ids,
    projectedAnchorIds: ['anchor-a'],
    projectionBudget: 1,
  });
  assert.equal(k6.k6_class_suspected, true);
  assert.deepEqual(k6.missing_from_projection, ['anchor-b']);
});

test('LH-0 beat options wire projection for persistent arms', () => {
  const bOpts = resolveLh0BeatOptions(buildLh0ArmConfig(LH0_ARMS.LH_B));
  const aOpts = resolveLh0BeatOptions(buildLh0ArmConfig(LH0_ARMS.LH_A));
  assert.equal(bOpts.projectionLifecycleEnabled, true);
  assert.equal(bOpts.lh0ConsumptionEnforcer, true);
  assert.equal(aOpts.projectionLifecycleEnabled, false);
});

test('LH-0 validate-apparatus smoke writes artifacts', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'lh0-app-'));
  const report = runValidateApparatus({ outputDir: tmp });
  assert.equal(report.live_micro_runs_executed, false);
  assert.equal(report.rp_quality_conclusions, false);
  assert.equal(report.production_runtime_modified, false);
  assert.ok(fs.existsSync(path.join(tmp, 'issue201-lh0-apparatus-validation.json')));
  assert.equal(report.readiness_for_lh0_micro_execution, true);
});

test('LH-0 full deterministic suite passes', () => {
  const suite = runDeterministicValidationSuite();
  assert.equal(suite.all_pass, true, JSON.stringify(suite.checks, null, 2));
});

test('LH-0 execution protocol not authorized', () => {
  const protocol = buildLh0ExecutionProtocol();
  assert.equal(protocol.authorized, false);
});
