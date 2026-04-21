"""Shared scene-start bootstrap spine (GitHub #83).

Single canonical ordering for fresh continuity: ``initialize_fresh_continuity_scene_core``
(``initialize_scene`` → cast bootstrap → opening backfill → one ``apply_scene_setup``),
plus UI/headless helpers for opening mirror, opener location/time, narrator resolution,
and headless template bundle prep — callers inject I/O and concrete ``apply`` targets.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class FreshContinuityInitParams:
    """Inputs for the pre-finalize continuity scene slice (new scene only)."""

    character_names: list[str]
    opening_description: str
    scene_setup: dict[str, Any] | None


def initialize_fresh_continuity_scene_core(
    manager: Any,
    *,
    params: FreshContinuityInitParams,
    build_initial_scene_issues_fn: Callable[..., Any],
    apply_scene_setup_to_scene_state_fn: Callable[..., None],
) -> None:
    """Initialize ``manager.scene_state`` when unset; then bootstrap cast and apply setup.

    Ordering (must stay aligned with ``restore_or_initialize_continuity_manager``):

    1. ``initialize_scene`` with ``initial_issues=build_initial_scene_issues(scene_setup)``
    2. ``bootstrap_present_characters_from_cast``
    3. Backfill ``opening_description`` on scene_state if still empty
    4. Single ``apply_scene_setup_to_scene_state`` when ``scene_setup`` is non-None

    Callers that load from ``from_dict`` and already have ``scene_state`` skip step 1
    only when ``manager.scene_state`` was created by restore — this function is intended
    for the branch where a new manager needs its first ``scene_state``.
    """
    if manager.scene_state is None:
        manager.initialize_scene(
            location=None,
            opening_description=params.opening_description,
            present_characters=params.character_names,
            initial_issues=build_initial_scene_issues_fn(params.scene_setup),
        )

    manager.bootstrap_present_characters_from_cast(params.character_names)
    if params.opening_description and not manager.scene_state.opening_description:
        manager.scene_state.opening_description = params.opening_description
    if params.scene_setup:
        # Call shape must match ``restore_or_initialize_continuity_manager`` injectees
        # (e.g. ``app.apply_scene_setup_to_scene_state``: two positionals + continuity_manager=).
        apply_scene_setup_to_scene_state_fn(
            manager.scene_state,
            params.scene_setup,
            continuity_manager=manager,
        )


def mirror_opening_into_scene_state(
    continuity_manager: Any,
    opening_final: str,
) -> None:
    """Set ``opening_description`` and ``environment_description`` to the resolved opening.

    Matches historical Streamlit behavior: ``initialize_scene`` only set
    ``opening_description``; environment mirror was applied before finalize.
    """
    if continuity_manager is None or continuity_manager.scene_state is None:
        return
    ss = continuity_manager.scene_state
    ss.opening_description = str(opening_final or "")
    ss.environment_description = str(opening_final or "")


def apply_opener_location_time_to_continuity(
    continuity_manager: Any,
    opener: Any | None,
    *,
    apply_location: bool = True,
) -> None:
    """Apply optional opener-derived location / time before setup seam finalize.

    When ``apply_location`` is False, only ``time`` is applied (Issue #94: location
    may already be set from composed ``BootstrapInterpretation``).
    """
    if continuity_manager is None or continuity_manager.scene_state is None:
        return
    if opener is None:
        return
    loc = getattr(opener, "location", None)
    if apply_location and loc:
        continuity_manager.scene_state.location = loc
        continuity_manager.notify_raw_location_bypass_for_audit()
    tim = getattr(opener, "time", None)
    if tim:
        continuity_manager.scene_state.time_of_day = tim


async def resolve_streamlit_opening_narrative(
    *,
    scene_setup: dict[str, Any] | None,
    opener: Any | None,
    resolve_opening_text_fn: Callable[[dict[str, Any] | None, Any], str],
    display_char_names: list[str],
    char_names: list[str],
    user_name: str,
    scene_owner: str,
    build_scene_role_prompt_context_fn: Callable[
        [dict[str, Any] | None, list[str] | None], list[dict[str, str]]
    ],
    narrator: Any,
) -> str:
    """Return final opening prose (authored, ``scene_setup.opening_text``, or narrator LLM).

    Streamlit-only: requires a narrator agent when no static opening is available.
    """
    opening = resolve_opening_text_fn(scene_setup, opener)
    if str(opening or "").strip():
        return str(opening).strip()

    from autogen_agentchat.messages import TextMessage
    from autogen_core import CancellationToken

    premise = str(scene_setup.get("premise", "") or "") if scene_setup else ""
    tpl_id = str(scene_setup.get("template_id", "") or "") if scene_setup else ""
    role_map = json.dumps(
        build_scene_role_prompt_context_fn(scene_setup, char_names),
        ensure_ascii=False,
    )
    narrator_prompt = f"""Write an opening scene description.

CHARACTERS PRESENT: {", ".join(display_char_names)}
PLAYER CHARACTER NAME: {user_name}
SCENE OWNER: {scene_owner}
SCENE TEMPLATE ID: {tpl_id}
SCENE TEMPLATE PREMISE: {premise}
SCENE ROLE MAP: {role_map}

Describe the setting, atmosphere, and where each character is positioned. End with a hook that invites the characters to begin interacting. Keep it evocative but concise (3-5 sentences)."""
    cancellation_token = CancellationToken()
    opening_task = TextMessage(content=narrator_prompt, source="user")
    narrator_result = await narrator.on_messages([opening_task], cancellation_token)
    return str(narrator_result.chat_message.content or "").strip()


def headless_prepare_scene_setup_bundle(
    *,
    st_module: Any,
    scene_template_id: str | None,
    scene_template_role_assignments: dict[str, str] | None,
    character_card_ids: list[str],
    resolved_character_files: list[str],
    resolve_scene_template_setup_fn: Callable[[], tuple[Any, str]],
) -> tuple[dict[str, Any] | None, str]:
    """Configure template session keys and resolve ``scene_setup`` for headless (before continuity init).

    When ``scene_template_id`` is set, ``scene_template_role_assignments`` is **required**
    (same contract as scenario manifests — Issue #80). Call ``resolve_scene_template_setup_fn``
    after mutating ``st_module.session_state`` (``selected_scene_template_id``,
    ``scene_role_assignments`` file-keyed).
    """
    tpl = str(scene_template_id or "").strip()
    if not tpl:
        return None, ""
    if not scene_template_role_assignments:
        raise ValueError(
            "headless scene_template_id requires scene_template_role_assignments "
            "(Issue #80); omit scene_template_id or supply card id → role_name map."
        )
    st_module.session_state["selected_scene_template_id"] = tpl
    card_to_file = {
        str(cid).strip(): resolved_character_files[i]
        for i, cid in enumerate(character_card_ids)
    }
    file_roles: dict[str, str] = {}
    for cid, role in scene_template_role_assignments.items():
        ck = str(cid).strip()
        if ck not in card_to_file:
            raise ValueError(
                f"scene_template_role_assignments key {ck!r} is not in character_card_ids"
            )
        file_roles[card_to_file[ck]] = str(role).strip()
    st_module.session_state["scene_role_assignments"] = file_roles
    return resolve_scene_template_setup_fn()


def append_scene_opening_chat_message(
    *,
    st_module: Any,
    opening_final: str,
    user_name: str,
) -> None:
    """Append the Scene Opening row (matches Streamlit ``start_scene`` shape)."""
    hist = st_module.session_state.setdefault("chat_history", [])
    hist.append(
        {
            "role": "system",
            "content": (
                f"**Scene Opening**\n\n{opening_final}\n\n"
                f"**You are playing as**: {user_name}"
            ),
            "speaker": "Narrator",
        }
    )

