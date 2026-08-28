"""Build bounded occurrence evidence at PublicEvent promotion (Issue #51)."""

from __future__ import annotations

from typing import Any

from character_move_adapters import (
    is_canonical_v2_move,
    legacy_flat_action_text,
    legacy_flat_dialogue_text,
    root_or_flat_dialogue_text,
)
from perception_audibility_constants import (
    AUDIBILITY_DIRECTED,
    AUDIBILITY_PRIVATE,
    AUDIBILITY_PUBLIC,
)
from perception_audibility_normalize import _clean_audience, normalize_move_audibility

from continuity_state_occurrence_evidence import (
    MAX_CONTRIBUTION_CONTENT,
    MAX_CONTRIBUTIONS,
    MAX_FACT_REFS,
    MAX_SCOPED_EVIDENCE,
    MAX_TRIGGER_EXCERPT,
    OccurrenceContribution,
    OccurrenceEvidence,
    ScopedEvidence,
    StructuredFactRef,
    TriggeringUser,
    _bound_text,
)


def _move_action_text(move: dict[str, Any]) -> str:
    if is_canonical_v2_move(move):
        return legacy_flat_action_text(move)
    return str(move.get("action", "") or "").strip()


def _move_dialogue_text(move: dict[str, Any]) -> str:
    if is_canonical_v2_move(move):
        return legacy_flat_dialogue_text(move)
    return str(move.get("dialogue", "") or "").strip()


def _character_contributions(
    *,
    acting_character: str,
    move: dict[str, Any],
    present_characters: list[str],
) -> tuple[list[OccurrenceContribution], list[ScopedEvidence]]:
    contributions: list[OccurrenceContribution] = []
    scoped: list[ScopedEvidence] = []
    action_text = _move_action_text(move)
    if action_text:
        contributions.append(
            OccurrenceContribution(
                producer="character",
                contribution_kind="action",
                content=_bound_text(
                    f"{acting_character} {action_text}",
                    limit=MAX_CONTRIBUTION_CONTENT,
                ),
                metadata={"actor": acting_character},
            )
        )

    if is_canonical_v2_move(move):
        move_norm = normalize_move_audibility(dict(move), acting_character, present_characters)
        beats = move_norm.get("beats")
        if isinstance(beats, list):
            for beat in beats:
                if not isinstance(beat, dict) or beat.get("type") != "speech":
                    continue
                dialogue = str(beat.get("dialogue", "") or "").strip()
                if not dialogue:
                    continue
                aud = str(
                    beat.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC
                ).lower()
                if aud == AUDIBILITY_PUBLIC:
                    contributions.append(
                        OccurrenceContribution(
                            producer="character",
                            contribution_kind="dialogue",
                            content=_bound_text(
                                f'{acting_character} said: "{dialogue}"',
                                limit=MAX_CONTRIBUTION_CONTENT,
                            ),
                            metadata={"actor": acting_character, "audibility": aud},
                        )
                    )
                else:
                    audience = _clean_audience(beat.get("audience"), acting_character)
                    scoped.append(
                        ScopedEvidence(
                            audibility=aud,
                            audience=audience,
                            content=_bound_text(
                                f'{acting_character} said: "{dialogue}"',
                                limit=MAX_CONTRIBUTION_CONTENT,
                            ),
                        )
                    )
        return contributions[:MAX_CONTRIBUTIONS], scoped[:MAX_SCOPED_EVIDENCE]

    dialogue = _move_dialogue_text(move)
    if not dialogue:
        return contributions[:MAX_CONTRIBUTIONS], scoped[:MAX_SCOPED_EVIDENCE]
    aud = str(move.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    if aud == AUDIBILITY_PUBLIC:
        contributions.append(
            OccurrenceContribution(
                producer="character",
                contribution_kind="dialogue",
                content=_bound_text(
                    f'{acting_character} said: "{dialogue}"',
                    limit=MAX_CONTRIBUTION_CONTENT,
                ),
                metadata={"actor": acting_character, "audibility": aud},
            )
        )
    else:
        audience = _clean_audience(move.get("audience"), acting_character)
        scoped.append(
            ScopedEvidence(
                audibility=aud,
                audience=audience,
                content=_bound_text(
                    f'{acting_character} said: "{dialogue}"',
                    limit=MAX_CONTRIBUTION_CONTENT,
                ),
            )
        )
    return contributions[:MAX_CONTRIBUTIONS], scoped[:MAX_SCOPED_EVIDENCE]


def _director_contribution(director_decision: dict[str, Any]) -> OccurrenceContribution | None:
    if not isinstance(director_decision, dict):
        return None
    environment_event = str(director_decision.get("environment_event", "") or "").strip()
    if not environment_event:
        return None
    return OccurrenceContribution(
        producer="director",
        contribution_kind="environment_event",
        content=_bound_text(environment_event, limit=MAX_CONTRIBUTION_CONTENT),
    )


def _substantive_user_history_entry(
    rp_history: list[dict[str, Any]],
) -> dict[str, Any] | None:
    latest_user: dict[str, Any] | None = None
    latest_skip: dict[str, Any] | None = None
    for entry in rp_history:
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get("kind", "") or "")
        if kind == "user":
            latest_user = entry
        elif kind == "player_skip":
            latest_skip = entry
    if latest_user is None:
        return None
    if latest_skip is not None:
        user_seq = int(latest_user.get("sequence_index", -1))
        skip_seq = int(latest_skip.get("sequence_index", -1))
        if skip_seq > user_seq:
            return None
    return latest_user


def _triggering_user_from_history(
    rp_history: list[dict[str, Any]] | None,
) -> TriggeringUser | None:
    if not rp_history:
        return None
    entry = _substantive_user_history_entry(rp_history)
    if not isinstance(entry, dict):
        return None
    entry_id = str(entry.get("entry_id", "") or "").strip()
    if not entry_id:
        return None
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    speaker = str(
        entry.get("actor_id") or metadata.get("speaker") or "Player"
    ).strip()
    raw_content = str(entry.get("content", "") or "").strip()
    content = _bound_text(raw_content, limit=MAX_TRIGGER_EXCERPT) if raw_content else None
    seq = entry.get("sequence_index")
    return TriggeringUser(
        entry_id=entry_id,
        speaker=speaker,
        content=content,
        hg_round_id=(
            str(entry.get("hg_round_id")).strip() if entry.get("hg_round_id") else None
        ),
        sequence_index=int(seq) if seq is not None else None,
    )


def _structured_fact_refs_from_markers(markers: list[str]) -> list[StructuredFactRef]:
    refs: list[StructuredFactRef] = []
    for marker in markers:
        token = str(marker or "").strip()
        if not token:
            continue
        refs.append(StructuredFactRef(ref_kind="grounding_marker", ref_id=token))
        if len(refs) >= MAX_FACT_REFS:
            break
    return refs


def build_move_specific_summary(
    *,
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    state_changes: list[str],
    grounding_markers: list[str],
    base_promotion: bool,
) -> str:
    """Prefer move-specific audibility-safe meaning; templates only as fallback."""
    action = _move_action_text(move)
    dialogue = root_or_flat_dialogue_text(move)
    environment_event = str(
        director_decision.get("environment_event", "") or ""
    ).strip()

    if action and dialogue:
        summary = f'{acting_character} {action}; said: "{dialogue}"'
    elif action:
        summary = f"{acting_character} {action}"
    elif dialogue:
        summary = f'{acting_character} said: "{dialogue}"'
    elif environment_event:
        summary = environment_event
    elif state_changes:
        summary = str(state_changes[0])
    else:
        summary = f"{acting_character} took action"

    if not base_promotion and grounding_markers:
        from scene_grounding import grounding_markers_event_summary

        summary = grounding_markers_event_summary(grounding_markers)

    return _bound_text(summary, limit=500)


def build_occurrence_evidence_for_promotion(
    *,
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    grounding_markers: list[str],
    rp_history: list[dict[str, Any]] | None,
    present_characters: list[str],
) -> OccurrenceEvidence | None:
    contributions, scoped = _character_contributions(
        acting_character=acting_character,
        move=move,
        present_characters=present_characters,
    )
    director = _director_contribution(director_decision)
    if director is not None:
        contributions.append(director)
    contributions = contributions[:MAX_CONTRIBUTIONS]

    trigger = _triggering_user_from_history(rp_history)
    refs = _structured_fact_refs_from_markers(grounding_markers)

    if not (contributions or trigger or refs or scoped):
        return None
    return OccurrenceEvidence(
        contributions=contributions,
        triggering_user=trigger,
        structured_fact_refs=refs,
        scoped_evidence=scoped,
    )


def append_resolved_outcome_refs(
    evidence: OccurrenceEvidence | None,
    outcome_ids: list[str],
) -> OccurrenceEvidence | None:
    if not outcome_ids:
        return evidence
    refs = list(evidence.structured_fact_refs) if evidence is not None else []
    existing = {r.ref_id for r in refs}
    for outcome_id in outcome_ids:
        token = str(outcome_id or "").strip()
        if not token or token in existing:
            continue
        refs.append(StructuredFactRef(ref_kind="resolved_outcome", ref_id=token))
        existing.add(token)
        if len(refs) >= MAX_FACT_REFS:
            break
    if evidence is None and not refs:
        return None
    if evidence is None:
        return OccurrenceEvidence(structured_fact_refs=refs)
    evidence.structured_fact_refs = refs[:MAX_FACT_REFS]
    return evidence
