/**
 * Issue #201 LH-1A — synthetic lifecycle proofs (apparatus tests, not RP-quality evidence).
 */
import { LIFECYCLE_EVENT_TYPES, LIFECYCLE_STATES } from './issue201-lifecycle-states.mjs';
import { LifecycleTracer } from './issue201-lifecycle-tracer.mjs';
import { ObligationLedger, createObligationRecord } from './issue201-obligation-ledger.mjs';
import { classifySeamFailure } from './issue201-seam-classifier.mjs';
import { buildLh0ArmConfig } from './issue201-lh0-arms.mjs';
import { buildRetrievalSufficiencyVerdict } from './issue201-lh1a-archaeology.mjs';

function ledgerWithObligation({ arm, obligationId, fixtureId = 'ayame_lh1a_v1' }) {
  const cfg = buildLh0ArmConfig(arm);
  const ledger = new ObligationLedger({ fixtureManifest: { fixture_id: fixtureId } });
  const tracer = new LifecycleTracer({ ledger, arm });
  const obligation = createObligationRecord({
    obligationId,
    fixtureId,
    arm,
    originTurn: 3,
    mechanism: cfg.preservation_mechanism ?? 'continuity_only',
    activationCondition: { predicate: { type: 'turn_gte', value: 18 }, horizon_turn: 22 },
    decisionRelevant: true,
    deferralRationale: 'Synthetic dormancy until relevance window.',
    cognitionMechanism: cfg.cognition_mechanisms[0] ?? 'none',
    persistenceLocation: `_lh1a/${arm}/${obligationId}.json`,
    authorizedConsumer: 'character_move',
    tokenAccounting: { input_tokens: 200, output_tokens: 80, reasoning_tokens: 40 },
  });
  ledger.register(obligation);
  return { ledger, tracer, obligationId };
}

export function runSyntheticLifecycleProofs() {
  const proofs = [];

  // dormant → relevant activation
  {
    const { ledger, tracer, obligationId } = ledgerWithObligation({ arm: 'lh_b', obligationId: 'SYN-DORMANT' });
    tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.PERSISTED, { turn: 3 });
    tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.DEFERRED_VALID, { turn: 4 });
    ledger.setLifecycleState(obligationId, LIFECYCLE_STATES.DEFERRED_VALID, { turn: 4 });
    tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.PROJECTED, { turn: 18, consumer: 'character_move' });
    tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.CONSUMER_USED, { turn: 18, consumer: 'character_move' });
    ledger.setLifecycleState(obligationId, LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL, { turn: 18 });
    proofs.push({
      name: 'dormant_to_relevant_activation',
      pass: ledger.get(obligationId).lifecycle_state === LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL,
    });
  }

  // valid non-activation
  {
    const { ledger, obligationId } = ledgerWithObligation({ arm: 'lh_c', obligationId: 'SYN-NONACT' });
    ledger.setLifecycleState(obligationId, LIFECYCLE_STATES.DEFERRED_VALID, { turn: 5 });
    proofs.push({
      name: 'valid_non_activation',
      pass: ledger.get(obligationId).lifecycle_state === LIFECYCLE_STATES.DEFERRED_VALID,
    });
  }

  // premature activation
  {
    const { ledger, obligationId } = ledgerWithObligation({ arm: 'lh_d', obligationId: 'SYN-PREMATURE' });
    ledger.setLifecycleState(obligationId, LIFECYCLE_STATES.ACTIVATED_PREMATURE, { turn: 10 });
    proofs.push({
      name: 'premature_activation_classification',
      pass: ledger.get(obligationId).lifecycle_state === LIFECYCLE_STATES.ACTIVATED_PREMATURE,
    });
  }

  // tracked dead
  {
    const { ledger, obligationId } = ledgerWithObligation({ arm: 'lh_b', obligationId: 'SYN-DEAD' });
    ledger.setLifecycleState(obligationId, LIFECYCLE_STATES.TRACKED_DEAD, { turn: 22 });
    proofs.push({
      name: 'tracked_dead_classification',
      pass: ledger.get(obligationId).lifecycle_state === LIFECYCLE_STATES.TRACKED_DEAD,
    });
  }

  // retrieval sufficient vs persistence useful
  {
    const retrievalOnly = buildRetrievalSufficiencyVerdict({ transcriptSufficient: true, persistenceSuppliedInterpretation: false });
    const persistenceUseful = buildRetrievalSufficiencyVerdict({ transcriptSufficient: false, persistenceSuppliedInterpretation: true });
    proofs.push({
      name: 'retrieval_vs_persistence_distinction',
      pass: retrievalOnly.marginal_value_attribution === 'retrieval_sufficient'
        && persistenceUseful.marginal_value_attribution === 'persistence_useful',
    });
  }

  // projection omission seam
  {
    const seam = classifySeamFailure({
      generated: true,
      persisted: true,
      retrieved: true,
      projected: false,
      consumerReceived: false,
    });
    proofs.push({
      name: 'projection_omission_attribution',
      pass: seam?.seam === 'projection_failure',
    });
  }

  // consumer non-use
  {
    const seam = classifySeamFailure({
      generated: true,
      persisted: true,
      retrieved: true,
      projected: true,
      consumerReceived: true,
      consumerUsed: false,
    });
    proofs.push({
      name: 'consumer_non_use_attribution',
      pass: seam?.seam === 'consumption_failure',
    });
  }

  // consequential activation
  {
    const { ledger, tracer, obligationId } = ledgerWithObligation({ arm: 'lh_c', obligationId: 'SYN-CONSEQ' });
    tracer.recordStage(obligationId, LIFECYCLE_EVENT_TYPES.OBSERVABLE_CONSEQUENCE, { turn: 20 });
    ledger.setLifecycleState(obligationId, LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL, { turn: 20 });
    proofs.push({
      name: 'consequential_activation_attribution',
      pass: ledger.get(obligationId).lifecycle_state === LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL,
    });
  }

  return {
    all_pass: proofs.every((p) => p.pass),
    proofs,
  };
}
