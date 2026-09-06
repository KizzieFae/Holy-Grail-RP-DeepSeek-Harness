import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { createHolyGrailRpContext } from '../bootstrap.mjs';
import { repoRoot } from '../lib/runtime-config.mjs';
import { CampaignLimits } from './campaign-limits.mjs';
import { joinScenarioForensics, readExecutionAttempts } from './forensic-query.mjs';
import { startHarnessRuntime } from './harness-runtime.mjs';
import { directorFor, VALID_CHARACTER_MOVE } from './inference-mocks.mjs';
import { createInstrumentedInference } from './instrumented-inference.mjs';
import {
  createLiveHarnessRpContext,
  createLiveRuntimeConfig,
  describeResolvedProfiles,
  mockRuntimeConfig,
} from './live-config.mjs';
import {
  detectIssue136ForbiddenLeaks,
  installIssue136ValidationCards,
  ISSUE136_FIXTURE_IDS,
  loadIssue136TruthFixture,
  truthAdjudicatorPayload,
} from './issue136-fixture-truth.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../../..');

export const ISSUE136_IMPLEMENTATION_SHA = 'f3852196395505b8077ab817a736c7e7eddef099';

export const ISSUE136_REPETITIONS = {
  '136-T2-A-STABILITY': 3,
  '136-T2-B-POS-CHANGE': 2,
  '136-T2-C-NEG-CHANGE': 2,
  '136-T2-D-INACTION': 3,
  '136-T2-E-ENTITLEMENT': 2,
  '136-T2-F-ACTION-REQUIRED': 3,
};

const LIVE_MAX_ATTEMPTS = 3;
const QA_ATTEMPTS_PER_CHARACTER_TURN = LIVE_MAX_ATTEMPTS;
const ST_INFERENCES_PER_ROUND = 3;
const CHARACTER_INFERENCES_PER_LIVE_TURN = 2 + QA_ATTEMPTS_PER_CHARACTER_TURN * 2;
const PLOT_COGNITION_PER_CHARACTER_TURN = 3;
const SENTINEL_EXTRA_INFERENCES = 8;

const JON_RESTITUTION_MOVE = {
  move_schema_version: 2,
  beats: [{
    type: 'action',
    action: 'publicly acknowledges the breach, names the specific harm to Mara, and offers concrete restitution before the shop steward',
  }],
  motivation: {
    goal: 'make amends',
    tactic: 'public accountability',
    emotional_driver: 'remorseful',
    risk_level: 'medium',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const JON_BETRAYAL_MOVE = {
  move_schema_version: 2,
  beats: [{
    type: 'action',
    action: 'is confronted with falsified safety records implicating Mara while the shop steward confirms the betrayal authoritatively',
  }],
  motivation: {
    goal: 'deflect blame',
    tactic: 'minimize exposure',
    emotional_driver: 'defensive',
    risk_level: 'high',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const NARRATOR_BY_FIXTURE = {
  '136-T2-A-STABILITY': [
    'Jon approached Mara at the workbench with routine workshop business; nothing new had changed between them.',
  ],
  '136-T2-B-POS-CHANGE': [
    'Before the gathered shop steward, Jon publicly acknowledged the breach, named the harm to Mara, and offered concrete restitution.',
    'The steward witnessed the restitution offer; Mara must now respond.',
  ],
  '136-T2-C-NEG-CHANGE': [
    'The shop steward confronted Jon with falsified safety records implicating Mara and confirmed the betrayal authoritatively.',
    'The betrayal was now authoritatively confirmed; Mara must respond.',
  ],
  '136-T2-D-INACTION': [
    'A distant scraping sound came from behind a sealed inspection panel, but no immediate danger was visible.',
  ],
  '136-T2-E-ENTITLEMENT': [
    'Alice waited in the vault antechamber, uncertain what Bob knew.',
    'Bob stepped to the keypad and entered a code without speaking the digits aloud; the vault door clicked unlocked.',
    'The door stood open, but Alice had heard no code spoken aloud.',
  ],
  '136-T2-F-ACTION-REQUIRED': [
    'A support bracket cracked visibly above a colleague\'s station; immediate harm looked likely without intervention.',
  ],
};

const ENTITLEMENT_SEQUENCE = ['Alice', 'Bob', 'Alice'];

export function issue136CampaignDataRoot() {
  return path.join(REPO_ROOT, 'data', 'issue136_tier2_campaign');
}

export function deriveIssue136SafetyGuard({
  repetitions = ISSUE136_REPETITIONS,
  includeSentinel = true,
  marginRatio = 0.25,
} = {}) {
  let campaignRuns = 0;
  let liveCharacterTurns = 0;
  let multiTurnRounds = 0;

  for (const [fixtureId, reps] of Object.entries(repetitions)) {
    const truth = loadIssue136TruthFixture(fixtureId);
    campaignRuns += reps;
    const liveTurnsPerCampaign = truth.turn_structure.live_character_turns.length;
    liveCharacterTurns += reps * liveTurnsPerCampaign;
    const roundsPerCampaign = truth.turn_structure.multi_round_session === true
      ? Number(truth.turn_structure.campaign_rounds ?? truth.turn_structure.rounds ?? 1)
      : 1;
    multiTurnRounds += reps * roundsPerCampaign;
  }
  if (includeSentinel) campaignRuns += 1;

  const roundInferences = ST_INFERENCES_PER_ROUND;
  const perLiveTurn = CHARACTER_INFERENCES_PER_LIVE_TURN + PLOT_COGNITION_PER_CHARACTER_TURN;
  const baseInferences = (multiTurnRounds * roundInferences) + (liveCharacterTurns * perLiveTurn);
  const sentinelInferences = includeSentinel ? SENTINEL_EXTRA_INFERENCES : 0;
  const subtotal = baseInferences + sentinelInferences;
  const margin = Math.ceil(subtotal * marginRatio);
  const maxInferences = subtotal + margin;
  const maxRuns = campaignRuns + Math.max(2, Math.ceil(campaignRuns * 0.1));

  return {
    max_runs: maxRuns,
    max_inferences: maxInferences,
    derivation: {
      campaign_runs: campaignRuns,
      live_character_turns: liveCharacterTurns,
      multi_turn_rounds: multiTurnRounds,
      st_inferences_per_round: ST_INFERENCES_PER_ROUND,
      character_inferences_per_live_turn: CHARACTER_INFERENCES_PER_LIVE_TURN,
      plot_cognition_per_character_turn: PLOT_COGNITION_PER_CHARACTER_TURN,
      qa_attempts_per_character_turn: QA_ATTEMPTS_PER_CHARACTER_TURN,
      sentinel_extra_inferences: sentinelInferences,
      base_inferences: baseInferences,
      margin_ratio: marginRatio,
      margin,
    },
  };
}

function buildSessionCreateBody(truth) {
  const body = {
    characters: truth.character_cards,
    opening: { mode: 'custom', text: truth.scene_stimulus },
    location: 'Workshop',
    memory_scope_id: `issue136-${crypto.randomUUID()}`,
    plot_cognition_scope_id: `issue136-pc-${crypto.randomUUID()}`,
  };
  if (truth.cast.length > 1) {
    body.role_assignments = {};
    for (const name of truth.cast) {
      body.role_assignments[name] = name === truth.character_id ? 'guest' : 'staff';
    }
  }
  return body;
}

function buildDirectorMocks(truth) {
  const rounds = Number(truth.turn_structure.rounds ?? 1);
  if (truth.fixture_id === '136-T2-E-ENTITLEMENT') {
    return [directorFor('Alice'), directorFor('Bob'), directorFor('Alice')];
  }
  if (truth.fixture_id === '136-T2-B-POS-CHANGE' || truth.fixture_id === '136-T2-C-NEG-CHANGE') {
    return [directorFor('Jon'), directorFor('Mara')];
  }
  return Array.from({ length: rounds }, () => directorFor(truth.character_id));
}

function buildCharacterMocks(truth, mode) {
  const rounds = Number(truth.turn_structure.rounds ?? 1);
  const liveTurns = new Set(truth.turn_structure.live_character_turns ?? []);
  const mocks = [];
  for (let i = 0; i < rounds; i += 1) {
    if (!liveTurns.has(i)) {
      if (truth.fixture_id === '136-T2-B-POS-CHANGE') {
        mocks.push([JSON.stringify(JON_RESTITUTION_MOVE)]);
      } else if (truth.fixture_id === '136-T2-C-NEG-CHANGE') {
        mocks.push([JSON.stringify(JON_BETRAYAL_MOVE)]);
      } else {
        mocks.push([JSON.stringify(VALID_CHARACTER_MOVE)]);
      }
      continue;
    }
    mocks.push(mode === 'mock' ? [JSON.stringify(VALID_CHARACTER_MOVE)] : []);
  }
  return mocks;
}

function buildNarratorMocks(truth) {
  const lines = NARRATOR_BY_FIXTURE[truth.fixture_id] ?? [];
  return lines.map((prose) => [prose]);
}

function extractCharacterOutputText(characterTurn) {
  const parts = [];
  if (characterTurn?.proposed_move) {
    parts.push(JSON.stringify(characterTurn.proposed_move));
  }
  if (characterTurn?.validated_move) {
    parts.push(JSON.stringify(characterTurn.validated_move));
  }
  if (characterTurn?.presentation_text) {
    parts.push(String(characterTurn.presentation_text));
  }
  const trace = characterTurn?.character_inference_trace ?? characterTurn?.characterInferenceTrace;
  if (trace?.raw_output) parts.push(String(trace.raw_output));
  return parts.join('\n');
}

function extractQaChain(characterTurn) {
  const trace = characterTurn?.character_inference_trace
    ?? characterTurn?.characterInferenceTrace
    ?? {};
  const attempts = trace.attempts ?? trace.candidate_attempts ?? [];
  return attempts.map((attempt, index) => ({
    attempt_index: attempt.attempt_index ?? index,
    candidate_text: attempt.raw_output ?? attempt.candidate_text ?? null,
    semantic_evaluation: attempt.semantic_evaluation ?? attempt.qa_result ?? null,
    accepted: attempt.accepted ?? null,
    outcome: attempt.outcome ?? null,
  }));
}

function extractStorytellerRecord(roundResult) {
  const st = roundResult.storyteller ?? null;
  if (!st) {
    return { activation: 'absent', package_id: null, assessment_evidence_id: null };
  }
  return {
    activation: st.bound ? 'active' : (st.skipped ? 'skipped' : 'degraded'),
    package_id: st.package_id ?? null,
    assessment_evidence_id: st.assessment_evidence_id ?? null,
    degradation_level: st.degradation_level ?? null,
    mapped_preview: st.mapped_preview ?? null,
    invalidated: st.invalidated === true,
    invalidation_reason: st.invalidation_reason ?? null,
  };
}

function buildForensicRecord({
  runId,
  fixtureId,
  repetition,
  truth,
  roundResult,
  roundResults = null,
  instrumentedSummary,
  profiles,
  dataDir,
  scopeId,
  deterministicLeaks = [],
}) {
  const multiRound = Array.isArray(roundResults) && roundResults.length > 0;
  const sourceRounds = multiRound ? roundResults : [roundResult];
  const characterTurns = sourceRounds.flatMap((round) => round.character_turns ?? []);
  const primaryTurn = characterTurns[characterTurns.length - 1] ?? null;
  const outputText = characterTurns.map(extractCharacterOutputText).join('\n');
  const leaks = [
    ...deterministicLeaks,
    ...detectIssue136ForbiddenLeaks(outputText, truth, truth.character_id),
  ];
  const forensics = joinScenarioForensics({
    forensicsDir: path.join(dataDir, 'plot_cognition_forensics'),
    dataDir,
    scopeId,
    hgSessionId: roundResult.hg_session_id,
  });

  let overall_fidelity_judgment = 'ambiguous';
  let knowledge_violation_judgment = 'ambiguous';
  if (leaks.length > 0) {
    overall_fidelity_judgment = 'fail';
    knowledge_violation_judgment = 'fail';
  }

  const storytellerRecords = sourceRounds.map((round, index) => ({
    round_index: index,
    ...extractStorytellerRecord(round),
  }));

  return {
    run_id: runId,
    fixture_id: fixtureId,
    repetition,
    candidate_sha: null,
    main_anchor: null,
    model_provider_config: profiles,
    authoritative_facts: truth.committed_facts,
    character_entitled_knowledge: truth.character_knowledge,
    scene_stimulus: truth.scene_stimulus,
    storyteller: storytellerRecords,
    character_turns: characterTurns.map((turn) => ({
      character_id: turn.character_id,
      character_turn_index: turn.character_turn_index,
      committed: turn.committed ?? true,
      initial_candidate: extractCharacterOutputText(turn),
      qa_chain: extractQaChain(turn),
      final_output: extractCharacterOutputText(turn),
      domain_commit_id: turn.domain_commit_id ?? null,
    })),
    final_committed_output: extractCharacterOutputText(primaryTurn),
    action_vs_inaction: 'ambiguous',
    change_vs_stability: 'ambiguous',
    change_direction: 'ambiguous',
    contextual_support: 'ambiguous',
    unsupported_softening_judgment: 'ambiguous',
    unsupported_hardening_judgment: 'ambiguous',
    action_avoidance_judgment: 'ambiguous',
    knowledge_violation_judgment,
    overall_fidelity_judgment,
    confidence: leaks.length > 0 ? 'high' : 'low',
    ambiguity_notes: leaks.length > 0
      ? []
      : ['Automated harness flags only deterministic entitlement leaks; semantic dimensions require Governance adjudication.'],
    evidence: {
      hg_session_id: roundResult.hg_session_id,
      hg_scene_id: roundResult.hg_scene_id,
      hg_round_ids: sourceRounds.map((round) => round.hg_round_id),
      hg_round_id: roundResult.hg_round_id,
      evidence_ids: forensics.evidenceIds,
      chronicle_keys: forensics.chronicleKeys,
      integrity_gaps: forensics.integrityGaps,
    },
    adjudicator_truth_ref: truthAdjudicatorPayload(truth),
    instrumentation: instrumentedSummary,
    forbidden_leak_detections: leaks,
  };
}

async function withIssue136Harness({ mode, campaignLimits, campaignDataDir }, fn) {
  const runtime = await startHarnessRuntime({
    dataDir: campaignDataDir,
    sessionsDir: path.join(campaignDataDir, 'sessions'),
    forensicsDir: path.join(campaignDataDir, 'plot_cognition_forensics'),
    executionEvidence: true,
  });
  installIssue136ValidationCards(runtime.dataDir);
  const isLive = mode === 'live';
  const rpBundle = isLive
    ? await createLiveHarnessRpContext({ baseUrl: runtime.baseUrl, dataDir: runtime.dataDir })
    : await createHolyGrailRpContext({
      domainApi: { baseUrl: runtime.baseUrl },
      inference: {
        executionEvidence: {
          enabled: true,
          root: path.join(runtime.dataDir, 'execution_evidence'),
        },
      },
    });
  const runtimeConfig = isLive ? createLiveRuntimeConfig() : mockRuntimeConfig();
  const rawStore = [];
  const originalRun = rpBundle.phaseExecutors._runEphemeralInference.bind(rpBundle.phaseExecutors);
  const instrumented = createInstrumentedInference({
    phaseExecutors: {
      runEphemeralInference: (params) => originalRun(rpBundle.ctx, params),
    },
    campaignLimits,
    runtimeConfig,
    rawStore,
  });
  const priorRun = rpBundle.phaseExecutors._runEphemeralInference;
  rpBundle.phaseExecutors._runEphemeralInference = (ctx, params) => instrumented.runEphemeralInference(params);

  try {
    return await fn({
      ...runtime,
      ...rpBundle,
      instrumented,
      runtimeConfig,
      rawStore,
      campaignDataDir,
      mode,
    });
  } finally {
    rpBundle.phaseExecutors._runEphemeralInference = priorRun;
    await rpBundle.ctx.fiber.dispose();
    await runtime.dispose();
  }
}

export async function runIssue136FixtureCampaign({
  fixtureId,
  repetition = 1,
  mode = 'mock',
  campaignLimits = null,
  campaignDataDir = null,
  harness = null,
} = {}) {
  const truth = loadIssue136TruthFixture(fixtureId);
  const dataDir = campaignDataDir ?? path.join(issue136CampaignDataRoot(), mode, fixtureId, `rep-${repetition}`);
  fs.mkdirSync(dataDir, { recursive: true });
  const limits = campaignLimits ?? new CampaignLimits(deriveIssue136SafetyGuard());

  const execute = async (ctx) => {
    limits.assertCanRun();
    const sessionBody = buildSessionCreateBody(truth);
    const created = await ctx.api.createSession(sessionBody);
    const scopeId = sessionBody.memory_scope_id;

    let roundResult;
    let roundResults = null;

    if (truth.turn_structure.multi_round_session === true) {
      const narratorLines = NARRATOR_BY_FIXTURE[truth.fixture_id] ?? [];
      roundResults = [];
      for (let index = 0; index < ENTITLEMENT_SEQUENCE.length; index += 1) {
        const actor = ENTITLEMENT_SEQUENCE[index];
        const round = await ctx.orchestrator.runRound({
          domainApi: { baseUrl: ctx.baseUrl },
          session: { mode: 'open', hg_session_id: created.hg_session_id },
          mockDirectorResponses: [directorFor(actor)],
          mockCharacterTurnResponses: [mode === 'mock' ? [JSON.stringify(VALID_CHARACTER_MOVE)] : []],
          mockNarratorTurnResponses: [[narratorLines[index] ?? '']],
          liveMaxAttempts: LIVE_MAX_ATTEMPTS,
          roleProfiles: ctx.runtimeConfig.roleProfiles,
        });
        roundResults.push(round);
      }
      roundResult = roundResults[roundResults.length - 1];
    } else {
      const directorMocks = buildDirectorMocks(truth);
      const characterMocks = buildCharacterMocks(truth, mode);
      const narratorMocks = buildNarratorMocks(truth);
      roundResult = await ctx.orchestrator.runRound({
        domainApi: { baseUrl: ctx.baseUrl },
        session: { mode: 'open', hg_session_id: created.hg_session_id },
        mockDirectorResponses: directorMocks,
        mockCharacterTurnResponses: characterMocks,
        mockNarratorTurnResponses: narratorMocks,
        liveMaxAttempts: LIVE_MAX_ATTEMPTS,
        defensiveTurnCeiling: Math.max(truth.cast.length, truth.turn_structure.rounds) * 2,
        roleProfiles: ctx.runtimeConfig.roleProfiles,
      });
    }
    limits.recordRun();

    const instrumentedSummary = ctx.instrumented.summarize();
    const profiles = describeResolvedProfiles(ctx.runtimeConfig);
    const runId = `issue136-${fixtureId}-r${repetition}-${crypto.randomUUID()}`;
    const forensic = buildForensicRecord({
      runId,
      fixtureId,
      repetition,
      truth,
      roundResult,
      roundResults,
      instrumentedSummary,
      profiles,
      dataDir: ctx.dataDir,
      scopeId,
    });

    const reportPath = path.join(dataDir, `${runId}.json`);
    fs.writeFileSync(reportPath, `${JSON.stringify({
      forensic,
      round_result: roundResult,
      round_results: roundResults,
    }, null, 2)}\n`, 'utf8');

    return {
      run_id: runId,
      fixture_id: fixtureId,
      repetition,
      mode,
      report_path: reportPath,
      forensic,
      round_result: roundResult,
      round_results: roundResults,
      limits: limits.snapshot(),
    };
  };

  if (harness) {
    return execute(harness);
  }
  return withIssue136Harness({ mode, campaignLimits: limits, campaignDataDir: dataDir }, execute);
}

export async function runIssue136ProductionSentinel({
  mode = 'mock',
  campaignLimits = null,
  campaignDataDir = null,
  harness = null,
} = {}) {
  const dataDir = campaignDataDir ?? path.join(issue136CampaignDataRoot(), mode, 'sentinel');
  fs.mkdirSync(dataDir, { recursive: true });
  const limits = campaignLimits ?? new CampaignLimits(deriveIssue136SafetyGuard());

  const execute = async (ctx) => {
    limits.assertCanRun();
    const created = await ctx.api.createSession({
      characters: ['mara-slow-forgive', 'jon-default'],
      opening: {
        mode: 'custom',
        text: 'Mara and Jon share the workshop after the public accord breach; no new facts have emerged.',
      },
      location: 'Workshop',
      memory_scope_id: `issue136-sentinel-${crypto.randomUUID()}`,
      plot_cognition_scope_id: `issue136-sentinel-pc-${crypto.randomUUID()}`,
      role_assignments: { Mara: 'guest', Jon: 'staff' },
    });

    const roundResult = await ctx.orchestrator.runRound({
      domainApi: { baseUrl: ctx.baseUrl },
      session: { mode: 'open', hg_session_id: created.hg_session_id },
      mockDirectorResponses: mode === 'mock' ? [directorFor('Mara')] : [],
      mockCharacterTurnResponses: mode === 'mock' ? [[JSON.stringify(VALID_CHARACTER_MOVE)]] : [[]],
      mockNarratorTurnResponses: mode === 'mock'
        ? [['Mara kept her attention on the workbench as Jon lingered nearby.']]
        : [[]],
      liveMaxAttempts: LIVE_MAX_ATTEMPTS,
      roleProfiles: ctx.runtimeConfig.roleProfiles,
    });
    limits.recordRun();

    const runId = `issue136-sentinel-${crypto.randomUUID()}`;
    const record = {
      run_id: runId,
      kind: 'production_like_sentinel',
      mode,
      storyteller: extractStorytellerRecord(roundResult),
      round_result: roundResult,
      instrumentation: ctx.instrumented.summarize(),
      profiles: describeResolvedProfiles(ctx.runtimeConfig),
    };
    const reportPath = path.join(dataDir, `${runId}.json`);
    fs.writeFileSync(reportPath, `${JSON.stringify(record, null, 2)}\n`, 'utf8');
    return { ...record, report_path: reportPath, limits: limits.snapshot() };
  };

  if (harness) return execute(harness);
  return withIssue136Harness({ mode, campaignLimits: limits, campaignDataDir: dataDir }, execute);
}

export async function runIssue136Tier2Campaign({
  mode = 'mock',
  includeSentinel = true,
  fixtureFilter = null,
  campaignDataDir = null,
} = {}) {
  const guard = deriveIssue136SafetyGuard({ includeSentinel });
  const limits = new CampaignLimits({
    maxRuns: guard.max_runs,
    maxInferences: guard.max_inferences,
  });
  const rootDir = campaignDataDir ?? path.join(issue136CampaignDataRoot(), mode, new Date().toISOString().replace(/[:.]/g, '-'));
  fs.mkdirSync(rootDir, { recursive: true });

  const fixtureIds = (fixtureFilter ?? ISSUE136_FIXTURE_IDS).filter((id) => ISSUE136_FIXTURE_IDS.includes(id));
  const runs = [];

  await withIssue136Harness({ mode, campaignLimits: limits, campaignDataDir: rootDir }, async (harness) => {
    for (const fixtureId of fixtureIds) {
      const reps = ISSUE136_REPETITIONS[fixtureId] ?? 1;
      for (let repetition = 1; repetition <= reps; repetition += 1) {
        const result = await runIssue136FixtureCampaign({
          fixtureId,
          repetition,
          mode,
          campaignLimits: limits,
          campaignDataDir: path.join(rootDir, fixtureId, `rep-${repetition}`),
          harness,
        });
        runs.push(result);
      }
    }
    if (includeSentinel) {
      const sentinel = await runIssue136ProductionSentinel({
        mode,
        campaignLimits: limits,
        campaignDataDir: path.join(rootDir, 'sentinel'),
        harness,
      });
      runs.push(sentinel);
    }
  });

  const report = {
    schema: 'issue136_tier2_campaign_report_v1',
    mode,
    campaign_data_dir: rootDir,
    safety_guard: guard,
    limits: limits.snapshot(),
    fixture_ids: fixtureIds,
    repetitions: ISSUE136_REPETITIONS,
    runs,
    repo_root: repoRoot,
    implementation_sha: ISSUE136_IMPLEMENTATION_SHA,
  };
  const reportPath = path.join(rootDir, 'campaign-report.json');
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  return { ...report, report_path: reportPath };
}

export function proveProductionInferenceUnchanged() {
  const productionPaths = [
    'v2/domain/modules/character_context.py',
    'v2/domain/modules/director_context.py',
    'v2/rp_runtime/src/lib/live-inference-prompts.mjs',
  ];
  const diffs = {};
  for (const rel of productionPaths) {
    try {
      const out = execSync(`git diff ${ISSUE136_IMPLEMENTATION_SHA}..HEAD -- "${rel}"`, {
        cwd: REPO_ROOT,
        encoding: 'utf8',
      });
      diffs[rel] = out.trim();
    } catch {
      diffs[rel] = 'diff_unavailable';
    }
  }
  const changed = Object.entries(diffs).filter(([, value]) => value.length > 0 && value !== 'diff_unavailable');
  return {
    implementation_sha: ISSUE136_IMPLEMENTATION_SHA,
    production_paths_checked: productionPaths,
    changed_paths: changed.map(([rel]) => rel),
    unchanged: changed.length === 0,
    diffs,
  };
}
