import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { deriveObligationSignals } from '../src/lib/a2-obligation-dispatch.mjs';
import { runA2IndexedRetrievalStep, clearIndexedRetrievalProbeCache } from '../src/lib/a2-indexed-retrieval.mjs';
import {
  validateCorpusIntegrity,
  runRetrievalProbe,
  buildK3SevenStageChecklist,
  adjudicateK6Stages,
  buildCapabilityMatrix,
  exportCapabilityMatrixMarkdown,
  detectTier1Failures,
  buildBlindPacket,
  validateBlindPacketIntegrity,
  createLibrarianLedgerEntry,
  loadPolicies,
  loadTruthManifest,
  runValidateApparatus,
} from '../scripts/lib/issue201-g3e-lib.mjs';

test('G3-E corpus integrity and reproducibility', () => {
  const corpus = validateCorpusIntegrity();
  assert.ok(corpus.record_count >= 280 && corpus.record_count <= 320);
  assert.equal(corpus.truth_manifest_valid, true);
  assert.equal(corpus.sha_matches_manifest, true);
  assert.equal(corpus.reproducible_rebuild, true);
});

test('G3-E retrieval probe returns all K cases', () => {
  clearIndexedRetrievalProbeCache();
  const probe = runRetrievalProbe();
  assert.equal(probe.cases.length, 7);
  const k3 = probe.cases.find((row) => row.case_id === 'K3');
  assert.ok(k3);
  assert.ok((k3.forensic_chain?.entitlement_decision?.entitlement_rejection_count ?? 0) > 0);
  assert.equal(k3.eligible_record_ids.includes('g3e-private-kizzie-debt'), false);
});

test('G3-E K3 seven-stage forensic chain (mock stages 6-7)', () => {
  const truth = loadTruthManifest();
  const probe = runRetrievalProbe();
  const k3Probe = probe.cases.find((row) => row.case_id === 'K3');
  const checklist = buildK3SevenStageChecklist({
    truth,
    probeCase: k3Probe,
    mockForensics: { forbidden_in_character_manifest: true, forbidden_in_presentation: true },
  });
  assert.equal(checklist.all_production_stages_pass, true);
  assert.equal(checklist.apparatus_mock_stages_pass, true);
});

test('G3-E K6 R/P/C/S/M independently reportable', () => {
  const probe = runRetrievalProbe();
  const policy = loadPolicies().find((p) => p.case_id === 'K6');
  const k6Probe = probe.cases.find((row) => row.case_id === 'K6');
  const k6 = adjudicateK6Stages({
    probeCase: k6Probe,
    policy,
    mockMove: { text: 'Guests overnight need lease clause and witness notification.' },
    mockPresentation: 'Ayame explains guest and witness rules.',
  });
  assert.equal(k6.independently_reportable, true);
  assert.equal(k6.stages['K6-R'].pass, true);
  assert.equal(typeof k6.stages['K6-P'].pass, 'boolean');
  assert.equal(k6.stages['K6-C'].mode, 'mock');
  assert.notEqual(k6.stages['K6-M'], undefined);
});

test('G3-E A2 indexed retrieval wiring and librarian absence', () => {
  const dispatch = deriveObligationSignals({
    scenarioKey: 'ayame_archive_interview',
    eligibleActors: ['ayame'],
    roleAssignments: { ayame: 'host' },
    retrievalManifestGap: true,
  });
  assert.ok(dispatch.authorizations.includes('indexed_retrieval'));
  assert.ok(dispatch.not_authorized.includes('default_librarian_mediation'));
  const step = runA2IndexedRetrievalStep({ caseId: 'K1', viewerCharacterId: 'ayame' });
  assert.equal(step.ok, true);
  assert.equal(step.librarian_invocation_count, 0);
});

test('G3-E capability matrix has no aggregate pass rate', () => {
  const probe = runRetrievalProbe();
  const matrix = buildCapabilityMatrix({ probe });
  assert.equal(matrix.aggregate_pass_rate, null);
  assert.equal(matrix.rows.length, 14);
  const md = exportCapabilityMatrixMarkdown(matrix);
  assert.match(md, /No aggregate X\/7/);
});

test('G3-E blind packet strips architecture labels', () => {
  const packet = buildBlindPacket({
    samples: [{
      case_id: 'K1',
      presentation_text: 'sample',
      dimensions_template: ['coherence'],
    }],
    answerKey: { K1: { arm: 'a2_indexed_retrieval' } },
  });
  const integrity = validateBlindPacketIntegrity(packet);
  assert.equal(integrity.labels_stripped, true);
  assert.equal(integrity.answer_key_present, true);
});

test('G3-E Tier-1 detector flags leakage', () => {
  const clear = detectTier1Failures({
    forbiddenIds: ['g3e-private-kizzie-debt'],
    projectedIds: [],
    manifestIds: [],
    presentationText: '',
  });
  assert.equal(clear.tier1_clear, true);
  const leak = detectTier1Failures({
    forbiddenIds: ['g3e-private-kizzie-debt'],
    projectedIds: ['g3e-private-kizzie-debt'],
    manifestIds: [],
    presentationText: '',
  });
  assert.equal(leak.tier1_clear, false);
});

test('G3-E librarian ledger schema', () => {
  const entry = createLibrarianLedgerEntry({
    cost: { input_tokens: 10 },
    informationSupplied: ['g3e-lease-guests'],
    consumer: 'character_packaging',
    decisionChanged: false,
    observableBenefit: null,
    classification: 'unused',
  });
  assert.equal(entry.causal_claim_from_instrumentation_only, false);
});

test('G3-E validate-apparatus smoke writes artifacts', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'g3e-app-'));
  const report = runValidateApparatus({ outputDir: tmp });
  assert.equal(report.live_campaign_executed, false);
  assert.ok(fs.existsSync(path.join(tmp, 'capability-matrix.md')));
});
