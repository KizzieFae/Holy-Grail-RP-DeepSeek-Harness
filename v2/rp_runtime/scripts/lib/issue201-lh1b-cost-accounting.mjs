/**
 * Issue #201 LH-1B — cost attribution from execution-evidence attempts.
 */
import { LH1B_SCHEMAS } from './issue201-lh1b-contract.mjs';
import { LIFECYCLE_STATES } from './issue201-lifecycle-states.mjs';

const PERSISTENT_KINDS = new Set([
  'plot_cognition_init',
  'plot_cognition_update',
  'plot_cognition_epistemic_eval',
  'storyteller_post_commit_issue_pressure',
  'consolidated_narrative_intelligence',
]);

export function attemptsToInferenceEvents(attempts = []) {
  return attempts.map((row) => ({
    inference_kind: row.correlation?.inference_kind ?? row.inference_kind ?? 'unknown',
    input_tokens: row.response?.usage?.input_tokens
      ?? row.usage?.input_tokens
      ?? row.input_tokens
      ?? 0,
    output_tokens: row.response?.usage?.output_tokens
      ?? row.usage?.output_tokens
      ?? row.output_tokens
      ?? 0,
    reasoning_tokens: row.response?.usage?.reasoning_tokens
      ?? row.usage?.reasoning_tokens
      ?? row.reasoning_tokens
      ?? 0,
    wall_ms: row.inference_health?.inference_wall_clock_ms
      ?? row.wall_ms
      ?? 0,
    async: row.correlation?.inference_kind === 'storyteller_post_commit_issue_pressure',
    evidence_id: row.evidence_id ?? row.correlation?.evidence_id,
    hg_round_id: row.correlation?.hg_round_id,
  }));
}

export function buildLh1bCostRollup({
  arm,
  sequenceId,
  inferenceEvents = [],
  obligationLedger = null,
  forkInfluenceCount = 0,
  r5Count = 0,
}) {
  const byResponsibility = {};
  let inputTokens = 0;
  let outputTokens = 0;
  let reasoningTokens = 0;
  let wallMs = 0;
  let persistentCalls = 0;
  let persistentTokens = 0;

  for (const ev of inferenceEvents) {
    const kind = ev.inference_kind ?? 'unknown';
    byResponsibility[kind] = (byResponsibility[kind] ?? 0) + 1;
    inputTokens += ev.input_tokens ?? 0;
    outputTokens += ev.output_tokens ?? 0;
    reasoningTokens += ev.reasoning_tokens ?? 0;
    wallMs += ev.wall_ms ?? 0;
    if (PERSISTENT_KINDS.has(kind)) {
      persistentCalls += 1;
      persistentTokens += (ev.input_tokens ?? 0) + (ev.output_tokens ?? 0) + (ev.reasoning_tokens ?? 0);
    }
  }

  const obligations = obligationLedger
    ? [...obligationLedger.obligations.values()]
    : [];
  const consequential = obligations.filter((o) => (
    o.lifecycle_state === LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL
  ));

  return {
    schema: LH1B_SCHEMAS.COST_ROLLUP,
    arm,
    sequence_id: sequenceId,
    total_inference_calls: inferenceEvents.length,
    inference_calls_by_responsibility: byResponsibility,
    persistent_cognition_calls: persistentCalls,
    input_tokens: inputTokens,
    output_tokens: outputTokens,
    reasoning_tokens: reasoningTokens,
    wall_ms_total: wallMs,
    persistent_cognition_tokens: persistentTokens,
    generated_obligations: obligations.length,
    consequential_activations: consequential.length,
    cost_per_demonstrated_influence: forkInfluenceCount > 0
      ? persistentTokens / forkInfluenceCount
      : null,
    cost_per_r5_marginal_value: r5Count > 0 ? persistentTokens / r5Count : null,
    fork_influence_count: forkInfluenceCount,
    r5_marginal_value_count: r5Count,
  };
}
