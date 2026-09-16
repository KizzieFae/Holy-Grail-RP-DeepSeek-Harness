/**
 * Issue #201 LH-1A — deterministic apparatus validation (pre-live gates).
 */
import fs from 'node:fs';
import path from 'node:path';

import { buildLh0ArmConfig, buildAllLh0ArmConfigs } from './issue201-lh0-arms.mjs';
import { runLh0ConsumerValueValidationSuite } from './issue201-lh0-consumer-value-validation-lib.mjs';
import { runLh0TimingValidationSuite } from './issue201-lh0-timing-validation-lib.mjs';
import { enforceConsumptionLifecycleConfig } from './issue201-lifecycle-tracer.mjs';
import { LIFECYCLE_STATES, LH0_SCHEMAS } from './issue201-lifecycle-states.mjs';
import {
  LH1A_CHECKPOINTS,
  LH1A_FORBIDDEN_MODEL_FACING,
  LH1A_OBLIGATION_CLASSES,
  LH1A_SCENARIO_FAMILIES,
  LH1A_SCHEMAS,
  LH1A_TURN_COUNT,
  LH1A_TURN_MIN,
  LH1A_TURN_MAX,
  buildLh1aCampaignMatrix,
} from './issue201-lh1a-contract.mjs';
import { loadAllLh1aFixtures, loadLh1aFixtureManifest, obligationClassesPresent, sceneForTurn } from './issue201-lh1a-fixtures.mjs';
import { loadLh1aPolicy, policyModelFacingText, sha256File } from './issue201-lh1a-player-policy.mjs';
import { LH1A_FIXTURE_ROOT } from './issue201-lh1a-fixtures.mjs';
import { LH1A_POLICY_ROOT } from './issue201-lh1a-player-policy.mjs';
import {
  buildCampaignPlan,
  validateLhAIsolation,
  validateLhDFairness,
} from './issue201-lh1a-orchestrator.mjs';
import { buildAllCheckpointSlices } from './issue201-lh1a-checkpoint-exporter.mjs';
import {
  buildLh1aAnswerKey,
  buildLh1aBlindPacket,
  validateLh1aBlindPacketIntegrity,
} from './issue201-lh1a-blind-packet.mjs';
import { buildArchaeologyDossier } from './issue201-lh1a-archaeology.mjs';
import { buildCostRollup } from './issue201-lh1a-cost-accounting.mjs';
import { runSyntheticLifecycleProofs } from './issue201-lh1a-synthetic-proofs.mjs';
import { fileURLToPath } from 'node:url';

import { REPO_ROOT } from './issue201-lh0-fixtures.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RUBRIC_PATH = path.join(REPO_ROOT, 'governance/records/issue201-lh1a-rubric/lh1a_blind_rubric_v1.json');
const LIVE_LIB_PATH = path.join(__dirname, 'issue201-lh0-live-lib.mjs');

function check(name, pass, detail = null) {
  return { name, pass, detail };
}

function fixturePathForScenario(scenarioKey) {
  const file = scenarioKey === LH1A_SCENARIO_FAMILIES.AYAME
    ? 'ayame_lh1a_fixture_v1.json'
    : 'arkham_lh1a_fixture_v1.json';
  return path.join(LH1A_FIXTURE_ROOT, file);
}

export function runLh1aApparatusValidationSuite() {
  const checks = [];
  const fixtures = loadAllLh1aFixtures();
  const matrix = buildLh1aCampaignMatrix();
  const campaignPlan = buildCampaignPlan();
  const rubric = JSON.parse(fs.readFileSync(RUBRIC_PATH, 'utf8'));
  const blindPacket = buildLh1aBlindPacket({ campaignPlan, rubric });
  const blindIntegrity = validateLh1aBlindPacketIntegrity(blindPacket);
  const isolation = validateLhAIsolation(campaignPlan);
  const synthetic = runSyntheticLifecycleProofs();
  const lh0Consumer = runLh0ConsumerValueValidationSuite();
  const lh0Timing = runLh0TimingValidationSuite();

  // 1–8 campaign shape
  checks.push(check('four_arm_definitions', buildAllLh0ArmConfigs().length === 4));
  checks.push(check('two_scenario_families', fixtures.length === 2));
  checks.push(check('eight_planned_sequences', matrix.length === 8 && campaignPlan.sequence_count === 8));
  checks.push(check('turn_count_in_range', fixtures.every((f) => f.turns >= LH1A_TURN_MIN && f.turns <= LH1A_TURN_MAX)));
  checks.push(check('two_scenes_minimum', fixtures.every((f) => f.scenes.length >= 2)));
  checks.push(check('checkpoint_positions_valid', fixtures.every((f) => (
    f.checkpoints.C1 === LH1A_CHECKPOINTS.C1
    && f.checkpoints.C2 === LH1A_CHECKPOINTS.C2
    && f.checkpoints.C3 === LH1A_CHECKPOINTS.C3
  ))));

  // 7–12 obligations
  for (const fixture of fixtures) {
    const classes = obligationClassesPresent(fixture);
    const missing = LH1A_OBLIGATION_CLASSES.filter((c) => !classes.has(c));
    checks.push(check(`obligation_minimum_${fixture.fixture_id}`, missing.length === 0, missing.join(', ') || null));
    const delayed = fixture.obligations.find((o) => o.class === 'delayed_consequence');
    checks.push(check(
      `delayed_consequence_window_${fixture.fixture_id}`,
      delayed && delayed.action_turn_max <= 10 && delayed.consequence_turn_min >= 18,
    ));
    checks.push(check(
      `dormancy_opportunities_${fixture.fixture_id}`,
      fixture.obligations.some((o) => (o.dormancy_min_turns ?? 0) >= 8 || o.class === 'dormant_thread'),
    ));
    checks.push(check(
      `cross_scene_obligations_${fixture.fixture_id}`,
      fixture.obligations.some((o) => o.class === 'cross_scene_continuity'),
    ));
    checks.push(check(
      `non_resolution_${fixture.fixture_id}`,
      fixture.obligations.some((o) => o.class === 'non_resolution_pressure'),
    ));
    checks.push(check(
      `premature_trap_${fixture.fixture_id}`,
      fixture.obligations.some((o) => o.class === 'premature_resolution_trap'),
    ));
  }

  // 13–16 player policy + blind
  for (const scenarioKey of Object.values(LH1A_SCENARIO_FAMILIES)) {
    const { policy } = loadLh1aPolicy(scenarioKey);
    checks.push(check(`player_policy_arm_neutral_${scenarioKey}`, policy.arm_neutral === true));
    const modelText = policyModelFacingText(policy).toLowerCase();
    const leaks = LH1A_FORBIDDEN_MODEL_FACING.filter((m) => modelText.includes(m.toLowerCase()));
    checks.push(check(`no_model_facing_leaks_${scenarioKey}`, leaks.length === 0, leaks.join(', ') || null));
  }
  checks.push(check('blind_packet_strips_arm_identity', blindIntegrity.pass === true, blindIntegrity.leaked_patterns?.join(', ')));
  checks.push(check('blind_rubric_frozen', rubric.locked === true && rubric.schema === LH1A_SCHEMAS.BLIND_RUBRIC));

  // 18–21 schemas
  checks.push(check('lifecycle_schema_valid', Object.keys(LIFECYCLE_STATES).length >= 8));
  const archDossier = buildArchaeologyDossier({ sequencePlan: campaignPlan.sequences[0] });
  checks.push(check('archaeology_schema_valid', archDossier.schema === LH1A_SCHEMAS.ARCHAEOLOGY_DOSSIER));
  const costRollup = buildCostRollup({ arm: 'lh_b', sequenceId: 'test', inferenceEvents: [] });
  checks.push(check('cost_schema_valid', costRollup.schema === LH1A_SCHEMAS.COST_ROLLUP && costRollup.alters_inference_behavior === false));
  checks.push(check('seam_attribution_schema_valid', synthetic.proofs.some((p) => p.name.includes('attribution'))));

  // 22–25 PVR / player path / isolation
  const liveLibSource = fs.readFileSync(LIVE_LIB_PATH, 'utf8');
  checks.push(check('pvr_path_preserved', liveLibSource.includes('runPlayerPvrAndRecord')));
  checks.push(check('record_user_turn_preserved', liveLibSource.includes('recordUserTurn')));
  checks.push(check('lh_a_isolation', isolation.pass === true, isolation.violations?.join('; ')));
  checks.push(check('entitlement_isolation_concept', isolation.pass === true));

  // 26–28 B/C/D mechanisms + LH-D fairness
  for (const arm of ['lh_b', 'lh_c', 'lh_d']) {
    const cfg = buildLh0ArmConfig(arm);
    checks.push(check(`${arm}_persistent_enabled`, cfg.persistent_cognition_enabled === true));
    try {
      enforceConsumptionLifecycleConfig(cfg);
      checks.push(check(`${arm}_consumption_enforcer`, true));
    } catch (err) {
      checks.push(check(`${arm}_consumption_enforcer`, false, String(err.message)));
    }
  }
  checks.push(check('b_c_d_comparable_obligations', fixtures[0].obligations.length === fixtures[1].obligations.length));
  const lhD = validateLhDFairness(buildLh0ArmConfig('lh_d'));
  checks.push(check('lh_d_fairness_controls', lhD.pass === true, lhD.violations?.join('; ')));

  // 29–31 scene / transcript
  for (const fixture of fixtures) {
    const tBefore = sceneForTurn(fixture, fixture.scene_transition_turn - 1);
    const tAfter = sceneForTurn(fixture, fixture.scene_transition_turn);
    checks.push(check(
      `scene_transition_${fixture.fixture_id}`,
      tBefore?.scene_id !== tAfter?.scene_id,
    ));
    checks.push(check(
      `transcript_window_lt_turns_${fixture.fixture_id}`,
      (fixture.transcript_window_turns ?? 6) < fixture.turns,
    ));
  }

  // 32–36 exporters observation-only
  const slices = buildAllCheckpointSlices(campaignPlan.sequences[0]);
  checks.push(check('checkpoint_exporter_observation_only', slices.every((s) => s.observation_only && !s.mutates_story_state)));
  checks.push(check('archaeology_exporter_observation_only', archDossier.mutates_story_state === false));
  checks.push(check('cost_instrumentation_non_mutating', costRollup.alters_inference_behavior === false));
  checks.push(check('blind_metadata_arm_safe', blindIntegrity.pass));
  checks.push(check('campaign_fail_closed', campaignPlan.fail_closed === true));

  // 37 prior regressions
  checks.push(check('lh0_consumer_value_regressions', lh0Consumer.all_pass === true));
  checks.push(check('lh0_timing_regressions', lh0Timing.all_pass === true));
  checks.push(check('synthetic_lifecycle_proofs', synthetic.all_pass === true));

  // Additional design gates
  checks.push(check('synthetic_cross_scene_resurfacing_proof', synthetic.proofs.find((p) => p.name === 'dormant_to_relevant_activation')?.pass === true));
  checks.push(check('answer_key_separate_from_packet', buildLh1aAnswerKey(campaignPlan).length === 8));
  checks.push(check('policy_hashes_recorded', campaignPlan.sequences.every((s) => s.policy_hash && s.fixture_hash)));

  const frozenArtifacts = {
    ayame_fixture_hash: sha256File(fixturePathForScenario(LH1A_SCENARIO_FAMILIES.AYAME)),
    arkham_fixture_hash: sha256File(fixturePathForScenario(LH1A_SCENARIO_FAMILIES.ARKHAM)),
    ayame_policy_hash: sha256File(path.join(LH1A_POLICY_ROOT, 'ayame_lh1a_policy_v1.json')),
    arkham_policy_hash: sha256File(path.join(LH1A_POLICY_ROOT, 'arkham_lh1a_policy_v1.json')),
    rubric_hash: sha256File(RUBRIC_PATH),
  };

  const allPass = checks.every((c) => c.pass);

  return {
    schema: LH1A_SCHEMAS.VALIDATION,
    all_pass: allPass,
    checks,
    frozen_artifacts: frozenArtifacts,
    campaign_plan_summary: {
      sequence_count: campaignPlan.sequence_count,
      turn_count: LH1A_TURN_COUNT,
      checkpoints: LH1A_CHECKPOINTS,
    },
    synthetic_lifecycle_proofs: synthetic,
    blind_integrity: blindIntegrity,
    lh0_regressions: {
      consumer_value: lh0Consumer.all_pass,
      timing: lh0Timing.all_pass,
    },
    readiness_for_live_lh1a_execution: false,
    readiness_for_governance_execution_gate: allPass,
  };
}
