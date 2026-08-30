import assert from 'node:assert/strict';
import test from 'node:test';

import { runInferenceWithContractCorrection } from '../src/lib/contract-correction-substrate.mjs';
import {
  LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
  buildLibrarianProposalCorrectionPrompt,
  buildLibrarianProposalPrompt,
  parseLibrarianProposalResult,
} from '../src/lib/librarian-proposal-envelope.mjs';
import { runLibrarianProposalGeneration } from '../src/lib/librarian-proposal-substrate.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { makeTempSessionsDir, reserveLocalPort, startDomainApi } from './helpers/domain-api.mjs';

const COMMIT_ID = 'commit-contract-test-1';
const CATALOG = new Set([`committed_move:${COMMIT_ID}`]);
const PARSE_CONTEXT = {
  catalogIds: CATALOG,
  sampleAnchorId: `committed_move:${COMMIT_ID}`,
  domainCommitId: COMMIT_ID,
};

function validProposal(overrides = {}) {
  return JSON.stringify({
    schema: LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
    proposals: [
      {
        proposal_id: 'prop-valid-1',
        proposal_kind: 'information_salience',
        derivation_summary: 'Committed move advances the scene.',
        confidence: 'likely',
        evidence_anchors: [
          {
            anchor_id: `committed_move:${COMMIT_ID}`,
            evidence_kind: 'committed_move',
            anchor_commit_id: COMMIT_ID,
          },
        ],
        proposed_payload: {
          subject_ref: `commit:${COMMIT_ID}`,
          salience_level: 'major',
        },
        ...overrides,
      },
    ],
  });
}

const HISTORICAL_MALFORMED = JSON.stringify({
  request_id: 'hist-req-1',
  proposals: [
    {
      change_kind: 'information_salience',
      target: 'scene',
      confidence: 'likely',
      evidence_anchors: [`committed_move:${COMMIT_ID}`],
    },
  ],
});

test('buildLibrarianProposalPrompt includes canonical contract fields', () => {
  const prompt = buildLibrarianProposalPrompt(PARSE_CONTEXT);
  assert.match(prompt, /hg_librarian_proposal_result_v1/);
  assert.match(prompt, /proposal_kind/);
  assert.match(prompt, /proposed_payload/);
  assert.match(prompt, /change_kind/);
  assert.match(prompt, /evidence_anchors/);
});

test('parseLibrarianProposalResult accepts valid grounded proposal', () => {
  const parsed = parseLibrarianProposalResult(validProposal(), CATALOG);
  assert.equal(parsed.ok, true);
});

test('parseLibrarianProposalResult rejects malformed JSON', () => {
  const parsed = parseLibrarianProposalResult('{not-json', CATALOG);
  assert.equal(parsed.ok, false);
});

test('parseLibrarianProposalResult rejects wrong schema identifier', () => {
  const parsed = parseLibrarianProposalResult(
    JSON.stringify({ schema: 'wrong_schema_v1', proposals: [] }),
    CATALOG,
  );
  assert.equal(parsed.error, 'schema_mismatch');
});

test('parseLibrarianProposalResult rejects missing required fields', () => {
  const parsed = parseLibrarianProposalResult(
    JSON.stringify({
      schema: LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
      proposals: [{ proposal_kind: 'information_salience' }],
    }),
    CATALOG,
  );
  assert.equal(parsed.ok, false);
});

test('parseLibrarianProposalResult rejects invalid enum values', () => {
  const parsed = parseLibrarianProposalResult(
    JSON.stringify({
      schema: LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
      proposals: [
        {
          proposal_kind: 'not_a_real_kind',
          derivation_summary: 'x',
          confidence: 'likely',
          evidence_anchors: [{ anchor_id: `committed_move:${COMMIT_ID}`, evidence_kind: 'committed_move' }],
          proposed_payload: { subject_ref: 'x', salience_level: 'major' },
        },
      ],
    }),
    CATALOG,
  );
  assert.match(String(parsed.error), /proposal_kind/);
});

test('parseLibrarianProposalResult accepts empty proposals array', () => {
  const parsed = parseLibrarianProposalResult(
    JSON.stringify({ schema: LIBRARIAN_PROPOSAL_RESULT_SCHEMA, proposals: [] }),
    CATALOG,
  );
  assert.equal(parsed.ok, true);
  assert.equal(parsed.result.proposals.length, 0);
});

test('contract correction repairs historical malformed shape with exactly one extra attempt', async () => {
  const calls = [];
  const inference = await runInferenceWithContractCorrection({
    runEphemeralInference: async (args) => {
      calls.push(args.inferenceId);
      return {
        evidenceId: `ev-${calls.length}`,
        raw: calls.length === 1 ? HISTORICAL_MALFORMED : validProposal(),
        failed: false,
        trace: { finish: { kind: 'stop' } },
      };
    },
    primaryInferenceId: 'inf-lib-primary',
    primaryInferenceKind: 'librarian_proposal',
    correctionInferenceKind: 'librarian_proposal_contract_correction',
    buildPrimaryPrompt: () => buildLibrarianProposalPrompt(PARSE_CONTEXT),
    buildCorrectionPrompt: buildLibrarianProposalCorrectionPrompt,
    parseFn: (raw, ctx) => parseLibrarianProposalResult(raw, ctx.catalogIds),
    parseContext: PARSE_CONTEXT,
    manifest: { contributions: [] },
    maxCorrections: 1,
  });
  assert.equal(calls.length, 2);
  assert.equal(inference.ok, true);
  assert.equal(inference.correctionUsed, true);
  assert.equal(inference.inferRuns.length, 2);
});

test('contract correction stops after second malformed response', async () => {
  const inference = await runInferenceWithContractCorrection({
    runEphemeralInference: async () => ({
      evidenceId: 'ev',
      raw: HISTORICAL_MALFORMED,
      failed: false,
      trace: { finish: { kind: 'stop' } },
    }),
    primaryInferenceId: 'inf-lib-fail',
    primaryInferenceKind: 'librarian_proposal',
    correctionInferenceKind: 'librarian_proposal_contract_correction',
    buildPrimaryPrompt: () => buildLibrarianProposalPrompt(PARSE_CONTEXT),
    buildCorrectionPrompt: buildLibrarianProposalCorrectionPrompt,
    parseFn: (raw, ctx) => parseLibrarianProposalResult(raw, ctx.catalogIds),
    parseContext: PARSE_CONTEXT,
    manifest: { contributions: [] },
    maxCorrections: 1,
  });
  assert.equal(inference.ok, false);
  assert.equal(inference.correctionUsed, true);
  assert.equal(inference.inferRuns.length, 2);
});

test('host semantic rejection does not trigger contract correction', async (t) => {
  const calls = [];
  const port = await reserveLocalPort();
  const host = await startDomainApi(port, { t });
  const api = createDomainApiClient(host.baseUrl);
  const session = await api.createSession({ cast: ['Alice'] });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  const validation = await api.validateDirectorDecision({
    hg_scene_id: session.hg_scene_id,
    hg_round_id: round.hg_round_id,
    inference_id: 'inf-dir-72',
    turn_index: 0,
    attempt_index: 0,
    proposed_decision: {
      next_actor: 'Alice',
      end_round: false,
      reason: 'Alice acts.',
      environment_event: '',
      tension_shift: 'steady',
    },
  });
  const commit = await api.commitMove({
    inference_id: 'inf-commit-72',
    hg_scene_id: session.hg_scene_id,
    hg_round_id: round.hg_round_id,
    character_id: 'Alice',
    validated_move: {
      move_schema_version: 2,
      beats: [{ type: 'action', action: 'checks the latch' }],
      motivation: { goal: 'inspect', tactic: 'check', emotional_driver: 'wary', risk_level: 'low' },
      semantic_evaluation: { decision: 'no_covered_change' },
    },
    director_decision: validation.normalized_decision,
    expected_turn_index: 0,
  });
  const commitId = commit.domain_commit_id;
  const semanticallyInvalid = JSON.stringify({
    schema: LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
    proposals: [
      {
        proposal_kind: 'information_salience',
        derivation_summary: 'Manufactured fact attempt.',
        confidence: 'likely',
        evidence_anchors: [
          {
            anchor_id: `committed_move:${commitId}`,
            evidence_kind: 'committed_move',
            anchor_commit_id: commitId,
          },
        ],
        proposed_payload: {
          subject_ref: `commit:${commitId}`,
          salience_level: 'major',
          manufactured_fact: true,
        },
      },
    ],
  });
  const result = await runLibrarianProposalGeneration({
    domainApi: api,
    hgSceneId: session.hg_scene_id,
    inferenceId: 'inf-librarian-72-host-reject',
    proposalContextRequest: {
      request_id: 'req-72-host-reject',
      hg_scene_id: session.hg_scene_id,
      hg_round_id: round.hg_round_id,
      turn_index: commit.continuity_turn_index,
      domain_commit_id: commitId,
      librarian_inference_id: 'inf-librarian-72-host-reject',
      visibility_envelope: {
        viewer_role: 'host_internal',
        authority_ceiling_enforced: 'derived',
      },
    },
    runEphemeralInference: async (args) => {
      calls.push(args.inferenceId);
      return {
        evidenceId: `ev-${calls.length}`,
        raw: semanticallyInvalid,
        failed: false,
        trace: { finish: { kind: 'stop' } },
      };
    },
    mockResponse: semanticallyInvalid,
  });
  await host.stop();
  assert.equal(calls.length, 1);
  assert.equal(result.ok, true);
  assert.equal(result.batch?.degradation_mode, 'host_validation_failed');
  assert.equal(result.correctionUsed, false);
});

test('structural parse failure is classified separately from provider inference failure', async (t) => {
  const port = await reserveLocalPort();
  const host = await startDomainApi(port, { t });
  const api = createDomainApiClient(host.baseUrl);

  async function commitAlice(prefix) {
    const session = await api.createSession({ cast: ['Alice'], hg_session_id: `sess-${prefix}` });
    const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
    const validation = await api.validateDirectorDecision({
      hg_scene_id: session.hg_scene_id,
      hg_round_id: round.hg_round_id,
      inference_id: `inf-dir-${prefix}`,
      turn_index: 0,
      attempt_index: 0,
      proposed_decision: {
        next_actor: 'Alice',
        end_round: false,
        reason: 'Alice acts.',
        environment_event: '',
        tension_shift: 'steady',
      },
    });
    const commit = await api.commitMove({
      inference_id: `inf-commit-${prefix}`,
      hg_scene_id: session.hg_scene_id,
      hg_round_id: round.hg_round_id,
      character_id: 'Alice',
      validated_move: {
        move_schema_version: 2,
        beats: [{ type: 'action', action: 'checks the latch' }],
        motivation: { goal: 'inspect', tactic: 'check', emotional_driver: 'wary', risk_level: 'low' },
        semantic_evaluation: { decision: 'no_covered_change' },
      },
      director_decision: validation.normalized_decision,
      expected_turn_index: 0,
    });
    return { session, round, commit };
  }

  const parseCase = await commitAlice('parse');
  const parseFail = await runLibrarianProposalGeneration({
    domainApi: api,
    hgSceneId: parseCase.session.hg_scene_id,
    inferenceId: 'inf-librarian-72-parse-fail',
    proposalContextRequest: {
      request_id: 'req-72-parse-fail',
      hg_scene_id: parseCase.session.hg_scene_id,
      hg_round_id: parseCase.round.hg_round_id,
      turn_index: parseCase.commit.continuity_turn_index,
      domain_commit_id: parseCase.commit.domain_commit_id,
      librarian_inference_id: 'inf-librarian-72-parse-fail',
      visibility_envelope: {
        viewer_role: 'host_internal',
        authority_ceiling_enforced: 'derived',
      },
    },
    runEphemeralInference: async () => ({
      evidenceId: 'ev-parse-fail',
      raw: HISTORICAL_MALFORMED,
      failed: false,
      trace: { finish: { kind: 'stop' } },
    }),
    mockResponse: [HISTORICAL_MALFORMED, HISTORICAL_MALFORMED],
  });

  const providerCase = await commitAlice('provider');
  const providerFail = await runLibrarianProposalGeneration({
    domainApi: api,
    hgSceneId: providerCase.session.hg_scene_id,
    inferenceId: 'inf-librarian-72-provider-fail',
    proposalContextRequest: {
      request_id: 'req-72-provider-fail',
      hg_scene_id: providerCase.session.hg_scene_id,
      hg_round_id: providerCase.round.hg_round_id,
      turn_index: providerCase.commit.continuity_turn_index,
      domain_commit_id: providerCase.commit.domain_commit_id,
      librarian_inference_id: 'inf-librarian-72-provider-fail',
      visibility_envelope: {
        viewer_role: 'host_internal',
        authority_ceiling_enforced: 'derived',
      },
    },
    runEphemeralInference: async () => ({
      evidenceId: 'ev-provider-fail',
      raw: null,
      failed: true,
      failure: 'provider_timeout',
      trace: { finish: { kind: 'error' } },
    }),
    mockResponse: null,
  });
  await host.stop();
  assert.equal(parseFail.proposalGenerationFailure, 'structural_parse_failed');
  assert.equal(parseFail.batch?.degradation_mode, 'malformed_result');
  assert.equal(providerFail.proposalGenerationFailure, 'provider_inference_failed');
  assert.equal(providerFail.batch?.degradation_mode, 'inference_failed');
});

test('live generation accepts valid proposal through Host validation', async (t) => {
  const port = 48765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const api = createDomainApiClient(host.baseUrl);
  t.after(() => host.stop());
  const session = await api.createSession({ cast: ['Alice'] });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  const validation = await api.validateDirectorDecision({
    hg_scene_id: session.hg_scene_id,
    hg_round_id: round.hg_round_id,
    inference_id: 'inf-dir-72-live',
    turn_index: 0,
    attempt_index: 0,
    proposed_decision: {
      next_actor: 'Alice',
      end_round: false,
      reason: 'Alice acts.',
      environment_event: '',
      tension_shift: 'steady',
    },
  });
  const commit = await api.commitMove({
    inference_id: 'inf-commit-72-live',
    hg_scene_id: session.hg_scene_id,
    hg_round_id: round.hg_round_id,
    character_id: 'Alice',
    validated_move: {
      move_schema_version: 2,
      beats: [{ type: 'action', action: 'checks the latch carefully' }],
      motivation: { goal: 'inspect', tactic: 'check', emotional_driver: 'wary', risk_level: 'low' },
      semantic_evaluation: { decision: 'no_covered_change' },
    },
    director_decision: validation.normalized_decision,
    expected_turn_index: 0,
  });
  const commitId = commit.domain_commit_id;
  const result = await runLibrarianProposalGeneration({
    domainApi: api,
    hgSceneId: session.hg_scene_id,
    inferenceId: 'inf-librarian-72-live',
    proposalContextRequest: {
      request_id: 'req-72-live',
      hg_scene_id: session.hg_scene_id,
      hg_round_id: round.hg_round_id,
      turn_index: commit.continuity_turn_index,
      domain_commit_id: commitId,
      librarian_inference_id: 'inf-librarian-72-live',
      visibility_envelope: {
        viewer_role: 'host_internal',
        authority_ceiling_enforced: 'derived',
      },
    },
    runEphemeralInference: async ({ mockResponses }) => ({
      evidenceId: 'ev-live-valid',
      raw: mockResponses?.[0] ?? validProposal({
        evidence_anchors: [{ anchor_id: `committed_move:${commitId}`, evidence_kind: 'committed_move', anchor_commit_id: commitId }],
        proposed_payload: { subject_ref: `commit:${commitId}`, salience_level: 'major' },
      }),
      failed: false,
      trace: { finish: { kind: 'stop' } },
    }),
    mockResponse: validProposal({
      evidence_anchors: [{ anchor_id: `committed_move:${commitId}`, evidence_kind: 'committed_move', anchor_commit_id: commitId }],
      proposed_payload: { subject_ref: `commit:${commitId}`, salience_level: 'major' },
    }),
  });
  assert.equal(result.ok, true);
  assert.equal(result.batch?.host_validation?.accepted, true);
  assert.equal(result.correctionUsed, false);
});
