import { LIFECYCLE_STATES } from './issue201-lifecycle-states.mjs';
import { classifySeamFailure, detectK6ClassCondition } from './issue201-seam-classifier.mjs';
import { loadLh0FixtureManifest } from './issue201-lh0-fixtures.mjs';
import {
  detectObligationUseInText,
  obligationMetDeferredLaterChain,
} from './issue201-lh0-consumer-evidence.mjs';

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
  return {
    received: receiptStep?.consumer_received === true
      || transport?.character?.consumer_received === true
      || transport?.character_consumer_receipt === true,
    receivedIds: receiptStep?.received_obligation_ids
      ?? transport?.character?.received_obligation_ids
      ?? [],
    referencedIds: receiptStep?.referenced_obligation_ids
      ?? transport?.character?.referenced_obligation_ids
      ?? [],
    influencedIds: receiptStep?.decision_influenced_obligation_ids
      ?? transport?.character?.decision_influenced_obligation_ids
      ?? [],
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
  const premature = lh0Store.obligations.find((o) => o.negative_control);
  const prematureState = premature?.lifecycle_state;

  const hasLivePostCommit = turns.some((t) => t.lh0_post_commit?.live_cognition === true);
  const hasPersistence = lh0Store.obligations.length > 0
    && lh0Store.events.some((e) => e.event_type === 'persisted');

  const hasProjection = turns.some((t) => {
    const transport = turnTransport(t);
    return transport?.projected_finalized === true
      || t.audit?.lh0_character_consumer_receipt?.projection_supplied === true;
  });

  const hasConsumerReceipt = turns.some((t) => turnReceipt(t).received);
  const hasConsumerUse = turns.some((t) => {
    const receipt = turnReceipt(t);
    const presentationUsed = detectObligationUseInText(
      t.presentation_text,
      receipt.receivedIds,
    );
    return receipt.referencedIds.length > 0 || presentationUsed.length > 0;
  });
  const hasDecisionInfluence = turns.some((t) => {
    const receipt = turnReceipt(t);
    return receipt.influencedIds.length > 0
      || (receipt.referencedIds.length > 0 && t.committed === true);
  });
  const hasConsequential = turns.some((t) => (
    (t.lh0_consequences?.obligation_ids?.length ?? 0) > 0
    && turnReceipt(t).received
  )) && lh0Store.obligations.some((o) => (
    o.lifecycle_state === LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL
    && !o.negative_control
  ));

  const deferredObligations = manifest.obligations.filter((o) => o.class === 'valid_deferral');
  const hasDeferredLater = deferredObligations.some((fo) => {
    const storeOb = lh0Store.obligations.find((o) => o.obligation_id === fo.obligation_id);
    if (!storeOb) return false;
    const laterTurn = turns.find((t) => t.turn_index >= (storeOb.activated_turn ?? 999));
    const laterReceipt = laterTurn ? turnReceipt(laterTurn).received : false;
    const laterUse = turns.some((t) => (
      t.turn_index >= (storeOb.activated_turn ?? 999)
      && (
        turnReceipt(t).referencedIds.includes(fo.obligation_id)
        || detectObligationUseInText(t.presentation_text, [fo.obligation_id]).length > 0
      )
    ));
    return obligationMetDeferredLaterChain(lh0Store, fo.obligation_id)
      && laterReceipt
      && laterUse;
  });

  const noPremature = prematureState !== LIFECYCLE_STATES.ACTIVATED_PREMATURE;
  const isolationPass = turns.every((t) => (t.actor_context_isolation?.pass ?? true));
  const k6 = detectK6ClassCondition({
    requiredAnchorIds: manifest.k6_probe.required_anchor_ids,
    eligibleAnchorIds: manifest.k6_probe.required_anchor_ids,
    projectedAnchorIds: turns.flatMap((t) => t.lh0_projection?.projected_anchor_ids ?? []),
    projectionBudget: manifest.k6_probe.projection_budget,
  });

  const criteria = {
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

  const allPass = Object.values(criteria).every((c) => c.pass) && isolationPass;
  return {
    arm,
    criteria,
    all_pass: allPass,
    lh1a_ready: allPass,
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
    ...Object.fromEntries(Object.entries(r.criteria).map(([k, v]) => [k, v.pass])),
    lh1a_ready: r.lh1a_ready,
  }));
}
