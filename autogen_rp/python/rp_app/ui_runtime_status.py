"""Read-only runtime / evaluation status for Streamlit (UI sync pass 1).

Single source for sidebar status strip and debug panel. Uses the same backend
interpretation as the turn pipeline — no duplicate env rules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from episodic_memory_prompt import is_episodic_memory_enabled
from retrieved_context_select import get_index_path_from_env


def build_runtime_evaluation_status(*, st_module: Any) -> dict[str, Any]:
    """Snapshot from env helpers + existing session_state only (no new keys)."""
    scene_started = bool(st_module.session_state.get("scene_started", False))
    idx_path = get_index_path_from_env()
    retrieval_on = idx_path is not None
    index_basename = Path(idx_path).name if idx_path else ""
    return {
        "scene_started": scene_started,
        "retrieval_on": retrieval_on,
        "index_basename": index_basename,
        "episodic_on": is_episodic_memory_enabled(),
        "audit_enabled": bool(st_module.session_state.get("audit_enabled", False)),
        "template_id": st_module.session_state.get("selected_scene_template_id"),
        "template_display": (
            "(legacy opener flow — no template id)"
            if not st_module.session_state.get("selected_scene_template_id")
            else str(st_module.session_state.get("selected_scene_template_id"))
        ),
    }


def runtime_evaluation_status_markdown(*, st_module: Any) -> str:
    """Markdown lines for status strip and debug panel (identical content)."""
    d = build_runtime_evaluation_status(st_module=st_module)
    lines: list[str] = []
    if d["retrieval_on"]:
        ib = d["index_basename"]
        extra = f" — `{ib}`" if ib else ""
        lines.append(f"- **Authored retrieval (env):** ON{extra}")
    else:
        lines.append(
            "- **Authored retrieval (env):** OFF (`RP_RETRIEVED_CONTEXT_INDEX` unset or empty)"
        )
    lines.append(
        f"- **Episodic merge (env):** {'ON' if d['episodic_on'] else 'OFF'} (`RP_EPISODIC_MEMORY`)"
    )
    if d["scene_started"]:
        aud = "**ON**" if d["audit_enabled"] else "**OFF**"
        lines.append(
            f"- **Audit:** {aud} for this scene (frozen at start; cannot change mid-scene)."
        )
        lines.append(
            f"- **Active template (frozen at scene start):** {d['template_display']}"
        )
    else:
        if d["audit_enabled"]:
            lines.append(
                "- **Audit:** Will be **enabled** when you start if the Audit toggle below stays ON. "
                "**Locked at scene start** — cannot change mid-scene from this UI."
            )
        else:
            lines.append(
                "- **Audit:** Will be **disabled** when you start unless you turn the Audit toggle below ON "
                "before **Start Scene**. **Locked at scene start** — cannot change mid-scene from this UI."
            )
        lines.append(f"- **Selected template:** {d['template_display']}")
    return "\n".join(lines)
