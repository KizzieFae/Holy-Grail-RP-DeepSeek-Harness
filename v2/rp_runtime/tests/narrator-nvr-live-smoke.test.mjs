import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import { startDomainApi } from './helpers/domain-api.mjs';

const hasLiveKey = Boolean(process.env.DEEPSEEK_API_KEY?.trim());

const SPEECH_MOVE = {
  move_schema_version: 2,
  beats: [
    {
      type: 'speech',
      dialogue: 'Keep your voice down, Bob.',
      audibility: 'directed',
      audience: ['Bob'],
    },
  ],
  motivation: {
    goal: 'warn quietly',
    tactic: 'hushed tone',
    emotional_driver: 'alert',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const DIRECTOR_JSON = JSON.stringify({
  next_actor: 'Alice',
  end_round: false,
  reason: 'Alice should act next.',
  environment_event: '',
  tension_shift: 'steady',
});

async function commitAliceMove(api, sessionId, roundId) {
  const validation = await api.validateDirectorDecision({
    hg_scene_id: sessionId,
    hg_round_id: roundId,
    inference_id: 'inf-director-narrator-nvr-live',
    turn_index: 0,
    attempt_index: 0,
    proposed_decision: JSON.parse(DIRECTOR_JSON),
  });
  assert.equal(validation.accepted, true);
  const commit = await api.commitMove({
    inference_id: 'inf-commit-narrator-nvr-live',
    hg_scene_id: sessionId,
    hg_round_id: roundId,
    character_id: 'Alice',
    validated_move: SPEECH_MOVE,
    director_decision: validation.normalized_decision,
    expected_turn_index: 0,
  });
  assert.equal(commit.committed, true);
  return commit;
}

function sceneAgentCollector(events) {
  return {
    session: {
      append(type, payload) {
        events.push({ type, payload });
      },
    },
  };
}

test('live narrator combined envelope smoke: JSON envelope parses and prose stays human-facing', {
  skip: hasLiveKey ? false : 'DEEPSEEK_API_KEY not set',
  timeout: 240_000,
}, async (t) => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-live-narrator-nvr-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const previous = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
  };
  process.env.HG_DATA_DIR = dataDir;
  process.env.HG_EXECUTION_EVIDENCE = 'on';
  t.after(() => {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    fs.rmSync(dataDir, { recursive: true, force: true });
  });

  const host = await startDomainApi(undefined, { t, sessionsDir });
  const api = createDomainApiClient(host.baseUrl);
  const { ctx, phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
    inference: { mountDeepSeek: true },
  });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const session = await api.createSession({ cast: ['Alice', 'Bob', 'Carol'] });
  const sessionId = session.hg_session_id;
  const round = await api.startRound({ hg_scene_id: sessionId });
  const commit = await commitAliceMove(api, sessionId, round.hg_round_id);
  const sceneEvents = [];

  const narratorResult = await phaseExecutors.runNarrator({
    api,
    trace: ctx.hgTraceEmitter,
    recorder: phaseExecutors.executionEvidenceRecorder,
    sceneAgent: sceneAgentCollector(sceneEvents),
    sceneSessionId: 'live-narrator-nvr-smoke',
    hgSessionId: sessionId,
    hgSceneId: sessionId,
    hgRoundId: round.hg_round_id,
    characterId: 'Alice',
    domainCommitId: commit.domain_commit_id,
    continuityTurnIndex: commit.continuity_turn_index,
    narratorInferenceId: 'inf-narrator-nvr-live-smoke',
    mockNarratorResponses: [],
    mockNarratorSemanticQaResponses: [],
    characterTurnIndex: 0,
    modelProfile: deepseekInferenceProfile(),
    semanticEvaluatorProfile: deepseekInferenceProfile({ maxTokens: 2048 }),
    narratorSemanticQaEnabled: false,
    prompt: null,
  });

  assert.equal(narratorResult.presentation_rendered, true, narratorResult.presentation_failure_reason);
  assert.ok(narratorResult.presentation_text);
  assert.doesNotMatch(narratorResult.presentation_text, /^\s*\{/);
  assert.doesNotMatch(narratorResult.presentation_text, /narrative_visibility/);

  if (narratorResult.narrative_visibility?.units?.length) {
    assert.ok(Array.isArray(narratorResult.narrative_visibility.units));
    const kinds = new Set(narratorResult.narrative_visibility.units.map((unit) => unit.kind));
    assert.ok(kinds.size > 0);
  }

  await api.recordPresentation({
    hg_session_id: sessionId,
    domain_commit_id: commit.domain_commit_id,
    hg_round_id: round.hg_round_id,
    character_id: 'Alice',
    presentation_text: narratorResult.presentation_text,
    presentation_failed: false,
    narrative_visibility: narratorResult.narrative_visibility ?? null,
  });

  const history = await api.getSessionHistory(sessionId);
  const presentation = history.entries.find((entry) => entry.kind === 'presentation');
  assert.ok(presentation);
  assert.equal(presentation.content, narratorResult.presentation_text);
  if (narratorResult.narrative_visibility) {
    assert.ok(presentation.metadata?.narrative_visibility?.units?.length);
  }
});
