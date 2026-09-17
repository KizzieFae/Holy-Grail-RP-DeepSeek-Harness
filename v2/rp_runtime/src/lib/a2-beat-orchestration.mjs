/**
 * Issue #201 G3-A — experimental A2 beat orchestrator (harness-only).
 *
 * NOT imported by production bootstrap. Implements minimal simple/complex paths
 * with Character → commit → Narrator separation.
 */
import crypto from 'node:crypto';

import { SessionId } from '@deepseek-ai/dsh-session';

import {
  LIVE_CHARACTER_PROMPT,
  LIVE_NARRATOR_PROMPT,
  LIVE_A2_F2_NARRATOR_SPATIAL_PROMPT,
} from './live-inference-prompts.mjs';
import { createDecisionValueLogger } from './a2-decision-value-logger.mjs';
import { deriveObligationSignals } from './a2-obligation-dispatch.mjs';
import {
  participationDirectorDecision,
  participationTrace,
  eligibilityTrace,
} from '../plugins/hg-round-orchestrator/round-helpers.mjs';
import { roleForCharacter } from '../plugins/hg-phase-executors/role-utils.mjs';
import {
  captureActorContextPackages,
  auditPrivateKnowledgeIsolation,
} from './a2-actor-isolation-audit.mjs';
import { runPostCommitPlotCognitionLifecycle } from './plot-cognition-orchestration.mjs';
import { runA2IndexedRetrievalStep } from './a2-indexed-retrieval.mjs';
import { runLh0PostCommitAdapter } from '../../scripts/lib/issue201-lh0-post-commit-adapters.mjs';
import { LH0_ARMS } from '../../scripts/lib/issue201-lh0-arms.mjs';
import {
  prepareLh0RoundTransport,
  recordLh0TransportAuditStep,
  buildLh0ConsequenceMarker,
} from '../../scripts/lib/issue201-lh0-transport.mjs';
import {
  buildCharacterConsumerEvidence,
  extractLh0ObligationIdsFromManifest,
} from '../../scripts/lib/issue201-lh0-consumer-evidence.mjs';

export const A2_TOPOLOGY_ABSENT = [
  'storyteller_preamble',
  'director_semantic_qa',
  'narrator_semantic_qa',
  'narrator_environment_cognition',
  'character_orientation_llm',
  'default_librarian_mediation',
  'synchronous_plot',
  'character_semantic_evaluation_f1',
  'plot_epistemic_eval',
];

function createAuditStep(name, detail = {}) {
  return { step: name, at_ms: Date.now(), ...detail };
}

function extractSpatialClaimsFromNarratorRaw(raw, explicitClaims) {
  if (explicitClaims) return explicitClaims;
  if (!raw) return null;
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
    if (parsed?.spatial_claims) return parsed.spatial_claims;
    if (parsed?.presentation?.spatial_claims) return parsed.presentation.spatial_claims;
  } catch {
    return null;
  }
  return null;
}

/**
 * Run one A2 experimental beat (single character turn in round).
 */
export async function runA2BeatRound({
  phaseExecutors,
  api,
  trace,
  sceneAgent,
  sceneSessionId,
  hgSessionId,
  hgSceneId,
  options = {},
}) {
  const auditSteps = [];
  const decisionValue = options.decisionValueLogger ?? createDecisionValueLogger();
  const roleProfiles = options.roleProfiles ?? {};
  const liveMaxAttempts = Number(options.liveMaxAttempts ?? 3);
  const scenarioKey = options.scenarioKey ?? 'ayame_controlled';
  const roleAssignments = options.roleAssignments ?? {};
  const uniformProjectionEligible = options.uniformProjectionEligible ?? true;
  const characterSemanticEvaluationEnabled = options.characterSemanticEvaluationEnabled === true;
  const skipPostCommitPlot = options.skipPostCommitPlot !== false;
  const presentationSpatialClaims = options.presentationSpatialClaims ?? null;
  const requireStructuredSpatialClaims = options.requireStructuredSpatialClaims === true;
  const resolveSpatialClaimsFromEvidence = options.resolveSpatialClaimsFromEvidence ?? null;
  const mockCharacterResponses = options.mockCharacterTurnResponses?.[0] ?? options.mockCharacterResponses ?? [];
  const mockNarratorResponses = options.mockNarratorTurnResponses?.[0] ?? options.mockNarratorResponses ?? [];
  const mockDirectorResponses = options.mockDirectorResponses ?? [];
  const criticalPathStartedAt = Date.now();

  auditSteps.push(createAuditStep('player_input_recorded', {
    hg_session_id: hgSessionId,
    skipped: 'ingress handled by harness before orchestrator',
  }));

  const round = await api.startRound({ hg_scene_id: hgSceneId });
  const hgRoundId = round.hg_round_id;
  auditSteps.push(createAuditStep('round_started', { hg_round_id: hgRoundId }));

  const eligibility = await api.getEligibleActors({
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
  });
  const eligibleActors = eligibility.eligible_actors ?? [];
  auditSteps.push(createAuditStep('actor_eligibility', {
    snapshot: eligibilityTrace(eligibility),
    eligible_count: eligibleActors.length,
  }));

  const enableIndexedRetrieval = options.enableIndexedRetrieval === true;
  const obligationDispatch = deriveObligationSignals({
    scenarioKey,
    eligibleActors,
    roleAssignments,
    uniformProjectionEligible,
    retrievalManifestGap: options.retrievalManifestGap === true || enableIndexedRetrieval,
  });
  auditSteps.push(createAuditStep('obligation_dispatch', obligationDispatch));

  let actorContextAudit = null;
  if (options.captureActorContextPackages === true) {
    const actorPackages = await captureActorContextPackages({
      api,
      hgSceneId,
      hgRoundId,
      turnIndex: round.turn_index,
      eligibleActors,
      characterRoles: eligibility.character_roles ?? roleAssignments,
    });
    actorContextAudit = {
      packages: actorPackages.map((p) => ({ character_id: p.character_id, summary: p.summary })),
      isolation: auditPrivateKnowledgeIsolation(actorPackages),
    };
    auditSteps.push(createAuditStep('actor_context_isolation', actorContextAudit.isolation));
  }

  const participation = await api.getParticipationDecision({
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    eligibility_snapshot_id: eligibility.eligibility_snapshot_id,
  });
  auditSteps.push(createAuditStep('participation_decision', {
    snapshot: participationTrace(participation),
  }));

  const cognitionTurnIndex = Number(round.turn_index ?? 0);
  let lh0PrecomputedProjection = options.lh0PrecomputedProjection ?? null;
  let lh0Transport = null;
  let lh0DirectorProjectionReceipt = null;
  let projectionLifecycleForCharacter = options.projectionLifecycleEnabled === true;
  const lhProvenanceAudit = options.lhProvenanceAudit === true;
  const transportCharacterId = (participation.selection_mode === 'direct' && participation.selected_actor)
    ? participation.selected_actor
    : (eligibleActors[0] ?? null);
  if (options.lh0Arm && options.lh0SessionsDir && transportCharacterId) {
    lh0Transport = prepareLh0RoundTransport({
      sessionsDir: options.lh0SessionsDir,
      hgSessionId,
      hgRoundId,
      fixtureTurnIndex: options.lh0FixtureTurnIndex ?? cognitionTurnIndex,
      bindingTurnIndex: cognitionTurnIndex,
      characterId: transportCharacterId,
      arm: options.lh0Arm,
      faultInjection: options.lh0FaultInjection ?? null,
    });
    lh0DirectorProjectionReceipt = lh0Transport.directorProjection;
    if (!lh0PrecomputedProjection) {
      if (options.lh0Arm === LH0_ARMS.LH_B) {
        lh0PrecomputedProjection = lh0Transport.characterPrecomputed;
        projectionLifecycleForCharacter = lh0Transport.usePlotProjectionLifecycle
          && !lh0PrecomputedProjection;
      } else {
        lh0PrecomputedProjection = lh0Transport.characterPrecomputed;
        projectionLifecycleForCharacter = false;
      }
    }
    const transportAudit = recordLh0TransportAuditStep(lh0Transport, {
      omitCharacterReceipt: options.lh0FaultInjection === 'omit_receipt',
    });
    auditSteps.push(createAuditStep('lh0_projection_transport', transportAudit));
  }

  let directorPhase;
  const forceDirectorInference = options.lh1bForceDirectorInference === true;
  const deterministicActor = forceDirectorInference
    ? null
    : ((participation.selection_mode === 'direct' && participation.selected_actor)
      ? participation.selected_actor
      : (eligibleActors.length === 1 ? eligibleActors[0] : null));
  if (deterministicActor) {
    directorPhase = {
      accepted: true,
      endRound: false,
      directorDecision: participationDirectorDecision(
        deterministicActor,
        participation.reason ?? 'single_eligible_actor',
      ),
      selectedCharacterId: deterministicActor,
      participationDirect: participation.selection_mode === 'direct',
      director_llm_invoked: false,
    };
    auditSteps.push(createAuditStep('director_deterministic_select', {
      selected_character_id: deterministicActor,
      source: participation.selection_mode === 'direct' ? 'participation_direct' : 'single_eligible_actor',
    }));
  } else {
    const directorInferenceId = `inf-a2-director-${crypto.randomUUID()}`;
    const directorStartedAt = Date.now();
    directorPhase = await phaseExecutors.runDirector({
      api,
      sceneAgent,
      sceneSessionId,
      hgSessionId,
      hgSceneId,
      hgRoundId,
      directorInferenceId,
      directorAttemptSeed: 0,
      mockDirectorResponses,
      mockDirectorSemanticQaResponses: [],
      directorResponseIndex: 0,
      actorsUsedThisRound: [],
      turnIndex: round.turn_index,
      eligibilitySnapshot: eligibilityTrace(eligibility),
      participationContext: {
        eligibilitySnapshotId: eligibility.eligibility_snapshot_id,
        directorConstraintActor: participation.director_constraint_actor ?? null,
        continuationC2Skip: participation.continuation_c2_skip,
      },
      modelProfile: roleProfiles.director,
      semanticEvaluatorProfile: roleProfiles.semantic_evaluator,
      liveMaxAttempts,
      directorSemanticQaEnabled: false,
      precomputedDirectorProjection: lh0DirectorProjectionReceipt,
      lh0ExpectedObligationIds: lh0Transport?.directorDue?.map((o) => o.obligation_id) ?? [],
      lhProvenanceAudit,
    });
    decisionValue.record({
      inference_kind: 'director_turn',
      experimental_identity: 'a2_director',
      consumer: 'turn_selection',
      decision_purpose: 'actor_selection',
      unique_information: 'selected_actor',
      downstream_decision: 'character_move_target',
      deterministic_alternative_existed: false,
      mandatory: obligationDispatch.beat_class === 'complex',
      obligation_trigger: 'actor_multiplicity_or_ambiguity',
      wall_ms: Date.now() - directorStartedAt,
    });
    directorPhase.director_llm_invoked = true;
    auditSteps.push(createAuditStep('director_cognition', {
      selected_character_id: directorPhase.selectedCharacterId ?? null,
      accepted: directorPhase.accepted === true,
    }));
  }

  if (!directorPhase.accepted || !directorPhase.selectedCharacterId) {
    return {
      schema: 'issue201_g3_a2_round_v1',
      architecture_arm: 'a2_prototype',
      committed: false,
      completion_reason: 'director_failure',
      audit_steps: auditSteps,
      obligation_dispatch: obligationDispatch,
      topology_absent: A2_TOPOLOGY_ABSENT,
      decision_value: decisionValue.toJSON(),
    };
  }

  const characterId = directorPhase.selectedCharacterId;
  let indexedRetrieval = null;
  if (enableIndexedRetrieval) {
    indexedRetrieval = runA2IndexedRetrievalStep({
      caseId: options.g3eCaseId ?? 'K1',
      viewerCharacterId: characterId,
    });
    auditSteps.push(createAuditStep('indexed_retrieval', {
      case_id: indexedRetrieval.case_id,
      ok: indexedRetrieval.ok === true,
      selection_path: indexedRetrieval.selection_path,
      ranked_count: (indexedRetrieval.ranked_ids ?? []).length,
      librarian_invocation_count: 0,
      hard_access_rejected: indexedRetrieval.hard_access_rejected,
    }));
  }
  if (lh0Transport && transportCharacterId !== characterId) {
    lh0Transport = prepareLh0RoundTransport({
      sessionsDir: options.lh0SessionsDir,
      hgSessionId,
      hgRoundId,
      fixtureTurnIndex: options.lh0FixtureTurnIndex ?? cognitionTurnIndex,
      bindingTurnIndex: cognitionTurnIndex,
      characterId,
      arm: options.lh0Arm,
      faultInjection: options.lh0FaultInjection ?? null,
    });
    lh0DirectorProjectionReceipt = lh0Transport.directorProjection;
    if (!options.lh0PrecomputedProjection) {
      lh0PrecomputedProjection = lh0Transport.characterPrecomputed;
    }
  }

  const characterInferenceId = `inf-a2-character-${crypto.randomUUID()}`;
  const characterStartedAt = Date.now();
  const characterTurn = await phaseExecutors.runCharacter({
    api,
    sceneAgent,
    sceneSessionId,
    hgSessionId,
    hgSceneId,
    hgRoundId,
    characterId,
    directorDecision: directorPhase.directorDecision,
    characterInferenceId,
    mockResponses: mockCharacterResponses,
    mockSemanticEvaluatorResponses: [],
    characterTurnIndex: 0,
    characterRole: roleForCharacter(characterId, eligibility.character_roles ?? {}),
    modelProfile: roleProfiles.character,
    semanticEvaluatorProfile: roleProfiles.semantic_evaluator,
    liveMaxAttempts,
    prompt: options.livePrompts?.character ?? LIVE_CHARACTER_PROMPT,
    skipCharacterKnowledgeCognition: options.skipCharacterKnowledgeCognition !== false,
    semanticEvaluationEnabled: characterSemanticEvaluationEnabled,
    projectionLifecycleEnabled: projectionLifecycleForCharacter,
    precomputedFinalizedProjection: lh0PrecomputedProjection,
    lh0ExpectedObligationIds: lh0Transport?.characterDue?.map((o) => o.obligation_id) ?? [],
    lh0FixtureTurnIndex: options.lh0FixtureTurnIndex ?? null,
    lh0FixtureManifest: options.lh0FixtureManifest ?? null,
    lhProvenanceAudit,
  });
  if (lh0Transport && directorPhase.lh0DirectorConsumerEvidence) {
    const dirEvidence = directorPhase.lh0DirectorConsumerEvidence;
    const transportAudit = auditSteps.find((s) => s.step === 'lh0_projection_transport');
    if (transportAudit) {
      transportAudit.director_consumer_receipt = dirEvidence.consumer_received;
      transportAudit.director_received_obligation_ids = dirEvidence.received_obligation_ids;
    }
    auditSteps.push(createAuditStep('lh0_director_consumer_receipt', dirEvidence));
  }
  if (lh0Transport && characterTurn.consumerManifest) {
    const charEvidence = buildCharacterConsumerEvidence({
      manifest: characterTurn.consumerManifest,
      finalizedProjection: lh0PrecomputedProjection,
      projectionSupplied: Boolean(lh0PrecomputedProjection),
      obligationIdsExpected: lh0Transport.characterDue.map((o) => o.obligation_id),
    });
    const transportAudit = auditSteps.find((s) => s.step === 'lh0_projection_transport');
    if (transportAudit) {
      transportAudit.character_consumer_receipt = charEvidence.consumer_received;
      transportAudit.received_obligation_ids = charEvidence.received_obligation_ids;
    }
    auditSteps.push(createAuditStep('lh0_character_consumer_receipt', charEvidence));
  }
  decisionValue.record({
    inference_kind: 'character_move',
    experimental_identity: 'a2_character_move',
    consumer: 'continuity_commit',
    decision_purpose: 'proposed_move',
    unique_information: 'structured_character_move',
    downstream_decision: 'authoritative_commit',
    deterministic_alternative_existed: false,
    mandatory: true,
    obligation_trigger: 'core_a2_endpoint',
    wall_ms: Date.now() - characterStartedAt,
  });
  auditSteps.push(createAuditStep('character_cognition', {
    character_id: characterId,
    committed: characterTurn.committed === true,
    semantic_evaluation_enabled: characterSemanticEvaluationEnabled,
    orientation_skipped: options.skipCharacterKnowledgeCognition !== false,
    projection_lifecycle_skipped: options.projectionLifecycleEnabled !== true,
    lh0_consumption_enforcer: options.lh0ConsumptionEnforcer === true,
    lh0_arm: options.lh0Arm ?? null,
  }));

  if (!characterTurn.committed) {
    return {
      schema: 'issue201_g3_a2_round_v1',
      architecture_arm: 'a2_prototype',
      committed: false,
      completion_reason: 'character_failure',
      character_turn: characterTurn,
      audit_steps: auditSteps,
      obligation_dispatch: obligationDispatch,
      topology_absent: A2_TOPOLOGY_ABSENT,
      decision_value: decisionValue.toJSON(),
    };
  }

  auditSteps.push(createAuditStep('authoritative_commit', {
    domain_commit_id: characterTurn.domainCommitId,
    continuity_turn_index: characterTurn.continuityTurnIndex,
  }));

  const narratorInferenceId = `inf-a2-narrator-${crypto.randomUUID()}`;
  const narratorStartedAt = Date.now();
  const narratorResult = await phaseExecutors.runNarrator({
    api,
    sceneAgent,
    sceneSessionId,
    hgSessionId,
    hgSceneId,
    hgRoundId,
    characterId,
    domainCommitId: characterTurn.domainCommitId,
    continuityTurnIndex: characterTurn.continuityTurnIndex,
    narratorInferenceId,
    mockNarratorResponses,
    mockNarratorSemanticQaResponses: [],
    characterTurnIndex: 0,
    modelProfile: roleProfiles.narrator,
    semanticEvaluatorProfile: roleProfiles.semantic_evaluator,
    narratorSemanticQaEnabled: false,
    skipNarratorEnvironmentCognition: true,
    prompt: options.livePrompts?.narrator
      ?? (requireStructuredSpatialClaims ? LIVE_A2_F2_NARRATOR_SPATIAL_PROMPT : LIVE_NARRATOR_PROMPT),
  });
  decisionValue.record({
    inference_kind: 'narrator_presentation',
    experimental_identity: 'a2_narrator_presentation',
    consumer: 'player_visible_presentation',
    decision_purpose: 'render_committed_event',
    unique_information: 'presentation_text',
    downstream_decision: 'player_visible_output',
    deterministic_alternative_existed: false,
    mandatory: true,
    obligation_trigger: 'core_a2_endpoint',
    wall_ms: Date.now() - narratorStartedAt,
  });
  auditSteps.push(createAuditStep('narrator_cognition', {
    presentation_rendered: narratorResult.presentation_rendered === true,
    env_cognition_skipped: true,
    semantic_qa_skipped: true,
  }));

  const presentationText = narratorResult.presentation_text ?? '';
  const narratorValidation = await api.validateNarratorPresentation({
    hg_scene_id: hgSceneId,
    domain_commit_id: characterTurn.domainCommitId,
    presentation_text: presentationText,
  });
  auditSteps.push(createAuditStep('presentation_validation', {
    accepted: narratorValidation.accepted === true,
    validation_class: narratorValidation.validation_class ?? null,
  }));

  let spatialClaims = extractSpatialClaimsFromNarratorRaw(
    narratorResult.narrator_raw_output ?? null,
    presentationSpatialClaims,
  );
  if (!spatialClaims && resolveSpatialClaimsFromEvidence) {
    spatialClaims = await resolveSpatialClaimsFromEvidence({
      hgSessionId,
      hgRoundId,
      narratorResult,
    });
  }
  let spatialValidation = null;
  if (spatialClaims) {
    spatialValidation = await api.validatePresentationSpatialClaims({
      hg_scene_id: hgSceneId,
      spatial_claims: spatialClaims,
    });
    auditSteps.push(createAuditStep('spatial_claims_validation', spatialValidation));
  } else if (requireStructuredSpatialClaims) {
    auditSteps.push(createAuditStep('spatial_claims_validation', {
      skipped: false,
      reason: 'required_structured_spatial_claims_missing',
      accepted: false,
    }));
    spatialValidation = {
      accepted: false,
      validation_class: 'missing_surface',
      reason: 'required_structured_spatial_claims_missing',
    };
  } else {
    auditSteps.push(createAuditStep('spatial_claims_validation', {
      skipped: true,
      reason: 'no_structured_spatial_claims_surface',
    }));
  }

  const criticalPathWallMs = Date.now() - criticalPathStartedAt;
  auditSteps.push(createAuditStep('player_visible_presentation', {
    presentation_length: presentationText.length,
    critical_path_wall_ms: criticalPathWallMs,
  }));

  let plotPostCommit = { skipped: true, reason: 'g3a_default_off' };
  let plotPostCommitWallMs = 0;
  let lh0PostCommit = null;
  if (options.lh0Arm && options.lh0SessionsDir) {
    const lh0Started = Date.now();
    lh0PostCommit = await runLh0PostCommitAdapter({
      arm: options.lh0Arm,
      domainApi: api,
      trace,
      sceneAgent,
      scope: { hgSessionId, hgSceneId, hgRoundId, sceneSessionId },
      hgSceneId,
      hgRoundId,
      hgSessionId,
      domainCommitId: characterTurn.domainCommitId,
      turnIndex: options.lh0FixtureTurnIndex ?? cognitionTurnIndex,
      fixtureTurnIndex: options.lh0FixtureTurnIndex ?? cognitionTurnIndex,
      runtimeTurnIndex: cognitionTurnIndex,
      presentationText,
      sessionsDir: options.lh0SessionsDir,
      runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
      modelProfile: roleProfiles.storyteller ?? roleProfiles.director,
      evidenceContextBase: { hgSessionId, hgSceneId, hgRoundId, sceneSessionId },
      fixtureManifest: options.lh0FixtureManifest ?? null,
    });
    lh0PostCommit.wall_ms = Date.now() - lh0Started;
    auditSteps.push(createAuditStep('lh0_post_commit', lh0PostCommit));
  } else if (!skipPostCommitPlot && options.runPostCommitPlot === true) {
    const plotStartedAt = Date.now();
    plotPostCommit = await runPostCommitPlotCognitionLifecycle({
      domainApi: api,
      trace,
      sceneAgent,
      scope: {
        hgSessionId,
        hgSceneId,
        hgRoundId,
        domainCommitId: characterTurn.domainCommitId,
      },
      hgSceneId,
      inferenceId: `inf-plot-a2-${crypto.randomUUID()}`,
      runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
      modelProfile: roleProfiles.storyteller ?? roleProfiles.director,
      evidenceContextBase: {
        hgSessionId,
        hgSceneId,
        hgRoundId,
        domainCommitId: characterTurn.domainCommitId,
      },
    });
    plotPostCommitWallMs = Date.now() - plotStartedAt;
    plotPostCommit.wall_ms = plotPostCommitWallMs;
    plotPostCommit.outside_critical_path = true;
    auditSteps.push(createAuditStep('plot_post_commit', plotPostCommit));
  } else {
    auditSteps.push(createAuditStep('plot_post_commit', plotPostCommit));
  }

  const presentSequence = enableIndexedRetrieval
    ? [
      'indexed_retrieval',
      'character_move',
      'deterministic_move_validation',
      'authoritative_commit',
      'narrator_presentation',
      'deterministic_presentation_validation',
    ]
    : [
      'character_move',
      'deterministic_move_validation',
      'authoritative_commit',
      'narrator_presentation',
      'deterministic_presentation_validation',
    ];
  const topologyProof = {
    absent: A2_TOPOLOGY_ABSENT,
    present_sequence: presentSequence,
    director_llm_invoked: directorPhase.director_llm_invoked === true,
    character_semantic_evaluation_enabled: characterSemanticEvaluationEnabled,
    two_call_contract: true,
  };

  if (options.lh0ConsumptionEnforcer === true) {
    const projectionEnabled = options.projectionLifecycleEnabled === true;
    const knowledgeCognitionEnabled = options.skipCharacterKnowledgeCognition === false;
    const enforcerPass = projectionEnabled && knowledgeCognitionEnabled;
    auditSteps.push(createAuditStep('lh0_consumption_lifecycle_enforcer', {
      pass: enforcerPass,
      projection_lifecycle_enabled: projectionEnabled,
      character_knowledge_cognition_enabled: knowledgeCognitionEnabled,
      fail_closed: !enforcerPass,
      g3d_class_gap_prevented: enforcerPass,
    }));
  }

  const blockingSpatial = (spatialValidation && spatialValidation.accepted === false)
    || (requireStructuredSpatialClaims && !spatialClaims);
  const committed = characterTurn.committed === true
    && narratorResult.presentation_rendered === true
    && narratorValidation.accepted === true
    && !blockingSpatial;

  return {
    schema: 'issue201_g3_a2_round_v1',
    architecture_arm: 'a2_prototype',
    committed,
    completion_reason: committed ? 'a2_beat_complete' : 'presentation_or_spatial_validation_failed',
    hg_round_id: hgRoundId,
    domain_commit_id: characterTurn.domainCommitId,
    selected_character_id: characterId,
    presentation_text: presentationText,
    character_turn: characterTurn,
    narrator_result: narratorResult,
    narrator_validation: narratorValidation,
    spatial_validation: spatialValidation,
    spatial_claims: spatialClaims ?? null,
    structured_spatial_surface_present: Boolean(spatialClaims),
    actor_context_audit: actorContextAudit,
    obligation_dispatch: obligationDispatch,
    indexed_retrieval: indexedRetrieval,
    topology_proof: topologyProof,
    audit_steps: auditSteps,
    decision_value: decisionValue.toJSON(),
    plot_post_commit: plotPostCommit,
    lh0_post_commit: lh0PostCommit,
    lh0_transport: lh0Transport ? {
      director: {
        receipt_applicable: lh0Transport.director_receipt_applicable,
        deterministic_fixture: lh0Transport.director_deterministic_fixture,
        projected_obligation_ids: lh0Transport.directorDue.map((o) => o.obligation_id),
        consumer_receipt: false,
      },
      character: characterTurn.lh0ConsumerEvidence ?? null,
      projected_finalized: lh0Transport.projected_finalized,
      candidate_only: lh0Transport.candidate_only,
      fault_injection: lh0Transport.fault_injection,
    } : null,
    lh0_consequences: (() => {
      if (!lh0Transport || !characterTurn.committed) return null;
      const influenced = characterTurn.lh0ConsumerEvidence?.decision_influenced_obligation_ids ?? [];
      if (!influenced.length) return null;
      return buildLh0ConsequenceMarker(influenced, {
        turnIndex: options.lh0FixtureTurnIndex ?? cognitionTurnIndex,
        hgRoundId,
      });
    })(),
    lh0_director_projection_receipt: lh0DirectorProjectionReceipt,
    efficiency: {
      critical_path_wall_ms: criticalPathWallMs,
      plot_post_commit_wall_ms: plotPostCommitWallMs,
      llm_call_count: decisionValue.records.length,
    },
  };
}

/**
 * Harness helper: create isolated scene session for A2 runs.
 */
export async function createA2SceneAgent(ctx, baseUrl) {
  const sceneSessionId = SessionId(`hg-a2-${crypto.randomUUID()}`);
  const sceneAgent = ctx.agentLoop.create(sceneSessionId, { kind: 'mock' });
  return { sceneSessionId, sceneAgent };
}
