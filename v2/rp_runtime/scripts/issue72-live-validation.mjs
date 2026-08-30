/**
 * Bounded live validation for Issue #72 — Librarian proposal output contract.
 * Run: node scripts/issue72-live-validation.mjs
 */
import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import { runLibrarianProposalGeneration } from '../src/lib/librarian-proposal-substrate.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { startDomainApi } from '../tests/helpers/domain-api.mjs';

const ACTIONS = [
  'examines the worn latch with careful fingers',
  'listens for movement beyond the threshold',
  'notes the faint scent of rain on the stone',
];

const HISTORICAL_MALFORMED = (commitId) => JSON.stringify({
  request_id: 'hist-correction-trial',
  proposals: [{
    change_kind: 'information_salience',
    target: 'scene',
    confidence: 'likely',
    evidence_anchors: [`committed_move:${commitId}`],
  }],
});

async function commitMove(api, { sessionId, action, suffix }) {
  const session = await api.createSession({
    cast: ['Alice'],
    hg_session_id: `issue72-live-${suffix}`,
  });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  const validation = await api.validateDirectorDecision({
    hg_scene_id: session.hg_scene_id,
    hg_round_id: round.hg_round_id,
    inference_id: `inf-dir-${suffix}`,
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
    inference_id: `inf-commit-${suffix}`,
    hg_scene_id: session.hg_scene_id,
    hg_round_id: round.hg_round_id,
    character_id: 'Alice',
    validated_move: {
      move_schema_version: 2,
      beats: [{ type: 'action', action }],
      motivation: {
        goal: 'observe',
        tactic: 'careful',
        emotional_driver: 'wary',
        risk_level: 'low',
      },
      semantic_evaluation: { decision: 'no_covered_change' },
    },
    director_decision: validation.normalized_decision,
    expected_turn_index: 0,
  });
  return { session, round, commit, sessionId: session.hg_session_id ?? sessionId };
}

function classifyResult(result) {
  if (result.proposalGenerationFailure === 'provider_inference_failed') return 'provider_failure';
  if (result.proposalGenerationFailure === 'structural_parse_failed') return 'parse_failure';
  if (result.batch?.degradation_mode === 'host_validation_failed') return 'host_rejection';
  if (result.batch?.host_validation?.accepted) return 'success';
  if (result.ok && result.parsed) return 'parsed_pending_host';
  return 'other';
}

async function runTrial({
  api,
  runEphemeralInference,
  modelProfile,
  suffix,
  action,
  forceMalformedPrimary = false,
  malformedPrimary = null,
}) {
  const { session, round, commit } = await commitMove(api, { action, suffix });
  const commitId = commit.domain_commit_id;
  const inferenceId = `inf-librarian-72-live-${suffix}`;
  const wrappedInference = forceMalformedPrimary
    ? async (params) => {
      if (!String(params.inferenceId || '').includes('contract-correction')) {
        return {
          evidenceId: `ev-forced-malformed-${suffix}`,
          raw: malformedPrimary ?? HISTORICAL_MALFORMED(commitId),
          failed: false,
          trace: { finish: { kind: 'stop' } },
        };
      }
      return runEphemeralInference(params);
    }
    : runEphemeralInference;
  const result = await runLibrarianProposalGeneration({
    domainApi: api,
    hgSceneId: session.hg_scene_id,
    inferenceId,
    proposalContextRequest: {
      request_id: `req-72-live-${suffix}`,
      hg_scene_id: session.hg_scene_id,
      hg_round_id: round.hg_round_id,
      turn_index: commit.continuity_turn_index,
      domain_commit_id: commitId,
      librarian_inference_id: inferenceId,
      visibility_envelope: {
        viewer_role: 'host_internal',
        authority_ceiling_enforced: 'derived',
      },
    },
    runEphemeralInference: wrappedInference,
    modelProfile,
  });
  const kinds = result.parsed?.proposals?.map((p) => p.proposal_kind)
    ?? result.batch?.proposals?.map((p) => p.proposal_kind)
    ?? [];
  return {
    trial: suffix,
    session_anchor: session.hg_session_id ?? `issue72-live-${suffix}`,
    domain_commit_id: commitId,
    primary_contract_ok: !forceMalformedPrimary && result.contractLineage?.primary_parse_error == null,
    primary_parse_error: result.contractLineage?.primary_parse_error ?? null,
    correction_required: result.correctionUsed === true,
    correction_ok: result.correctionUsed ? result.ok : null,
    proposal_kinds: kinds,
    host_accepted: result.batch?.host_validation?.accepted ?? false,
    degradation_mode: result.batch?.degradation_mode ?? null,
    proposal_generation_failure: result.proposalGenerationFailure ?? null,
    forensic_class: classifyResult(result),
    final_disposition: result.batch?.host_validation?.accepted
      ? 'accepted'
      : (result.proposalGenerationFailure ?? result.batch?.degradation_mode ?? 'rejected'),
  };
}

const port = 50765 + Math.floor(Math.random() * 1000);
const host = await startDomainApi(port);
const api = createDomainApiClient(host.baseUrl);
const { phaseExecutors, ctx } = await createHolyGrailRpContext({
  domainApi: { baseUrl: host.baseUrl },
  inference: { mountDeepSeek: true },
});
const modelProfile = deepseekInferenceProfile({ reasoningEffort: 'low', maxTokens: 1024 });
const runEphemeralInference = phaseExecutors.runEphemeralInference.bind(phaseExecutors);

const trials = [];
try {
  trials.push(await runTrial({
    api,
    runEphemeralInference,
    modelProfile,
    suffix: 'a',
    action: ACTIONS[0],
  }));
  trials.push(await runTrial({
    api,
    runEphemeralInference,
    modelProfile,
    suffix: 'b',
    action: ACTIONS[1],
  }));
  trials.push(await runTrial({
    api,
    runEphemeralInference,
    modelProfile,
    suffix: 'c-correction',
    action: ACTIONS[2],
    forceMalformedPrimary: true,
  }));
  trials.push(await runTrial({
    api,
    runEphemeralInference,
    modelProfile,
    suffix: 'd-retry',
    action: ACTIONS[0],
  }));
} finally {
  await ctx.fiber.dispose();
  await host.stop();
}

console.log(JSON.stringify({ issue: 72, trials }, null, 2));
