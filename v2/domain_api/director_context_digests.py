"""Bounded Director context digests and completeness contract (#26)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from continuity_issue_manager_wiring import DEFAULT_ACTIVE_ISSUE_LIMIT  # noqa: E402
from continuity_issue_retrieval import get_active_issues  # noqa: E402
from continuity_state import IssueStatus  # noqa: E402

from .contract import PromptContribution  # noqa: E402
from .session_history import substantive_user_entry_for_trigger  # noqa: E402
from .session_state import LiveSession, RoundFixture  # noqa: E402

MAX_ORCHESTRATION_TURNS = 6
MAX_ACTION_CHARS = 160
MAX_DIALOGUE_CHARS = 240
MAX_SPOTLIGHT_HISTORY = 3

DIRECTOR_CONTEXT_CONTRACT_VERSION = "director_context_v1"


def _truncate(text: str, max_len: int) -> str:
    cleaned = str(text or "").strip()
    if len(cleaned) <= max_len:
        return cleaned
    if max_len <= 1:
        return cleaned[:max_len]
    return cleaned[: max_len - 1] + "…"


def _beat_text(move: dict[str, Any], beat_type: str) -> str:
    for beat in move.get("beats") or []:
        if isinstance(beat, dict) and beat.get("type") == beat_type:
            return str(beat.get(beat_type, "") or "")
    return ""


def _authority_ref(
    *,
    ref_id: str,
    kind: str,
    authority_class: str,
    label: str,
    text: str,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ref_id": ref_id,
        "kind": kind,
        "authority_class": authority_class,
        "label": label,
        "text": text,
    }
    if provenance:
        payload["provenance"] = dict(provenance)
    return payload


def project_recent_orchestration_digest(
    fixture: LiveSession,
    rnd: RoundFixture,
    manifest_id: str,
) -> tuple[PromptContribution | None, list[dict[str, Any]]]:
    """Project bounded current-round committed character turns for Director orchestration."""
    _ = fixture
    turns = list(rnd.character_turns)[-MAX_ORCHESTRATION_TURNS:]
    if not turns:
        return None, []

    entries: list[dict[str, Any]] = []
    refs: list[dict[str, Any]] = []
    for turn in turns:
        move = dict(turn.committed_move or {})
        actor = str(turn.character_id or "").strip()
        turn_index = int(turn.continuity_turn_index)
        action = _truncate(_beat_text(move, "action"), MAX_ACTION_CHARS)
        dialogue = _truncate(_beat_text(move, "dialogue"), MAX_DIALOGUE_CHARS)
        entry: dict[str, Any] = {
            "turn_index": turn_index,
            "actor": actor,
            "action": action,
            "dialogue": dialogue,
        }
        motivation = move.get("motivation")
        if isinstance(motivation, dict):
            addressee = str(motivation.get("addressee", "") or "").strip()
            if addressee:
                entry["addressee"] = addressee
        entries.append(entry)
        summary_parts = [part for part in (action, dialogue) if part]
        refs.append(
            _authority_ref(
                ref_id=f"orch:{turn_index}:{actor}",
                kind="orchestration_turn",
                authority_class="authoritative",
                label=f"Committed turn {turn_index} ({actor})",
                text=" | ".join(summary_parts) if summary_parts else f"{actor} committed turn",
                provenance={
                    "turn_index": turn_index,
                    "actor": actor,
                    "domain_commit_id": turn.domain_commit_id,
                },
            )
        )

    content = (
        "RECENT ORCHESTRATION (current round, bounded):\n"
        + json.dumps({"recent_orchestration": entries}, ensure_ascii=False, indent=2)
    )
    contribution = PromptContribution(
        contribution_id=f"{manifest_id}-recent-orchestration",
        source_kind="recent_orchestration",
        authority_class="authoritative",
        knowledge_ids=tuple(ref["ref_id"] for ref in refs),
        priority=14,
        content=content,
        provenance={
            "hg_round_id": rnd.hg_round_id,
            "turn_count": len(entries),
            "max_turns": MAX_ORCHESTRATION_TURNS,
        },
    )
    return contribution, refs


def project_actor_suitability_digest(
    fixture: LiveSession,
    rnd: RoundFixture,
    available: list[str],
    manifest_id: str,
    *,
    participation_mode: str | None = None,
) -> tuple[PromptContribution | None, list[dict[str, Any]]]:
    """Project structured actor-suitability evidence (not a scoring function)."""
    _ = fixture
    if len(available) <= 1:
        return None, []

    used = list(rnd.actors_used_this_round)
    spotlight = list(rnd.spotlight_history)[-MAX_SPOTLIGHT_HISTORY:]
    last_speaker = ""
    if rnd.character_turns:
        last_speaker = str(rnd.character_turns[-1].character_id or "").strip()

    payload = {
        "eligible_actors": list(available),
        "actors_used_this_round": used,
        "spotlight_last_3": spotlight,
        "last_speaker": last_speaker,
    }
    if participation_mode:
        payload["participation_mode"] = participation_mode

    refs: list[dict[str, Any]] = []
    for actor in available:
        refs.append(
            _authority_ref(
                ref_id=f"eligible:{actor}",
                kind="eligibility_fact",
                authority_class="authoritative",
                label=f"Eligible actor ({actor})",
                text=f"{actor} is eligible for Director selection in the current snapshot.",
            )
        )
    if used:
        refs.append(
            _authority_ref(
                ref_id="suit:used_this_round",
                kind="participation_summary",
                authority_class="derived",
                label="Actors used this round",
                text=f"Actors already used this round: {', '.join(used)}",
            )
        )
    if spotlight:
        refs.append(
            _authority_ref(
                ref_id="suit:spotlight",
                kind="participation_summary",
                authority_class="derived",
                label="Recent spotlight history",
                text=f"Recent spotlight order: {', '.join(spotlight)}",
            )
        )
    if last_speaker:
        refs.append(
            _authority_ref(
                ref_id="suit:last_speaker",
                kind="participation_summary",
                authority_class="derived",
                label="Last speaker",
                text=f"Last committed speaker this round: {last_speaker}",
            )
        )

    content = (
        "ACTOR SUITABILITY EVIDENCE:\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )
    contribution = PromptContribution(
        contribution_id=f"{manifest_id}-actor-suitability",
        source_kind="actor_suitability",
        authority_class="derived",
        knowledge_ids=tuple(ref["ref_id"] for ref in refs),
        priority=13,
        content=content,
        provenance={"hg_round_id": rnd.hg_round_id},
    )
    return contribution, refs


def project_scene_pressures_digest(
    fixture: LiveSession,
    manifest_id: str,
) -> tuple[PromptContribution | None, list[dict[str, Any]]]:
    """Project bounded active issue pressures with claim-specific authority refs."""
    mgr = fixture.manager
    active_issues = get_active_issues(
        manager=mgr,
        limit=DEFAULT_ACTIVE_ISSUE_LIMIT,
        statuses=[IssueStatus.ACTIVE, IssueStatus.ESCALATING],
    )
    if not active_issues:
        return None, []

    entries: list[dict[str, Any]] = []
    refs: list[dict[str, Any]] = []
    for issue in active_issues:
        issue_id = str(issue.issue_id)
        entry = {
            "issue_id": issue_id,
            "status": issue.status.value,
            "participants": list(issue.participants),
            "last_change": issue.last_change,
            "pressure_kind": issue.pressure_kind,
            "blocked_what": issue.blocked_what,
            "required_next_step": issue.required_next_step,
            "description": issue.description,
        }
        entries.append(entry)
        refs.extend(
            [
                _authority_ref(
                    ref_id=f"issue:{issue_id}:status",
                    kind="continuity_issue",
                    authority_class="authoritative",
                    label=f"Issue status ({issue_id})",
                    text=f"Issue {issue_id} status: {issue.status.value}",
                ),
                _authority_ref(
                    ref_id=f"issue:{issue_id}:participants",
                    kind="continuity_issue",
                    authority_class="authoritative",
                    label=f"Issue participants ({issue_id})",
                    text=f"Issue participants: {', '.join(issue.participants) or 'none'}",
                ),
            ]
        )
        if issue.last_change:
            refs.append(
                _authority_ref(
                    ref_id=f"issue:{issue_id}:last_change",
                    kind="continuity_issue",
                    authority_class="authoritative",
                    label=f"Issue last change ({issue_id})",
                    text=issue.last_change,
                )
            )
        if issue.blocked_what:
            refs.append(
                _authority_ref(
                    ref_id=f"issue:{issue_id}:blocked_what",
                    kind="continuity_issue",
                    authority_class="derived",
                    label=f"Issue blocked what ({issue_id})",
                    text=issue.blocked_what,
                )
            )
        if issue.pressure_kind:
            refs.append(
                _authority_ref(
                    ref_id=f"issue:{issue_id}:pressure_kind",
                    kind="continuity_issue",
                    authority_class="derived",
                    label=f"Issue pressure kind ({issue_id})",
                    text=issue.pressure_kind,
                )
            )
        if issue.required_next_step:
            refs.append(
                _authority_ref(
                    ref_id=f"issue:{issue_id}:required_next_step",
                    kind="continuity_issue",
                    authority_class="advisory",
                    label=f"Issue required next step ({issue_id})",
                    text=issue.required_next_step,
                )
            )
        if issue.description:
            refs.append(
                _authority_ref(
                    ref_id=f"issue:{issue_id}:description",
                    kind="continuity_issue",
                    authority_class="derived",
                    label=f"Issue description ({issue_id})",
                    text=issue.description,
                )
            )

    content = (
        "SCENE PRESSURES (bounded active issues):\n"
        + json.dumps({"active_issues": entries}, ensure_ascii=False, indent=2)
    )
    contribution = PromptContribution(
        contribution_id=f"{manifest_id}-scene-pressures",
        source_kind="scene_pressures",
        authority_class="derived",
        knowledge_ids=tuple(ref["ref_id"] for ref in refs),
        priority=12,
        content=content,
        provenance={"active_issue_count": len(entries)},
    )
    return contribution, refs


def _extract_steering_hints(content: str, eligible: list[str]) -> list[dict[str, Any]]:
    text = str(content or "").strip()
    if not text:
        return []

    hints: list[dict[str, Any]] = []
    seen: set[str] = set()
    ordered_names = sorted(
        {str(name).strip() for name in eligible if str(name or "").strip()},
        key=len,
        reverse=True,
    )
    lowered = text.casefold()
    for name in ordered_names:
        prefix = f"{name.casefold()},"
        prefix_space = f"{name.casefold()} "
        if lowered.startswith(prefix) or lowered.startswith(prefix_space):
            key = f"vocative:{name.casefold()}"
            if key not in seen:
                seen.add(key)
                hints.append(
                    {
                        "type": "vocative",
                        "target": name,
                        "extraction_method": "vocative_prefix_match",
                    }
                )

    for name in ordered_names:
        pattern = re.compile(rf"(?<!\w)@{re.escape(name)}\b", re.IGNORECASE)
        if pattern.search(text):
            key = f"mention:{name.casefold()}"
            if key not in seen:
                seen.add(key)
                hints.append(
                    {
                        "type": "at_mention",
                        "target": name,
                        "extraction_method": "at_mention",
                    }
                )
    return hints


def project_user_turn_source_and_hints(
    fixture: LiveSession,
    eligible: list[str],
    manifest_id: str,
) -> tuple[list[PromptContribution], list[dict[str, Any]]]:
    """Project authoritative user source and optional deterministic steering hints."""
    latest_user = substantive_user_entry_for_trigger(fixture.rp_history)
    if latest_user is None:
        return [], []

    raw_content = str(latest_user.get("content") or "").strip()
    if not raw_content:
        return [], []

    entry_id = str(latest_user.get("entry_id") or "unknown")
    contributions: list[PromptContribution] = []
    refs: list[dict[str, Any]] = [
        _authority_ref(
            ref_id=f"user:{entry_id}",
            kind="user_turn_source",
            authority_class="authoritative",
            label="Committed user turn",
            text=raw_content,
            provenance={
                "entry_id": entry_id,
                "sequence_index": latest_user.get("sequence_index"),
            },
        )
    ]
    contributions.append(
        PromptContribution(
            contribution_id=f"{manifest_id}-user-turn-source",
            source_kind="user_turn_source",
            authority_class="authoritative",
            knowledge_ids=(f"user:{entry_id}",),
            priority=15,
            content=f"USER TURN (committed):\n{raw_content}",
            provenance={
                "trigger_entry_id": entry_id,
                "trigger_sequence_index": latest_user.get("sequence_index"),
                "visibility": "orchestration_projection",
                "trigger_redacted": False,
            },
        )
    )

    hints = _extract_steering_hints(raw_content, eligible)
    if hints:
        hint_refs: list[dict[str, Any]] = []
        for index, hint in enumerate(hints):
            target = str(hint.get("target") or "")
            method = str(hint.get("extraction_method") or "unknown")
            ref_id = f"steer:{entry_id}:hint:{index}"
            hint_refs.append(
                _authority_ref(
                    ref_id=ref_id,
                    kind="user_steering_hint",
                    authority_class="derived",
                    label=f"Steering hint ({target})",
                    text=f"Deterministic {method} hint toward {target}",
                    provenance={"extraction_method": method, "target": target},
                )
            )
        refs.extend(hint_refs)
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-user-steering-hints",
                source_kind="user_steering_hints",
                authority_class="derived",
                knowledge_ids=tuple(ref["ref_id"] for ref in hint_refs),
                priority=16,
                content=(
                    "USER STEERING HINTS (deterministic extraction only):\n"
                    + json.dumps({"hints": hints}, ensure_ascii=False, indent=2)
                ),
                provenance={
                    "trigger_entry_id": entry_id,
                    "extraction_method": "deterministic_vocative_and_at_mention",
                },
            )
        )
    return contributions, refs


def build_director_authority_references(
    *ref_groups: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Aggregate authority refs while preserving first occurrence order."""
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in ref_groups:
        for ref in group:
            ref_id = str(ref.get("ref_id") or "").strip()
            if not ref_id or ref_id in seen:
                continue
            seen.add(ref_id)
            merged.append(dict(ref))
    return merged


def _has_source_kind(contributions: list[PromptContribution], source_kind: str) -> bool:
    return any(
        contribution.source_kind == source_kind and str(contribution.content or "").strip()
        for contribution in contributions
    )


def validate_director_context_completeness(
    contributions: list[PromptContribution],
    *,
    has_round_turns: bool,
    multiple_eligible: bool,
    has_active_issues: bool,
    has_user_turn: bool,
) -> dict[str, Any]:
    """Validate required Director context contributions; raise ValueError when missing."""
    required: list[str] = ["scene_state", "scene_progression", "inference_instruction"]
    missing: list[str] = []
    for source_kind in required:
        if not _has_source_kind(contributions, source_kind):
            missing.append(source_kind)

    conditional: list[tuple[str, bool]] = [
        ("recent_orchestration", has_round_turns),
        ("actor_suitability", multiple_eligible),
        ("scene_pressures", has_active_issues),
        ("user_turn_source", has_user_turn),
    ]
    for source_kind, required_when in conditional:
        if required_when:
            required.append(source_kind)
            if not _has_source_kind(contributions, source_kind):
                missing.append(source_kind)

    if missing:
        raise ValueError(
            "Director context completeness contract failed; missing required contributions: "
            + ", ".join(missing)
        )

    return {
        "contract_version": DIRECTOR_CONTEXT_CONTRACT_VERSION,
        "satisfied": True,
        "required_contributions": required,
        "warnings": [],
    }


def build_director_scene_evidence_contributions(
    fixture: LiveSession,
    rnd: RoundFixture,
    manifest_id: str,
    available: list[str],
    *,
    participation_mode: str | None = None,
    auth_contributions: list[PromptContribution],
) -> tuple[list[PromptContribution], list[dict[str, Any]]]:
    """Collect shared legitimate scene evidence for Director and semantic QA."""
    contributions = list(auth_contributions)
    ref_groups: list[list[dict[str, Any]]] = []

    orch_contrib, orch_refs = project_recent_orchestration_digest(fixture, rnd, manifest_id)
    if orch_contrib is not None:
        contributions.append(orch_contrib)
        ref_groups.append(orch_refs)

    suit_contrib, suit_refs = project_actor_suitability_digest(
        fixture,
        rnd,
        available,
        manifest_id,
        participation_mode=participation_mode,
    )
    if suit_contrib is not None:
        contributions.append(suit_contrib)
        ref_groups.append(suit_refs)

    pressure_contrib, pressure_refs = project_scene_pressures_digest(fixture, manifest_id)
    if pressure_contrib is not None:
        contributions.append(pressure_contrib)
        ref_groups.append(pressure_refs)

    user_contribs, user_refs = project_user_turn_source_and_hints(
        fixture,
        available,
        manifest_id,
    )
    contributions.extend(user_contribs)
    if user_refs:
        ref_groups.append(user_refs)

    return contributions, build_director_authority_references(*ref_groups)


def director_scene_condition_flags(
    fixture: LiveSession,
    rnd: RoundFixture,
    available: list[str],
) -> dict[str, bool]:
    mgr = fixture.manager
    active_issue_ids = list(getattr(mgr.scene_state, "active_issue_ids", None) or [])
    return {
        "has_round_turns": bool(rnd.character_turns),
        "multiple_eligible": len(available) > 1,
        "has_active_issues": bool(active_issue_ids),
        "has_user_turn": substantive_user_entry_for_trigger(fixture.rp_history) is not None,
    }
