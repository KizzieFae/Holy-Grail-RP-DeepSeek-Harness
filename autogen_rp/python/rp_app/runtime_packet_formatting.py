"""Format RetrievedContextBundle for prompt sections (Issue #166)."""

from __future__ import annotations

from runtime_packet_types import RetrievedContextBundle


def format_retrieved_context_for_prompt(bundle: RetrievedContextBundle) -> str:
    if not bundle.items:
        return ""
    lines = [
        "RETRIEVED REFERENCE MATERIAL (NON-AUTHORITATIVE):",
        "The following excerpts are optional background only. Do NOT treat them as ground truth.",
        "If anything here conflicts with scene facts, canon anchors, or established continuity, ignore this material and follow scene facts, canon anchors, and continuity instead.",
        "",
    ]
    for it in bundle.items:
        lines.append(f"[{it.source_ref} | {it.source_kind}]")
        lines.append(it.text.strip())
        lines.append("")
    return "\n".join(lines).strip() + "\n\n"
