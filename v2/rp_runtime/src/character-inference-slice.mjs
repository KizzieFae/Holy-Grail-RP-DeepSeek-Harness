import { Context } from '@deepseek-ai/cordis';
import AgentLoop from '@deepseek-ai/dsh-agent-loop';
import { mountAgentLoopTestDependencies } from '@deepseek-ai/dsh-agent-loop-testkit';
import { createUserMessage } from '@deepseek-ai/dsh-llm';
import { SessionId } from '@deepseek-ai/dsh-session';

import {
  commitMove,
  createScene,
  getSceneState,
  prepareContext,
  validateMove,
} from './domain-api-client.mjs';
import { HG_MOCK_MODEL, HG_MOCK_PROVIDER, HgMockLlmAdapter } from './mock-llm-adapter.mjs';

function waitForIdle(ctx, agent) {
  return new Promise((resolve) => {
    const dispose = ctx.on('agent/status', ({ agent: subject, status }) => {
      if (subject === agent && status === 'idle') {
        dispose();
        resolve();
      }
    });
  });
}

function finalAssistantText(events) {
  const message = [...events].reverse().find((event) => event.type === 'assistant/message');
  if (!message || message.type !== 'assistant/message') return '';
  return message.data.message.content
    .filter((block) => block.type === 'text')
    .map((block) => block.text)
    .join('');
}

function parseJsonObject(text) {
  const trimmed = text.trim();
  const start = trimmed.indexOf('{');
  const end = trimmed.lastIndexOf('}');
  if (start < 0 || end < start) {
    throw new Error('model output did not contain a JSON object');
  }
  return JSON.parse(trimmed.slice(start, end + 1));
}

/** Run one ephemeral character inference through DSH with Python authority. */
export async function runCharacterInferenceSlice(options) {
  const characterId = options.characterId ?? 'Alice';
  const role = options.role ?? 'guest';
  const inferenceId = options.inferenceId ?? `inf-${crypto.randomUUID()}`;
  const sceneSessionId = SessionId(`hg-scene-dsh-${crypto.randomUUID()}`);
  const inferenceSessionId = SessionId(`hg-inf-${inferenceId}`);

  let hgSceneId = options.hgSceneId;
  if (!hgSceneId) {
    const created = await createScene(options.domainApi, { cast: ['Alice', 'Bob'] });
    hgSceneId = String(created.hg_scene_id);
  }

  const beforeState = await getSceneState(options.domainApi, hgSceneId);
  const expectedTurnIndex = Number(beforeState.turn_counter ?? 0);

  const ctx = new Context();
  await mountAgentLoopTestDependencies(ctx, {
    systemPrompt: { persona: 'Holy Grail character inference slot (ephemeral).' },
  });
  ctx.llm.registerAdapter([HG_MOCK_PROVIDER], new HgMockLlmAdapter(options.mockResponses));
  await ctx.plugin(AgentLoop, { agents: [] });

  const sceneAgent = ctx.agentLoop.create(sceneSessionId, {
    provider: HG_MOCK_PROVIDER,
    model: HG_MOCK_MODEL,
  });

  const agent = ctx.agentLoop.create(inferenceSessionId, {
    provider: HG_MOCK_PROVIDER,
    model: HG_MOCK_MODEL,
  });

  const trace = {
    scene_dsh_session_id: String(sceneSessionId),
    inference_dsh_session_id: String(inferenceSessionId),
    attempts: [],
  };

  let attemptIndex = 0;
  let committed = false;
  let continuityTurnIndex = null;
  let domainCommitId = null;
  let manifestId = '';

  while (attemptIndex < options.mockResponses.length && !committed) {
    const manifest = await prepareContext(options.domainApi, {
      hg_scene_id: hgSceneId,
      inference_id: inferenceId,
      character_id: characterId,
      role,
      turn_index: expectedTurnIndex,
      attempt_index: attemptIndex,
    });
    manifestId = String(manifest.manifest_id);

    const disposers = [];
    const contributions = manifest.contributions ?? [];
    for (const contribution of contributions) {
      const dispose = agent.ctx.systemPrompt.context({
        name: String(contribution.contribution_id),
        order: Number(contribution.priority ?? 0),
        text: String(contribution.content ?? ''),
      });
      disposers.push(dispose);
    }

    agent.followup(
      createUserMessage({
        content: [{ type: 'text', text: 'Produce your character move as JSON only.' }],
        source: { kind: 'user' },
      }),
    );
    await waitForIdle(ctx, agent);

    const events = [...agent.session.events];
    const lastRaw = finalAssistantText(events);
    let proposed;
    try {
      proposed = parseJsonObject(lastRaw);
    } catch (error) {
      proposed = { parse_error: String(error) };
    }

    agent.session.append('hg/move-proposed', {
      inference_id: inferenceId,
      attempt_index: attemptIndex,
      character_id: characterId,
      hg_scene_id: hgSceneId,
      manifest_id: manifestId,
      proposed_move: proposed,
      raw_model_output: lastRaw,
    });

    const validation = await validateMove(options.domainApi, {
      inference_id: inferenceId,
      hg_scene_id: hgSceneId,
      character_id: characterId,
      role,
      turn_index: expectedTurnIndex,
      attempt_index: attemptIndex,
      proposed_move: proposed,
      raw_model_output: lastRaw,
    });

    trace.attempts.push({
      attempt_index: attemptIndex,
      manifest_id: manifestId,
      validation,
      proposed_move: proposed,
    });

    if (!validation.accepted) {
      agent.session.append('hg/move-rejected', {
        inference_id: inferenceId,
        attempt_index: attemptIndex,
        character_id: characterId,
        hg_scene_id: hgSceneId,
        validation_class: String(validation.validation_class ?? 'unknown'),
        reason: String(validation.reason ?? ''),
        retryable: Boolean(validation.retryable),
      });
      attemptIndex += 1;
      for (const dispose of disposers) dispose();
      continue;
    }

    const commit = await commitMove(options.domainApi, {
      inference_id: inferenceId,
      hg_scene_id: hgSceneId,
      character_id: characterId,
      validated_move: validation.normalized_move ?? proposed,
      expected_turn_index: expectedTurnIndex,
    });

    if (!commit.committed) {
      agent.session.append('hg/move-rejected', {
        inference_id: inferenceId,
        attempt_index: attemptIndex,
        character_id: characterId,
        hg_scene_id: hgSceneId,
        validation_class: 'continuity_anchor',
        reason: String(commit.reason ?? 'commit rejected'),
        retryable: false,
      });
      attemptIndex += 1;
      for (const dispose of disposers) dispose();
      continue;
    }

    committed = true;
    continuityTurnIndex = Number(commit.continuity_turn_index);
    domainCommitId = String(commit.domain_commit_id ?? '');
    agent.session.append('hg/move-committed', {
      inference_id: inferenceId,
      attempt_index: attemptIndex,
      character_id: characterId,
      hg_scene_id: hgSceneId,
      continuity_turn_index: continuityTurnIndex,
      domain_commit_id: domainCommitId,
      dsh_session_id: String(inferenceSessionId),
    });
    for (const dispose of disposers) dispose();
  }

  const finalEvents = [...agent.session.events];
  await ctx.fiber.dispose();
  void sceneAgent;

  return {
    inference_id: inferenceId,
    hg_scene_id: hgSceneId,
    character_id: characterId,
    dsh_session_id: String(inferenceSessionId),
    attempt_index: attemptIndex,
    manifest_id: manifestId,
    continuity_turn_index: continuityTurnIndex,
    domain_commit_id: domainCommitId,
    committed,
    events: finalEvents,
    trace,
  };
}
