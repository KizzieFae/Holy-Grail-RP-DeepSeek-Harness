from typing import Any, Sequence

from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage


def create_selector_func(
    *,
    st_module: Any,
    participant_names: list[str],
    detect_forced_speaker_fn,
    get_character_display_name_fn,
):
    def selector_func(
        messages: Sequence[BaseAgentEvent | BaseChatMessage],
    ) -> str | None:
        if not messages:
            return None

        pending_forced_speaker = st_module.session_state.get("pending_forced_speaker")
        if (
            pending_forced_speaker in participant_names
            and not st_module.session_state.get("forced_speaker_consumed", False)
        ):
            st_module.session_state["forced_speaker_consumed"] = True
            st_module.session_state["selector_decisions"].append(
                f"Forced speaker selected: {pending_forced_speaker}"
            )
            return pending_forced_speaker

        last_msg = messages[-1]
        content = str(getattr(last_msg, "content", "") or "")
        if not content:
            return None

        participant_sources = set(participant_names)
        last_source = getattr(last_msg, "source", None)

        previous_participant_speaker = next(
            (
                getattr(message, "source", None)
                for message in reversed(messages[:-1])
                if getattr(message, "source", None) in participant_sources
            ),
            None,
        )

        if last_source not in participant_sources:
            selected_speaker = detect_forced_speaker_fn(
                content,
                participant_names,
                previous_participant_speaker,
                resolve_display_name=get_character_display_name_fn,
            )
            if selected_speaker is not None:
                st_module.session_state["selector_decisions"].append(
                    f"User/non-participant message routed to: {selected_speaker}"
                )
            return selected_speaker

        if len(participant_names) == 2:
            for name in participant_names:
                if name != last_source:
                    st_module.session_state["selector_decisions"].append(
                        f"Alternating from {last_source} to {name}"
                    )
                    return name

        return None

    return selector_func


def choose_fallback_actor(
    *,
    available_actors: list[str],
    forced_speaker: str | None,
    spotlight_history: list[str],
    choose_fallback_actor_impl_fn,
) -> str | None:
    return choose_fallback_actor_impl_fn(
        available_actors,
        forced_speaker,
        spotlight_history,
    )
