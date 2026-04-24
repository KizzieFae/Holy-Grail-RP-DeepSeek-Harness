from typing import Any, Callable

from bootstrap_composition import (
    STREAMLIT_OPENING_MODE_CHARACTER,
    STREAMLIT_OPENING_MODE_CUSTOM,
    STREAMLIT_OPENING_MODE_GENERATED,
    STREAMLIT_OPENING_MODE_TEMPLATE,
)

# Multi-opener: explicit choice required — no implicit first option (Issue #101).
_OPENER_SELECT_PLACEHOLDER = "— Select an opener —"


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


def _resolve_owner_file_for_opening(
    *,
    st_module: Any,
    selected_chars: list[str],
    character_loader_cls: Any,
    resolve_character_file_fn: Callable[[Any, str], str | None],
) -> str | None:
    if not selected_chars:
        return None
    loader = character_loader_cls()
    owner_file = resolve_character_file_fn(
        loader, st_module.session_state.get("scene_owner", "")
    )
    if owner_file and owner_file not in selected_chars:
        return None
    return owner_file


def _opening_scope_fingerprint(
    opening_mode: str,
    selected_template_id: str | None,
    owner_file: str | None,
) -> str:
    if opening_mode == STREAMLIT_OPENING_MODE_TEMPLATE:
        return f"{opening_mode}|{selected_template_id or ''}|"
    if opening_mode == STREAMLIT_OPENING_MODE_CHARACTER:
        return f"{opening_mode}||{owner_file or ''}"
    return f"{opening_mode}||"


def _sync_opener_scope_session_state(
    *,
    st_module: Any,
    opening_mode: str,
    selected_template_id: str | None,
    selected_chars: list[str],
    character_loader_cls: Any,
    resolve_character_file_fn: Callable[[Any, str], str | None],
) -> None:
    """Clear stale selected_opener_id when template/mode/owner scope changes."""
    owner_for_scope: str | None = None
    if opening_mode == STREAMLIT_OPENING_MODE_CHARACTER and selected_chars:
        owner_for_scope = _resolve_owner_file_for_opening(
            st_module=st_module,
            selected_chars=selected_chars,
            character_loader_cls=character_loader_cls,
            resolve_character_file_fn=resolve_character_file_fn,
        )
    fp = _opening_scope_fingerprint(
        opening_mode,
        selected_template_id if opening_mode == STREAMLIT_OPENING_MODE_TEMPLATE else None,
        owner_for_scope if opening_mode == STREAMLIT_OPENING_MODE_CHARACTER else None,
    )
    if st_module.session_state.get("opener_selection_scope_key") != fp:
        st_module.session_state["opener_selection_scope_key"] = fp
        st_module.session_state["selected_opener_id"] = None


def _selection_resolves_for_multi_opener_list(
    openers: list[Any], selected_opener_id: str | None
) -> bool:
    """True if selection is sufficient for multi-opener scope (matches bootstrap intent)."""
    if len(openers) <= 1:
        return True
    s = (selected_opener_id or "").strip()
    if not s:
        return False
    by_id = [o for o in openers if o.id == s]
    if len(by_id) == 1:
        return True
    by_label = [o for o in openers if o.label == s]
    return len(by_label) == 1


def streamlit_opener_selection_error(
    *,
    opening_mode: str,
    selected_opener_id: str | None,
    scene_setup: dict[str, Any] | None,
    selected_chars: list[str],
    scene_owner: str,
    opener_manager: Any,
    character_loader_cls: Any,
    resolve_character_file_fn: Callable[[Any, str], str | None],
) -> str | None:
    """Return user-facing error if multi-opener scope has no valid pick; else None."""
    if opening_mode in (
        STREAMLIT_OPENING_MODE_CUSTOM,
        STREAMLIT_OPENING_MODE_GENERATED,
    ):
        return None
    if opening_mode == STREAMLIT_OPENING_MODE_TEMPLATE:
        tid = (
            str(scene_setup.get("template_id") or "").strip()
            if scene_setup
            else ""
        )
        if not tid:
            return None
        openers = opener_manager.get_template_openers(tid)
        if len(openers) <= 1:
            return None
        if _selection_resolves_for_multi_opener_list(openers, selected_opener_id):
            return None
        return (
            "Select a template opening before starting the scene "
            "(multiple openers are available)."
        )
    if opening_mode == STREAMLIT_OPENING_MODE_CHARACTER:
        loader = character_loader_cls()
        owner_file = resolve_character_file_fn(loader, scene_owner)
        if not owner_file or owner_file not in selected_chars:
            return None
        openers = opener_manager.get_character_openers(owner_file)
        if len(openers) <= 1:
            return None
        if _selection_resolves_for_multi_opener_list(openers, selected_opener_id):
            return None
        return (
            "Select a character opener before starting the scene "
            "(multiple openers are available)."
        )
    return None


def _opener_display_row_label(op: Any) -> str:
    return f"{op.label} ({op.id})"


def _render_opener_helper_captions(st_module: Any, opener: Any) -> None:
    """Primary = label + id; secondary = description only when present (passthrough)."""
    st_module.caption(f"**{_opener_display_row_label(opener)}**")
    desc = getattr(opener, "description", None)
    if isinstance(desc, str) and desc.strip():
        st_module.caption(desc.strip())


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
    _sync_opener_scope_session_state(
        st_module=st_module,
        opening_mode=opening_mode,
        selected_template_id=selected_template_id,
        selected_chars=selected_chars,
        character_loader_cls=character_loader_cls,
        resolve_character_file_fn=resolve_character_file_fn,
    )

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
            if len(template_openers) == 1:
                only = template_openers[0]
                st_module.session_state["selected_opener_id"] = only.id
                _render_opener_helper_captions(st_module, only)
                with st_module.expander("Preview Template Opening"):
                    st_module.text(only.text)
            else:
                display_keys = [_OPENER_SELECT_PLACEHOLDER] + [
                    _opener_display_row_label(op) for op in template_openers
                ]
                label_to_op = {
                    _opener_display_row_label(op): op for op in template_openers
                }
                cur = st_module.session_state.get("selected_opener_id")
                valid_ids = {op.id for op in template_openers}
                valid_labels = {op.label for op in template_openers}
                resolved = None
                if cur in valid_ids:
                    resolved = next(o for o in template_openers if o.id == cur)
                elif cur in valid_labels:
                    by_l = [o for o in template_openers if o.label == cur]
                    resolved = by_l[0] if len(by_l) == 1 else None

                if resolved is not None:
                    default_key = _opener_display_row_label(resolved)
                    idx = (
                        display_keys.index(default_key)
                        if default_key in display_keys
                        else 0
                    )
                else:
                    idx = 0

                pick = st_module.selectbox(
                    "Select Template Opening",
                    options=display_keys,
                    index=idx,
                    key="template_opener_select",
                )
                if pick == _OPENER_SELECT_PLACEHOLDER:
                    st_module.session_state["selected_opener_id"] = None
                    st_module.warning(
                        "Choose an opener above before **Start Scene** when multiple template openers exist."
                    )
                else:
                    op_picked = label_to_op[pick]
                    st_module.session_state["selected_opener_id"] = op_picked.id
                    _render_opener_helper_captions(st_module, op_picked)
                    with st_module.expander("Preview Template Opening"):
                        st_module.text(op_picked.text)
        else:
            st_module.session_state["selected_opener_id"] = None
            if selected_template is not None and selected_template.opening_text:
                st_module.info(
                    "No template opener JSON was found for this template. Add entries under "
                    "`initial_messages` in the scene template JSON and/or add "
                    "`{template_id}_initial_message.json` under `data/scene_templates/`, "
                    "or choose **Custom text** or **Generated (LLM)**. "
                    "Template card `opening_text` is not used on Start Scene for this path."
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
                if len(openers) == 1:
                    only = openers[0]
                    st_module.session_state["selected_opener_id"] = only.id
                    _render_opener_helper_captions(st_module, only)
                    with st_module.expander("Preview Opener"):
                        st_module.text(only.text)
                else:
                    display_keys = [_OPENER_SELECT_PLACEHOLDER] + [
                        _opener_display_row_label(op) for op in openers
                    ]
                    label_to_op = {
                        _opener_display_row_label(op): op for op in openers
                    }
                    cur = st_module.session_state.get("selected_opener_id")
                    valid_ids = {op.id for op in openers}
                    valid_labels = {op.label for op in openers}
                    resolved = None
                    if cur in valid_ids:
                        resolved = next(o for o in openers if o.id == cur)
                    elif cur in valid_labels:
                        by_l = [o for o in openers if o.label == cur]
                        resolved = by_l[0] if len(by_l) == 1 else None

                    if resolved is not None:
                        default_key = _opener_display_row_label(resolved)
                        idx = (
                            display_keys.index(default_key)
                            if default_key in display_keys
                            else 0
                        )
                    else:
                        idx = 0

                    pick = st_module.selectbox(
                        "Select Opener",
                        options=display_keys,
                        index=idx,
                        key="opener_select",
                    )
                    if pick == _OPENER_SELECT_PLACEHOLDER:
                        st_module.session_state["selected_opener_id"] = None
                        st_module.warning(
                            "Choose an opener above before **Start Scene** when multiple character openers exist."
                        )
                    else:
                        op_picked = label_to_op[pick]
                        st_module.session_state["selected_opener_id"] = op_picked.id
                        _render_opener_helper_captions(st_module, op_picked)
                        with st_module.expander("Preview Opener"):
                            st_module.text(op_picked.text)
            else:
                st_module.info(
                    "No character opener JSON for this role. Add `<name>_initial_message.json` in "
                    "`data/autogen_characters/`, switch to **Generated (LLM)**, "
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
