/**
 * Issue #201 LH-0 — semantic-seam deterministic validation (pre-live gates).
 */
import { validateBridgeManifest } from '../../src/lib/manifest-validation.mjs';
import { LH0_ARMS } from './issue201-lh0-arms.mjs';
import { loadLh0FixtureManifest } from './issue201-lh0-fixtures.mjs';
import {
  buildLh0FinalizedProjection,
  obligationsForConsumer,
  readLh0Store,
} from './issue201-lh0-persistent-store.mjs';
import {
  buildCharacterConsumerEvidence,
  validateLh0FinalizedProjectionPackage,
} from './issue201-lh0-consumer-evidence.mjs';
import {
  isBookkeepingOnlySemanticContent,
  resolveLh0ModelFacingContent,
  buildInformationUniquenessReport,
  buildSalienceComparabilityReport,
  loadLh0CausalDesign,
  listDecisionForks,
  deferredObligationWithheldBeforeActivation,
  seedLh0ObligationFromFixture,
} from './issue201-lh0-semantic-content.mjs';
import { validateLh0FairnessControls, validateArmConfigs } from './issue201-lh0-lib.mjs';
import { buildLh0ArmConfig } from './issue201-lh0-arms.mjs';
import { runLh0RemediationValidationSuite } from './issue201-lh0-remediation-lib.mjs';
import { LIFECYCLE_STATES } from './issue201-lifecycle-states.mjs';
import { adjudicateLh0ArmSequence } from './issue201-lh0-live-adjudication.mjs';

function check(name, pass, detail = null) {
  return { name, pass, detail };
}

function buildSampleStore(fixture) {
  return {
    schema: 'issue201_lh0_persistent_store_v1',
    obligations: fixture.obligations
      .filter((o) => !o.negative_control)
      .map((o) => seedLh0ObligationFromFixture(o, { mechanism: 'fixture_seed', source: 'fixture_seed' })),
    events: [],
  };
}

export function runLh0SemanticValidationSuite() {
  const fixture = loadLh0FixtureManifest();
  const causal = loadLh0CausalDesign(fixture);
  const checks = [];
  const arms = [LH0_ARMS.LH_B, LH0_ARMS.LH_C, LH0_ARMS.LH_D];
  const store = buildSampleStore(fixture);
  const deferred = fixture.obligations.find((o) => o.obligation_id === 'LH0-OBL-DEFERRED');
  const later = fixture.obligations.find((o) => o.obligation_id === 'LH0-OBL-LATER');

  const projectionsByArm = {};
  for (const arm of arms) {
    const projection = buildLh0FinalizedProjection([deferred, later], {
      batchId: `lh0-${arm}`,
      consumer: 'character_move',
      characterId: 'Ayame',
      hgRoundId: 'hg-round-semantic',
      turnIndex: 5,
    });
    projectionsByArm[arm] = projection;
    checks.push(check(
      `${arm}_semantic_projection_valid`,
      validateLh0FinalizedProjectionPackage(projection, { consumer: 'character_move' }).valid === true,
    ));
    const content = projection.contributions.map((c) => c.content).join(' ');
    checks.push(check(
      `${arm}_semantic_projection_not_bookkeeping`,
      !isBookkeepingOnlySemanticContent(content),
    ));
    checks.push(check(
      `${arm}_semantic_projection_traceable`,
      projection.contributions.every((c) => c.provenance?.lh0_obligation_id),
    ));
  }

  const salience = buildSalienceComparabilityReport(projectionsByArm);
  checks.push(check('b_c_d_salience_comparable', salience.comparable === true));

  const manifestSample = {
    manifest_id: 'semantic-manifest',
    inference_kind: 'character_turn',
    contributions: projectionsByArm[LH0_ARMS.LH_B].contributions,
  };
  const receipt = buildCharacterConsumerEvidence({
    manifest: manifestSample,
    finalizedProjection: projectionsByArm[LH0_ARMS.LH_B],
    projectionSupplied: true,
    obligationIdsExpected: [deferred.obligation_id, later.obligation_id],
  });
  checks.push(check('character_manifest_semantic_receipt', receipt.consumer_received === true));
  checks.push(check(
    'bookkeeping_representation_fails_adequacy',
    isBookkeepingOnlySemanticContent(`LH0-OBL-DEFERRED: plot_scribe_tracked:LH0-OBL-DEFERRED`),
  ));

  const withheld = obligationsForConsumer(store, { turn: 4, consumer: 'character_move' });
  checks.push(check(
    'deferred_withheld_before_predicate',
    withheld.every((o) => o.obligation_id !== 'LH0-OBL-DEFERRED'),
  ));
  const active = obligationsForConsumer(store, { turn: 5, consumer: 'character_move' });
  checks.push(check(
    'deferred_projected_when_predicate_satisfied',
    active.some((o) => o.obligation_id === 'LH0-OBL-DEFERRED'),
  ));
  checks.push(check(
    'deferred_timing_contract',
    deferredObligationWithheldBeforeActivation(store, 'LH0-OBL-DEFERRED', 4) === true,
  ));

  checks.push(check('fixture_decision_forks_defined', listDecisionForks(fixture).length >= 2));
  checks.push(check(
    'fixture_choice_classes_defined',
    listDecisionForks(fixture).every((f) => (
      (f.with_obligation_choice_classes?.length ?? 0) > 0
      && (f.without_obligation_choice_classes?.length ?? 0) > 0
    )),
  ));

  const uniqueness = buildInformationUniquenessReport({
    manifestContributions: [
      { source_kind: 'scene_context', content: 'Household interview in receiving room.' },
      { source_kind: 'recent_scene_transcript', content: 'Applicant arrived for live-in position.' },
    ],
    fixture,
  });
  checks.push(check('information_uniqueness_recorded', uniqueness.schema != null));
  checks.push(check('information_uniqueness_clean_probe', uniqueness.all_unique === true));

  const lhAConfig = buildLh0ArmConfig(LH0_ARMS.LH_A);
  checks.push(check(
    'lh_a_omits_persistent_cognition',
    lhAConfig.persistent_cognition_enabled !== true,
  ));

  const fairness = validateLh0FairnessControls();
  checks.push(check('lh_d_fairness_enforced', fairness.all_pass === true));
  const armConfigs = validateArmConfigs();
  checks.push(check('arm_configs_valid', armConfigs.all_pass === true));

  const storeOnly = adjudicateLh0ArmSequence({
    arm: LH0_ARMS.LH_B,
    turns: [],
    lh0Store: {
      obligations: [{
        obligation_id: 'LH0-OBL-DEFERRED',
        lifecycle_state: LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL,
        intro_turn: 2,
        activated_turn: 5,
      }],
      events: [],
    },
    fixture,
  });
  checks.push(check(
    'consequence_requires_committed_behavior',
    storeOnly.criteria.G_consequential_activation.pass === false,
  ));

  const priorRemediation = runLh0RemediationValidationSuite();
  checks.push(check('prior_remediation_regressions', priorRemediation.all_pass === true));

  for (const ob of fixture.obligations.filter((o) => !o.negative_control)) {
    checks.push(check(
      `semantic_content_resolves_${ob.obligation_id}`,
      resolveLh0ModelFacingContent(ob, fixture).length > 20,
    ));
  }

  checks.push(check(
    'causal_design_salience_contract',
    causal.salience?.base_priority === 18 && causal.salience?.source_kind === 'active_constraints',
  ));

  const allPass = checks.every((c) => c.pass);
  return {
    schema: 'issue201_lh0_semantic_validation_v1',
    all_pass: allPass,
    checks,
    information_uniqueness: uniqueness,
    salience_comparability: salience,
    readiness_for_final_qualification: allPass,
  };
}
