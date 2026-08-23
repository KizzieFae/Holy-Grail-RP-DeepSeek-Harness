/**
 * Map phase validation outcomes into durable decision evidence.
 */

export function directorDecisionPatch({
  proposed,
  parseError,
  validation,
  outcome,
  eligibilitySnapshot,
  participationContext,
  actorsUsedThisRound,
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

  if (outcome === 'accepted' && validation) {
    const normalized = validation.normalized_decision ?? proposed;
    patch.decision.director = {
      normalized_decision: normalized,
      selected_character_id: validation.selected_character_id ?? normalized?.next_actor ?? null,
      end_round: Boolean(normalized?.end_round),
      constraints: {
        eligibility_snapshot_id:
          participationContext?.eligibilitySnapshotId
          ?? eligibilitySnapshot?.eligibility_snapshot_id
          ?? null,
        director_constraint_actor: participationContext?.directorConstraintActor ?? null,
        continuation_c2_skip: Boolean(participationContext?.continuationC2Skip),
        actors_used_this_round: [...(actorsUsedThisRound ?? [])],
      },
    };
  }

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
}) {
  return {
    decision: {
      role: 'narrator',
      outcome: presentationFailed ? 'presentation_failed' : 'succeeded',
      inference_outcome: inferenceOutcome ?? null,
      presentation_text: presentationText ?? null,
      failure_reason: failureReason ?? null,
    },
    associations: {
      domain_commit_id: domainCommitId ?? null,
      continuity_turn_index: continuityTurnIndex ?? null,
    },
  };
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
