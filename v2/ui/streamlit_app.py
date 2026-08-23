"""Holy Grail V2 — minimal Streamlit surface (presentation-only consumer)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import streamlit as st

API_BASE = os.environ.get("HG_APP_API_URL", "http://127.0.0.1:8765").rstrip("/")


def api_request(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": body}
        raise RuntimeError(parsed.get("error", parsed)) from exc


def init_state() -> None:
    if "hg_session_id" not in st.session_state:
        st.session_state.hg_session_id = None
    if "transcript" not in st.session_state:
        st.session_state.transcript = []
    if "runtime_status" not in st.session_state:
        st.session_state.runtime_status = "unknown"
    if "character_catalog" not in st.session_state:
        st.session_state.character_catalog = []
    if "template_catalog" not in st.session_state:
        st.session_state.template_catalog = []
    if "setup_provenance" not in st.session_state:
        st.session_state.setup_provenance = None
    if "memory_scope_id" not in st.session_state:
        st.session_state.memory_scope_id = None
    if "template_openers" not in st.session_state:
        st.session_state.template_openers = []
    if "user_persona_id" not in st.session_state:
        st.session_state.user_persona_id = "Player"
    if "player_character_file_id" not in st.session_state:
        st.session_state.player_character_file_id = None
    if "reasoning_effort" not in st.session_state:
        st.session_state.reasoning_effort = "low"
    if "role_routing" not in st.session_state:
        st.session_state.role_routing = "simple"
    if "audit_tags_by_entry" not in st.session_state:
        st.session_state.audit_tags_by_entry = {}


def load_audit_tags() -> None:
    if not st.session_state.hg_session_id:
        st.session_state.audit_tags_by_entry = {}
        return
    try:
        payload = api_request(
            "GET",
            f"/api/sessions/{st.session_state.hg_session_id}/audit-tags",
        )
        tags = payload.get("tags", [])
        st.session_state.audit_tags_by_entry = {
            tag["anchor"]["entry_id"]: tag for tag in tags if tag.get("anchor", {}).get("entry_id")
        }
    except Exception:  # noqa: BLE001
        st.session_state.audit_tags_by_entry = {}


def refresh_status() -> None:
    try:
        status = api_request("GET", "/api/status")
        st.session_state.runtime_status = status.get("health", {}).get(
            "application_status", "ready"
        )
        if status.get("active_session_id"):
            st.session_state.hg_session_id = status["active_session_id"]
        if status.get("transcript"):
            st.session_state.transcript = status["transcript"]
    except Exception as exc:  # noqa: BLE001
        st.session_state.runtime_status = f"unavailable: {exc}"


def load_catalogs() -> None:
    try:
        st.session_state.character_catalog = api_request("GET", "/api/characters").get(
            "characters", []
        )
        st.session_state.template_catalog = api_request("GET", "/api/scene-templates").get(
            "scene_templates", []
        )
    except Exception:  # noqa: BLE001
        pass


def load_runtime_settings() -> None:
    try:
        payload = api_request("GET", "/api/settings/runtime")
        runtime = payload.get("runtime", {})
        if runtime.get("reasoningEffort"):
            st.session_state.reasoning_effort = runtime["reasoningEffort"]
        if runtime.get("roleRouting"):
            st.session_state.role_routing = runtime["roleRouting"]
    except Exception:  # noqa: BLE001
        pass


def save_runtime_settings() -> None:
    api_request(
        "PUT",
        "/api/settings/runtime",
        {
            "reasoningEffort": st.session_state.reasoning_effort,
            "roleRouting": st.session_state.role_routing,
        },
    )


def render_sidebar() -> None:
    st.sidebar.header("Holy Grail V2")
    st.sidebar.caption(f"API: {API_BASE}")

    load_catalogs()
    load_runtime_settings()
    characters = st.session_state.character_catalog
    templates = st.session_state.template_catalog

    if characters:
        labels = {
            item["character_id"]: f"{item['display_name']} ({item['character_id']})"
            for item in characters
        }
        selected_ids = st.sidebar.multiselect(
            "Character cards",
            options=list(labels.keys()),
            format_func=lambda cid: labels[cid],
        )
    else:
        st.sidebar.warning("Character catalog unavailable — using prototype cast.")
        selected_ids = []

    st.sidebar.subheader("Player identity")
    st.session_state.user_persona_id = st.sidebar.text_input(
        "Your display name",
        st.session_state.user_persona_id,
        help="Stable user persona label for transcript and memory attribution.",
    )
    player_options = ["(external user)"] + selected_ids
    player_labels = {
        "(external user)": "External user (not a cast character)",
        **{
            cid: labels[cid] if characters else cid
            for cid in selected_ids
        },
    }
    player_choice = st.sidebar.selectbox(
        "Play as",
        options=player_options,
        format_func=lambda cid: player_labels.get(cid, cid),
        index=0
        if not st.session_state.player_character_file_id
        else (
            player_options.index(st.session_state.player_character_file_id)
            if st.session_state.player_character_file_id in player_options
            else 0
        ),
    )
    st.session_state.player_character_file_id = (
        None if player_choice == "(external user)" else player_choice
    )

    st.sidebar.subheader("Session setup")
    template_id = None
    template_meta = None
    if templates:
        template_labels = {
            item["template_id"]: item["template_id"].replace("_", " ")
            for item in templates
        }
        template_choice = st.sidebar.selectbox(
            "Scene template (optional)",
            options=["(none)"] + list(template_labels.keys()),
            format_func=lambda tid: "No template" if tid == "(none)" else template_labels[tid],
        )
        if template_choice != "(none)":
            template_id = template_choice
            template_meta = next(
                (item for item in templates if item["template_id"] == template_id),
                None,
            )

    role_assignments: dict[str, str] = {}
    if template_id and template_meta:
        st.sidebar.caption("Assign character cards to template roles")
        for slot in template_meta.get("role_slots", []):
            role_name = slot.get("role_name", "")
            if not role_name:
                continue
            role_assignments[role_name] = st.sidebar.selectbox(
                f"Role: {role_name}",
                options=["(unassigned)"] + selected_ids,
                format_func=lambda cid: "Unassigned" if cid == "(unassigned)" else cid,
                key=f"role_{template_id}_{role_name}",
            )

    opener_id = None
    if template_id:
        try:
            opener_payload = api_request(
                "GET", f"/api/scene-templates/{template_id}/openers"
            )
            st.session_state.template_openers = opener_payload.get("openers", [])
        except Exception:  # noqa: BLE001
            st.session_state.template_openers = []
        openers = st.session_state.template_openers
        if openers:
            opener_labels = {
                item["opener_id"]: item.get("label") or item["opener_id"]
                for item in openers
            }
            opener_id = st.sidebar.selectbox(
                "Template opener",
                options=list(opener_labels.keys()),
                format_func=lambda oid: opener_labels[oid],
            )

    opening_mode = st.sidebar.selectbox(
        "Opening",
        options=["minimal", "custom", "template", "generated"],
        help="Minimal uses premise only. Template uses authored opener assets. Generated uses DSH inference.",
    )
    custom_opening = ""
    if opening_mode == "custom":
        custom_opening = st.sidebar.text_area("Custom opening text", height=80)

    memory_scope_input = st.sidebar.text_input(
        "Continuity scope ID (optional)",
        "",
        help="Reuse an existing memory_scope_id for shared world continuity across sessions.",
    )

    st.sidebar.subheader("Model settings")
    st.session_state.reasoning_effort = st.sidebar.selectbox(
        "Reasoning level",
        options=["off", "low", "high", "max"],
        index=["off", "low", "high", "max"].index(st.session_state.reasoning_effort),
        help="Applies to Director and Character inference. Narrator stays off for latency.",
    )
    with st.sidebar.expander("Advanced model routing"):
        st.session_state.role_routing = st.radio(
            "Role routing",
            options=["simple", "advanced"],
            index=0 if st.session_state.role_routing == "simple" else 1,
            help="Simple uses one model for Director/Character. Advanced enables per-role overrides via API.",
        )
    if st.sidebar.button("Apply model settings"):
        try:
            save_runtime_settings()
            st.sidebar.success("Model settings updated for subsequent turns.")
        except Exception as exc:  # noqa: BLE001
            st.sidebar.error(str(exc))

    if st.sidebar.button("Create session"):
        if selected_ids:
            payload: dict = {"characters": selected_ids}
            if template_id:
                payload["scene_template_id"] = template_id
                assignments_by_file = {
                    char_id: role_name
                    for role_name, char_id in role_assignments.items()
                    if char_id and char_id != "(unassigned)"
                }
                if assignments_by_file:
                    payload["role_assignments"] = assignments_by_file
            opening_payload: dict = {"mode": opening_mode}
            if opening_mode == "custom" and custom_opening.strip():
                opening_payload["text"] = custom_opening.strip()
            elif opening_mode == "template":
                if not template_id:
                    st.sidebar.error("Template opening requires a scene template.")
                    return
                if not opener_id:
                    st.sidebar.error("Select a template opener before creating the session.")
                    return
                opening_payload["opener_id"] = opener_id
            payload["opening"] = opening_payload
        else:
            cast_input = st.sidebar.text_input("Prototype cast", "Alice", key="proto_cast")
            payload = {"cast": [name.strip() for name in cast_input.split(",") if name.strip()]}
        if memory_scope_input.strip():
            payload["memory_scope_id"] = memory_scope_input.strip()
        if st.session_state.user_persona_id.strip():
            payload["user_persona_id"] = st.session_state.user_persona_id.strip()
        if st.session_state.player_character_file_id:
            payload["player_character_file_id"] = st.session_state.player_character_file_id

        save_runtime_settings()
        result = api_request("POST", "/api/sessions/create", payload)
        session = result["session"]
        st.session_state.hg_session_id = session["hg_session_id"]
        st.session_state.setup_provenance = session.get("setup_provenance")
        st.session_state.memory_scope_id = session.get("memory_scope_id")
        if st.session_state.setup_provenance:
            st.session_state.user_persona_id = (
                st.session_state.setup_provenance.get("user_persona_id")
                or st.session_state.user_persona_id
            )
            st.session_state.player_character_file_id = (
                st.session_state.setup_provenance.get("player_character_file_id")
            )
        st.session_state.transcript = result.get("transcript", [])
        load_audit_tags()
        st.sidebar.success(f"Created {st.session_state.hg_session_id}")

    resume_id = st.sidebar.text_input("Resume session id", st.session_state.hg_session_id or "")
    if st.sidebar.button("Open session") and resume_id.strip():
        result = api_request("POST", "/api/sessions/open", {"hg_session_id": resume_id.strip()})
        session = result["session"]
        st.session_state.hg_session_id = session["hg_session_id"]
        st.session_state.setup_provenance = session.get("setup_provenance")
        transcript = api_request(
            "GET", f"/api/sessions/{st.session_state.hg_session_id}/transcript"
        )
        st.session_state.transcript = transcript.get("transcript", [])
        load_audit_tags()
        st.sidebar.success(f"Opened {st.session_state.hg_session_id}")

    if st.session_state.setup_provenance or st.session_state.memory_scope_id:
        st.sidebar.subheader("Active session")
        if st.session_state.memory_scope_id:
            st.sidebar.caption(f"Continuity scope: {st.session_state.memory_scope_id}")
        if st.session_state.setup_provenance:
            provenance = st.session_state.setup_provenance
            if provenance.get("player_character_display_name"):
                st.sidebar.caption(
                    f"Player character: {provenance['player_character_display_name']}"
                )
            elif provenance.get("user_persona_id"):
                st.sidebar.caption(f"User persona: {provenance['user_persona_id']}")

    if st.session_state.hg_session_id:
        load_audit_tags()
        tags = list(st.session_state.audit_tags_by_entry.values())
        if tags:
            st.sidebar.subheader("Session tags")
            for tag in sorted(tags, key=lambda item: item.get("tag_index", 0)):
                anchor = tag.get("anchor", {})
                speaker = anchor.get("speaker", "unknown")
                entry_id = anchor.get("entry_id", "")
                comment = tag.get("comment")
                label = f"#{tag.get('tag_index', '?')} {speaker}"
                st.sidebar.caption(label)
                st.sidebar.caption(f"`{entry_id}`")
                if comment:
                    st.sidebar.write(comment)
        try:
            state = api_request("GET", f"/api/sessions/{st.session_state.hg_session_id}/state")
            st.sidebar.json(state.get("state", state))
        except Exception as exc:  # noqa: BLE001
            st.sidebar.warning(str(exc))


def render_entry_tag_controls(entry: dict) -> None:
    entry_id = entry.get("entry_id")
    if not entry_id or not st.session_state.hg_session_id:
        return

    tag = st.session_state.audit_tags_by_entry.get(entry_id)
    control_col, _ = st.columns([1, 5])
    with control_col:
        if tag:
            st.caption("Tagged")
            if st.button("Untag", key=f"untag-{entry_id}", type="secondary"):
                try:
                    api_request(
                        "DELETE",
                        f"/api/audit-tags/{tag['tag_id']}",
                        {"hg_session_id": st.session_state.hg_session_id},
                    )
                    load_audit_tags()
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Untag failed: {exc}")
        elif st.button("Tag", key=f"tag-{entry_id}", type="secondary"):
            try:
                api_request(
                    "POST",
                    "/api/audit-tags",
                    {
                        "hg_session_id": st.session_state.hg_session_id,
                        "entry_id": entry_id,
                        "created_by": {
                            "surface": "streamlit",
                            "persona": st.session_state.user_persona_id,
                        },
                    },
                )
                load_audit_tags()
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Tag failed: {exc}")

    if tag:
        note_key = f"note-{entry_id}"
        current_comment = tag.get("comment") or ""
        with st.expander("Add note", expanded=False):
            note_text = st.text_area(
                "Forensic note (optional)",
                value=current_comment,
                key=note_key,
                height=80,
            )
            if st.button("Save note", key=f"save-note-{entry_id}"):
                try:
                    api_request(
                        "PATCH",
                        f"/api/audit-tags/{tag['tag_id']}",
                        {
                            "hg_session_id": st.session_state.hg_session_id,
                            "comment": note_text.strip() or None,
                        },
                    )
                    load_audit_tags()
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Note save failed: {exc}")


def render_chat() -> None:
    st.title("Holy Grail V2")
    st.caption(f"Runtime: {st.session_state.runtime_status}")

    if st.session_state.hg_session_id:
        load_audit_tags()

    for entry in st.session_state.transcript:
        speaker = entry.get("speaker") or entry.get("role", "unknown")
        if entry.get("player_skip"):
            with st.chat_message("assistant"):
                st.caption(f"**{speaker}** — {entry.get('content', 'Turn skipped')}")
                render_entry_tag_controls(entry)
            continue
        with st.chat_message("user" if entry.get("role") == "user" else "assistant"):
            st.markdown(f"**{speaker}:** {entry.get('content', '')}")
            render_entry_tag_controls(entry)

    if not st.session_state.hg_session_id:
        st.info("Create or open a durable HG session to begin.")
        return

    round_busy = st.session_state.runtime_status == "round_in_progress"
    if st.button("Skip turn", disabled=round_busy, type="secondary"):
        try:
            result = api_request(
                "POST",
                "/api/turns/skip",
                {"userName": st.session_state.user_persona_id},
            )
            st.session_state.transcript = result.get("transcript", st.session_state.transcript)
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Skip turn failed: {exc}")

    prompt = st.chat_input("Your message", disabled=round_busy)
    if not prompt:
        return

    try:
        result = api_request(
            "POST",
            "/api/turns/submit",
            {
                "userMessage": prompt,
                "userName": st.session_state.user_persona_id,
            },
        )
        st.session_state.transcript = result.get("transcript", st.session_state.transcript)
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Turn failed: {exc}")


def main() -> None:
    st.set_page_config(page_title="Holy Grail V2", page_icon="⚔️", layout="wide")
    init_state()
    refresh_status()
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
