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

function roleForCharacter(characterId, characterRoles = {}) {
  return characterRoles[characterId] ?? (characterId === 'Alice' ? 'guest' : 'staff');
}

function classifyRoundCompletion(completionReason) {
  if (completionReason === 'director_end_round' || completionReason === 'no_eligible_actors') {
    return { completion_status: 'completed', completion_class: 'semantic' };
  }
  if (completionReason === 'defensive_turn_ceiling') {
    return { completion_status: 'completed', completion_class: 'defensive' };
  }
  return { completion_status: 'aborted', completion_class: 'failure' };
}

function eligibilityTrace(eligibility) {
  return {
    eligible_actors: eligibility.eligible_actors ?? [],
    actors_used_this_round: eligibility.actors_used_this_round ?? [],
    present_characters: eligibility.present_characters ?? [],
    offstage_characters: eligibility.offstage_characters ?? [],
    absent_but_relevant: eligibility.absent_but_relevant ?? [],
    actors: eligibility.actors ?? [],
  };
}

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

  _correlation({ hgSceneId, hgRoundId, sceneSessionId }) {
    return baseCorrelation({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      dsh_scene_session_id: String(sceneSessionId),
    });
  }

  async _runDirectorPhase({
    api,
    sceneAgent,
    sceneSessionId,
    hgSceneId,
    hgRoundId,
    directorInferenceId,
    directorAttemptSeed,
    mockDirectorResponses,
    directorResponseIndex,
    actorsUsedThisRound,
    turnIndex,
    eligibilitySnapshot,
  }) {
    let directorAttempt = directorAttemptSeed;
    let directorAccepted = false;
    let directorDecision = null;
    let directorManifestId = '';
    let selectedCharacterId = null;
    let directorInferenceSessionId = null;
    let endRound = false;

    while (directorResponseIndex < mockDirectorResponses.length && !directorAccepted) {
      const manifest = await api.prepareDirectorContext({
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        inference_id: directorInferenceId,
        turn_index: turnIndex,
        attempt_index: directorAttempt,
        actors_used_this_round: actorsUsedThisRound,
      });
      directorManifestId = String(manifest.manifest_id);

      const directorRun = await this._runEphemeralInference({
        inferenceId: `${directorInferenceId}-${directorAttempt}`,
        prompt: 'Produce your director decision as JSON only.',
        manifest,
        mockResponses: [mockDirectorResponses[directorResponseIndex]],
      });
      directorInferenceSessionId = directorRun.inferenceSessionId;

      let proposed;
      try {
        proposed = parseJsonObject(directorRun.raw);
      } catch (error) {
        proposed = { parse_error: String(error) };
      }

      appendHgEvent(sceneAgent.session, 'hg/director-proposed', {
        ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
        inference_id: directorInferenceId,
        director_inference_session_id: directorInferenceSessionId,
        role: 'director',
        attempt_index: directorAttempt,
        manifest_id: directorManifestId,
        proposed_decision: proposed,
        raw_model_output: directorRun.raw,
        actors_used_this_round: actorsUsedThisRound,
        eligibility_snapshot: eligibilitySnapshot,
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
          ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
          inference_id: directorInferenceId,
          director_inference_session_id: directorInferenceSessionId,
          role: 'director',
          attempt_index: directorAttempt,
          validation_class: String(validation.validation_class ?? 'unknown'),
          reason: String(validation.reason ?? ''),
          retryable: Boolean(validation.retryable),
          proposed_decision: proposed,
          eligibility_snapshot: eligibilitySnapshot,
        });
        directorAttempt += 1;
        directorResponseIndex += 1;
        continue;
      }

      directorAccepted = true;
      directorDecision = validation.normalized_decision ?? proposed;
      endRound = Boolean(directorDecision.end_round);
      selectedCharacterId = endRound
        ? null
        : String(validation.selected_character_id ?? directorDecision.next_actor ?? '');
      appendHgEvent(sceneAgent.session, 'hg/director-accepted', {
        ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
        inference_id: directorInferenceId,
        director_inference_session_id: directorInferenceSessionId,
        role: 'director',
        attempt_index: directorAttempt,
        manifest_id: directorManifestId,
        selected_character_id: selectedCharacterId,
        normalized_decision: directorDecision,
        end_round: endRound,
        actors_used_this_round: actorsUsedThisRound,
        eligibility_snapshot: eligibilitySnapshot,
      });
      directorResponseIndex += 1;
    }

    return {
      accepted: directorAccepted,
      endRound,
      directorDecision,
      selectedCharacterId,
      directorManifestId,
      directorInferenceSessionId,
      directorAttempt,
      directorResponseIndex,
    };
  }

  async _runCharacterTurn({
    api,
    sceneAgent,
    sceneSessionId,
    hgSceneId,
    hgRoundId,
    characterId,
    directorDecision,
    characterInferenceId,
    mockResponses,
    characterTurnIndex,
    characterRole,
  }) {
    const role = characterRole ?? roleForCharacter(characterId);
    let attemptIndex = 0;
    let committed = false;
    let continuityTurnIndex = null;
    let domainCommitId = null;
    let characterManifestId = '';
    let characterInferenceSessionId = null;

    while (attemptIndex < mockResponses.length && !committed) {
      const state = await api.getSceneState(hgSceneId);
      const expectedTurnIndex = Number(state.turn_counter ?? 0);
      const manifest = await api.prepareCharacterContext({
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        inference_id: characterInferenceId,
        character_id: characterId,
        role,
        turn_index: expectedTurnIndex,
        attempt_index: attemptIndex,
      });
      characterManifestId = String(manifest.manifest_id);

      const characterRun = await this._runEphemeralInference({
        inferenceId: `${characterInferenceId}-${attemptIndex}`,
        prompt: 'Produce your character move as JSON only.',
        manifest,
        mockResponses: [mockResponses[attemptIndex]],
      });
      characterInferenceSessionId = characterRun.inferenceSessionId;

      let proposed;
      try {
        proposed = parseJsonObject(characterRun.raw);
      } catch (error) {
        proposed = { parse_error: String(error) };
      }

      appendHgEvent(sceneAgent.session, 'hg/move-proposed', {
        ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
        inference_id: characterInferenceId,
        character_inference_session_id: characterInferenceSessionId,
        role: 'character',
        character_id: characterId,
        character_turn_index: characterTurnIndex,
        attempt_index: attemptIndex,
        manifest_id: characterManifestId,
        proposed_move: proposed,
        raw_model_output: characterRun.raw,
      });

      const validation = await api.validateMove({
        inference_id: characterInferenceId,
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        character_id: characterId,
        role,
        turn_index: expectedTurnIndex,
        attempt_index: attemptIndex,
        proposed_move: proposed,
        raw_model_output: characterRun.raw,
      });

      if (!validation.accepted) {
        appendHgEvent(sceneAgent.session, 'hg/move-rejected', {
          ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
          inference_id: characterInferenceId,
          character_inference_session_id: characterInferenceSessionId,
          role: 'character',
          character_id: characterId,
          character_turn_index: characterTurnIndex,
          attempt_index: attemptIndex,
          validation_class: String(validation.validation_class ?? 'unknown'),
          reason: String(validation.reason ?? ''),
          retryable: Boolean(validation.retryable),
        });
        attemptIndex += 1;
        continue;
      }

      const commit = await api.commitMove({
        inference_id: characterInferenceId,
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        character_id: characterId,
        validated_move: validation.normalized_move ?? proposed,
        director_decision: directorDecision,
        expected_turn_index: expectedTurnIndex,
      });

      if (!commit.committed) {
        appendHgEvent(sceneAgent.session, 'hg/move-rejected', {
          ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
          inference_id: characterInferenceId,
          character_inference_session_id: characterInferenceSessionId,
          role: 'character',
          character_id: characterId,
          character_turn_index: characterTurnIndex,
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
        ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
        inference_id: characterInferenceId,
        character_inference_session_id: characterInferenceSessionId,
        role: 'character',
        character_id: characterId,
        character_turn_index: characterTurnIndex,
        attempt_index: attemptIndex,
        manifest_id: characterManifestId,
        continuity_turn_index: continuityTurnIndex,
        domain_commit_id: domainCommitId,
      });
    }

    return {
      committed,
      characterId,
      continuityTurnIndex,
      domainCommitId,
      characterManifestId,
      characterInferenceSessionId,
    };
  }

  async _runNarratorPresentation({
    api,
    sceneAgent,
    sceneSessionId,
    hgSceneId,
    hgRoundId,
    characterId,
    domainCommitId,
    continuityTurnIndex,
    narratorInferenceId,
    mockNarratorResponses,
    characterTurnIndex,
  }) {
    const manifest = await api.prepareNarratorContext({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      inference_id: narratorInferenceId,
      character_id: characterId,
      domain_commit_id: domainCommitId,
      continuity_turn_index: continuityTurnIndex,
    });
    const manifestId = String(manifest.manifest_id);

    appendHgEvent(sceneAgent.session, 'hg/narrator-started', {
      ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
      inference_id: narratorInferenceId,
      role: 'narrator',
      character_id: characterId,
      character_turn_index: characterTurnIndex,
      manifest_id: manifestId,
      domain_commit_id: domainCommitId,
      continuity_turn_index: continuityTurnIndex,
    });

    try {
      const narratorRun = await this._runEphemeralInference({
        inferenceId: narratorInferenceId,
        prompt: 'Render the committed character move as scene narration only.',
        manifest,
        mockResponses: mockNarratorResponses?.length
          ? mockNarratorResponses
          : ['She nodded thoughtfully, taking in the workshop around her.'],
      });
      const presentationText = narratorRun.raw.trim();
      if (!presentationText) {
        throw new Error('narrator produced empty presentation output');
      }

      appendHgEvent(sceneAgent.session, 'hg/narrator-completed', {
        ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
        inference_id: narratorInferenceId,
        narrator_inference_session_id: narratorRun.inferenceSessionId,
        role: 'narrator',
        character_id: characterId,
        character_turn_index: characterTurnIndex,
        manifest_id: manifestId,
        domain_commit_id: domainCommitId,
        continuity_turn_index: continuityTurnIndex,
        presentation_text: presentationText,
      });

      return {
        presentation_rendered: true,
        presentation_text: presentationText,
        presentation_failed: false,
        narrator_inference_session_id: narratorRun.inferenceSessionId,
        narrator_manifest_id: manifestId,
      };
    } catch (error) {
      appendHgEvent(sceneAgent.session, 'hg/narrator-failed', {
        ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
        inference_id: narratorInferenceId,
        role: 'narrator',
        character_id: characterId,
        character_turn_index: characterTurnIndex,
        manifest_id: manifestId,
        domain_commit_id: domainCommitId,
        continuity_turn_index: continuityTurnIndex,
        reason: String(error?.message ?? error),
        presentation_failure_class: 'runtime_render',
        canon_preserved: true,
      });
      return {
        presentation_rendered: false,
        presentation_text: null,
        presentation_failed: true,
        presentation_failure_reason: String(error?.message ?? error),
        narrator_manifest_id: manifestId,
      };
    }
  }

  async runRound(options) {
    const api = this._domainClient(options.domainApi?.baseUrl);
    const mockDirectorResponses = [...(options.mockDirectorResponses ?? [])];
    const mockCharacterTurnResponses = options.mockCharacterTurnResponses
      ?? (options.mockCharacterResponses ? [options.mockCharacterResponses] : []);
    const mockNarratorTurnResponses = options.mockNarratorTurnResponses
      ?? (options.mockNarratorResponses ? [options.mockNarratorResponses] : []);

    let hgSceneId = options.hgSceneId;
    if (!hgSceneId) {
      const created = await api.createScene(options.createScene ?? { cast: ['Alice', 'Bob'] });
      hgSceneId = String(created.hg_scene_id);
    }
    const round = await api.startRound({ hg_scene_id: hgSceneId });
    const hgRoundId = String(round.hg_round_id);
    const initialTurnIndex = Number(round.turn_index ?? 0);
    const sceneState = await api.getSceneState(hgSceneId);
    const castSize = Array.isArray(sceneState.present_characters)
      ? sceneState.present_characters.length
      : 2;
    const defensiveTurnCeiling = Number(
      options.defensiveTurnCeiling
      ?? options.maxCharacterTurns
      ?? Math.max(castSize, 1) * 2,
    );

    const sceneSessionId = SessionId(`hg-scene-${hgSceneId}`);
    const sceneAgent = this.ctx.agentLoop.create(sceneSessionId, {
      provider: HG_MOCK_PROVIDER,
      model: HG_MOCK_MODEL,
    });

    appendHgEvent(sceneAgent.session, 'hg/round-started', {
      ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
      turn_index: initialTurnIndex,
      defensive_turn_ceiling: defensiveTurnCeiling,
    });

    const characterTurns = [];
    const actorsUsedThisRound = [];
    let directorResponseIndex = 0;
    let directorAttemptSeed = 0;
    let completionReason = null;
    let lastDirectorInferenceSessionId = null;
    let characterRoles = {};

    while (true) {
      if (characterTurns.length >= defensiveTurnCeiling) {
        completionReason = 'defensive_turn_ceiling';
        break;
      }

      const eligibility = await api.getEligibleActors({
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
      });
      const eligibilitySnapshot = eligibilityTrace(eligibility);
      characterRoles = eligibility.character_roles ?? {};
      const eligibleActors = eligibility.eligible_actors ?? [];

      if (!eligibleActors.length) {
        completionReason = 'no_eligible_actors';
        appendHgEvent(sceneAgent.session, 'hg/eligibility-exhausted', {
          ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
          eligibility_snapshot: eligibilitySnapshot,
          actors_used_this_round: actorsUsedThisRound,
        });
        break;
      }

      appendHgEvent(sceneAgent.session, 'hg/eligibility-snapshot', {
        ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
        character_turn_index: characterTurns.length,
        eligibility_snapshot: eligibilitySnapshot,
        actors_used_this_round: actorsUsedThisRound,
      });

      const directorInferenceId = `inf-director-${characterTurns.length}-${crypto.randomUUID()}`;
      const directorPhase = await this._runDirectorPhase({
        api,
        sceneAgent,
        sceneSessionId,
        hgSceneId,
        hgRoundId,
        directorInferenceId,
        directorAttemptSeed,
        mockDirectorResponses,
        directorResponseIndex,
        actorsUsedThisRound,
        turnIndex: initialTurnIndex,
        eligibilitySnapshot,
      });
      directorAttemptSeed = directorPhase.directorAttempt;
      directorResponseIndex = directorPhase.directorResponseIndex;
      lastDirectorInferenceSessionId = directorPhase.directorInferenceSessionId;

      if (!directorPhase.accepted) {
        completionReason = 'director_failure';
        break;
      }
      if (directorPhase.endRound) {
        completionReason = 'director_end_round';
        break;
      }
      if (!directorPhase.selectedCharacterId) {
        completionReason = 'director_failure';
        break;
      }

      const characterTurnIndex = characterTurns.length;
      const characterInferenceId = `inf-character-${characterTurnIndex}-${crypto.randomUUID()}`;
      const characterResponses = mockCharacterTurnResponses[characterTurnIndex] ?? [];
      const characterTurn = await this._runCharacterTurn({
        api,
        sceneAgent,
        sceneSessionId,
        hgSceneId,
        hgRoundId,
        characterId: directorPhase.selectedCharacterId,
        directorDecision: directorPhase.directorDecision,
        characterInferenceId,
        mockResponses: characterResponses,
        characterTurnIndex,
        characterRole: roleForCharacter(directorPhase.selectedCharacterId, characterRoles),
      });

      if (!characterTurn.committed) {
        completionReason = 'character_failure';
        break;
      }

      actorsUsedThisRound.push(characterTurn.characterId);

      const narratorInferenceId = `inf-narrator-${characterTurnIndex}-${crypto.randomUUID()}`;
      const narratorResponses = mockNarratorTurnResponses[characterTurnIndex] ?? [];
      const narratorResult = await this._runNarratorPresentation({
        api,
        sceneAgent,
        sceneSessionId,
        hgSceneId,
        hgRoundId,
        characterId: characterTurn.characterId,
        domainCommitId: characterTurn.domainCommitId,
        continuityTurnIndex: characterTurn.continuityTurnIndex,
        narratorInferenceId,
        mockNarratorResponses: narratorResponses,
        characterTurnIndex,
      });

      characterTurns.push({
        character_turn_index: characterTurnIndex,
        character_id: characterTurn.characterId,
        director_decision: directorPhase.directorDecision,
        domain_commit_id: characterTurn.domainCommitId,
        continuity_turn_index: characterTurn.continuityTurnIndex,
        character_inference_session_id: characterTurn.characterInferenceSessionId,
        narrator_inference_session_id: narratorResult.narrator_inference_session_id ?? null,
        presentation_rendered: narratorResult.presentation_rendered,
        presentation_text: narratorResult.presentation_text,
        presentation_failed: narratorResult.presentation_failed,
      });
    }

    if (completionReason === null) {
      completionReason = 'no_eligible_actors';
    }

    const { completion_status: completionStatus, completion_class: completionClass } =
      classifyRoundCompletion(completionReason);

    appendHgEvent(sceneAgent.session, 'hg/round-completed', {
      ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
      completion_status: completionStatus,
      completion_class: completionClass,
      completion_reason: completionReason,
      character_turn_count: characterTurns.length,
      actors_used_this_round: actorsUsedThisRound,
      defensive_turn_ceiling: defensiveTurnCeiling,
    });

    const lastTurn = characterTurns[characterTurns.length - 1] ?? null;
    return {
      completion_status: completionStatus,
      completion_class: completionClass,
      completion_reason: completionReason,
      round_completed: completionStatus === 'completed',
      character_turn_count: characterTurns.length,
      character_turns: characterTurns,
      actors_used_this_round: actorsUsedThisRound,
      committed: characterTurns.length > 0,
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      dsh_scene_session_id: String(sceneSessionId),
      director_inference_session_id: lastDirectorInferenceSessionId,
      character_inference_session_id: lastTurn?.character_inference_session_id ?? null,
      narrator_inference_session_id: lastTurn?.narrator_inference_session_id ?? null,
      selected_character_id: lastTurn?.character_id ?? null,
      continuity_turn_index: lastTurn?.continuity_turn_index ?? null,
      domain_commit_id: lastTurn?.domain_commit_id ?? null,
      presentation_rendered: lastTurn?.presentation_rendered ?? false,
      presentation_text: lastTurn?.presentation_text ?? null,
      presentation_failed: lastTurn?.presentation_failed ?? false,
      defensive_turn_ceiling: defensiveTurnCeiling,
      scene_events: [...sceneAgent.session.events],
      boundary_metrics: api.metrics,
    };
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
}
