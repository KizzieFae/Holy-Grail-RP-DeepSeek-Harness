import { Service } from '@deepseek-ai/cordis';
import AgentLoop from '@deepseek-ai/dsh-agent-loop';
import { mountAgentLoopTestDependencies } from '@deepseek-ai/dsh-agent-loop-testkit';
import { createUserMessage } from '@deepseek-ai/dsh-llm';
import { SessionId } from '@deepseek-ai/dsh-session';

import { createDomainApiClient } from '../../lib/domain-api-client.mjs';
import {
  agentOptionsFromProfile,
  inferenceAttemptLimit,
  mockInferenceProfile,
  resolveInferenceProfile,
  resolveRoleProfiles,
} from '../../lib/inference-profile.mjs';
import { extractInferenceTrace } from '../../lib/inference-trace.mjs';
import {
  LIVE_CHARACTER_PROMPT,
  LIVE_DIRECTOR_PROMPT,
  LIVE_NARRATOR_PROMPT,
} from '../../lib/live-inference-prompts.mjs';
import {
  finalAssistantText,
  parseJsonObject,
  registerManifestContributions,
  waitForIdle,
} from '../../lib/inference-utils.mjs';
import { HgMockLlmAdapter } from '../../mock-llm-adapter.mjs';
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
    eligibility_snapshot_id: eligibility.eligibility_snapshot_id ?? null,
    eligible_actors: eligibility.eligible_actors ?? [],
    actors_used_this_round: eligibility.actors_used_this_round ?? [],
    present_characters: eligibility.present_characters ?? [],
    offstage_characters: eligibility.offstage_characters ?? [],
    absent_but_relevant: eligibility.absent_but_relevant ?? [],
    actors: eligibility.actors ?? [],
  };
}

function participationTrace(participation) {
  return {
    eligibility_snapshot_id: participation.eligibility_snapshot_id ?? null,
    selection_mode: participation.selection_mode ?? null,
    selected_actor: participation.selected_actor ?? null,
    director_required: Boolean(participation.director_required),
    director_constraint_actor: participation.director_constraint_actor ?? null,
    participation_sources: participation.participation_sources ?? [],
    reason: participation.reason ?? '',
    forced_designation_ignored: Boolean(participation.forced_designation_ignored),
    forced_designation_ignore_reason: participation.forced_designation_ignore_reason ?? null,
    continuation_c2_skip: Boolean(participation.continuation_c2_skip),
  };
}

function syntheticDirectorDecision(characterId, reason) {
  return {
    next_actor: characterId,
    end_round: false,
    reason: reason ?? `Participation policy selected ${characterId}.`,
    environment_event: '',
    tension_shift: '',
    source: 'participation_policy',
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
    if (options.inference?.mountDeepSeek || this.config.inference?.mountDeepSeek) {
      const { mountDeepSeekProvider } = await import('../../lib/mount-deepseek-provider.mjs');
      await mountDeepSeekProvider(this.ctx, {
        ...this.config.inference?.deepseek,
        ...options.inference?.deepseek,
      });
    }
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
    modelProfile,
  }) {
    const profile = resolveInferenceProfile(this.config.inference, modelProfile);
    let disposeAdapter = () => {};

    if (profile.kind === 'mock') {
      const adapter = new HgMockLlmAdapter(
        mockResponses.length ? mockResponses : ['{}'],
      );
      disposeAdapter = this.ctx.llm.registerAdapter([profile.provider], adapter);
    }

    const agent = this.ctx.agentLoop.create(
      SessionId(`hg-inf-${inferenceId}`),
      agentOptionsFromProfile(profile),
    );
    const releaseManifest = registerManifestContributions(agent, manifest?.contributions);
    agent.followup(
      createUserMessage({
        content: [{ type: 'text', text: prompt }],
        source: { kind: 'user' },
      }),
    );
    await waitForIdle(this.ctx, agent);

    const contributionIds = (manifest?.contributions ?? []).map(
      (entry) => String(entry.contribution_id),
    );
    const trace = extractInferenceTrace(agent.session.events, {
      provider: profile.provider,
      model: profile.model,
      reasoningEffort: profile.reasoningEffort ?? null,
      manifestId: manifest?.manifest_id ?? null,
      contributionIds,
    });
    const raw = trace.assistant_text;
    releaseManifest();
    disposeAdapter();

    return {
      raw,
      inferenceSessionId: String(agent.id),
      trace,
      failed: trace.failed,
      failure: trace.failure,
      inferenceSessionEvents: [...agent.session.events],
    };
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
    participationContext,
    modelProfile,
    liveMaxAttempts,
    prompt,
  }) {
    let directorAttempt = directorAttemptSeed;
    let directorAccepted = false;
    let directorDecision = null;
    let directorManifestId = '';
    let selectedCharacterId = null;
    let directorInferenceSessionId = null;
    let directorInferenceTrace = null;
    let endRound = false;
    const attemptLimit = inferenceAttemptLimit(mockDirectorResponses, liveMaxAttempts);
    let attemptsUsed = 0;

    while (!directorAccepted && attemptsUsed < attemptLimit) {
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
        prompt: prompt ?? 'Produce your director decision as JSON only.',
        manifest,
        mockResponses: mockDirectorResponses.length
          ? [mockDirectorResponses[directorResponseIndex]]
          : [],
        modelProfile,
      });
      directorInferenceSessionId = directorRun.inferenceSessionId;
      directorInferenceTrace = directorRun.trace;

      if (directorRun.failed) {
        appendHgEvent(sceneAgent.session, 'hg/inference-failed', {
          ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
          inference_id: directorInferenceId,
          director_inference_session_id: directorInferenceSessionId,
          role: 'director',
          attempt_index: directorAttempt,
          manifest_id: directorManifestId,
          failure: directorRun.failure,
          inference_trace: directorInferenceTrace,
        });
        directorAttempt += 1;
        directorResponseIndex += 1;
        attemptsUsed += 1;
        continue;
      }

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
        inference_trace: directorInferenceTrace,
      });

      const validation = await api.validateDirectorDecision({
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        inference_id: directorInferenceId,
        turn_index: turnIndex,
        attempt_index: directorAttempt,
        proposed_decision: proposed,
        raw_model_output: directorRun.raw,
        eligibility_snapshot_id: participationContext?.eligibilitySnapshotId ?? eligibilitySnapshot?.eligibility_snapshot_id,
        director_constraint_actor: participationContext?.directorConstraintActor ?? null,
        continuation_c2_skip: Boolean(participationContext?.continuationC2Skip),
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
        attemptsUsed += 1;
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
      directorInferenceTrace,
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
    modelProfile,
    liveMaxAttempts,
    prompt,
  }) {
    const role = characterRole ?? roleForCharacter(characterId);
    let attemptIndex = 0;
    let committed = false;
    let continuityTurnIndex = null;
    let domainCommitId = null;
    let characterManifestId = '';
    let characterInferenceSessionId = null;
    let characterInferenceTrace = null;
    const attemptLimit = inferenceAttemptLimit(mockResponses, liveMaxAttempts);

    while (!committed && attemptIndex < attemptLimit) {
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
        prompt: prompt ?? 'Produce your character move as JSON only.',
        manifest,
        mockResponses: mockResponses.length ? [mockResponses[attemptIndex]] : [],
        modelProfile,
      });
      characterInferenceSessionId = characterRun.inferenceSessionId;
      characterInferenceTrace = characterRun.trace;

      if (characterRun.failed) {
        appendHgEvent(sceneAgent.session, 'hg/inference-failed', {
          ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
          inference_id: characterInferenceId,
          character_inference_session_id: characterInferenceSessionId,
          role: 'character',
          character_id: characterId,
          character_turn_index: characterTurnIndex,
          attempt_index: attemptIndex,
          manifest_id: characterManifestId,
          failure: characterRun.failure,
          inference_trace: characterInferenceTrace,
        });
        attemptIndex += 1;
        continue;
      }

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
        inference_trace: characterInferenceTrace,
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
      characterInferenceTrace,
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
    modelProfile,
    prompt,
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
      const narratorMockFallback = modelProfile?.kind === 'mock'
        ? ['She nodded thoughtfully, taking in the workshop around her.']
        : [];
      const narratorRun = await this._runEphemeralInference({
        inferenceId: narratorInferenceId,
        prompt: prompt ?? 'Render the committed character move as scene narration only.',
        manifest,
        mockResponses: mockNarratorResponses?.length
          ? mockNarratorResponses
          : narratorMockFallback,
        modelProfile,
      });

      if (narratorRun.failed) {
        throw new Error(narratorRun.failure?.message ?? 'narrator provider inference failed');
      }

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
        inference_trace: narratorRun.trace,
      });

      return {
        presentation_rendered: true,
        presentation_text: presentationText,
        presentation_failed: false,
        narrator_inference_session_id: narratorRun.inferenceSessionId,
        narrator_manifest_id: manifestId,
        narrator_inference_trace: narratorRun.trace,
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
    const roleProfiles = resolveRoleProfiles(options, this.config.inference);
    const liveMaxAttempts = Number(options.liveMaxAttempts ?? 3);
    const livePrompts = options.livePrompts ?? {};
    const roundStartedAt = Date.now();
    const roleTimings = {
      director_ms: [],
      character_ms: [],
      narrator_ms: [],
    };
    const roleTraces = {
      director: null,
      character: null,
      narrator: null,
    };

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
    const sceneAgent = this.ctx.agentLoop.create(
      sceneSessionId,
      agentOptionsFromProfile(mockInferenceProfile()),
    );

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
    let pendingForcedDesignation = options.forcedDesignation ?? options.forced_designation ?? null;
    let forcedDesignationConsumed = false;

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

      const participation = await api.getParticipationDecision({
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        eligibility_snapshot_id: eligibility.eligibility_snapshot_id,
        forced_designation: forcedDesignationConsumed ? null : pendingForcedDesignation,
      });
      const participationSnapshot = participationTrace(participation);

      appendHgEvent(sceneAgent.session, 'hg/participation-decision', {
        ...this._correlation({ hgSceneId, hgRoundId, sceneSessionId }),
        character_turn_index: characterTurns.length,
        participation: participationSnapshot,
        eligibility_snapshot: eligibilitySnapshot,
      });

      let directorPhase;
      if (participation.selection_mode === 'direct' && participation.selected_actor) {
        if ((participation.participation_sources ?? []).includes('forced_designation')) {
          forcedDesignationConsumed = true;
        }
        directorPhase = {
          accepted: true,
          endRound: false,
          directorDecision: syntheticDirectorDecision(
            participation.selected_actor,
            participation.reason,
          ),
          selectedCharacterId: participation.selected_actor,
          directorManifestId: null,
          directorInferenceSessionId: null,
          directorAttempt: directorAttemptSeed,
          directorResponseIndex,
          participationDirect: true,
        };
      } else {
        const directorInferenceId = `inf-director-${characterTurns.length}-${crypto.randomUUID()}`;
        const directorStartedAt = Date.now();
        directorPhase = await this._runDirectorPhase({
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
          participationContext: {
            eligibilitySnapshotId: eligibility.eligibility_snapshot_id,
            directorConstraintActor: participation.director_constraint_actor ?? null,
            continuationC2Skip: participation.continuation_c2_skip,
          },
          modelProfile: roleProfiles.director,
          liveMaxAttempts,
          prompt: livePrompts.director ?? LIVE_DIRECTOR_PROMPT,
        });
        roleTimings.director_ms.push(Date.now() - directorStartedAt);
        roleTraces.director = directorPhase.directorInferenceTrace ?? null;
        directorPhase.participationDirect = false;
      }
      directorAttemptSeed = directorPhase.directorAttempt;
      directorResponseIndex = directorPhase.directorResponseIndex;
      if (directorPhase.directorInferenceSessionId) {
        lastDirectorInferenceSessionId = directorPhase.directorInferenceSessionId;
      }

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
      const characterStartedAt = Date.now();
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
        modelProfile: roleProfiles.character,
        liveMaxAttempts,
        prompt: livePrompts.character ?? LIVE_CHARACTER_PROMPT,
      });
      roleTimings.character_ms.push(Date.now() - characterStartedAt);
      roleTraces.character = characterTurn.characterInferenceTrace ?? null;

      if (!characterTurn.committed) {
        completionReason = 'character_failure';
        break;
      }

      actorsUsedThisRound.push(characterTurn.characterId);

      const narratorInferenceId = `inf-narrator-${characterTurnIndex}-${crypto.randomUUID()}`;
      const narratorResponses = mockNarratorTurnResponses[characterTurnIndex] ?? [];
      const narratorStartedAt = Date.now();
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
        modelProfile: roleProfiles.narrator,
        prompt: livePrompts.narrator ?? LIVE_NARRATOR_PROMPT,
      });
      roleTimings.narrator_ms.push(Date.now() - narratorStartedAt);
      roleTraces.narrator = narratorResult.narrator_inference_trace ?? null;

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
      role_profiles: roleProfiles,
      role_inference_traces: roleTraces,
      round_timing_ms: {
        total: Date.now() - roundStartedAt,
        director: roleTimings.director_ms,
        character: roleTimings.character_ms,
        narrator: roleTimings.narrator_ms,
      },
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
    const sceneAgent = this.ctx.agentLoop.create(
      sceneSessionId,
      agentOptionsFromProfile(mockInferenceProfile()),
    );

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
    let inferenceTrace = null;
    let providerFailure = null;
    const mockResponses = options.mockResponses ?? [];
    const modelProfile = options.modelProfile ?? options.model_profile ?? null;
    const maxAttempts = mockResponses.length > 0 ? mockResponses.length : 1;

    while (attemptIndex < maxAttempts && !committed) {
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

      const inferenceRun = await this._runEphemeralInference({
        inferenceId: `${inferenceId}-${attemptIndex}`,
        prompt: options.prompt ?? (
          'Respond with a single JSON object only (no markdown). '
          + 'Schema: {"move_schema_version":2,"beats":[{"type":"action","action":"..."}],'
          + '"motivation":{"goal":"...","tactic":"...","emotional_driver":"...","risk_level":"low"},'
          + '"semantic_evaluation":{"decision":"no_covered_change"}}'
        ),
        manifest,
        mockResponses: mockResponses.length ? [mockResponses[attemptIndex]] : [],
        modelProfile,
      });
      inferenceTrace = inferenceRun.trace;

      if (inferenceRun.failed) {
        providerFailure = inferenceRun.failure;
        appendHgEvent(sceneAgent.session, 'hg/inference-failed', {
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
          provider: inferenceTrace?.provider ?? null,
          model: inferenceTrace?.model ?? null,
          failure: providerFailure,
          inference_trace: inferenceTrace,
        });
        break;
      }

      const { raw } = inferenceRun;

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
      inference_trace: inferenceTrace,
      provider_failure: providerFailure,
      scene_events: [...sceneAgent.session.events],
      boundary_metrics: api.metrics,
    };
  }
}
