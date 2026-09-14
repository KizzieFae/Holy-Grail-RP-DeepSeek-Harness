"""Shared Player-authorship authority contract and provenance projection (#157)."""

from __future__ import annotations

import json
from typing import Any

from .player_identity import player_character_file_id, resolve_player_display_name
from .session_history import history_entries
from .session_state import LiveSession
from .viewer_player_perception import resolve_player_character_name

PLAYER_AUTHORSHIP_GUARDRAIL_ID = "guardrail:player_authorship"

TIER1_PLAYER_ORIGIN_KINDS: frozenset[str] = frozenset(
    {
        "user_post",
        "player_decomposition",
        "character_card",
        "tagged_derived",
    }
)

MAX_REF_CHARS = 1200

PLAYER_AUTHORSHIP_GUARDRAIL_TEXT = (
    "Player-authorship authority: a Player-owned fact is authoritative only when provenance "
    "ultimately traces to an explicitly permitted Tier-1 origin (Player-authored post, "
    "authoritative Player decomposition derived from that post, Player/character card, or "
    "explicitly tagged derived fact with traceable Player lineage). "
    "Character/Narrator commits, generic transcript prose, orchestration output, untagged "
    "continuity/canon/grounding, and unknown provenance do NOT establish Player authority. "
    "Hard violations: unsupported objective Player assertion; unsupported Player "
    "sensation/embodiment; material Player-behavior amplification. "
    "Character private/scenario knowledge does NOT authorize fabrication of Player physical, "
    "physiological, emotional-display, or other sensory evidence. Such claimed observations "
    "require support from perception_fact:authorized_inventory:*, perception_fact:entitled:*, "
    "applicable grounding:* visible facts, or established player_fact:* observable sources. "
    "Subjective phrasing alone does not cure missing perceptual substrate. "
    "Permissible: faithful paraphrase of entitled perceptual evidence; fallible interpretive "
    "conclusions explicitly anchored to entitled perceptual evidence in the same move; "
    "collaborative world/environment invention without unsupported Player-body attribution. "
    "R02b (authorship: is the Player fact established?) is orthogonal to R14 (entitlement: "
    "may this Character know/use an established fact?)."
)

CHARACTER_PERCEPTUAL_GROUNDING_DISCIPLINE = (
    "PERCEPTUAL GROUNDING (Character move): Scenario premise, character-private knowledge, "
    "canon, and other context may inform private reasoning, motivation, tactics, dialogue, "
    "and decisions. Claims in action beats that the Character perceives Player sensory "
    "evidence (posture, expression, fatigue, trembling, bodily tells, emotional display, "
    "or similar) must be grounded in the AUTHORITATIVE PERCEPTUAL INVENTORY. "
    "Knowledge alone does not create evidence. An empty Player-targeted sensory inventory "
    "does not authorize inventing plausible observables. Subjective wording does not "
    "manufacture evidence."
)


def _truncate(text: str, limit: int = MAX_REF_CHARS) -> str:
    cleaned = str(text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def build_player_authorship_guardrail() -> dict[str, Any]:
    return {
        "ref_id": PLAYER_AUTHORSHIP_GUARDRAIL_ID,
        "kind": "guardrail",
        "authority_class": "authoritative",
        "label": "Player authorship",
        "text": PLAYER_AUTHORSHIP_GUARDRAIL_TEXT,
        "provenance": {
            "origin_kind": "guardrail",
            "contract": "player_authorship_authority_v1",
        },
    }


def _player_fact_ref(
    *,
    ref_id: str,
    kind: str,
    label: str,
    text: str,
    origin_kind: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    if origin_kind not in TIER1_PLAYER_ORIGIN_KINDS:
        raise ValueError(f"unsupported player authority origin_kind: {origin_kind}")
    return {
        "ref_id": ref_id,
        "kind": kind,
        "authority_class": "authoritative",
        "label": label,
        "text": _truncate(text),
        "provenance": {
            **dict(provenance),
            "origin_kind": origin_kind,
            "player_authorship_tier": "tier_1",
        },
    }


def _project_user_post_refs(history: list[dict[str, Any]], player_character: str | None) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for entry in history_entries(history):
        if entry.kind != "user":
            continue
        entry_id = str(entry.entry_id or "").strip()
        content = str(entry.content or "").strip()
        if not entry_id or not content:
            continue
        refs.append(
            _player_fact_ref(
                ref_id=f"player_fact:user_post:{entry_id}",
                kind="player_user_post",
                label=f"Player-authored post ({entry_id})",
                text=content,
                origin_kind="user_post",
                provenance={
                    "entry_id": entry_id,
                    "sequence_index": entry.sequence_index,
                    "hg_round_id": entry.hg_round_id,
                    "player_character": player_character,
                },
            )
        )
        metadata = dict(entry.metadata or {})
        decomposition = metadata.get("player_decomposition") or metadata.get("semantic_decomposition")
        if isinstance(decomposition, dict):
            refs.append(
                _player_fact_ref(
                    ref_id=f"player_fact:decomposition:{entry_id}",
                    kind="player_decomposition",
                    label=f"Player decomposition ({entry_id})",
                    text=_truncate(json.dumps(decomposition, ensure_ascii=False)),
                    origin_kind="player_decomposition",
                    provenance={
                        "entry_id": entry_id,
                        "sequence_index": entry.sequence_index,
                        "source_post_ref": f"player_fact:user_post:{entry_id}",
                        "player_character": player_character,
                    },
                )
            )
    return refs


def _project_player_card_refs(fixture: LiveSession, player_character: str | None) -> list[dict[str, Any]]:
    snapshot = dict(getattr(fixture, "setup_snapshot", None) or {})
    file_id = player_character_file_id(snapshot)
    if not file_id:
        return []
    cards = snapshot.get("character_cards") or {}
    if not isinstance(cards, dict):
        return []
    card = cards.get(file_id)
    if not isinstance(card, dict):
        return []
    refs: list[dict[str, Any]] = []
    display = resolve_player_display_name(
        player_character_file_id=file_id,
        names_by_file=dict(snapshot.get("character_file_ids") or {}),
    ) or player_character or file_id
    for field in ("description", "appearance", "personality", "background"):
        text = str(card.get(field) or "").strip()
        if not text:
            continue
        refs.append(
            _player_fact_ref(
                ref_id=f"player_fact:card:{file_id}:{field}",
                kind="character_card",
                label=f"Player character card ({display}: {field})",
                text=text,
                origin_kind="character_card",
                provenance={
                    "character_file_id": file_id,
                    "player_character": display,
                    "source_field": field,
                },
            )
        )
    lore_facts = card.get("lore_facts") or []
    if isinstance(lore_facts, list):
        for index, item in enumerate(lore_facts):
            text = str(item or "").strip()
            if not text:
                continue
            refs.append(
                _player_fact_ref(
                    ref_id=f"player_fact:card:{file_id}:lore:{index}",
                    kind="character_card",
                    label=f"Player character card lore ({display}:{index})",
                    text=text,
                    origin_kind="character_card",
                    provenance={
                        "character_file_id": file_id,
                        "player_character": display,
                        "source_field": "lore_facts",
                        "source_index": index,
                    },
                )
            )
    return refs


def project_player_authority_references(
    fixture: LiveSession,
    *,
    player_character: str | None = None,
) -> list[dict[str, Any]]:
    """Project Tier-1 Player-authoritative refs from session state (anti-laundering safe)."""
    resolved_player = player_character
    if not resolved_player and getattr(fixture, "setup_snapshot", None) is not None:
        resolved_player = resolve_player_character_name(fixture)
    refs: list[dict[str, Any]] = []
    history = list(getattr(fixture, "rp_history", None) or [])
    refs.extend(_project_user_post_refs(history, resolved_player))
    refs.extend(_project_player_card_refs(fixture, resolved_player))
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ref in refs:
        ref_id = str(ref.get("ref_id") or "").strip()
        if not ref_id or ref_id in seen:
            continue
        seen.add(ref_id)
        merged.append(ref)
    return merged


def merge_player_authorship_authority_references(
    base_refs: list[dict[str, Any]],
    fixture: LiveSession,
    *,
    player_character: str | None = None,
    include_guardrail: bool = True,
) -> list[dict[str, Any]]:
    """Insert guardrail + player inventory ahead of other authority refs (deduped)."""
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    if include_guardrail:
        guardrail = build_player_authorship_guardrail()
        ordered.append(guardrail)
        seen.add(PLAYER_AUTHORSHIP_GUARDRAIL_ID)
    for ref in project_player_authority_references(fixture, player_character=player_character):
        ref_id = str(ref.get("ref_id") or "").strip()
        if ref_id and ref_id not in seen:
            seen.add(ref_id)
            ordered.append(ref)
    for ref in base_refs:
        ref_id = str(ref.get("ref_id") or "").strip()
        if not ref_id or ref_id in seen:
            continue
        seen.add(ref_id)
        ordered.append(ref)
    return ordered
