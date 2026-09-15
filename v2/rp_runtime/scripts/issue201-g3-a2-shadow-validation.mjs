/**
 * Issue #201 G3-A — A2 prototype wiring verification harness (no G3-B live comparison).
 *
 * Usage (from v2/rp_runtime): node scripts/issue201-g3-a2-shadow-validation.mjs
 */
import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { SessionId } from '@deepseek-ai/dsh-session';

import { runA2BeatRound } from '../src/lib/a2-beat-orchestration.mjs';
import { createDecisionValueLogger } from '../src/lib/a2-decision-value-logger.mjs';
import { createHarnessRpContext, startHarnessRuntime } from '../src/scenario-harness/harness-runtime.mjs';
import { mockInferenceProfile, resolveRoleProfiles } from '../src/lib/inference-profile.mjs';
import { G3_SCENARIOS } from './lib/issue201-g3-scenarios.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

const VALID_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'opens the door with measured calm' }],
  motivation: { goal: 'respond', tactic: 'welcome', emotional_driver: 'control', risk_level: 'low' },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const VALID_NARRATOR = 'The host acknowledges the knock with a stillness that feels rehearsed.';

function gitSha() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  } catch {
    return null;
  }
}

async function createScenarioSession(api, scenario) {
  const openersRes = await fetch(
    `${api.baseUrl ?? ''}/v1/catalog/scene-templates/${encodeURIComponent(scenario.id)}/openers`,
  );
  const openersPayload = openersRes.ok ? await openersRes.json() : { openers: [] };
  const openers = openersPayload.openers ?? [];
  const opener = scenario.openerPreference
    ? openers.find((o) => String(o.opener_id ?? '').includes(scenario.openerPreference)) ?? openers[0]
    : openers[0];
  const body = {
    characters: scenario.characters,
    scene_template_id: scenario.id,
    role_assignments: scenario.roleAssignments,
    player_character_file_id: scenario.playerCharacterFileId,
    user_persona_id: scenario.userName,
    opening: opener
      ? { mode: 'template', opener_id: opener.opener_id }
      : { mode: 'minimal' },
  };
  const res = await fetch(`${api._baseUrl || api.baseUrl}/v1/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`session create failed: ${res.status}`);
  return res.json();
}

async function main() {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const evidenceRoot = process.env.ISSUE201_G3_EVIDENCE_ROOT
    ?? path.join(REPO_ROOT, 'data', 'investigation_runs', `issue201-g3-a2-${stamp}`);
  fs.mkdirSync(evidenceRoot, { recursive: true });

  const harness = await startHarnessRuntime({
    dataDir: path.join(evidenceRoot, 'harness-data'),
  });
  const { ctx, phaseExecutors } = await createHarnessRpContext({
    baseUrl: harness.baseUrl,
    dataDir: harness.dataDir,
  });
  const { createDomainApiClient } = await import('../src/lib/domain-api-client.mjs');
  const domainApi = createDomainApiClient(harness.baseUrl);
  const roleProfiles = resolveRoleProfiles({ roleProfiles: {
    character: mockInferenceProfile(),
    narrator: mockInferenceProfile(),
    director: mockInferenceProfile(),
    semantic_evaluator: mockInferenceProfile(),
  } }, {});

  const wiringResults = [];
  for (const scenarioKey of ['ayame_controlled']) {
    const scenario = G3_SCENARIOS[scenarioKey];
    const createRes = await fetch(`${harness.baseUrl}/v1/sessions/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cast: ['Alice'] }),
    });
    if (!createRes.ok) throw new Error(`session create failed: ${createRes.status}`);
    const session = await createRes.json();
    const hgSessionId = session.hg_session_id;
    const sceneSessionId = SessionId(`hg-g3a-${crypto.randomUUID()}`);
    const sceneAgent = ctx.agentLoop.create(sceneSessionId, { kind: 'mock' });

    await domainApi.recordUserTurn({
      hg_session_id: hgSessionId,
      content: scenario.playerPost,
      speaker: 'Player',
      player_decomposition: {
        schema: 'hg_player_decomposition_v1',
        uniform_projection_eligible: true,
        player_action: scenario.playerPost,
      },
    });

    const decisionValue = createDecisionValueLogger();
    const roundResult = await runA2BeatRound({
      phaseExecutors,
      api: domainApi,
      trace: ctx.hgTraceEmitter,
      sceneAgent,
      sceneSessionId,
      hgSessionId,
      hgSceneId: hgSessionId,
      options: {
        scenarioKey,
        roleAssignments: { Alice: 'guest' },
        roleProfiles,
        uniformProjectionEligible: true,
        mockCharacterResponses: [JSON.stringify(VALID_MOVE)],
        mockNarratorResponses: [VALID_NARRATOR],
        presentationSpatialClaims: scenarioKey === 'ayame_controlled' ? {
          schema: 'hg_presentation_spatial_claims_v1',
          claims: [],
        } : null,
        decisionValueLogger: decisionValue,
        liveMaxAttempts: 3,
      },
    });

    wiringResults.push({
      scenario_key: scenarioKey,
      hg_session_id: hgSessionId,
      round_result: roundResult,
    });
  }

  const report = {
    schema: 'issue201_g3_a2_wiring_verification_v1',
    experimental_sha: gitSha(),
    architecture_arm: 'a2_prototype',
    evidence_root: evidenceRoot,
    wiring_results: wiringResults,
    isolation: {
      production_bootstrap_imports_a2: false,
      harness_only_entry: 'issue201-g3-a2-shadow-validation.mjs',
      orchestrator_module: 'src/lib/a2-beat-orchestration.mjs',
    },
    g3d_sequence_length_decision: 4,
    g3b_baseline_rerun_policy: 'only_on_material_substrate_drift',
  };

  const reportPath = path.join(evidenceRoot, 'issue201-g3-a2-wiring-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf8');
  console.log(`G3-A wiring report: ${reportPath}`);

  await ctx.fiber.dispose();
  await harness.dispose();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
