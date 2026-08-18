from collections.abc import Callable
from typing import Any


def eligible_agent_keys_for_present_characters(
    present_characters: list[Any],
    participant_agent_keys: list[str],
    *,
    display_name_for_key: Callable[[str], str],
) -> list[str]:
    """Map continuity ``present_characters`` entries to ``AssistantAgent.name`` keys.

    Scene state may list card display names (e.g. ``Hannah Lovelace``) while the
    turn runner uses agent identifiers (e.g. ``Hannah_Lovelace``). Without this
    mapping, :func:`get_available_actors` can drop valid cast members from the
    eligible pool. Only exact matches: agent key self-match or display string
    equality via ``display_name_for_key`` — no fuzzy aliases.
    """
    out: list[str] = []
    seen: set[str] = set()
    keys = [str(k).strip() for k in participant_agent_keys if str(k or "").strip()]
    for raw in present_characters or []:
        label = str(raw or "").strip()
        if not label:
            continue
        resolved = ""
        if label in keys:
            resolved = label
        else:
            for cn in keys:
                if str(display_name_for_key(cn) or "").strip() == label:
                    resolved = cn
                    break
        if resolved and resolved not in seen:
            seen.add(resolved)
            out.append(resolved)
    return out


def validate_turn_selection_decision(
    decision: dict[str, Any],
    participant_names: list[str],
    available_actors: list[str],
    trigger_text: str,
    spotlight_history: list[str],
    *,
    pending_forced_speaker: str | None = None,
    forced_speaker_consumed: bool = False,
    continuation_override_actor: str | None = None,
    offstage_characters: list[str] | None = None,
) -> list[str]:
    issues: list[str] = []
    next_actor = str(decision.get("next_actor", "") or "")
    end_round = bool(decision.get("end_round"))
    if end_round and not next_actor:
        return []

    if next_actor not in participant_names:
        issues.append(f"Selected actor is not a participant: {next_actor}")
        return issues
    if next_actor not in available_actors:
        issues.append(f"Selected actor is not in available_next_actors: {next_actor}")

    off = offstage_characters or []
    if off and next_actor in off:
        issues.append(f"Selected actor is marked offstage: {next_actor}")

    if not (decision.get("is_fallback") or decision.get("source") == "fallback"):
        pf = str(pending_forced_speaker or "").strip()
        if (
            pf
            and not forced_speaker_consumed
            and pf in available_actors
            and next_actor != pf
        ):
            issues.append(
                f"next_actor should match pending forced speaker ({pf}), got {next_actor}"
            )
        co = str(continuation_override_actor or "").strip()
        sh = spotlight_history or []
        tail = [str(x or "").strip() for x in sh if str(x or "").strip()]
        last_spot = tail[-1] if tail else ""
        continuation_skipped_c2 = bool(
            co and co in available_actors and last_spot and last_spot == co
        )
        if (
            co
            and co in available_actors
            and next_actor != co
            and not continuation_skipped_c2
        ):
            issues.append(
                f"next_actor should match continuation override ({co}), got {next_actor}"
            )

    return issues


def get_available_actors(
    participant_names: list[str],
    used_actors: list[str] | None = None,
    eligible_participants: list[str] | None = None,
    offstage_characters: list[str] | None = None,
) -> list[str]:
    used = set(used_actors or [])
    available = [name for name in participant_names if name not in used]
    if eligible_participants is not None:
        eligible = set(eligible_participants)
        available = [name for name in available if name in eligible]
    off = set(offstage_characters or [])
    return [name for name in available if name not in off]
