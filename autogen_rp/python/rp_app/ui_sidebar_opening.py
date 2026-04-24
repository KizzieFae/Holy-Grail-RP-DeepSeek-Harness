from typing import Any, Callable

from bootstrap_composition import (
    STREAMLIT_OPENING_MODE_CHARACTER,
    STREAMLIT_OPENING_MODE_CUSTOM,
    STREAMLIT_OPENING_MODE_GENERATED,
    STREAMLIT_OPENING_MODE_TEMPLATE,
)


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
            "Opening mode chooses **prose source** for scene start. The **template id** still applies to "
            "continuity roles and, when authored retrieval is ON, template-scoped retrieval rows. "
            "It does not inject template `opening_text` on Start Scene (use an opener, Custom, or Generated)."
        )
    if opening_mode == STREAMLIT_OPENING_MODE_TEMPLATE and selected_template_id:
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
                    "No template opener JSON files were found. Add `*_opener_*.json` for this template, "
                    "or choose **Custom text** or **Generated (LLM)**. The card `opening_text` is not used "
                    "on Start Scene in this app path (only opener assets or explicit Custom/Generated apply)."
                )
                with st_module.expander("Template card `opening_text` (reference only, not used on Start)"):
                    st_module.text(selected_template.opening_text)
    elif opening_mode == STREAMLIT_OPENING_MODE_CHARACTER and selected_chars:
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
                    "No character opener JSON for this role. Add `*_initial_message.json`, switch to **Generated (LLM)**, "
                    "or use **Custom text** — the app does not fall back to template `opening_text` or auto-generate."
                )
                st_module.session_state["selected_opener_id"] = None

    elif opening_mode == STREAMLIT_OPENING_MODE_CUSTOM:
        st_module.session_state["selected_opener_id"] = None
        custom_text = st_module.text_area(
            "Custom Opening Text",
            value=st_module.session_state.get("custom_opener_text", ""),
            placeholder="Type your scene opening here...",
            height=120,
            key="custom_opener_input",
        )
        st_module.session_state["custom_opener_text"] = custom_text
    elif opening_mode == STREAMLIT_OPENING_MODE_GENERATED:
        st_module.session_state["selected_opener_id"] = None
        st_module.caption(
            "**Generated (LLM):** the narrator fabricates a first-paragraph opening from the template/cast. "
            "This is the explicit generated mode — it does not use character or template JSON openers, "
            "Custom text, or template `opening_text`."
        )
