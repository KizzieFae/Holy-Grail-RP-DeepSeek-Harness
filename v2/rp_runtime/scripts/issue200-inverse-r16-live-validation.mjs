/**
 * Bounded live validation for Issue #200 — inverse R16 objective regression.
 * Run from v2/rp_runtime: node scripts/issue200-inverse-r16-live-validation.mjs
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execSync } from 'node:child_process';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import { runSemanticEvaluation } from '../src/plugins/hg-phase-executors/character-semantic-evaluation.mjs';
import { startDomainApi } from '../tests/helpers/domain-api.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

const PLAYER_ACTION_COMPLETION_GUARDRAIL_ID = 'guardrail:player_action_completion';

const WIPE_POST =
  'Kizzie smiled, wiping her feet on the mat before stepping toward the doorway.';

const MOTIVATION_BASE = {
  goal: 'enforce household entry protocol',
  tactic: 'doorway authority',
  emotional_driver: 'controlled',
  risk_level: 'medium',
};

const CASE_MOVES = {
  A_objective_regression: {
    move_schema_version: 2,
    beats: [
      { type: 'speech', dialogue: 'You have not wiped your feet.' },
    ],
    motivation: MOTIVATION_BASE,
    semantic_evaluation: { decision: 'no_covered_change' },
  },
  B_ignorance_command: {
    move_schema_version: 2,
    beats: [
      { type: 'speech', dialogue: 'Wipe your feet.' },
    ],
    motivation: {
      ...MOTIVATION_BASE,
      goal: 'enforce protocol from incomplete perception',
      tactic: 'command before verifying compliance',
    },
    semantic_evaluation: { decision: 'no_covered_change' },
  },
  C_deliberate_deception: {
    move_schema_version: 2,
    beats: [
      {
        type: 'action',
        action: 'meets Kizzie\'s eyes with deliberate coldness, choosing to feign ignorance she does not possess',
      },
      {
        type: 'speech',
        dialogue: 'You have not wiped your feet. Do not pretend otherwise.',
      },
    ],
    motivation: {
      goal: 'assert dominance through deliberate false accusation',
      tactic: 'manipulation',
      emotional_driver: 'control',
      risk_level: 'high',
    },
    semantic_evaluation: { decision: 'no_covered_change' },
  },
  D_distinct_requirement: {
    move_schema_version: 2,
    beats: [
      { type: 'speech', dialogue: 'Take your shoes off.' },
    ],
    motivation: {
      ...MOTIVATION_BASE,
      goal: 'advance to the next protocol step',
      tactic: 'distinct subsequent requirement',
    },
    semantic_evaluation: { decision: 'no_covered_change' },
  },
};

const LIVE_CASES = [
  {
    case_id: 'A',
    label: 'objective_regression',
    player_post: WIPE_POST,
    move_key: 'A_objective_regression',
    expect: 'r16_hard',
  },
  {
    case_id: 'B',
    label: 'ignorance_command',
    player_post: WIPE_POST,
    move_key: 'B_ignorance_command',
    expect: 'pass',
    epistemic_note:
      'Player wipe is authoritative in player_fact; Character issues command from incomplete perception without objectively denying established completion.',
  },
  {
    case_id: 'C',
    label: 'deliberate_deception',
    player_post: WIPE_POST,
    move_key: 'C_deliberate_deception',
    expect: 'pass',
    epistemic_note:
      'Candidate action/motivation establish deliberate manipulation rather than system factual regression.',
  },
  {
    case_id: 'D',
    label: 'distinct_subsequent_requirement',
    player_post: WIPE_POST,
    move_key: 'D_distinct_requirement',
    expect: 'pass',
  },
];

const EVAL_PROFILE = deepseekInferenceProfile({
  reasoningEffort: 'low',
  maxTokens: 1024,
});

function gitIdentity() {
  try {
    const candidateSha = execSync('git rev-parse HEAD', { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
    const baseSha = execSync('git rev-parse HEAD^', { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
    const dirty = execSync('git status --porcelain', { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
    return {
      base_sha: baseSha,
      candidate_sha: candidateSha,
      working_tree_clean: dirty.length === 0,
      dirty_paths: dirty ? dirty.split('\n') : [],
    };
  } catch {
    return { base_sha: null, candidate_sha: null, working_tree_clean: null, dirty_paths: [] };
  }
}

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
}) {
  const evaluationPassId = `issue200-${caseId}-run0`;
  const evalOutcome = await runSemanticEvaluation({
    api,
    runEphemeralInference,
    recorder: null,
    scope: {
      hgSessionId: session.hg_session_id,
      hgSceneId: session.hg_scene_id,
      hgRoundId: round.hg_round_id,
    },
    characterInferenceId: `inf-issue200-${caseId}`,
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
  return {
    ok: evalOutcome.ok,
    infrastructure_failure: evalOutcome.infrastructureFailure ?? false,
    evidence_id: evalOutcome.evidenceId,
    inference_session_id: evalOutcome.inferenceSessionId ?? null,
    raw_evaluator_output: evalOutcome.raw,
    result: evalOutcome.result,
    classification: classifyEvaluation(evalOutcome.result),
    usage: evalOutcome.trace?.usage ?? null,
  };
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
  return {
    guardrail_declarative: authoritySource.includes(PLAYER_ACTION_COMPLETION_GUARDRAIL_ID),
    inverse_r16_in_guardrail: authoritySource.includes('R16 inverse'),
    eval_instruction_objective_regression: semanticSource.includes('Objective regression'),
    eval_instruction_incomplete_perception: semanticSource.includes('incomplete perception'),
  };
}

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    throw new Error('DEEPSEEK_API_KEY not set; live validation requires provider credentials');
  }

  const provenance = gitIdentity();
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-issue200-live-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const previous = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
  };
  process.env.HG_DATA_DIR = dataDir;
  process.env.HG_EXECUTION_EVIDENCE = 'on';

  const port = 28865 + Math.floor(Math.random() * 1000);
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
    const run = await runLiveEvaluation({
      api,
      runEphemeralInference,
      session,
      round,
      caseId: liveCase.case_id,
      move: CASE_MOVES[liveCase.move_key],
    });
    caseResults.push({
      case_id: liveCase.case_id,
      label: liveCase.label,
      expected: liveCase.expect,
      player_post: liveCase.player_post,
      epistemic_note: liveCase.epistemic_note ?? null,
      candidate_move: CASE_MOVES[liveCase.move_key],
      run: {
        ...run,
        matches_expectation: matchesExpectation(run.classification, liveCase.expect),
      },
    });
  }

  const authorityProjection = verifyAuthorityProjection();
  const allMatched = caseResults.every((c) => c.run.matches_expectation);
  const report = {
    schema: 'issue200_inverse_r16_live_validation_v1',
    generated_at: new Date().toISOString(),
    candidate_provenance: provenance,
    evaluator_profile: EVAL_PROFILE,
    authority_projection: authorityProjection,
    cases: caseResults,
    summary: {
      cases_total: caseResults.length,
      cases_matched: caseResults.filter((c) => c.run.matches_expectation).length,
      all_cases_matched: allMatched,
      validation_pass: allMatched,
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
  const jsonPath = path.join(outDir, `issue-200-live-validation-${stamp}.json`);
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
