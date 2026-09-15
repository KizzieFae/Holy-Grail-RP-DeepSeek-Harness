/**
 * Issue #201 Package D — D-10 post-commit Storyteller vs Plot longitudinal test.
 * Control: preamble OFF, post-commit issue-pressure ON.
 * Ablated: preamble OFF, post-commit issue-pressure OFF (skipLibrarianProposalGeneration).
 */
import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { SessionId } from '@deepseek-ai/dsh-session';

import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import {
  buildInferenceOptions,
  modelProfileForInferenceKind,
} from '../src/application/application-settings.mjs';
import {
  agentOptionsFromProfile,
  mockInferenceProfile,
} from '../src/lib/inference-profile.mjs';
import { defaultDataDir, defaultSessionsDir } from '../src/lib/runtime-config.mjs';
import {
  buildPolicyManifest,
  loadPolicy,
  selectPlayerStimulus,
} from './lib/issue201-d10-player-policy.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');
const CONTROL_SHA = 'c751ea666f0cae6524698005aa5859721c2e9738';
const DESIGN_SHA = 'd13f2a0';

const SCENARIOS = {
  arkham_stress: {
    id: 'arkham_asylum_mess_hall_arena',
    characters: ['harley_quinn', 'poison_ivy', 'magpie'],
    roleAssignments: {
      harley_quinn: 'instigator',
      poison_ivy: 'instigator_accomplice',
      magpie: 'new_arrival',
    },
    playerCharacterFileId: 'magpie',
    userName: 'Magpie',
    openerPreference: 'mess_hall_magpie',
    policyId: 'arkham_d10_policy_v1',
    sequencesPerArm: 2,
  },
  ayame_controlled: {
    id: 'ayame_household_entry_evaluation',
    characters: ['ayame', 'kizzie'],
    roleAssignments: { ayame: 'host', kizzie: 'applicant' },
    playerCharacterFileId: 'kizzie',
    userName: 'Kizzie',
    openerPreference: null,
    policyId: 'ayame_d10_policy_v1',
    sequencesPerArm: 1,
  },
};

const ARMS = [
  {
    arm_id: 'control',
    label: 'Post-commit Storyteller issue-pressure ON',
    round_options: { skipStorytellerCognition: true },
  },
  {
    arm_id: 'ablated',
    label: 'Post-commit Storyteller issue-pressure OFF',
    round_options: {
      skipStorytellerCognition: true,
      skipLibrarianProposalGeneration: true,
    },
  },
];

const PREAMBLE_STORYTELLER_KINDS = new Set([
  'storyteller_orientation',
  'storyteller_assessment',
]);
const POST_COMMIT_STORYTELLER_KINDS = new Set([
  'storyteller_post_commit_issue_pressure',
  'storyteller_post_commit_issue_pressure_contract_correction',
]);

function gitSha() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  } catch {
    return null;
  }
}

function kindCount(kinds, name) {
  return kinds.find((k) => k.inference_kind === name)?.count ?? 0;
}

function summarizeInferenceKinds(kinds) {
  const list = kinds ?? [];
  const storytellerKinds = list.filter((k) => String(k.inference_kind).startsWith('storyteller'));
  const plotKinds = list.filter((k) => String(k.inference_kind).startsWith('plot_cognition'));
  let preambleSt = 0;
  let postCommitSt = 0;
  for (const k of storytellerKinds) {
    if (PREAMBLE_STORYTELLER_KINDS.has(k.inference_kind)) preambleSt += k.count;
    if (POST_COMMIT_STORYTELLER_KINDS.has(k.inference_kind)) postCommitSt += k.count;
  }
  return {
    inference_count: list.reduce((s, k) => s + k.count, 0),
    librarian_mediation_count: kindCount(list, 'librarian_mediation'),
    character_orientation_count: kindCount(list, 'character_orientation'),
    director_semantic_qa_count: kindCount(list, 'director_semantic_qa'),
    director_decision_count: kindCount(list, 'director_decision'),
    narrator_presentation_count: kindCount(list, 'narrator_presentation'),
    storyteller_inference_count: storytellerKinds.reduce((s, k) => s + k.count, 0),
    storyteller_preamble_inference_count: preambleSt,
    storyteller_post_commit_inference_count: postCommitSt,
    plot_inference_count: plotKinds.reduce((s, k) => s + k.count, 0),
    kinds: list,
  };
}

function loadAttemptsForOperation(evidenceRoot, sessionId, operationId) {
  const indexPath = path.join(evidenceRoot, sessionId, 'index.json');
  if (!fs.existsSync(indexPath)) return [];
  const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
  const rows = [];
  for (const attemptId of index.attempt_ids ?? []) {
    const attemptPath = path.join(evidenceRoot, sessionId, 'attempts', `${attemptId}.json`);
    if (!fs.existsSync(attemptPath)) continue;
    const attempt = JSON.parse(fs.readFileSync(attemptPath, 'utf8'));
    const op = attempt.correlation?.operation_id
      ?? attempt.associations?.operation_id
      ?? attempt.decision?.operation_id
      ?? null;
    if (String(op) !== String(operationId)) continue;
    const usage = attempt.response?.usage ?? {};
    const timing = attempt.inference_health?.timing ?? attempt.timing ?? {};
    rows.push({
      evidence_id: attempt.evidence_id ?? attemptId,
      inference_kind: attempt.correlation?.inference_kind ?? null,
      attempt_index: attempt.correlation?.attempt_index ?? 0,
      wall_ms: timing.inference_wall_clock_ms ?? timing.wall_ms ?? timing.duration_ms ?? null,
      input_tokens: usage.inputTokens ?? usage.input_tokens ?? null,
      output_tokens: usage.outputTokens ?? usage.output_tokens ?? null,
      reasoning_tokens: usage.reasoningTokens ?? usage.reasoning_tokens ?? null,
      domain_commit_id: attempt.associations?.domain_commit_id
        ?? attempt.correlation?.domain_commit_id
        ?? null,
      decision: attempt.decision ?? null,
      response_text: attempt.response?.text ?? attempt.response?.content ?? null,
    });
  }
  return rows;
}

function mergeTurnInference(turns) {
  const kindMap = new Map();
  for (const t of turns) {
    for (const k of t.inference.kinds ?? []) {
      const prev = kindMap.get(k.inference_kind) ?? { count: 0, wall_ms_total: 0 };
      kindMap.set(k.inference_kind, {
        inference_kind: k.inference_kind,
        count: prev.count + k.count,
        wall_ms_total: prev.wall_ms_total + (k.wall_ms_total ?? 0),
      });
    }
  }
  const merged = summarizeInferenceKinds([...kindMap.values()]);
  return {
    ...merged,
    wall_ms_total: turns.reduce((s, row) => s + (row.inference.wall_ms_total ?? 0), 0),
    input_tokens_total: turns.reduce((s, row) => s + (row.inference.input_tokens_total ?? 0), 0),
    output_tokens_total: turns.reduce((s, row) => s + (row.inference.output_tokens_total ?? 0), 0),
    reasoning_tokens_total: turns.reduce((s, row) => s + (row.inference.reasoning_tokens_total ?? 0), 0),
    retry_count: turns.reduce((s, row) => s + (row.inference.retry_count ?? 0), 0),
  };
}

function summarizeAttempts(attempts) {
  const byKind = {};
  for (const row of attempts) {
    const key = row.inference_kind ?? 'unknown';
    if (!byKind[key]) byKind[key] = [];
    byKind[key].push(row);
  }
  const kinds = Object.entries(byKind)
    .filter(([k]) => k !== 'unknown' && k !== null)
    .map(([kind, rows]) => ({
      inference_kind: kind,
      count: rows.length,
      wall_ms_total: rows.reduce((s, r) => s + (r.wall_ms ?? 0), 0),
    }));
  return {
    ...summarizeInferenceKinds(kinds),
    wall_ms_total: attempts.reduce((s, r) => s + (r.wall_ms ?? 0), 0),
    input_tokens_total: attempts.reduce((s, r) => s + (r.input_tokens ?? 0), 0),
    output_tokens_total: attempts.reduce((s, r) => s + (r.output_tokens ?? 0), 0),
    reasoning_tokens_total: attempts.reduce((s, r) => s + (r.reasoning_tokens ?? 0), 0),
    retry_count: attempts.filter((r) => (r.attempt_index ?? 0) > 0).length,
  };
}

function tokenize(text) {
  return new Set(String(text ?? '').toLowerCase().match(/\b[a-z]{3,}\b/g) ?? []);
}

function tokenJaccard(a, b) {
  const A = tokenize(a);
  const B = tokenize(b);
  if (!A.size && !B.size) return 0;
  let inter = 0;
  for (const t of A) if (B.has(t)) inter += 1;
  return inter / (A.size + B.size - inter);
}

function readJsonIfExists(filePath) {
  if (!fs.existsSync(filePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return null;
  }
}

function extractContinuityForensics(hgSessionId, sessionsDir) {
  const sessionPath = path.join(sessionsDir, `${hgSessionId}.json`);
  const session = readJsonIfExists(sessionPath);
  if (!session) return { session_found: false };
  const manager = session.continuity_manager ?? session.manager ?? session;
  const overlays = manager.issue_pressure_semantic_overlays ?? {};
  const issues = manager.issues ?? manager.continuity_issues ?? {};
  const activeIssues = Object.entries(issues)
    .filter(([, v]) => {
      const state = typeof v === 'object' ? (v.state ?? v.status) : null;
      return state === 'ACTIVE' || state === 'ESCALATING';
    })
    .map(([id]) => id);
  return {
    session_found: true,
    continuity_version: manager.continuity_version ?? session.continuity_version ?? null,
    issue_pressure_semantic_overlays: overlays,
    active_issue_ids: activeIssues,
    plot_cognition_scope_id: session.plot_cognition_scope_id
      ?? manager.plot_cognition_scope_id
      ?? null,
  };
}

function extractPlotForensics(plotScopeId, sessionsDir) {
  if (!plotScopeId) return { overlay_found: false };
  const safe = String(plotScopeId).replace(/[/\\]/g, '_');
  const overlayPath = path.join(sessionsDir, '_plot_cognition_overlay', `${safe}.json`);
  const payload = readJsonIfExists(overlayPath);
  if (!payload) return { overlay_found: false, overlay_path: overlayPath };
  const pressures = payload.unresolved_narrative_pressures
    ?? payload.pressures
    ?? {};
  return {
    overlay_found: true,
    overlay_path: overlayPath,
    overlay_revision: payload.revision ?? null,
    unresolved_narrative_pressures: pressures,
    plot_goals: payload.plot_goals ?? payload.goals ?? {},
    global_plot_frame: payload.global_plot_frame ?? null,
  };
}

function comparePressures(overlays, plotPressures) {
  const pairs = [];
  const overlayEntries = Object.entries(overlays ?? {});
  const plotList = Object.values(plotPressures ?? {}).filter((p) => p && typeof p === 'object');
  for (const [issueRef, overlay] of overlayEntries) {
    const stText = [
      overlay?.semantic_unmet_condition,
      overlay?.stakes_summary,
    ].filter(Boolean).join(' ');
    let best = { plot_pressure_id: null, jaccard: 0, issue_ref_match: false };
    for (const plotP of plotList) {
      const plotText = plotP.pressure_text ?? plotP.text ?? '';
      const refs = plotP.continuity_issue_refs ?? plotP.issue_refs ?? [];
      const issueMatch = refs.includes(issueRef) || refs.includes(String(issueRef));
      const jac = tokenJaccard(stText, plotText);
      if (jac > best.jaccard || (issueMatch && !best.issue_ref_match)) {
        best = {
          plot_pressure_id: plotP.pressure_id ?? plotP.id ?? null,
          jaccard: jac,
          issue_ref_match: issueMatch,
        };
      }
    }
    let structural_class = 'unique_st';
    if (best.issue_ref_match && best.jaccard >= 0.55) structural_class = 'equivalent';
    else if (best.issue_ref_match || best.jaccard >= 0.35) structural_class = 'overlapping';
    else if (best.jaccard >= 0.35 && best.jaccard < 0.55) structural_class = 'overlapping';
    pairs.push({
      issue_ref: issueRef,
      storyteller_overlay: overlay,
      best_plot_match: best,
      structural_class,
      jaccard_screening_only: true,
    });
  }
  for (const plotP of plotList) {
    const plotId = plotP.pressure_id ?? plotP.id;
    const matched = pairs.some((p) => p.best_plot_match.plot_pressure_id === plotId);
    if (!matched) {
      pairs.push({
        issue_ref: null,
        plot_pressure_id: plotId,
        plot_pressure: plotP,
        structural_class: 'unique_plot',
      });
    }
  }
  return pairs;
}

function extractPostCommitForensics(attempts, roundOptions) {
  const postCommitAttempts = attempts.filter((a) => POST_COMMIT_STORYTELLER_KINDS.has(a.inference_kind));
  const hookSkipped = roundOptions.skipLibrarianProposalGeneration === true;
  const ranInference = postCommitAttempts.some((a) => a.inference_kind === 'storyteller_post_commit_issue_pressure');
  const eligibilitySkipped = postCommitAttempts.some((a) => {
    const d = a.decision?.post_commit_semantic ?? a.decision?.librarian_proposal ?? {};
    return d.eligibility_outcome || d.proposal_generation_skip_reason;
  });
  return {
    post_commit_hook_skipped: hookSkipped,
    storyteller_post_commit_inference_ran: ranInference,
    post_commit_attempt_count: postCommitAttempts.length,
    eligibility_skipped_signal: eligibilitySkipped,
    post_commit_attempts: postCommitAttempts.map((a) => ({
      evidence_id: a.evidence_id,
      inference_kind: a.inference_kind,
      domain_commit_id: a.domain_commit_id,
      decision_summary: a.decision?.post_commit_semantic
        ?? a.decision?.librarian_proposal
        ?? null,
    })),
  };
}

function runPreflight() {
  const contractPath = path.join(REPO_ROOT, 'v2', 'domain_api', 'librarian_proposal_contract.py');
  const contractText = fs.readFileSync(contractPath, 'utf8');
  const kindsMatch = contractText.match(/S4A_ACTIVE_PROPOSAL_KINDS[\s\S]*?frozenset\(\s*\{([^}]+)\}/);
  const activeKinds = kindsMatch
    ? kindsMatch[1].split(',').map((s) => s.replace(/["'\s]/g, '')).filter(Boolean)
    : [];
  const servicePath = path.join(
    REPO_ROOT, 'v2', 'rp_runtime', 'src', 'plugins', 'hg-round-orchestrator', 'service.mjs',
  );
  const serviceText = fs.readFileSync(servicePath, 'utf8');
  const checks = {
    s4a_active_proposal_kinds: activeKinds,
    only_issue_tension_pressure: activeKinds.length === 1 && activeKinds[0] === 'issue_tension_pressure',
    skip_hook_present: serviceText.includes('skipLibrarianProposalGeneration'),
    skip_invokes_skipped_stage: serviceText.includes("stage: 'skipped'"),
    skip_storyteller_separate: serviceText.includes('skipStorytellerCognition'),
    plot_skip_separate: serviceText.includes('skipPlotCognitionOrchestration'),
    blast_radius_unchanged: activeKinds.length === 1 && activeKinds[0] === 'issue_tension_pressure',
  };
  checks.pass = checks.only_issue_tension_pressure
    && checks.skip_hook_present
    && checks.skip_invokes_skipped_stage
    && checks.blast_radius_unchanged;
  return {
    schema: 'issue201_d10_preflight_v1',
    generated_at: new Date().toISOString(),
    experimental_sha: gitSha(),
    design_anchor_sha: DESIGN_SHA,
    checks,
    verdict: checks.pass ? 'PROCEED' : 'STOP_GOVERNANCE',
  };
}

async function createScenarioSession(client, scenario) {
  const openers = await client.listTemplateOpeners(scenario.id);
  const opener = scenario.openerPreference
    ? openers.find((o) => String(o.opener_id ?? '').includes(scenario.openerPreference)) ?? openers[0]
    : openers[0];
  if (!opener) throw new Error(`no opener for ${scenario.id}`);
  return client.createSession({
    characters: scenario.characters,
    sceneTemplateId: scenario.id,
    roleAssignments: scenario.roleAssignments,
    playerCharacterFileId: scenario.playerCharacterFileId,
    userPersonaId: scenario.userName,
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
  const sceneSessionId = SessionId(`hg-issue201-pvr-${crypto.randomUUID()}`);
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
    inferenceId: `issue201-triage-${crypto.randomUUID()}`,
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
      inferenceId: `issue201-pd-${crypto.randomUUID()}`,
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
  const lastTurn = roundResult.character_turns?.at(-1);
  return lastTurn?.presentation_text ?? '';
}

function objectiveChecks({ history, userEntry, roundResult, presentation }) {
  const issues = [];
  const userPvr = userEntry?.metadata?.perceptual_visibility ?? {};
  if (userPvr.validation_status && userPvr.validation_status !== 'valid') {
    issues.push({ type: 'pvr_validation', detail: userPvr.validation_status });
  }
  if (!roundResult?.committed) {
    issues.push({ type: 'round_not_committed', detail: roundResult?.completion_reason ?? null });
  }
  return {
    issue_count: issues.length,
    issues,
    committed: Boolean(roundResult?.committed),
    completion_reason: roundResult?.completion_reason ?? null,
    selected_character_id: roundResult?.selected_character_id ?? null,
    pvr_validation_status: userPvr.validation_status ?? null,
    presentation_length: String(presentation ?? '').length,
  };
}

async function runSequenceTurn({
  client, api, inferenceOpts, roundOptions, turnIndex, playerStimulus,
  sequenceId, evidenceRoot, policyHash, sessionsDir, plotScopeIdRef,
}) {
  const continuityBefore = extractContinuityForensics(client.activeSessionId, sessionsDir);
  const plotBefore = extractPlotForensics(
    continuityBefore.plot_cognition_scope_id ?? plotScopeIdRef.value,
    sessionsDir,
  );
  const operationId = `issue201-${sequenceId}-t${turnIndex}-${crypto.randomUUID()}`;
  client._beginRoundOperation(operationId, 'user_turn');
  const started = Date.now();
  await runPlayerPvrAndRecord(client, playerStimulus);
  const roundResult = await client.orchestrator.runRound({
    session: { mode: 'open', hg_session_id: client.activeSessionId },
    roleProfiles: inferenceOpts.roleProfiles,
    liveMaxAttempts: inferenceOpts.liveMaxAttempts,
    clientOperationId: operationId,
    spanTracker: client.activeSpanTracker,
    ...roundOptions,
  });
  await client._recordRoundPresentations(api, roundResult);
  await client._refreshTranscript();
  const operation_wall_ms = Date.now() - started;
  const presentation = presentationFromRound(roundResult);
  const history = await api.getSessionHistory(client.activeSessionId);
  const userEntry = [...history.entries].reverse().find((e) => e.kind === 'user');
  const attempts = loadAttemptsForOperation(evidenceRoot, client.activeSessionId, operationId);
  const inference = summarizeAttempts(attempts);
  const continuityAfter = extractContinuityForensics(client.activeSessionId, sessionsDir);
  if (continuityAfter.plot_cognition_scope_id) plotScopeIdRef.value = continuityAfter.plot_cognition_scope_id;
  const plotAfter = extractPlotForensics(continuityAfter.plot_cognition_scope_id, sessionsDir);
  const overlayDelta = {
    before_keys: Object.keys(continuityBefore.issue_pressure_semantic_overlays ?? {}),
    after_keys: Object.keys(continuityAfter.issue_pressure_semantic_overlays ?? {}),
    added: Object.keys(continuityAfter.issue_pressure_semantic_overlays ?? {})
      .filter((k) => !(continuityBefore.issue_pressure_semantic_overlays ?? {})[k]),
  };
  const pressureComparison = comparePressures(
    continuityAfter.issue_pressure_semantic_overlays,
    plotAfter.unresolved_narrative_pressures,
  );
  const postCommit = extractPostCommitForensics(attempts, roundOptions);
  return {
    turn_index: turnIndex,
    policy_hash: policyHash,
    branch_log: null,
    exact_player_stimulus: playerStimulus,
    client_operation_id: operationId,
    hg_round_id: roundResult.hg_round_id ?? null,
    domain_commit_id: roundResult.domain_commit_id ?? null,
    operation_wall_ms,
    presentation_text: presentation,
    objective: objectiveChecks({ history, userEntry, roundResult, presentation }),
    inference,
    storyteller_round_summary: roundResult.storyteller_round_summary ?? null,
    plot_cognition_resume_summary: roundResult.plot_cognition_resume_summary ?? null,
    continuity_turn_index: roundResult.continuity_turn_index ?? null,
    pressure_forensics: {
      post_commit: postCommit,
      continuity_before: {
        overlay_count: Object.keys(continuityBefore.issue_pressure_semantic_overlays ?? {}).length,
        active_issue_ids: continuityBefore.active_issue_ids,
      },
      continuity_after: {
        overlay_count: Object.keys(continuityAfter.issue_pressure_semantic_overlays ?? {}).length,
        issue_pressure_semantic_overlays: continuityAfter.issue_pressure_semantic_overlays,
        active_issue_ids: continuityAfter.active_issue_ids,
      },
      overlay_delta: overlayDelta,
      plot_before: {
        pressure_count: Object.keys(plotBefore.unresolved_narrative_pressures ?? {}).length,
        unresolved_narrative_pressures: plotBefore.unresolved_narrative_pressures,
      },
      plot_after: {
        pressure_count: Object.keys(plotAfter.unresolved_narrative_pressures ?? {}).length,
        unresolved_narrative_pressures: plotAfter.unresolved_narrative_pressures,
      },
      plot_st_comparison: pressureComparison,
    },
  };
}

async function runOneSequence({
  arm, scenarioKey, repIndex, policyBundle, evidenceRoot, outputsDir, sequenceAttempt,
  sessionsDir,
}) {
  const scenario = SCENARIOS[scenarioKey];
  const { policy, policy_hash } = policyBundle;
  const sequenceId = `D10-${arm.arm_id}-${scenarioKey}-seq${repIndex}-a${sequenceAttempt}`;
  const client = new HolyGrailApplicationClient({
    inferenceMode: 'live',
    runtime: {
      inference: {
        mountDeepSeek: true,
        executionEvidence: { enabled: true, root: evidenceRoot },
      },
    },
  });
  await client.start();
  const turns = [];
  const branchLogs = [];
  let failed = false;
  let error = null;
  let hgSessionId = null;
  const plotScopeIdRef = { value: null };
  try {
    const created = await createScenarioSession(client, scenario);
    hgSessionId = created.hg_session_id ?? client.activeSessionId;
    const api = client._domainApi();
    const inferenceOpts = buildInferenceOptions(client.runtimeSettings, {
      inferenceMode: client.options.inferenceMode,
    });
    const priorForPolicy = [];
    for (let turnIndex = 1; turnIndex <= policy.turn_count; turnIndex += 1) {
      const selection = selectPlayerStimulus(policy, turnIndex, priorForPolicy);
      selection.policy_hash = policy_hash;
      branchLogs.push({
        turn: turnIndex,
        policy_hash,
        predicate_hits: selection.predicate_hits,
        winning_predicate: selection.winning_predicate,
        branch_id: selection.branch_id,
        exact_player_stimulus: selection.exact_player_stimulus,
      });
      const turnRow = await runSequenceTurn({
        client,
        api,
        inferenceOpts,
        roundOptions: arm.round_options,
        turnIndex,
        playerStimulus: selection.exact_player_stimulus,
        sequenceId,
        evidenceRoot,
        policyHash: policy_hash,
        sessionsDir,
        plotScopeIdRef,
      });
      turnRow.branch_log = branchLogs[branchLogs.length - 1];
      turns.push(turnRow);
      priorForPolicy.push({
        turn_index: turnIndex,
        presentation_text: turnRow.presentation_text,
        winning_predicate: selection.winning_predicate,
      });
      if (!turnRow.objective.committed) {
        failed = true;
        error = `turn ${turnIndex} not committed: ${turnRow.objective.completion_reason}`;
        break;
      }
    }
  } catch (err) {
    failed = true;
    error = String(err?.message ?? err);
  } finally {
    await client.stop();
  }
  const allCommitted = turns.length === policy.turn_count
    && turns.every((t) => t.objective.committed);
  const postCommitActivations = turns.filter(
    (t) => t.pressure_forensics?.post_commit?.storyteller_post_commit_inference_ran,
  ).length;
  const sequence = {
    sequence_id: sequenceId,
    arm_id: arm.arm_id,
    arm_label: arm.label,
    round_options: arm.round_options,
    scenario_key: scenarioKey,
    scenario_id: scenario.id,
    repetition_index: repIndex,
    sequence_attempt: sequenceAttempt,
    policy_id: policy.policy_id,
    policy_hash,
    hg_session_id: hgSessionId,
    turn_count_expected: policy.turn_count,
    turn_count_completed: turns.length,
    all_committed: allCommitted,
    failed,
    error,
    branch_trajectory: branchLogs,
    turns,
    sequence_wall_ms: turns.reduce((s, t) => s + t.operation_wall_ms, 0),
    sequence_inference: mergeTurnInference(turns),
    post_commit_activation_count: postCommitActivations,
  };
  const outBase = path.join(outputsDir, sequenceId);
  fs.writeFileSync(`${outBase}-sequence.json`, `${JSON.stringify(sequence, null, 2)}\n`);
  for (const t of turns) {
    fs.writeFileSync(
      path.join(outputsDir, `${sequenceId}-t${t.turn_index}-presentation.txt`),
      t.presentation_text,
      'utf8',
    );
  }
  return sequence;
}

function buildBlindSequencePacket(sequences, outputsDir) {
  const eligible = sequences.filter((s) => s.all_committed && !s.failed);
  const shuffled = [...eligible];
  const seed = 20110;
  let s = seed;
  for (let i = shuffled.length - 1; i > 0; i -= 1) {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    const j = s % (i + 1);
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  shuffled.forEach((seq, i) => {
    seq.blind_label = `SEQ-${String.fromCharCode(65 + i)}`;
  });
  const briefingKeys = {
    arkham_asylum_mess_hall_arena: 'arkham_mess_hall_stress',
    ayame_household_entry_evaluation: 'ayame_household_entry',
  };
  const packetPath = path.join(outputsDir, 'issue201-d10-blind-sequence-packet.json');
  const keyPath = path.join(outputsDir, 'issue201-d10-blind-sequence-answer-key.json');
  const packet = {
    schema: 'issue201_blind_sequence_packet_v1',
    purpose: 'D-10 post-commit Storyteller vs Plot — complete sequence bundles',
    causal_question:
      'Once Plot is persistent narrative cognition, does post-commit Storyteller independently create narrative-pressure information that materially improves subsequent RP, or is it duplicative?',
    instructions:
      'Score each complete sequence using the 10 sequence-level dimensions. Do not request arm, session, inference, latency, or pressure forensics until after scoring is locked.',
    sequence_level_dimensions: [
      'thread persistence',
      'escalation coherence',
      'agenda persistence',
      'delayed consequences',
      'scene momentum',
      'cross-turn initiative',
      'reactive-loop avoidance',
      'premature-resolution avoidance',
      'plot-drift control',
      'cross-turn emotional/narrative continuity',
    ],
    sequences: shuffled.map((seq) => ({
      blind_label: seq.blind_label,
      scenario_briefing_key: briefingKeys[seq.scenario_id] ?? seq.scenario_id,
      turns: seq.turns.map((t) => ({
        turn_index: t.turn_index,
        player_stimulus: t.exact_player_stimulus,
        presentation_text: t.presentation_text,
      })),
    })),
  };
  const answerKey = shuffled.map((seq) => ({
    blind_label: seq.blind_label,
    sequence_id: seq.sequence_id,
    arm_id: seq.arm_id,
    scenario_key: seq.scenario_key,
    scenario_id: seq.scenario_id,
    repetition_index: seq.repetition_index,
    policy_id: seq.policy_id,
    policy_hash: seq.policy_hash,
    branch_trajectory: seq.branch_trajectory,
    post_commit_activation_count: seq.post_commit_activation_count,
  }));
  fs.writeFileSync(packetPath, `${JSON.stringify(packet, null, 2)}\n`);
  fs.writeFileSync(keyPath, `${JSON.stringify(answerKey, null, 2)}\n`);
  const leakageFields = ['arm_id', 'hg_session_id', 'pressure_forensics', 'sequence_inference'];
  const packetText = JSON.stringify(packet);
  const leakage = leakageFields.filter((f) => packetText.includes(`"${f}"`));
  return {
    packetPath,
    keyPath,
    sequence_count: shuffled.length,
    excluded: sequences.length - eligible.length,
    blinding_integrity: {
      leakage_fields_in_packet: leakage,
      pass: leakage.length === 0,
    },
  };
}

function summarizePressurePropagation(sequences) {
  const summary = {
    sequences: sequences.map((seq) => {
      const turns = seq.turns ?? [];
      const generated = turns.filter(
        (t) => t.pressure_forensics?.post_commit?.storyteller_post_commit_inference_ran,
      ).length;
      const overlaysAdded = turns.reduce(
        (s, t) => s + (t.pressure_forensics?.overlay_delta?.added?.length ?? 0), 0,
      );
      const classes = turns.flatMap(
        (t) => (t.pressure_forensics?.plot_st_comparison ?? []).map((p) => p.structural_class),
      );
      return {
        sequence_id: seq.sequence_id,
        arm_id: seq.arm_id,
        post_commit_activations: generated,
        overlay_keys_added: overlaysAdded,
        structural_class_counts: classes.reduce((acc, c) => {
          acc[c] = (acc[c] ?? 0) + 1;
          return acc;
        }, {}),
      };
    }),
  };
  return summary;
}

function parseArgs() {
  const args = process.argv.slice(2);
  const out = { only: null, evidenceRoot: null, skipExisting: true, skipAyame: false };
  for (let i = 0; i < args.length; i += 1) {
    if (args[i] === '--only' && args[i + 1]) out.only = args[++i];
    if (args[i] === '--evidence-root' && args[i + 1]) out.evidenceRoot = args[++i];
    if (args[i] === '--no-skip-existing') out.skipExisting = false;
    if (args[i] === '--skip-ayame') out.skipAyame = true;
  }
  return out;
}

async function runSequenceWithRetry(params) {
  const maxAttempts = 2;
  let last = null;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const seq = await runOneSequence({ ...params, sequenceAttempt: attempt });
    last = seq;
    if (seq.all_committed && !seq.failed) return seq;
    console.error(JSON.stringify({
      sequence_id: seq.sequence_id,
      attempt,
      failed: true,
      error: seq.error,
    }));
  }
  return last;
}

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) throw new Error('DEEPSEEK_API_KEY required');
  const cli = parseArgs();
  const preflight = runPreflight();
  if (!preflight.checks.pass) {
    console.error(JSON.stringify(preflight, null, 2));
    throw new Error('D-10 preflight STOP — hook blast radius changed');
  }
  const manifest = buildPolicyManifest();
  const head = gitSha();
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const evidenceRoot = cli.evidenceRoot
    ?? path.join(REPO_ROOT, 'data', 'investigation_runs', `issue201-package-d-d10-${stamp}`);
  const outputsDir = path.join(evidenceRoot, 'outputs');
  fs.mkdirSync(outputsDir, { recursive: true });
  const sessionsDir = defaultSessionsDir();
  fs.writeFileSync(
    path.join(evidenceRoot, 'd10_preflight.json'),
    `${JSON.stringify(preflight, null, 2)}\n`,
  );
  fs.writeFileSync(
    path.join(evidenceRoot, 'd10_policy_manifest.json'),
    `${JSON.stringify(manifest, null, 2)}\n`,
  );

  const policyBundles = {
    arkham_stress: loadPolicy('arkham_d10_policy_v1'),
    ayame_controlled: loadPolicy('ayame_d10_policy_v1'),
  };

  const plan = [];
  for (const scenarioKey of ['arkham_stress', 'ayame_controlled']) {
    if (cli.skipAyame && scenarioKey === 'ayame_controlled') continue;
    const scenario = SCENARIOS[scenarioKey];
    for (let rep = 1; rep <= scenario.sequencesPerArm; rep += 1) {
      const armOrder = scenarioKey === 'ayame_controlled'
        ? ARMS.filter((a) => a.arm_id === 'control').concat(
          ARMS.filter((a) => a.arm_id === 'ablated'),
        )
        : ARMS;
      for (const arm of armOrder) {
        const sequenceId = `D10-${arm.arm_id}-${scenarioKey}-seq${rep}`;
        plan.push({ arm, scenarioKey, rep, sequenceId, requires_ayame_calibration: scenarioKey === 'ayame_controlled' && arm.arm_id === 'ablated' });
      }
    }
  }

  const sequences = [];
  const failures = [];
  const allAttempts = [];
  let ayameCalibrationPassed = true;
  let ayameDropped = false;
  let ayameDropReason = null;

  for (const item of plan) {
    if (item.requires_ayame_calibration && !ayameCalibrationPassed) {
      console.warn(JSON.stringify({
        skipped: item.sequenceId,
        reason: ayameDropReason ?? 'ayame_calibration_failed',
      }));
      continue;
    }
    if (cli.only && !item.sequenceId.includes(cli.only)) continue;
    if (cli.skipExisting) {
      const existingFiles = fs.readdirSync(outputsDir)
        .filter((f) => f.startsWith(`${item.sequenceId}-a`) && f.endsWith('-sequence.json'));
      const committed = existingFiles
        .map((f) => JSON.parse(fs.readFileSync(path.join(outputsDir, f), 'utf8')))
        .find((row) => row.all_committed && !row.failed);
      if (committed) {
        console.log(`Skipping ${item.sequenceId} (existing committed sequence)`);
        sequences.push(committed);
        continue;
      }
    }
    console.log(`Running ${item.sequenceId} (${item.arm.arm_id})...`);
    const seq = await runSequenceWithRetry({
      arm: item.arm,
      scenarioKey: item.scenarioKey,
      repIndex: item.rep,
      policyBundle: policyBundles[item.scenarioKey],
      evidenceRoot,
      outputsDir,
      sessionsDir,
    });
    allAttempts.push(seq);
    if (seq.all_committed && !seq.failed) {
      sequences.push(seq);
      if (item.scenarioKey === 'ayame_controlled' && item.arm.arm_id === 'control') {
        if (seq.post_commit_activation_count < 1) {
          ayameCalibrationPassed = false;
          ayameDropped = true;
          ayameDropReason = 'control_sequence_post_commit_activation_below_threshold';
          console.warn(JSON.stringify({
            ayame_calibration: 'failed',
            reason: ayameDropReason,
            post_commit_activation_count: seq.post_commit_activation_count,
          }));
        }
      }
      console.log(JSON.stringify({
        sequence_id: seq.sequence_id,
        turns: seq.turn_count_completed,
        wall_ms: seq.sequence_wall_ms,
        st_post: seq.sequence_inference.storyteller_post_commit_inference_count,
        plot: seq.sequence_inference.plot_inference_count,
        post_commit_activations: seq.post_commit_activation_count,
      }));
    } else {
      failures.push(seq);
      if (item.scenarioKey === 'ayame_controlled' && item.arm.arm_id === 'control') {
        ayameCalibrationPassed = false;
        ayameDropped = true;
        ayameDropReason = 'ayame_control_sequence_failed';
      }
      console.error(JSON.stringify({ sequence_id: seq.sequence_id, failed: true, error: seq.error }));
    }
  }

  const blind = buildBlindSequencePacket(sequences, outputsDir);
  const pressureSummary = summarizePressurePropagation(sequences);
  const report = {
    schema: 'issue201_package_d_d10_post_commit_v1',
    generated_at: new Date().toISOString(),
    experimental_sha: head,
    control_substrate_sha: CONTROL_SHA,
    design_anchor_sha: DESIGN_SHA,
    evidence_root: evidenceRoot,
    preflight,
    policy_manifest: manifest,
    causal_question:
      'Once Plot is persistent narrative cognition, does post-commit Storyteller independently create narrative-pressure information that materially improves subsequent RP, or is it duplicative?',
    arms: ARMS,
    ayame_confirmatory_dropped: ayameDropped,
    ayame_drop_reason: ayameDropReason,
    sequences,
    failures,
    all_attempts: allAttempts,
    pressure_propagation_summary: pressureSummary,
    human_blind_eval: {
      ...blind,
      status: 'prepared_for_governance_blind_scoring',
    },
  };
  const reportPath = path.join(evidenceRoot, 'issue201-package-d-d10-post-commit-report.json');
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({
    reportPath,
    evidenceRoot,
    sequences_committed: sequences.length,
    failures: failures.length,
    blind_sequences: blind.sequence_count,
    blinding_pass: blind.blinding_integrity.pass,
    ayame_dropped: ayameDropped,
  }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
