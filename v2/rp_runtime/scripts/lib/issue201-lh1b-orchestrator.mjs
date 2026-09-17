/**
 * Issue #201 LH-1B — campaign orchestrator (planning; no live inference).
 */
import crypto from 'node:crypto';
import path from 'node:path';

import { buildLh0ArmConfig } from './issue201-lh0-arms.mjs';
import { gitSha } from './issue201-lh0-lib.mjs';
import {
  LH1B_CHECKPOINTS,
  LH1B_LIVE_EXECUTION_ORDER,
  LH1B_SCHEMAS,
  LH1B_TURN_COUNT,
  buildLh1bCampaignMatrix,
} from './issue201-lh1b-contract.mjs';
import {
  fixturePathForScenario,
  loadLh1bFixtureManifest,
  sceneForTurn,
} from './issue201-lh1b-fixtures.mjs';
import {
  loadLh1bPolicy,
  selectLh1bPlayerStimulus,
  sha256File,
} from './issue201-lh1b-player-policy.mjs';

export function buildLh1bSequencePlan({ arm, scenarioKey, blindLabel = null }) {
  const armConfig = buildLh0ArmConfig(arm);
  const fixture = loadLh1bFixtureManifest(scenarioKey);
  const { policy, policy_hash } = loadLh1bPolicy(scenarioKey);
  if (policy.fixture_id !== fixture.fixture_id) {
    throw new Error(`policy/fixture mismatch: ${policy.fixture_id} vs ${fixture.fixture_id}`);
  }
  const fixturePath = fixturePathForScenario(scenarioKey);
  const turns = [];
  for (let turnIndex = 1; turnIndex <= fixture.turns; turnIndex += 1) {
    const scene = sceneForTurn(fixture, turnIndex);
    turns.push({
      turn_index: turnIndex,
      scene_id: scene?.scene_id ?? null,
      player_stimulus: selectLh1bPlayerStimulus(policy, turnIndex),
      checkpoint: Object.entries(LH1B_CHECKPOINTS).find(([, t]) => t === turnIndex)?.[0] ?? null,
      director_inference_required: arm === 'lh_d' && turnIndex === 15,
    });
  }
  const sequenceId = `LH1B-PLAN-${arm}-${scenarioKey}-${crypto.randomUUID().slice(0, 8)}`;
  return {
    schema: LH1B_SCHEMAS.CAMPAIGN_PLAN,
    sequence_id: sequenceId,
    blind_label: blindLabel,
    arm,
    arm_label: armConfig.label,
    scenario_key: scenarioKey,
    scenario_id: fixture.scenario_id,
    fixture_id: fixture.fixture_id,
    fixture_hash: sha256File(fixturePath),
    policy_id: policy.policy_id,
    policy_hash,
    turn_count: fixture.turns,
    scene_count: fixture.scenes.length,
    scene_transition_turn: fixture.scene_transition_turn,
    checkpoints: fixture.checkpoints,
    arm_config: armConfig,
    persistent_cognition_enabled: armConfig.persistent_cognition_enabled,
    fork_ids: fixture.causal_design.decision_forks.map((f) => f.fork_id),
    turns,
    isolation: {
      dedicated_session: true,
      no_cross_sequence_store: true,
      lh_a_blocks_persistent_projection: arm === 'lh_a',
    },
  };
}

export function buildLh1bCampaignPlan({ candidateSha = null } = {}) {
  const sequences = LH1B_LIVE_EXECUTION_ORDER.map((slot) => buildLh1bSequencePlan({
    arm: slot.arm,
    scenarioKey: slot.scenario_key,
    blindLabel: slot.blind_label,
  }));
  return {
    schema: LH1B_SCHEMAS.CAMPAIGN_PLAN,
    campaign: 'lh1b_causal_replication',
    candidate_sha: candidateSha ?? gitSha(),
    sequence_count: sequences.length,
    turn_count_target: LH1B_TURN_COUNT,
    execution_order: 'lh1b_live_execution_order_v1',
    sequences,
    fail_closed: true,
    live_authorized: false,
  };
}

export function validateLh1bIsolation(campaignPlan) {
  const violations = [];
  for (const seq of campaignPlan.sequences ?? []) {
    if (seq.arm === 'lh_a' && seq.persistent_cognition_enabled) {
      violations.push(`${seq.sequence_id}: lh_a must not enable persistence`);
    }
    if (seq.arm !== 'lh_a' && !seq.persistent_cognition_enabled) {
      violations.push(`${seq.sequence_id}: persistent arm missing cognition`);
    }
  }
  return { pass: violations.length === 0, violations };
}

export { buildLh1bCampaignMatrix };
