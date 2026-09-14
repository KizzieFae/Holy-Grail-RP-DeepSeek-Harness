"""Deterministic positive perceptual-authority inventory for Character cognition (#199)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from memory_layer.writes import resolve_present_characters  # noqa: E402
from perceptual_visibility_contract import PLAYER_SOURCE_KIND  # noqa: E402
from perceptual_visibility_legacy import perceptual_visibility_record_from_entry_metadata  # noqa: E402
from perceptual_visibility_projection import (  # noqa: E402
    assemble_perceptual_history_entry_for_viewer,
)
from scene_grounding import rebuild_scene_grounding_from_continuity  # noqa: E402

from .contract import PromptContribution  # noqa: E402
from .session_history import (  # noqa: E402
    PLAYER_SKIP_KIND,
    history_entries,
    presentation_uses_narrator_prose_for_character,
)
from .session_state import LiveSession  # noqa: E402
from .viewer_player_perception import (  # noqa: E402
    resolve_perceptual_scene_context,
    resolve_player_character_name,
)

PERCEPTION_FACT_AUTHORIZED_INVENTORY_PREFIX = "perception_fact:authorized_inventory"
PERCEPTION_FACT_ENTITLED_PREFIX = "perception_fact:entitled"

_PLAYER_VISIBLE_GROUNDING_CATEGORIES = frozenset(
    {
        "medical",
        "medical_status",
    }
)

_OBSERVABLE_UNIT_KINDS = frozenset(
    {
        "observable_event",
        "observable_scene",
        "speech",
    }
)


def _inventory_ref_id(character_id: str, hg_round_id: str) -> str:
    return f"{PERCEPTION_FACT_AUTHORIZED_INVENTORY_PREFIX}:{character_id}:{hg_round_id}"


def _entitled_ref_id(entry_id: str, unit_id: str) -> str:
    return f"{PERCEPTION_FACT_ENTITLED_PREFIX}:{entry_id}:{unit_id}"


def _grounding_ref_id(fact_id: str) -> str:
    return f"grounding:{fact_id}"


def _unit_text_map(record: Any) -> dict[str, str]:
    return {str(unit.unit_id): str(unit.text or "").strip() for unit in record.units}


def _inventory_item(
    *,
    ref_id: str,
    text: str,
    label: str,
    source: str,
    targets_player: bool,
    entry_id: str | None = None,
    unit_id: str | None = None,
    fact_id: str | None = None,
) -> dict[str, Any]:
    return {
        "ref_id": ref_id,
        "kind": "perception_fact",
        "authority_class": "authoritative",
        "label": label,
        "text": text,
        "provenance": {
            "inventory_source": source,
            "targets_player": targets_player,
            "entry_id": entry_id,
            "unit_id": unit_id,
            "fact_id": fact_id,
        },
    }


def _player_name_matches(subject: str, player_character: str | None) -> bool:
    if not player_character:
        return False
    return str(subject or "").strip().lower() == str(player_character).strip().lower()


def _collect_grounding_perceptual_refs(
    fixture: LiveSession,
    *,
    player_character: str | None,
) -> list[dict[str, Any]]:
    mgr = fixture.manager
    if mgr is None:
        return []
    grounding = rebuild_scene_grounding_from_continuity(mgr)
    refs: list[dict[str, Any]] = []
    for raw in grounding.get("facts") or []:
        if not isinstance(raw, dict):
            continue
        category = str(raw.get("category") or "").strip()
        if category not in _PLAYER_VISIBLE_GROUNDING_CATEGORIES:
            continue
        fact_id = str(raw.get("fact_id") or "").strip()
        summary = str(raw.get("value_summary") or "").strip()
        if not fact_id or not summary:
            continue
        value = raw.get("value") if isinstance(raw.get("value"), dict) else {}
        subject = str(value.get("subject") or value.get("subject_id") or "").strip()
        targets_player = _player_name_matches(subject, player_character)
        refs.append(
            _inventory_item(
                ref_id=_grounding_ref_id(fact_id),
                text=summary,
                label=f"Settled visible scene fact ({category})",
                source="scene_grounding",
                targets_player=targets_player,
                fact_id=fact_id,
            )
        )
    return refs


def _append_inventory_from_assembly(
    items: list[dict[str, Any]],
    seen: set[str],
    *,
    assembly: Any,
    record: Any,
    entry_id: str,
    source: str,
    player_character: str | None,
    acting_character: str | None,
) -> None:
    if record is None:
        return
    unit_text = _unit_text_map(record)
    for unit_id in assembly.included_unit_ids:
        ref_id = _entitled_ref_id(entry_id, unit_id)
        if ref_id in seen:
            continue
        unit = next((u for u in record.units if str(u.unit_id) == str(unit_id)), None)
        if unit is None:
            continue
        if str(unit.kind) not in _OBSERVABLE_UNIT_KINDS:
            continue
        text = unit_text.get(str(unit_id), "")
        if not text:
            continue
        targets_player = False
        if record.source_kind == PLAYER_SOURCE_KIND:
            targets_player = True
        elif player_character and unit is not None:
            recipients = getattr(unit, "recipients", None)
            recipient_chars = []
            if recipients is not None:
                recipient_chars = list(getattr(recipients, "characters", None) or [])
            if any(_player_name_matches(name, player_character) for name in recipient_chars):
                targets_player = True
            elif player_character.lower() in text.lower():
                targets_player = True
        seen.add(ref_id)
        items.append(
            _inventory_item(
                ref_id=ref_id,
                text=text,
                label=f"Entitled percept ({source})",
                source=source,
                targets_player=targets_player,
                entry_id=entry_id,
                unit_id=str(unit_id),
            )
        )


def _collect_history_perceptual_refs(
    fixture: LiveSession,
    *,
    character_id: str,
    player_character: str | None,
) -> list[dict[str, Any]]:
    history = list(getattr(fixture, "rp_history", None) or [])
    present = resolve_present_characters(
        continuity_manager=fixture.manager,
        char_names=list(fixture.cast),
    )
    scene_context = resolve_perceptual_scene_context(fixture)
    entries = history_entries(history)
    committed_by_commit = {
        entry.domain_commit_id: entry
        for entry in entries
        if entry.kind == "committed_turn" and entry.domain_commit_id
    }
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for entry in entries:
        if entry.kind == PLAYER_SKIP_KIND:
            continue

        if entry.kind == "opening":
            assembly = assemble_perceptual_history_entry_for_viewer(
                entry.to_dict(),
                viewer_character=character_id,
                present_characters=present,
                source_kind="opening",
                perceptual_scene_context=scene_context,
                player_character=player_character,
            )
            record, _ = perceptual_visibility_record_from_entry_metadata(entry.metadata or {})
            _append_inventory_from_assembly(
                items,
                seen,
                assembly=assembly,
                record=record,
                entry_id=entry.entry_id,
                source="opening_pvr",
                player_character=player_character,
                acting_character=None,
            )
            continue

        if entry.kind == "user":
            assembly = assemble_perceptual_history_entry_for_viewer(
                entry.to_dict(),
                viewer_character=character_id,
                present_characters=present,
                source_kind=PLAYER_SOURCE_KIND,
                perceptual_scene_context=scene_context,
                player_character=player_character or entry.actor_id,
            )
            record, _ = perceptual_visibility_record_from_entry_metadata(entry.metadata or {})
            _append_inventory_from_assembly(
                items,
                seen,
                assembly=assembly,
                record=record,
                entry_id=entry.entry_id,
                source="player_pvr",
                player_character=player_character,
                acting_character=entry.actor_id,
            )
            continue

        if entry.kind == "presentation":
            commit_id = entry.domain_commit_id
            committed = committed_by_commit.get(commit_id) if commit_id else None
            structured_move = None
            acting_character = None
            if committed is not None:
                move = (committed.metadata or {}).get("structured_move")
                if isinstance(move, dict):
                    structured_move = move
                acting_character = str(committed.actor_id or "Character")
            if presentation_uses_narrator_prose_for_character(entry):
                assembly = assemble_perceptual_history_entry_for_viewer(
                    entry.to_dict(),
                    viewer_character=character_id,
                    present_characters=present,
                    structured_move=structured_move,
                    acting_character=acting_character,
                    source_kind="narrator",
                    perceptual_scene_context=scene_context,
                    player_character=player_character,
                )
                record, _ = perceptual_visibility_record_from_entry_metadata(
                    entry.metadata or {},
                    structured_move=structured_move,
                    acting_character=acting_character,
                )
                _append_inventory_from_assembly(
                    items,
                    seen,
                    assembly=assembly,
                    record=record,
                    entry_id=entry.entry_id,
                    source="narrator_pvr",
                    player_character=player_character,
                    acting_character=acting_character,
                )
            elif committed is not None:
                move = (committed.metadata or {}).get("structured_move")
                structured = move if isinstance(move, dict) else None
                actor = str(committed.actor_id or "Character")
                assembly = assemble_perceptual_history_entry_for_viewer(
                    committed.to_dict(),
                    viewer_character=character_id,
                    present_characters=present,
                    structured_move=structured,
                    acting_character=actor,
                    source_kind="character",
                    perceptual_scene_context=scene_context,
                    player_character=player_character,
                )
                record, _ = perceptual_visibility_record_from_entry_metadata(
                    committed.metadata or {},
                    structured_move=structured,
                    acting_character=actor,
                )
                _append_inventory_from_assembly(
                    items,
                    seen,
                    assembly=assembly,
                    record=record,
                    entry_id=committed.entry_id,
                    source="character_pvr",
                    player_character=player_character,
                    acting_character=actor,
                )
            continue

        if entry.kind == "committed_turn":
            if entry.domain_commit_id and any(
                e.kind == "presentation" and e.domain_commit_id == entry.domain_commit_id
                for e in entries
            ):
                continue
            move = (entry.metadata or {}).get("structured_move")
            structured = move if isinstance(move, dict) else None
            actor = str(entry.actor_id or "Character")
            assembly = assemble_perceptual_history_entry_for_viewer(
                entry.to_dict(),
                viewer_character=character_id,
                present_characters=present,
                structured_move=structured,
                acting_character=actor,
                source_kind="character",
                perceptual_scene_context=scene_context,
                player_character=player_character,
            )
            record, _ = perceptual_visibility_record_from_entry_metadata(
                entry.metadata or {},
                structured_move=structured,
                acting_character=actor,
            )
            _append_inventory_from_assembly(
                items,
                seen,
                assembly=assembly,
                record=record,
                entry_id=entry.entry_id,
                source="character_pvr",
                player_character=player_character,
                acting_character=actor,
            )

    return items


def build_character_perceptual_inventory_refs(
    fixture: LiveSession,
    *,
    character_id: str,
    hg_round_id: str,
) -> list[dict[str, Any]]:
    """Positive perceptual-authority inventory refs for generator and semantic evaluation."""
    player_character = None
    if getattr(fixture, "setup_snapshot", None):
        player_character = resolve_player_character_name(fixture)
    history_items = _collect_history_perceptual_refs(
        fixture,
        character_id=character_id,
        player_character=player_character,
    )
    grounding_items = _collect_grounding_perceptual_refs(
        fixture,
        player_character=player_character,
    )
    entitled_items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in history_items + grounding_items:
        ref_id = str(item.get("ref_id") or "")
        if not ref_id or ref_id in seen:
            continue
        seen.add(ref_id)
        entitled_items.append(item)

    player_sensory_items = [
        item
        for item in entitled_items
        if bool((item.get("provenance") or {}).get("targets_player"))
    ]
    inventory_ref_id = _inventory_ref_id(character_id, hg_round_id)
    if player_sensory_items:
        summary_lines = [
            f"- {item['ref_id']}: {item['text']}"
            for item in player_sensory_items
        ]
        summary = (
            f"Authorized perceptual evidence available to {character_id} at this scene point "
            f"({len(entitled_items)} entitled item(s); {len(player_sensory_items)} "
            f"Player-targeted sensory item(s)):\n"
            + "\n".join(summary_lines)
        )
    else:
        summary = (
            f"No authorized perceptual evidence of Player physical display, bodily state, "
            f"emotional display, or other sensory observables is available to {character_id} "
            f"at this scene point."
        )
        if entitled_items:
            other_lines = [
                f"- {item['ref_id']}: {item['text']}"
                for item in entitled_items
                if not (item.get("provenance") or {}).get("targets_player")
            ]
            if other_lines:
                summary += (
                    "\nOther entitled perceptual evidence (non-Player sensory substrate):\n"
                    + "\n".join(other_lines)
                )

    master = {
        "ref_id": inventory_ref_id,
        "kind": "perception_fact",
        "authority_class": "authoritative",
        "label": f"Authorized perceptual inventory ({character_id})",
        "text": summary,
        "provenance": {
            "inventory_source": "character_perceptual_inventory_v1",
            "character_id": character_id,
            "hg_round_id": hg_round_id,
            "entitled_count": len(entitled_items),
            "player_sensory_count": len(player_sensory_items),
        },
    }
    return [master, *entitled_items]


def project_perceptual_inventory_contribution(
    fixture: LiveSession,
    *,
    manifest_id: str,
    character_id: str,
    hg_round_id: str,
) -> PromptContribution:
    refs = build_character_perceptual_inventory_refs(
        fixture,
        character_id=character_id,
        hg_round_id=hg_round_id,
    )
    master = refs[0]
    payload = {
        "inventory_ref_id": master["ref_id"],
        "character_id": character_id,
        "hg_round_id": hg_round_id,
        "entitled_entries": refs[1:],
        "summary": master["text"],
    }
    return PromptContribution(
        contribution_id=f"{manifest_id}-authoritative-perceptual-inventory",
        source_kind="authoritative_perceptual_inventory",
        authority_class="authoritative",
        knowledge_ids=tuple(ref["ref_id"] for ref in refs),
        priority=17,
        content=(
            "AUTHORITATIVE PERCEPTUAL INVENTORY (positive authority for sensory claims):\n"
            f"{master['text']}\n\n"
            "Indexed entries (cite ref_id when grounding sensory observations):\n"
            f"{json.dumps(payload['entitled_entries'], ensure_ascii=False, indent=2)}"
        ),
        provenance={
            "character_id": character_id,
            "hg_round_id": hg_round_id,
            "projection_kind": "character_perceptual_inventory_v1",
            "entitled_count": len(refs) - 1,
        },
    )
