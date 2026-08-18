import { Service } from '@deepseek-ai/cordis';
import AgentLoop from '@deepseek-ai/dsh-agent-loop';
import { mountAgentLoopTestDependencies } from '@deepseek-ai/dsh-agent-loop-testkit';
import { SessionId } from '@deepseek-ai/dsh-session';

import { createDomainApiClient } from '../../lib/domain-api-client.mjs';
import HgContextBridge from '../hg-context-bridge/service.mjs';
import HgPhaseExecutors, { roleForCharacter } from '../hg-phase-executors/index.mjs';
import HgTraceEmitter from '../hg-trace-emitter/service.mjs';
import {
  agentOptionsFromProfile,
  mockInferenceProfile,
  resolveRoleProfiles,
} from '../../lib/inference-profile.mjs';
import {
  LIVE_CHARACTER_PROMPT,
  LIVE_DIRECTOR_PROMPT,
  LIVE_NARRATOR_PROMPT,
} from '../../lib/live-inference-prompts.mjs';
import { parseJsonObject } from '../../lib/inference-utils.mjs';

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
    if (!this.ctx.hgContextBridge) {
      new HgContextBridge(this.ctx);
    }
    HgTraceEmitter.ensure(this.ctx);
    HgPhaseExecutors.ensure(this.ctx, this.config);
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

  async runRound(options) {
    const api = this._domainClient(options.domainApi?.baseUrl);
    const phaseExecutors = this.ctx.hgPhaseExecutors;
    const trace = this.ctx.hgTraceEmitter;
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
    const scope = { hgSceneId, hgRoundId, sceneSessionId };

    trace.emit(sceneAgent.session, 'hg/round-started', scope, {
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
        trace.emit(sceneAgent.session, 'hg/eligibility-exhausted', scope, {
          eligibility_snapshot: eligibilitySnapshot,
          actors_used_this_round: actorsUsedThisRound,
        });
        break;
      }

      trace.emit(sceneAgent.session, 'hg/eligibility-snapshot', scope, {
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

      trace.emit(sceneAgent.session, 'hg/participation-decision', scope, {
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
        directorPhase = await phaseExecutors.runDirector({
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
      const characterTurn = await phaseExecutors.runCharacter({
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
      const narratorResult = await phaseExecutors.runNarrator({
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

    trace.emit(sceneAgent.session, 'hg/round-completed', scope, {
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
    const phaseExecutors = this.ctx.hgPhaseExecutors;
    const trace = this.ctx.hgTraceEmitter;
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
    const scope = { hgSceneId, hgRoundId, sceneSessionId };

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

      const inferenceRun = await phaseExecutors.runEphemeralInference({
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
        trace.emit(sceneAgent.session, 'hg/inference-failed', scope, {
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

      trace.emit(sceneAgent.session, 'hg/move-proposed', scope, {
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
        trace.emit(sceneAgent.session, 'hg/move-rejected', scope, {
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
        trace.emit(sceneAgent.session, 'hg/move-rejected', scope, {
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
      trace.emit(sceneAgent.session, 'hg/move-committed', scope, {
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
