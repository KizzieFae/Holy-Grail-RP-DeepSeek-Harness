/**
 * Issue #201 LH-1A — campaign orchestrator (planning + dry-run contract; no live inference).
 */
import crypto from 'node:crypto';

import { buildLh0ArmConfig } from './issue201-lh0-arms.mjs';
import { gitSha } from './issue201-lh0-lib.mjs';
import {
  LH1A_CHECKPOINTS,
  LH1A_SCHEMAS,
  LH1A_TURN_COUNT,
  buildLh1aCampaignMatrix,
} from './issue201-lh1a-contract.mjs';
import { loadLh1aFixtureManifest, sceneForTurn } from './issue201-lh1a-fixtures.mjs';
import path from 'node:path';

import { LH1A_FIXTURE_ROOT } from './issue201-lh1a-fixtures.mjs';
import {
  loadLh1aPolicy,
  selectLh1aPlayerStimulus,
  sha256File,
} from './issue201-lh1a-player-policy.mjs';

const BLIND_LABELS = ['SEQ-A', 'SEQ-B', 'SEQ-C', 'SEQ-D', 'SEQ-E', 'SEQ-F', 'SEQ-G', 'SEQ-H'];

/** Authoritative live execution order (arm blocks per scenario, no quality-based reordering). */
export const LH1A_LIVE_EXECUTION_ORDER = Object.freeze([
  { arm: 'lh_a', scenario_key: 'ayame_controlled' },
  { arm: 'lh_b', scenario_key: 'ayame_controlled' },
  { arm: 'lh_c', scenario_key: 'ayame_controlled' },
  { arm: 'lh_d', scenario_key: 'ayame_controlled' },
  { arm: 'lh_a', scenario_key: 'arkham_stress' },
  { arm: 'lh_b', scenario_key: 'arkham_stress' },
  { arm: 'lh_c', scenario_key: 'arkham_stress' },
  { arm: 'lh_d', scenario_key: 'arkham_stress' },
]);

export function buildSequencePlan({ arm, scenarioKey, blindLabel = null }) {
  const armConfig = buildLh0ArmConfig(arm);
  const fixture = loadLh1aFixtureManifest(scenarioKey);
  const { policy, policy_hash } = loadLh1aPolicy(scenarioKey);
  if (policy.fixture_id !== fixture.fixture_id) {
    throw new Error(`policy/fixture mismatch: ${policy.fixture_id} vs ${fixture.fixture_id}`);
  }
  const fixturePath = path.join(LH1A_FIXTURE_ROOT, `${scenarioKey === 'ayame_controlled' ? 'ayame' : 'arkham'}_lh1a_fixture_v1.json`);
  const turns = [];
  for (let turnIndex = 1; turnIndex <= fixture.turns; turnIndex += 1) {
    const scene = sceneForTurn(fixture, turnIndex);
    turns.push({
      turn_index: turnIndex,
      scene_id: scene?.scene_id ?? null,
      player_stimulus: selectLh1aPlayerStimulus(policy, turnIndex),
      checkpoint: Object.entries(LH1A_CHECKPOINTS).find(([, t]) => t === turnIndex)?.[0] ?? null,
    });
  }
  const sequenceId = `LH1A-PLAN-${arm}-${scenarioKey}-${crypto.randomUUID().slice(0, 8)}`;
  return {
    schema: LH1A_SCHEMAS.CAMPAIGN_PLAN,
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
    turns,
    obligation_ids: fixture.obligations.map((o) => o.obligation_id),
    isolation: {
      dedicated_session: true,
      no_cross_sequence_store: true,
      lh_a_blocks_persistent_projection: arm === 'lh_a',
    },
  };
}

export function buildLh1aLiveCampaignPlan({ candidateSha = null } = {}) {
  const sequences = LH1A_LIVE_EXECUTION_ORDER.map((slot, idx) => buildSequencePlan({
    arm: slot.arm,
    scenarioKey: slot.scenario_key,
    blindLabel: BLIND_LABELS[idx],
  }));
  return {
    schema: LH1A_SCHEMAS.CAMPAIGN_PLAN,
    campaign: 'lh1a_story_aging_screening_live',
    candidate_sha: candidateSha ?? gitSha(),
    apparatus_candidate_sha: '708ad05f5155cc1acc824cb8e7dc82d823e85dcb',
    sequence_count: sequences.length,
    turn_count_target: LH1A_TURN_COUNT,
    execution_order: 'lh1a_live_execution_order_v1',
    sequences,
    fail_closed: true,
    live_execution_authorized: true,
  };
}

export function buildCampaignPlan({ candidateSha = null } = {}) {
  const matrix = buildLh1aCampaignMatrix();
  if (matrix.length !== 8) throw new Error(`expected 8 sequences, got ${matrix.length}`);
  const shuffled = [...matrix];
  for (let i = shuffled.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  const sequences = shuffled.map((slot, idx) => buildSequencePlan({
    arm: slot.arm,
    scenarioKey: slot.scenario_key,
    blindLabel: BLIND_LABELS[idx],
  }));
  return {
    schema: LH1A_SCHEMAS.CAMPAIGN_PLAN,
    campaign: 'lh1a_story_aging_screening',
    candidate_sha: candidateSha ?? gitSha(),
    sequence_count: sequences.length,
    turn_count_target: LH1A_TURN_COUNT,
    sequences,
    fail_closed: true,
    live_execution_authorized: false,
  };
}

export function validateLhAIsolation(campaignPlan) {
  const violations = [];
  const persistentArms = campaignPlan.sequences.filter((s) => s.persistent_cognition_enabled);
  const controlArms = campaignPlan.sequences.filter((s) => !s.persistent_cognition_enabled);
  for (const seq of controlArms) {
    if (seq.arm_config.persistent_cognition_enabled) {
      violations.push(`${seq.sequence_id}: LH-A must not enable persistent cognition`);
    }
    if (seq.arm_config.projection_lifecycle_enabled) {
      violations.push(`${seq.sequence_id}: LH-A must not enable projection lifecycle`);
    }
  }
  for (const seq of persistentArms) {
    if (!seq.arm_config.projection_lifecycle_enabled) {
      violations.push(`${seq.sequence_id}: persistent arm missing projection lifecycle`);
    }
    if (!seq.arm_config.consumption_lifecycle_enforcer) {
      violations.push(`${seq.sequence_id}: persistent arm missing consumption enforcer`);
    }
  }
  const sessionIds = new Set(campaignPlan.sequences.map((s) => s.sequence_id));
  if (sessionIds.size !== 8) violations.push('sequence IDs must be unique');
  return { pass: violations.length === 0, violations };
}

export function validateLhDFairness(armConfig) {
  const violations = [];
  if (armConfig.arm !== 'lh_d') return { pass: true, violations };
  const f = armConfig.fairness ?? {};
  if (!f.deterministic_eligibility_first) violations.push('LH-D: deterministic_eligibility_first required');
  if (!f.director_retains_selection) violations.push('LH-D: director_retains_selection required');
  if (!f.guidance_not_dictation) violations.push('LH-D: guidance_not_dictation required');
  if (!f.no_continuity_mutation) violations.push('LH-D: no_continuity_mutation required');
  if (!f.no_unconditional_override) violations.push('LH-D: no_unconditional_override required');
  if (armConfig.unconditional_director_override) violations.push('LH-D: unconditional_director_override forbidden');
  return { pass: violations.length === 0, violations };
}
