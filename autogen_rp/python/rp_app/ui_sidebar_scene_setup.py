import asyncio
from typing import Any, Awaitable, Callable

from app_state_session import get_bot_reply_limit_widget_key
from bootstrap_composition import (
    STREAMLIT_OPENING_MODE_CHARACTER,
    STREAMLIT_OPENING_MODE_GENERATED,
    STREAMLIT_OPENING_MODE_CUSTOM,
    STREAMLIT_OPENING_MODE_TEMPLATE,
    streamlit_opening_mode_options_for_ui,
)
from ui_runtime_status import runtime_evaluation_status_markdown
from ui_sidebar_opening import load_character_names, render_opening_controls


def render_scene_setup_controls(
    *,
    st_module: Any,
    available: list[str],
    character_loader_cls: Any,
    has_player_character_conflict_fn: Callable[[list[str], str | None], bool],
    resolve_bot_reply_limit_fn: Callable[[int, int | None], int],
    scene_template_manager_cls: Any,
    opener_manager_cls: Any,
    resolve_character_file_fn: Callable[[Any, str], str | None],
    start_scene_fn: Callable[[list[str]], Awaitable[bool]],
) -> None:
    st_module.subheader("Runtime / Evaluation Status")
    st_module.caption(
        "Read-only. Uses the same rules as the runtime: `get_index_path_from_env()`, "
        "`is_episodic_memory_enabled()`, and your choices below. "
        "Restart the Streamlit app if you change environment variables outside the app."
    )
    st_module.markdown(runtime_evaluation_status_markdown(st_module=st_module))

    st_module.divider()

    st_module.subheader("NPCs in Scene")
    st_module.caption("Select the characters that should respond in this scene")

    scene_started = bool(st_module.session_state.get("scene_started", False))

    npc_options = [
        c for c in available if c != st_module.session_state.get("player_character")
    ]

    if not npc_options:
        st_module.warning("No character files found in data/autogen_characters/")
        st_module.info("Create character JSON files first.")
        return

    default_selected_chars = (
        st_module.session_state.get("selected_chars") if scene_started else None
    )
    if not default_selected_chars:
        default_selected_chars = (
            npc_options[:2] if len(npc_options) >= 2 else npc_options
        )
    default_selected_chars = [c for c in default_selected_chars if c in npc_options]

    selected_chars = st_module.multiselect(
        "Select characters",
        options=npc_options,
        default=default_selected_chars,
        key="npc_selection",
        disabled=scene_started,
    )
    char_names: list[str] = []

    if has_player_character_conflict_fn(
        selected_chars, st_module.session_state.get("player_character")
    ):
        st_module.error(
            "The character you are playing cannot also be selected as a bot in this scene."
        )

    configured_bot_count = len(selected_chars) or len(
        st_module.session_state.get("characters", [])
    )
    if (
        configured_bot_count > 0
        and st_module.session_state.get("bot_reply_limit") is None
    ):
        st_module.session_state["bot_reply_limit"] = resolve_bot_reply_limit_fn(
            configured_bot_count,
            configured_bot_count,
        )

    if configured_bot_count > 0:
        st_module.subheader("Bot Replies Per Round")
        st_module.caption(
            "Hard ceiling on how many NPC turns run after each user message."
        )

        configured_limit = st_module.session_state.get("bot_reply_limit")
        if isinstance(configured_limit, int):
            default_limit = resolve_bot_reply_limit_fn(
                configured_bot_count,
                configured_limit,
            )
        else:
            default_limit = configured_bot_count

        st_module.number_input(
            "Max replies",
            min_value=1,
            max_value=configured_bot_count,
            value=int(default_limit),
            step=1,
            key=get_bot_reply_limit_widget_key(st_module=st_module),
        )

    if selected_chars:
        st_module.subheader("Scene Owner")
        st_module.caption("Which character owns this scene?")
        char_names = load_character_names(
            selected_chars=selected_chars,
            character_loader_cls=character_loader_cls,
        )

        if st_module.session_state.get("scene_started", False):
            current_owner = (
                st_module.session_state.get("audit_session_owner")
                or st_module.session_state.get("scene_owner")
                or char_names[0]
            )
            st_module.selectbox(
                "Scene Owner",
                options=char_names,
                index=(
                    char_names.index(current_owner)
                    if current_owner in char_names
                    else 0
                ),
                key="scene_owner_display",
                disabled=True,
            )
        else:
            initial_owner = st_module.session_state.get("scene_owner") or char_names[0]
            initial_index = (
                char_names.index(initial_owner) if initial_owner in char_names else 0
            )

            selected_owner = st_module.selectbox(
                "Scene Owner",
                options=char_names,
                index=initial_index,
                key="scene_owner_select",
            )
            st_module.session_state["scene_owner"] = selected_owner

    template_manager = scene_template_manager_cls()
    templates = template_manager.list_templates()
    selected_template = None
    selected_template_id = None
    if templates:
        st_module.subheader("Scene Template")
        st_module.caption(
            "Sets the continuity template id, role slots, and opener path. When authored retrieval is ON "
            "(env `RP_RETRIEVED_CONTEXT_INDEX`), it also selects **template-scoped** index rows "
            "(`role_slots`, `premise`) for matching templates. "
            "“(legacy opener flow)” means **no** template id — template lane retrieval does not apply."
        )
        template_options = ["(legacy opener flow)"] + [
            template.template_id for template in templates
        ]
        current_template_id = st_module.session_state.get("selected_scene_template_id")
        selected_template_option = (
            current_template_id
            if current_template_id in template_options
            else "(legacy opener flow)"
        )
        selected_template_id = st_module.selectbox(
            "Scene Template",
            options=template_options,
            index=template_options.index(selected_template_option),
            key="scene_template_select",
            disabled=st_module.session_state.get("scene_started", False),
        )
        selected_template_id = (
            None
            if selected_template_id == "(legacy opener flow)"
            else selected_template_id
        )
        template_selection_changed = selected_template_id != current_template_id
        st_module.session_state["selected_scene_template_id"] = selected_template_id

        if template_selection_changed:
            if selected_template_id:
                st_module.session_state["opening_mode"] = STREAMLIT_OPENING_MODE_TEMPLATE
            elif st_module.session_state.get("opening_mode") == STREAMLIT_OPENING_MODE_TEMPLATE:
                st_module.session_state["opening_mode"] = STREAMLIT_OPENING_MODE_CHARACTER

        if selected_template_id:
            selected_template = next(
                (
                    template
                    for template in templates
                    if template.template_id == selected_template_id
                ),
                None,
            )
            if selected_template is not None:
                role_options = [""] + [
                    slot.role_name for slot in selected_template.role_slots
                ]
                current_assignments = {
                    key: value
                    for key, value in st_module.session_state.get(
                        "scene_role_assignments", {}
                    ).items()
                    if key in selected_chars
                }
                for char_file, char_name in zip(
                    selected_chars, char_names, strict=False
                ):
                    selected_role = st_module.selectbox(
                        f"Role for {char_name}",
                        options=role_options,
                        index=(
                            role_options.index(current_assignments.get(char_file, ""))
                            if current_assignments.get(char_file, "") in role_options
                            else 0
                        ),
                        key=f"scene_role_assignment_{char_file}",
                        disabled=st_module.session_state.get("scene_started", False),
                    )
                    if selected_role:
                        current_assignments[char_file] = selected_role
                    else:
                        current_assignments.pop(char_file, None)
                st_module.session_state["scene_role_assignments"] = current_assignments
    else:
        st_module.session_state["selected_scene_template_id"] = None
        st_module.session_state["scene_role_assignments"] = {}

    st_module.subheader("Scene Opening")
    opening_mode_options = streamlit_opening_mode_options_for_ui(
        with_template=bool(selected_template_id)
    )
    current_opening_mode = st_module.session_state.get("opening_mode", "character")
    opening_mode_index = (
        opening_mode_options.index(current_opening_mode)
        if current_opening_mode in opening_mode_options
        else 0
    )
    opening_mode = st_module.radio(
        "Opening Mode",
        options=opening_mode_options,
        index=opening_mode_index,
        format_func=lambda x: (
            "Template opening (JSON)"
            if x == STREAMLIT_OPENING_MODE_TEMPLATE
            else "Character opener (JSON)"
            if x == STREAMLIT_OPENING_MODE_CHARACTER
            else "Custom text"
            if x == STREAMLIT_OPENING_MODE_CUSTOM
            else "Generated (LLM)"
            if x == STREAMLIT_OPENING_MODE_GENERATED
            else str(x)
        ),
        key="opening_mode_radio",
    )
    st_module.session_state["opening_mode"] = opening_mode

    if selected_template_id and opening_mode == STREAMLIT_OPENING_MODE_CHARACTER:
        st_module.info(
            "You have a Scene Template selected, but Opening Mode is set to Character Opener. "
            "In this mode, the app only looks for <character>_initial_message.json in data/autogen_characters/. "
            "Switch Opening Mode to Template Opening to use the template-authored opener."
        )

    render_opening_controls(
        st_module=st_module,
        opening_mode=opening_mode,
        selected_template_id=selected_template_id,
        selected_template=selected_template,
        templates=templates,
        selected_chars=selected_chars,
        opener_manager_cls=opener_manager_cls,
        character_loader_cls=character_loader_cls,
        template_manager_cls=scene_template_manager_cls,
        resolve_character_file_fn=resolve_character_file_fn,
    )

    st_module.subheader("Audit Logging")
    if st_module.session_state.get("scene_started", False):
        audit_enabled = bool(st_module.session_state.get("audit_enabled", False))
        st_module.toggle(
            "Enable audit logging for this scene",
            value=audit_enabled,
            key="audit_enabled_display",
            disabled=True,
        )
    else:
        audit_enabled = st_module.toggle(
            "Enable audit logging for this scene",
            value=st_module.session_state.get("audit_enabled", False),
            key="audit_enabled_toggle",
            disabled=False,
        )
        st_module.session_state["audit_enabled"] = audit_enabled
    if audit_enabled:
        st_module.caption(
            "Writes full, light, and summary audit artifacts. Character turns may include "
            "**metadata.retrieval_summary** (counts/refs only) when authored retrieval produced a bundle. "
            "Run-level **retrieval_session** is merged into `_audit_summary.json` on each summary refresh "
            "(same behavior as headless simulation). "
            "**structured_eval** metrics files and strict retrieval verification remain simulation/CLI-only."
        )
    else:
        st_module.caption(
            "No audit files for this scene unless you enable the toggle above before **Start Scene**. "
            "Audit is **locked at scene start**."
        )

    if selected_chars and st_module.button("Start Scene", type="primary"):
        st_module.session_state["selected_chars"] = selected_chars
        if st_module.session_state.get("player_character") is None:
            st_module.session_state["user_name"] = st_module.session_state.get(
                "user_name_input", "Traveler"
            )
        scene_started = asyncio.run(start_scene_fn(selected_chars))
        if scene_started:
            st_module.rerun()
