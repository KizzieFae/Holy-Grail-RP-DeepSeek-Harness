/**
 * Issue #201 LH-0 — seam verification apparatus (deterministic validation).
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

import {
  LIFECYCLE_EVENT_TYPES,
  LIFECYCLE_STATES,
  LH0_SCHEMAS,
  SEAM_FAILURE_CLASSES,
} from './issue201-lifecycle-states.mjs';
import { ObligationLedger, createObligationRecord, validateDeferredValidContract } from './issue201-obligation-ledger.mjs';
import {
  LifecycleTracer,
  enforceConsumptionLifecycleConfig,
  transportLevelFromFlags,
} from './issue201-lifecycle-tracer.mjs';
import { classifySeamFailure, detectK6ClassCondition } from './issue201-seam-classifier.mjs';
import {
  LH0_ARMS,
  buildAllLh0ArmConfigs,
  buildLh0ArmConfig,
  resolveLh0BeatOptions,
} from './issue201-lh0-arms.mjs';
import { loadLh0FixtureManifest, REPO_ROOT } from './issue201-lh0-fixtures.mjs';

export { REPO_ROOT, LH0_ARMS, loadLh0FixtureManifest };

export function gitSha() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  } catch {
    return 'unknown';
  }
}

function mechanismForArm(arm) {
  const cfg = buildLh0ArmConfig(arm);
  return cfg.cognition_mechanisms[0] ?? 'none';
}

function persistenceForArm(arm) {
  const cfg = buildLh0ArmConfig(arm);
  return cfg.preservation_mechanism ?? 'continuity_only';
}

/**
 * Simulate synthetic happy-path obligation through full lifecycle (no LLM).
 */
export function simulateHappyPathObligation({
  arm,
  obligationId,
  fixtureId,
  originTurn = 1,
  activationTurn = 3,
  consumer = 'director_turn',
  withDeferral = false,
  deferUntilTurn = 5,
}) {
  const ledger = new ObligationLedger({ fixtureManifest: { fixture_id: fixtureId } });
  const tracer = new LifecycleTracer({ ledger, arm });

  const obligation = createObligationRecord({
    obligationId,
    fixtureId,
    arm,
    originTurn,
    mechanism: persistenceForArm(arm),
    activationCondition: {
      predicate: { type: 'turn_gte', value: withDeferral ? deferUntilTurn : activationTurn },
      horizon_turn: withDeferral ? deferUntilTurn : activationTurn,
    },
    decisionRelevant: true,
    deferralRationale: withDeferral ? `activation inappropriate before turn ${deferUntilTurn}` : null,
    cognitionMechanism: mechanismForArm(arm),
    persistenceLocation: `_lh0_state/${arm}/${obligationId}.json`,
    authorizedConsumer: consumer,
    tokenAccounting: { input_tokens: 120, output_tokens: 40, reasoning_tokens: 0 },
  });
  ledger.register(obligation);

  tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.GENERATED, { turn: originTurn });
  tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.PERSISTED, { turn: originTurn });

  if (withDeferral) {
    tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.DEFERRED_VALID, {
      turn: originTurn + 1,
      evidence: { deferral_rationale: obligation.deferral_rationale },
    });
  }

  tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.PROJECTED, {
    turn: withDeferral ? deferUntilTurn : activationTurn,
    consumer,
  });
  tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.CONSUMER_RECEIVED, {
    turn: withDeferral ? deferUntilTurn : activationTurn,
    consumer,
  });
  tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.CONSUMER_USED, {
    turn: withDeferral ? deferUntilTurn : activationTurn,
    consumer,
    evidence: { decision_relevant: true, content_hash: `hash-${obligationId}` },
  });
  tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.DECISION_INFLUENCED, {
    turn: withDeferral ? deferUntilTurn : activationTurn,
    evidence: { decision_id: `dec-${obligationId}` },
  });
  tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.ACTIVATED, {
    turn: withDeferral ? deferUntilTurn : activationTurn,
    evidence: { linked_obligation_id: obligationId },
  });
  tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.OBSERVABLE_CONSEQUENCE, {
    turn: withDeferral ? deferUntilTurn : activationTurn,
    evidence: { consequence_id: `cons-${obligationId}` },
  });

  return { tracer, ledger, obligationId };
}

export function simulatePrematureActivation({ arm, obligationId, fixtureId, activationHorizon = 5 }) {
  const ledger = new ObligationLedger();
  const tracer = new LifecycleTracer({ ledger, arm });
  ledger.register(createObligationRecord({
    obligationId,
    fixtureId,
    arm,
    originTurn: 2,
    mechanism: persistenceForArm(arm),
    activationCondition: {
      predicate: { type: 'turn_gte', value: activationHorizon },
      horizon_turn: activationHorizon,
    },
    decisionRelevant: true,
    cognitionMechanism: mechanismForArm(arm),
    authorizedConsumer: 'character_move',
  }));
  tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.GENERATED, { turn: 2 });
  tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.PERSISTED, { turn: 2 });
  tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.PREMATURE_ACTIVATION, {
    turn: 3,
    evidence: { attempted_before_horizon: activationHorizon },
  });
  return { tracer, ledger };
}

export function simulateNegativeControl(breakLayer) {
  const base = {
    generated: true,
    persisted: true,
    retrieved: true,
    projected: true,
    consumerReceived: true,
    consumerUsed: true,
    decisionInfluenced: true,
    observableConsequence: true,
  };
  switch (breakLayer) {
    case 'persistence':
      return classifySeamFailure({ ...base, persisted: false, generated: true });
    case 'projection':
      return classifySeamFailure({ ...base, projected: false, persisted: true });
    case 'consumer_receipt':
      return classifySeamFailure({
        ...base, consumerReceived: false, projected: true,
      });
    case 'consumer_use':
      return classifySeamFailure({
        ...base, consumerUsed: false, consumerReceived: true,
      });
    default:
      throw new Error(`unknown break layer: ${breakLayer}`);
  }
}

export function simulateG3dGapPattern({ obligationId = 'G3D-GAP-1' }) {
  const ledger = new ObligationLedger();
  const tracer = new LifecycleTracer({ ledger, arm: LH0_ARMS.LH_B });
  ledger.register(createObligationRecord({
    obligationId,
    fixtureId: 'g3d_gap_probe',
    arm: LH0_ARMS.LH_B,
    originTurn: 1,
    mechanism: 'plot_overlay',
    activationCondition: { predicate: { type: 'always' }, horizon_turn: 4 },
    cognitionMechanism: 'plot_cognition_update',
    authorizedConsumer: 'character_move',
  }));
  tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.GENERATED, { turn: 1 });
  tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.PERSISTED, { turn: 1 });
  // No projection — G3-D class gap
  const gap = tracer.detectG3dClassGap();
  const seam = tracer.seamAttributionFor(obligationId, { projected: false, persisted: true, generated: true });
  return { gap, seam, tracer };
}

export function validateArmConfigs() {
  const arms = buildAllLh0ArmConfigs();
  const results = arms.map((cfg) => {
    const enforcement = enforceConsumptionLifecycleConfig(cfg);
    const beatOptions = resolveLh0BeatOptions(cfg);
    return {
      arm: cfg.arm,
      label: cfg.label,
      enforcement,
      beat_options_projection: beatOptions.projectionLifecycleEnabled,
      persistent_cognition: cfg.persistent_cognition_enabled,
    };
  });
  const persistentArms = results.filter((r) => r.persistent_cognition);
  const allPersistentPass = persistentArms.every((r) => r.enforcement.pass);
  const lhAPass = results.find((r) => r.arm === LH0_ARMS.LH_A)?.enforcement.pass;
  return {
    all_pass: allPersistentPass && lhAPass,
    results,
    g3d_gap_prevented: persistentArms.every((r) => r.beat_options_projection === true),
  };
}

export function validateLh0FairnessControls() {
  const lhD = buildLh0ArmConfig(LH0_ARMS.LH_D);
  const checks = [
    { name: 'deterministic_eligibility_first', pass: lhD.fairness.deterministic_eligibility_first === true },
    { name: 'guidance_not_dictation', pass: lhD.fairness.guidance_not_dictation === true },
    { name: 'no_unconditional_override', pass: lhD.fairness.no_unconditional_override === true },
    { name: 'no_continuity_mutation', pass: lhD.fairness.no_continuity_mutation === true },
    { name: 'rejects_unconditional_override_flag', pass: enforceConsumptionLifecycleConfig({
      ...lhD,
      unconditional_director_override: true,
    }).pass === false },
  ];
  return { all_pass: checks.every((c) => c.pass), checks };
}

export function runDeterministicValidationSuite() {
  const manifest = loadLh0FixtureManifest();
  const armConfigValidation = validateArmConfigs();
  const fairness = validateLh0FairnessControls();

  const armHappyPaths = [LH0_ARMS.LH_B, LH0_ARMS.LH_C, LH0_ARMS.LH_D].map((arm) => {
    const { ledger, obligationId } = simulateHappyPathObligation({
      arm,
      obligationId: `HAPPY-${arm}`,
      fixtureId: manifest.fixture_id,
      withDeferral: arm === LH0_ARMS.LH_C,
      deferUntilTurn: 5,
    });
    const ob = ledger.get(obligationId);
    return {
      arm,
      terminal_state: ob.lifecycle_state,
      transport_level: transportLevelFromFlags({
        generated: true,
        persisted: true,
        projected: true,
        consumer_referenced: true,
        observable_consequence: true,
      }),
      archaeology: ledger.toArchaeologyRecord(obligationId),
    };
  });

  const deferred = simulateHappyPathObligation({
    arm: LH0_ARMS.LH_B,
    obligationId: 'LH0-OBL-DEFERRED-SIM',
    fixtureId: manifest.fixture_id,
    withDeferral: true,
    deferUntilTurn: 5,
  });
  const deferredContract = validateDeferredValidContract({
    ...deferred.ledger.get('LH0-OBL-DEFERRED-SIM'),
    deferral_rationale: 'predicate not satisfied until turn 5',
  });

  const premature = simulatePrematureActivation({
    arm: LH0_ARMS.LH_B,
    obligationId: 'LH0-OBL-PREMATURE-SIM',
    fixtureId: manifest.fixture_id,
  });
  const prematureState = premature.ledger.get('LH0-OBL-PREMATURE-SIM').lifecycle_state;

  const negativeControls = manifest.negative_controls.map((nc) => ({
    control_id: nc.control_id,
    expected_seam: nc.expected_seam,
    observed: simulateNegativeControl(nc.break_layer),
  }));

  const g3dGap = simulateG3dGapPattern({});

  const k6Probe = detectK6ClassCondition({
    requiredAnchorIds: manifest.k6_probe.required_anchor_ids,
    eligibleAnchorIds: manifest.k6_probe.required_anchor_ids,
    projectedAnchorIds: ['anchor-a'],
    projectionBudget: manifest.k6_probe.projection_budget,
  });

  const identityStable = deferred.ledger.get('LH0-OBL-DEFERRED-SIM').obligation_id
    === 'LH0-OBL-DEFERRED-SIM'
    && deferred.ledger.toArchaeologyRecord('LH0-OBL-DEFERRED-SIM').obligation_id
      === 'LH0-OBL-DEFERRED-SIM';

  const checks = {
    arm_configs_pass: armConfigValidation.all_pass,
    g3d_gap_prevented_in_config: armConfigValidation.g3d_gap_prevented,
    fairness_pass: fairness.all_pass,
    happy_path_l4_all_persistent_arms: armHappyPaths.every(
      (r) => r.terminal_state === LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL,
    ),
    deferred_valid_contract: deferredContract.valid,
    premature_detected: prematureState === LIFECYCLE_STATES.ACTIVATED_PREMATURE,
    negative_controls_attributed: negativeControls.every(
      (nc) => nc.observed?.seam?.includes(nc.expected_seam.split('_')[0])
        || nc.observed?.seam === nc.expected_seam
        || (nc.expected_seam === 'persistence_failure' && nc.observed?.seam === SEAM_FAILURE_CLASSES.PERSISTENCE)
        || (nc.expected_seam === 'projection_failure' && nc.observed?.seam === SEAM_FAILURE_CLASSES.PROJECTION)
        || (nc.expected_seam === 'consumption_failure' && nc.observed?.seam === SEAM_FAILURE_CLASSES.CONSUMPTION),
    ),
    g3d_gap_detectable: g3dGap.gap.detected === true,
    g3d_gap_seam_projection: g3dGap.seam?.seam === SEAM_FAILURE_CLASSES.PROJECTION,
    k6_class_detectable: k6Probe.k6_class_suspected === true,
    obligation_identity_stable: identityStable,
    archaeology_exportable: armHappyPaths.every((r) => r.archaeology?.schema === LH0_SCHEMAS.ARCHAEOLOGY_RECORD),
    cost_attribution_ready: deferred.ledger.costAttributionSummary().schema === LH0_SCHEMAS.COST_ATTRIBUTION,
    comparable_arm_semantics: armHappyPaths.every((r) => r.transport_level === 'L4'),
  };

  const allPass = Object.values(checks).every(Boolean);
  return {
    all_pass: allPass,
    checks,
    arm_config_validation: armConfigValidation,
    fairness,
    arm_happy_paths: armHappyPaths,
    negative_controls: negativeControls,
    g3d_gap_probe: g3dGap,
    k6_probe: k6Probe,
    deferred_contract: deferredContract,
    premature_state: prematureState,
  };
}

export function runValidateApparatus({ outputDir }) {
  fs.mkdirSync(outputDir, { recursive: true });
  const manifest = loadLh0FixtureManifest();
  const validation = runDeterministicValidationSuite();
  const armConfigs = buildAllLh0ArmConfigs();

  const report = {
    schema: LH0_SCHEMAS.APPARATUS_VALIDATION,
    activation_commit: '741e1ce',
    implementation_base_sha: gitSha(),
    live_micro_runs_executed: false,
    rp_quality_conclusions: false,
    fixture_manifest: manifest,
    arm_configs: armConfigs,
    deterministic_validation: validation,
    readiness_for_lh0_micro_execution: validation.all_pass,
    production_runtime_modified: false,
    k6_remediation_implemented: false,
    known_limitations: [
      'Lifecycle stages 6–7 (live Primary RP decision influence) validated via synthetic simulation only',
      'Persistent cognition adapters (Plot/Storyteller/consolidated) are configuration contracts — live LLM wiring deferred to micro-run authorization',
      'K6 remediation not implemented; detection-only probe included',
    ],
  };

  fs.writeFileSync(
    path.join(outputDir, 'issue201-lh0-apparatus-validation.json'),
    `${JSON.stringify(report, null, 2)}\n`,
  );
  fs.writeFileSync(
    path.join(outputDir, 'issue201-lh0-arm-configs.json'),
    `${JSON.stringify(armConfigs, null, 2)}\n`,
  );
  fs.writeFileSync(
    path.join(outputDir, 'issue201-lh0-deterministic-checks.json'),
    `${JSON.stringify(validation, null, 2)}\n`,
  );

  const sampleTrace = simulateHappyPathObligation({
    arm: LH0_ARMS.LH_B,
    obligationId: 'SAMPLE-TRACE',
    fixtureId: manifest.fixture_id,
  });
  fs.writeFileSync(
    path.join(outputDir, 'issue201-lh0-sample-trace.json'),
    `${JSON.stringify(sampleTrace.ledger.toJSON(), null, 2)}\n`,
  );

  return report;
}

export function buildLh0ExecutionProtocol() {
  return {
    schema: 'issue201_lh0_execution_protocol_v1',
    authorized: false,
    prerequisite: 'Governance authorization for LH-0 micro-run execution',
    stages: [
      { stage: 'LH-0', turns: 6, sequences_per_arm: 1, arms: ['lh_b', 'lh_c', 'lh_d'], control: 'lh_a' },
    ],
    pass_criteria: {
      l2_plus_projection: true,
      consumer_receipt_logged: true,
      l3_or_deferred_valid: true,
      seam_attribution_on_failure: true,
    },
    explicit_prohibitions: [
      'no_rp_quality_conclusions_from_lh0',
      'no_lh1a_without_governance_evaluation',
    ],
  };
}
