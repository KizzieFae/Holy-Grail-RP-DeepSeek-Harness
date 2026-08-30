/**
 * Issue #45 scenario-grade acceptance: retained F/G lineage, tag-origin, restart, S4 join.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { AuditTagService } from '../src/lib/audit-tags/service.mjs';
import { auditTagsRoot } from '../src/lib/audit-tags/config.mjs';
import { resolveTagForensicScope } from '../src/lib/audit-tags/forensic-scope.mjs';
import { CHARACTER_ORIENTATION_SCHEMA } from '../src/lib/character-orientation-envelope.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { createExecutionEvidenceRecorder } from '../src/lib/execution-evidence/recorder.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';
import {
  librarianOmittedCandidateId,
  NI_FORENSICS_CONTRACT,
} from '../src/lib/execution-evidence/ni-evidence.mjs';
import { LIBRARIAN_MEDIATION_RESULT_SCHEMA } from '../src/lib/librarian-mediation-envelope.mjs';
import { LIBRARIAN_PROPOSAL_RESULT_SCHEMA } from '../src/lib/librarian-proposal-envelope.mjs';
import { STORYTELLER_ASSESSMENT_SCHEMA } from '../src/lib/storyteller-assessment-envelope.mjs';
import { STORYTELLER_ORIENTATION_SCHEMA } from '../src/lib/storyteller-orientation-envelope.mjs';
import {
  makeTempSessionsDir,
  reserveLocalPort,
  startDomainApi,
} from './helpers/domain-api.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RETRIEVAL_INDEX = path.join(__dirname, 'fixtures', 'ni-forensics-retrieval-index.json');

const FACT_F_ID = 'ni-fact-f';
const FACT_G_ID = 'ni-fact-g';
const FACT_F_MARKER = 'FACT_F_HIDDEN_MARKER';
const FACT_G_MARKER = 'FACT_G_VISIBLE_MARKER';
const FACT_F_SOURCE = `lmi:cand:${FACT_F_ID}`;
const FACT_G_SOURCE = `lmi:cand:${FACT_G_ID}`;

const MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'checks the rusted latch carefully' }],
  motivation: {
    goal: 'inspect latch',
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

const MEMORY_SCOPE_ID = 'ni-acceptance-scope-1';

function seedScopeKnowledgeFacts(sessionsDir, scopeId) {
  const scopeDir = path.join(sessionsDir, '_scope_knowledge');
  fs.mkdirSync(scopeDir, { recursive: true });
  const safeScope = scopeId.replace(/[/\\]/g, '_');
  const now = new Date().toISOString();
  const payload = {
    scope_id: scopeId,
    records: [
      {
        knowledge_id: FACT_F_ID,
        scope_id: scopeId,
        knowledge_kind: 'learned_world_knowledge',
        content: `${FACT_F_MARKER}: secret treaty clause investigators track but actors may not recall.`,
        authority_class: 'suggestive',
        visibility: 'scope_global',
        source_kind: 'acceptance_seed',
        source_continuity_anchor_id: 'ni-acceptance-anchor-unbound',
        created_at: now,
      },
    ],
  };
  fs.writeFileSync(path.join(scopeDir, `${safeScope}.json`), JSON.stringify(payload, null, 2));
}

const NARRATOR_PROSE = 'Alice checked the rusted latch with deliberate care.';

async function createAcceptanceSession(baseUrl) {
  const res = await fetch(`${baseUrl}/v1/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cast: ['Alice'],
      memory_scope_id: MEMORY_SCOPE_ID,
    }),
  });
  if (!res.ok) throw new Error(`sessions/create failed: ${res.status}`);
  return res.json();
}

const MOCK_STORYTELLER_ORIENTATION = JSON.stringify({
  schema: STORYTELLER_ORIENTATION_SCHEMA,
  orientation_id: 'orient-ni-acc-1',
  turn_index: 0,
  trigger: 'round_start',
  information_gaps: ['What tensions are active for Alice?'],
  temporal_focus: 'current',
  breadth_preference: 'broad',
});

const MOCK_STORYTELLER_ASSESSMENT = JSON.stringify({
  schema: STORYTELLER_ASSESSMENT_SCHEMA,
  assessment_id: 'assess-ni-acc-1',
  observations: [{
    text: 'Betrayal tension is thematically central.',
    evidence_refs: [{ ref_kind: 'bundle_entry', stable_ref: 'entry-alice' }],
    confidence: 'likely',
  }],
  active_tensions: [{
    label: 'Betrayal strain',
    interpretive_note: 'Pressure without required confrontation.',
    evidence_refs: [{ ref_kind: 'bundle_entry', stable_ref: 'entry-alice' }],
  }],
  narrative_priorities: [{
    focus: 'Trust fracture',
    why_it_matters: 'Actors may attend to reconciliation or avoidance.',
    evidence_refs: [{ ref_kind: 'bundle_entry', stable_ref: 'entry-alice' }],
  }],
  progression_opportunities: [{
    opportunity_label: 'Reconciliation path',
    narrative_hook: 'Alice could seek clarity if she chooses.',
    evidence_refs: [{ ref_kind: 'bundle_entry', stable_ref: 'entry-alice' }],
  }],
  unresolved_threads: [{
    thread_label: 'Broken treaty seal',
    neglect_risk: 'May fade if not referenced again.',
    evidence_refs: [{ ref_kind: 'bundle_entry', stable_ref: 'entry-alice' }],
  }],
  uncertainty: [],
  information_gaps: [],
  evidence_refs: [{ ref_kind: 'bundle_entry', stable_ref: 'entry-alice' }],
});

function buildValidLibrarianProposal(commitId) {
  return JSON.stringify({
    schema: LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
    proposals: [{
      proposal_id: 'prop-ni-acc-1',
      proposal_kind: 'information_salience',
      derivation_summary: 'Committed move advances the scene objective.',
      confidence: 'likely',
      evidence_anchors: [{
        anchor_id: `committed_move:${commitId}`,
        evidence_kind: 'committed_move',
        anchor_commit_id: commitId,
      }],
      proposed_payload: {
        subject_ref: `commit:${commitId}`,
        salience_level: 'major',
      },
    }],
  });
}

function mockCharacterOrientation(characterId) {
  return JSON.stringify({
    schema: CHARACTER_ORIENTATION_SCHEMA,
    orientation_id: 'orient-char-ni-acc-1',
    turn_index: 0,
    character_id: characterId,
    information_gaps: ['What do I know about the latch and treaties?'],
    temporal_focus: 'current',
    breadth_preference: 'broad',
  });
}

function mockCharacterMediation() {
  return JSON.stringify({
    schema: LIBRARIAN_MEDIATION_RESULT_SCHEMA,
    selected_items: [{
      source_id: FACT_G_SOURCE,
      relevance_rank: 1,
      relevance_band: 'high',
      interpretive_status: 'likely',
      answers_focus_questions: ['What do I know about the latch and treaties?'],
    }],
  });
}

function makeTempDataEnv(t) {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-ni-acceptance-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const previous = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
    HG_EXECUTION_EVIDENCE_DIR: process.env.HG_EXECUTION_EVIDENCE_DIR,
    HG_AUDIT_TAGS_DIR: process.env.HG_AUDIT_TAGS_DIR,
    RP_RETRIEVED_CONTEXT_INDEX: process.env.RP_RETRIEVED_CONTEXT_INDEX,
  };
  process.env.HG_DATA_DIR = dataDir;
  process.env.HG_EXECUTION_EVIDENCE = 'on';
  delete process.env.HG_EXECUTION_EVIDENCE_DIR;
  delete process.env.HG_AUDIT_TAGS_DIR;
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

function readPersistedAttempts(dataDir, hgSessionId) {
  const root = path.join(evidenceRoot(dataDir), hgSessionId);
  const index = JSON.parse(fs.readFileSync(path.join(root, 'index.json'), 'utf8'));
  const attempts = (index.attempt_ids ?? []).map((evidenceId) => JSON.parse(
    fs.readFileSync(path.join(root, 'attempts', `${evidenceId}.json`), 'utf8'),
  ));
  return { index, attempts, root };
}

function loadSessionAuditLog(sessionsDir, hgSceneId) {
  const sessionPath = path.join(sessionsDir, `${hgSceneId}.json`);
  const session = JSON.parse(fs.readFileSync(sessionPath, 'utf8'));
  return session.metadata?.v2_host_state?.librarian_proposal_audit_log
    ?? session.librarian_proposal_audit_log
    ?? [];
}

function findByInferenceKind(attempts, kind) {
  return attempts.filter((attempt) => attempt.correlation?.inference_kind === kind);
}

function findMediationForCharacter(attempts) {
  return findByInferenceKind(attempts, 'librarian_mediation')
    .find((attempt) => String(attempt.correlation?.parent_inference_id ?? '').startsWith('inf-character-'));
}

function findCharacterMove(attempts) {
  return findByInferenceKind(attempts, 'character_move')
    .find((attempt) => attempt.decision?.commit?.committed);
}

function findDirectorDecision(attempts) {
  return findByInferenceKind(attempts, 'director_decision')[0] ?? null;
}

function requestText(attempt) {
  const contributions = attempt?.request?.contributions ?? [];
  return contributions.map((item) => String(item?.content ?? '')).join('\n');
}

function allRetrievalCandidateIds(mediationAttempt) {
  const dispositions = mediationAttempt.decision?.librarian_mediation?.retrieval_disposition ?? [];
  return dispositions.flatMap((item) => item.candidate_ids_returned ?? []);
}

function reconstructNegativeLineageF(mediationAttempt) {
  const med = mediationAttempt.decision?.librarian_mediation;
  assert.ok(med, 'mediation decision required');
  const catalog = med.catalog_source_ids ?? [];
  const selected = med.selected_source_ids ?? [];
  const retrievalReturned = allRetrievalCandidateIds(mediationAttempt);
  assert.ok(catalog.includes(FACT_F_SOURCE), 'catalog must include F');
  assert.ok(catalog.includes(FACT_G_SOURCE), 'catalog must include G');
  assert.ok(retrievalReturned.includes(FACT_F_ID), 'retrieval returned F');
  assert.ok(retrievalReturned.includes(FACT_G_ID), 'retrieval returned G');
  assert.ok(!selected.includes(FACT_F_SOURCE), 'librarian did not select F');
  assert.equal(
    librarianOmittedCandidateId(catalog, selected, FACT_F_ID),
    FACT_F_ID,
    'F omission owned at librarian mediation',
  );
  return {
    retrievalReturned,
    catalogSourceIds: catalog,
    selectedSourceIds: selected,
    omissionOwner: 'librarian_mediation',
    omittedCandidateId: FACT_F_ID,
  };
}

function reconstructPositiveLineageG(mediationAttempt, characterMoveAttempt) {
  const med = mediationAttempt.decision?.librarian_mediation;
  const catalog = med.catalog_source_ids ?? [];
  const selected = med.selected_source_ids ?? [];
  assert.ok(selected.includes(FACT_G_SOURCE), 'librarian selected G');
  const entryId = med.source_id_to_entry_id?.[FACT_G_SOURCE];
  assert.ok(entryId, 'bundle entry mapped for G');
  const moveText = requestText(characterMoveAttempt);
  assert.ok(moveText.includes(FACT_G_MARKER), 'G semantic content in character request');
  assert.equal(moveText.includes(FACT_F_MARKER), false, 'F not in character request');
  return {
    retrievalReturned: allRetrievalCandidateIds(mediationAttempt),
    catalogSourceIds: catalog,
    selectedSourceIds: selected,
    bundleEntryId: entryId,
    bundleId: med.bundle_id,
    packagingMapped: characterMoveAttempt.associations?.packaging_disposition?.mapped_contribution_ids ?? [],
    characterRequestContains: FACT_G_MARKER,
  };
}


function reconstructFromTag(tag, dataDir, hgSessionId) {
  const scope = tag.forensic_scope ?? {};
  assert.ok(scope.hg_round_id, 'tag forensic_scope has round');
  const { index, attempts } = readPersistedAttempts(dataDir, hgSessionId);
  const recorder = createExecutionEvidenceRecorder({
    enabled: true,
    root: evidenceRoot(dataDir),
  });
  const resolved = resolveTagForensicScope({
    hgSessionId,
    anchor: tag.anchor,
    evidenceRecorder: recorder,
    evidenceIndex: index,
  });
  assert.ok(['complete', 'partial'].includes(resolved.resolution_status), resolved.resolution_status);
  const commitId = tag.anchor?.domain_commit_id ?? scope.domain_commit_id;
  const mediation = findMediationForCharacter(attempts);
  const move = findCharacterMove(attempts);
  assert.ok(mediation && move, 'tag-origin reaches mediation and move evidence');
  const fChain = reconstructNegativeLineageF(mediation);
  const gChain = reconstructPositiveLineageG(mediation, move);
  return { resolved, fChain, gChain, commitId };
}

test('NI forensic acceptance: retained F/G scenario, tag-origin, restart, S4 join', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  const port = await reserveLocalPort();
  const host = await startDomainApi(port, {
    t,
    sessionsDir,
    hostEnv: { HG_RETRIEVAL_INDEX_PATH: RETRIEVAL_INDEX },
  });
  const { baseUrl } = host;

  seedScopeKnowledgeFacts(sessionsDir, MEMORY_SCOPE_ID);

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  const created = await createAcceptanceSession(baseUrl);

  const round = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'open', hg_session_id: created.hg_session_id },
    mockStorytellerOrientationResponse: MOCK_STORYTELLER_ORIENTATION,
    mockStorytellerAssessmentResponse: MOCK_STORYTELLER_ASSESSMENT,
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterOrientationResponses: [mockCharacterOrientation('Alice')],
    mockCharacterMediationResponses: [mockCharacterMediation()],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
    mockLibrarianProposalResponses: ({ domainCommitId }) => buildValidLibrarianProposal(domainCommitId),
  });

  assert.equal(round.completion_status, 'completed', round.completion_reason);
  assert.equal(round.presentation_rendered, true);
  const hgSessionId = round.hg_session_id;
  const hgSceneId = round.hg_scene_id;
  const domainCommitId = round.domain_commit_id;
  assert.ok(domainCommitId);

  await ctx.fiber.dispose();
  await host.stop();

  const { index, attempts } = readPersistedAttempts(dataDir, hgSessionId);
  assert.equal(index.ni?.evidence_contract, NI_FORENSICS_CONTRACT);

  const orientation = findByInferenceKind(attempts, 'character_orientation')[0];
  const mediation = findMediationForCharacter(attempts);
  const storytellerAssessment = findByInferenceKind(attempts, 'storyteller_assessment')[0];
  const storytellerOrientation = findByInferenceKind(attempts, 'storyteller_orientation')[0];
  const director = findDirectorDecision(attempts);
  const characterMove = findCharacterMove(attempts);
  const proposal = findByInferenceKind(attempts, 'librarian_proposal')[0];

  assert.ok(orientation, 'character orientation evidence');
  assert.ok(mediation, 'librarian mediation evidence');
  assert.ok(storytellerAssessment, 'storyteller assessment evidence');
  assert.ok(storytellerOrientation, 'storyteller orientation evidence');
  assert.ok(director, 'director decision evidence');
  assert.ok(characterMove, 'committed character move evidence');
  assert.ok(proposal, 'librarian proposal evidence');

  const fChain = reconstructNegativeLineageF(mediation);
  const gChain = reconstructPositiveLineageG(mediation, characterMove);

  assert.ok(director.associations?.storyteller_assessment_evidence_id, 'director linked to storyteller');
  assert.ok(
    director.associations?.packaging_disposition?.mapped_contribution_ids?.length,
    'director packaging disposition recorded',
  );
  const directorText = requestText(director);
  assert.ok(
    directorText.includes('Betrayal') || directorText.includes('Trust fracture'),
    'storyteller advisory projected into director request',
  );

  const port2 = await reserveLocalPort();
  const host2 = await startDomainApi(port2, {
    t,
    sessionsDir,
    hostEnv: { HG_RETRIEVAL_INDEX_PATH: RETRIEVAL_INDEX },
  });
  const api = createDomainApiClient(host2.baseUrl);
  await api.openSession(hgSessionId);

  const history = await api.getSessionHistory(hgSessionId);
  const presentationEntry = (history.entries ?? []).find((entry) => entry.kind === 'presentation')
    ?? (history.entries ?? []).find(
      (entry) => entry.kind === 'committed_turn' && entry.domain_commit_id === domainCommitId,
    )
    ?? (history.transcript ?? []).find((entry) => entry.role === 'assistant');
  assert.ok(presentationEntry?.entry_id, 'presentation entry for tag anchor');

  const tagService = new AuditTagService({
    env: {
      HG_DATA_DIR: dataDir,
      HG_EXECUTION_EVIDENCE: 'on',
    },
  });
  const { tag } = await tagService.createTag({
    hgSessionId,
    entryId: presentationEntry.entry_id,
    getHistory: async () => history,
    createdBy: { surface: 'test', persona: 'Player' },
  });
  assert.ok(tag.forensic_scope, 'tag has forensic_scope');
  const tagOrigin = reconstructFromTag(tag, dataDir, hgSessionId);
  assert.deepEqual(tagOrigin.fChain.omittedCandidateId, FACT_F_ID);
  assert.equal(tagOrigin.gChain.characterRequestContains, FACT_G_MARKER);

  const auditLog = loadSessionAuditLog(sessionsDir, hgSceneId);
  assert.equal(auditLog.length, 1);
  const auditEntry = auditLog[0];
  const batchId = auditEntry.librarian_proposal_batch_id;
  assert.ok(batchId);
  assert.equal(auditEntry.librarian_proposal_domain_commit_id, domainCommitId);

  const restartedStore = new ExecutionEvidenceStore(evidenceRoot(dataDir));
  const restartedRecorder = createExecutionEvidenceRecorder({
    enabled: true,
    root: evidenceRoot(dataDir),
  });
  restartedStore.rebuildSemanticNavigationIndexes(hgSessionId);
  const restartedIndex = restartedRecorder.readIndex(hgSessionId);
  const { attempts: restartedAttempts } = readPersistedAttempts(dataDir, hgSessionId);

  const restartedMediation = findMediationForCharacter(restartedAttempts);
  const restartedMove = findCharacterMove(restartedAttempts);
  reconstructNegativeLineageF(restartedMediation);
  reconstructPositiveLineageG(restartedMediation, restartedMove);
  reconstructFromTag(tag, dataDir, hgSessionId);

  const proposals = findByInferenceKind(restartedAttempts, 'librarian_proposal');
  assert.equal(proposals.length, 1, 'exactly one proposal evidence attempt after restart');
  const proposalMatch = proposals[0];
  assert.equal(proposalMatch.decision?.librarian_proposal?.batch_id, batchId);
  assert.equal(
    restartedIndex.ni?.by_commit?.[domainCommitId]?.proposal_evidence_id,
    proposalMatch.evidence_id,
  );
  assert.ok(
    proposalMatch.associations?.domain_commit_id === domainCommitId
    || proposalMatch.correlation?.domain_commit_id === domainCommitId
    || auditEntry.librarian_proposal_domain_commit_id === domainCommitId,
  );

  const tagsRoot = auditTagsRoot({ HG_DATA_DIR: dataDir });
  const tagPath = path.join(tagsRoot, hgSessionId, 'tags', `${tag.tag_id}.json`);
  assert.ok(fs.existsSync(tagPath), 'audit tag persisted on disk');
  assert.ok(fs.existsSync(path.join(evidenceRoot(dataDir), hgSessionId, 'index.json')));
});
