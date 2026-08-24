/**
 * Participation-direct deterministic decision evidence (#28).
 */

export function buildParticipationEligibilityBlock(eligibilitySnapshot) {
  return {
    eligibility_snapshot_id: eligibilitySnapshot?.eligibility_snapshot_id ?? null,
    eligible_actors: [...(eligibilitySnapshot?.eligible_actors ?? [])],
    present_characters: [...(eligibilitySnapshot?.present_characters ?? [])],
    offstage_characters: [...(eligibilitySnapshot?.offstage_characters ?? [])],
    absent_but_relevant: [...(eligibilitySnapshot?.absent_but_relevant ?? [])],
    actors_used_this_round: [...(eligibilitySnapshot?.actors_used_this_round ?? [])],
  };
}

export function participationDecisionPatch({
  participation,
  eligibilitySnapshot,
  outcome = 'selected',
}) {
  return {
    decision: {
      role: 'participation',
      outcome,
      participation: {
        selection_mode: participation?.selection_mode ?? null,
        selected_actor: participation?.selected_actor ?? null,
        participation_sources: [...(participation?.participation_sources ?? [])],
        reason: participation?.reason ?? '',
        director_required: Boolean(participation?.director_required),
        director_constraint_actor: participation?.director_constraint_actor ?? null,
        continuation_c2_skip: Boolean(participation?.continuation_c2_skip),
        forced_designation_ignored: Boolean(participation?.forced_designation_ignored),
        forced_designation_ignore_reason:
          participation?.forced_designation_ignore_reason ?? null,
        eligibility: buildParticipationEligibilityBlock(eligibilitySnapshot),
      },
    },
  };
}
