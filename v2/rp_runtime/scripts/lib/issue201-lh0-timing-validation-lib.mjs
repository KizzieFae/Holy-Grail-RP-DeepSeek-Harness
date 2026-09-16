/**
 * Issue #201 LH-0 — turn-alignment deterministic validation (pre-live gates).
 */
import { LH0_ARMS } from './issue201-lh0-arms.mjs';
import { buildLh0ArmConfig } from './issue201-lh0-arms.mjs';
import { loadLh0FixtureManifest } from './issue201-lh0-fixtures.mjs';
import {
  buildLh0FinalizedProjection,
  classifyLh0ObligationStates,
  obligationsForConsumer,
} from './issue201-lh0-persistent-store.mjs';
import { prepareLh0RoundTransport } from './issue201-lh0-transport.mjs';
import { buildCharacterConsumerEvidence } from './issue201-lh0-consumer-evidence.mjs';
import {
  buildInformationUniquenessReport,
  listDecisionForks,
  seedLh0ObligationFromFixture,
} from './issue201-lh0-semantic-content.mjs';
import { resolveLh0TransportClocks } from './issue201-lh0-clocks.mjs';
import { runLh0SemanticValidationSuite } from './issue201-lh0-semantic-validation-lib.mjs';
import { LIFECYCLE_STATES } from './issue201-lifecycle-states.mjs';

function check(name, pass, detail = null) {
  return { name, pass, detail };
}

function buildSeededStore(fixture) {
  const store = {
    schema: 'issue201_lh0_persistent_store_v1',
    obligations: fixture.obligations
      .filter((o) => !o.negative_control)
      .map((o) => seedLh0ObligationFromFixture(o, { mechanism: 'fixture_seed', source: 'fixture_seed' })),
    events: [],
  };
  for (let turn = 1; turn <= 4; turn += 1) {
    classifyLh0ObligationStates(store, turn);
  }
  return store;
}

function simulateReceiptAtFixtureTurn(store, fixtureTurn, bindingTurn) {
  const transport = prepareLh0RoundTransport({
    sessionsDir: '/tmp/unused',
    hgSessionId: 'hg-session-timing',
    hgRoundId: `hg-round-fixture-${fixtureTurn}`,
    fixtureTurnIndex: fixtureTurn,
    bindingTurnIndex: bindingTurn,
    characterId: 'Ayame',
    arm: LH0_ARMS.LH_B,
    storeOverride: JSON.parse(JSON.stringify(store)),
  });
  const manifest = {
    manifest_id: `manifest-timing-${fixtureTurn}`,
    inference_kind: 'character_turn',
    contributions: transport.characterProjection?.contributions ?? [],
  };
  const receipt = buildCharacterConsumerEvidence({
    manifest,
    finalizedProjection: transport.characterProjection,
    projectionSupplied: Boolean(transport.characterProjection),
    obligationIdsExpected: transport.characterDue.map((o) => o.obligation_id),
  });
  return { transport, receipt };
}

export function runLh0TimingValidationSuite() {
  const fixture = loadLh0FixtureManifest();
  const forks = listDecisionForks(fixture);
  const guestFork = forks.find((f) => f.fork_id === 'FORK-GUEST-POLICY');
  const curfewFork = forks.find((f) => f.fork_id === 'FORK-EVENING-DUTY-CURFEW');
  const checks = [];
  const store = buildSeededStore(fixture);
  const deferred = fixture.obligations.find((o) => o.obligation_id === 'LH0-OBL-DEFERRED');
  const later = fixture.obligations.find((o) => o.obligation_id === 'LH0-OBL-LATER');

  const clocks = resolveLh0TransportClocks({ fixtureTurnIndex: 5, bindingTurnIndex: 4 });
  checks.push(check('two_clocks_separately_represented', clocks.fixture_turn_index === 5 && clocks.runtime_binding_turn_index === 4));

  const t4Char = obligationsForConsumer(store, { turn: 4, consumer: 'character_move' });
  checks.push(check('t4_deferred_not_due', t4Char.every((o) => o.obligation_id !== 'LH0-OBL-DEFERRED')));
  const deferredRow = store.obligations.find((o) => o.obligation_id === 'LH0-OBL-DEFERRED');
  checks.push(check(
    't4_deferred_valid_state',
    deferredRow?.lifecycle_state === LIFECYCLE_STATES.DEFERRED_VALID,
  ));

  const t4Sim = simulateReceiptAtFixtureTurn(store, 4, 3);
  checks.push(check('t4_no_character_projection', t4Sim.transport.characterDue.length === 0));
  checks.push(check('t4_no_semantic_receipt', t4Sim.receipt.consumer_received === false));

  const t5Char = obligationsForConsumer(store, { turn: 5, consumer: 'character_move' });
  checks.push(check('t5_guest_obligations_due', t5Char.some((o) => o.obligation_id === 'LH0-OBL-DEFERRED')
    && t5Char.some((o) => o.obligation_id === 'LH0-OBL-LATER')));

  const t5Sim = simulateReceiptAtFixtureTurn(store, 5, 4);
  checks.push(check('t5_projection_before_cognition_contract', t5Sim.transport.projected_finalized === true));
  checks.push(check('t5_semantic_manifest_receipt', t5Sim.receipt.semantic_receipt_adequate === true));
  checks.push(check(
    't5_fixture_clock_used_for_eligibility',
    t5Sim.transport.fixture_turn_index === 5,
  ));
  checks.push(check(
    't5_runtime_clock_used_for_binding',
    t5Sim.transport.runtime_binding_turn_index === 4,
  ));

  const t6Sim = simulateReceiptAtFixtureTurn(store, 6, 5);
  checks.push(check('t6_projection_contract', t6Sim.transport.projected_finalized === true));
  checks.push(check('t6_semantic_manifest_receipt', t6Sim.receipt.semantic_receipt_adequate === true));

  const lhA = buildLh0ArmConfig(LH0_ARMS.LH_A);
  checks.push(check('lh_a_omits_persistent_cognition', lhA.persistent_cognition_enabled !== true));

  const uniqueness = buildInformationUniquenessReport({ manifestContributions: [], fixture });
  checks.push(check('information_uniqueness_clean', uniqueness.all_unique === true));

  const salience = [LH0_ARMS.LH_B, LH0_ARMS.LH_C, LH0_ARMS.LH_D].map((arm) => {
    const projection = buildLh0FinalizedProjection([deferred, later], {
      batchId: `salience-${arm}`,
      consumer: 'character_move',
      characterId: 'Ayame',
      hgRoundId: 'hg-round-salience',
      turnIndex: 4,
    });
    return projection.contributions[0];
  });
  checks.push(check(
    'b_c_d_comparable_payload',
    salience.every((c) => c.priority === salience[0].priority)
      && salience.every((c) => c.source_kind === 'active_constraints'),
  ));

  checks.push(check('guest_fork_turn_authored', guestFork?.decision_turn === 5));
  checks.push(check('curfew_fork_turn_authored', curfewFork?.decision_turn === 6));
  checks.push(check(
    'decision_classes_frozen',
    (guestFork?.with_obligation_choice_classes?.length ?? 0) > 0
      && (guestFork?.without_obligation_choice_classes?.length ?? 0) > 0,
  ));

  const semantic = runLh0SemanticValidationSuite();
  checks.push(check('prior_semantic_regressions', semantic.all_pass === true));

  const allPass = checks.every((c) => c.pass);
  return {
    schema: 'issue201_lh0_timing_validation_v1',
    all_pass: allPass,
    checks,
    information_uniqueness: uniqueness,
    fixture_clock_contract: {
      guest_policy_fork_turn: guestFork?.decision_turn ?? null,
      curfew_fork_turn: curfewFork?.decision_turn ?? null,
      deferred_activation_turn: deferred?.activation_predicate?.value ?? null,
    },
    readiness_for_turn_aligned_qualification: allPass,
  };
}
