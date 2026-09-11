import assert from 'node:assert/strict';
import test from 'node:test';

import { findCatalogEntry } from '../src/application/llm-call-catalog.mjs';
import { runInferenceWithContractCorrection } from '../src/lib/contract-correction-substrate.mjs';
import {
  LIBRARIAN_MEDIATION_CORRECTION_KIND,
  LIBRARIAN_MEDIATION_RESULT_SCHEMA,
  buildLibrarianMediationCorrectionPrompt,
  buildLibrarianMediationPrompt,
  parseLibrarianMediationResult,
} from '../src/lib/librarian-mediation-envelope.mjs';
import {
  contractRequiredSelectedItemFields,
  librarianMediationContractPromptLines,
} from '../src/lib/librarian-mediation-inference-contract.mjs';
import { buildLibrarianMediationDecisionPatch } from '../src/lib/execution-evidence/ni-evidence.mjs';
import { runLibrarianMediation } from '../src/lib/librarian-mediation-substrate.mjs';

const SOURCE_A = 'lmi:cand:source-a';
const SOURCE_B = 'lmi:cand:source-b';
const CATALOG = new Set([SOURCE_A, SOURCE_B]);
const PARSE_CONTEXT = { catalogIds: CATALOG, sampleSourceId: SOURCE_A };

function validMediation(overrides = {}) {
  return JSON.stringify({
    schema: LIBRARIAN_MEDIATION_RESULT_SCHEMA,
    selected_items: [
      {
        source_id: SOURCE_A,
        relevance_rank: 1,
        relevance_band: 'high',
        interpretive_status: 'likely',
        salience_note: 'Answers the focus question.',
        answers_focus_questions: ['What is present?'],
      },
    ],
    synthesis_entries: [
      {
        synthesis_id: 'synth-1',
        synthesis_kind: 'summary',
        content: 'Bounded synthesis.',
        source_ids: [SOURCE_A],
      },
    ],
    ...overrides,
  });
}

const MALFORMED_RANK = JSON.stringify({
  schema: LIBRARIAN_MEDIATION_RESULT_SCHEMA,
  selected_items: [{ source_id: SOURCE_A, rank: 1, relevance: 'note' }],
});

const MALFORMED_SYNTHESIS = JSON.stringify({
  schema: LIBRARIAN_MEDIATION_RESULT_SCHEMA,
  selected_items: [{ source_id: SOURCE_A, relevance_rank: 1 }],
  synthesis: [{ summary: 'wrong shape', source_ids: [SOURCE_A] }],
});

test('buildLibrarianMediationPrompt includes authoritative contract fields', () => {
  const prompt = buildLibrarianMediationPrompt(PARSE_CONTEXT);
  assert.match(prompt, /relevance_rank/);
  assert.match(prompt, /synthesis_entries/);
  assert.match(prompt, /selected_items\[\]\.rank/);
});

test('parseLibrarianMediationResult rejects rank alias', () => {
  const parsed = parseLibrarianMediationResult(MALFORMED_RANK, CATALOG);
  assert.equal(parsed.ok, false);
  assert.match(String(parsed.error), /relevance_rank/);
});

test('contractRequiredSelectedItemFields includes relevance_rank from JSON artifact', () => {
  assert.deepEqual(contractRequiredSelectedItemFields(), ['source_id', 'relevance_rank']);
});

test('runInferenceWithContractCorrection recovers rank malformed primary', async () => {
  let callCount = 0;
  const inference = await runInferenceWithContractCorrection({
    runEphemeralInference: async ({ evidenceContext }) => {
      callCount += 1;
      const kind = evidenceContext?.inferenceKind ?? 'primary';
      const raw = kind === LIBRARIAN_MEDIATION_CORRECTION_KIND
        ? validMediation()
        : MALFORMED_RANK;
      return {
        failed: false,
        raw,
        evidenceId: `ev-${kind}-${callCount}`,
      };
    },
    primaryInferenceId: 'inf-mediation-primary',
    primaryInferenceKind: 'librarian_mediation',
    correctionInferenceKind: LIBRARIAN_MEDIATION_CORRECTION_KIND,
    buildPrimaryPrompt: () => buildLibrarianMediationPrompt(PARSE_CONTEXT),
    buildCorrectionPrompt: buildLibrarianMediationCorrectionPrompt,
    parseFn: (raw, ctx) => parseLibrarianMediationResult(raw, ctx.catalogIds),
    parseContext: PARSE_CONTEXT,
    manifest: { manifest_id: 'manifest-mediation', contributions: [] },
    maxCorrections: 1,
  });

  assert.equal(callCount, 2);
  assert.equal(inference.ok, true);
  assert.equal(inference.correctionUsed, true);
  assert.equal(inference.lineage?.primary?.parse_error, 'selected_items[0].relevance_rank');
});

test('runInferenceWithContractCorrection fails closed after malformed correction', async () => {
  let callCount = 0;
  const inference = await runInferenceWithContractCorrection({
    runEphemeralInference: async ({ evidenceContext }) => {
      callCount += 1;
      const kind = evidenceContext?.inferenceKind ?? 'primary';
      const raw = MALFORMED_RANK;
      return {
        failed: false,
        raw,
        evidenceId: `ev-${kind}-${callCount}`,
      };
    },
    primaryInferenceId: 'inf-mediation-primary-fail',
    primaryInferenceKind: 'librarian_mediation',
    correctionInferenceKind: LIBRARIAN_MEDIATION_CORRECTION_KIND,
    buildPrimaryPrompt: () => buildLibrarianMediationPrompt(PARSE_CONTEXT),
    buildCorrectionPrompt: buildLibrarianMediationCorrectionPrompt,
    parseFn: (raw, ctx) => parseLibrarianMediationResult(raw, ctx.catalogIds),
    parseContext: PARSE_CONTEXT,
    manifest: { manifest_id: 'manifest-mediation', contributions: [] },
    maxCorrections: 1,
  });

  assert.equal(callCount, 2);
  assert.equal(inference.ok, false);
  assert.equal(inference.correctionUsed, true);
});

test('structurally valid primary does not invoke correction', async () => {
  let callCount = 0;
  const inference = await runInferenceWithContractCorrection({
    runEphemeralInference: async () => {
      callCount += 1;
      return { failed: false, raw: validMediation(), evidenceId: 'ev-primary-only' };
    },
    primaryInferenceId: 'inf-mediation-valid',
    primaryInferenceKind: 'librarian_mediation',
    correctionInferenceKind: LIBRARIAN_MEDIATION_CORRECTION_KIND,
    buildPrimaryPrompt: () => buildLibrarianMediationPrompt(PARSE_CONTEXT),
    buildCorrectionPrompt: buildLibrarianMediationCorrectionPrompt,
    parseFn: (raw, ctx) => parseLibrarianMediationResult(raw, ctx.catalogIds),
    parseContext: PARSE_CONTEXT,
    manifest: { manifest_id: 'manifest-mediation', contributions: [] },
    maxCorrections: 1,
  });

  assert.equal(callCount, 1);
  assert.equal(inference.correctionUsed, false);
  assert.equal(inference.ok, true);
});

test('buildLibrarianMediationDecisionPatch records contract lineage separately from host acceptance', () => {
  const patch = buildLibrarianMediationDecisionPatch({
    prepareResponse: { mediation_catalog: [{ source_id: SOURCE_A }] },
    parsedResult: { selected_items: [{ source_id: SOURCE_A, relevance_rank: 1 }] },
    bundle: {
      mediation_mode: 'deterministic_fallback',
      audit: { host_validation: { accepted: false, rejection_codes: ['empty_selection'] } },
    },
    hostAccepted: false,
    hostRejectionCodes: ['empty_selection'],
    contractLineage: {
      correction_used: true,
      primary_parse_error: 'selected_items[0].relevance_rank',
      correction_evidence_id: 'ev-corr',
    },
    structuralParseError: null,
    mediationGenerationStage: 'contract_correction',
    primaryRawSelectedCount: 7,
  });
  assert.equal(patch.decision.librarian_mediation.contract_correction_used, true);
  assert.equal(patch.decision.librarian_mediation.host_accepted, false);
  assert.equal(patch.decision.librarian_mediation.primary_raw_selected_count, 7);
  assert.equal(patch.decision.librarian_mediation.mediation_generation_stage, 'contract_correction');
});

test('shared catalog entries route Storyteller Narrator Character through runLibrarianMediation', () => {
  for (const callId of [
    'librarian_mediation@character',
    'librarian_mediation@narrator',
  ]) {
    const entry = findCatalogEntry(callId);
    assert.equal(entry.owner_export, 'runLibrarianMediation');
    assert.equal(entry.canonical_inference_kind, 'librarian_mediation');
  }
});

test('runLibrarianMediation integrates correction before finalize', async () => {
  let finalizeFallbackArg = null;
  const prepareResponse = {
    request_id: 'req-test',
    manifest_id: 'manifest-test',
    mediation_catalog: [{ source_id: SOURCE_A }, { source_id: SOURCE_B }],
    contributions: [],
    retrieval_request_ids: [],
    retrieval_disposition: [],
  };
  const result = await runLibrarianMediation({
    domainApi: {
      prepareLibrarianMediationContext: async () => prepareResponse,
      finalizeLibrarianMediation: async (payload) => {
        finalizeFallbackArg = payload.allow_deterministic_fallback;
        return {
          bundle_id: 'bundle-1',
          mediation_mode: payload.mediation_result ? 'contextual_semantic' : 'deterministic_fallback',
          audit: { host_validation: { accepted: true, rejection_codes: [] } },
          entries: [],
        };
      },
    },
    hgSceneId: 'scene-1',
    inferenceId: 'inf-storyteller-mediation',
    knowledgeAccessRequest: { request_id: 'req-test' },
    runEphemeralInference: async ({ evidenceContext }) => ({
      failed: false,
      raw: evidenceContext?.inferenceKind === LIBRARIAN_MEDIATION_CORRECTION_KIND
        ? validMediation()
        : MALFORMED_RANK,
      evidenceId: `ev-${evidenceContext?.inferenceKind ?? 'primary'}`,
    }),
    allowDeterministicFallback: true,
  });

  assert.equal(finalizeFallbackArg, true);
  assert.equal(result.contractLineage?.correction_used, true);
  assert.equal(result.structuralParseSucceeded, true);
  assert.ok(result.bundle);
});

test('runLibrarianMediation preserves Character allowDeterministicFallback false', async () => {
  let finalizeFallbackArg = null;
  const result = await runLibrarianMediation({
    domainApi: {
      prepareLibrarianMediationContext: async () => ({
        request_id: 'req-char',
        manifest_id: 'manifest-char',
        mediation_catalog: [{ source_id: SOURCE_A }],
        contributions: [],
        retrieval_request_ids: [],
        retrieval_disposition: [],
      }),
      finalizeLibrarianMediation: async (payload) => {
        finalizeFallbackArg = payload.allow_deterministic_fallback;
        return {
          bundle_id: null,
          mediation_mode: 'authoritative_only',
          audit: { host_validation: { accepted: false, rejection_codes: [] } },
          entries: [],
        };
      },
    },
    hgSceneId: 'scene-1',
    inferenceId: 'inf-character-mediation-policy',
    knowledgeAccessRequest: { request_id: 'req-char' },
    runEphemeralInference: async ({ evidenceContext }) => ({
      failed: false,
      raw: evidenceContext?.inferenceKind === LIBRARIAN_MEDIATION_CORRECTION_KIND
        ? MALFORMED_RANK
        : MALFORMED_RANK,
      evidenceId: `ev-${evidenceContext?.inferenceKind ?? 'primary'}`,
    }),
    allowDeterministicFallback: false,
  });

  assert.equal(finalizeFallbackArg, false);
  assert.equal(result.ok, false);
});

test('structurally valid primary with Host rejection does not invoke correction', async () => {
  let inferenceCalls = 0;
  const result = await runLibrarianMediation({
    domainApi: {
      prepareLibrarianMediationContext: async () => ({
        request_id: 'req-host-reject',
        manifest_id: 'manifest-host-reject',
        mediation_catalog: [{ source_id: SOURCE_A }],
        contributions: [],
        retrieval_request_ids: [],
        retrieval_disposition: [],
      }),
      finalizeLibrarianMediation: async () => ({
        bundle_id: 'bundle-host-reject',
        mediation_mode: 'deterministic_fallback',
        audit: {
          host_validation: {
            accepted: false,
            reason: 'mediation_result_rejected',
            rejection_codes: ['empty_selection'],
          },
        },
        entries: [],
      }),
    },
    hgSceneId: 'scene-1',
    inferenceId: 'inf-host-reject',
    knowledgeAccessRequest: { request_id: 'req-host-reject' },
    runEphemeralInference: async () => {
      inferenceCalls += 1;
      return { failed: false, raw: validMediation({ selected_items: [] }), evidenceId: 'ev-primary' };
    },
    allowDeterministicFallback: true,
  });

  assert.equal(inferenceCalls, 1);
  assert.equal(result.contractLineage?.correction_used, false);
  assert.equal(result.structuralParseSucceeded, true);
  assert.equal(result.hostAccepted, false);
});

test('librarianMediationContractPromptLines aligns with parser-required selected item fields', () => {
  const lines = librarianMediationContractPromptLines(PARSE_CONTEXT).join('\n');
  for (const field of contractRequiredSelectedItemFields()) {
    assert.match(lines, new RegExp(field));
  }
});
