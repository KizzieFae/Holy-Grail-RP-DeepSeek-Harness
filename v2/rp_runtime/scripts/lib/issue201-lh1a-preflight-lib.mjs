/**
 * Issue #201 LH-1A — mandatory deterministic preflight before live inference.
 */
import fs from 'node:fs';
import path from 'node:path';

import { buildLh0ArmConfig, buildAllLh0ArmConfigs } from './issue201-lh0-arms.mjs';
import { gitSha, REPO_ROOT } from './issue201-lh0-lib.mjs';
import { runLh0ConsumerValueValidationSuite } from './issue201-lh0-consumer-value-validation-lib.mjs';
import { runLh0TimingValidationSuite } from './issue201-lh0-timing-validation-lib.mjs';
import {
  LH1A_CHECKPOINTS,
  LH1A_FORBIDDEN_MODEL_FACING,
  LH1A_SCHEMAS,
  LH1A_SCENARIO_FAMILIES,
  LH1A_TURN_COUNT,
} from './issue201-lh1a-contract.mjs';
import { loadAllLh1aFixtures, sceneForTurn } from './issue201-lh1a-fixtures.mjs';
import { loadLh1aPolicy, policyModelFacingText, sha256File } from './issue201-lh1a-player-policy.mjs';
import { LH1A_FIXTURE_ROOT } from './issue201-lh1a-fixtures.mjs';
import { LH1A_POLICY_ROOT } from './issue201-lh1a-player-policy.mjs';
import {
  buildLh1aLiveCampaignPlan,
  validateLhAIsolation,
  validateLhDFairness,
} from './issue201-lh1a-orchestrator.mjs';
import { buildAllCheckpointSlices } from './issue201-lh1a-checkpoint-exporter.mjs';
import {
  buildLh1aBlindPacket,
  validateLh1aBlindPacketIntegrity,
} from './issue201-lh1a-blind-packet.mjs';
import { buildArchaeologyDossier } from './issue201-lh1a-archaeology.mjs';
import { buildCostRollup } from './issue201-lh1a-cost-accounting.mjs';
import { runLh1aApparatusValidationSuite } from './issue201-lh1a-validation-lib.mjs';
import { fileURLToPath } from 'node:url';

const APPARATUS_CANDIDATE_SHA = '708ad05f5155cc1acc824cb8e7dc82d823e85dcb';
const FROZEN_HASHES = Object.freeze({
  ayame_fixture_hash: '208956064650058b0e60093893ba0a569e4035d181dd75ac9e5834d3a14054d4',
  arkham_fixture_hash: 'f9556fc504660935eddc8b1e918969fe6d5fcf32aef9416ff5bde5b6d9f50212',
  ayame_policy_hash: '868384b06e85d980ad42b331bc59b0ac8e00a56a7b4ee9006c1bdd23e7075bd2',
  arkham_policy_hash: 'fb14d6f2a4f10adda6a1680be4c415671be939bbfb1fad18867ebadef2130a2c',
  rubric_hash: 'f533cc604b276f7798639db863c8e2264254233ab162de03b343841df840bb91',
});

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RUBRIC_PATH = path.join(REPO_ROOT, 'governance/records/issue201-lh1a-rubric/lh1a_blind_rubric_v1.json');
const LIVE_LIB_PATH = path.join(__dirname, 'issue201-lh1a-live-lib.mjs');

function check(name, pass, detail = null) {
  return { name, pass, detail };
}

function fixturePath(scenarioKey) {
  const file = scenarioKey === LH1A_SCENARIO_FAMILIES.AYAME
    ? 'ayame_lh1a_fixture_v1.json'
    : 'arkham_lh1a_fixture_v1.json';
  return path.join(LH1A_FIXTURE_ROOT, file);
}

export function runLh1aLivePreflight({ apparatusCandidateSha = APPARATUS_CANDIDATE_SHA } = {}) {
  const checks = [];
  const fixtures = loadAllLh1aFixtures();
  const campaignPlan = buildLh1aLiveCampaignPlan();
  const rubric = JSON.parse(fs.readFileSync(RUBRIC_PATH, 'utf8'));
  const blindPacket = buildLh1aBlindPacket({ campaignPlan, rubric });
  const blindIntegrity = validateLh1aBlindPacketIntegrity(blindPacket);
  const isolation = validateLhAIsolation(campaignPlan);
  const apparatus = runLh1aApparatusValidationSuite();
  const lh0Consumer = runLh0ConsumerValueValidationSuite();
  const lh0Timing = runLh0TimingValidationSuite();
  const liveLibSource = fs.existsSync(LIVE_LIB_PATH) ? fs.readFileSync(LIVE_LIB_PATH, 'utf8') : '';

  const measuredHashes = {
    ayame_fixture_hash: sha256File(fixturePath(LH1A_SCENARIO_FAMILIES.AYAME)),
    arkham_fixture_hash: sha256File(fixturePath(LH1A_SCENARIO_FAMILIES.ARKHAM)),
    ayame_policy_hash: sha256File(path.join(LH1A_POLICY_ROOT, 'ayame_lh1a_policy_v1.json')),
    arkham_policy_hash: sha256File(path.join(LH1A_POLICY_ROOT, 'arkham_lh1a_policy_v1.json')),
    rubric_hash: sha256File(RUBRIC_PATH),
  };

  checks.push(check('apparatus_candidate_identified', Boolean(apparatusCandidateSha)));
  for (const [key, expected] of Object.entries(FROZEN_HASHES)) {
    checks.push(check(`frozen_hash_${key}`, measuredHashes[key] === expected, `${measuredHashes[key]} vs ${expected}`));
  }
  checks.push(check('four_arm_definitions', buildAllLh0ArmConfigs().length === 4));
  checks.push(check('two_scenario_definitions', fixtures.length === 2));
  checks.push(check('eight_sequences_planned', campaignPlan.sequence_count === 8));
  checks.push(check('twenty_two_turns_per_sequence', campaignPlan.sequences.every((s) => s.turn_count === LH1A_TURN_COUNT)));
  checks.push(check('two_scenes_per_sequence', campaignPlan.sequences.every((s) => s.scene_count === 2)));
  checks.push(check('t12_transition_intact', fixtures.every((f) => f.scene_transition_turn === 12)));
  checks.push(check('checkpoint_positions', fixtures.every((f) => (
    f.checkpoints.C1 === LH1A_CHECKPOINTS.C1
    && f.checkpoints.C2 === LH1A_CHECKPOINTS.C2
    && f.checkpoints.C3 === LH1A_CHECKPOINTS.C3
  ))));

  for (const scenarioKey of Object.values(LH1A_SCENARIO_FAMILIES)) {
    const arms = campaignPlan.sequences.filter((s) => s.scenario_key === scenarioKey);
    const hashes = new Set(arms.map((s) => s.policy_hash));
    checks.push(check(`player_policy_identical_across_arms_${scenarioKey}`, hashes.size === 1));
    const { policy } = loadLh1aPolicy(scenarioKey);
    const leaks = LH1A_FORBIDDEN_MODEL_FACING.filter((m) => policyModelFacingText(policy).toLowerCase().includes(m.toLowerCase()));
    checks.push(check(`no_model_facing_leaks_${scenarioKey}`, leaks.length === 0));
  }

  checks.push(check('live_wiring_pvr_record', liveLibSource.includes('runPlayerPvrAndRecord')));
  checks.push(check('live_wiring_a2_beat', liveLibSource.includes('runA2BeatRound')));
  checks.push(check('record_user_turn_path', liveLibSource.includes('recordUserTurn') || liveLibSource.includes('runPlayerPvrAndRecord')));
  checks.push(check('no_raw_text_bypass', !liveLibSource.includes('rawTextBypass') && !liveLibSource.includes('skipPvr')));

  const lhA = buildLh0ArmConfig('lh_a');
  const lhB = buildLh0ArmConfig('lh_b');
  const lhC = buildLh0ArmConfig('lh_c');
  const lhD = buildLh0ArmConfig('lh_d');
  checks.push(check('lh_a_no_persistent', lhA.persistent_cognition_enabled === false));
  checks.push(check('lh_b_plot_scribe', lhB.cognition_mechanisms.includes('plot_cognition_init')));
  checks.push(check('lh_c_storyteller_persistent', lhC.cognition_mechanisms.includes('persistent_storyteller_agenda')));
  checks.push(check('lh_c_no_sync_preamble', lhC.sync_storyteller_preamble === false && lhC.sync_storyteller_post_commit === false));
  checks.push(check('lh_d_consolidated', lhD.cognition_mechanisms.includes('consolidated_narrative_intelligence')));
  checks.push(check('lh_d_fairness', validateLhDFairness(lhD).pass === true));
  checks.push(check('character_autonomy_preserved', lhD.fairness.director_retains_selection === true));
  checks.push(check('continuity_authoritative', lhD.fairness.no_continuity_mutation === true));
  checks.push(check('narrator_presentation_only', lhD.unconditional_director_override === false));
  checks.push(check('persistent_no_direct_continuity_mutation', lhD.fairness.no_continuity_mutation === true));
  checks.push(check('sequence_isolation', isolation.pass === true, isolation.violations?.join('; ')));
  checks.push(check('no_cross_arm_store_contamination', isolation.pass === true && liveLibSource.includes('writeLh0Store')));
  checks.push(check('blind_packet_arm_safe', blindIntegrity.pass === true));
  const slices = buildAllCheckpointSlices(campaignPlan.sequences[0]);
  checks.push(check('checkpoint_observation_only', slices.every((s) => s.observation_only && !s.mutates_story_state)));
  const arch = buildArchaeologyDossier({ sequencePlan: campaignPlan.sequences[0] });
  checks.push(check('archaeology_observation_only', arch.mutates_story_state === false));
  const cost = buildCostRollup({ arm: 'lh_b', sequenceId: 'preflight', inferenceEvents: [] });
  checks.push(check('cost_non_mutating', cost.alters_inference_behavior === false));
  checks.push(check('campaign_fail_closed', campaignPlan.fail_closed === true));
  checks.push(check('lh0_consumer_regressions', lh0Consumer.all_pass === true));
  checks.push(check('lh0_timing_regressions', lh0Timing.all_pass === true));
  checks.push(check('lh1a_apparatus_regressions', apparatus.all_pass === true));

  const allPass = checks.every((c) => c.pass);
  return {
    schema: 'issue201_lh1a_live_preflight_v1',
    apparatus_candidate_sha: apparatusCandidateSha,
    execution_candidate_sha: gitSha(),
    frozen_hashes: FROZEN_HASHES,
    measured_hashes: measuredHashes,
    campaign_plan: campaignPlan,
    checks,
    all_pass: allPass,
    live_execution_authorized: allPass,
  };
}

export { APPARATUS_CANDIDATE_SHA, FROZEN_HASHES };
