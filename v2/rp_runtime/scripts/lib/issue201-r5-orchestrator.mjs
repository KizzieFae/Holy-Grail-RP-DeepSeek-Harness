/**
 * Issue #201 R5 — two-sequence campaign plan (A1/B1 only).
 */
import crypto from 'node:crypto';

import { buildLh0ArmConfig } from './issue201-lh0-arms.mjs';
import { gitSha } from './issue201-lh0-lib.mjs';
import { R5_LIVE_EXECUTION_ORDER, R5_SCHEMAS } from './issue201-r5-contract.mjs';
import { fixturePathForR5, loadR5FixtureManifest } from './issue201-r5-fixtures.mjs';
import { loadR5Policy, selectR5PlayerStimulus, sha256File } from './issue201-r5-player-policy.mjs';

export function buildR5SequencePlan({ arm, blindLabel }) {
  const armConfig = buildLh0ArmConfig(arm);
  const fixture = loadR5FixtureManifest();
  const { policy, policy_hash } = loadR5Policy();
  const turns = [];
  for (let turnIndex = 1; turnIndex <= fixture.turns; turnIndex += 1) {
    const scene = fixture.scenes.find(
      (s) => turnIndex >= s.turn_range[0] && turnIndex <= s.turn_range[1],
    );
    turns.push({
      turn_index: turnIndex,
      scene_id: scene?.scene_id ?? null,
      player_stimulus: selectR5PlayerStimulus(policy, turnIndex),
      establishment_turn: turnIndex === fixture.establishment.turn_index,
      decision_turn: turnIndex === fixture.qualification.decision_turn_index,
    });
  }
  return {
    schema: R5_SCHEMAS.CAMPAIGN_PLAN,
    sequence_id: `R5-PLAN-${arm}-${crypto.randomUUID().slice(0, 8)}`,
    blind_label: blindLabel,
    arm,
    arm_label: armConfig.label,
    scenario_key: fixture.scenario_key,
    fixture_id: fixture.fixture_id,
    fixture_hash: sha256File(fixturePathForR5()),
    policy_id: policy.policy_id,
    policy_hash,
    turn_count: fixture.turns,
    arm_config: armConfig,
    persistent_cognition_enabled: armConfig.persistent_cognition_enabled,
    fork_ids: fixture.causal_design.decision_forks.map((f) => f.fork_id),
    turns,
    isolation: {
      dedicated_session: true,
      establishment_arm_neutral: true,
      lh_a_blocks_persistent_projection: arm === 'lh_a',
    },
  };
}

export function buildR5CampaignPlan({ candidateSha = null } = {}) {
  const sequences = R5_LIVE_EXECUTION_ORDER.map((slot) => buildR5SequencePlan({
    arm: slot.arm,
    blindLabel: slot.blind_label,
  }));
  return {
    schema: R5_SCHEMAS.CAMPAIGN_PLAN,
    campaign: 'lh1b_r5_discrimination',
    candidate_sha: candidateSha ?? gitSha(),
    sequence_count: sequences.length,
    sequences,
    live_authorized: false,
    a2_replicate_deferred: true,
  };
}
