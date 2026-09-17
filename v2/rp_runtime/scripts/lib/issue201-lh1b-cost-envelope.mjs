/**
 * Issue #201 LH-1B — corrected live cost envelope from LH-1A observed aggregates.
 *
 * Inference event definition: one execution-evidence attempt record with
 * correlation.inference_kind (same as summarizeAttempts / buildCostRollup).
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { LH1B_SCHEMAS, LH1B_TURN_COUNT, LH1B_LIVE_EXECUTION_ORDER } from './issue201-lh1b-contract.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../../..');
const LH1A_INTEGRITY_PATH = path.join(
  REPO_ROOT,
  'governance/records/issue201-lh1a-evaluation/issue201-lh1a-blind-integrity-report.json',
);

const LH1A_CAMPAIGN_TOTAL = Object.freeze({
  inference_events: 782,
  player_turns: 176,
  events_per_player_turn: 782 / 176,
});

function loadLh1aIntegrityCosts() {
  if (!fs.existsSync(LH1A_INTEGRITY_PATH)) return null;
  return JSON.parse(fs.readFileSync(LH1A_INTEGRITY_PATH, 'utf8')).costs ?? null;
}

function perTurnFromArm(costs, arm) {
  const row = costs?.byArm?.[arm];
  if (!row || !row.turns) return null;
  return {
    inference_events_per_turn: row.inference_count / row.turns,
    input_tokens_per_turn: row.input_tokens / row.turns,
    output_tokens_per_turn: row.output_tokens / row.turns,
    reasoning_tokens_per_turn: row.reasoning_tokens / row.turns,
    wall_ms_per_turn: row.wall_ms / row.turns,
    persistent_obligations_per_turn: (row.generated_obligations ?? 0) / row.turns,
  };
}

function ayamePerTurnFromScenario(costs) {
  const row = costs?.byScenario?.ayame_controlled;
  if (!row || !row.turns) return null;
  return row.inference_count / row.turns;
}

/**
 * Prior LH-1B report used ~29 inferences/turn by conflating per-round LLM call budget
 * (decision_value.records / efficiency.llm_call_count semantics) with execution-evidence
 * attempt records. LH-1A observed aggregate is 782 events / 176 turns ≈ 4.44.
 */
export function explainLh1bCostEstimateCorrection() {
  return {
    prior_estimate_error: '~29 inferences/turn assumed multi-phase round internals as evidence attempts',
    lh1a_observed_aggregate: LH1A_CAMPAIGN_TOTAL,
    authoritative_definition: 'execution-evidence attempt with correlation.inference_kind',
    ayame_only_rate: ayamePerTurnFromScenario(loadLh1aIntegrityCosts()),
  };
}

export function buildLh1bCostEnvelope() {
  const lh1aCosts = loadLh1aIntegrityCosts();
  const perArm = {
    lh_a: perTurnFromArm(lh1aCosts, 'lh_a'),
    lh_b: perTurnFromArm(lh1aCosts, 'lh_b'),
    lh_d: perTurnFromArm(lh1aCosts, 'lh_d'),
  };
  const fallbackAyame = ayamePerTurnFromScenario(lh1aCosts) ?? LH1A_CAMPAIGN_TOTAL.events_per_player_turn;

  const sequences = LH1B_LIVE_EXECUTION_ORDER.map((slot) => {
    const rate = perArm[slot.arm]?.inference_events_per_turn ?? fallbackAyame;
    const expectedEvents = Math.round(rate * LH1B_TURN_COUNT);
    const persistentKinds = slot.arm === 'lh_a' ? 0 : expectedEvents * 0.35;
    return {
      blind_label: slot.blind_label,
      arm: slot.arm,
      turns: LH1B_TURN_COUNT,
      expected_inference_events: expectedEvents,
      expected_persistent_specific_events: Math.round(persistentKinds),
      expected_input_tokens: perArm[slot.arm]
        ? Math.round(perArm[slot.arm].input_tokens_per_turn * LH1B_TURN_COUNT)
        : null,
      expected_output_tokens: perArm[slot.arm]
        ? Math.round(perArm[slot.arm].output_tokens_per_turn * LH1B_TURN_COUNT)
        : null,
      expected_reasoning_tokens: perArm[slot.arm]
        ? Math.round(perArm[slot.arm].reasoning_tokens_per_turn * LH1B_TURN_COUNT)
        : null,
      expected_wall_ms: perArm[slot.arm]
        ? Math.round(perArm[slot.arm].wall_ms_per_turn * LH1B_TURN_COUNT)
        : null,
    };
  });

  const totalEvents = sequences.reduce((n, s) => n + s.expected_inference_events, 0);
  const totalWall = sequences.reduce((n, s) => n + (s.expected_wall_ms ?? 0), 0);

  return {
    schema: LH1B_SCHEMAS.COST_ENVELOPE,
    correction: explainLh1bCostEstimateCorrection(),
    lh1a_baseline: {
      total_inference_events: LH1A_CAMPAIGN_TOTAL.inference_events,
      total_player_turns: LH1A_CAMPAIGN_TOTAL.player_turns,
      events_per_player_turn: LH1A_CAMPAIGN_TOTAL.events_per_player_turn,
      per_arm_per_turn: perArm,
      ayame_scenario_per_turn: fallbackAyame,
    },
    lh1b_campaign: {
      sequences,
      total_player_turns: LH1B_TURN_COUNT * sequences.length,
      expected_inference_events: totalEvents,
      expected_events_per_player_turn: totalEvents / (LH1B_TURN_COUNT * sequences.length),
      expected_wall_ms_total: totalWall,
      expected_wall_hours: totalWall ? totalWall / 3_600_000 : null,
    },
    uncertainty: {
      structural_retry_multiplier: '1.0–1.4× events if character structural retries recur at LH-1A rates',
      director_t15_extra: 'LH-D S5 may add one director_turn attempt at T15 (+1 event)',
      token_variance: '±15% from transcript growth and retry count',
      wall_time_variance: 'model latency and retry count dominate; use LH-1A ayame wall/turn as prior',
    },
    no_token_ceiling: true,
  };
}
