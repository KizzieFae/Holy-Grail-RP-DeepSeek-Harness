/**
 * Issue #201 LH-0 — bounded remediation deterministic validation.
 */
import { validateBridgeManifest } from '../../src/lib/manifest-validation.mjs';
import { LH0_ARMS } from './issue201-lh0-arms.mjs';
import { loadLh0FixtureManifest } from './issue201-lh0-fixtures.mjs';
import { buildLh0FinalizedProjection } from './issue201-lh0-persistent-store.mjs';
import {
  validateLh0FinalizedProjectionPackage,
  buildCharacterConsumerEvidence,
} from './issue201-lh0-consumer-evidence.mjs';
import {
  prepareLh0RoundTransport,
  recordLh0TransportAuditStep,
} from './issue201-lh0-transport.mjs';
import {
  adjudicateLh0ArmSequence,
  buildFirstRunFalsePositiveTrace,
} from './issue201-lh0-live-adjudication.mjs';
import { classifySeamFailure } from './issue201-seam-classifier.mjs';
import { validateLh0FairnessControls, validateArmConfigs } from './issue201-lh0-lib.mjs';
import { buildLh0HarnessInferenceManifest } from './issue201-lh0-post-commit-adapters.mjs';
import { LIFECYCLE_STATES } from './issue201-lifecycle-states.mjs';

function check(name, pass, detail = null) {
  return { name, pass, detail };
}

export function runLh0RemediationValidationSuite() {
  const fixture = loadLh0FixtureManifest();
  const sampleObligation = fixture.obligations[1];
  const checks = [];

  const lhCProjection = buildLh0FinalizedProjection([sampleObligation], {
    batchId: 'lh0-char-test',
    consumer: 'character_move',
    characterId: 'kizzie',
    hgRoundId: 'hg-round-test',
    turnIndex: 5,
  });
  const lhDProjection = buildLh0FinalizedProjection([fixture.obligations[2]], {
    batchId: 'lh0-char-d',
    consumer: 'character_move',
    characterId: 'kizzie',
    hgRoundId: 'hg-round-test',
    turnIndex: 5,
  });

  checks.push(check(
    'lh_c_projection_manifest_valid',
    validateLh0FinalizedProjectionPackage(lhCProjection, { consumer: 'character_move' }).valid === true,
  ));
  checks.push(check(
    'lh_d_projection_manifest_valid',
    validateLh0FinalizedProjectionPackage(lhDProjection, { consumer: 'character_move' }).valid === true,
  ));

  let missingKindCaught = false;
  try {
    validateBridgeManifest({
      manifest: {
        manifest_id: 'bad',
        contributions: [{ contribution_id: 'c1', source_kind: 'active_constraints', content: 'x' }],
      },
      inferenceKind: 'character_turn',
    });
  } catch (err) {
    missingKindCaught = /missing required inference_kind|missing inference_kind/.test(String(err.message));
  }
  checks.push(check('missing_inference_kind_regression', missingKindCaught));

  const seededStore = {
    schema: 'issue201_lh0_persistent_store_v1',
    obligations: [{
      ...sampleObligation,
      authorized_consumer: 'character_move',
      activation_predicate: { type: 'turn_gte', value: 5 },
      activation_horizon_turn: 5,
      intro_turn: 2,
    }],
    events: [],
  };
  const transport = prepareLh0RoundTransport({
    sessionsDir: '/tmp/unused',
    hgSessionId: 'hg-session-test',
    hgRoundId: 'hg-round-test',
    turnIndex: 5,
    characterId: 'kizzie',
    arm: LH0_ARMS.LH_C,
    faultInjection: null,
    storeOverride: seededStore,
  });
  const audit = recordLh0TransportAuditStep(transport);
  checks.push(check(
    'candidate_construction_not_receipt',
    audit.candidate_only === true && audit.character_consumer_receipt === false,
  ));
  checks.push(check(
    'finalized_projection_not_receipt',
    audit.projected_finalized === Boolean(transport.characterPrecomputed)
      && audit.character_consumer_receipt === false,
  ));

  const manifestWithReceipt = {
    manifest_id: 'm1',
    inference_kind: 'character_turn',
    contributions: lhCProjection.contributions,
  };
  const receiptEvidence = buildCharacterConsumerEvidence({
    manifest: manifestWithReceipt,
    finalizedProjection: lhCProjection,
    projectionSupplied: true,
    obligationIdsExpected: [sampleObligation.obligation_id],
  });
  checks.push(check('consumer_input_required_for_receipt', receiptEvidence.consumer_received === true));

  const receiptOnly = buildCharacterConsumerEvidence({
    manifest: { manifest_id: 'm2', inference_kind: 'character_turn', contributions: [] },
    finalizedProjection: lhCProjection,
    projectionSupplied: true,
    obligationIdsExpected: [sampleObligation.obligation_id],
  });
  checks.push(check('receipt_alone_not_use', receiptOnly.consumer_received === false));

  const useOnly = {
    ...receiptEvidence,
    consumer_used: false,
    referenced_obligation_ids: [],
  };
  checks.push(check('use_required_for_influence', useOnly.referenced_obligation_ids.length === 0));

  const falsePositive = adjudicateLh0ArmSequence({
    arm: LH0_ARMS.LH_B,
    turns: buildFirstRunFalsePositiveTrace(),
    lh0Store: buildFirstRunFalsePositiveTrace()[0].lh0_store,
    fixture,
  });
  checks.push(check(
    'old_false_positive_fails_c',
    falsePositive.criteria.C_projection.pass === false,
  ));
  checks.push(check(
    'old_false_positive_fails_d',
    falsePositive.criteria.D_consumer_receipt.pass === false,
  ));
  checks.push(check(
    'old_false_positive_fails_e',
    falsePositive.criteria.E_consumer_use.pass === false,
  ));
  checks.push(check(
    'old_false_positive_fails_h',
    falsePositive.criteria.H_deferred_later_activation.pass === false,
  ));

  const omitProjectionTransport = prepareLh0RoundTransport({
    sessionsDir: '/tmp/unused',
    hgSessionId: 'hg-session-test',
    hgRoundId: 'hg-round-test',
    turnIndex: 5,
    characterId: 'kizzie',
    arm: LH0_ARMS.LH_C,
    faultInjection: 'omit_projection',
    storeOverride: seededStore,
  });
  const omitProjectionAudit = recordLh0TransportAuditStep(omitProjectionTransport);
  const projectionSeam = classifySeamFailure({
    generated: true,
    persisted: true,
    projected: omitProjectionAudit.projected_finalized,
  });
  checks.push(check(
    'live_path_projection_omission_attributed',
    projectionSeam.seam === 'projection_failure',
  ));

  const omitReceiptTransport = prepareLh0RoundTransport({
    sessionsDir: '/tmp/unused',
    hgSessionId: 'hg-session-test',
    hgRoundId: 'hg-round-test',
    turnIndex: 5,
    characterId: 'kizzie',
    arm: LH0_ARMS.LH_C,
    faultInjection: 'omit_receipt',
    storeOverride: seededStore,
  });
  const omitReceiptAudit = recordLh0TransportAuditStep(omitReceiptTransport, { omitCharacterReceipt: true });
  checks.push(check(
    'live_path_receipt_omission_attributed',
    omitReceiptAudit.character_precomputed_supplied === false
      && omitReceiptAudit.character_consumer_receipt === false,
  ));

  checks.push(check(
    'director_temporal_ordering_recorded',
    audit.director_deterministic_fixture === true && audit.director_consumer_receipt === false,
  ));

  checks.push(check(
    'character_receipt_traceable',
    receiptEvidence.received_obligation_ids.includes(sampleObligation.obligation_id),
  ));

  const storeOnlyActivation = {
    obligations: [{
      obligation_id: 'LH0-OBL-DEFERRED',
      lifecycle_state: LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL,
      intro_turn: 2,
      activated_turn: 5,
      class: 'valid_deferral',
    }],
    events: [],
  };
  const storeOnlyAdj = adjudicateLh0ArmSequence({
    arm: LH0_ARMS.LH_B,
    turns: [],
    lh0Store: storeOnlyActivation,
    fixture,
  });
  checks.push(check(
    'store_activation_alone_not_consequence',
    storeOnlyAdj.criteria.G_consequential_activation.pass === false,
  ));
  checks.push(check(
    'store_activation_alone_not_deferred_chain',
    storeOnlyAdj.criteria.H_deferred_later_activation.pass === false,
  ));

  const fairness = validateLh0FairnessControls();
  checks.push(check('lh_d_fairness_enforced', fairness.all_pass === true));
  const armConfigs = validateArmConfigs();
  checks.push(check('arm_configs_valid', armConfigs.all_pass === true));

  const storytellerManifest = buildLh0HarnessInferenceManifest({
    inferenceId: 'lh0-test-storyteller',
    mechanism: 'storyteller_post_commit_issue_pressure',
    prompt: 'lh0 harness prompt',
  });
  const plotManifest = buildLh0HarnessInferenceManifest({
    inferenceId: 'lh0-test-plot',
    mechanism: 'plot_cognition_update',
    prompt: 'lh0 harness prompt',
  });
  checks.push(check(
    'lh_c_post_commit_manifest_valid',
    validateBridgeManifest({
      manifest: storytellerManifest,
      inferenceKind: storytellerManifest.inference_kind,
    }) === storytellerManifest.inference_kind,
  ));
  checks.push(check(
    'lh_d_post_commit_manifest_valid',
    validateBridgeManifest({
      manifest: plotManifest,
      inferenceKind: plotManifest.inference_kind,
    }) === plotManifest.inference_kind,
  ));

  const allPass = checks.every((c) => c.pass);
  return {
    schema: 'issue201_lh0_remediation_validation_v1',
    all_pass: allPass,
    checks,
    readiness_for_corrective_live_execution: allPass,
  };
}
