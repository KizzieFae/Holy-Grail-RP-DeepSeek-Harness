import { Service } from '@deepseek-ai/cordis';
import AgentLoop from '@deepseek-ai/dsh-agent-loop';
import { mountAgentLoopTestDependencies } from '@deepseek-ai/dsh-agent-loop-testkit';
import { createUserMessage } from '@deepseek-ai/dsh-llm';
import { SessionId } from '@deepseek-ai/dsh-session';

import { createDomainApiClient } from '../../lib/domain-api-client.mjs';
import {
  finalAssistantText,
  parseJsonObject,
  registerManifestContributions,
  waitForIdle,
} from '../../lib/inference-utils.mjs';
import { HG_MOCK_MODEL, HG_MOCK_PROVIDER, HgMockLlmAdapter } from '../../mock-llm-adapter.mjs';
import { appendHgEvent, baseCorrelation } from './events.mjs';

export default class HolyGrailRpRuntime extends Service {
  static name = 'hgRpRuntime';

  constructor(ctx, config = {}) {
    super(ctx, HolyGrailRpRuntime.name);
    this.config = config;
  }

  async mountStack(options) {
    await mountAgentLoopTestDependencies(this.ctx, {
      systemPrompt: { persona: options.persona ?? 'Holy Grail RP runtime.' },
    });
    await this.ctx.plugin(AgentLoop, { agents: [] });
  }

  _domainClient(baseUrl) {
    return createDomainApiClient(baseUrl ?? this.config.domainApi?.baseUrl);
  }

  async _runEphemeralInference({
    inferenceId,
    prompt,
    manifest,
    mockResponses,
  }) {
    const adapter = new HgMockLlmAdapter(
      mockResponses.length ? mockResponses : ['{}'],
    );
    const disposeAdapter = this.ctx.llm.registerAdapter([HG_MOCK_PROVIDER], adapter);
    const agent = this.ctx.agentLoop.create(SessionId(`hg-inf-${inferenceId}`), {
      provider: HG_MOCK_PROVIDER,
      model: HG_MOCK_MODEL,
    });
    const releaseManifest = registerManifestContributions(agent, manifest?.contributions);
    agent.followup(
      createUserMessage({
        content: [{ type: 'text', text: prompt }],
        source: { kind: 'user' },
      }),
    );
    await waitForIdle(this.ctx, agent);
    const raw = finalAssistantText(agent.session.events);
    releaseManifest();
    disposeAdapter();
    return { raw, inferenceSessionId: String(agent.id) };
  }

  async runCharacterInference(options) {
    const api = this._domainClient(options.domainApi?.baseUrl);
    const characterId = options.characterId ?? 'Alice';
    const role = options.role ?? 'guest';
    const inferenceId = options.inferenceId ?? `inf-char-${crypto.randomUUID()}`;

    let hgSceneId = options.hgSceneId;
    let hgRoundId = options.hgRoundId;
    if (!hgSceneId) {
      const created = await api.createScene({ cast: ['Alice', 'Bob'] });
      hgSceneId = String(created.hg_scene_id);
    }
    if (!hgRoundId) {
      const round = await api.startRound({ hg_scene_id: hgSceneId });
      hgRoundId = String(round.hg_round_id);
    }

    const beforeState = await api.getSceneState(hgSceneId);
    const expectedTurnIndex = Number(beforeState.turn_counter ?? 0);
    const sceneSessionId = SessionId(`hg-scene-${hgSceneId}`);
    const sceneAgent = this.ctx.agentLoop.create(sceneSessionId, {
      provider: HG_MOCK_PROVIDER,
      model: HG_MOCK_MODEL,
    });

    const directorDecision = options.directorDecision ?? {
      next_actor: characterId,
      end_round: false,
      reason: 'character-only slice',
      environment_event: '',
      tension_shift: '',
    };

    let attemptIndex = 0;
    let committed = false;
    let continuityTurnIndex = null;
    let domainCommitId = null;
    let manifestId = '';
    const mockResponses = options.mockResponses ?? [];

    while (attemptIndex < mockResponses.length && !committed) {
      const manifest = await api.prepareCharacterContext({
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        inference_id: inferenceId,
        character_id: characterId,
        role,
        turn_index: expectedTurnIndex,
        attempt_index: attemptIndex,
      });
      manifestId = String(manifest.manifest_id);

      const { raw } = await this._runEphemeralInference({
        inferenceId: `${inferenceId}-${attemptIndex}`,
        prompt: 'Produce your character move as JSON only.',
        manifest,
        mockResponses: [mockResponses[attemptIndex]],
      });

      let proposed;
      try {
        proposed = parseJsonObject(raw);
      } catch (error) {
        proposed = { parse_error: String(error) };
      }

      appendHgEvent(sceneAgent.session, 'hg/move-proposed', {
        ...baseCorrelation({
          hg_scene_id: hgSceneId,
          hg_round_id: hgRoundId,
          dsh_scene_session_id: String(sceneSessionId),
        }),
        inference_id: inferenceId,
        role: 'character',
        character_id: characterId,
        attempt_index: attemptIndex,
        manifest_id: manifestId,
        proposed_move: proposed,
        raw_model_output: raw,
      });

      const validation = await api.validateMove({
        inference_id: inferenceId,
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        character_id: characterId,
        role,
        turn_index: expectedTurnIndex,
        attempt_index: attemptIndex,
        proposed_move: proposed,
        raw_model_output: raw,
      });

      if (!validation.accepted) {
        appendHgEvent(sceneAgent.session, 'hg/move-rejected', {
          ...baseCorrelation({
            hg_scene_id: hgSceneId,
            hg_round_id: hgRoundId,
            dsh_scene_session_id: String(sceneSessionId),
          }),
          inference_id: inferenceId,
          role: 'character',
          character_id: characterId,
          attempt_index: attemptIndex,
          validation_class: String(validation.validation_class ?? 'unknown'),
          reason: String(validation.reason ?? ''),
          retryable: Boolean(validation.retryable),
        });
        attemptIndex += 1;
        continue;
      }

      const commit = await api.commitMove({
        inference_id: inferenceId,
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        character_id: characterId,
        validated_move: validation.normalized_move ?? proposed,
        director_decision: directorDecision,
        expected_turn_index: expectedTurnIndex,
      });

      if (!commit.committed) {
        appendHgEvent(sceneAgent.session, 'hg/move-rejected', {
          ...baseCorrelation({
            hg_scene_id: hgSceneId,
            hg_round_id: hgRoundId,
            dsh_scene_session_id: String(sceneSessionId),
          }),
          inference_id: inferenceId,
          role: 'character',
          character_id: characterId,
          attempt_index: attemptIndex,
          validation_class: 'continuity_anchor',
          reason: String(commit.reason ?? 'commit rejected'),
          retryable: false,
        });
        attemptIndex += 1;
        continue;
      }

      committed = true;
      continuityTurnIndex = Number(commit.continuity_turn_index);
      domainCommitId = String(commit.domain_commit_id ?? '');
      appendHgEvent(sceneAgent.session, 'hg/move-committed', {
        ...baseCorrelation({
          hg_scene_id: hgSceneId,
          hg_round_id: hgRoundId,
          dsh_scene_session_id: String(sceneSessionId),
        }),
        inference_id: inferenceId,
        role: 'character',
        character_id: characterId,
        attempt_index: attemptIndex,
        manifest_id: manifestId,
        continuity_turn_index: continuityTurnIndex,
        domain_commit_id: domainCommitId,
      });
    }

    return {
      committed,
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      inference_id: inferenceId,
      character_id: characterId,
      dsh_scene_session_id: String(sceneSessionId),
      continuity_turn_index: continuityTurnIndex,
      domain_commit_id: domainCommitId,
      scene_events: [...sceneAgent.session.events],
      boundary_metrics: api.metrics,
    };
  }

  async runDirectorCharacterRound(options) {
    const api = this._domainClient(options.domainApi?.baseUrl);
    const directorResponses = options.mockDirectorResponses ?? [];
    const characterResponses = options.mockCharacterResponses ?? [];

    let hgSceneId = options.hgSceneId;
    if (!hgSceneId) {
      const created = await api.createScene({ cast: ['Alice', 'Bob'] });
      hgSceneId = String(created.hg_scene_id);
    }
    const round = await api.startRound({ hg_scene_id: hgSceneId });
    const hgRoundId = String(round.hg_round_id);
    const turnIndex = Number(round.turn_index ?? 0);

    const sceneSessionId = SessionId(`hg-scene-${hgSceneId}`);
    const sceneAgent = this.ctx.agentLoop.create(sceneSessionId, {
      provider: HG_MOCK_PROVIDER,
      model: HG_MOCK_MODEL,
    });

    appendHgEvent(sceneAgent.session, 'hg/round-started', {
      ...baseCorrelation({
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        dsh_scene_session_id: String(sceneSessionId),
      }),
      turn_index: turnIndex,
    });

    const directorInferenceId = options.directorInferenceId ?? `inf-director-${crypto.randomUUID()}`;
    let directorAttempt = 0;
    let directorAccepted = false;
    let directorDecision = null;
    let directorManifestId = '';
    let selectedCharacterId = null;
    let directorInferenceSessionId = null;

    while (directorAttempt < directorResponses.length && !directorAccepted) {
      const manifest = await api.prepareDirectorContext({
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        inference_id: directorInferenceId,
        turn_index: turnIndex,
        attempt_index: directorAttempt,
      });
      directorManifestId = String(manifest.manifest_id);

      const directorRun = await this._runEphemeralInference({
        inferenceId: `${directorInferenceId}-${directorAttempt}`,
        prompt: 'Produce your director decision as JSON only.',
        manifest,
        mockResponses: [directorResponses[directorAttempt]],
      });
      directorInferenceSessionId = directorRun.inferenceSessionId;

      let proposed;
      try {
        proposed = parseJsonObject(directorRun.raw);
      } catch (error) {
        proposed = { parse_error: String(error) };
      }

      appendHgEvent(sceneAgent.session, 'hg/director-proposed', {
        ...baseCorrelation({
          hg_scene_id: hgSceneId,
          hg_round_id: hgRoundId,
          dsh_scene_session_id: String(sceneSessionId),
        }),
        inference_id: directorInferenceId,
        director_inference_session_id: directorInferenceSessionId,
        role: 'director',
        attempt_index: directorAttempt,
        manifest_id: directorManifestId,
        proposed_decision: proposed,
        raw_model_output: directorRun.raw,
      });

      const validation = await api.validateDirectorDecision({
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        inference_id: directorInferenceId,
        turn_index: turnIndex,
        attempt_index: directorAttempt,
        proposed_decision: proposed,
        raw_model_output: directorRun.raw,
      });

      if (!validation.accepted) {
        appendHgEvent(sceneAgent.session, 'hg/director-rejected', {
          ...baseCorrelation({
            hg_scene_id: hgSceneId,
            hg_round_id: hgRoundId,
            dsh_scene_session_id: String(sceneSessionId),
          }),
          inference_id: directorInferenceId,
          director_inference_session_id: directorInferenceSessionId,
          role: 'director',
          attempt_index: directorAttempt,
          validation_class: String(validation.validation_class ?? 'unknown'),
          reason: String(validation.reason ?? ''),
          retryable: Boolean(validation.retryable),
        });
        directorAttempt += 1;
        continue;
      }

      directorAccepted = true;
      directorDecision = validation.normalized_decision ?? proposed;
      selectedCharacterId = String(validation.selected_character_id ?? directorDecision.next_actor);
      appendHgEvent(sceneAgent.session, 'hg/director-accepted', {
        ...baseCorrelation({
          hg_scene_id: hgSceneId,
          hg_round_id: hgRoundId,
          dsh_scene_session_id: String(sceneSessionId),
        }),
        inference_id: directorInferenceId,
        director_inference_session_id: directorInferenceSessionId,
        role: 'director',
        attempt_index: directorAttempt,
        manifest_id: directorManifestId,
        selected_character_id: selectedCharacterId,
        normalized_decision: directorDecision,
      });
    }

    if (!directorAccepted || !directorDecision || !selectedCharacterId) {
      return {
        committed: false,
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        director_accepted: false,
        scene_events: [...sceneAgent.session.events],
        boundary_metrics: api.metrics,
      };
    }

    const characterInferenceId = options.characterInferenceId ?? `inf-character-${crypto.randomUUID()}`;
    let characterAttempt = 0;
    let committed = false;
    let continuityTurnIndex = null;
    let domainCommitId = null;
    let characterManifestId = '';
    let characterInferenceSessionId = null;

    while (characterAttempt < characterResponses.length && !committed) {
      const manifest = await api.prepareCharacterContext({
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        inference_id: characterInferenceId,
        character_id: selectedCharacterId,
        role: selectedCharacterId === 'Alice' ? 'guest' : 'staff',
        turn_index: turnIndex,
        attempt_index: characterAttempt,
      });
      characterManifestId = String(manifest.manifest_id);

      const characterRun = await this._runEphemeralInference({
        inferenceId: `${characterInferenceId}-${characterAttempt}`,
        prompt: 'Produce your character move as JSON only.',
        manifest,
        mockResponses: [characterResponses[characterAttempt]],
      });
      characterInferenceSessionId = characterRun.inferenceSessionId;

      let proposed;
      try {
        proposed = parseJsonObject(characterRun.raw);
      } catch (error) {
        proposed = { parse_error: String(error) };
      }

      appendHgEvent(sceneAgent.session, 'hg/move-proposed', {
        ...baseCorrelation({
          hg_scene_id: hgSceneId,
          hg_round_id: hgRoundId,
          dsh_scene_session_id: String(sceneSessionId),
        }),
        inference_id: characterInferenceId,
        character_inference_session_id: characterInferenceSessionId,
        role: 'character',
        character_id: selectedCharacterId,
        attempt_index: characterAttempt,
        manifest_id: characterManifestId,
        proposed_move: proposed,
        raw_model_output: characterRun.raw,
      });

      const validation = await api.validateMove({
        inference_id: characterInferenceId,
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        character_id: selectedCharacterId,
        role: selectedCharacterId === 'Alice' ? 'guest' : 'staff',
        turn_index: turnIndex,
        attempt_index: characterAttempt,
        proposed_move: proposed,
        raw_model_output: characterRun.raw,
      });

      if (!validation.accepted) {
        appendHgEvent(sceneAgent.session, 'hg/move-rejected', {
          ...baseCorrelation({
            hg_scene_id: hgSceneId,
            hg_round_id: hgRoundId,
            dsh_scene_session_id: String(sceneSessionId),
          }),
          inference_id: characterInferenceId,
          character_inference_session_id: characterInferenceSessionId,
          role: 'character',
          character_id: selectedCharacterId,
          attempt_index: characterAttempt,
          validation_class: String(validation.validation_class ?? 'unknown'),
          reason: String(validation.reason ?? ''),
          retryable: Boolean(validation.retryable),
        });
        characterAttempt += 1;
        continue;
      }

      const commit = await api.commitMove({
        inference_id: characterInferenceId,
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        character_id: selectedCharacterId,
        validated_move: validation.normalized_move ?? proposed,
        director_decision: directorDecision,
        expected_turn_index: turnIndex,
      });

      if (!commit.committed) {
        appendHgEvent(sceneAgent.session, 'hg/move-rejected', {
          ...baseCorrelation({
            hg_scene_id: hgSceneId,
            hg_round_id: hgRoundId,
            dsh_scene_session_id: String(sceneSessionId),
          }),
          inference_id: characterInferenceId,
          character_inference_session_id: characterInferenceSessionId,
          role: 'character',
          character_id: selectedCharacterId,
          attempt_index: characterAttempt,
          validation_class: 'continuity_anchor',
          reason: String(commit.reason ?? 'commit rejected'),
          retryable: false,
        });
        characterAttempt += 1;
        continue;
      }

      committed = true;
      continuityTurnIndex = Number(commit.continuity_turn_index);
      domainCommitId = String(commit.domain_commit_id ?? '');
      appendHgEvent(sceneAgent.session, 'hg/move-committed', {
        ...baseCorrelation({
          hg_scene_id: hgSceneId,
          hg_round_id: hgRoundId,
          dsh_scene_session_id: String(sceneSessionId),
        }),
        inference_id: characterInferenceId,
        character_inference_session_id: characterInferenceSessionId,
        role: 'character',
        character_id: selectedCharacterId,
        attempt_index: characterAttempt,
        manifest_id: characterManifestId,
        continuity_turn_index: continuityTurnIndex,
        domain_commit_id: domainCommitId,
      });
    }

    return {
      committed,
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      director_inference_id: directorInferenceId,
      director_inference_session_id: directorInferenceSessionId,
      character_inference_id: characterInferenceId,
      character_inference_session_id: characterInferenceSessionId,
      selected_character_id: selectedCharacterId,
      director_decision: directorDecision,
      dsh_scene_session_id: String(sceneSessionId),
      continuity_turn_index: continuityTurnIndex,
      domain_commit_id: domainCommitId,
      scene_events: [...sceneAgent.session.events],
      boundary_metrics: api.metrics,
    };
  }
}
