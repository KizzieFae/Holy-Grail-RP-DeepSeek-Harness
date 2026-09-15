/**
 * Issue #201 LH-0 — synthetic obligation ledger with DEFERRED_VALID contract.
 */
import {
  LIFECYCLE_STATES,
  LH0_SCHEMAS,
  PRESERVATION_MECHANISMS,
} from './issue201-lifecycle-states.mjs';

export function validateDeferredValidContract(obligation) {
  const errors = [];
  if (!obligation.decision_relevant) {
    errors.push('DEFERRED_VALID requires decision_relevant=true');
  }
  if (!obligation.deferral_rationale) {
    errors.push('DEFERRED_VALID requires deferral_rationale explaining why activation is inappropriate now');
  }
  if (!obligation.activation_condition?.predicate) {
    errors.push('DEFERRED_VALID requires activation_condition.predicate');
  }
  if (
    obligation.activation_condition?.horizon_turn == null
    && obligation.activation_condition?.narrative_predicate == null
  ) {
    errors.push('DEFERRED_VALID requires activation_condition.horizon_turn or narrative_predicate');
  }
  if (!obligation.obligation_id) {
    errors.push('obligation_id required for durable identity');
  }
  return { valid: errors.length === 0, errors };
}

export function createObligationRecord({
  obligationId,
  fixtureId,
  arm,
  originTurn,
  mechanism,
  activationCondition,
  decisionRelevant = true,
  deferralRationale = null,
  cognitionMechanism = null,
  persistenceLocation = null,
  authorizedConsumer = null,
  tokenAccounting = null,
}) {
  if (!PRESERVATION_MECHANISMS.includes(mechanism)) {
    throw new Error(`invalid preservation mechanism: ${mechanism}`);
  }
  return {
    schema: LH0_SCHEMAS.OBLIGATION,
    obligation_id: obligationId,
    fixture_id: fixtureId,
    arm,
    origin_turn: originTurn,
    preservation_mechanism: mechanism,
    activation_condition: activationCondition,
    decision_relevant: decisionRelevant,
    deferral_rationale: deferralRationale,
    cognition_mechanism: cognitionMechanism,
    persistence_location: persistenceLocation,
    authorized_consumer: authorizedConsumer,
    lifecycle_state: LIFECYCLE_STATES.GEN_UNUSED,
    dormancy_turns: 0,
    token_accounting: tokenAccounting ?? { input_tokens: 0, output_tokens: 0, reasoning_tokens: 0 },
    provenance: {
      responsible_cognition_mechanism: cognitionMechanism,
      creation_turn: originTurn,
    },
  };
}

export class ObligationLedger {
  constructor({ fixtureManifest = null } = {}) {
    this.fixtureManifest = fixtureManifest;
    this.obligations = new Map();
    this.events = [];
  }

  register(obligation) {
    if (this.obligations.has(obligation.obligation_id)) {
      throw new Error(`duplicate obligation_id: ${obligation.obligation_id}`);
    }
    this.obligations.set(obligation.obligation_id, { ...obligation });
    return obligation;
  }

  get(obligationId) {
    return this.obligations.get(obligationId) ?? null;
  }

  appendEvent(event) {
    const record = {
      schema: LH0_SCHEMAS.LIFECYCLE_EVENT,
      ...event,
      at_index: this.events.length,
    };
    this.events.push(record);
    if (event.obligation_id && this.obligations.has(event.obligation_id)) {
      const ob = this.obligations.get(event.obligation_id);
      if (event.lifecycle_state) {
        ob.lifecycle_state = event.lifecycle_state;
      }
      if (event.turn != null) {
        if (event.event_type === 'resurfaced') {
          ob.resurfacing_turn = event.turn;
        }
        if (ob.origin_turn != null && event.turn > ob.origin_turn) {
          ob.dormancy_turns = event.turn - (ob.last_touch_turn ?? ob.origin_turn);
        }
        ob.last_touch_turn = event.turn;
      }
      this.obligations.set(event.obligation_id, ob);
    }
    return record;
  }

  setLifecycleState(obligationId, lifecycleState, { turn = null, evidence = {} } = {}) {
    const ob = this.obligations.get(obligationId);
    if (!ob) throw new Error(`unknown obligation: ${obligationId}`);
    if (lifecycleState === LIFECYCLE_STATES.DEFERRED_VALID) {
      const check = validateDeferredValidContract({
        ...ob,
        decision_relevant: ob.decision_relevant,
        deferral_rationale: evidence.deferral_rationale ?? ob.deferral_rationale,
        activation_condition: ob.activation_condition,
        obligation_id: ob.obligation_id,
      });
      if (!check.valid) {
        throw new Error(`invalid DEFERRED_VALID: ${check.errors.join('; ')}`);
      }
    }
    ob.lifecycle_state = lifecycleState;
    this.obligations.set(obligationId, ob);
    return this.appendEvent({
      obligation_id: obligationId,
      turn,
      event_type: 'lifecycle_transition',
      lifecycle_state: lifecycleState,
      evidence,
    });
  }

  toArchaeologyRecord(obligationId) {
    const ob = this.obligations.get(obligationId);
    if (!ob) return null;
    const related = this.events.filter((e) => e.obligation_id === obligationId);
    return {
      schema: LH0_SCHEMAS.ARCHAEOLOGY_RECORD,
      obligation_id: obligationId,
      origin_turn: ob.origin_turn,
      responsible_cognition_mechanism: ob.cognition_mechanism,
      persistence_location: ob.persistence_location,
      preservation_mechanism: ob.preservation_mechanism,
      activation_predicate: ob.activation_condition,
      projection_events: related.filter((e) => e.event_type === 'projected'),
      receiving_consumer: ob.authorized_consumer,
      activation_turn: related.find((e) => e.event_type === 'activated')?.turn ?? null,
      decision_influence: related.find((e) => e.event_type === 'decision_influenced') ?? null,
      observable_consequence: related.find((e) => e.event_type === 'observable_consequence') ?? null,
      terminal_lifecycle_state: ob.lifecycle_state,
      event_chain: related,
    };
  }

  costAttributionSummary() {
    const rows = [...this.obligations.values()];
    const sumTokens = (obs) => obs.reduce((acc, o) => {
      acc.input += o.token_accounting?.input_tokens ?? 0;
      acc.output += o.token_accounting?.output_tokens ?? 0;
      return acc;
    }, { input: 0, output: 0 });
    const consequential = rows.filter((o) => o.lifecycle_state === LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL);
    const deferredValid = rows.filter((o) => o.lifecycle_state === LIFECYCLE_STATES.DEFERRED_VALID);
    const deferredToConsequential = rows.filter(
      (o) => o.lifecycle_state === LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL
        && this.events.some((e) => e.obligation_id === o.obligation_id && e.lifecycle_state === LIFECYCLE_STATES.DEFERRED_VALID),
    );
    const neverUseful = rows.filter((o) => (
      o.lifecycle_state === LIFECYCLE_STATES.TRACKED_DEAD
      || o.lifecycle_state === LIFECYCLE_STATES.CONSUMED_INERT
      || o.lifecycle_state === LIFECYCLE_STATES.GEN_UNUSED
    ));
    const premature = rows.filter((o) => o.lifecycle_state === LIFECYCLE_STATES.ACTIVATED_PREMATURE);
    const totalTokens = sumTokens(rows);
    return {
      schema: LH0_SCHEMAS.COST_ATTRIBUTION,
      persistent_tokens: totalTokens,
      activated_consequential_count: consequential.length,
      cost_per_activated_consequential: consequential.length
        ? totalTokens.input / consequential.length
        : null,
      deferred_valid_count: deferredValid.length,
      deferred_to_consequential_count: deferredToConsequential.length,
      never_useful_count: neverUseful.length,
      premature_activation_count: premature.length,
      persistence_yield: rows.length ? consequential.length / rows.length : 0,
    };
  }

  toJSON() {
    return {
      schema: LH0_SCHEMAS.OBLIGATION_TRACE,
      fixture_manifest_id: this.fixtureManifest?.fixture_id ?? null,
      obligations: [...this.obligations.values()],
      events: this.events,
      cost_attribution: this.costAttributionSummary(),
    };
  }
}
