/**
 * Issue #201 LH-1A — cost / topology accounting rollup.
 */
import { LH1A_SCHEMAS } from './issue201-lh1a-contract.mjs';
import { LIFECYCLE_STATES } from './issue201-lifecycle-states.mjs';

export function buildCostRollup({
  arm,
  sequenceId,
  inferenceEvents = [],
  obligationLedger = null,
}) {
  const byResponsibility = {};
  let syncCount = 0;
  let asyncCount = 0;
  let inputTokens = 0;
  let outputTokens = 0;
  let reasoningTokens = 0;
  let wallMs = 0;
  for (const ev of inferenceEvents) {
    const kind = ev.inference_kind ?? ev.responsibility ?? 'unknown';
    byResponsibility[kind] = (byResponsibility[kind] ?? 0) + 1;
    if (ev.async === true) asyncCount += 1;
    else syncCount += 1;
    inputTokens += ev.input_tokens ?? 0;
    outputTokens += ev.output_tokens ?? 0;
    reasoningTokens += ev.reasoning_tokens ?? 0;
    wallMs += ev.wall_ms ?? 0;
  }
  const costBase = obligationLedger?.costAttributionSummary?.() ?? {};
  const obligations = obligationLedger
    ? [...obligationLedger.obligations.values()]
    : [];
  const consequential = obligations.filter((o) => o.lifecycle_state === LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL);
  const deferredValid = obligations.filter((o) => o.lifecycle_state === LIFECYCLE_STATES.DEFERRED_VALID);
  const neverUseful = obligations.filter((o) => (
    o.lifecycle_state === LIFECYCLE_STATES.TRACKED_DEAD
    || o.lifecycle_state === LIFECYCLE_STATES.CONSUMED_INERT
  ));
  const premature = obligations.filter((o) => o.lifecycle_state === LIFECYCLE_STATES.ACTIVATED_PREMATURE);
  const persistentTokens = inputTokens + outputTokens + reasoningTokens;
  return {
    schema: LH1A_SCHEMAS.COST_ROLLUP,
    arm,
    sequence_id: sequenceId,
    total_inference_calls: inferenceEvents.length,
    inference_calls_by_responsibility: byResponsibility,
    synchronous_calls: syncCount,
    asynchronous_calls: asyncCount,
    input_tokens: inputTokens,
    output_tokens: outputTokens,
    reasoning_tokens: reasoningTokens,
    wall_ms_total: wallMs,
    persistent_cognition_tokens: persistentTokens,
    generated_obligations: obligations.length,
    useful_deferred_obligations: deferredValid.length,
    consequential_activations: consequential.length,
    premature_activations: premature.length,
    tracked_dead_obligations: neverUseful.length,
    cost_per_consequential_obligation: consequential.length
      ? persistentTokens / consequential.length
      : null,
    persistence_yield: obligations.length ? consequential.length / obligations.length : 0,
    deferred_precision: deferredValid.length
      ? consequential.filter((o) => deferredValid.some((d) => d.obligation_id === o.obligation_id)).length / deferredValid.length
      : null,
    never_useful_rate: obligations.length ? neverUseful.length / obligations.length : 0,
    premature_activation_rate: obligations.length ? premature.length / obligations.length : 0,
    alters_inference_behavior: false,
    ...costBase,
  };
}
