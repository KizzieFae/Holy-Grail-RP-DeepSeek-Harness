"""Markdown reporting for ``HeadlessSimulationResult`` checklist output."""

from __future__ import annotations

import json

from headless_simulation_runner import HeadlessSimulationResult


def format_simulation_audit_markdown(result: HeadlessSimulationResult) -> str:
    """Human-readable audit block for checklist review."""
    lines = [
        "## LLM scene simulation audit",
        "",
    ]
    if result.scenario_id:
        lines.append(f"* **Scenario:** `{result.scenario_id}`")
    if result.scenario_title:
        lines.append(f"* **Title:** {result.scenario_title}")
    if result.scenario_intent:
        lines.append(f"* **Intent:** {result.scenario_intent}")
    if result.audit_session_number is not None:
        lines.append(f"* **Audit session:** {result.audit_session_number:03d}")
    if result.audit_summary_report_path:
        lines.append(f"* **Audit summary report:** `{result.audit_summary_report_path}`")
    if result.progression_metrics_summary:
        m = result.progression_metrics_summary
        lines.append(
            f"* **First qualifying delta (continuity turn index):** "
            f"{m.get('first_qualifying_progression_delta_turn_index')!r}"
        )
        lines.append(f"* **Progression retries:** {m.get('progression_retries_triggered', 0)}")
        lines.append(
            f"* **Failed progression attempts:** {m.get('failed_progression_attempts', 0)}"
        )
        lines.append(
            f"* **Qualifying / non-qualifying accepted turns:** "
            f"{m.get('qualifying_turns', 0)} / {m.get('non_qualifying_turns', 0)}"
        )
        lines.append(
            f"* **Progression enforcement:** "
            f"{'on' if m.get('progression_enforcement_enabled') else 'off (baseline)'}"
        )
    if result.structured_eval:
        se = result.structured_eval
        if se.get("issue29_long_run_harness"):
            lines.append("* **Issue #29 long-run harness:** enabled (investigation-only)")
        if se.get("verdict") is not None:
            lines.append(f"* **Verdict (manual):** {se.get('verdict')!r}")
        if se.get("failure_classification") is not None:
            lines.append(
                f"* **Failure classification (manual):** {se.get('failure_classification')!r}"
            )
    lines.extend(
        [
            f"* **Continuity turns processed:** {result.continuity_turn_counter}",
            f"* **Last turn classifier consequences:** {result.last_turn_consequences!r}",
            "",
            "### Selector / pipeline notes",
        ]
    )
    for s in result.selector_decisions:
        lines.append(f"- {s}")
    lines.extend(["", "### Structured moves (orchestration)", ""])
    for i, m in enumerate(result.recent_structured_moves, 1):
        if not isinstance(m, dict):
            lines.append(f"{i}. {m!r}")
            continue
        sp = m.get("speaker", "")
        lines.append(f"{i}. **{sp}** action={m.get('action', '')!r} dialogue={m.get('dialogue', '')!r}")
        lines.append(f"   - consequences: {m.get('consequences', [])!r}")
    lines.extend(["", "### Chat history (rendered + user lines)", ""])
    for entry in result.chat_history[-24:]:
        role = entry.get("role", "")
        name = entry.get("name", "")
        content = str(entry.get("content", ""))[:500]
        lines.append(f"- [{role}] {name}: {content!r}")
    if result.structured_eval:
        lines.extend(
            [
                "",
                "### Structured run result (JSON)",
                "",
                "```json",
                json.dumps(result.structured_eval, indent=2, ensure_ascii=False),
                "```",
            ]
        )
    return "\n".join(lines)
