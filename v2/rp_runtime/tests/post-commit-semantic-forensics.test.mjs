import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { ExecutionEvidenceRecorder } from '../src/lib/execution-evidence/recorder.mjs';
import {
  buildLibrarianProposalDecisionPatch,
  buildPostCommitSemanticDecisionPatch,
  resolvePostCommitSemanticDecision,
} from '../src/lib/execution-evidence/ni-evidence.mjs';

test('canonical post-commit semantic decision patch writes post_commit_semantic only', () => {
  const patch = buildPostCommitSemanticDecisionPatch({
    batch: {
      batch_id: 'batch-1',
      domain_commit_id: 'commit-1',
      orchestration_status: 'finalized',
      host_validation: { accepted: true, rejection_codes: [] },
      continuity_decision: { accepted_count: 1, rejected_count: 0 },
      durable_mutation_applied: true,
    },
  });
  assert.ok(patch.decision.post_commit_semantic);
  assert.equal(patch.decision.librarian_proposal, undefined);
  assert.equal(patch.decision.post_commit_semantic.semantic_producer_role, 'storyteller');
});

test('legacy decision patch remains readable', () => {
  const patch = buildLibrarianProposalDecisionPatch({
    batch: { batch_id: 'legacy-batch', host_validation: { accepted: true, rejection_codes: [] } },
  });
  const resolved = resolvePostCommitSemanticDecision({
    librarian_proposal: patch.decision.librarian_proposal,
  });
  assert.equal(resolved.batch_id, 'legacy-batch');
});

test('deterministic disposition evidence is not indexed as inference utilization', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-disposition-'));
  const recorder = new ExecutionEvidenceRecorder({ enabled: true, root });
  const hgSessionId = 'hg-session-disposition-1';
  const evidenceId = recorder.recordPostCommitSemanticDisposition({
    hgSessionId,
    domainCommitId: 'commit-skip-1',
    hgRoundId: 'round-1',
    continuityTurnIndex: 1,
    postCommitSemanticInferenceId: 'semantic-inf-1',
    batch: { batch_id: 'batch-skip-1', request_id: 'req-1' },
    eligibilityOutcome: 'no_eligible_active_issues',
  });
  assert.ok(evidenceId);
  const attempt = recorder.readAttempt(hgSessionId, evidenceId);
  assert.equal(attempt.correlation.role, 'post_commit_semantic_disposition');
  assert.equal(attempt.correlation.record_class, 'deterministic_disposition');
  assert.equal(attempt.request, null);
  assert.equal(attempt.response, null);
  assert.equal(attempt.inference_health, undefined);
  assert.equal(attempt.evidence_contract, undefined);

  const index = recorder.readIndex(hgSessionId);
  const commitBucket = index.ni.by_commit['commit-skip-1'];
  assert.equal(commitBucket.semantic_disposition_evidence_id, evidenceId);
  assert.equal(commitBucket.proposal_evidence_id, undefined);
  const roundActivity = index.round_activity['round-1'];
  assert.ok(roundActivity);
  assert.equal(roundActivity.inference_kinds.post_commit_semantic_disposition, undefined);
});
