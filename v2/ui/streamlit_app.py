"""Holy Grail V2 — minimal Streamlit surface (presentation-only consumer)."""

from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request
import uuid

import streamlit as st

API_BASE = os.environ.get("HG_APP_API_URL", "http://127.0.0.1:8765").rstrip("/")
TURN_SUBMIT_WAIT_SEC = int(os.environ.get("HG_TURN_SUBMIT_WAIT_SEC", "180"))
SESSION_CREATE_WAIT_SEC = int(os.environ.get("HG_SESSION_CREATE_WAIT_SEC", "180"))
API_READ_TIMEOUT_SEC = int(os.environ.get("HG_API_READ_TIMEOUT_SEC", "30"))
RECOVERY_POLL_INTERVAL_SEC = float(os.environ.get("HG_TURN_RECOVERY_POLL_SEC", "2"))
RECOVERY_PRESENTATION_BUDGET_SEC = int(os.environ.get("HG_TURN_RECOVERY_BUDGET_SEC", "600"))


class ApiResponseWaitExpired(Exception):
    """Client synchronous response wait expired — not authoritative round failure."""


class ApiConnectivityError(Exception):
    """Could not reach application API — not authoritative round failure."""


class ApiAuthoritativeFailure(Exception):
    """Server/application reported terminal round failure."""

    def __init__(self, failure: object) -> None:
        self.failure = failure
        super().__init__(str(failure))


def api_request(
    method: str,
    path: str,
    payload: dict | None = None,
    *,
    timeout: float | None = None,
) -> dict:
    url = f"{API_BASE}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    read_timeout = timeout if timeout is not None else API_READ_TIMEOUT_SEC
    try:
        with urllib.request.urlopen(req, timeout=read_timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except TimeoutError as exc:
        if method == "POST" and path == "/api/turns/submit":
            raise ApiResponseWaitExpired(str(exc)) from exc
        raise ApiConnectivityError(str(exc)) from exc
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": body}
        if exc.code == 502:
            raise ApiAuthoritativeFailure(parsed.get("error", parsed)) from exc
        if exc.code == 409:
            raise RuntimeError(parsed.get("error", parsed)) from exc
        raise RuntimeError(parsed.get("error", parsed)) from exc
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, TimeoutError) or (
            isinstance(reason, socket.timeout)
        ):
            if method == "POST" and path == "/api/turns/submit":
                raise ApiResponseWaitExpired(str(exc)) from exc
            raise ApiConnectivityError(str(exc)) from exc
        if "timed out" in str(exc).lower():
            if method == "POST" and path == "/api/turns/submit":
                raise ApiResponseWaitExpired(str(exc)) from exc
            raise ApiConnectivityError(str(exc)) from exc
        raise ApiConnectivityError(str(exc)) from exc


def record_recovery_milestone(
    milestone: str,
    *,
    operation_id: str | None,
    details: dict | None = None,
) -> None:
    if not st.session_state.hg_session_id:
        return
    try:
        api_request(
            "POST",
            "/api/application/recovery-milestone",
            {
                "hg_session_id": st.session_state.hg_session_id,
                "client_operation_id": operation_id,
                "milestone": milestone,
                "details": {
                    **(details or {}),
                    "response_wait_sec": TURN_SUBMIT_WAIT_SEC,
                },
            },
        )
    except Exception:  # noqa: BLE001
        pass


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
    if "role_routing" not in st.session_state:
        st.session_state.role_routing = "simple"
    if "audit_tags_by_entry" not in st.session_state:
        st.session_state.audit_tags_by_entry = {}
    if "turn_submission_locked" not in st.session_state:
        st.session_state.turn_submission_locked = False
    if "turn_recovery_active" not in st.session_state:
        st.session_state.turn_recovery_active = False
    if "pending_operation_id" not in st.session_state:
        st.session_state.pending_operation_id = None
    if "recovery_started_at" not in st.session_state:
        st.session_state.recovery_started_at = None
    if "recovery_status_message" not in st.session_state:
        st.session_state.recovery_status_message = None


def submission_controls_locked() -> bool:
    return bool(
        st.session_state.turn_submission_locked
        or st.session_state.turn_recovery_active
        or st.session_state.runtime_status == "round_in_progress"
    )


def clear_turn_recovery(*, unlock: bool = True) -> None:
    st.session_state.turn_recovery_active = False
    st.session_state.pending_operation_id = None
    st.session_state.recovery_started_at = None
    st.session_state.recovery_status_message = None
    if unlock:
        st.session_state.turn_submission_locked = False


def apply_status_payload(status: dict) -> None:
    health = status.get("health", {})
    st.session_state.runtime_status = health.get("application_status", "ready")
    if status.get("active_session_id"):
        st.session_state.hg_session_id = status["active_session_id"]
    if status.get("transcript"):
        st.session_state.transcript = status["transcript"]


def refresh_status() -> None:
    try:
        status = api_request("GET", "/api/status")
        apply_status_payload(status)
    except ApiConnectivityError as exc:
        st.session_state.runtime_status = f"unavailable: {exc}"
    except Exception as exc:  # noqa: BLE001
        st.session_state.runtime_status = f"unavailable: {exc}"


def recovery_poll_once() -> str:
    """Return recovery phase: processing | success | failure | unknown | connectivity."""
    operation_id = st.session_state.pending_operation_id
    try:
        status = api_request("GET", "/api/status")
        apply_status_payload(status)
    except ApiConnectivityError:
        return "connectivity"

    health = status.get("health", {})
    app_status = health.get("application_status")
    if app_status == "round_in_progress":
        return "processing"

    terminal = health.get("last_round_terminal") or {}
    if terminal.get("operation_id") == operation_id:
        if terminal.get("outcome") == "succeeded":
            return "success"
        if terminal.get("outcome") == "failed":
            return "failure"

    if app_status == "error" and health.get("last_error"):
        if terminal.get("operation_id") == operation_id:
            return "failure"

    if app_status in {"ready", "error"}:
        return "processing"

    return "unknown"


def handle_turn_recovery() -> None:
    started_at = st.session_state.recovery_started_at or time.time()
    elapsed = time.time() - started_at
    phase = recovery_poll_once()

    if phase == "processing":
        st.session_state.recovery_status_message = (
            "Round still processing on the server. Waiting for authoritative completion…"
        )
        st.info(st.session_state.recovery_status_message)
        if elapsed >= RECOVERY_PRESENTATION_BUDGET_SEC:
            record_recovery_milestone(
                "recovery_terminal",
                operation_id=st.session_state.pending_operation_id,
                details={"result": "polling_exhausted"},
            )
            clear_turn_recovery(unlock=True)
            st.warning(
                "Unable to determine current round outcome after automatic recovery polling. "
                "Use Refresh status or resume the session transcript when connectivity returns."
            )
            return
        time.sleep(RECOVERY_POLL_INTERVAL_SEC)
        st.rerun()
        return

    if phase == "success":
        record_recovery_milestone(
            "recovery_terminal",
            operation_id=st.session_state.pending_operation_id,
            details={"result": "success_recovered"},
        )
        clear_turn_recovery(unlock=True)
        st.success("Recovered authoritative round completion.")
        st.rerun()
        return

    if phase == "failure":
        record_recovery_milestone(
            "recovery_terminal",
            operation_id=st.session_state.pending_operation_id,
            details={"result": "failure_recovered"},
        )
        clear_turn_recovery(unlock=True)
        st.error("Round failed on the server (authoritative application failure).")
        st.rerun()
        return

    if phase == "connectivity":
        st.session_state.recovery_status_message = (
            "Unable to reach the application server to determine round status."
        )
        st.warning(st.session_state.recovery_status_message)
        if elapsed >= RECOVERY_PRESENTATION_BUDGET_SEC:
            record_recovery_milestone(
                "recovery_terminal",
                operation_id=st.session_state.pending_operation_id,
                details={"result": "status_unknown"},
            )
            clear_turn_recovery(unlock=True)
            st.warning("Unable to determine current round outcome.")
        else:
            time.sleep(RECOVERY_POLL_INTERVAL_SEC)
            st.rerun()
        return

    st.session_state.recovery_status_message = (
        "Unable to determine current round status from the application."
    )
    st.warning(st.session_state.recovery_status_message)
    if elapsed >= RECOVERY_PRESENTATION_BUDGET_SEC:
        record_recovery_milestone(
            "recovery_terminal",
            operation_id=st.session_state.pending_operation_id,
            details={"result": "status_unknown"},
        )
        clear_turn_recovery(unlock=True)
    else:
        time.sleep(RECOVERY_POLL_INTERVAL_SEC)
        st.rerun()


def begin_turn_submission() -> str:
    operation_id = str(uuid.uuid4())
    st.session_state.turn_submission_locked = True
    st.session_state.pending_operation_id = operation_id
    st.session_state.turn_recovery_active = False
    st.session_state.recovery_started_at = None
    st.session_state.recovery_status_message = None
    return operation_id


def start_turn_recovery_from_wait_expiry(operation_id: str) -> None:
    st.session_state.turn_recovery_active = True
    st.session_state.recovery_started_at = time.time()
    record_recovery_milestone(
        "client_wait_expired",
        operation_id=operation_id,
        details={"response_wait_sec": TURN_SUBMIT_WAIT_SEC},
    )
    record_recovery_milestone(
        "recovery_started",
        operation_id=operation_id,
        details={},
    )


def submit_user_turn(user_message: str, user_name: str, operation_id: str) -> None:
    api_request(
        "POST",
        "/api/turns/submit",
        {
            "userMessage": user_message,
            "userName": user_name,
            "client_operation_id": operation_id,
        },
        timeout=TURN_SUBMIT_WAIT_SEC,
    )


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
        if runtime.get("roleRouting"):
            st.session_state.role_routing = runtime["roleRouting"]
    except Exception:  # noqa: BLE001
        pass


def save_runtime_settings() -> None:
    api_request(
        "PUT",
        "/api/settings/runtime",
        {
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
    st.sidebar.caption(
        "Per-role reasoning and token profiles are configured internally. "
        "Use advanced API routing for experimentation."
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
        try:
            result = api_request(
                "POST",
                "/api/sessions/create",
                payload,
                timeout=SESSION_CREATE_WAIT_SEC,
            )
        except ApiConnectivityError as exc:
            st.sidebar.error(
                "Session create timed out or could not reach the application API. "
                f"Generated openings use live inference and may need up to "
                f"{SESSION_CREATE_WAIT_SEC}s. ({exc})"
            )
            return
        except Exception as exc:  # noqa: BLE001
            st.sidebar.error(str(exc))
            return
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

    if st.sidebar.button("Refresh status"):
        refresh_status()
        st.sidebar.success(f"Runtime: {st.session_state.runtime_status}")

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

    if st.session_state.turn_recovery_active:
        handle_turn_recovery()

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

    controls_locked = submission_controls_locked()
    if st.button("Skip turn", disabled=controls_locked, type="secondary"):
        operation_id = begin_turn_submission()
        try:
            result = api_request(
                "POST",
                "/api/turns/skip",
                {
                    "userName": st.session_state.user_persona_id,
                    "client_operation_id": operation_id,
                },
                timeout=TURN_SUBMIT_WAIT_SEC,
            )
            st.session_state.transcript = result.get("transcript", st.session_state.transcript)
            clear_turn_recovery(unlock=True)
            st.rerun()
        except ApiResponseWaitExpired:
            start_turn_recovery_from_wait_expiry(operation_id)
            st.rerun()
        except ApiAuthoritativeFailure as exc:
            clear_turn_recovery(unlock=True)
            st.error(f"Skip turn failed on server: {exc.failure}")
        except Exception as exc:  # noqa: BLE001
            clear_turn_recovery(unlock=True)
            st.error(f"Skip turn failed: {exc}")

    prompt = st.chat_input("Your message", disabled=controls_locked)
    if not prompt:
        return

    operation_id = begin_turn_submission()
    try:
        result = api_request(
            "POST",
            "/api/turns/submit",
            {
                "userMessage": prompt,
                "userName": st.session_state.user_persona_id,
                "client_operation_id": operation_id,
            },
            timeout=TURN_SUBMIT_WAIT_SEC,
        )
        st.session_state.transcript = result.get("transcript", st.session_state.transcript)
        clear_turn_recovery(unlock=True)
        st.rerun()
    except ApiResponseWaitExpired:
        start_turn_recovery_from_wait_expiry(operation_id)
        st.rerun()
    except ApiAuthoritativeFailure as exc:
        clear_turn_recovery(unlock=True)
        st.error(f"Round failed on server (authoritative application failure): {exc.failure}")
    except Exception as exc:  # noqa: BLE001
        clear_turn_recovery(unlock=True)
        st.error(f"Submission error: {exc}")


def main() -> None:
    st.set_page_config(page_title="Holy Grail V2", page_icon="⚔️", layout="wide")
    init_state()
    if not st.session_state.turn_recovery_active:
        refresh_status()
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
