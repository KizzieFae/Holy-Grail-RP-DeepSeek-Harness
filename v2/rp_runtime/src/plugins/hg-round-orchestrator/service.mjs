import { Service } from '@deepseek-ai/cordis';
import { SessionId } from '@deepseek-ai/dsh-session';

import { createDomainApiClient } from '../../lib/domain-api-client.mjs';
import { resolveRoundSession } from '../../lib/resolve-round-session.mjs';
import { runPostCommitLibrarianLifecycle } from '../../lib/librarian-proposal-orchestration.mjs';
import { runPlotCognitionPendingWorkLifecycle, runPostCommitPlotCognitionLifecycle } from '../../lib/plot-cognition-orchestration.mjs';
import { runStorytellerCognition } from '../../lib/storyteller-cognition-substrate.mjs';
import { buildStorytellerAdvisoryDecisionPatch } from '../../lib/execution-evidence/ni-evidence.mjs';
import { roleForCharacter } from '../hg-phase-executors/role-utils.mjs';
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
import {
  classifyRoundCompletion,
  eligibilityTrace,
  participationDirectorDecision,
  participationTrace,
} from './round-helpers.mjs';

/**
 * Round lifecycle orchestrator: eligibility, participation, phase sequencing,
 * completion classification, and application-facing round results.
 */
export default class HgRoundOrchestrator extends Service {
  static name = 'hgRoundOrchestrator';

  static inject = ['hgPhaseExecutors', 'hgTraceEmitter', 'agentLoop'];

  constructor(ctx, config = {}) {
    super(ctx, HgRoundOrchestrator.name);
    this.config = config;
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
    const mockSemanticEvaluatorTurnResponses = options.mockSemanticEvaluatorTurnResponses ?? [];
    const mockDirectorSemanticQaResponses = options.mockDirectorSemanticQaResponses ?? [];
    const mockNarratorSemanticQaResponses = options.mockNarratorSemanticQaResponses ?? [];
    const mockLibrarianProposalResponses = options.mockLibrarianProposalResponses ?? [];
    const mockPlotCognitionUpdateResponses = options.mockPlotCognitionUpdateResponses ?? [];
    const mockPlotCognitionInitResponse = options.mockPlotCognitionInitResponse ?? null;
    const plotCognitionDelayMs = Number(options.plotCognitionDelayMs ?? 0);
    const mockCharacterOrientationResponses = options.mockCharacterOrientationResponses
      ?? (options.mockCharacterOrientationResponse
        ? [options.mockCharacterOrientationResponse]
        : []);
    const mockCharacterMediationResponses = options.mockCharacterMediationResponses
      ?? (options.mockCharacterMediationResponse
        ? [options.mockCharacterMediationResponse]
        : []);
    const librarianProposalDelayMs = Number(options.librarianProposalDelayMs ?? 0);
    const DEFAULT_SEMANTIC_PASS = JSON.stringify({
      schema: 'hg_semantic_evaluation_result_v1',
      overall_result: 'pass',
      findings: [],
    });
    const DEFAULT_DIRECTOR_SEMANTIC_PASS = JSON.stringify({
      schema: 'hg_semantic_qa_result_v1',
      evaluation_target_role: 'director',
      evaluation_pass_id: 'director-qa-pass',
      overall_result: 'pass',
      findings: [],
    });
    const DEFAULT_NARRATOR_SEMANTIC_PASS = JSON.stringify({
      schema: 'hg_semantic_qa_result_v1',
      evaluation_target_role: 'narrator',
      evaluation_pass_id: 'narrator-qa-pass',
      overall_result: 'pass',
      findings: [],
    });
    const roleProfiles = resolveRoleProfiles(options, this.config.inference);
    const liveMaxAttempts = Number(options.liveMaxAttempts ?? 3);
    const livePrompts = options.livePrompts ?? {};
    const roundStartedAt = Date.now();
    const roleTimings = {
      director_ms: [],
      character_ms: [],
      narrator_ms: [],
      librarian_ms: [],
      plot_cognition_ms: [],
    };
    const roleTraces = {
      director: null,
      character: null,
      narrator: null,
    };

    const sessionInfo = await resolveRoundSession(api, options);
    const hgSessionId = sessionInfo.hgSessionId;
    const hgSceneId = sessionInfo.hgSceneId;
    const continuityVersion = sessionInfo.continuityVersion;

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

    const sceneSessionId = SessionId(`hg-exec-${crypto.randomUUID()}`);
    const sceneAgent = this.ctx.agentLoop.create(
      sceneSessionId,
      agentOptionsFromProfile(mockInferenceProfile()),
    );
    const scope = { hgSessionId, hgSceneId, hgRoundId, sceneSessionId };

    trace.emit(sceneAgent.session, 'hg/round-started', scope, {
      turn_index: initialTurnIndex,
      defensive_turn_ceiling: defensiveTurnCeiling,
      continuity_version: continuityVersion,
    });

    let storytellerRoundSummary = null;
    let storytellerAssessmentEvidenceId = null;
    if (options.skipStorytellerCognition !== true) {
      trace.emit(sceneAgent.session, 'hg/storyteller-started', scope, {});
      const storytellerInferenceId = `inf-storyteller-${hgRoundId}`;
      let storytellerResult;
      try {
        storytellerResult = await runStorytellerCognition({
          domainApi: api,
          hgSceneId,
          hgRoundId,
          inferenceId: storytellerInferenceId,
          runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
          mockOrientationResponse: options.mockStorytellerOrientationResponse ?? null,
          mockMediationResponse: options.mockStorytellerMediationResponse ?? null,
          mockAssessmentResponse: options.mockStorytellerAssessmentResponse ?? null,
          modelProfile: roleProfiles.storyteller ?? roleProfiles.director,
          evidenceContextBase: {
            hgSessionId,
            hgSceneId,
            hgRoundId,
            sceneSessionId,
          },
          allowDeterministicFallback: options.storytellerAllowDeterministicFallback !== false,
          recorder: phaseExecutors.executionEvidenceRecorder,
          hgSessionId,
        });
      } catch (error) {
        storytellerResult = {
          ok: false,
          stage: 'error',
          package: null,
          audit: { reason: String(error?.message ?? error ?? 'storyteller_error') },
        };
      }
      if (storytellerResult.ok && storytellerResult.package) {
        const bindResult = await api.bindStorytellerAdvisoryPackage({
          hg_scene_id: hgSceneId,
          hg_round_id: hgRoundId,
          package: storytellerResult.package,
          audit: storytellerResult.audit ?? null,
        });
        if (
          phaseExecutors.executionEvidenceRecorder?.isEnabled?.()
          && storytellerResult.assessmentRun?.evidenceId
          && hgSessionId
        ) {
          phaseExecutors.executionEvidenceRecorder.patchDecision(
            storytellerResult.assessmentRun.evidenceId,
            hgSessionId,
            buildStorytellerAdvisoryDecisionPatch({
              assessmentAccepted: Boolean(storytellerResult.assessmentFinalize?.accepted),
              assessmentReason: storytellerResult.assessmentFinalize?.reason ?? null,
              packageId: storytellerResult.package?.package_id ?? null,
              bindAccepted: Boolean(bindResult.accepted),
              bindRejectionReason: bindResult.reason ?? null,
              degradationLevel: storytellerResult.package?.degradation?.level ?? null,
            }),
          );
        }
        storytellerAssessmentEvidenceId = storytellerResult.assessmentRun?.evidenceId
          ?? storytellerResult.audit?.assessment_evidence_id
          ?? null;
        storytellerRoundSummary = {
          attempted: true,
          bound: Boolean(bindResult.accepted),
          package_id: storytellerResult.package.package_id ?? null,
          degradation_level: storytellerResult.package.degradation?.level ?? 'none',
          mapped_preview: bindResult.mapped_preview ?? null,
          assessment_evidence_id: storytellerAssessmentEvidenceId,
        };
        trace.emit(sceneAgent.session, 'hg/storyteller-completed', scope, {
          package_id: storytellerRoundSummary.package_id,
          degradation_level: storytellerRoundSummary.degradation_level,
          bound: storytellerRoundSummary.bound,
          mapped_preview: storytellerRoundSummary.mapped_preview,
        });
      } else {
        storytellerRoundSummary = {
          attempted: true,
          bound: false,
          stage: storytellerResult.stage,
          reason: storytellerResult.audit?.reason ?? storytellerResult.stage,
        };
        trace.emit(sceneAgent.session, 'hg/storyteller-skipped', scope, storytellerRoundSummary);
      }
    }

    const characterTurns = [];
    const actorsUsedThisRound = [];
    let directorResponseIndex = 0;
    let directorAttemptSeed = 0;
    let completionReason = null;
    let lastDirectorInferenceSessionId = null;
    let characterRoles = {};
    let pendingForcedDesignation = options.forcedDesignation ?? options.forced_designation ?? null;
    let forcedDesignationConsumed = false;
    const librarianOrchestrationByCommit = new Map();
    const plotCognitionOrchestrationByCommit = new Map();
    let plotCognitionResumeSummary = null;

    if (options.skipPlotCognitionOrchestration !== true) {
      const resumeStartedAt = Date.now();
      plotCognitionResumeSummary = await runPlotCognitionPendingWorkLifecycle({
        domainApi: api,
        trace,
        sceneAgent,
        scope,
        hgSceneId,
        inferenceId: `inf-plot-cog-resume-${hgRoundId}`,
        runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
        mockUpdateResponse: mockPlotCognitionUpdateResponses[0] ?? null,
        mockInitResponse: mockPlotCognitionInitResponse,
        modelProfile: roleProfiles.storyteller ?? roleProfiles.director,
        evidenceContextBase: {
          hgSessionId,
          hgSceneId,
          hgRoundId,
          sceneSessionId,
        },
      });
      roleTimings.plot_cognition_ms.push(Date.now() - resumeStartedAt);
      trace.emit(sceneAgent.session, 'hg/plot-cognition-resume', scope, {
        ok: plotCognitionResumeSummary.ok === true,
        operation: plotCognitionResumeSummary.operation ?? null,
        stage: plotCognitionResumeSummary.stage ?? null,
        fresh_after: plotCognitionResumeSummary.freshAfter === true,
      });
    }

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
          directorDecision: participationDirectorDecision(
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
        const directorSemanticMocks = mockDirectorSemanticQaResponses.length
          ? mockDirectorSemanticQaResponses
          : mockDirectorResponses.map(() => DEFAULT_DIRECTOR_SEMANTIC_PASS);
        directorPhase = await phaseExecutors.runDirector({
          api,
          sceneAgent,
          sceneSessionId,
          hgSessionId,
          hgSceneId,
          hgRoundId,
          directorInferenceId,
          directorAttemptSeed,
          mockDirectorResponses,
          mockDirectorSemanticQaResponses: directorSemanticMocks,
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
          semanticEvaluatorProfile: roleProfiles.semantic_evaluator,
          liveMaxAttempts,
          prompt: livePrompts.director ?? LIVE_DIRECTOR_PROMPT,
          directorSemanticQaEnabled: options.directorSemanticQaEnabled !== false,
          storytellerAssessmentEvidenceId: storytellerRoundSummary?.bound
            ? storytellerAssessmentEvidenceId
            : null,
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
      let participationEvidenceId = null;
      if (directorPhase.participationDirect) {
        participationEvidenceId = phaseExecutors.executionEvidenceRecorder
          .recordParticipationDecision({
            hgSessionId,
            hgSceneId,
            hgRoundId,
            characterTurnIndex,
            participation: participationSnapshot,
            eligibilitySnapshot,
            selectedCharacterId: directorPhase.selectedCharacterId,
            characterInferenceId,
          });
      }
      const characterResponses = mockCharacterTurnResponses[characterTurnIndex] ?? [];
      const semanticMocks = mockSemanticEvaluatorTurnResponses[characterTurnIndex]
        ?? characterResponses.map(() => DEFAULT_SEMANTIC_PASS);
      const characterStartedAt = Date.now();
      const characterTurn = await phaseExecutors.runCharacter({
        api,
        sceneAgent,
        sceneSessionId,
        hgSessionId,
        hgSceneId,
        hgRoundId,
        characterId: directorPhase.selectedCharacterId,
        directorDecision: directorPhase.directorDecision,
        characterInferenceId,
        mockResponses: characterResponses,
        mockSemanticEvaluatorResponses: semanticMocks,
        characterTurnIndex,
        characterRole: roleForCharacter(directorPhase.selectedCharacterId, characterRoles),
        modelProfile: roleProfiles.character,
        semanticEvaluatorProfile: roleProfiles.semantic_evaluator,
        liveMaxAttempts,
        prompt: livePrompts.character ?? LIVE_CHARACTER_PROMPT,
        participationEvidenceId,
        mockCharacterOrientationResponse: mockCharacterOrientationResponses[characterTurnIndex] ?? null,
        mockCharacterMediationResponse: mockCharacterMediationResponses[characterTurnIndex] ?? null,
      });
      roleTimings.character_ms.push(Date.now() - characterStartedAt);
      roleTraces.character = characterTurn.characterInferenceTrace ?? null;

      if (!characterTurn.committed) {
        completionReason = 'character_failure';
        break;
      }

      actorsUsedThisRound.push(characterTurn.characterId);

      if (storytellerRoundSummary?.bound) {
        const storytellerState = await api.getStorytellerRoundState({
          hgSceneId,
          hgRoundId,
        });
        if (!storytellerState.is_valid && storytellerState.invalidation_reason) {
          trace.emit(sceneAgent.session, 'hg/storyteller-invalidated', scope, {
            package_id: storytellerState.package_id,
            invalidation_reason: storytellerState.invalidation_reason,
            character_turn_index: characterTurnIndex,
          });
          storytellerRoundSummary = {
            ...storytellerRoundSummary,
            invalidated: true,
            invalidation_reason: storytellerState.invalidation_reason,
          };
        }
      }

      const narratorInferenceId = `inf-narrator-${characterTurnIndex}-${crypto.randomUUID()}`;
      const librarianInferenceId = `inf-librarian-${characterTurnIndex}-${crypto.randomUUID()}`;
      const plotCognitionInferenceId = `inf-plot-cog-${characterTurnIndex}-${crypto.randomUUID()}`;
      const domainCommitId = characterTurn.domainCommitId;

      if (librarianOrchestrationByCommit.has(domainCommitId)) {
        completionReason = 'librarian_orchestration_duplicate';
        break;
      }
      if (plotCognitionOrchestrationByCommit.has(domainCommitId)) {
        completionReason = 'plot_cognition_orchestration_duplicate';
        break;
      }

      const narratorResponses = mockNarratorTurnResponses[characterTurnIndex] ?? [];
      const narratorSemanticMocks = mockNarratorSemanticQaResponses.length
        ? mockNarratorSemanticQaResponses
        : (narratorResponses.length
          ? narratorResponses.map(() => DEFAULT_NARRATOR_SEMANTIC_PASS)
          : [DEFAULT_NARRATOR_SEMANTIC_PASS, DEFAULT_NARRATOR_SEMANTIC_PASS]);
      const librarianMockResponse = typeof mockLibrarianProposalResponses === 'function'
        ? mockLibrarianProposalResponses({
          domainCommitId,
          characterTurnIndex,
          hgRoundId,
        })
        : mockLibrarianProposalResponses[characterTurnIndex] ?? null;

      const librarianStartedAt = Date.now();
      let librarianJoinPromise;
      if (options.skipLibrarianProposalGeneration === true) {
        librarianJoinPromise = Promise.resolve({
          ok: true,
          terminal: true,
          skipped: true,
          blockingPersistenceFailure: false,
          stage: 'skipped',
        });
      } else {
        librarianJoinPromise = runPostCommitLibrarianLifecycle({
          domainApi: api,
          trace,
          sceneAgent,
          scope,
          hgSceneId,
          hgRoundId,
          characterTurnIndex,
          domainCommitId,
          continuityTurnIndex: characterTurn.continuityTurnIndex,
          librarianInferenceId,
          runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
          mockResponse: librarianMockResponse,
          modelProfile: roleProfiles.librarian ?? roleProfiles.director,
          evidenceContextBase: {
            hgSessionId,
            hgSceneId,
            hgRoundId,
            sceneSessionId,
          },
          delayMs: librarianProposalDelayMs,
          recorder: phaseExecutors.executionEvidenceRecorder,
          characterMoveEvidenceId: characterTurn.committedCharacterEvidenceId ?? null,
        });
      }
      librarianOrchestrationByCommit.set(domainCommitId, librarianJoinPromise);

      const plotCognitionMockResponse = typeof mockPlotCognitionUpdateResponses === 'function'
        ? mockPlotCognitionUpdateResponses
        : mockPlotCognitionUpdateResponses[characterTurnIndex] ?? null;
      const plotCognitionStartedAt = Date.now();
      let plotCognitionJoinPromise;
      if (options.skipPlotCognitionOrchestration === true) {
        plotCognitionJoinPromise = Promise.resolve({
          ok: true,
          skipped: true,
          terminal: true,
          stage: 'skipped',
        });
      } else {
        plotCognitionJoinPromise = runPostCommitPlotCognitionLifecycle({
          domainApi: api,
          trace,
          sceneAgent,
          scope,
          hgSceneId,
          inferenceId: plotCognitionInferenceId,
          runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
          mockUpdateResponse: plotCognitionMockResponse,
          modelProfile: roleProfiles.storyteller ?? roleProfiles.director,
          evidenceContextBase: {
            hgSessionId,
            hgSceneId,
            hgRoundId,
            sceneSessionId,
            domainCommitId,
          },
          delayMs: plotCognitionDelayMs,
        });
      }
      plotCognitionOrchestrationByCommit.set(domainCommitId, plotCognitionJoinPromise);

      const narratorStartedAt = Date.now();
      const narratorPromise = phaseExecutors.runNarrator({
        api,
        sceneAgent,
        sceneSessionId,
        hgSessionId,
        hgSceneId,
        hgRoundId,
        characterId: characterTurn.characterId,
        domainCommitId: characterTurn.domainCommitId,
        continuityTurnIndex: characterTurn.continuityTurnIndex,
        narratorInferenceId,
        mockNarratorResponses: narratorResponses,
        mockNarratorSemanticQaResponses: narratorSemanticMocks,
        characterTurnIndex,
        modelProfile: roleProfiles.narrator,
        semanticEvaluatorProfile: roleProfiles.semantic_evaluator,
        narratorSemanticQaEnabled: options.narratorSemanticQaEnabled !== false,
        prompt: livePrompts.narrator ?? LIVE_NARRATOR_PROMPT,
      });

      const narratorResult = await narratorPromise;
      roleTimings.narrator_ms.push(Date.now() - narratorStartedAt);
      roleTraces.narrator = narratorResult.narrator_inference_trace ?? null;

      const librarianResult = await librarianJoinPromise;
      roleTimings.librarian_ms.push(Date.now() - librarianStartedAt);

      const plotCognitionResult = await plotCognitionJoinPromise;
      roleTimings.plot_cognition_ms.push(Date.now() - plotCognitionStartedAt);

      trace.emit(sceneAgent.session, 'hg/plot-cognition-join', scope, {
        domain_commit_id: domainCommitId,
        character_turn_index: characterTurnIndex,
        plot_cognition_inference_id: plotCognitionInferenceId,
        ok: plotCognitionResult.ok === true,
        operation: plotCognitionResult.operation ?? null,
        stage: plotCognitionResult.stage ?? null,
        fresh_after: plotCognitionResult.freshAfter === true,
        pending_preserved: plotCognitionResult.pendingPreserved === true,
      });

      trace.emit(sceneAgent.session, 'hg/librarian-proposal-join', scope, {
        domain_commit_id: domainCommitId,
        character_turn_index: characterTurnIndex,
        librarian_inference_id: librarianInferenceId,
        narrator_inference_session_id: narratorResult.narrator_inference_session_id ?? null,
        blocking_persistence_failure: Boolean(librarianResult.blockingPersistenceFailure),
        terminal: Boolean(librarianResult.terminal),
        stage: librarianResult.stage ?? null,
      });

      if (librarianResult.blockingPersistenceFailure) {
        completionReason = 'librarian_persistence_failure';
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
          narrative_visibility: narratorResult.narrative_visibility ?? null,
          presentation_failed: narratorResult.presentation_failed,
          inference_outcome: narratorResult.inference_outcome,
          librarian_inference_id: librarianInferenceId,
          librarian_stage: librarianResult.stage ?? null,
          librarian_blocking_persistence_failure: true,
        });
        break;
      }

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
        narrative_visibility: narratorResult.narrative_visibility ?? null,
        presentation_failed: narratorResult.presentation_failed,
        inference_outcome: narratorResult.inference_outcome,
        librarian_inference_id: librarianInferenceId,
        librarian_stage: librarianResult.stage ?? null,
        librarian_degradation_mode: librarianResult.degradationMode ?? null,
        librarian_terminal: librarianResult.terminal === true,
        plot_cognition_inference_id: plotCognitionInferenceId,
        plot_cognition_stage: plotCognitionResult.stage ?? null,
        plot_cognition_ok: plotCognitionResult.ok === true,
        plot_cognition_fresh_after: plotCognitionResult.freshAfter === true,
        plot_cognition_pending_preserved: plotCognitionResult.pendingPreserved === true,
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
    const finalSceneState = await api.getSceneState(hgSceneId);

    return {
      completion_status: completionStatus,
      completion_class: completionClass,
      completion_reason: completionReason,
      round_completed: completionStatus === 'completed',
      character_turn_count: characterTurns.length,
      character_turns: characterTurns,
      actors_used_this_round: actorsUsedThisRound,
      committed: characterTurns.length > 0,
      hg_session_id: hgSessionId,
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      continuity_version: Number(finalSceneState.continuity_version ?? continuityVersion),
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
      inference_outcome: lastTurn?.inference_outcome ?? null,
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
        librarian: roleTimings.librarian_ms,
        plot_cognition: roleTimings.plot_cognition_ms,
      },
      plot_cognition_resume: plotCognitionResumeSummary,
      storyteller: storytellerRoundSummary,
    };
  }
}
