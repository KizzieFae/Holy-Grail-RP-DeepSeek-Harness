import fs from 'node:fs';
import path from 'node:path';

import { LIFECYCLE_STATES } from './issue201-lifecycle-states.mjs';
import { validateDeferredValidContract } from './issue201-obligation-ledger.mjs';
import {
  LH0_SEMANTIC_PROJECTION_PRIORITY,
  resolveLh0ModelFacingContent,
} from './issue201-lh0-semantic-content.mjs';

export function lh0StorePath(sessionsDir, hgSessionId) {
  const safe = String(hgSessionId).replace(/[/\\]/g, '_');
  return path.join(sessionsDir, '_lh0_persistent_obligations', `${safe}.json`);
}

export function readLh0Store(sessionsDir, hgSessionId) {
  const p = lh0StorePath(sessionsDir, hgSessionId);
  if (!fs.existsSync(p)) {
    return { schema: 'issue201_lh0_persistent_store_v1', obligations: [], events: [] };
  }
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

export function writeLh0Store(sessionsDir, hgSessionId, store) {
  const p = lh0StorePath(sessionsDir, hgSessionId);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, `${JSON.stringify(store, null, 2)}\n`);
  return p;
}

export function upsertLh0Obligation(store, obligation, { turn, inferenceId, mechanism }) {
  const idx = store.obligations.findIndex((o) => o.obligation_id === obligation.obligation_id);
  const row = {
    ...obligation,
    last_inference_id: inferenceId,
    cognition_mechanism: mechanism,
    persistence_location: 'sessions/_lh0_persistent_obligations',
    updated_turn: turn,
  };
  if (idx >= 0) store.obligations[idx] = { ...store.obligations[idx], ...row };
  else store.obligations.push(row);
  store.events.push({
    turn,
    obligation_id: obligation.obligation_id,
    event_type: 'persisted',
    inference_id: inferenceId,
    mechanism,
  });
  return store;
}

export function evaluateActivationPredicate(predicate, turn) {
  if (!predicate) return false;
  if (predicate.type === 'turn_gte') return turn >= Number(predicate.value);
  return false;
}

export function obligationsForConsumer(store, { turn, consumer }) {
  return store.obligations.filter((o) => {
    if (o.authorized_consumer && o.authorized_consumer !== consumer) return false;
    if (o.negative_control) return false;
    return evaluateActivationPredicate(o.activation_predicate, turn);
  });
}

export function buildLh0FinalizedProjection(obligations, {
  batchId,
  consumer,
  characterId = null,
  hgRoundId = null,
  turnIndex = null,
  bindingDigest = null,
}) {
  if (!obligations.length) return null;
  const digest = bindingDigest ?? `lh0-${obligations.map((o) => o.obligation_id).join('|')}`;
  const binding = {
    schema: 'issue201_lh0_projection_binding_v1',
    batch_id: batchId,
    binding_digest: digest,
    hg_round_id: hgRoundId,
    turn_index: turnIndex,
    consumer,
    ...(characterId ? { character_id: characterId } : {}),
  };
  const sourceKind = consumer === 'director_turn' ? 'scene_pressures' : 'active_constraints';
  const contributions = obligations.map((o, index) => ({
    contribution_id: `lh0-${batchId}-${o.obligation_id}`,
    source_kind: sourceKind,
    authority_class: 'derived',
    knowledge_ids: [`lh0-obligation:${o.obligation_id}`],
    priority: LH0_SEMANTIC_PROJECTION_PRIORITY + index,
    content: resolveLh0ModelFacingContent(o),
    provenance: {
      lh0_obligation_id: o.obligation_id,
      lh0_fixture_class: o.class ?? null,
      lh0_authorized_consumer: o.authorized_consumer ?? consumer,
      finalized_projection: true,
    },
  }));
  return {
    batch_id: batchId,
    binding_digest: digest,
    binding,
    contributions,
    inference_kind: consumer === 'director_turn' ? 'director_turn' : 'character_turn',
  };
}

export function classifyLh0ObligationStates(store, turn) {
  for (const ob of store.obligations) {
    const due = evaluateActivationPredicate(ob.activation_predicate, turn);
    if (ob.negative_control && due && turn < ob.activation_horizon_turn) {
      ob.lifecycle_state = LIFECYCLE_STATES.ACTIVATED_PREMATURE;
      continue;
    }
    if (!due && turn < ob.activation_horizon_turn && ob.intro_turn < turn) {
      const check = validateDeferredValidContract({
        obligation_id: ob.obligation_id,
        decision_relevant: true,
        deferral_rationale: ob.deferral_rationale ?? 'activation predicate not yet satisfied',
        activation_condition: {
          predicate: ob.activation_predicate,
          horizon_turn: ob.activation_horizon_turn,
        },
      });
      const deferredState = check.valid ? LIFECYCLE_STATES.DEFERRED_VALID : LIFECYCLE_STATES.TRACKED_DEAD;
      if (ob.lifecycle_state !== deferredState) {
        ob.lifecycle_state = deferredState;
        if (check.valid) {
          store.events.push({
            turn,
            obligation_id: ob.obligation_id,
            event_type: 'deferred_valid',
            lifecycle_state: deferredState,
          });
        }
      }
    }
    if (due && ob.activated_turn == null) {
      ob.activated_turn = turn;
      ob.lifecycle_state = LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL;
      store.events.push({
        turn,
        obligation_id: ob.obligation_id,
        event_type: 'activated_consequential',
        lifecycle_state: LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL,
      });
    }
  }
  return store;
}
