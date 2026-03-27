import json
from typing import Any


def get_available_characters(*, character_loader_cls: Any) -> list[str]:
    loader = character_loader_cls()
    return loader.list_available_characters()


def resolve_character_file(
    *, loader: Any, identifier: str, make_agent_identifier_fn
) -> str | None:
    normalized = str(identifier or "").removesuffix(".json").strip()
    if not normalized:
        return None

    available = loader.list_available_characters()
    canonical_by_lower = {str(item).lower(): str(item) for item in available}
    canonical_direct = canonical_by_lower.get(normalized.lower())
    if canonical_direct:
        return canonical_direct

    try:
        loader.load_character_card(normalized)
        canonical_loaded = canonical_by_lower.get(normalized.lower())
        return canonical_loaded or normalized
    except FileNotFoundError:
        pass

    for candidate in available:
        try:
            card = loader.load_character_card(candidate)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        display_name = str(card.get("name", "")).strip()
        if display_name.lower() == normalized.lower():
            return candidate
        if (
            make_agent_identifier_fn(display_name).lower()
            == make_agent_identifier_fn(normalized).lower()
        ):
            return candidate

    return None


def get_character_display_name(
    *,
    st_module: Any,
    identifier: str,
    character_state_cls: Any,
    character_loader_cls: Any,
    resolve_character_file_fn,
) -> str:
    normalized_identifier = str(identifier or "").strip()
    if not normalized_identifier:
        return "Unknown"

    character_states = st_module.session_state.get("character_states", {})
    if isinstance(character_states, dict):
        state = character_states.get(normalized_identifier)
        if isinstance(state, character_state_cls) and str(state.name).strip():
            return str(state.name).strip()

    loader = character_loader_cls()
    char_file = resolve_character_file_fn(loader, normalized_identifier)
    if char_file is not None:
        try:
            card = loader.load_character_card(char_file)
            display_name = str(card.get("name", "") or "").strip()
            if display_name:
                return display_name
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    return normalized_identifier.replace("_", " ")


def get_character_display_names(
    *, identifiers: list[str], get_character_display_name_fn
) -> list[str]:
    return [get_character_display_name_fn(identifier) for identifier in identifiers]


def rebuild_character_agents(
    *,
    st_module: Any,
    model_client: Any,
    character_loader_cls: Any,
    resolve_character_file_fn,
) -> list[Any]:
    loader = character_loader_cls()
    selected_chars = st_module.session_state.get("selected_chars", [])
    identifiers: list[str] = []

    if isinstance(selected_chars, list) and selected_chars:
        identifiers = [str(item) for item in selected_chars]
    else:
        character_states = st_module.session_state.get("character_states", {})
        if isinstance(character_states, dict) and character_states:
            identifiers = list(character_states.keys())
        else:
            identifiers = [
                agent.name for agent in st_module.session_state.get("characters", [])
            ]

    resolved_files: list[str] = []
    agents: list[Any] = []
    for identifier in identifiers:
        char_file = resolve_character_file_fn(loader, identifier)
        if char_file is None:
            continue
        try:
            agent, _state = loader.load_and_create_agent(char_file, model_client)
            agents.append(agent)
            resolved_files.append(char_file)
        except FileNotFoundError:
            continue

    if agents:
        st_module.session_state["characters"] = agents
        st_module.session_state["selected_chars"] = resolved_files

    return agents
