import assert from 'node:assert/strict';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import {
  PLAYER_AUTHORSHIP_DIMENSION,
  applyNarratorSemanticPolicy,
  assessPlayerAuthorshipRepairVerification,
  buildCorrectionContextFromNarratorQa,
  buildPlayerAuthorshipRepairObligation,
} from '../src/plugins/hg-phase-executors/narrator-semantic-qa.mjs';
import { runNarratorPhase } from '../src/plugins/hg-phase-executors/narrator-phase.mjs';
import { startDomainApi } from './helpers/domain-api.mjs';

const GUARDRAIL = 'guardrail:player_authorship';
const VALID_CITATION = [{
  finding_index: 0,
  status: 'valid',
  resolved_authority_class: 'authoritative',
}];

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

function playerAuthorshipHard(passId, findingText) {
  return JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'narrator',
    evaluation_pass_id: passId,
    overall_result: 'reject_hard',
    findings: [{
      dimension: PLAYER_AUTHORSHIP_DIMENSION,
      severity: 'hard',
      finding: findingText,
      rationale: 'no player_fact supports cold-on-skin claim',
      authoritative_citation: { ref_id: GUARDRAIL },
    }],
  });
}

function playerAuthorshipSoft(passId, findingText) {
  return JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'narrator',
    evaluation_pass_id: passId,
    overall_result: 'reject_soft',
    findings: [{
      dimension: PLAYER_AUTHORSHIP_DIMENSION,
      severity: 'soft',
      finding: findingText,
      rationale: 'possible unsupported Player sensation',
    }],
  });
}

function semanticPass(passId) {
  return JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'narrator',
    evaluation_pass_id: passId,
    overall_result: 'pass',
    findings: [],
  });
}

function semanticSoftOther(passId) {
  return JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'narrator',
    evaluation_pass_id: passId,
    overall_result: 'reject_soft',
    findings: [{
      dimension: 'nar_framing_distortion',
      severity: 'soft',
      finding: 'minor framing concern',
      rationale: 'residual soft only',
    }],
  });
}

function makeEvalOutcome(result, citationValidations = VALID_CITATION) {
  return {
    infrastructureFailure: false,
    citationValidations,
    result,
  };
}

async function commitAliceMove(api, sessionId, roundId) {
  const validation = await api.validateDirectorDecision({
    hg_scene_id: sessionId,
    hg_round_id: roundId,
    inference_id: 'inf-director-pa-repair',
    turn_index: 0,
    attempt_index: 0,
    proposed_decision: JSON.parse(DIRECTOR_JSON),
  });
  return api.commitMove({
    inference_id: 'inf-commit-pa-repair',
    hg_scene_id: sessionId,
    hg_round_id: roundId,
    character_id: 'Alice',
    validated_move: ACTION_MOVE,
    director_decision: validation.normalized_decision,
    expected_turn_index: 0,
  });
}

function sceneAgentCollector(events) {
  return { session: { append(type, payload) { events.push({ type, payload }); } } };
}

function makeRunEphemeral(ctx, narratorResponses, qaResponses) {
  let narratorCall = 0;
  let qaCall = 0;
  return async (args) => {
    if (args.evidenceContext?.role === 'semantic_evaluator') {
      const raw = qaResponses[qaCall] ?? qaResponses[qaResponses.length - 1];
      qaCall += 1;
      return {
        evidenceId: `ev-qa-${qaCall}`,
        inferenceSessionId: 'is-qa',
        raw,
        failed: false,
        trace: { finish: { kind: 'stop' } },
      };
    }
    if (args.evidenceContext?.inferenceKind === 'narrator_environment_cognition') {
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
    const raw = narratorResponses[narratorCall] ?? narratorResponses[narratorResponses.length - 1];
    narratorCall += 1;
    return {
      evidenceId: `ev-narrator-${narratorCall}`,
      inferenceSessionId: 'is-narrator',
      raw,
      failed: false,
      trace: { finish: { kind: 'stop' } },
    };
  };
}

test('repair obligation cleared when regenerated candidate passes without nar_player_authorship', () => {
  const obligation = {
    kind: 'nar_player_authorship_hard_repair',
    dimension: PLAYER_AUTHORSHIP_DIMENSION,
    status: 'pending',
    source_evaluation_pass_id: 'inf-qa-0',
    source_attempt_index: 0,
    offending_assertion: 'Unsupported Player skin sensation',
  };
  const verification = assessPlayerAuthorshipRepairVerification(
    obligation,
    makeEvalOutcome({
      overall_result: 'pass',
      findings: [],
    }),
  );
  assert.equal(verification.status, 'cleared');

  const policy = applyNarratorSemanticPolicy(
    makeEvalOutcome({ overall_result: 'pass', findings: [] }),
    { attemptIndex: 1, maxAttempts: 2, pendingPlayerAuthorshipRepair: obligation },
  );
  assert.equal(policy.action, 'pass');
  assert.equal(policy.playerAuthorshipRepairCleared, true);
});

test('repair obligation blocks accept_with_residuals when violation persists as soft', () => {
  const obligation = {
    kind: 'nar_player_authorship_hard_repair',
    dimension: PLAYER_AUTHORSHIP_DIMENSION,
    status: 'pending',
    source_evaluation_pass_id: 'inf-qa-0',
    source_attempt_index: 0,
    offending_assertion: 'Unsupported Player skin sensation',
  };
  const evalOutcome = makeEvalOutcome({
    overall_result: 'reject_soft',
    findings: [{
      dimension: PLAYER_AUTHORSHIP_DIMENSION,
      severity: 'soft',
      finding: 'chill still attributed to Player skin',
      rationale: 'soft only',
    }],
  }, []);
  const verification = assessPlayerAuthorshipRepairVerification(obligation, evalOutcome);
  assert.equal(verification.status, 'unverified');

  const policy = applyNarratorSemanticPolicy(evalOutcome, {
    attemptIndex: 1,
    maxAttempts: 2,
    pendingPlayerAuthorshipRepair: obligation,
  });
  assert.equal(policy.action, 'player_authorship_fail_closed');
});

test('repair obligation blocks accept_with_residuals without nar_player_authorship clearance proof', () => {
  const obligation = {
    kind: 'nar_player_authorship_hard_repair',
    dimension: PLAYER_AUTHORSHIP_DIMENSION,
    status: 'pending',
    source_evaluation_pass_id: 'inf-qa-0',
    source_attempt_index: 0,
    offending_assertion: 'Unsupported Player skin sensation',
  };
  const evalOutcome = makeEvalOutcome({
    overall_result: 'reject_soft',
    findings: [{
      dimension: 'nar_framing_distortion',
      severity: 'soft',
      finding: 'minor framing concern',
      rationale: 'unrelated soft only',
    }],
  }, []);
  const policy = applyNarratorSemanticPolicy(evalOutcome, {
    attemptIndex: 1,
    maxAttempts: 2,
    pendingPlayerAuthorshipRepair: obligation,
  });
  assert.equal(policy.action, 'player_authorship_fail_closed');
  assert.equal(policy.repairVerification.status, 'unverified');
});

test('hard nar_player_authorship exhaustion remains player_authorship_rejected', async (t) => {
  const port = 34790 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const api = createDomainApiClient(host.baseUrl);
  t.after(() => host.stop());

  const { ctx } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => { await ctx.fiber.dispose(); });

  const session = await api.createSession({ cast: ['Alice'], location: 'Study' });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  const commit = await commitAliceMove(api, session.hg_session_id, round.hg_round_id);
  const badCandidate = 'The cold bit sharply against Kizzie\'s skin.';
  const sceneEvents = [];

  const result = await runNarratorPhase({
    api,
    runEphemeralInference: makeRunEphemeral(
      ctx,
      [badCandidate, badCandidate],
      [
        playerAuthorshipHard('inf-pa-repair-qa-0', 'Unsupported Player skin sensation'),
        playerAuthorshipHard('inf-pa-repair-qa-1', 'Unsupported Player skin sensation persists'),
      ],
    ),
    recorder: ctx.hgPhaseExecutors.executionEvidenceRecorder,
    trace: ctx.hgTraceEmitter,
    sceneAgent: sceneAgentCollector(sceneEvents),
    sceneSessionId: 'scene-pa-repair-exhaust',
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    characterId: 'Alice',
    domainCommitId: commit.domain_commit_id,
    continuityTurnIndex: commit.continuity_turn_index,
    narratorInferenceId: 'inf-pa-repair-exhaust',
    mockNarratorResponses: [badCandidate, badCandidate],
    mockNarratorSemanticQaResponses: [],
    characterTurnIndex: 0,
    modelProfile: deepseekInferenceProfile(),
    semanticEvaluatorProfile: deepseekInferenceProfile(),
    narratorSemanticQaEnabled: true,
  });

  assert.equal(result.presentation_rendered, false);
  assert.equal(result.terminal_disposition, 'player_authorship_rejected');
});

test('successful repair renders when obligation is cleared', async (t) => {
  const port = 34795 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const api = createDomainApiClient(host.baseUrl);
  t.after(() => host.stop());

  const { ctx } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => { await ctx.fiber.dispose(); });

  const session = await api.createSession({ cast: ['Alice'], location: 'Study' });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  const commit = await commitAliceMove(api, session.hg_session_id, round.hg_round_id);
  const badCandidate = 'The cold bit sharply against Kizzie\'s skin.';
  const repairedCandidate = 'Cold air drifted through the open doorway.';
  const sceneEvents = [];

  const result = await runNarratorPhase({
    api,
    runEphemeralInference: makeRunEphemeral(
      ctx,
      [badCandidate, repairedCandidate],
      [
        playerAuthorshipHard('inf-pa-repair-ok-0', 'Unsupported Player skin sensation'),
        semanticPass('inf-pa-repair-ok-1'),
      ],
    ),
    recorder: ctx.hgPhaseExecutors.executionEvidenceRecorder,
    trace: ctx.hgTraceEmitter,
    sceneAgent: sceneAgentCollector(sceneEvents),
    sceneSessionId: 'scene-pa-repair-ok',
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    characterId: 'Alice',
    domainCommitId: commit.domain_commit_id,
    continuityTurnIndex: commit.continuity_turn_index,
    narratorInferenceId: 'inf-pa-repair-ok',
    mockNarratorResponses: [badCandidate, repairedCandidate],
    mockNarratorSemanticQaResponses: [],
    characterTurnIndex: 0,
    modelProfile: deepseekInferenceProfile(),
    semanticEvaluatorProfile: deepseekInferenceProfile(),
    narratorSemanticQaEnabled: true,
  });

  assert.equal(result.presentation_rendered, true);
  assert.equal(result.terminal_disposition, 'narrator_presented');
  const qaEvents = sceneEvents.filter((event) => event.type === 'hg/narrator-semantic-qa');
  assert.equal(qaEvents[1]?.payload.player_authorship_repair_verification?.status, 'cleared');
});

test('failed repair with soft downgrade does not render', async (t) => {
  const port = 34800 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const api = createDomainApiClient(host.baseUrl);
  t.after(() => host.stop());

  const { ctx } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => { await ctx.fiber.dispose(); });

  const session = await api.createSession({ cast: ['Alice'], location: 'Study' });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  const commit = await commitAliceMove(api, session.hg_session_id, round.hg_round_id);
  const badCandidate = 'The cold bit sharply against Kizzie\'s skin.';
  const stillBadCandidate = 'The chill stung Kizzie\'s exposed skin.';
  const sceneEvents = [];

  const result = await runNarratorPhase({
    api,
    runEphemeralInference: makeRunEphemeral(
      ctx,
      [badCandidate, stillBadCandidate],
      [
        playerAuthorshipHard('inf-pa-repair-fail-0', 'Unsupported Player skin sensation'),
        playerAuthorshipSoft('inf-pa-repair-fail-1', 'Player skin sensation may remain'),
      ],
    ),
    recorder: ctx.hgPhaseExecutors.executionEvidenceRecorder,
    trace: ctx.hgTraceEmitter,
    sceneAgent: sceneAgentCollector(sceneEvents),
    sceneSessionId: 'scene-pa-repair-fail',
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    characterId: 'Alice',
    domainCommitId: commit.domain_commit_id,
    continuityTurnIndex: commit.continuity_turn_index,
    narratorInferenceId: 'inf-pa-repair-fail',
    mockNarratorResponses: [badCandidate, stillBadCandidate],
    mockNarratorSemanticQaResponses: [],
    characterTurnIndex: 0,
    modelProfile: deepseekInferenceProfile(),
    semanticEvaluatorProfile: deepseekInferenceProfile(),
    narratorSemanticQaEnabled: true,
  });

  assert.equal(result.presentation_rendered, false);
  assert.equal(result.terminal_disposition, 'player_authorship_rejected');
});

test('forensic lineage records repair obligation, correction context, and verification', () => {
  const evalOutcome = makeEvalOutcome({
    overall_result: 'reject_hard',
    findings: [{
      dimension: PLAYER_AUTHORSHIP_DIMENSION,
      severity: 'hard',
      finding: 'Unsupported Player skin sensation',
      rationale: 'no inventory support',
      authoritative_citation: { ref_id: GUARDRAIL },
    }],
  });
  const obligation = buildPlayerAuthorshipRepairObligation({
    evalOutcome,
    evaluationPassId: 'inf-qa-0',
    attemptIndex: 0,
    candidatePresentation: 'The cold bit sharply against Kizzie\'s skin.',
  });
  assert.ok(obligation);
  assert.equal(obligation.source_evaluation_pass_id, 'inf-qa-0');
  assert.match(obligation.offending_assertion, /skin sensation/i);

  const correction = buildCorrectionContextFromNarratorQa(evalOutcome.result, {
    evaluationPassId: 'inf-qa-0',
    playerAuthorshipRepairObligation: obligation,
  });
  assert.ok(correction.player_authorship_repair_obligation);
  assert.match(correction.instruction, /Remove unsupported Player sensation/);

  const verification = assessPlayerAuthorshipRepairVerification(
    obligation,
    makeEvalOutcome({ overall_result: 'reject_soft', findings: [{
      dimension: 'nar_framing_distortion',
      severity: 'soft',
      finding: 'minor framing',
      rationale: 'unrelated',
    }] }, []),
  );
  assert.equal(verification.status, 'unverified');
});
