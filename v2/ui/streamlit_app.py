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


def render_sidebar() -> None:
    st.sidebar.header("Holy Grail V2")
    st.sidebar.caption(f"API: {API_BASE}")

    load_catalogs()
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

    template_id = None
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

    opening_mode = st.sidebar.selectbox(
        "Opening",
        options=["minimal", "custom"],
        help="Template opener assets can be added in a follow-up slice.",
    )
    custom_opening = ""
    if opening_mode == "custom":
        custom_opening = st.sidebar.text_area("Custom opening text", height=80)

    memory_scope_input = st.sidebar.text_input(
        "Memory scope (optional — leave blank for new isolated scope)",
        "",
        help="Reuse an existing memory_scope_id to share cross-session relationship memory.",
    )

    if st.sidebar.button("Create session"):
        if selected_ids:
            payload: dict = {"characters": selected_ids}
            if template_id:
                payload["scene_template_id"] = template_id
            if opening_mode == "custom" and custom_opening.strip():
                payload["opening"] = {"mode": "custom", "text": custom_opening.strip()}
            else:
                payload["opening"] = {"mode": "minimal"}
        else:
            cast_input = st.sidebar.text_input("Prototype cast", "Alice", key="proto_cast")
            payload = {"cast": [name.strip() for name in cast_input.split(",") if name.strip()]}
        if memory_scope_input.strip():
            payload["memory_scope_id"] = memory_scope_input.strip()

        result = api_request("POST", "/api/sessions/create", payload)
        session = result["session"]
        st.session_state.hg_session_id = session["hg_session_id"]
        st.session_state.setup_provenance = session.get("setup_provenance")
        st.session_state.memory_scope_id = session.get("memory_scope_id")
        st.session_state.transcript = []
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
        st.sidebar.success(f"Opened {st.session_state.hg_session_id}")

    if st.session_state.setup_provenance or st.session_state.memory_scope_id:
        st.sidebar.subheader("Session setup")
        if st.session_state.memory_scope_id:
            st.sidebar.caption(f"memory_scope_id: {st.session_state.memory_scope_id}")
        if st.session_state.setup_provenance:
            st.sidebar.json(st.session_state.setup_provenance)

    if st.session_state.hg_session_id:
        try:
            state = api_request("GET", f"/api/sessions/{st.session_state.hg_session_id}/state")
            st.sidebar.json(state.get("state", state))
        except Exception as exc:  # noqa: BLE001
            st.sidebar.warning(str(exc))


def render_chat() -> None:
    st.title("Holy Grail V2")
    st.caption(f"Runtime: {st.session_state.runtime_status}")

    for entry in st.session_state.transcript:
        speaker = entry.get("speaker") or entry.get("role", "unknown")
        with st.chat_message("user" if entry.get("role") == "user" else "assistant"):
            st.markdown(f"**{speaker}:** {entry.get('content', '')}")

    if not st.session_state.hg_session_id:
        st.info("Create or open a durable HG session to begin.")
        return

    prompt = st.chat_input("Your message")
    if not prompt:
        return

    try:
        result = api_request("POST", "/api/turns/submit", {"userMessage": prompt})
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
