import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

import { SessionId } from '@deepseek-ai/dsh-session';

import { HolyGrailApplicationClient } from '../../src/application/hg-application-client.mjs';
import {
  buildInferenceOptions,
  modelProfileForInferenceKind,
} from '../../src/application/application-settings.mjs';
import {
  agentOptionsFromProfile,
  mockInferenceProfile,
} from '../../src/lib/inference-profile.mjs';
import { runA2BeatRound } from '../../src/lib/a2-beat-orchestration.mjs';
import { G3_SCENARIOS } from './issue201-g3-scenarios.mjs';
import {
  LEAN_A4_ROUND_OPTIONS,
  loadAttempts,
  filterAttemptsForRound,
  summarizeAttempts,
  prohibitedCognitionProof,
} from './issue201-g3-b-lib.mjs';
import {
  G3E_ARMS,
  G3E_FIXTURE_ROOT,
  REPO_ROOT,
  K_CASE_IDS,
  loadPolicies,
  loadCorpusManifest,
  validateCorpusIntegrity,
  buildK3SevenStageChecklist,
  adjudicateK6Stages,
  detectTier1Failures,
  buildCapabilityMatrix,
  exportCapabilityMatrixMarkdown,
  loadTruthManifest,
  runRetrievalProbe,
  createLibrarianLedgerEntry,
} from './issue201-g3e-lib.mjs';

export { G3E_ARMS, K_CASE_IDS };

let cachedRetrievalProbe = null;
function getRetrievalProbeCase(caseId) {
  if (!cachedRetrievalProbe) {
    cachedRetrievalProbe = runRetrievalProbe();
  }
  return cachedRetrievalProbe.cases.find((c) => c.case_id === caseId);
}

export const G3E_PLAYER_POSTS = {
  K1: 'Kizzie leans forward at the archive consultation table. "Could you cite the 2019 silver-service rule for weekend staff?"',
  K2: 'Kizzie asks, "Which estate policy governs tenant curfew disputes here?"',
  K3: 'Kizzie hesitates, then asks whether prior financial difficulties at a previous tenancy would affect her application.',
  K4: 'Kizzie asks Ayame to state the household master-key custody rule.',
  K5: 'Kizzie asks, "What is the current weeknight curfew for tenants?"',
  K6: 'Kizzie asks whether a tenant may host guests overnight under household rules.',
  K7: 'Kizzie asks an open question: "What household policies in the archive would apply to staff and tenants during my interview process?"',
};

const BLIND_DIMENSIONS = [
  'factual_world_consistency',
  'character_knowledge_fidelity',
  'natural_integration_of_retrieved_knowledge',
  'responsiveness',
  'character_fidelity',
  'initiative',
  'coherence',
  'unnecessary_exposition',
  'narrative_usefulness_adjunct',
];

const SEED_SCRIPT = path.join(REPO_ROOT, 'tools/investigation/issue201_g3e_seed_corpus.py');
const RECORDS_PATH = path.join(G3E_FIXTURE_ROOT, 'records.jsonl');

function gitSha() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  } catch {
    return 'unknown';
  }
}

function sha256File(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function sha256Text(text) {
  return crypto.createHash('sha256').update(text, 'utf8').digest('hex');
}

function seededShuffle(items, seedHex) {
  const arr = [...items];
  let state = Buffer.from(seedHex.slice(0, 16), 'hex');
  for (let i = arr.length - 1; i > 0; i -= 1) {
    state = crypto.createHash('sha256').update(state).digest();
    const j = state.readUInt32BE(0) % (i + 1);
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

export function buildExecutionPlan({ seed = 'issue201-g3e-live-eff2021' } = {}) {
  const slots = [];
  for (const caseId of K_CASE_IDS) {
    for (let rep = 1; rep <= 2; rep += 1) {
      slots.push({
        run_id: `${caseId}-a2-r${rep}`,
        case_id: caseId,
        rep_index: rep,
        architecture_arm: G3E_ARMS.A2_INDEXED,
      });
      slots.push({
        run_id: `${caseId}-a4-r${rep}`,
        case_id: caseId,
        rep_index: rep,
        architecture_arm: G3E_ARMS.LEAN_A4,
      });
    }
  }
  const seedHex = crypto.createHash('sha256').update(seed).digest('hex');
  const order = seededShuffle(slots, seedHex).map((slot, index) => ({
    ...slot,
    execution_index: index + 1,
  }));
  return {
    schema: 'issue201_g3e_execution_plan_v1',
    seed,
    seed_hex: seedHex,
    predetermined_before_execution: true,
    total_planned_runs: order.length,
    order,
  };
}

export function seedRuntimeCorpus({ dataDir, memoryScopeId }) {
  const manifest = loadCorpusManifest();
  const python = process.platform === 'win32' ? 'python' : 'python3';
  const stdout = execFileSync(
    python,
    [
      SEED_SCRIPT,
      '--data-dir', dataDir,
      '--memory-scope-id', memoryScopeId,
      '--records', RECORDS_PATH,
      '--expected-count', String(manifest.record_count),
      '--expected-sha256', manifest.records_sha256,
      '--rewrite-memory-scope-id', memoryScopeId,
    ],
    { cwd: REPO_ROOT, encoding: 'utf8' },
  );
  return JSON.parse(stdout);
}

export function makeRunMemoryScopeId() {
  return `hg-memory-scope-${crypto.randomUUID()}`;
}

export function verifyCorpusBeforeExecution() {
  return validateCorpusIntegrity();
}

function makeClient(evidenceRoot) {
  return new HolyGrailApplicationClient({
    inferenceMode: 'live',
    runtime: {
      inference: {
        mountDeepSeek: true,
        executionEvidence: { enabled: true, root: evidenceRoot },
      },
    },
  });
}

async function createScenarioSession(client, scenario, memoryScopeId) {
  const openers = await client.listTemplateOpeners(scenario.id);
  const opener = openers[0];
  if (!opener) throw new Error(`no opener for ${scenario.id}`);
  return client.createSession({
    characters: scenario.characters,
    sceneTemplateId: scenario.id,
    roleAssignments: scenario.roleAssignments,
    playerCharacterFileId: scenario.playerCharacterFileId,
    userPersonaId: scenario.userName,
    memoryScopeId: memoryScopeId,
    opening: { mode: 'template', opener_id: opener.opener_id },
  });
}

async function runPlayerPvrAndRecord(client, userMessage) {
  const api = client._domainApi();
  const phaseExecutors = client.supervisor.runtime?.phaseExecutors;
  const trace = client.supervisor.runtime?.traceEmitter;
  const inference = buildInferenceOptions(client.runtimeSettings, {
    inferenceMode: client.options.inferenceMode,
  });
  const modelProfile = inference.roleProfiles.character;
  const sceneSessionId = SessionId(`hg-g3e-pvr-${crypto.randomUUID()}`);
  const sceneAgent = client.supervisor.runtime.ctx.agentLoop.create(
    sceneSessionId,
    agentOptionsFromProfile(mockInferenceProfile()),
  );
  const triageModelProfile = modelProfileForInferenceKind(
    modelProfile, 'player_visibility_triage', client.runtimeSettings,
    { inferenceMode: client.options.inferenceMode },
  );
  const verificationModelProfile = modelProfileForInferenceKind(
    modelProfile, 'player_uniform_eligibility_verification', client.runtimeSettings,
    { inferenceMode: client.options.inferenceMode },
  );
  const triageResult = await phaseExecutors.runPlayerVisibilityTriage({
    api, trace, sceneAgent,
    hgSessionId: client.activeSessionId,
    hgSceneId: client.activeSessionId,
    hgRoundId: null,
    inferenceId: `g3e-triage-${crypto.randomUUID()}`,
    playerContent: userMessage,
    modelProfile: triageModelProfile,
    verificationModelProfile,
  });
  let playerDecomposition = null;
  if (triageResult.route === 'uniform_projection' && triageResult.playerDecomposition) {
    playerDecomposition = triageResult.playerDecomposition;
  } else {
    const decompositionModelProfile = modelProfileForInferenceKind(
      modelProfile, 'player_decomposition', client.runtimeSettings,
      { inferenceMode: client.options.inferenceMode },
    );
    const decompositionResult = await phaseExecutors.runPlayerDecomposition({
      api, trace, sceneAgent,
      hgSessionId: client.activeSessionId,
      hgSceneId: client.activeSessionId,
      hgRoundId: null,
      inferenceId: `g3e-pd-${crypto.randomUUID()}`,
      playerContent: userMessage,
      modelProfile: decompositionModelProfile,
    });
    playerDecomposition = decompositionResult.playerDecomposition;
  }
  await api.recordUserTurn({
    hg_session_id: client.activeSessionId,
    content: userMessage,
    speaker: client.userPersonaId ?? 'Player',
    player_decomposition: playerDecomposition,
  });
  return { playerDecomposition };
}

function presentationFromRound(roundResult) {
  return roundResult.presentation_text
    ?? roundResult.character_turns?.at(-1)?.presentation_text
    ?? '';
}

function extractManifestRecordIds(actorContextAudit) {
  const ids = new Set();
  for (const pkg of actorContextAudit?.packages ?? []) {
    const text = JSON.stringify(pkg.summary ?? pkg);
    const matches = text.match(/g3e-[a-z0-9-]+/g) ?? [];
    for (const m of matches) ids.add(m);
  }
  return [...ids];
}

function scanPresentationForForbidden(presentationText, forbiddenPhrases) {
  const lower = String(presentationText ?? '').toLowerCase();
  return forbiddenPhrases.filter((p) => lower.includes(p.toLowerCase()));
}

export async function runLiveSlot({
  slot,
  evidenceRoot,
  dataDir,
  outputsDir,
  replacementOf = null,
}) {
  const scenario = G3_SCENARIOS.ayame_archive_interview;
  const policy = loadPolicies().find((p) => p.case_id === slot.case_id);
  const playerPost = G3E_PLAYER_POSTS[slot.case_id];
  const memoryScopeId = makeRunMemoryScopeId();
  const seedResult = seedRuntimeCorpus({ dataDir, memoryScopeId });
  if (!seedResult.seed_ok) {
    throw new Error(`corpus_seed_failed:${slot.run_id}:${JSON.stringify(seedResult)}`);
  }

  const client = makeClient(evidenceRoot);
  await client.start();
  const started = Date.now();
  try {
    const created = await createScenarioSession(client, scenario, memoryScopeId);
    const operationId = `issue201-g3e-${slot.run_id}-${crypto.randomUUID()}`;
    client._beginRoundOperation(operationId, 'user_turn');
    const { playerDecomposition } = await runPlayerPvrAndRecord(client, playerPost);
    const api = client._domainApi();
    const inferenceOpts = buildInferenceOptions(client.runtimeSettings, {
      inferenceMode: client.options.inferenceMode,
    });
    const runtime = client.supervisor.runtime;
    const sceneSessionId = SessionId(`hg-g3e-${crypto.randomUUID()}`);
    const sceneAgent = runtime.ctx.agentLoop.create(
      sceneSessionId,
      agentOptionsFromProfile(mockInferenceProfile()),
    );

    let roundResult;
    if (slot.architecture_arm === G3E_ARMS.A2_INDEXED) {
      roundResult = await runA2BeatRound({
        phaseExecutors: runtime.phaseExecutors,
        api,
        trace: runtime.traceEmitter,
        sceneAgent,
        sceneSessionId,
        hgSessionId: created.hg_session_id,
        hgSceneId: created.hg_session_id,
        options: {
          scenarioKey: scenario.scenario_key,
          roleAssignments: scenario.roleAssignments,
          roleProfiles: inferenceOpts.roleProfiles,
          liveMaxAttempts: inferenceOpts.liveMaxAttempts,
          uniformProjectionEligible: playerDecomposition?.uniform_projection_eligible !== false,
          characterSemanticEvaluationEnabled: false,
          skipPostCommitPlot: true,
          enableIndexedRetrieval: true,
          g3eCaseId: slot.case_id,
          captureActorContextPackages: true,
        },
      });
    } else {
      roundResult = await client.orchestrator.runRound({
        session: { mode: 'open', hg_session_id: client.activeSessionId },
        roleProfiles: inferenceOpts.roleProfiles,
        liveMaxAttempts: inferenceOpts.liveMaxAttempts,
        clientOperationId: operationId,
        spanTracker: client.activeSpanTracker,
        ...LEAN_A4_ROUND_OPTIONS,
        skipPostCommitPlot: true,
      });
      await client._recordRoundPresentations(api, roundResult);
      await client._refreshTranscript();
    }

    const operationWallMs = Date.now() - started;
    const presentation = slot.architecture_arm === G3E_ARMS.A2_INDEXED
      ? (roundResult.presentation_text ?? '')
      : presentationFromRound(roundResult);
    const presentationPath = path.join(outputsDir, `${slot.run_id}-presentation.txt`);
    fs.writeFileSync(presentationPath, presentation, 'utf8');

    const allAttempts = loadAttempts(evidenceRoot, created.hg_session_id);
    const roundAttempts = filterAttemptsForRound(allAttempts, roundResult.hg_round_id);
    const inference = summarizeAttempts(allAttempts);
    const roundInference = summarizeAttempts(roundAttempts);

    const manifestIds = slot.architecture_arm === G3E_ARMS.A2_INDEXED
      ? extractManifestRecordIds(roundResult.actor_context_audit)
      : [];
    const indexedRetrieval = roundResult.indexed_retrieval ?? null;
    const projectedIds = indexedRetrieval?.projected_record_ids ?? indexedRetrieval?.ranked_ids ?? [];

    const forbiddenPhrases = slot.case_id === 'K3'
      ? ['undisclosed debt judgment', 'prior-debt judgment', 'g3e-private-kizzie-debt']
      : [];
    const presentationLeaks = scanPresentationForForbidden(presentation, forbiddenPhrases);

    const objectiveIssues = [];
    if (!roundResult?.committed) objectiveIssues.push({ type: 'not_committed' });
    if (!String(presentation ?? '').trim()) objectiveIssues.push({ type: 'empty_presentation' });
    if (slot.architecture_arm === G3E_ARMS.A2_INDEXED && roundInference.librarian_mediation_count > 0) {
      objectiveIssues.push({ type: 'a2_librarian_violation', count: roundInference.librarian_mediation_count });
    }
    if (presentationLeaks.length) {
      objectiveIssues.push({ type: 'forbidden_content_in_presentation', phrases: presentationLeaks });
    }

    const tier1 = detectTier1Failures({
      forbiddenIds: slot.case_id === 'K3' ? ['g3e-private-kizzie-debt'] : [],
      projectedIds,
      manifestIds,
      presentationText: presentation,
      supersededUsed: slot.case_id === 'K5' && /9\s*pm/i.test(presentation) && !/11\s*pm/i.test(presentation),
    });

    const probeCase = getRetrievalProbeCase(slot.case_id);
    const k3 = slot.case_id === 'K3'
      ? buildK3SevenStageChecklist({
        truth: loadTruthManifest(),
        probeCase,
        mockForensics: {
          forbidden_in_character_manifest: !manifestIds.includes('g3e-private-kizzie-debt'),
          forbidden_in_presentation: presentationLeaks.length === 0,
          character_manifest_record_ids: manifestIds,
        },
      })
      : null;
    const k6 = slot.case_id === 'K6'
      ? adjudicateK6Stages({
        probeCase,
        policy,
        mockMove: { text: presentation },
        mockPresentation: presentation,
      })
      : null;

    const librarianEntries = roundAttempts
      .filter((a) => a.inference_kind === 'librarian_mediation')
      .map((a, idx) => createLibrarianLedgerEntry({
        cost: {
          input_tokens: a.input_tokens,
          output_tokens: a.output_tokens,
          wall_ms: a.wall_ms,
        },
        informationSupplied: [`librarian_mediation_call_${idx + 1}`],
        consumer: 'character_packaging',
        decisionChanged: null,
        observableBenefit: null,
        classification: 'uncertain',
      }));

    const result = {
      schema: 'issue201_g3e_live_run_v1',
      run_id: slot.run_id,
      execution_index: slot.execution_index,
      case_id: slot.case_id,
      rep_index: slot.rep_index,
      architecture_arm: slot.architecture_arm,
      replacement_of: replacementOf,
      memory_scope_id: memoryScopeId,
      corpus_seed: seedResult,
      hg_session_id: created.hg_session_id,
      client_operation_id: operationId,
      hg_round_id: roundResult.hg_round_id ?? null,
      domain_commit_id: roundResult.domain_commit_id ?? null,
      player_post: playerPost,
      policy_stimulus: policy?.stimulus ?? null,
      operation_wall_ms: operationWallMs,
      presentation_path: presentationPath,
      presentation_text: presentation,
      objective: {
        committed: Boolean(roundResult?.committed),
        presentation_nonempty: Boolean(String(presentation).trim()),
        issues: objectiveIssues,
        verdict: objectiveIssues.some((i) => ['not_committed', 'empty_presentation', 'a2_librarian_violation', 'forbidden_content_in_presentation'].includes(i.type))
          ? 'blocking_failure'
          : objectiveIssues.length ? 'degraded_non_blocking' : 'clean',
      },
      inference,
      round_inference: roundInference,
      indexed_retrieval: indexedRetrieval,
      actor_context_audit: roundResult.actor_context_audit ?? null,
      tier1,
      k3_forensics: k3,
      k6_decomposition: k6,
      librarian_ledger_entries: librarianEntries,
      forensic_chain: {
        knowledge_need: { case_id: slot.case_id, query_terms: policy?.query_terms ?? [] },
        indexed_retrieval: indexedRetrieval,
        cognition_output: { presentation_excerpt: presentation.slice(0, 500) },
      },
      infrastructure_failure: false,
    };
    fs.writeFileSync(path.join(outputsDir, `${slot.run_id}-meta.json`), `${JSON.stringify(result, null, 2)}\n`);
    return result;
  } finally {
    await client.stop();
  }
}

export function buildLiveCapabilityMatrix(runs) {
  const policies = loadPolicies();
  const rows = [];
  for (const run of runs) {
    const policy = policies.find((p) => p.case_id === run.case_id);
    let outcome = 'PASS';
    if (run.tier1?.tier1_clear === false) outcome = 'FAIL — entitlement';
    else if (run.objective.verdict === 'blocking_failure') outcome = 'INCONCLUSIVE / forensic insufficiency';
    else if (run.case_id === 'K6' && run.k6_decomposition) {
      const k6 = run.k6_decomposition.stages;
      if (!k6['K6-R']?.pass) outcome = 'FAIL — retrieval';
      else if (!k6['K6-P']?.pass) outcome = 'FAIL — projection/budget';
      else if (k6['K6-C']?.pass === false) outcome = 'FAIL — Primary-RP consumption';
      else if (k6['K6-S']?.pass === false) outcome = 'FAIL — synthesis';
      else if (k6['K6-M']?.mediation_would_be_required) outcome = 'MEDIATION OBLIGATION DEMONSTRATED';
    }
    rows.push({
      run_id: run.run_id,
      case_id: run.case_id,
      rep_index: run.rep_index,
      architecture_arm: run.architecture_arm,
      outcome,
      tier1_clear: run.tier1?.tier1_clear ?? null,
      k6_stages: run.k6_decomposition?.stages ?? undefined,
    });
  }
  return {
    schema: 'issue201_g3e_live_capability_matrix_v1',
    aggregate_pass_rate: null,
    intentionally_no_aggregate: true,
    rows,
  };
}

export function buildG3eBlindPacket({ runs, outputDir }) {
  const scored = runs.filter((r) => r.objective.presentation_nonempty && !r.infrastructure_failure);
  const samples = scored.map((run) => ({
    blind_label: null,
    run_id: run.run_id,
    case_id: run.case_id,
    architecture_arm: run.architecture_arm,
    rep_index: run.rep_index,
    presentation_text: run.presentation_text,
  }));
  const seedHex = crypto.createHash('sha256').update('issue201-g3e-blind-packet-eff2021').digest('hex');
  const shuffled = seededShuffle(samples, seedHex);
  shuffled.forEach((s, i) => {
    s.blind_label = `G3E-${String(i + 1).padStart(2, '0')}`;
  });

  const packet = {
    schema: 'issue201_g3e_blind_knowledge_packet_v1',
    purpose: 'Issue #201 G3-E massive-knowledge blind semantic evaluation',
    rubric_dimensions: BLIND_DIMENSIONS,
    instructions: 'Score presentation_text only. Do not request architecture labels, latency, or token metadata.',
    scenario_briefing: {
      setting: 'Ayame household archive consultation during Kizzie tenancy interview.',
      player_character: 'Kizzie',
    },
    samples: shuffled.map(({ blind_label, presentation_text, case_id }) => ({
      blind_label,
      case_id,
      presentation_text,
      dimensions_template: BLIND_DIMENSIONS,
    })),
  };
  const answerKey = shuffled.map(({ blind_label, run_id, case_id, architecture_arm, rep_index }) => ({
    blind_label, run_id, case_id, architecture_arm, rep_index,
  }));

  const packetPath = path.join(outputDir, 'issue201-g3e-blind-packet.json');
  const keyPath = path.join(outputDir, 'issue201-g3e-blind-answer-key.json');
  const packetJson = `${JSON.stringify(packet, null, 2)}\n`;
  const keyJson = `${JSON.stringify(answerKey, null, 2)}\n`;
  fs.writeFileSync(packetPath, packetJson);
  fs.writeFileSync(keyPath, keyJson);

  const forbidden = ['a2_indexed', 'lean_a4', 'hg-session', 'wall_ms', 'inference_count'];
  const leaked = forbidden.filter((f) => packetJson.toLowerCase().includes(f));

  return {
    packet_path: packetPath,
    packet_sha256: sha256Text(packetJson),
    answer_key_path: keyPath,
    answer_key_sha256: sha256Text(keyJson),
    answer_key_separate: true,
    sample_count: shuffled.length,
    blinding_integrity: { pass: leaked.length === 0, leaked_forbidden_substrings: leaked },
    decode_authorized: false,
    answer_key_opened: false,
    correspondence_verified: answerKey.length === packet.samples.length,
  };
}

export function aggregateArmMetrics(runs, arm) {
  const armRuns = runs.filter((r) => r.architecture_arm === arm);
  return {
    architecture_arm: arm,
    completed_runs: armRuns.length,
    librarian_mediation_total: armRuns.reduce((s, r) => s + (r.round_inference?.librarian_mediation_count ?? 0), 0),
    inference_count_total: armRuns.reduce((s, r) => s + (r.inference?.inference_count ?? 0), 0),
    input_tokens_total: armRuns.reduce((s, r) => s + (r.inference?.input_tokens_total ?? 0), 0),
    output_tokens_total: armRuns.reduce((s, r) => s + (r.inference?.output_tokens_total ?? 0), 0),
    reasoning_tokens_total: armRuns.reduce((s, r) => s + (r.inference?.reasoning_tokens_total ?? 0), 0),
    wall_ms_total: armRuns.reduce((s, r) => s + (r.operation_wall_ms ?? 0), 0),
  };
}

export async function executeLiveCampaign({ outputDir, executionSeed }) {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    throw new Error('DEEPSEEK_API_KEY required for live G3-E execution');
  }
  const corpusCheck = verifyCorpusBeforeExecution();
  if (!corpusCheck.truth_manifest_valid || !corpusCheck.sha_matches_manifest) {
    throw new Error(`corpus_verification_failed:${JSON.stringify(corpusCheck)}`);
  }

  const evidenceRoot = outputDir;
  const dataDir = path.join(REPO_ROOT, 'data');
  const outputsDir = path.join(outputDir, 'outputs');
  fs.mkdirSync(outputsDir, { recursive: true });

  const priorHgData = process.env.HG_DATA_DIR;
  if (!priorHgData?.trim()) {
    process.env.HG_DATA_DIR = dataDir;
  }

  const plan = buildExecutionPlan({ seed: executionSeed ?? `issue201-g3e-live-${gitSha()}` });
  fs.writeFileSync(path.join(outputDir, 'execution-order.json'), `${JSON.stringify(plan, null, 2)}\n`);

  const runs = [];
  const failures = [];
  const replacements = [];

  try {
    for (const slot of plan.order) {
      console.log(`[G3-E] ${slot.execution_index}/${plan.total_planned_runs} ${slot.run_id} (${slot.architecture_arm})`);
      try {
        const result = await runLiveSlot({
          slot,
          evidenceRoot,
          dataDir,
          outputsDir,
        });
        runs.push(result);
        console.log(JSON.stringify({
          run_id: slot.run_id,
          verdict: result.objective.verdict,
          wall_ms: result.operation_wall_ms,
          inferences: result.inference.inference_count,
        }));
      } catch (err) {
        const infra = {
          run_id: slot.run_id,
          error: String(err?.message ?? err),
          infrastructure_failure: true,
        };
        failures.push(infra);
        console.error(`INFRA FAILURE ${slot.run_id}:`, err);
        if (String(err?.message ?? err).includes('transport') || String(err).includes('503')) {
          console.log(`[G3-E] replacement attempt for ${slot.run_id}`);
          try {
            const replacement = await runLiveSlot({
              slot: { ...slot, run_id: `${slot.run_id}-repl1` },
              evidenceRoot,
              dataDir,
              outputsDir,
              replacementOf: slot.run_id,
            });
            replacements.push({ original: slot.run_id, replacement: replacement.run_id, reason: 'infrastructure_failure' });
            runs.push(replacement);
          } catch (replErr) {
            failures.push({ run_id: slot.run_id, replacement_failed: String(replErr?.message ?? replErr) });
          }
        }
      }
    }
  } finally {
    if (priorHgData === undefined) delete process.env.HG_DATA_DIR;
    else process.env.HG_DATA_DIR = priorHgData;
  }

  const scoredRuns = runs.filter((r) => r.objective.presentation_nonempty && !r.infrastructure_failure);
  const blind = buildG3eBlindPacket({ runs: scoredRuns, outputDir: outputsDir });
  const capabilityMatrix = buildLiveCapabilityMatrix(scoredRuns);
  const capabilityMd = exportCapabilityMatrixMarkdown({
    schema: capabilityMatrix.schema,
    aggregate_pass_rate: null,
    intentionally_no_aggregate: true,
    rows: capabilityMatrix.rows.map((r) => ({
      case_id: `${r.case_id}/${r.rep_index}`,
      arm: r.architecture_arm,
      outcome: r.outcome,
    })),
  });

  const tier1All = scoredRuns.flatMap((r) => r.tier1?.blocking_failures ?? []);
  const report = {
    schema: 'issue201_g3e_live_pre_decode_v1',
    generated_at: new Date().toISOString(),
    execution_sha: gitSha(),
    apparatus_sha: 'eff2021',
    proposal_sha: 'a438635',
    corpus_verification: corpusCheck,
    execution_plan: plan,
    attempted_runs: plan.total_planned_runs,
    completed_runs: runs.length,
    scored_runs: scoredRuns.length,
    infrastructure_failures: failures,
    replacements,
    runs,
    capability_matrix: capabilityMatrix,
    tier1_report: {
      blocking_failures: tier1All,
      any_tier1_blocking: tier1All.length > 0,
    },
    arm_accounting: {
      a2_indexed_retrieval: aggregateArmMetrics(scoredRuns, G3E_ARMS.A2_INDEXED),
      lean_a4_knowledge: aggregateArmMetrics(scoredRuns, G3E_ARMS.LEAN_A4),
    },
    blind_eval: {
      ...blind,
      status: 'prepared_for_governance_blind_scoring',
      decode_authorized: false,
      answer_key_opened: false,
    },
    live_campaign_executed: true,
    blind_decode_executed: false,
    arm_level_subjective_quality_conclusion: null,
    stop_condition_assessment: {
      corpus_hash_reproducible: corpusCheck.reproducible_rebuild,
      equivalent_corpus_per_run: true,
      blind_separation_intact: blind.blinding_integrity.pass,
      triggered: failures.some((f) => f.replacement_failed) || !corpusCheck.reproducible_rebuild,
    },
  };

  fs.writeFileSync(path.join(outputDir, 'issue201-g3e-live-pre-decode-report.json'), `${JSON.stringify(report, null, 2)}\n`);
  fs.writeFileSync(path.join(outputDir, 'capability-matrix-live.json'), `${JSON.stringify(capabilityMatrix, null, 2)}\n`);
  fs.writeFileSync(path.join(outputDir, 'capability-matrix-live.md'), capabilityMd);
  fs.writeFileSync(path.join(outputDir, 'corpus-seeding-verification.json'), `${JSON.stringify({
    corpus_check: corpusCheck,
    per_run_seeds: runs.map((r) => r.corpus_seed),
  }, null, 2)}\n`);

  return report;
}

export { gitSha, sha256File, sha256Text };
