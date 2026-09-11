/**
 * Issue #164 formal validation harness (scenario-grade fresh-scene paths).
 */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';
import { resolvePostCommitSemanticDecision } from '../src/lib/execution-evidence/ni-evidence.mjs';
import { LIBRARIAN_PROPOSAL_RESULT_SCHEMA } from '../src/lib/librarian-proposal-envelope.mjs';
import {
  appendEffectiveConfigurationEpoch,
  captureBuildProvenance,
  buildEffectiveConfigurationSnapshot,
  createEffectiveConfigurationEpoch,
  sha256CanonicalFingerprint,
} from '../src/lib/runtime-configuration-provenance.mjs';
import {
  makeTempSessionsDir,
  reserveLocalPort,
  startDomainApi,
} from './helpers/domain-api.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');
const NI_FIXTURE_EVIDENCE = path.join(
  REPO_ROOT,
  'tools/investigation/fixtures/ni_forensic_acceptance/execution_evidence',
);

const MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'checks the latch carefully' }],
  motivation: {
    goal: 'inspect',
    tactic: 'slow check',
    emotional_driver: 'wary',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const DIRECTOR_FOR = (name) => ({
  next_actor: name,
  end_round: false,
  reason: `${name} should speak next.`,
  environment_event: '',
  tension_shift: 'steady',
});

const NARRATOR_PROSE = 'Alice checked the latch with deliberate care.';

function makeTempDataEnv(t) {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-val-164-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const previous = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
    HG_EXECUTION_EVIDENCE_DIR: process.env.HG_EXECUTION_EVIDENCE_DIR,
  };
  process.env.HG_DATA_DIR = dataDir;
  process.env.HG_EXECUTION_EVIDENCE = 'on';
  delete process.env.HG_EXECUTION_EVIDENCE_DIR;
  t.after(() => {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    fs.rmSync(dataDir, { recursive: true, force: true });
  });
  return { dataDir, sessionsDir };
}

function evidenceRoot(dataDir) {
  return path.join(dataDir, 'execution_evidence');
}

function readAttempts(dataDir, hgSessionId) {
  const root = path.join(evidenceRoot(dataDir), hgSessionId);
  const index = JSON.parse(fs.readFileSync(path.join(root, 'index.json'), 'utf8'));
  const attempts = (index.attempt_ids ?? []).map((evidenceId) => JSON.parse(
    fs.readFileSync(path.join(root, 'attempts', `${evidenceId}.json`), 'utf8'),
  ));
  return { index, attempts, root };
}

function byInferenceKind(attempts, kind) {
  return attempts.filter((entry) => entry.correlation?.inference_kind === kind);
}

function loadSessionAuditLog(sessionsDir, hgSceneId) {
  const files = fs.readdirSync(sessionsDir).filter((name) => name.endsWith('.json') && name !== '_session_index.json');
  for (const name of files) {
    const payload = JSON.parse(fs.readFileSync(path.join(sessionsDir, name), 'utf8'));
    const hostState = payload.metadata?.v2_host_state ?? {};
    if (payload.hg_session_id === hgSceneId || name.replace('.json', '') === hgSceneId) {
      return hostState.librarian_proposal_audit_log ?? [];
    }
  }
  for (const name of files) {
    const payload = JSON.parse(fs.readFileSync(path.join(sessionsDir, name), 'utf8'));
    if (payload.hg_session_id === hgSceneId) {
      return payload.metadata?.v2_host_state?.librarian_proposal_audit_log ?? [];
    }
  }
  return [];
}

function buildValidProposal(commitId) {
  return JSON.stringify({
    schema: LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
    proposals: [{
      proposal_id: 'prop-val-1',
      proposal_kind: 'issue_tension_pressure',
      proposal_origin: 'storyteller',
      derivation_summary: 'Active issue pressure remains.',
      confidence: 'likely',
      evidence_anchors: [
        {
          anchor_id: `committed_move:${commitId}`,
          evidence_kind: 'committed_move',
          anchor_commit_id: commitId,
        },
        {
          anchor_id: 'continuity_issue:issue-live-1',
          evidence_kind: 'continuity_issue',
          anchor_commit_id: commitId,
        },
      ],
      proposed_payload: {
        issue_ref: 'issue-live-1',
        semantic_unmet_condition: 'Pressure remains after the move.',
      },
    }],
  });
}

function assertNoSecretLeak(payload) {
  const text = JSON.stringify(payload);
  assert.ok(!text.includes('DEEPSEEK_API_KEY'), 'API key leaked');
  assert.ok(!/sk-[a-zA-Z0-9]{10,}/.test(text), 'token-like secret leaked');
  assert.ok(!text.includes('secret-value'), 'test secret leaked');
}

const validationEvidence = {
  zeroWork: null,
  eligible: null,
};

test('Issue #164 formal validation — fresh-scene zero-work path (V1/V3/V5/V6/V7/V15)', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  const port = await reserveLocalPort();
  const host = await startDomainApi(port, { t, sessionsDir });
  const { baseUrl } = host;

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const created = await fetch(`${baseUrl}/v1/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cast: ['Alice'] }),
  }).then((res) => res.json());

  const epochId = 'epoch-val-zero';
  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'open', hg_session_id: created.hg_session_id },
    skipStorytellerCognition: true,
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
    effectiveConfigurationEpochId: epochId,
  });

  const hgSessionId = result.hg_session_id;
  const domainCommitId = result.domain_commit_id;
  const { index, attempts } = readAttempts(dataDir, hgSessionId);

  const semanticAttempts = byInferenceKind(attempts, 'storyteller_post_commit_issue_pressure');
  assert.equal(semanticAttempts.length, 0, 'no semantic LLM on zero-work path');

  const disposition = attempts.find(
    (entry) => entry.correlation?.role === 'post_commit_semantic_disposition',
  );
  assert.ok(disposition, 'deterministic disposition evidence exists');
  assert.equal(disposition.request, null);
  assert.equal(disposition.response, null);
  assert.equal(disposition.correlation.record_class, 'deterministic_disposition');
  assert.equal(disposition.inference_health, undefined);
  assert.equal(
    disposition.decision.post_commit_semantic_disposition.inference_required,
    false,
  );
  assert.equal(
    disposition.decision.post_commit_semantic_disposition.eligibility_outcome,
    'no_eligible_active_issues',
  );
  assert.equal(disposition.correlation.effective_configuration_epoch_id, epochId);

  const commitBucket = index.ni.by_commit[domainCommitId];
  assert.equal(commitBucket.semantic_disposition_evidence_id, disposition.evidence_id);
  assert.equal(commitBucket.proposal_evidence_id, undefined);

  const roundActivity = index.round_activity[result.hg_round_id];
  assert.ok(roundActivity);
  assert.equal(roundActivity.inference_kinds?.post_commit_semantic_disposition, undefined);

  const eventTypes = (result.scene_events ?? []).map((event) => event.type);
  assert.ok(eventTypes.includes('hg/post-commit-semantic-started'));
  assert.ok(eventTypes.includes('hg/post-commit-semantic-completed'));
  assert.ok(eventTypes.includes('hg/post-commit-semantic-join'));
  assert.equal(eventTypes.filter((type) => type.startsWith('hg/librarian-proposal-')).length, 0);

  const auditLog = loadSessionAuditLog(sessionsDir, result.hg_scene_id);
  assert.equal(auditLog.length, 1);
  const audit = auditLog[0];
  assert.equal(audit.semantic_producer_role, 'storyteller');
  assert.equal(audit.semantic_eligibility_skip_reason, 'no_eligible_active_issues');
  assert.ok(audit.post_commit_semantic_domain_commit_id);

  const store = new ExecutionEvidenceStore(evidenceRoot(dataDir));
  const rebuilt = store.rebuildSemanticNavigationIndexes(hgSessionId);
  assert.equal(
    rebuilt.ni.by_commit[domainCommitId].semantic_disposition_evidence_id,
    disposition.evidence_id,
  );

  const turnJson = execFileSync(
    'python',
    [
      path.join(REPO_ROOT, 'tools/investigation/trace_turn_forensics.py'),
      hgSessionId,
      'commit',
      domainCommitId,
      '--json',
      '--sessions-root',
      sessionsDir,
      '--evidence-root',
      evidenceRoot(dataDir),
    ],
    { encoding: 'utf8', cwd: REPO_ROOT },
  );
  const turnEnvelope = JSON.parse(turnJson);
  const semanticAudit = turnEnvelope.surfaces.find((s) => s.contract === 'post_commit_semantic_audit');
  assert.ok(semanticAudit);
  assert.equal(semanticAudit.summary.semantic_producer_role, 'storyteller');
  assert.equal(semanticAudit.summary.inference_required, false);
  assert.equal(semanticAudit.summary.semantic_eligibility_skip_reason, 'no_eligible_active_issues');

  await host.stop();
  const port2 = await reserveLocalPort();
  const host2 = await startDomainApi(port2, { t, sessionsDir });
  await createDomainApiClient(host2.baseUrl).openSession(hgSessionId);
  const { attempts: reloadedAttempts, index: reloadedIndex } = readAttempts(dataDir, hgSessionId);
  const reloadedDisposition = reloadedAttempts.find(
    (entry) => entry.evidence_id === disposition.evidence_id,
  );
  assert.ok(reloadedDisposition);
  assert.equal(
    reloadedIndex.ni.by_commit[domainCommitId].semantic_disposition_evidence_id,
    disposition.evidence_id,
  );

  validationEvidence.zeroWork = {
    hgSessionId,
    hgRoundId: result.hg_round_id,
    domainCommitId,
    dispositionEvidenceId: disposition.evidence_id,
    epochId,
  };
});

test('Issue #164 formal validation — fresh-scene eligible path (V2/V3/V5/V6/V7/V11)', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  const port = await reserveLocalPort();
  const host = await startDomainApi(port, { t, sessionsDir });
  const { baseUrl } = host;

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const created = await fetch(`${baseUrl}/v1/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cast: ['Alice'], seed_active_issue: true }),
  }).then((res) => res.json());

  const epochId = 'epoch-val-eligible';
  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'open', hg_session_id: created.hg_session_id },
    skipStorytellerCognition: true,
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
    mockLibrarianProposalResponses: ({ domainCommitId }) => buildValidProposal(domainCommitId),
    effectiveConfigurationEpochId: epochId,
  });

  const hgSessionId = result.hg_session_id;
  const domainCommitId = result.domain_commit_id;
  const { index, attempts } = readAttempts(dataDir, hgSessionId);

  const semanticAttempts = byInferenceKind(attempts, 'storyteller_post_commit_issue_pressure');
  assert.equal(semanticAttempts.length, 1, 'exactly one semantic LLM per commit');
  const proposalAttempt = semanticAttempts[0];
  assert.equal(proposalAttempt.decision?.librarian_proposal, undefined);
  assert.ok(proposalAttempt.decision?.post_commit_semantic);
  assert.equal(
    proposalAttempt.decision.post_commit_semantic.semantic_producer_role,
    'storyteller',
  );
  assert.equal(proposalAttempt.correlation.effective_configuration_epoch_id, epochId);
  assert.ok(proposalAttempt.request?.inference_profile);

  const dispositionAttempts = attempts.filter(
    (entry) => entry.correlation?.role === 'post_commit_semantic_disposition',
  );
  assert.equal(dispositionAttempts.length, 0);

  const commitBucket = index.ni.by_commit[domainCommitId];
  assert.equal(commitBucket.proposal_evidence_id, proposalAttempt.evidence_id);
  assert.equal(commitBucket.semantic_disposition_evidence_id, undefined);

  const auditLog = loadSessionAuditLog(sessionsDir, result.hg_scene_id);
  assert.equal(auditLog.length, 1);
  const audit = auditLog[0];
  assert.equal(audit.semantic_producer_role, 'storyteller');
  assert.ok(audit.post_commit_semantic_batch_id);
  assert.equal(audit.librarian_inference_id, undefined);

  const eventTypes = (result.scene_events ?? []).map((event) => event.type);
  assert.ok(eventTypes.includes('hg/post-commit-semantic-started'));
  assert.ok(eventTypes.includes('hg/post-commit-semantic-completed'));
  assert.ok(eventTypes.includes('hg/post-commit-semantic-join'));
  assert.equal(eventTypes.filter((type) => type.startsWith('hg/librarian-proposal-')).length, 0);

  const store = new ExecutionEvidenceStore(evidenceRoot(dataDir));
  const rebuilt = store.rebuildSemanticNavigationIndexes(hgSessionId);
  assert.equal(
    rebuilt.ni.by_commit[domainCommitId].proposal_evidence_id,
    proposalAttempt.evidence_id,
  );

  validationEvidence.eligible = {
    hgSessionId,
    hgRoundId: result.hg_round_id,
    domainCommitId,
    proposalEvidenceId: proposalAttempt.evidence_id,
    epochId,
  };
});

test('Issue #164 formal validation — historical compatibility (V4)', () => {
  const legacyAttempt = {
    decision: {
      librarian_proposal: {
        batch_id: 'legacy-batch-1',
        orchestration_status: 'finalized',
        semantic_producer_role: 'librarian',
      },
    },
  };
  const resolved = resolvePostCommitSemanticDecision(legacyAttempt.decision);
  assert.equal(resolved.batch_id, 'legacy-batch-1');
  assert.equal(resolved.semantic_producer_role, 'librarian');

  const historicalSession = 'hg-session-ni-acc-1';
  const historicalPath = path.join(NI_FIXTURE_EVIDENCE, historicalSession, 'index.json');
  assert.ok(fs.existsSync(historicalPath), 'historical NI fixture present');
  const historicalIndex = JSON.parse(fs.readFileSync(historicalPath, 'utf8'));
  assert.ok(historicalIndex.ni?.by_commit);
});

test('Issue #164 formal validation — runtime provenance lifecycle (V8–V14)', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);

  const client = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { sessionsDir },
    env: {
      ...process.env,
      HG_DATA_DIR: dataDir,
      DEEPSEEK_API_KEY: 'secret-value',
      HG_REPO_COMMIT_SHA: 'validation-sha-164',
    },
  });
  await client.start();
  t.after(() => client.stop());

  const opened = await client.createSession({ cast: ['Alice'] });
  const hgSessionId = opened.hg_session_id;
  const state1 = await client.getSessionState();
  const baseUrl = client.supervisor.domainHost?.baseUrl;
  const build = client.runtimeBuildProvenance;
  const effective1 = client.runtimeEffectiveConfiguration;
  assert.equal(build.schema, 'hg_runtime_build_provenance_v1');
  assert.equal(build.repository_commit_sha, 'validation-sha-164');
  assert.ok(build.captured_at);
  assert.notEqual(build.effective_configuration_fingerprint, effective1.epochs[0].effective_configuration_fingerprint);
  assertNoSecretLeak(build);
  assert.equal(effective1.epochs.length, 1);
  assert.equal(effective1.current_epoch_id, effective1.epochs[0].epoch_id);

  await client.updateRuntimeSettings({ inferenceMode: 'mock' });
  assert.equal(client.runtimeEffectiveConfiguration.epochs.length, 1, 'stable settings: no duplicate epoch');

  const round1 = await client.submitSkipTurn({
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
  });
  const { attempts: attempts1 } = readAttempts(dataDir, hgSessionId);
  const llm1 = attempts1.filter((a) => a.request?.schema === 'hg_assembled_request_v1');
  const round1EpochIds = new Set(
    llm1.map((attempt) => attempt.correlation.effective_configuration_epoch_id).filter(Boolean),
  );
  assert.equal(round1EpochIds.size, 1, 'round attempts share one governing epoch');
  const round1EpochId = [...round1EpochIds][0];
  assert.ok(
    client.runtimeEffectiveConfiguration.epochs.some((epoch) => epoch.epoch_id === round1EpochId),
    'governing epoch is persisted in configuration epochs',
  );

  await client.updateRuntimeSettings({ inferenceMode: 'live', model: 'deepseek-chat' });
  const epochsAfterSettings = client.runtimeEffectiveConfiguration;
  assert.ok(epochsAfterSettings.epochs.length >= 2, 'material settings change appends epoch');
  assert.notEqual(
    epochsAfterSettings.epochs.at(-1).effective_configuration_fingerprint,
    effective1.epochs[0].effective_configuration_fingerprint,
  );

  const settingsEpochId = epochsAfterSettings.current_epoch_id;
  const round2 = await client.submitSkipTurn({
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
  });
  const { attempts: attempts2 } = readAttempts(dataDir, hgSessionId);
  const round2Llm = attempts2.filter((a) => a.request?.schema === 'hg_assembled_request_v1')
    .filter((a) => !attempts1.some((prior) => prior.evidence_id === a.evidence_id));
  assert.ok(round2Llm.length >= 1);
  for (const attempt of round2Llm) {
    assert.equal(attempt.correlation.effective_configuration_epoch_id, settingsEpochId);
  }

  await client.openSession(hgSessionId);
  assert.deepEqual(client.runtimeBuildProvenance, build);
  assert.equal(
    client.runtimeEffectiveConfiguration.current_epoch_id,
    epochsAfterSettings.current_epoch_id,
  );

  const fpA = createEffectiveConfigurationEpoch({
    settings: { inferenceMode: 'mock' },
    options: { inferenceMode: 'mock' },
    epochId: 'fp-a',
  });
  const fpB = createEffectiveConfigurationEpoch({
    settings: { inferenceMode: 'mock' },
    options: { inferenceMode: 'mock' },
    epochId: 'fp-b',
    effectiveFrom: 'session_open',
  });
  fpB.captured_at = 'different-time';
  assert.equal(fpA.effective_configuration_fingerprint, fpB.effective_configuration_fingerprint);

  const fpLive = createEffectiveConfigurationEpoch({
    settings: { inferenceMode: 'live', model: 'deepseek-chat' },
    options: { inferenceMode: 'live' },
    epochId: 'fp-live',
  });
  assert.notEqual(fpA.effective_configuration_fingerprint, fpLive.effective_configuration_fingerprint);

  const partialSnapshot = buildEffectiveConfigurationSnapshot(
    {},
    { inferenceMode: 'live', env: { HG_EXECUTION_EVIDENCE: 'on' } },
  );
  assert.ok(['complete', 'partial'].includes(partialSnapshot.capture_status));
  assert.ok(Array.isArray(partialSnapshot.unavailable_fields));
  assertNoSecretLeak(partialSnapshot);
  assertNoSecretLeak(client.runtimeEffectiveConfiguration);
  const sessionFile = JSON.parse(fs.readFileSync(path.join(sessionsDir, `${hgSessionId}.json`), 'utf8'));
  assert.deepEqual(sessionFile.metadata.v2_host_state.runtime_build_provenance, build);

  assert.ok(round1.round.committed);
  assert.ok(state1.hg_session_id);
});

test('Issue #164 formal validation — export evidence ids for report', () => {
  assert.ok(validationEvidence.zeroWork?.dispositionEvidenceId);
  assert.ok(validationEvidence.eligible?.proposalEvidenceId);
});
