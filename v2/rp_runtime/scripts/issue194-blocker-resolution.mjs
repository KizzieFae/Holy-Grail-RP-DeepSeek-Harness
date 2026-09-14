/**
 * Issue #194 formal-validation blocker resolution evidence.
 * Run from v2/rp_runtime: node scripts/issue194-blocker-resolution.mjs
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { modelProfileForInferenceKind, resolveApplicationRoleProfiles } from '../src/application/application-settings.mjs';
import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { HG_DEEPSEEK_DEFAULT_MODEL } from '../src/lib/inference-profile.mjs';
import {
  classifyCognitionResultDeliberationProfile,
  DELIBERATION_PROFILE_CONSTRAINED,
  DELIBERATION_PROFILE_DEEP,
  shouldEscalateConstrainedCognitionToDeep,
} from '../src/lib/narrator-environment-deliberation-profile.mjs';
import { runNarratorEnvironmentCognition } from '../src/lib/narrator-environment-cognition-substrate.mjs';
import { buildPlayerVisibilityTriageUserPrompt, runPlayerVisibilityTriagePhase } from '../src/plugins/hg-phase-executors/player-visibility-triage-phase.mjs';
import { runPlayerDecompositionPhase } from '../src/plugins/hg-phase-executors/player-decomposition-phase.mjs';
import { startDomainApi } from '../tests/helpers/domain-api.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

const F06_KNOCK_POST =
  'Kizzie glanced up, double-checking the house number and then steeled herself before knocking.';

const HISTORICAL_F06 = {
  session_id: 'hg-session-f06d7b72-1f3f-47d6-8ab9-c9a6ddd72a40',
  triage_evidence_id: '267644f3-8c0d-4f0a-9f0e-8f3e8b0e0f01',
  triage_result: {
    uniform_projection_safe: false,
    reason: 'requires_semantic_decomposition',
  },
  player_source_normalized_chars: 93,
};

function gitSha() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  } catch {
    return null;
  }
}

function loadAttempt(evidenceRoot, sessionId, attemptId) {
  const attemptPath = path.join(evidenceRoot, sessionId, 'attempts', `${attemptId}.json`);
  return JSON.parse(fs.readFileSync(attemptPath, 'utf8'));
}

function listInferenceAttempts(evidenceRoot, sessionId, inferenceKind, suffix = '') {
  const indexPath = path.join(evidenceRoot, sessionId, 'index.json');
  if (!fs.existsSync(indexPath)) return [];
  const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
  const matches = [];
  for (const attemptId of index.attempt_ids ?? []) {
    const attempt = loadAttempt(evidenceRoot, sessionId, attemptId);
    const corr = attempt.correlation ?? {};
    if (corr.inference_kind !== inferenceKind) continue;
    const infId = String(corr.inference_id ?? '');
    if (suffix && !infId.includes(suffix)) continue;
    if (!suffix && infId.includes('deep-escalation')) continue;
    const usage = attempt.response?.usage ?? {};
    const timing = attempt.inference_health?.timing ?? attempt.timing ?? {};
    matches.push({
      evidence_id: attempt.evidence_id ?? attemptId,
      inference_id: corr.inference_id ?? null,
      wall_ms: timing.inference_wall_clock_ms ?? timing.wall_ms ?? null,
      input_tokens: usage.inputTokens ?? usage.input_tokens ?? null,
      output_tokens: usage.outputTokens ?? usage.output_tokens ?? null,
      reasoning_tokens: usage.reasoningTokens ?? usage.reasoning_tokens ?? null,
      reasoning_effort: attempt.request?.reasoning_effort ?? null,
      assistant_text: attempt.response?.assistant_text ?? null,
      request_user_prompt: attempt.request?.user_prompt ?? attempt.request?.prompt ?? null,
    });
  }
  return matches;
}

function summarizeInferenceAttempt(evidenceRoot, sessionId, inferenceKind, suffix = '') {
  const matches = listInferenceAttempts(evidenceRoot, sessionId, inferenceKind, suffix);
  return matches[0] ?? null;
}

function escalationPredicateDetail(cognitionResult) {
  const needs = cognitionResult?.information_needs ?? [];
  const resolutions = cognitionResult?.resolutions ?? [];
  const categories = [...new Set(
    resolutions
      .filter((item) => item && typeof item === 'object')
      .map((item) => String(item.category ?? '').trim())
      .filter(Boolean),
  )];
  const mediationHits = resolutions.filter((item) => (
    item
    && typeof item === 'object'
    && item.mediation_outcome != null
    && item.mediation_outcome !== ''
    && item.mediation_outcome !== 'no_match'
  ));
  const profile = classifyCognitionResultDeliberationProfile(cognitionResult);
  const predicates = [];
  if (needs.length > 1) predicates.push('information_needs.length > 1');
  if (categories.some((c) => c === 'C' || c === 'cannot_safely_resolve')) {
    predicates.push('resolution category C or cannot_safely_resolve');
  }
  if (mediationHits.length > 0) {
    predicates.push(`mediation_outcome present (${mediationHits.map((m) => m.mediation_outcome).join(', ')})`);
  }
  if (needs.length === 1 && categories.length === 0) {
    predicates.push('single need with empty resolutions[] (fail-safe default deep)');
  }
  if (needs.length === 1 && categories.length > 0 && !categories.every((c) => c === 'B2')) {
    predicates.push(`single need with non-B2 categories: ${categories.join(', ')}`);
  }
  if (needs.length === 1 && categories.length > 0 && categories.every((c) => c === 'B2') && profile === DELIBERATION_PROFILE_CONSTRAINED) {
    predicates.push('compliant single-B2 (no escalation)');
  }
  return {
    need_count: needs.length,
    resolution_count: resolutions.length,
    categories,
    mediation_hits: mediationHits,
    classified_profile: profile,
    escalation_predicates: predicates,
    should_escalate: shouldEscalateConstrainedCognitionToDeep(
      DELIBERATION_PROFILE_CONSTRAINED,
      cognitionResult,
    ),
  };
}

async function runTriageCharacterization({ api, runEphemeralInference, repeats = 5 }) {
  const modelProfile = modelProfileForInferenceKind(
    resolveApplicationRoleProfiles({ inferenceMode: 'live', roleRouting: 'simple', model: HG_DEEPSEEK_DEFAULT_MODEL }).character,
    'player_visibility_triage',
    {},
    { inferenceMode: 'live' },
  );
  const sessionId = `issue194-triage-char-${Date.now()}`;
  await api.createSession({ cast: ['Ayame', 'Kizzie'], hg_session_id: sessionId });
  const userPrompt = buildPlayerVisibilityTriageUserPrompt(F06_KNOCK_POST);
  const runs = [];
  for (let i = 0; i < repeats; i += 1) {
    const result = await runPlayerVisibilityTriagePhase({
      api,
      runEphemeralInference,
      hgSessionId: sessionId,
      hgSceneId: sessionId,
      hgRoundId: `issue194-triage-round-${i}`,
      inferenceId: `issue194-triage-${i}`,
      playerContent: F06_KNOCK_POST,
      modelProfile,
    });
    runs.push({
      run_index: i,
      route: result.route,
      checker_result: result.checkerResult,
    });
  }
  return {
    player_text: F06_KNOCK_POST,
    player_text_length: F06_KNOCK_POST.length,
    triage_user_prompt: userPrompt,
    triage_user_prompt_length: userPrompt.length,
    historical_reference: HISTORICAL_F06.triage_result,
    runs,
    uniform_count: runs.filter((r) => r.route === 'uniform_projection').length,
    semantic_count: runs.filter((r) => r.route === 'full_pvr').length,
  };
}

async function runF06SemanticDecomposition({ api, runEphemeralInference, evidenceRoot }) {
  const sessionId = `issue194-f06-decomp-${Date.now()}`;
  await api.createSession({ cast: ['Ayame', 'Kizzie'], hg_session_id: sessionId });
  const modelProfile = modelProfileForInferenceKind(
    resolveApplicationRoleProfiles({ inferenceMode: 'live', roleRouting: 'simple', model: HG_DEEPSEEK_DEFAULT_MODEL }).character,
    'player_decomposition',
    {},
    { inferenceMode: 'live' },
  );
  const started = Date.now();
  const phaseResult = await runPlayerDecompositionPhase({
    api,
    runEphemeralInference,
    hgSessionId: sessionId,
    hgSceneId: sessionId,
    hgRoundId: `issue194-f06-decomp-round`,
    inferenceId: 'issue194-f06-semantic-decomposition',
    playerContent: F06_KNOCK_POST,
    modelProfile,
  });
  const wallMs = Date.now() - started;
  const attempts = listInferenceAttempts(evidenceRoot, sessionId, 'player_decomposition');
  const units = phaseResult.playerDecomposition?.perceptual_visibility?.units ?? [];
  return {
    path: 'production runPlayerDecompositionPhase (semantic decomposition; triage bypassed)',
    attempt_count: attempts.length,
    retry_used: attempts.length > 1,
    wall_ms_observed: wallMs,
    accepted: Boolean(units.length && !phaseResult.playerDecomposition?.failure_class),
    failure_class: phaseResult.playerDecomposition?.failure_class ?? null,
    normalization_audit: phaseResult.normalizationAudit ?? null,
    unit_count: units.length,
    units: units.map((unit) => ({
      kind: unit.kind,
      scope: unit.recipients?.scope ?? null,
      text: unit.text,
    })),
    attempts,
  };
}

async function setupF06OpeningCommit({ api }) {
  const sessionId = `issue194-env-f06-${Date.now()}`;
  await api.createSession({
    cast: ['Ayame', 'Kizzie'],
    hg_session_id: sessionId,
    location: 'Mansion steps',
  });
  const round = await api.startRound({ hg_scene_id: sessionId });
  await api.recordUserTurn({
    hg_session_id: sessionId,
    content: F06_KNOCK_POST,
    speaker: 'Kizzie',
    hg_round_id: round.hg_round_id,
  });
  const directorDecision = {
    next_actor: 'Ayame',
    end_round: false,
    reason: 'Ayame answers the door.',
    environment_event: '',
    tension_shift: 'steady',
  };
  const validation = await api.validateDirectorDecision({
    hg_scene_id: sessionId,
    hg_round_id: round.hg_round_id,
    inference_id: `inf-director-${sessionId}`,
    turn_index: 0,
    attempt_index: 0,
    proposed_decision: directorDecision,
  });
  if (!validation.accepted) {
    throw new Error(`director validation failed: ${validation.reason ?? 'unknown'}`);
  }
  const validatedMove = {
    move_schema_version: 2,
    beats: [
      { type: 'action', action: 'opens the door and studies the applicant on the step' },
      { type: 'speech', dialogue: 'Punctual. That is a promising beginning.' },
    ],
    motivation: { goal: 'respond', tactic: 'doorway exchange', emotional_driver: 'formal', risk_level: 'medium' },
    semantic_evaluation: { decision: 'no_covered_change' },
  };
  const commit = await api.commitMove({
    inference_id: `inf-commit-${sessionId}`,
    hg_scene_id: sessionId,
    hg_round_id: round.hg_round_id,
    character_id: 'Ayame',
    validated_move: validatedMove,
    director_decision: validation.normalized_decision,
    expected_turn_index: 0,
  });
  if (!commit.committed) {
    throw new Error('commitMove failed for F06 opening setup');
  }
  return {
    sessionId,
    roundId: round.hg_round_id,
    domainCommitId: commit.domain_commit_id,
    continuityTurnIndex: commit.continuity_turn_index ?? 1,
  };
}

async function runEnvCognitionSlice({
  api,
  runEphemeralInference,
  evidenceRoot,
  label,
  sessionId,
  roundId,
  domainCommitId,
  continuityTurnIndex,
}) {
  const inferenceId = `issue194-env-${label}`;
  const modelProfile = resolveApplicationRoleProfiles({
    inferenceMode: 'live',
    roleRouting: 'simple',
    model: HG_DEEPSEEK_DEFAULT_MODEL,
  }).narrator;
  const started = Date.now();
  const result = await runNarratorEnvironmentCognition({
    api,
    runEphemeralInference,
    hgSessionId: sessionId,
    hgSceneId: sessionId,
    hgRoundId: roundId,
    inferenceId,
    characterId: 'Ayame',
    domainCommitId,
    continuityTurnIndex,
    modelProfile,
  });
  const wallMs = Date.now() - started;
  let probeRaw = null;
  let deepRaw = null;
  const probeAttempt = summarizeInferenceAttempt(evidenceRoot, sessionId, 'narrator_environment_cognition');
  const deepAttempt = summarizeInferenceAttempt(evidenceRoot, sessionId, 'narrator_environment_cognition', 'deep-escalation');
  probeRaw = probeAttempt?.assistant_text ?? null;
  deepRaw = deepAttempt?.assistant_text ?? null;
  let probeParsed = null;
  let deepParsed = null;
  try {
    if (probeRaw) probeParsed = JSON.parse(probeRaw);
  } catch { /* ignore */ }
  try {
    if (deepRaw) deepParsed = JSON.parse(deepRaw);
  } catch { /* ignore */ }
  const prepare = await api.prepareNarratorEnvironmentCognitionContext({
    hg_scene_id: sessionId,
    hg_round_id: roundId,
    inference_id: inferenceId,
    character_id: 'Ayame',
    domain_commit_id: domainCommitId,
    continuity_turn_index: continuityTurnIndex,
  });
  return {
    label,
    wall_ms_total: wallMs,
    initial_deliberation_profile: result.initialDeliberationProfile ?? null,
    final_deliberation_profile: result.deliberationProfile ?? null,
    deliberation_profile_escalated: result.deliberationProfileEscalated ?? false,
    prepare_time_profile: prepare?.deliberation_profile ?? null,
    probe: probeAttempt ? {
      ...probeAttempt,
      escalation_analysis: probeParsed ? escalationPredicateDetail(probeParsed) : null,
      cognition_result: probeParsed,
    } : null,
    deep_retry: deepAttempt ? {
      ...deepAttempt,
      cognition_result: deepParsed,
    } : null,
    combined_probe_deep_wall_ms: (probeAttempt?.wall_ms ?? 0) + (deepAttempt?.wall_ms ?? 0),
    combined_probe_deep_reasoning_tokens: (probeAttempt?.reasoning_tokens ?? 0) + (deepAttempt?.reasoning_tokens ?? 0),
    cognition_status: result.environmentCognitionEvidence?.cognition_status ?? null,
  };
}

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    throw new Error('DEEPSEEK_API_KEY required');
  }

  const evidenceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'issue194-blocker-'));
  process.env.HG_EXECUTION_EVIDENCE = 'on';

  const port = 29880 + Math.floor(Math.random() * 100);
  const host = await startDomainApi(port, { withSession: true });
  const api = createDomainApiClient(host.baseUrl);
  const { ctx, phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
    inference: {
      mountDeepSeek: true,
      executionEvidence: { enabled: true, root: evidenceRoot },
    },
  });
  const runEphemeralInference = phaseExecutors.runEphemeralInference.bind(phaseExecutors);

  const report = {
    schema: 'issue194_blocker_resolution_v1',
    generated_at: new Date().toISOString(),
    candidate_sha: gitSha(),
    evidence_root: evidenceRoot,
  };

  console.log('Triage characterization (F06 text)...');
  report.triage_input_equivalence = {
    historical: {
      player_text: F06_KNOCK_POST,
      normalized_length: HISTORICAL_F06.player_source_normalized_chars,
      triage_result: HISTORICAL_F06.triage_result,
      note: 'Challenge/refinement forensic replay; manifest is instruction-only (#121).',
    },
    validation_live_misfire: {
      route: 'uniform_projection',
      checker_result: {
        uniform_projection_safe: true,
        reason: 'affirmative_uniform_present',
      },
      note: 'Prior formal-validation full turn; not reproduced here.',
    },
    authoritative_triage_inputs: {
      player_text_identical: true,
      triage_user_prompt: buildPlayerVisibilityTriageUserPrompt(F06_KNOCK_POST),
      manifest_scope: 'instruction-only (no history/perception metadata in manifest)',
      corpus_expectation: 'full_pvr (neg_internal_cognition / mixed observable+internal)',
    },
  };
  report.triage_characterization = await runTriageCharacterization({
    api,
    runEphemeralInference,
    repeats: 5,
  });

  console.log('F06 semantic decomposition (production path, triage bypassed)...');
  report.f06_semantic_decomposition = await runF06SemanticDecomposition({
    api,
    runEphemeralInference,
    evidenceRoot,
  });

  console.log('F06-shaped environmental cognition (narrow envelope)...');
  const opening = await setupF06OpeningCommit({ api });
  report.f06_environmental_cognition = await runEnvCognitionSlice({
    api,
    runEphemeralInference,
    evidenceRoot,
    label: 'f06-opening',
    sessionId: opening.sessionId,
    roundId: opening.roundId,
    domainCommitId: opening.domainCommitId,
    continuityTurnIndex: opening.continuityTurnIndex,
  });

  console.log('Narrow no-escalation characterization (3 runs)...');
  const narrowRuns = [];
  for (let i = 0; i < 3; i += 1) {
    const narrow = await setupF06OpeningCommit({ api });
    narrowRuns.push(await runEnvCognitionSlice({
      api,
      runEphemeralInference,
      evidenceRoot,
      label: `narrow-char-${i}`,
      sessionId: narrow.sessionId,
      roundId: narrow.roundId,
      domainCommitId: narrow.domainCommitId,
      continuityTurnIndex: narrow.continuityTurnIndex,
    }));
  }
  report.narrow_no_escalation_characterization = {
    runs: narrowRuns,
    no_escalation_count: narrowRuns.filter((r) => !r.deliberation_profile_escalated).length,
    escalation_count: narrowRuns.filter((r) => r.deliberation_profile_escalated).length,
  };

  report.historical_env_cognition_baseline = {
    wall_ms_approx: 55728,
    reasoning_tokens_approx: 11454,
    note: 'Historical F06 single deep cognition call; approximate from investigation record.',
  };

  await host.stop();
  await ctx.fiber.dispose();

  const outPath = path.join(REPO_ROOT, 'governance', 'records', 'issue-194-blocker-resolution-2026-09-14.json');
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ outPath, summary: {
    triage_uniform: report.triage_characterization.uniform_count,
    triage_semantic: report.triage_characterization.semantic_count,
    decomp_attempts: report.f06_semantic_decomposition.attempt_count,
    decomp_accepted: report.f06_semantic_decomposition.accepted,
    env_escalated: report.f06_environmental_cognition.deliberation_profile_escalated,
    narrow_no_escalation: report.narrow_no_escalation_characterization.no_escalation_count,
  } }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
