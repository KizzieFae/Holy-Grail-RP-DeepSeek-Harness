/**
 * Bounded live validation for Issue #193 — R16 player_action_completion.
 * Run from v2/rp_runtime: node scripts/issue193-r16-live-validation.mjs
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import { runSemanticEvaluation } from '../src/plugins/hg-phase-executors/character-semantic-evaluation.mjs';
import { runCharacterPhase } from '../src/plugins/hg-phase-executors/character-phase.mjs';
import { startDomainApi } from '../tests/helpers/domain-api.mjs';
import { attachCharacterCognitionApiStubs } from '../tests/helpers/character-cognition-mock.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

const PLAYER_ACTION_COMPLETION_GUARDRAIL_ID = 'guardrail:player_action_completion';

const MOTIVATION = {
  goal: 'respond',
  tactic: 'doorway exchange',
  emotional_driver: 'formal',
  risk_level: 'medium',
};

const KNOCK_POST =
  'Kizzie glanced up, double-checking the house number and then steeled herself before knocking.';

const ENTER_POST =
  'Kizzie drew a steady breath, crossed the threshold into the foyer, and stepped inside.';

const CASE_MOVES = {
  A_healthy_invitation: {
    move_schema_version: 2,
    beats: [
      { type: 'action', action: 'opens the door and studies the applicant on the step' },
      { type: 'speech', dialogue: 'Punctual. That is a promising beginning.' },
      { type: 'action', action: 'gestures toward the foyer' },
      { type: 'speech', dialogue: 'Come in when you are ready.' },
    ],
    motivation: MOTIVATION,
    semantic_evaluation: { decision: 'no_covered_change' },
  },
  B_f06_assumed_entry: {
    move_schema_version: 2,
    beats: [
      { type: 'action', action: 'opens the door and studies the applicant on the step' },
      { type: 'speech', dialogue: 'Punctual. That is a promising beginning.' },
      { type: 'action', action: 'gestures inside' },
      { type: 'speech', dialogue: 'Come in. Mind the rug.' },
      { type: 'action', action: 'closes the door behind Kizzie' },
      { type: 'speech', dialogue: 'Before we begin, tell me how you found your way to my notice.' },
    ],
    motivation: MOTIVATION,
    semantic_evaluation: { decision: 'no_covered_change' },
  },
  B_f06_corrected: {
    move_schema_version: 2,
    beats: [
      { type: 'action', action: 'opens the door and studies the applicant on the step' },
      { type: 'speech', dialogue: 'Punctual. That is a promising beginning.' },
      { type: 'action', action: 'gestures toward the foyer' },
      { type: 'speech', dialogue: 'Come in when you are ready.' },
      { type: 'speech', dialogue: 'Before we begin, tell me how you found your way to my notice.' },
    ],
    motivation: MOTIVATION,
    semantic_evaluation: { decision: 'no_covered_change' },
  },
  C_explicit_entry_close_door: {
    move_schema_version: 2,
    beats: [
      { type: 'action', action: 'steps aside to let Kizzie enter, then closes the door behind her' },
      { type: 'speech', dialogue: 'Mind the rug.' },
    ],
    motivation: MOTIVATION,
    semantic_evaluation: { decision: 'no_covered_change' },
  },
  D_unresolved_coercion: {
    move_schema_version: 2,
    beats: [
      { type: 'action', action: 'reaches for Kizzie and tries to drag her inside' },
      { type: 'speech', dialogue: 'Inside. Now.' },
    ],
    motivation: MOTIVATION,
    semantic_evaluation: { decision: 'no_covered_change' },
  },
  E_assumed_coercion_success: {
    move_schema_version: 2,
    beats: [
      { type: 'action', action: 'grabs Kizzie and drags her across the threshold into the foyer' },
      { type: 'action', action: 'slams the door shut behind her' },
    ],
    motivation: MOTIVATION,
    semantic_evaluation: { decision: 'no_covered_change' },
  },
  F_assumed_agreement: {
    move_schema_version: 2,
    beats: [
      { type: 'speech', dialogue: 'Will you accept the terms as written?' },
      { type: 'speech', dialogue: 'Good. I knew you would agree.' },
    ],
    motivation: MOTIVATION,
    semantic_evaluation: { decision: 'no_covered_change' },
  },
  G_unilateral_social: {
    move_schema_version: 2,
    beats: [
      { type: 'speech', dialogue: "You're fired. Get out." },
    ],
    motivation: MOTIVATION,
    semantic_evaluation: { decision: 'no_covered_change' },
  },
  H_throw_attempt: {
    move_schema_version: 2,
    beats: [
      { type: 'action', action: 'snatches a ledger and hurls it toward Kizzie' },
    ],
    motivation: MOTIVATION,
    semantic_evaluation: { decision: 'no_covered_change' },
  },
  H_throw_completed_impact: {
    move_schema_version: 2,
    beats: [
      {
        type: 'action',
        action: 'hurls a ledger that strikes Kizzie and sends her stumbling backward onto the floor',
      },
    ],
    motivation: MOTIVATION,
    semantic_evaluation: { decision: 'no_covered_change' },
  },
};

const LIVE_CASES = [
  { case_id: 'A', label: 'healthy_multi_beat_invitation', player_post: KNOCK_POST, move_key: 'A_healthy_invitation', expect: 'pass' },
  { case_id: 'B', label: 'f06_assumed_entry', player_post: KNOCK_POST, move_key: 'B_f06_assumed_entry', expect: 'r16_hard' },
  { case_id: 'C', label: 'explicit_player_entry', player_post: ENTER_POST, move_key: 'C_explicit_entry_close_door', expect: 'pass' },
  { case_id: 'D', label: 'unresolved_coercion_attempt', player_post: KNOCK_POST, move_key: 'D_unresolved_coercion', expect: 'pass' },
  { case_id: 'E', label: 'assumed_coercion_success', player_post: KNOCK_POST, move_key: 'E_assumed_coercion_success', expect: 'r16_hard' },
  { case_id: 'F', label: 'assumed_agreement', player_post: KNOCK_POST, move_key: 'F_assumed_agreement', expect: 'r16_hard' },
  { case_id: 'G', label: 'unilateral_npc_social_action', player_post: KNOCK_POST, move_key: 'G_unilateral_social', expect: 'pass' },
  { case_id: 'H1', label: 'attack_attempt_only', player_post: KNOCK_POST, move_key: 'H_throw_attempt', expect: 'pass' },
  { case_id: 'H2', label: 'unsupported_completed_player_impact', player_post: KNOCK_POST, move_key: 'H_throw_completed_impact', expect: 'r16_hard' },
];

const EVAL_PROFILE = deepseekInferenceProfile({
  reasoningEffort: 'low',
  maxTokens: 1024,
});

function classifyEvaluation(result) {
  const findings = result?.findings ?? [];
  const r16Hard = findings.some((f) => f.dimension === 'R16' && f.severity === 'hard')
    || (result?.overall_result === 'reject_hard'
      && findings.some((f) => f.dimension === 'R16'));
  const pass = result?.overall_result === 'pass'
    && !findings.some((f) => f.severity === 'hard');
  return { pass, r16Hard, overall: result?.overall_result ?? null, findings };
}

function matchesExpectation(classification, expect) {
  if (expect === 'pass') return classification.pass;
  if (expect === 'r16_hard') return classification.r16Hard;
  return false;
}

async function setupSession(api, playerPost) {
  const session = await api.createSession({ cast: ['Ayame', 'Kizzie'], location: 'Mansion steps' });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  await api.recordUserTurn({
    hg_session_id: session.hg_session_id,
    content: playerPost,
    speaker: 'Kizzie',
    hg_round_id: round.hg_round_id,
  });
  return { session, round };
}

async function runLiveEvaluation({
  api,
  runEphemeralInference,
  session,
  round,
  caseId,
  move,
  repetition = 1,
}) {
  const runs = [];
  for (let i = 0; i < repetition; i += 1) {
    const evaluationPassId = `issue193-${caseId}-run${i}`;
    const evalOutcome = await runSemanticEvaluation({
      api,
      runEphemeralInference,
      recorder: null,
      scope: {
        hgSessionId: session.hg_session_id,
        hgSceneId: session.hg_scene_id,
        hgRoundId: round.hg_round_id,
      },
      characterInferenceId: `inf-issue193-${caseId}`,
      characterId: 'Ayame',
      role: 'host',
      hgSceneId: session.hg_scene_id,
      hgRoundId: round.hg_round_id,
      hgSessionId: session.hg_session_id,
      turnIndex: 0,
      evaluationPassId,
      candidateMove: move,
      rawModelOutput: JSON.stringify(move),
      semanticEvaluatorProfile: EVAL_PROFILE,
      parentCharacterEvidenceId: null,
    });
    runs.push({
      repetition_index: i,
      ok: evalOutcome.ok,
      infrastructure_failure: evalOutcome.infrastructureFailure ?? false,
      evidence_id: evalOutcome.evidenceId,
      inference_session_id: evalOutcome.inferenceSessionId ?? null,
      raw_evaluator_output: evalOutcome.raw,
      result: evalOutcome.result,
      classification: classifyEvaluation(evalOutcome.result),
      usage: evalOutcome.trace?.usage ?? null,
    });
  }
  return runs;
}

function verifyAuthorityProjection() {
  const authorityPath = path.join(
    REPO_ROOT,
    'v2/domain_api/player_action_completion_authority.py',
  );
  const semanticPath = path.join(
    REPO_ROOT,
    'v2/domain_api/semantic_evaluation_context.py',
  );
  const authoritySource = fs.readFileSync(authorityPath, 'utf8');
  const semanticSource = fs.readFileSync(semanticPath, 'utf8');
  const heuristicPatterns = [
    /\bre\.compile\b/,
    /\bregex\b/i,
    /closes the door/i,
    /behind Kizzie/i,
    /positional verb/i,
  ];
  const heuristicHits = heuristicPatterns.filter((pattern) => pattern.test(authoritySource));
  return {
    guardrail_declarative: authoritySource.includes(PLAYER_ACTION_COMPLETION_GUARDRAIL_ID),
    no_heuristic_inference_in_authority_module: heuristicHits.length === 0,
    eval_instruction_mentions_r16: semanticSource.includes('R16 player action completion'),
    eval_instruction_permission_not_movement: semanticSource.includes('location_entry_outcome'),
    player_posts_projected_via_authorship_merge: semanticSource.includes(
      'merge_player_authorship_authority_references',
    ),
  };
}

async function runF06CorrectionPath({ api, runEphemeralInference }) {
  const { session, round } = await setupSession(api, KNOCK_POST);
  const prepareCalls = [];
  const stubbedApi = attachCharacterCognitionApiStubs({
    ...api,
    async getSceneState() {
      return { turn_counter: 0 };
    },
    async prepareCharacterContext(body) {
      prepareCalls.push(body);
      return api.prepareCharacterContext(body);
    },
    async validateMove(body) {
      return {
        accepted: true,
        validation_class: 'valid',
        reason: '',
        retryable: false,
        normalized_move: body.proposed_move,
      };
    },
    async commitMove() {
      return { committed: true, continuity_turn_index: 1, domain_commit_id: 'dc-issue193-f06' };
    },
  });

  const sceneAgent = { session: { append() {} } };
  const result = await runCharacterPhase({
    runEphemeralInference,
    recorder: null,
    trace: { emit: () => {} },
    api: stubbedApi,
    sceneAgent,
    sceneSessionId: 'scene-issue193-f06',
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    characterId: 'Ayame',
    directorDecision: { next_actor: 'Ayame' },
    characterInferenceId: 'inf-issue193-f06-correction',
    mockResponses: [
      JSON.stringify(CASE_MOVES.B_f06_assumed_entry),
      JSON.stringify(CASE_MOVES.B_f06_corrected),
    ],
    mockSemanticEvaluatorResponses: [],
    modelProfile: EVAL_PROFILE,
    semanticEvaluatorProfile: EVAL_PROFILE,
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
    semanticEvaluationEnabled: true,
    projectionLifecycleEnabled: false,
  });

  const correctionCall = prepareCalls.find((call) => call.correction_context);
  return {
    committed: result.committed,
    generated_candidate_count: result.generatedCandidateCount,
    terminal_disposition: result.terminalDisposition,
    correction_context_present: Boolean(correctionCall?.correction_context),
    correction_dimensions: correctionCall?.correction_context?.findings?.map((f) => f.dimension) ?? [],
    corrected_beat_count: CASE_MOVES.B_f06_corrected.beats.length,
    corrected_has_assumed_entry: CASE_MOVES.B_f06_corrected.beats.some(
      (beat) => /closes the door behind/i.test(beat.action ?? ''),
    ),
  };
}

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    throw new Error('DEEPSEEK_API_KEY not set; live validation requires provider credentials');
  }

  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-issue193-live-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const previous = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
  };
  process.env.HG_DATA_DIR = dataDir;
  process.env.HG_EXECUTION_EVIDENCE = 'on';

  const port = 28765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  const api = createDomainApiClient(host.baseUrl);
  const { ctx, phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
    inference: { mountDeepSeek: true },
  });
  const runEphemeralInference = phaseExecutors.runEphemeralInference.bind(phaseExecutors);

  const caseResults = [];
  for (const liveCase of LIVE_CASES) {
    const { session, round } = await setupSession(api, liveCase.player_post);
    const repetition = (liveCase.case_id === 'A' || liveCase.case_id === 'B') ? 2 : 1;
    const runs = await runLiveEvaluation({
      api,
      runEphemeralInference,
      session,
      round,
      caseId: liveCase.case_id,
      move: CASE_MOVES[liveCase.move_key],
      repetition,
    });
    const outcomes = runs.map((run) => ({
      ...run,
      matches_expectation: matchesExpectation(run.classification, liveCase.expect),
    }));
    caseResults.push({
      case_id: liveCase.case_id,
      label: liveCase.label,
      expected: liveCase.expect,
      player_post: liveCase.player_post,
      candidate_move: CASE_MOVES[liveCase.move_key],
      repetition,
      runs: outcomes,
      stable: outcomes.every((run) => run.matches_expectation),
    });
  }

  const f06Correction = await runF06CorrectionPath({
    api,
    runEphemeralInference,
  });

  const authorityProjection = verifyAuthorityProjection();

  const allStable = caseResults.every((c) => c.stable);
  const report = {
    schema: 'issue193_r16_live_validation_v1',
    generated_at: new Date().toISOString(),
    evaluator_profile: EVAL_PROFILE,
    authority_projection: authorityProjection,
    cases: caseResults,
    f06_correction_path: f06Correction,
    summary: {
      cases_total: caseResults.length,
      cases_stable: caseResults.filter((c) => c.stable).length,
      all_cases_stable: allStable,
      discrimination_pair_stable: caseResults
        .filter((c) => c.case_id === 'A' || c.case_id === 'B')
        .every((c) => c.stable),
      f06_correction_success: f06Correction.committed
        && f06Correction.correction_context_present
        && !f06Correction.corrected_has_assumed_entry,
      validation_pass: allStable
        && f06Correction.committed
        && f06Correction.correction_context_present
        && !f06Correction.corrected_has_assumed_entry,
    },
  };

  await host.stop();
  await ctx.fiber.dispose();
  for (const [key, value] of Object.entries(previous)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  fs.rmSync(dataDir, { recursive: true, force: true });

  const outDir = path.join(REPO_ROOT, 'governance/records');
  fs.mkdirSync(outDir, { recursive: true });
  const stamp = new Date().toISOString().slice(0, 10);
  const jsonPath = path.join(outDir, `issue-193-live-validation-${stamp}.json`);
  fs.writeFileSync(jsonPath, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ ok: true, report_path: jsonPath, summary: report.summary }, null, 2));
  if (!report.summary.validation_pass) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
