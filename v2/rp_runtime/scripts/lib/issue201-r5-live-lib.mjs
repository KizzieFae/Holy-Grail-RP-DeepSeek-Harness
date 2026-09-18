/**
 * Issue #201 R5 — mock/live sequence execution on authoritative LH-1B turn path.
 */
import fs from 'node:fs';
import path from 'node:path';

import { HolyGrailApplicationClient } from '../../src/application/hg-application-client.mjs';
import { G3_SCENARIOS } from './issue201-g3-scenarios.mjs';
import { buildLh0ArmConfig } from './issue201-lh0-arms.mjs';
import { writeLh0Store } from './issue201-lh0-persistent-store.mjs';
import { defaultSessionsDir } from '../../src/lib/runtime-config.mjs';
import {
  LH1B_TURN_ORDERING,
  runLh1bTurn,
} from './issue201-lh1b-live-lib.mjs';
import { loadR5FixtureManifest } from './issue201-r5-fixtures.mjs';
import { verifyR5FrozenHashes } from './issue201-r5-frozen-hashes.mjs';
import { R5_SCHEMAS } from './issue201-r5-contract.mjs';
import { gitSha } from './issue201-lh0-lib.mjs';

const SCENARIO = G3_SCENARIOS.ayame_controlled;

async function createR5Client(evidenceRoot, sessionsDir) {
  const client = new HolyGrailApplicationClient({
    inferenceMode: 'live',
    runtime: {
      inference: {
        mountDeepSeek: true,
        executionEvidence: { enabled: true, root: evidenceRoot },
      },
      sessionsDir,
    },
  });
  await client.start();
  const openers = await client.listTemplateOpeners(SCENARIO.id);
  const opener = openers[0];
  if (!opener) throw new Error('no opener for R5 scenario');
  await client.createSession({
    characters: SCENARIO.characters,
    sceneTemplateId: SCENARIO.id,
    roleAssignments: SCENARIO.roleAssignments,
    playerCharacterFileId: SCENARIO.playerCharacterFileId,
    userPersonaId: SCENARIO.userName,
    opening: { mode: 'template', opener_id: opener.opener_id },
  });
  return client;
}

/**
 * Execute one R5 sequence (14 turns) through the real runner with mock inference profiles.
 */
export async function executeR5MockSequence({
  sequencePlan,
  evidenceRoot,
  mockOverridesByTurn = {},
  forceMockInferenceProfiles = true,
}) {
  const hashCheck = verifyR5FrozenHashes();
  if (!hashCheck.pass) {
    return {
      failed: true,
      error: `frozen hash drift: ${hashCheck.drift.map(([k]) => k).join(',')}`,
      stop_condition: 'fixture_policy_hash_drift',
    };
  }

  const fixture = loadR5FixtureManifest();
  const armConfig = buildLh0ArmConfig(sequencePlan.arm);
  const sessionsDir = defaultSessionsDir();
  const sequenceId = sequencePlan.blind_label ?? `R5-${sequencePlan.arm}`;
  const turns = [];
  let failed = false;
  let error = null;
  let stopCondition = null;
  let hgSessionId = null;

  const client = await createR5Client(evidenceRoot, sessionsDir);
  try {
    hgSessionId = client.activeSessionId;
    if (armConfig.persistent_cognition_enabled) {
      writeLh0Store(sessionsDir, hgSessionId, {
        schema: 'issue201_lh0_persistent_store_v1',
        campaign: 'r5',
        fixture_id: fixture.fixture_id,
        obligations: [],
        events: [],
      });
    }
    for (const planTurn of sequencePlan.turns) {
      const turnIndex = planTurn.turn_index;
      const row = await runLh1bTurn({
        client,
        armConfig,
        fixture,
        scenario: SCENARIO,
        turnIndex,
        playerStimulus: planTurn.player_stimulus,
        sceneId: planTurn.scene_id,
        sequenceId,
        evidenceRoot,
        sessionsDir,
        frozenHashGate: hashCheck,
        mockOverrides: {
          forceMockInferenceProfiles,
          ...mockOverridesByTurn[turnIndex],
        },
      });
      turns.push(row);
      if (!row.committed) {
        failed = true;
        error = `turn ${turnIndex} not committed`;
        stopCondition = 'terminal_beat_failure_budget_exceeded';
        break;
      }
    }
  } catch (err) {
    failed = true;
    error = String(err?.message ?? err);
    stopCondition = err.stop_condition ?? 'projection_seam_failed';
  } finally {
    await client.stop();
  }

  const outDir = path.join(evidenceRoot, 'r5_sequences', sequenceId);
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'sequence_result.json'), JSON.stringify({
    schema: R5_SCHEMAS.RUNNER_QUALIFICATION,
    sequence_id: sequenceId,
    arm: sequencePlan.arm,
    blind_label: sequencePlan.blind_label,
    failed,
    error,
    stop_condition: stopCondition,
    hg_session_id: hgSessionId,
    turn_count: turns.length,
    turns,
    frozen_hashes: hashCheck.measured,
    runner_sha: gitSha(),
  }, null, 2));

  return {
    sequence_id: sequenceId,
    arm: sequencePlan.arm,
    blind_label: sequencePlan.blind_label,
    failed,
    error,
    stop_condition: stopCondition,
    hg_session_id: hgSessionId,
    turns,
    evidence_path: outDir,
    frozen_hashes: hashCheck.measured,
    turn_ordering: [...LH1B_TURN_ORDERING],
  };
}
