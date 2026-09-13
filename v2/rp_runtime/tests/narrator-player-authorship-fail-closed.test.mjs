import assert from 'node:assert/strict';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import { runNarratorPhase } from '../src/plugins/hg-phase-executors/narrator-phase.mjs';
import { startDomainApi } from './helpers/domain-api.mjs';

const ACTION_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'examines the ledger carefully' }],
  motivation: {
    goal: 'verify the accounts',
    tactic: 'close reading',
    emotional_driver: 'focused',
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
    inference_id: 'inf-director-pa-fc',
    turn_index: 0,
    attempt_index: 0,
    proposed_decision: JSON.parse(DIRECTOR_JSON),
  });
  const commit = await api.commitMove({
    inference_id: 'inf-commit-pa-fc',
    hg_scene_id: sessionId,
    hg_round_id: roundId,
    character_id: 'Alice',
    validated_move: ACTION_MOVE,
    director_decision: validation.normalized_decision,
    expected_turn_index: 0,
  });
  return commit;
}

function sceneAgentCollector(events) {
  return { session: { append(type, payload) { events.push({ type, payload }); } } };
}

function playerAuthorshipHard(passId) {
  return JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'narrator',
    evaluation_pass_id: passId,
    overall_result: 'reject_hard',
    findings: [{
      dimension: 'nar_player_authorship',
      severity: 'hard',
      finding: 'Unsupported Player skin sensation attributed in narration',
      rationale: 'no player_fact supports cold-on-skin claim',
      authoritative_citation: { ref_id: 'guardrail:player_authorship' },
    }],
  });
}

test('narrator player-authorship hard exhaustion is fail-closed', async (t) => {
  const port = 34765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const api = createDomainApiClient(host.baseUrl);
  t.after(() => host.stop());

  const { ctx } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => { await ctx.fiber.dispose(); });

  const session = await api.createSession({ cast: ['Alice'], location: 'Study' });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  const commit = await commitAliceMove(api, session.hg_session_id, round.hg_round_id);
  const candidate = 'The cold bit at Kizzie\'s bare skin as she stepped into the draft.';
  const sceneEvents = [];

  const result = await runNarratorPhase({
    api,
    runEphemeralInference: async (args) => {
      const kind = args.evidenceContext?.inferenceKind;
      if (args.evidenceContext?.role === 'semantic_evaluator') {
        const passId = args.evidenceContext?.evaluationPassId ?? 'pass';
        return {
          evidenceId: `ev-qa-${passId}`,
          inferenceSessionId: 'is-qa',
          raw: playerAuthorshipHard(passId),
          failed: false,
          trace: { finish: { kind: 'stop' } },
        };
      }
      if (kind === 'narrator_environment_cognition') {
        return {
          evidenceId: 'ev-env',
          inferenceSessionId: 'is-env',
          raw: JSON.stringify({
            cognition_status: 'complete',
            n1: { baseline_sufficient: true },
            environmental_response_obligations: [],
          }),
          failed: false,
          trace: { finish: { kind: 'stop' } },
        };
      }
      return {
        evidenceId: 'ev-narrator',
        inferenceSessionId: 'is-narrator',
        raw: candidate,
        failed: false,
        trace: { finish: { kind: 'stop' } },
      };
    },
    recorder: ctx.hgPhaseExecutors.executionEvidenceRecorder,
    trace: ctx.hgTraceEmitter,
    sceneAgent: sceneAgentCollector(sceneEvents),
    sceneSessionId: 'scene-pa-fail-closed',
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    characterId: 'Alice',
    domainCommitId: commit.domain_commit_id,
    continuityTurnIndex: commit.continuity_turn_index,
    narratorInferenceId: 'inf-pa-fail-closed',
    mockNarratorResponses: [candidate, candidate],
    mockNarratorSemanticQaResponses: [],
    characterTurnIndex: 0,
    modelProfile: deepseekInferenceProfile(),
    semanticEvaluatorProfile: deepseekInferenceProfile(),
    narratorSemanticQaEnabled: true,
  });

  assert.equal(result.presentation_rendered, false);
  assert.equal(result.terminal_disposition, 'player_authorship_rejected');
  const qaEvents = sceneEvents.filter((event) => event.type === 'hg/narrator-semantic-qa');
  assert.ok(qaEvents.length >= 2);
  assert.ok(qaEvents.some((event) => event.payload.policy_action === 'player_authorship_fail_closed'));
});
