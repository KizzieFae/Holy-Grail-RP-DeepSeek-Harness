export function classifyRoundCompletion(completionReason) {
  if (completionReason === 'director_end_round' || completionReason === 'no_eligible_actors') {
    return { completion_status: 'completed', completion_class: 'semantic' };
  }
  if (completionReason === 'defensive_turn_ceiling') {
    return { completion_status: 'completed', completion_class: 'defensive' };
  }
  return { completion_status: 'aborted', completion_class: 'failure' };
}

export function eligibilityTrace(eligibility) {
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

export function participationTrace(participation) {
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

/**
 * Normalize direct participation selection into the director-decision shape
 * required by commit APIs. Not a Director inference result — tagged via source.
 */
export function participationDirectorDecision(characterId, reason) {
  return {
    next_actor: characterId,
    end_round: false,
    reason: reason ?? `Participation policy selected ${characterId}.`,
    environment_event: '',
    tension_shift: '',
    source: 'participation_policy',
  };
}
