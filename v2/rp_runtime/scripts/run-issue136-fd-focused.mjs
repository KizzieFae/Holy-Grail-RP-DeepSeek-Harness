/**
 * Issue #136 — focused live validation: F×3 + D×2 (5 runs only).
 * Does NOT run A/B/C/E, sentinel, or full Tier-2 campaign.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { readExecutionAttempts } from '../tests/helpers/plot-cognition-projection-fixtures.mjs';
import {
  deriveIssue136SafetyGuard,
  ISSUE136_FD_FOCUSED_FIXTURE_ORDER,
  ISSUE136_FD_FOCUSED_REPETITIONS,
  ISSUE136_IMPLEMENTATION_SHA,
  proveProductionInferenceUnchanged,
  runIssue136Tier2Campaign,
} from '../src/scenario-harness/issue136-tier2-campaign.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

function findAttemptsByKind(attempts, inferenceKind) {
  return attempts.filter((attempt) => attempt.correlation?.inference_kind === inferenceKind);
}

function extractTranscriptFromAttempt(attempt) {
  const contributions = attempt?.request?.contributions
    ?? attempt?.request?.assembled_request?.contributions
    ?? [];
  const transcript = contributions.find((c) => c.source_kind === 'recent_scene_transcript');
  const sceneSetup = contributions.find((c) => c.source_kind === 'scene_setup');
  const directorContext = contributions.find((c) => c.source_kind === 'director_context');
  const contract = contributions.find((c) => String(c.contribution_id ?? '').endsWith('-response-contract'));
  return {
    manifest_id: attempt?.request?.assembled_request?.manifest_id
      ?? attempt?.correlation?.manifest_id
      ?? null,
    recent_scene_transcript: transcript ? {
      contribution_id: transcript.contribution_id,
      source_kind: transcript.source_kind,
      priority: transcript.priority,
      content_preview: String(transcript.content ?? '').slice(0, 800),
    } : null,
    scene_setup: sceneSetup ? {
      contribution_id: sceneSetup.contribution_id,
      content_preview: String(sceneSetup.content ?? '').slice(0, 300),
    } : null,
    director_context: directorContext ? {
      contribution_id: directorContext.contribution_id,
      content_preview: String(directorContext.content ?? '').slice(0, 500),
    } : null,
    response_contract: contract ? {
      contribution_id: contract.contribution_id,
      provenance: contract.provenance ?? null,
    } : null,
  };
}

function extractStorytellerFinalize(attempts) {
  const orientation = findAttemptsByKind(attempts, 'storyteller_orientation').at(-1);
  const assessment = findAttemptsByKind(attempts, 'storyteller_assessment').at(-1);
  const librarian = findAttemptsByKind(attempts, 'librarian_mediation').at(-1)
    ?? findAttemptsByKind(attempts, 'librarian_context_mediation').at(-1);
  return {
    orientation_finalize: {
      accepted: orientation?.decision?.storyteller_orientation?.accepted
        ?? orientation?.decision?.finalize?.accepted
        ?? orientation?.decision?.orientation_finalize?.accepted
        ?? null,
      reason: orientation?.decision?.finalize?.reason
        ?? orientation?.decision?.orientation_finalize?.reason
        ?? null,
      evidence_id: orientation?.evidence_id ?? null,
    },
    assessment_finalize: {
      accepted: assessment?.decision?.storyteller_advisory?.assessment_accepted
        ?? assessment?.decision?.finalize?.accepted
        ?? assessment?.decision?.assessment_finalize?.accepted
        ?? null,
      reason: assessment?.decision?.finalize?.reason
        ?? assessment?.decision?.assessment_finalize?.reason
        ?? null,
      evidence_id: assessment?.evidence_id ?? null,
    },
    librarian: {
      degradation_mode: librarian?.decision?.librarian_mediation?.degradation_mode
        ?? librarian?.decision?.degradation_mode
        ?? null,
      terminal: librarian?.decision?.terminal ?? null,
      evidence_id: librarian?.evidence_id ?? null,
    },
  };
}

function sumTokenUsage(attempts) {
  let prompt = 0;
  let completion = 0;
  for (const attempt of attempts) {
    const usage = attempt?.response?.usage ?? attempt?.response?.token_usage ?? null;
    if (!usage) continue;
    prompt += Number(usage.prompt_tokens ?? usage.input_tokens ?? usage.inputTokens ?? 0);
    completion += Number(usage.completion_tokens ?? usage.output_tokens ?? usage.outputTokens ?? 0);
  }
  return { prompt_tokens: prompt, completion_tokens: completion, total_tokens: prompt + completion };
}

function extractDirectorCue(roundResult) {
  const turn = (roundResult?.character_turns ?? [])[0] ?? null;
  const decision = turn?.director_decision ?? roundResult?.director_decision ?? null;
  if (!decision) return null;
  return {
    next_actor: decision.next_actor ?? null,
    environment_event: decision.environment_event ?? null,
    reason: decision.reason ?? null,
    tension_shift: decision.tension_shift ?? null,
  };
}

function extractCharacterRun(roundResult, attempts) {
  const turn = (roundResult?.character_turns ?? []).find((t) => t.character_id === 'Mara')
    ?? (roundResult?.character_turns ?? [])[0]
    ?? null;
  const moveAttempts = findAttemptsByKind(attempts, 'character_move');
  const qaAttempts = findAttemptsByKind(attempts, 'character_semantic_qa');
  const committedAttempt = moveAttempts.find((a) => a.decision?.commit?.committed === true)
    ?? moveAttempts.at(-1)
    ?? null;
  const manifestProof = committedAttempt ? extractTranscriptFromAttempt(committedAttempt) : null;
  const trace = turn?.character_inference_trace ?? turn?.characterInferenceTrace ?? {};
  const attemptChain = (trace.attempts ?? trace.candidate_attempts ?? []).map((a, index) => ({
    attempt_index: a.attempt_index ?? index,
    accepted: a.accepted ?? null,
    outcome: a.outcome ?? null,
    semantic_evaluation: a.semantic_evaluation ?? a.qa_result ?? null,
    raw_output_preview: String(a.raw_output ?? a.candidate_text ?? '').slice(0, 1500),
  }));
  return {
    character_id: turn?.character_id ?? 'Mara',
    committed: turn?.committed ?? null,
    domain_commit_id: turn?.domain_commit_id ?? null,
    proposed_move: turn?.proposed_move ?? null,
    validated_move: turn?.validated_move ?? null,
    presentation_text: turn?.presentation_text ?? null,
    attempts: attemptChain,
    semantic_qa: qaAttempts.map((a) => ({
      evidence_id: a.evidence_id,
      decision: a.decision ?? null,
    })),
    manifest_proof: manifestProof,
    contract_revision: manifestProof?.response_contract?.provenance?.response_contract_revision ?? null,
    contract_digest: manifestProof?.response_contract?.provenance?.response_contract_digest ?? null,
  };
}

function buildRunRecord(run, gateRoot) {
  const round = run.round_result ?? {};
  const hgSessionId = run.forensic?.evidence?.hg_session_id ?? round.hg_session_id ?? null;
  const attempts = hgSessionId ? readExecutionAttempts(gateRoot, hgSessionId) : [];
  const character = extractCharacterRun(round, attempts);
  const storyteller = round.storyteller ?? {};
  const infra = extractStorytellerFinalize(attempts);
  const tokens = sumTokenUsage(attempts);
  return {
    run_id: run.run_id,
    fixture_id: run.fixture_id,
    repetition: run.repetition,
    hg_session_id: hgSessionId,
    hg_round_id: round.hg_round_id ?? null,
    report_path: run.report_path,
    fixture_validity: character.manifest_proof?.recent_scene_transcript ? 'VALID' : 'INVALID',
    character_structure: (character.committed === true || character.domain_commit_id) ? 'PASS' : 'FAIL',
    storyteller_bound: storyteller.bound === true,
    storyteller: {
      bound: storyteller.bound ?? false,
      package_id: storyteller.package_id ?? null,
      degradation_level: storyteller.degradation_level ?? null,
      assessment_evidence_id: storyteller.assessment_evidence_id ?? null,
      stage: storyteller.stage ?? null,
      reason: storyteller.reason ?? null,
    },
    orientation_finalize: infra.orientation_finalize,
    assessment_finalize: infra.assessment_finalize,
    librarian: infra.librarian,
    director_cue: extractDirectorCue(round),
    perception_proof: {
      opening_stimulus: run.forensic?.scene_stimulus ?? null,
      recent_scene_transcript: character.manifest_proof?.recent_scene_transcript ?? null,
      scene_setup: character.manifest_proof?.scene_setup ?? null,
      director_context: character.manifest_proof?.director_context ?? null,
    },
    character,
    token_usage: tokens,
    inference_count: attempts.length,
    instrumentation: run.forensic?.instrumentation ?? null,
  };
}

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    throw new Error('DEEPSEEK_API_KEY not set');
  }

  const executionSha = process.env.ISSUE136_EXECUTION_SHA
    ?? (() => {
      try {
        return fs.readFileSync(path.join(REPO_ROOT, '.git', 'HEAD'), 'utf8').includes('ref:')
          ? null
          : null;
      } catch {
        return null;
      }
    })();

  const guard = deriveIssue136SafetyGuard({
    repetitions: ISSUE136_FD_FOCUSED_REPETITIONS,
    includeSentinel: false,
  });
  const productionProof = proveProductionInferenceUnchanged();
  const gateRoot = path.join(
    REPO_ROOT,
    'data',
    'issue136_tier2_campaign',
    'live',
    `fd-focused-${new Date().toISOString().replace(/[:.]/g, '-')}`,
  );
  fs.mkdirSync(gateRoot, { recursive: true });

  const report = await runIssue136Tier2Campaign({
    mode: 'live',
    includeSentinel: false,
    fixtureFilter: ISSUE136_FD_FOCUSED_FIXTURE_ORDER,
    fixtureOrder: ISSUE136_FD_FOCUSED_FIXTURE_ORDER,
    repetitionsOverride: ISSUE136_FD_FOCUSED_REPETITIONS,
    campaignDataDir: gateRoot,
  });

  const runRecords = report.runs.map((run) => buildRunRecord(run, gateRoot));
  const totalInferences = report.limits?.inference_count
    ?? runRecords.reduce((sum, run) => sum + run.inference_count, 0);
  const tokenTotals = runRecords.reduce((acc, run) => ({
    prompt_tokens: acc.prompt_tokens + run.token_usage.prompt_tokens,
    completion_tokens: acc.completion_tokens + run.token_usage.completion_tokens,
    total_tokens: acc.total_tokens + run.token_usage.total_tokens,
  }), { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 });
  if (tokenTotals.total_tokens === 0) {
    for (const run of runRecords) {
      for (const call of run.instrumentation?.calls ?? []) {
        const usage = call.usage ?? {};
        tokenTotals.prompt_tokens += Number(usage.inputTokens ?? usage.prompt_tokens ?? 0);
        tokenTotals.completion_tokens += Number(usage.outputTokens ?? usage.completion_tokens ?? 0);
      }
    }
    tokenTotals.total_tokens = tokenTotals.prompt_tokens + tokenTotals.completion_tokens;
  }

  const envelope = {
    schema: 'issue136_fd_focused_live_report_v1',
    gate: 'FD_FOCUSED',
    execution_sha: executionSha,
    candidate_sha: ISSUE136_IMPLEMENTATION_SHA,
    fixture_encoding_revision: 'opening_pvr_turn_zero_v1',
    historical_g4_evidence_root: 'data/issue136_tier2_campaign/live/2026-09-07T03-40-45-925Z/',
    historical_g4_fd_semantics_invalid: true,
    approved_matrix: ISSUE136_FD_FOCUSED_REPETITIONS,
    safety_guard_recorded: guard,
    production_inference_proof: productionProof,
    provider_model_reasoning: {
      provider: 'deepseek-official',
      model: 'deepseek-v4-flash',
      reasoning: 'low',
    },
    evidence_root: gateRoot,
    total_live_runs: runRecords.length,
    total_live_inferences: totalInferences,
    token_usage: tokenTotals,
    campaign_state: report.campaign_state,
    limits: report.limits,
    runs: runRecords,
    raw_campaign_report_path: report.report_path,
  };

  const outPath = path.join(gateRoot, 'fd-focused-live-report.json');
  fs.writeFileSync(outPath, `${JSON.stringify(envelope, null, 2)}\n`, 'utf8');
  process.stdout.write(`${JSON.stringify({
    report_path: outPath,
    evidence_root: gateRoot,
    runs: runRecords.length,
    inferences: totalInferences,
    tokens: tokenTotals,
    campaign_state: report.campaign_state,
  }, null, 2)}\n`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
