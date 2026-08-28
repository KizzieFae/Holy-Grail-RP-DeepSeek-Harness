import { buildSemanticQaDecisionFields } from './semantic-qa-patch.mjs';

/**
 * Map phase validation outcomes into durable decision evidence.
 */

export function buildDirectorEligibilityBlock(
  eligibilitySnapshot,
  participationContext,
  actorsUsedThisRound,
) {
  return {
    eligibility_snapshot_id:
      participationContext?.eligibilitySnapshotId
      ?? eligibilitySnapshot?.eligibility_snapshot_id
      ?? null,
    eligible_actors: [...(eligibilitySnapshot?.eligible_actors ?? [])],
    present_characters: [...(eligibilitySnapshot?.present_characters ?? [])],
    offstage_characters: [...(eligibilitySnapshot?.offstage_characters ?? [])],
    absent_but_relevant: [...(eligibilitySnapshot?.absent_but_relevant ?? [])],
    director_constraint_actor: participationContext?.directorConstraintActor ?? null,
    continuation_c2_skip: Boolean(participationContext?.continuationC2Skip),
    actors_used_this_round: [...(actorsUsedThisRound ?? [])],
  };
}

function applyDirectorDecisionBlocks(
  patch,
  {
    outcome,
    validation,
    proposed,
    eligibilitySnapshot,
    participationContext,
    actorsUsedThisRound,
    semanticQa,
    residualSoftConcerns,
    terminalDisposition,
    retention,
  },
) {
  const director = {
    eligibility: buildDirectorEligibilityBlock(
      eligibilitySnapshot,
      participationContext,
      actorsUsedThisRound,
    ),
  };

  if (validation?.accepted) {
    const normalized = validation.normalized_decision ?? proposed;
    director.normalized_decision = normalized;
    director.selected_character_id =
      validation.selected_character_id ?? normalized?.next_actor ?? null;
    director.end_round = Boolean(normalized?.end_round);
    director.constraints = {
      eligibility_snapshot_id:
        participationContext?.eligibilitySnapshotId
        ?? eligibilitySnapshot?.eligibility_snapshot_id
        ?? null,
      director_constraint_actor: participationContext?.directorConstraintActor ?? null,
      continuation_c2_skip: Boolean(participationContext?.continuationC2Skip),
      actors_used_this_round: [...(actorsUsedThisRound ?? [])],
    };
  }

  patch.decision.director = director;

  if (semanticQa) {
    patch.decision.semantic_qa = buildSemanticQaDecisionFields(semanticQa);
  }
  if (residualSoftConcerns) {
    patch.decision.residual_soft_concerns = residualSoftConcerns;
  }
  if (terminalDisposition) {
    patch.decision.terminal_disposition = terminalDisposition;
  }
  if (retention) {
    patch.decision.retention = retention;
  }
}

export function directorDecisionPatch({
  proposed,
  parseError,
  validation,
  outcome,
  eligibilitySnapshot,
  participationContext,
  actorsUsedThisRound,
  semanticQa = null,
  residualSoftConcerns = null,
  terminalDisposition = null,
  retention = null,
}) {
  const patch = {
    decision: {
      role: 'director',
      outcome,
      parse: {
        proposed,
        parse_error: parseError ?? proposed?.parse_error ?? null,
      },
    },
  };

  if (validation) {
    patch.decision.validation = {
      accepted: Boolean(validation.accepted),
      validation_class: validation.validation_class ?? null,
      reason: validation.reason ?? '',
      retryable: Boolean(validation.retryable),
    };
  }

  applyDirectorDecisionBlocks(patch, {
    outcome,
    validation,
    proposed,
    eligibilitySnapshot,
    participationContext,
    actorsUsedThisRound,
    semanticQa,
    residualSoftConcerns,
    terminalDisposition,
    retention,
  });

  return patch;
}

export function characterDecisionPatch({
  proposed,
  parseError,
  validation,
  outcome,
  commit,
  semanticEvaluation = null,
  residualSoftConcerns = null,
  terminalDisposition = null,
}) {
  const patch = {
    decision: {
      role: 'character',
      outcome,
      parse: {
        proposed_move: proposed,
        parse_error: parseError ?? proposed?.parse_error ?? null,
      },
    },
  };

  if (validation) {
    patch.decision.validation = {
      accepted: Boolean(validation.accepted),
      validation_class: validation.validation_class ?? null,
      reason: validation.reason ?? '',
      retryable: Boolean(validation.retryable),
      normalized_move: validation.normalized_move ?? null,
    };
  }

  if (commit?.committed) {
    patch.associations = {
      domain_commit_id: commit.domain_commit_id ?? null,
      continuity_turn_index: commit.continuity_turn_index ?? null,
    };
    patch.decision.commit = {
      committed: true,
      domain_commit_id: commit.domain_commit_id ?? null,
      continuity_turn_index: commit.continuity_turn_index ?? null,
    };
  } else if (commit) {
    patch.decision.commit = {
      committed: false,
      reason: commit.reason ?? '',
    };
  }

  if (semanticEvaluation) {
    patch.decision.semantic_evaluation = semanticEvaluation;
  }
  if (residualSoftConcerns) {
    patch.decision.residual_soft_concerns = residualSoftConcerns;
  }
  if (terminalDisposition) {
    patch.decision.terminal_disposition = terminalDisposition;
  }

  return patch;
}

export function narratorDecisionPatch({
  inferenceOutcome,
  presentationText,
  presentationFailed,
  failureReason,
  domainCommitId,
  continuityTurnIndex,
  attemptIndex = null,
  finishKindRaw = null,
  finishKindNormalized = null,
  validationAccepted = null,
  validationClass = null,
  validationReason = null,
  retryable = null,
  retryDecision = null,
  rejectedPresentationText = null,
  terminalDisposition = null,
  semanticQa = null,
  residualSoftConcerns = null,
  environmentCognition = null,
}) {
  const patch = {
    decision: {
      role: 'narrator',
      outcome: presentationFailed ? 'presentation_failed' : 'succeeded',
      inference_outcome: inferenceOutcome ?? null,
      presentation_text: presentationText ?? null,
      failure_reason: failureReason ?? null,
      attempt_index: attemptIndex,
      finish_kind_raw: finishKindRaw,
      finish_kind_normalized: finishKindNormalized,
      validation_accepted: validationAccepted,
      validation_class: validationClass,
      validation_reason: validationReason,
      retryable,
      retry_decision: retryDecision,
      rejected_presentation_text: rejectedPresentationText,
      terminal_disposition: terminalDisposition,
    },
    associations: {
      domain_commit_id: domainCommitId ?? null,
      continuity_turn_index: continuityTurnIndex ?? null,
    },
  };
  if (semanticQa) {
    patch.decision.semantic_qa = buildSemanticQaDecisionFields(semanticQa);
  }
  if (residualSoftConcerns) {
    patch.decision.residual_soft_concerns = residualSoftConcerns;
  }
  if (environmentCognition) {
    patch.decision.environment_cognition = environmentCognition;
  }
  return patch;
}

export function openingDecisionPatch({
  inferenceOutcome,
  presentationText,
  presentationFailed,
  failureReason,
  attemptIndex,
}) {
  return {
    decision: {
      role: 'opening',
      outcome: presentationFailed ? 'presentation_failed' : 'succeeded',
      inference_outcome: inferenceOutcome ?? null,
      presentation_text: presentationText ?? null,
      failure_reason: failureReason ?? null,
      attempt_index: attemptIndex ?? null,
    },
  };
}
