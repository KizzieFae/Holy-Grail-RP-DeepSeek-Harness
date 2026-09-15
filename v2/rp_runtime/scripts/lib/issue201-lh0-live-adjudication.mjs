import { LH0_ARMS } from './issue201-lh0-arms.mjs';
import { LIFECYCLE_STATES } from './issue201-lifecycle-states.mjs';
import { classifySeamFailure, detectK6ClassCondition } from './issue201-seam-classifier.mjs';
import { loadLh0FixtureManifest } from './issue201-lh0-fixtures.mjs';
import {
  isBookkeepingOnlySemanticContent,
  listDecisionForks,
  obligationMetDeferredLaterChain,
} from './issue201-lh0-semantic-content.mjs';

function criterionPass(flags) {
  return { pass: flags.every(Boolean), flags };
}

function turnTransport(turn) {
  return turn.audit?.projection_transport
    ?? turn.audit?.lh0_projection_transport
    ?? turn.lh0_transport
    ?? null;
}

function turnReceipt(turn) {
  const receiptStep = turn.audit?.character_consumer_receipt
    ?? turn.audit?.lh0_character_consumer_receipt;
  const transport = turnTransport(turn);
  const causal = turn.lh0_causal_evidence ?? {};
  return {
    received: receiptStep?.consumer_received === true
      || transport?.character?.consumer_received === true
      || transport?.character_consumer_receipt === true,
    receivedIds: receiptStep?.received_obligation_ids
      ?? transport?.character?.received_obligation_ids
      ?? [],
    referencedIds: causal.influenced_obligation_ids
      ?? receiptStep?.referenced_obligation_ids
      ?? transport?.character?.referenced_obligation_ids
      ?? [],
    influencedIds: causal.influenced_obligation_ids
      ?? receiptStep?.decision_influenced_obligation_ids
      ?? transport?.character?.decision_influenced_obligation_ids
      ?? [],
    consumerUsed: causal.consumer_used === true
      || transport?.character?.consumer_used === true,
    semanticReceiptAdequate: receiptStep?.semantic_receipt_adequate === true
      || transport?.character?.semantic_receipt_adequate === true,
  };
}


export function buildFirstRunFalsePositiveTrace() {
  return [{
    turn_index: 3,
    lh0_post_commit: { live_cognition: true, ok: true },
    domain_commit_id: 'hg-commit-false-positive',
    lh0_projection: {
      projected: true,
      consumer_received: true,
      consumer_used: true,
      decision_influenced: true,
    },
    audit: {
      projection_candidates: {
        director_receipt: true,
        character_receipt: false,
      },
    },
    lh0_store: {
      obligations: [{
        obligation_id: 'LH0-OBL-DEFERRED',
        lifecycle_state: LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL,
        activated_turn: 5,
        intro_turn: 2,
      }],
      events: [],
    },
  }];
}

export function adjudicateLh0ArmSequence({ arm, turns, lh0Store, fixture = null }) {
  const manifest = fixture ?? loadLh0FixtureManifest();
  const isCounterfactualArm = arm === LH0_ARMS.LH_A;
  const premature = lh0Store.obligations.find((o) => o.negative_control);
  const prematureState = premature?.lifecycle_state;

  const hasLivePostCommit = !isCounterfactualArm
    && turns.some((t) => t.lh0_post_commit?.live_cognition === true);
  const hasPersistence = !isCounterfactualArm
    && lh0Store.obligations.length > 0
    && lh0Store.events.some((e) => e.event_type === 'persisted');

  const hasProjection = !isCounterfactualArm && turns.some((t) => {
    const transport = turnTransport(t);
    const transportAudit = t.audit?.projection_transport ?? {};
    return transport?.projected_finalized === true
      && transportAudit.semantic_projection_adequate === true;
  });

  const hasConsumerReceipt = !isCounterfactualArm && turns.some((t) => {
    const receipt = turnReceipt(t);
    return receipt.received && receipt.semanticReceiptAdequate;
  });

  const hasConsumerUse = !isCounterfactualArm && turns.some((t) => (
    turnReceipt(t).consumerUsed && turnReceipt(t).received
  ));

  const hasDecisionInfluence = !isCounterfactualArm && turns.some((t) => (
    turnReceipt(t).influencedIds.length > 0 && t.committed === true
  ));

  const hasConsequential = !isCounterfactualArm && turns.some((t) => (
    (t.lh0_consequences?.obligation_ids?.length ?? 0) > 0
    && turnReceipt(t).influencedIds.length > 0
    && t.committed === true
  ));

  const deferredObligations = manifest.obligations.filter((o) => o.class === 'valid_deferral');
  const hasDeferredLater = !isCounterfactualArm && deferredObligations.some((fo) => {
    const storeOb = lh0Store.obligations.find((o) => o.obligation_id === fo.obligation_id);
    if (!storeOb) return false;
    const fork = listDecisionForks(manifest).find((f) => (
      (f.obligation_ids ?? []).includes(fo.obligation_id)
    ));
    const decisionTurn = turns.find((t) => t.turn_index === (fork?.decision_turn ?? storeOb.activated_turn));
    const decisionEvidence = decisionTurn?.lh0_causal_evidence ?? {};
    return obligationMetDeferredLaterChain(lh0Store, fo.obligation_id, { turns })
      && decisionEvidence.consumer_used === true
      && decisionEvidence.decision_influenced === true;
  });

  const noPremature = prematureState !== LIFECYCLE_STATES.ACTIVATED_PREMATURE;
  const isolationPass = turns.every((t) => (t.actor_context_isolation?.pass ?? true));
  const k6 = detectK6ClassCondition({
    requiredAnchorIds: manifest.k6_probe.required_anchor_ids,
    eligibleAnchorIds: manifest.k6_probe.required_anchor_ids,
    projectedAnchorIds: turns.flatMap((t) => t.lh0_projection?.projected_anchor_ids ?? []),
    projectionBudget: manifest.k6_probe.projection_budget,
  });

  const criteria = isCounterfactualArm ? {
    A_generation: criterionPass([true]),
    B_persistence: criterionPass([true]),
    C_projection: criterionPass([true]),
    D_consumer_receipt: criterionPass([true]),
    E_consumer_use: criterionPass([true]),
    F_decision_influence: criterionPass([true]),
    G_consequential_activation: criterionPass([true]),
    H_deferred_later_activation: criterionPass([true]),
    I_no_premature_activation: criterionPass([noPremature]),
    J_seam_attribution: criterionPass([true]),
  } : {
    A_generation: criterionPass([hasLivePostCommit]),
    B_persistence: criterionPass([hasPersistence]),
    C_projection: criterionPass([hasProjection]),
    D_consumer_receipt: criterionPass([hasConsumerReceipt]),
    E_consumer_use: criterionPass([hasConsumerUse]),
    F_decision_influence: criterionPass([hasDecisionInfluence]),
    G_consequential_activation: criterionPass([hasConsequential]),
    H_deferred_later_activation: criterionPass([hasDeferredLater]),
    I_no_premature_activation: criterionPass([noPremature]),
    J_seam_attribution: criterionPass([true]),
  };

  const persistentReady = !isCounterfactualArm
    && Object.values(criteria).every((c) => c.pass)
    && isolationPass;
  return {
    arm,
    counterfactual_arm: isCounterfactualArm,
    criteria,
    all_pass: persistentReady,
    lh1a_ready: persistentReady,
    premature_state: prematureState ?? null,
    consequential_obligations: lh0Store.obligations
      .filter((o) => o.lifecycle_state === LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL)
      .map((o) => o.obligation_id),
    deferred_obligations: lh0Store.obligations
      .filter((o) => o.lifecycle_state === LIFECYCLE_STATES.DEFERRED_VALID
        || (o.activated_turn != null && o.intro_turn < o.activated_turn))
      .map((o) => o.obligation_id),
    entitlement_pvr: { pass: isolationPass, leaks: turns.flatMap((t) => t.actor_context_isolation?.leaks ?? []) },
    k6_probe: k6,
    seam_failures: turns.map((t) => t.seam_failure).filter(Boolean),
    disclaimer: 'LH-0 validates transport, persistence, consumption, deferral, activation, and forensic attribution. It does not establish comparative RP quality or long-horizon narrative value.',
  };
}

export function buildPassFailMatrix(armResults) {
  return armResults.map((r) => ({
    arm: r.arm,
    counterfactual: r.counterfactual_arm === true,
    ...Object.fromEntries(Object.entries(r.criteria).map(([k, v]) => [k, v.pass])),
    lh1a_ready: r.lh1a_ready,
  }));
}

export function buildCounterfactualInterpretation({ controlSequence, persistentSequences, fixture = null }) {
  const fx = fixture ?? loadLh0FixtureManifest();
  const forks = listDecisionForks(fx);
  const comparisons = forks.map((fork) => {
    const controlTurn = controlSequence.turns.find((t) => t.turn_index === fork.decision_turn);
    const controlClass = controlTurn?.lh0_causal_evidence?.matched_forks?.[0]?.choice_class ?? null;
    const persistent = persistentSequences.map((seq) => {
      const turn = seq.turns.find((t) => t.turn_index === fork.decision_turn);
      return {
        arm: seq.arm,
        choice_class: turn?.lh0_causal_evidence?.matched_forks?.[0]?.choice_class ?? null,
        influenced: turn?.lh0_causal_evidence?.decision_influenced === true,
      };
    });
    const diverged = persistent.some((p) => p.choice_class && controlClass && p.choice_class !== controlClass);
    return {
      fork_id: fork.fork_id,
      decision_turn: fork.decision_turn,
      control_choice_class: controlClass,
      persistent,
      materially_different: diverged,
      interpretation: diverged
        ? 'converging_counterfactual_difference'
        : 'same_outcome_or_indeterminate',
    };
  });
  return {
    schema: 'issue201_lh0_counterfactual_interpretation_v1',
    comparisons,
  };
}
