from typing import Any, Callable


def load_character_names(
    *, selected_chars: list[str], character_loader_cls: Any
) -> list[str]:
    char_names: list[str] = []
    for char_file in selected_chars:
        try:
            loader = character_loader_cls()
            card = loader.load_character_card(char_file)
            char_names.append(card.get("name", char_file))
        except Exception:
            char_names.append(char_file)
    return char_names


def render_opening_controls(
    *,
    st_module: Any,
    opening_mode: str,
    selected_template_id: str | None,
    selected_template: Any,
    templates: list[Any],
    selected_chars: list[str],
    opener_manager_cls: Any,
    character_loader_cls: Any,
    template_manager_cls: Any,
    resolve_character_file_fn: Callable[[Any, str], str | None],
) -> None:
    if selected_template_id:
        st_module.caption(
            "Opening mode chooses **prose source** only. The **template id** above still applies to "
            "continuity roles and, when authored retrieval is ON, template-scoped retrieval rows."
        )
    if opening_mode == "template" and selected_template_id:
        if selected_template is None:
            selected_template = next(
                (
                    template
                    for template in templates
                    if template.template_id == selected_template_id
                ),
                None,
            )
        opener_manager = opener_manager_cls()
        template_manager = template_manager_cls()
        template_openers = opener_manager.get_template_openers(
            selected_template_id, template_manager
        )
        if template_openers:
            opener_options = {f"{op.label} ({op.id})": op.id for op in template_openers}
            current_template_opener_id = st_module.session_state.get(
                "selected_opener_id"
            )
            template_opener_values = list(opener_options.values())
            selected_template_opener_index = (
                template_opener_values.index(current_template_opener_id)
                if current_template_opener_id in template_opener_values
                else 0
            )
            selected_template_opener = st_module.selectbox(
                "Select Template Opening",
                options=list(opener_options.keys()),
                index=selected_template_opener_index,
                key="template_opener_select",
            )
            st_module.session_state["selected_opener_id"] = opener_options[
                selected_template_opener
            ]
            selected_template_opener_obj = next(
                (
                    op
                    for op in template_openers
                    if op.id == opener_options[selected_template_opener]
                ),
                None,
            )
            if selected_template_opener_obj is not None:
                with st_module.expander("Preview Template Opening"):
                    st_module.text(selected_template_opener_obj.text)
        else:
            st_module.session_state["selected_opener_id"] = None
            if selected_template is not None and selected_template.opening_text:
                st_module.info(
                    "No authored template opener files were found for this Scene Template. "
                    "The app will use the template's built-in opening_text."
                )
                with st_module.expander("Preview Template Opening"):
                    st_module.text(selected_template.opening_text)
    elif opening_mode == "character" and selected_chars:
        opener_manager = opener_manager_cls()
        loader = character_loader_cls()
        owner_file = resolve_character_file_fn(
            loader, st_module.session_state.get("scene_owner", "")
        )
        if owner_file not in selected_chars:
            owner_file = None

        if owner_file:
            openers = opener_manager.get_character_openers(owner_file)
            if openers:
                opener_options = {f"{op.label} ({op.id})": op.id for op in openers}
                current_character_opener_id = st_module.session_state.get(
                    "selected_opener_id"
                )
                opener_values = list(opener_options.values())
                selected_character_opener_index = (
                    opener_values.index(current_character_opener_id)
                    if current_character_opener_id in opener_values
                    else 0
                )
                selected_opener = st_module.selectbox(
                    "Select Opener",
                    options=list(opener_options.keys()),
                    index=selected_character_opener_index,
                    key="opener_select",
                )
                st_module.session_state["selected_opener_id"] = opener_options[
                    selected_opener
                ]

                selected_opener_obj = next(
                    (op for op in openers if op.id == opener_options[selected_opener]),
                    None,
                )
                if selected_opener_obj:
                    with st_module.expander("Preview Opener"):
                        st_module.text(selected_opener_obj.text)
            else:
                st_module.info(
                    "No authored openers found for this character. Will use narrator generation."
                )
                st_module.session_state["selected_opener_id"] = None

    elif opening_mode == "custom":
        st_module.session_state["selected_opener_id"] = None
        custom_text = st_module.text_area(
            "Custom Opening Text",
            value=st_module.session_state.get("custom_opener_text", ""),
            placeholder="Type your scene opening here...",
            height=120,
            key="custom_opener_input",
        )
        st_module.session_state["custom_opener_text"] = custom_text
