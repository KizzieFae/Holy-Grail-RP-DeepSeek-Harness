import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { AuditTagService } from '../src/lib/audit-tags/service.mjs';
import { auditTagsRoot } from '../src/lib/audit-tags/config.mjs';
import {
  buildLibrarianMediationDecisionPatch,
  librarianOmittedCandidateId,
  NI_FORENSICS_CONTRACT,
} from '../src/lib/execution-evidence/ni-evidence.mjs';
import { createExecutionEvidenceRecorder } from '../src/lib/execution-evidence/recorder.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';

test('librarian mediation decision uses complete catalog without truncation', () => {
  const prepareResponse = {
    manifest_id: 'manifest-librarian-req-1',
    mediation_catalog: [
      { source_id: 'lmi:cand:fact-f' },
      { source_id: 'lmi:cand:fact-g' },
      { source_id: 'lmi:auth:scene:1' },
    ],
    retrieval_request_ids: ['rr-1'],
    retrieval_disposition: [{
      request_id: 'rr-1',
      candidate_ids_returned: ['fact-f', 'fact-g'],
      diagnostics: { budget_exhausted: 0 },
      retrieval_omitted: false,
    }],
  };
  const patch = buildLibrarianMediationDecisionPatch({
    prepareResponse,
    parsedResult: {
      selected_items: [{ source_id: 'lmi:cand:fact-g', relevance_rank: 1 }],
    },
    bundle: {
      bundle_id: 'bundle-1',
      mediation_mode: 'contextual_semantic',
      entries: [{
        entry_id: 'entry-1',
        provenance: { catalog_source_id: 'lmi:cand:fact-g' },
      }],
      budget_accounting: { entries_truncated: 0 },
      audit: { host_validation: { accepted: true } },
    },
    hostAccepted: true,
  });
  assert.equal(patch.decision.librarian_mediation.catalog_source_ids.length, 3);
  assert.deepEqual(patch.decision.librarian_mediation.selected_source_ids, ['lmi:cand:fact-g']);
  assert.equal(
    librarianOmittedCandidateId(
      patch.decision.librarian_mediation.catalog_source_ids,
      patch.decision.librarian_mediation.selected_source_ids,
      'fact-f',
    ),
    'fact-f',
  );
  assert.equal(
    librarianOmittedCandidateId(
      patch.decision.librarian_mediation.catalog_source_ids,
      patch.decision.librarian_mediation.selected_source_ids,
      'fact-g',
    ),
    null,
  );
});

test('NI evidence contract and index rebuild', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-ni-index-'));
  const store = new ExecutionEvidenceStore(root);
  const recorder = createExecutionEvidenceRecorder({ enabled: true, root });
  const hgSessionId = 'sess-ni-1';
  const evidenceId = 'evidence-ni-1';
  store.writeAttempt({
    evidence_id: evidenceId,
    evidence_contract: NI_FORENSICS_CONTRACT,
    correlation: {
      hg_session_id: hgSessionId,
      hg_round_id: 'round-1',
      inference_id: 'inf-char-1',
      parent_inference_id: 'inf-char-1',
      inference_kind: 'character_orientation',
      role: 'character',
    },
    request: {},
    response: {},
    decision: null,
    associations: {},
  });
  recorder.linkNiAssociation(hgSessionId, evidenceId, 'evidence-ni-2', {
    leftKey: 'mediation_evidence_id',
    rightKey: 'orientation_evidence_id',
  });
  const index = store.rebuildSemanticNavigationIndexes(hgSessionId);
  assert.equal(index.ni.evidence_contract, NI_FORENSICS_CONTRACT);
  assert.equal(
    index.ni.by_round['round-1']['inf-char-1'].character_orientation,
    evidenceId,
  );
  fs.rmSync(root, { recursive: true, force: true });
});

test('audit tag creation succeeds when evidence disabled', async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-tag-ni-'));
  const previous = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
    HG_AUDIT_TAGS_DIR: process.env.HG_AUDIT_TAGS_DIR,
  };
  process.env.HG_DATA_DIR = dataDir;
  process.env.HG_EXECUTION_EVIDENCE = 'off';
  process.env.HG_AUDIT_TAGS_DIR = path.join(dataDir, 'audit_tags');
  const service = new AuditTagService();
  const entry = {
    entry_id: 'entry-1',
    sequence_index: 1,
    kind: 'presentation',
    hg_round_id: 'round-1',
    domain_commit_id: 'commit-1',
    actor_id: 'Narrator',
  };
  const result = await service.createTag({
    hgSessionId: 'sess-1',
    entryId: 'entry-1',
    getHistory: async () => ({ entries: [entry] }),
  });
  assert.equal(result.created, true);
  assert.equal(result.tag.forensic_scope.resolution_status, 'evidence_disabled');
  assert.equal(result.tag.anchor.entry_id, 'entry-1');
  for (const [key, value] of Object.entries(previous)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  fs.rmSync(dataDir, { recursive: true, force: true });
});

test('scenario-grade F/G lineage proof on mediation evidence', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-ni-fg-'));
  const store = new ExecutionEvidenceStore(root);
  const hgSessionId = 'sess-fg';
  const prepareResponse = {
    manifest_id: 'manifest-librarian-fg',
    request_id: 'kar-fg',
    mediation_catalog: [
      { source_id: 'lmi:cand:fact-f' },
      { source_id: 'lmi:cand:fact-g' },
    ],
    retrieval_request_ids: ['rr-fg'],
    retrieval_disposition: [{
      request_id: 'rr-fg',
      candidate_ids_returned: ['fact-f', 'fact-g'],
      diagnostics: { candidate_count_returned: 2, budget_exhausted: 0 },
    }],
    contributions: [{
      contribution_id: 'manifest-librarian-fg-catalog',
      knowledge_ids: ['lmi:cand:fact-f', 'lmi:cand:fact-g'],
      content: 'Eligible mediation catalog',
      provenance: { catalog_count: 2 },
    }],
  };
  const mediationResult = {
    selected_items: [{ source_id: 'lmi:cand:fact-g', relevance_rank: 1 }],
  };
  const bundle = {
    bundle_id: 'bundle-fg',
    mediation_mode: 'contextual_semantic',
    entries: [{
      entry_id: 'entry-g',
      provenance: { catalog_source_id: 'lmi:cand:fact-g' },
      ref: { display_hint: 'lmi:cand:fact-g' },
      content: 'Fact G visible',
    }],
    budget_accounting: { entries_truncated: 0 },
    audit: { host_validation: { accepted: true, rejection_codes: [] } },
  };
  const evidenceId = 'ev-fg-mediation';
  const patch = buildLibrarianMediationDecisionPatch({
    prepareResponse,
    parsedResult: mediationResult,
    bundle,
    hostAccepted: true,
  });
  store.writeAttempt({
    evidence_id: evidenceId,
    evidence_contract: NI_FORENSICS_CONTRACT,
    correlation: {
      hg_session_id: hgSessionId,
      hg_round_id: 'round-fg',
      inference_kind: 'librarian_mediation',
      role: 'librarian',
    },
    request: {
      contributions: prepareResponse.contributions,
    },
    response: { assistant_text: '{}' },
    decision: patch.decision,
    associations: {},
  });
  const attempt = store.readAttempt(hgSessionId, evidenceId);
  const med = attempt.decision.librarian_mediation;
  assert.ok(med.catalog_source_ids.includes('lmi:cand:fact-f'));
  assert.ok(med.catalog_source_ids.includes('lmi:cand:fact-g'));
  assert.deepEqual(med.selected_source_ids, ['lmi:cand:fact-g']);
  assert.equal(librarianOmittedCandidateId(med.catalog_source_ids, med.selected_source_ids, 'fact-f'), 'fact-f');
  assert.equal(med.source_id_to_entry_id['lmi:cand:fact-g'], 'entry-g');
  assert.ok(med.retrieval_disposition[0].candidate_ids_returned.includes('fact-f'));
  fs.rmSync(root, { recursive: true, force: true });
});
