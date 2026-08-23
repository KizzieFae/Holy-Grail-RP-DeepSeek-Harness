import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createHolyGrailAppServer } from '../src/application/app-server.mjs';
import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import { auditTagsRoot } from '../src/lib/audit-tags/config.mjs';
import { buildAnchorFromHistoryEntry } from '../src/lib/audit-tags/resolve-anchor.mjs';
import { AuditTagService } from '../src/lib/audit-tags/service.mjs';
import { AuditTagStore } from '../src/lib/audit-tags/store.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';
import {
  createTestSession,
  makeTempSessionsDir,
  startDomainApi,
} from './helpers/domain-api.mjs';

const MOCK_ROUND = {
  mockDirectorResponses: [
    JSON.stringify({
      next_actor: 'Alice',
      end_round: false,
      reason: 'Alice should respond.',
      environment_event: '',
      tension_shift: '',
    }),
    JSON.stringify({
      next_actor: 'Alice',
      end_round: true,
      reason: 'Round complete.',
      environment_event: '',
      tension_shift: '',
    }),
  ],
  mockCharacterTurnResponses: [[
    JSON.stringify({
      move_schema_version: 2,
      beats: [{ type: 'action', action: 'nods' }],
      motivation: {
        goal: 'ack',
        tactic: 'gesture',
        emotional_driver: 'calm',
        risk_level: 'low',
      },
      semantic_evaluation: { decision: 'no_covered_change' },
    }),
  ]],
  mockNarratorTurnResponses: [['Alice nodded thoughtfully in the workshop.']],
};

function makeTempDataEnv(t) {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-audit-tags-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const previous = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_AUDIT_TAGS_DIR: process.env.HG_AUDIT_TAGS_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
    HG_EXECUTION_EVIDENCE_DIR: process.env.HG_EXECUTION_EVIDENCE_DIR,
  };
  process.env.HG_DATA_DIR = dataDir;
  delete process.env.HG_AUDIT_TAGS_DIR;
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

test('audit tag store: create persists with null comment and index mapping', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-tag-store-'));
  const store = new AuditTagStore(root);
  const anchor = {
    kind: 'transcript_entry',
    entry_id: 'entry-1',
    sequence_index: 0,
    transcript_role: 'assistant',
    speaker: 'Alice',
    hg_round_id: 'round-1',
    domain_commit_id: 'commit-1',
    opening: false,
    player_skip: false,
    presentation_failed: false,
  };
  const { tag, created } = store.createTag('sess-1', {
    tag_id: 'tag-1',
    tag_index: 0,
    hg_session_id: 'sess-1',
    anchor,
    created_by: { surface: 'test', persona: 'Player' },
  });
  assert.equal(created, true);
  assert.equal(tag.comment, null);
  const index = store.readIndex('sess-1');
  assert.equal(index.tags_by_entry_id['entry-1'], 'tag-1');
  const reloaded = store.readTag('sess-1', 'tag-1');
  assert.equal(reloaded.anchor.entry_id, 'entry-1');
  fs.rmSync(root, { recursive: true, force: true });
});

test('audit tag store: idempotent create returns existing tag', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-tag-store-'));
  const store = new AuditTagStore(root);
  const anchor = {
    kind: 'transcript_entry',
    entry_id: 'entry-1',
    sequence_index: 0,
    transcript_role: 'assistant',
    speaker: 'Alice',
    hg_round_id: null,
    domain_commit_id: null,
    opening: false,
    player_skip: false,
    presentation_failed: false,
  };
  store.allocateTagIndex('sess-1');
  const first = store.createTag('sess-1', {
    tag_id: 'tag-1',
    tag_index: 0,
    hg_session_id: 'sess-1',
    anchor,
    created_by: { surface: 'test', persona: 'Player' },
  });
  const second = store.createTag('sess-1', {
    tag_id: 'tag-2',
    tag_index: 1,
    hg_session_id: 'sess-1',
    anchor,
    created_by: { surface: 'test', persona: 'Player' },
  });
  assert.equal(first.created, true);
  assert.equal(second.created, false);
  assert.equal(second.tag.tag_id, 'tag-1');
  assert.equal(store.listTagIds('sess-1').length, 1);
  assert.equal(store.readIndex('sess-1').next_tag_index, 1);
  fs.rmSync(root, { recursive: true, force: true });
});

test('audit tag store: comment update and delete', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-tag-store-'));
  const store = new AuditTagStore(root);
  const anchor = {
    kind: 'transcript_entry',
    entry_id: 'entry-1',
    sequence_index: 0,
    transcript_role: 'user',
    speaker: 'Player',
    hg_round_id: 'round-1',
    domain_commit_id: null,
    opening: false,
    player_skip: false,
    presentation_failed: false,
  };
  store.createTag('sess-1', {
    tag_id: 'tag-1',
    tag_index: 0,
    hg_session_id: 'sess-1',
    anchor,
    created_by: { surface: 'test', persona: 'Player' },
  });
  const updated = store.updateComment('sess-1', 'tag-1', 'suspicious');
  assert.equal(updated.comment, 'suspicious');
  assert.ok(updated.comment_updated_at);
  store.deleteTag('sess-1', 'tag-1');
  assert.equal(store.readTag('sess-1', 'tag-1'), null);
  assert.equal(store.readIndex('sess-1').tags_by_entry_id['entry-1'], undefined);
  fs.rmSync(root, { recursive: true, force: true });
});

test('resolve anchor covers representative history kinds', () => {
  const presentation = buildAnchorFromHistoryEntry({
    entry_id: 'p1',
    sequence_index: 2,
    kind: 'presentation',
    actor_id: 'Alice',
    hg_round_id: 'round-1',
    domain_commit_id: 'commit-1',
    presentation_status: 'failed',
  });
  assert.equal(presentation.presentation_failed, true);
  assert.equal(presentation.domain_commit_id, 'commit-1');

  const opening = buildAnchorFromHistoryEntry({
    entry_id: 'opening-1',
    sequence_index: 0,
    kind: 'opening',
    content: 'Once upon a time',
  });
  assert.equal(opening.opening, true);
  assert.equal(opening.speaker, 'Narrator');

  const skip = buildAnchorFromHistoryEntry({
    entry_id: 'skip-1',
    sequence_index: 1,
    kind: 'player_skip',
    actor_id: 'Player',
    metadata: { speaker: 'Player' },
    content: 'Turn skipped',
  });
  assert.equal(skip.player_skip, true);
});

test('audit tag service: multi-tag session with independent comments', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-tag-service-'));
  const service = new AuditTagService({ root });
  const entries = Array.from({ length: 5 }, (_, index) => ({
    entry_id: `entry-${index}`,
    sequence_index: index,
    kind: index % 2 === 0 ? 'user' : 'presentation',
    content: `line ${index}`,
    actor_id: index % 2 === 0 ? 'Player' : 'Alice',
    hg_round_id: `round-${Math.floor(index / 2)}`,
    domain_commit_id: index % 2 === 0 ? null : `commit-${index}`,
    presentation_status: 'succeeded',
    metadata: {},
  }));
  const getHistory = async () => ({ entries });

  for (const entry of entries) {
    const result = await service.createTag({
      hgSessionId: 'sess-1',
      entryId: entry.entry_id,
      getHistory,
      createdBy: { surface: 'test', persona: 'Player' },
    });
    assert.equal(result.created, true);
    await service.updateComment('sess-1', result.tag.tag_id, `note-${entry.entry_id}`);
  }

  const listed = service.listTags('sess-1');
  assert.equal(listed.length, 5);
  assert.deepEqual(
    listed.map((tag) => tag.comment),
    entries.map((entry) => `note-${entry.entry_id}`),
  );
  fs.rmSync(root, { recursive: true, force: true });
});

test('app server: audit tag create is idempotent and note updates are separate', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  const client = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { sessionsDir },
    env: process.env,
  });
  await client.start();
  t.after(() => client.stop());

  const server = createHolyGrailAppServer(client);
  const { baseUrl } = await server.listen(0);
  t.after(() => server.close());

  const created = await fetch(`${baseUrl}/api/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cast: ['Alice'] }),
  }).then((r) => r.json());
  const hgSessionId = created.session.hg_session_id;

  const turn = await fetch(`${baseUrl}/api/turns/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userMessage: 'Hello Alice', ...MOCK_ROUND }),
  }).then((r) => r.json());
  const entry = turn.transcript.find((item) => item.role === 'assistant');
  assert.ok(entry?.entry_id);

  const first = await fetch(`${baseUrl}/api/audit-tags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      hg_session_id: hgSessionId,
      entry_id: entry.entry_id,
      created_by: { surface: 'test', persona: 'Player' },
    }),
  });
  assert.equal(first.status, 201);
  const firstBody = await first.json();
  assert.equal(firstBody.tag.comment, null);

  const second = await fetch(`${baseUrl}/api/audit-tags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      hg_session_id: hgSessionId,
      entry_id: entry.entry_id,
    }),
  });
  assert.equal(second.status, 200);
  const secondBody = await second.json();
  assert.equal(secondBody.created, false);
  assert.equal(secondBody.tag.tag_id, firstBody.tag.tag_id);

  const patched = await fetch(`${baseUrl}/api/audit-tags/${firstBody.tag.tag_id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      hg_session_id: hgSessionId,
      comment: 'looks wrong',
    }),
  }).then((r) => r.json());
  assert.equal(patched.tag.comment, 'looks wrong');

  const listed = await fetch(`${baseUrl}/api/sessions/${hgSessionId}/audit-tags`).then((r) => r.json());
  assert.equal(listed.tags.length, 1);

  const tagRoot = path.join(auditTagsRoot(process.env), hgSessionId, 'tags');
  assert.equal(fs.readdirSync(tagRoot).length, 1);
  assert.ok(tagRoot.startsWith(path.join(dataDir, 'audit_tags')));

  const sessionPath = path.join(sessionsDir, `${hgSessionId}.json`);
  const sessionJson = JSON.parse(fs.readFileSync(sessionPath, 'utf8'));
  const historyText = JSON.stringify(sessionJson.rp_history ?? []);
  assert.equal(historyText.includes('looks wrong'), false);
  assert.equal(historyText.includes('audit_tag'), false);
});

test('app server: untag allows re-tag and survives reload', async (t) => {
  const { sessionsDir } = makeTempDataEnv(t);
  const client = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { sessionsDir },
    env: process.env,
  });
  await client.start();
  t.after(() => client.stop());

  const server = createHolyGrailAppServer(client);
  const { baseUrl } = await server.listen(0);
  t.after(() => server.close());

  const created = await fetch(`${baseUrl}/api/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cast: ['Alice'] }),
  }).then((r) => r.json());
  const hgSessionId = created.session.hg_session_id;

  const turn = await fetch(`${baseUrl}/api/turns/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userMessage: 'Hello', ...MOCK_ROUND }),
  }).then((r) => r.json());
  const entryId = turn.transcript.find((item) => item.role === 'user').entry_id;

  const tagged = await fetch(`${baseUrl}/api/audit-tags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hg_session_id: hgSessionId, entry_id: entryId }),
  }).then((r) => r.json());

  await fetch(`${baseUrl}/api/audit-tags/${tagged.tag.tag_id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hg_session_id: hgSessionId }),
  });

  const retagged = await fetch(`${baseUrl}/api/audit-tags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hg_session_id: hgSessionId, entry_id: entryId }),
  }).then((r) => r.json());
  assert.equal(retagged.created, true);
  assert.notEqual(retagged.tag.tag_id, tagged.tag.tag_id);

  const reloadedClient = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { sessionsDir },
    env: process.env,
  });
  await reloadedClient.start();
  t.after(() => reloadedClient.stop());
  const tags = reloadedClient.listAuditTags(hgSessionId);
  assert.equal(tags.length, 1);
  assert.equal(tags[0].anchor.entry_id, entryId);
});

test('audit tags remain useful when execution evidence disabled', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  process.env.HG_EXECUTION_EVIDENCE = 'off';
  const port = 25765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  t.after(() => host.stop());

  const client = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { baseUrl: host.baseUrl, sessionsDir },
    env: process.env,
  });
  await client.start();
  t.after(() => client.stop());

  const session = await createTestSession(host.baseUrl, ['Alice']);
  await client.openSession(session.hg_session_id);
  await client.submitUserTurn({
    userMessage: 'Hello',
    ...MOCK_ROUND,
  });
  const history = await client.orchestrator._domainClient().getSessionHistory(session.hg_session_id);
  const presentationEntry = (history.entries ?? []).find((entry) => entry.kind === 'presentation')
    ?? (history.transcript ?? []).find((entry) => entry.role === 'assistant');
  assert.ok(presentationEntry?.entry_id);

  const result = await client.createAuditTag({
    hgSessionId: session.hg_session_id,
    entryId: presentationEntry.entry_id,
    createdBy: { surface: 'test', persona: 'Player' },
  });
  assert.equal(result.created, true);

  const evidenceRoot = path.join(dataDir, 'execution_evidence', session.hg_session_id);
  assert.equal(fs.existsSync(evidenceRoot), false);
  const tag = client.getAuditTag({ hgSessionId: session.hg_session_id, tagId: result.tag.tag_id });
  assert.equal(tag.anchor.entry_id, presentationEntry.entry_id);
});

test('audit tag joins to execution evidence when present', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  const evidenceStore = new ExecutionEvidenceStore(path.join(dataDir, 'execution_evidence'));
  const evidenceId = 'ev-tag-join';
  const hgSessionId = 'sess-evidence-join';
  const hgRoundId = 'round-join';
  const domainCommitId = 'commit-join';
  evidenceStore.writeAttempt({
    evidence_id: evidenceId,
    correlation: {
      evidence_id: evidenceId,
      hg_session_id: hgSessionId,
      hg_scene_id: hgSessionId,
      hg_round_id: hgRoundId,
      role: 'narrator',
      inference_id: 'inf-1',
      attempt_index: 0,
    },
    associations: { domain_commit_id: domainCommitId },
    request: { schema: 'hg_assembled_request_v1', contributions: [{ content: 'director-context' }] },
    response: { schema: 'hg_model_response_v1', assistant_text: 'rendered' },
  });

  const service = new AuditTagService({ root: path.join(dataDir, 'audit_tags') });
  const entries = [{
    entry_id: 'entry-join',
    sequence_index: 1,
    kind: 'presentation',
    content: 'rendered',
    actor_id: 'Alice',
    hg_round_id: hgRoundId,
    domain_commit_id: domainCommitId,
    presentation_status: 'succeeded',
    metadata: {},
  }];
  const { tag } = await service.createTag({
    hgSessionId,
    entryId: 'entry-join',
    getHistory: async () => ({ entries }),
    createdBy: { surface: 'test', persona: 'Player' },
  });

  const index = evidenceStore.readIndex(hgSessionId);
  const roundAttempts = index.rounds[hgRoundId] ?? [];
  assert.ok(roundAttempts.includes(evidenceId));
  const attempt = evidenceStore.readAttempt(hgSessionId, evidenceId);
  assert.equal(attempt.associations.domain_commit_id, domainCommitId);
  assert.equal(tag.anchor.domain_commit_id, domainCommitId);
  assert.equal(tag.anchor.hg_round_id, hgRoundId);
});
