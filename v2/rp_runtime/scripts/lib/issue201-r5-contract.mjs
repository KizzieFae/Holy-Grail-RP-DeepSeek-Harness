/**
 * Issue #201 — minimal R5 persistence-unique discrimination contract.
 */
import { LH0_ARMS } from './issue201-lh0-arms.mjs';

export const R5_SCHEMAS = Object.freeze({
  FIXTURE_MANIFEST: 'issue201_r5_fixture_manifest_v1',
  PLAYER_POLICY: 'issue201_r5_player_policy_v1',
  CAMPAIGN_PLAN: 'issue201_r5_campaign_plan_v1',
  QUALIFICATION: 'issue201_r5_apparatus_qualification_v1',
  ESTABLISHMENT_EQUIVALENCE: 'issue201_r5_establishment_equivalence_v1',
});

export const R5_QUALIFIED_LH1B_RUNNER_SHA = 'dd11d10cc3f4a420691fb33f3533bd75dcb39a4f';

export const R5_LIVE_EXECUTION_ORDER = Object.freeze([
  { arm: 'lh_a', scenario_key: 'ayame_controlled', blind_label: 'R5-A1' },
  { arm: 'lh_b', scenario_key: 'ayame_controlled', blind_label: 'R5-B1' },
]);

export const R5_ARMS = Object.freeze({
  LH_A: LH0_ARMS.LH_A,
  LH_B: LH0_ARMS.LH_B,
});
