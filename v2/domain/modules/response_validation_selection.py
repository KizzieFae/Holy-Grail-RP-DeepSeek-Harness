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
