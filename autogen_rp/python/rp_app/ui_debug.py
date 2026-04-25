from typing import Any

from ui_runtime_status import runtime_evaluation_status_markdown


def render_debug_panel(*, st_module: Any) -> None:
    st_module.subheader("Debug Panel")
    debug_mode = st_module.toggle(
        "Enable Debug Mode", value=st_module.session_state.get("debug_mode", False)
    )
    st_module.session_state["debug_mode"] = debug_mode

    if debug_mode:
        st_module.caption("Debug information for troubleshooting")

        st_module.markdown("**Runtime / evaluation (read-only):**")
        st_module.markdown(runtime_evaluation_status_markdown(st_module=st_module))
        st_module.divider()

        selector_decisions = st_module.session_state.get("selector_decisions", [])
        st_module.markdown("**Selector Decisions:**")
        if selector_decisions:
            for decision in selector_decisions[-5:]:
                st_module.text(f"• {decision}")
        else:
            st_module.info(
                "No selector decisions recorded yet. Decisions are logged when the selector picks the next speaker."
            )

        st_module.divider()

        rejected = st_module.session_state.get("rejected_messages", [])
        st_module.markdown("**Rejected Messages:**")
        if rejected:
            st_module.warning(f"{len(rejected)} message(s) rejected")
            for rejected_message in rejected[-3:]:
                st_module.error(
                    f"{rejected_message['speaker']}: {rejected_message['reason']}"
                )
                st_module.caption(f"Content: {rejected_message['content'][:100]}...")
        else:
            st_module.success(
                "No messages rejected. Quality controls are active but no issues detected."
            )

        st_module.divider()

        st_module.markdown("**Active Quality Controls:**")
        st_module.text("✓ User speech detection (characters cannot speak for player)")
        st_module.text("✓ Duplicate content detection (repeats are filtered)")
        st_module.text("✓ Selector logging (who speaks when)")

        if st_module.button("Clear Debug Data"):
            st_module.session_state["selector_decisions"] = []
            st_module.session_state["rejected_messages"] = []
            st_module.rerun()
