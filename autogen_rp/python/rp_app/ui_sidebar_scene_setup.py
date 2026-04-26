import asyncio
from typing import Any, Awaitable, Callable

from bootstrap_composition import (
    STREAMLIT_OPENING_MODE_CUSTOM,
    STREAMLIT_OPENING_MODE_GENERATED,
    STREAMLIT_OPENING_MODE_TEMPLATE,
    migrate_legacy_generated_streamlit_opening_state,
    streamlit_opening_mode_options_for_ui,
)
from ui_sidebar_opening import (
    load_character_names,
    render_opening_controls,
    streamlit_opener_scope_fingerprint,
)


def render_scene_setup_controls(
    *,
    st_module: Any,
    available: list[str],
    character_loader_cls: Any,
    has_player_character_conflict_fn: Callable[[list[str], str | None], bool],
    scene_template_manager_cls: Any,
    opener_manager_cls: Any,
    resolve_character_file_fn: Callable[[Any, str], str | None],
    start_scene_fn: Callable[[list[str]], Awaitable[bool]],
) -> None:
    scene_started = bool(st_module.session_state.get("scene_started", False))

    npc_options = [
        c for c in available if c != st_module.session_state.get("player_character")
    ]

    template_manager = scene_template_manager_cls()
    templates = template_manager.list_templates()
    selected_template: Any | None = None
    selected_template_id: str | None = None
    if templates:
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
                st_module.session_state["opening_mode"] = STREAMLIT_OPENING_MODE_CUSTOM

        if selected_template_id:
            selected_template = next(
                (
                    template
                    for template in templates
                    if template.template_id == selected_template_id
                ),
                None,
            )
    else:
        st_module.session_state["selected_scene_template_id"] = None
        st_module.session_state["scene_role_assignments"] = {}

    st_module.subheader("NPCs in Scene")
    st_module.caption("Select the characters that should respond in this scene")

    if not npc_options:
        st_module.warning("No character files found in data/autogen_characters/")
        st_module.info("Create character JSON files first.")
        return

    default_selected_chars = (
        st_module.session_state.get("selected_chars") if scene_started else None
    )
    if not default_selected_chars:
        # Issue #104: fresh pre-start has no implicit default; no sorted [:2] preselection.
        default_selected_chars = []
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

    if selected_chars:
        char_names = load_character_names(
            selected_chars=selected_chars,
            character_loader_cls=character_loader_cls,
        )
        # Issue #102 / #107: no Scene Owner UI; keep `scene_owner` (normalized session/run
        # owner label) aligned with cast defaults before start—not Streamlit opener scope.
        if not st_module.session_state.get("scene_started", False):
            _cur = st_module.session_state.get("scene_owner")
            if _cur and _cur in char_names:
                st_module.session_state["scene_owner"] = _cur
            else:
                st_module.session_state["scene_owner"] = char_names[0]

    if templates and selected_template_id and selected_template is not None:
        role_options = [""] + [slot.role_name for slot in selected_template.role_slots]
        current_assignments = {
            key: value
            for key, value in st_module.session_state.get(
                "scene_role_assignments", {}
            ).items()
            if key in selected_chars
        }
        for char_file, char_name in zip(selected_chars, char_names, strict=False):
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

    st_module.subheader("Scene Opening")
    if st_module.session_state.get("opening_mode") == STREAMLIT_OPENING_MODE_GENERATED:
        _om = opener_manager_cls()
        _topts: list = (
            _om.get_template_openers(
                str(selected_template_id or "").strip(), template_manager
            )
            if selected_template_id
            else []
        )
        _n_mode, _n_oid = migrate_legacy_generated_streamlit_opening_state(
            opening_mode=STREAMLIT_OPENING_MODE_GENERATED,
            selected_template_id=selected_template_id,
            selected_opener_id=st_module.session_state.get("selected_opener_id"),
            template_openers=_topts,
        )
        st_module.session_state["opening_mode"] = _n_mode
        st_module.session_state["selected_opener_id"] = _n_oid
        st_module.session_state["opener_selection_scope_key"] = (
            streamlit_opener_scope_fingerprint(_n_mode, selected_template_id)
        )
        st_module.info(
            "The **Generated (LLM)** opening option has been removed. Your session was moved to "
            "**Template** or **Custom** opening (see **Opening Mode** above)."
        )
    opening_mode_options = streamlit_opening_mode_options_for_ui(
        with_template=bool(selected_template_id)
    )
    current_opening_mode = st_module.session_state.get("opening_mode", "custom")
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
            else "Custom text"
            if x == STREAMLIT_OPENING_MODE_CUSTOM
            else str(x)
        ),
        key="opening_mode_radio",
    )
    st_module.session_state["opening_mode"] = opening_mode

    render_opening_controls(
        st_module=st_module,
        opening_mode=opening_mode,
        selected_template_id=selected_template_id,
        selected_template=selected_template,
        templates=templates,
        opener_manager_cls=opener_manager_cls,
        template_manager_cls=scene_template_manager_cls,
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
