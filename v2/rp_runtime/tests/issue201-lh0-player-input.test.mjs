import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { startDomainApi } from './helpers/domain-api.mjs';
import { runLh0ConsumerValueValidationSuite } from '../scripts/lib/issue201-lh0-consumer-value-validation-lib.mjs';
import { LH0_NEUTRAL_GUEST_POLICY_QUESTION } from '../scripts/lib/issue201-lh0-consumer-value-contract.mjs';

function buildPublicSpeechDecomposition(content) {
  const normalized = String(content ?? '').normalize('NFC').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const sourceSha256 = createHash('sha256').update(normalized, 'utf8').digest('hex');
  return {
    perceptual_visibility: {
      units: [
        {
          unit_id: 'u1',
          kind: 'speech',
          text: normalized,
          recipients: { scope: 'public', characters: [], roles: [] },
          source_provenance: { segment_ids: ['s1'], order_index: 0 },
          source: 'player_decomposition',
        },
      ],
    },
    source_accounting: {
      source_length: normalized.length,
      source_sha256: sourceSha256,
      normalization: 'nfc_crlf_to_lf',
      segments: [
        {
          segment_id: 's1',
          char_start: 0,
          char_end: normalized.length,
          disposition: 'projects',
          unit_ids: ['u1'],
        },
      ],
    },
    generation: { inference_id: 'test-lh0-player-input' },
  };
}

test('recordUserTurn persists neutral stimulus in rp_history with PVR envelope', async (t) => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-lh0-player-input-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const host = await startDomainApi(undefined, { sessionsDir, hostEnv: { HG_DATA_DIR: dataDir } });
  t.after(() => host.stop());

  const createRes = await fetch(`${host.baseUrl}/v1/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cast: ['Ayame', 'Kizzie'] }),
  });
  const session = await createRes.json();
  const hgSessionId = session.hg_session_id;
  const api = createDomainApiClient(host.baseUrl);

  const round = await api.startRound({ hg_scene_id: hgSessionId });
  const decomposition = buildPublicSpeechDecomposition(LH0_NEUTRAL_GUEST_POLICY_QUESTION);
  await api.recordUserTurn({
    hg_session_id: hgSessionId,
    hg_round_id: round.hg_round_id,
    content: LH0_NEUTRAL_GUEST_POLICY_QUESTION,
    speaker: 'Kizzie',
    player_decomposition: decomposition,
  });

  const history = await api.getSessionHistory(hgSessionId);
  const userEntry = (history.entries ?? []).find((entry) => entry.kind === 'user');
  assert.ok(userEntry, 'user turn must be recorded in rp_history');
  assert.equal(userEntry.content, LH0_NEUTRAL_GUEST_POLICY_QUESTION);
  assert.ok(userEntry.metadata?.perceptual_visibility?.units?.length > 0, 'PVR envelope required');

  const manifest = await api.prepareCharacterContext({
    hg_scene_id: hgSessionId,
    hg_round_id: round.hg_round_id,
    character_id: 'Ayame',
    role: 'host',
    inference_id: 'test-lh0-player-input',
    turn_index: 0,
    attempt_index: 0,
  });
  assert.ok(manifest.contributions?.length > 0, 'Character projection must succeed after recordUserTurn');
});

test('LH-0 live lib chains runPlayerPvrAndRecord before runA2BeatRound', async () => {
  const source = fs.readFileSync(
    path.resolve('scripts/lib/issue201-lh0-live-lib.mjs'),
    'utf8',
  );
  assert.ok(source.includes('runPlayerPvrAndRecord'));
  assert.ok(source.includes('recordUserTurn'));
  const turnBlock = source.slice(source.indexOf('async function runLh0Turn'), source.indexOf('async function executeLh0LiveArm'));
  const pvrIndex = turnBlock.indexOf('runPlayerPvrAndRecord');
  const a2Index = turnBlock.indexOf('runA2BeatRound');
  assert.ok(pvrIndex >= 0 && a2Index > pvrIndex, 'PVR+recordUserTurn must precede runA2BeatRound');
});

test('consumer-value validation suite includes recordUserTurn regression gate', () => {
  const report = runLh0ConsumerValueValidationSuite();
  const recordGate = report.checks.find((c) => c.name === 'lh0_calls_record_user_turn');
  assert.ok(recordGate?.pass, 'lh0_calls_record_user_turn gate must pass');
  assert.equal(report.readiness_for_consumer_value_qualification, true);
});
