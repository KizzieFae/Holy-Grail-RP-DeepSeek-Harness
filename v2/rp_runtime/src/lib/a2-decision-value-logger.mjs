/**
 * Issue #201 G3 — per-inference decision-value accounting for A2 experiments.
 */

export function createDecisionValueLogger() {
  const records = [];

  return {
    records,
    record(entry) {
      records.push({
        inference_kind: entry.inference_kind ?? null,
        experimental_identity: entry.experimental_identity ?? null,
        consumer: entry.consumer ?? null,
        decision_purpose: entry.decision_purpose ?? null,
        unique_information: entry.unique_information ?? null,
        downstream_decision: entry.downstream_decision ?? null,
        deterministic_alternative_existed: entry.deterministic_alternative_existed ?? null,
        mandatory: entry.mandatory ?? null,
        obligation_trigger: entry.obligation_trigger ?? null,
        input_provenance: entry.input_provenance ?? null,
        wall_ms: entry.wall_ms ?? null,
        token_accounting: entry.token_accounting ?? null,
      });
    },
    toJSON() {
      return { schema: 'issue201_g3_decision_value_v1', records };
    },
  };
}
