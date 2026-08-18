"""Authoritative participation policy for the V2 domain kernel."""

from __future__ import annotations

from typing import Any

from .contract import EligibleActorsResponse, ParticipationDecision
from .fixture_store import RoundFixture, SceneFixture

_CONTINUATION_SUPERSEDING_TAGS = frozenset(
    {
        "agreement",
        "arrival",
        "commitment",
        "exit",
        "refusal",
        "access_denied",
        "access_granted",
        "revelation",
    }
)


def _structured_move_from_turn(record: Any) -> dict[str, Any]:
    move = dict(record.committed_move)
    return {
        "speaker": record.character_id,
        "action": _beat_text(move, "action"),
        "dialogue": _beat_text(move, "dialogue"),
        "motivation": dict(move.get("motivation") or {}),
    }


def _beat_text(move: dict[str, Any], beat_type: str) -> str:
    for beat in move.get("beats") or []:
        if isinstance(beat, dict) and beat.get("type") == beat_type:
            return str(beat.get(beat_type, "") or "")
    return ""


def resolve_continuation_actor(
    *,
    fixture: SceneFixture,
    rnd: RoundFixture,
    eligible_present: list[str],
    actors_used_this_round: list[str],
    offstage_characters: list[str],
) -> str | None:
    if not rnd.character_turns:
        return None

    last_move = _structured_move_from_turn(rnd.character_turns[-1])
    actor = str(last_move.get("speaker", "") or "").strip()
    if not actor or actor not in eligible_present:
        return None
    if actors_used_this_round.count(actor) != 1:
        return None

    if rnd.spotlight_history and str(rnd.spotlight_history[-1] or "") != actor:
        return None

    motivation = last_move.get("motivation", {})
    if not isinstance(motivation, dict):
        return None
    if not any(str(motivation.get(field, "") or "").strip() for field in ("goal", "tactic")):
        return None

    mgr = fixture.manager
    turn_metadata: dict[str, Any] = {}
    if mgr is not None:
        turn_index = int(getattr(mgr, "turn_counter", 0) or 0)
        metadata_by_index = getattr(mgr, "turn_metadata_by_index", {})
        if isinstance(metadata_by_index, dict):
            candidate_metadata = metadata_by_index.get(turn_index, {})
            if isinstance(candidate_metadata, dict):
                turn_metadata = candidate_metadata

    tags = {
        str(item) for item in turn_metadata.get("tags", []) if str(item or "").strip()
    }
    if tags.intersection(_CONTINUATION_SUPERSEDING_TAGS):
        return None

    off = {str(x).strip() for x in offstage_characters if str(x or "").strip()}
    unheard_other = [
        participant
        for participant in eligible_present
        if str(participant or "").strip()
        and str(participant).strip() not in off
        and str(participant).strip() != actor
        and actors_used_this_round.count(str(participant).strip()) == 0
    ]
    if unheard_other:
        return None

    return actor


def _continuation_c2_skip(rnd: RoundFixture, continuation_actor: str) -> bool:
    if not rnd.spotlight_history:
        return False
    last_spot = str(rnd.spotlight_history[-1] or "").strip()
    return bool(last_spot and last_spot == continuation_actor)


def evaluate_participation_policy(
    *,
    fixture: SceneFixture,
    rnd: RoundFixture,
    eligibility: EligibleActorsResponse,
    eligibility_snapshot_id: str,
    forced_designation: str | None,
) -> ParticipationDecision:
    if eligibility.eligibility_snapshot_id != eligibility_snapshot_id:
        raise ValueError(
            "eligibility snapshot mismatch: "
            f"expected {eligibility.eligibility_snapshot_id}, got {eligibility_snapshot_id}"
        )

    eligible = list(eligibility.eligible_actors)
    base = {
        "hg_scene_id": eligibility.hg_scene_id,
        "hg_round_id": eligibility.hg_round_id,
        "eligibility_snapshot_id": eligibility.eligibility_snapshot_id,
    }

    forced = str(forced_designation or "").strip()
    if forced:
        if forced in eligible:
            return ParticipationDecision(
                **base,
                selection_mode="direct",
                selected_actor=forced,
                director_required=False,
                director_constraint_actor=None,
                participation_sources=("forced_designation",),
                reason=f"Forced designation selects eligible actor {forced}.",
                forced_designation_ignored=False,
                forced_designation_ignore_reason=None,
                continuation_c2_skip=False,
            )
        ignore_reason = _ineligibility_reason(fixture, rnd, forced, eligibility)
        return ParticipationDecision(
            **base,
            selection_mode="director",
            selected_actor=None,
            director_required=True,
            director_constraint_actor=None,
            participation_sources=(),
            reason=(
                f"Forced designation of {forced} ignored"
                + (f" ({ignore_reason})" if ignore_reason else "")
                + "; Director selection required."
            ),
            forced_designation_ignored=True,
            forced_designation_ignore_reason=ignore_reason,
            continuation_c2_skip=False,
        )

    present_labels = list(eligibility.present_characters or fixture.cast)
    eligible_present = [
        entry.character_id
        for entry in eligibility.actors
        if entry.presence_status == "present"
    ]
    if not eligible_present:
        eligible_present = [
            name for name in present_labels if name in fixture.cast
        ]

    continuation_actor = resolve_continuation_actor(
        fixture=fixture,
        rnd=rnd,
        eligible_present=eligible_present,
        actors_used_this_round=list(rnd.actors_used_this_round),
        offstage_characters=list(eligibility.offstage_characters),
    )

    if continuation_actor and continuation_actor in eligible:
        if _continuation_c2_skip(rnd, continuation_actor):
            return ParticipationDecision(
                **base,
                selection_mode="director",
                selected_actor=None,
                director_required=True,
                director_constraint_actor=None,
                participation_sources=("continuation_preference",),
                reason=(
                    f"Continuation preference for {continuation_actor} "
                    "deferred to Director (C2 spotlight skip)."
                ),
                forced_designation_ignored=False,
                forced_designation_ignore_reason=None,
                continuation_c2_skip=True,
            )
        return ParticipationDecision(
            **base,
            selection_mode="direct",
            selected_actor=continuation_actor,
            director_required=False,
            director_constraint_actor=None,
            participation_sources=("continuation_preference",),
            reason=f"Continuation preference selects eligible actor {continuation_actor}.",
            forced_designation_ignored=False,
            forced_designation_ignore_reason=None,
            continuation_c2_skip=False,
        )

    if continuation_actor and continuation_actor not in eligible:
        return ParticipationDecision(
            **base,
            selection_mode="director",
            selected_actor=None,
            director_required=True,
            director_constraint_actor=None,
            participation_sources=(),
            reason=(
                f"Continuation preference for ineligible actor {continuation_actor} "
                "not applied; Director selection required."
            ),
            forced_designation_ignored=False,
            forced_designation_ignore_reason=None,
            continuation_c2_skip=False,
        )

    return ParticipationDecision(
        **base,
        selection_mode="director",
        selected_actor=None,
        director_required=True,
        director_constraint_actor=None,
        participation_sources=(),
        reason="No participation policy override; Director selection required.",
        forced_designation_ignored=False,
        forced_designation_ignore_reason=None,
        continuation_c2_skip=False,
    )


def _ineligibility_reason(
    fixture: SceneFixture,
    rnd: RoundFixture,
    character_id: str,
    eligibility: EligibleActorsResponse,
) -> str | None:
    for entry in eligibility.actors:
        if entry.character_id == character_id:
            return entry.exclusion_reason
    if character_id not in fixture.cast:
        return "not_in_cast"
    if character_id in rnd.actors_used_this_round:
        return "already_used_this_round"
    return "not_eligible"
