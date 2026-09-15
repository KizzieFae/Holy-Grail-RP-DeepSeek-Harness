/**
 * Issue #201 LH-0 — consumption lifecycle tracer (L0–L4 + §10 states).
 */
import {
  LIFECYCLE_STATES,
  TRANSPORT_LEVELS,
  LIFECYCLE_EVENT_TYPES,
} from './issue201-lifecycle-states.mjs';
import { classifySeamFailure } from './issue201-seam-classifier.mjs';
import { ObligationLedger } from './issue201-obligation-ledger.mjs';

export function transportLevelFromFlags(flags) {
  if (flags.observable_consequence) return TRANSPORT_LEVELS.L4_CONSEQUENTIAL;
  if (flags.consumer_referenced) return TRANSPORT_LEVELS.L3_CONSUMER_REFERENCED;
  if (flags.projected) return TRANSPORT_LEVELS.L2_PROJECTED;
  if (flags.persisted) return TRANSPORT_LEVELS.L1_PERSISTED;
  if (flags.generated) return TRANSPORT_LEVELS.L0_GENERATED;
  return null;
}

/**
 * Enforce LH-0 consumption pathway configuration (fail-closed).
 * Detects G3-D class gap: persistence without projection.
 */
export function enforceConsumptionLifecycleConfig(armConfig) {
  const errors = [];
  if (!armConfig) {
    return { pass: false, errors: ['arm config missing'] };
  }
  if (armConfig.persistent_cognition_enabled && !armConfig.projection_lifecycle_enabled) {
    errors.push('G3-D class gap: persistent cognition enabled but projection_lifecycle_enabled=false');
  }
  if (armConfig.persistent_cognition_enabled && armConfig.consumption_lifecycle_enforcer !== true) {
    errors.push('consumption_lifecycle_enforcer must be true for persistent arms');
  }
  if (armConfig.persistent_cognition_enabled && armConfig.skip_character_knowledge_cognition === true) {
    errors.push('skip_character_knowledge_cognition must be false when persistent cognition projects to Character');
  }
  if (armConfig.arm === 'lh_d' && armConfig.unconditional_director_override === true) {
    errors.push('LH-D fairness violation: unconditional_director_override not permitted');
  }
  if (armConfig.arm === 'lh_d' && armConfig.route_trivial_director_through_persistent === true) {
    errors.push('LH-D fairness violation: trivial Director routing through persistent model');
  }
  return { pass: errors.length === 0, errors };
}

export class LifecycleTracer {
  constructor({ ledger = null, arm = null } = {}) {
    this.ledger = ledger ?? new ObligationLedger();
    this.arm = arm;
    this.g3d_gap_detected = false;
  }

  recordStage(obligationId, stage, { turn = null, evidence = {}, consumer = null } = {}) {
    const flags = {
      generated: false,
      persisted: false,
      projected: false,
      consumer_referenced: false,
      decision_influenced: false,
      observable_consequence: false,
    };
    const eventTypeMap = {
      [LIFECYCLE_EVENT_TYPES.GENERATED]: 'generated',
      [LIFECYCLE_EVENT_TYPES.PERSISTED]: 'persisted',
      [LIFECYCLE_EVENT_TYPES.PROJECTED]: 'projected',
      [LIFECYCLE_EVENT_TYPES.CONSUMER_RECEIVED]: 'consumer_received',
      [LIFECYCLE_EVENT_TYPES.CONSUMER_USED]: 'consumer_used',
      [LIFECYCLE_EVENT_TYPES.DECISION_INFLUENCED]: 'decision_influenced',
      [LIFECYCLE_EVENT_TYPES.OBSERVABLE_CONSEQUENCE]: 'observable_consequence',
      [LIFECYCLE_EVENT_TYPES.ACTIVATED]: 'activated',
      [LIFECYCLE_EVENT_TYPES.PREMATURE_ACTIVATION]: 'premature_activation',
      [LIFECYCLE_EVENT_TYPES.EXPIRED_DEAD]: 'expired_dead',
      [LIFECYCLE_EVENT_TYPES.DEFERRED_VALID]: 'deferred_valid',
    };

    const ob = this.ledger.get(obligationId);
    if (!ob) throw new Error(`unknown obligation: ${obligationId}`);

    if (stage === LIFECYCLE_EVENT_TYPES.GENERATED) flags.generated = true;
    if (stage === LIFECYCLE_EVENT_TYPES.PERSISTED) flags.persisted = true;
    if (stage === LIFECYCLE_EVENT_TYPES.PROJECTED) flags.projected = true;
    if (stage === LIFECYCLE_EVENT_TYPES.CONSUMER_USED) flags.consumer_referenced = true;
    if (stage === LIFECYCLE_EVENT_TYPES.DECISION_INFLUENCED) flags.decision_influenced = true;
    if (stage === LIFECYCLE_EVENT_TYPES.OBSERVABLE_CONSEQUENCE) flags.observable_consequence = true;

    const priorEvents = this.ledger.events.filter((e) => e.obligation_id === obligationId);
    const hadPersist = priorEvents.some((e) => e.event_type === LIFECYCLE_EVENT_TYPES.PERSISTED);
    const hadProject = priorEvents.some((e) => e.event_type === LIFECYCLE_EVENT_TYPES.PROJECTED);

    if (stage === LIFECYCLE_EVENT_TYPES.PERSISTED && hadPersist && !flags.projected) {
      // detect G3-D pattern at later turn without projection
      this.g3d_gap_detected = true;
    }
    if (hadPersist && stage === LIFECYCLE_EVENT_TYPES.CONSUMER_USED && !hadProject) {
      this.g3d_gap_detected = true;
    }

    let lifecycleState = ob.lifecycle_state;
    if (stage === LIFECYCLE_EVENT_TYPES.DEFERRED_VALID) {
      lifecycleState = LIFECYCLE_STATES.DEFERRED_VALID;
    } else if (stage === LIFECYCLE_EVENT_TYPES.PREMATURE_ACTIVATION) {
      lifecycleState = LIFECYCLE_STATES.ACTIVATED_PREMATURE;
    } else if (stage === LIFECYCLE_EVENT_TYPES.EXPIRED_DEAD) {
      lifecycleState = LIFECYCLE_STATES.TRACKED_DEAD;
    } else if (stage === LIFECYCLE_EVENT_TYPES.OBSERVABLE_CONSEQUENCE) {
      lifecycleState = LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL;
    } else if (stage === LIFECYCLE_EVENT_TYPES.CONSUMER_USED && !evidence.decision_relevant) {
      lifecycleState = LIFECYCLE_STATES.CONSUMED_INERT;
    } else if (stage === LIFECYCLE_EVENT_TYPES.PROJECTED && evidence.ignored_by_consumer) {
      lifecycleState = LIFECYCLE_STATES.PROJECT_IGNORED;
    } else if (stage === LIFECYCLE_EVENT_TYPES.PERSISTED && evidence.inaccessible) {
      lifecycleState = LIFECYCLE_STATES.PERSIST_INACCESSIBLE;
    }

    const event = this.ledger.appendEvent({
      obligation_id: obligationId,
      turn,
      event_type: eventTypeMap[stage] ?? stage,
      lifecycle_state: lifecycleState,
      transport_level: transportLevelFromFlags({
        generated: hadPersist || stage === LIFECYCLE_EVENT_TYPES.GENERATED,
        persisted: hadPersist || stage === LIFECYCLE_EVENT_TYPES.PERSISTED,
        projected: hadProject || stage === LIFECYCLE_EVENT_TYPES.PROJECTED,
        consumer_referenced: flags.consumer_referenced,
        observable_consequence: flags.observable_consequence,
      }),
      consumer,
      evidence,
      arm: this.arm,
    });

    if (lifecycleState !== ob.lifecycle_state) {
      this.ledger.setLifecycleState(obligationId, lifecycleState, { turn, evidence });
    }

    return event;
  }

  detectG3dClassGap() {
    const obligations = [...this.ledger.obligations.keys()];
    let detected = this.g3d_gap_detected;
    for (const obligationId of obligations) {
      const events = this.ledger.events.filter((e) => e.obligation_id === obligationId);
      const persisted = events.some((e) => e.event_type === 'persisted');
      const projected = events.some((e) => e.event_type === 'projected');
      if (persisted && !projected) detected = true;
    }
    return {
      detected,
      description: 'generation/persistence without L2+ projection/consumption (G3-D failure mode)',
    };
  }

  seamAttributionFor(obligationId, extra = {}) {
    const events = this.ledger.events.filter((e) => e.obligation_id === obligationId);
    const flags = {
      generated: events.some((e) => e.event_type === 'generated'),
      persisted: events.some((e) => e.event_type === 'persisted'),
      projected: events.some((e) => e.event_type === 'projected'),
      consumerReceived: events.some((e) => e.event_type === 'consumer_received'),
      consumerUsed: events.some((e) => e.event_type === 'consumer_used'),
      decisionInfluenced: events.some((e) => e.event_type === 'decision_influenced'),
      observableConsequence: events.some((e) => e.event_type === 'observable_consequence'),
      ...extra,
    };
    return classifySeamFailure(flags);
  }

  buildTraceExport(obligationId) {
    return this.ledger.toArchaeologyRecord(obligationId);
  }
}
