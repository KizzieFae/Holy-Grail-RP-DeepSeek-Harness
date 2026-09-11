import assert from 'node:assert/strict';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { LIBRARIAN_PROPOSAL_RESULT_SCHEMA } from '../src/lib/librarian-proposal-envelope.mjs';
import { runLibrarianProposalGeneration } from '../src/lib/librarian-proposal-substrate.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { fetchSessionState, makeTempSessionsDir, startDomainApi } from './helpers/domain-api.mjs';

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

function eventIndex(events, type) {
  return events.findIndex((event) => event.type === type);
}

function buildValidLibrarianProposal(commitId) {
  return JSON.stringify({
    schema: LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
    proposals: [
      {
        proposal_id: 'prop-live-1',
        proposal_kind: 'issue_tension_pressure',
        proposal_origin: 'storyteller',
        derivation_summary: 'Committed move leaves active issue pressure unmet.',
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
          semantic_unmet_condition: 'The move does not resolve the active issue.',
        },
      },
    ],
  });
}

test('live S4: narrator completes before slow librarian join', async (t) => {
  const port = 44765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    skipStorytellerCognition: true,
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
    librarianProposalDelayMs: 250,
  });

  assert.equal(result.committed, true);
  assert.equal(result.presentation_rendered, true);
  assert.ok(result.round_timing_ms.librarian[0] >= 250);
  assert.ok(result.round_timing_ms.narrator[0] < result.round_timing_ms.librarian[0]);

  const narratorCompletedIdx = eventIndex(result.scene_events, 'hg/narrator-completed');
  const librarianCompletedIdx = eventIndex(result.scene_events, 'hg/post-commit-semantic-completed');
  const joinIdx = eventIndex(result.scene_events, 'hg/post-commit-semantic-join');
  assert.ok(narratorCompletedIdx >= 0);
  assert.ok(librarianCompletedIdx >= 0);
  assert.ok(joinIdx >= 0);
  assert.ok(narratorCompletedIdx < librarianCompletedIdx);
  assert.ok(librarianCompletedIdx <= joinIdx);
});

test('live S4: one orchestration lifecycle per commit and fail-open inference', async (t) => {
  const port = 45765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice', 'Bob'] },
    skipStorytellerCognition: true,
    mockDirectorResponses: [
      JSON.stringify(DIRECTOR_FOR('Alice')),
      JSON.stringify(DIRECTOR_FOR('Bob')),
    ],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)], [JSON.stringify(MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE], [NARRATOR_PROSE]],
    mockLibrarianProposalResponses: [null, null],
  });

  assert.equal(result.character_turn_count, 2);
  const prepareCalls = result.boundary_metrics.calls.filter(
    (call) => call.label === 'prepareLibrarianProposalContext',
  );
  const finalizeCalls = result.boundary_metrics.calls.filter(
    (call) => call.label === 'finalizeLibrarianProposals',
  );
  assert.equal(prepareCalls.length, 2);
  assert.equal(finalizeCalls.length, 2);
  assert.equal(result.character_turns[0].librarian_terminal, true);
  assert.equal(result.character_turns[1].librarian_terminal, true);
  assert.equal(result.completion_status, 'completed');
});

test('live S4: audit log survives session reload and blocks duplicate semantic inference', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  const port = 46765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const round = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    skipStorytellerCognition: true,
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
  });

  const commitId = round.domain_commit_id;
  assert.ok(commitId);

  const host2 = await startDomainApi(port + 1, { sessionsDir });
  t.after(() => host2.stop());
  const api = createDomainApiClient(host2.baseUrl);

  const inferenceCalls = [];
  const generation = await runLibrarianProposalGeneration({
    domainApi: api,
    hgSceneId: round.hg_scene_id,
    inferenceId: 'inf-librarian-reentry',
    proposalContextRequest: {
      request_id: `lpr-${crypto.randomUUID()}`,
      hg_scene_id: round.hg_scene_id,
      hg_round_id: round.hg_round_id,
      turn_index: round.continuity_turn_index,
      domain_commit_id: commitId,
      librarian_inference_id: 'inf-librarian-reentry',
      visibility_envelope: {
        viewer_role: 'host_internal',
        authority_ceiling_enforced: 'derived',
      },
    },
    runEphemeralInference: async () => {
      inferenceCalls.push('should-not-run');
      return { failed: false, raw: buildValidLibrarianProposal(commitId) };
    },
  });

  assert.equal(inferenceCalls.length, 0);
  assert.equal(generation.skipped, true);
  assert.equal(generation.stage, 'already_terminal');
});

test('live S4: skip hook suppresses orchestration without production disable', async (t) => {
  const port = 47765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    skipStorytellerCognition: true,
    skipLibrarianProposalGeneration: true,
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
  });

  assert.equal(
    result.boundary_metrics.calls.some((call) => call.label === 'prepareLibrarianProposalContext'),
    false,
  );
  assert.equal(result.scene_events.some((event) => event.type === 'hg/post-commit-semantic-started'), false);
  assert.equal(result.committed, true);
});

test('live S4: Host persistence failure blocks next turn without undoing commit or narrator', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  const port = 48765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, {
    sessionsDir,
    hostEnv: { HG_TEST_LIBRARIAN_PERSIST_FAIL: '1' },
  });
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice', 'Bob'] },
    skipStorytellerCognition: true,
    mockDirectorResponses: [
      JSON.stringify(DIRECTOR_FOR('Alice')),
      JSON.stringify(DIRECTOR_FOR('Bob')),
    ],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)], [JSON.stringify(MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE], [NARRATOR_PROSE]],
    mockLibrarianProposalResponses: [null],
  });

  assert.equal(result.completion_reason, 'librarian_persistence_failure');
  assert.equal(result.completion_status, 'aborted');
  assert.equal(result.completion_class, 'failure');
  assert.equal(result.character_turn_count, 1);
  assert.equal(result.committed, true);
  assert.equal(result.presentation_rendered, true);
  assert.equal(result.presentation_text, NARRATOR_PROSE);
  assert.equal(result.character_turns[0].librarian_blocking_persistence_failure, true);

  const eligibilityCalls = result.boundary_metrics.calls.filter(
    (call) => call.label === 'getEligibleActors',
  );
  assert.equal(eligibilityCalls.length, 1);

  const narratorCompletedIdx = eventIndex(result.scene_events, 'hg/narrator-completed');
  const librarianFailedIdx = eventIndex(result.scene_events, 'hg/post-commit-semantic-failed');
  const joinIdx = eventIndex(result.scene_events, 'hg/post-commit-semantic-join');
  assert.ok(narratorCompletedIdx >= 0);
  assert.ok(librarianFailedIdx >= 0);
  assert.ok(joinIdx >= 0);
  assert.ok(narratorCompletedIdx < joinIdx);
  assert.equal(result.scene_events[joinIdx].data.blocking_persistence_failure, true);

  const sceneState = await fetchSessionState(baseUrl, result.hg_session_id);
  assert.ok(Number(sceneState.turn_counter ?? 0) >= 1);

  const failOpenHost = await startDomainApi(port + 1, { sessionsDir: makeTempSessionsDir() });
  t.after(() => failOpenHost.stop());
  const { ctx: failOpenCtx, orchestrator: failOpenOrchestrator } = await createHolyGrailRpContext({
    domainApi: { baseUrl: failOpenHost.baseUrl },
  });
  t.after(async () => {
    await failOpenCtx.fiber.dispose();
  });

  const failOpenResult = await failOpenOrchestrator.runRound({
    domainApi: { baseUrl: failOpenHost.baseUrl },
    session: { mode: 'create', cast: ['Alice', 'Bob'] },
    skipStorytellerCognition: true,
    mockDirectorResponses: [
      JSON.stringify(DIRECTOR_FOR('Alice')),
      JSON.stringify(DIRECTOR_FOR('Bob')),
    ],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)], [JSON.stringify(MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE], [NARRATOR_PROSE]],
    mockLibrarianProposalResponses: [null, null],
  });

  assert.equal(failOpenResult.completion_status, 'completed');
  assert.equal(failOpenResult.completion_reason, 'no_eligible_actors');
  assert.equal(failOpenResult.character_turn_count, 2);
  assert.equal(failOpenResult.scene_events.some((event) => event.type === 'hg/post-commit-semantic-failed'), false);
});
