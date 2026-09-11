"""Inference-facing contract projection for S2a librarian_mediation (#169)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_CONTRACT_PATH = (
    Path(__file__).resolve().parents[1]
    / "contracts"
    / "inference"
    / "hg_librarian_mediation_result_v1.inference-contract.json"
)


@lru_cache(maxsize=1)
def load_librarian_mediation_inference_contract() -> dict[str, Any]:
    with _CONTRACT_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _render_field_specs(field_specs: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for field_name, spec in field_specs.items():
        if spec.get("type") == "array":
            item_fields = spec.get("item_fields") or {}
            lines.append(f"- {field_name}: array")
            for item_field, item_spec in item_fields.items():
                req = "required" if item_spec.get("required") else "optional"
                extra = ""
                if item_spec.get("type") == "enum":
                    extra = f" one of {item_spec.get('values')}"
                elif item_spec.get("type") == "positive_integer":
                    extra = " positive integer"
                elif item_spec.get("catalog_only"):
                    extra = " catalog source_id only"
                lines.append(f"  - {item_field} ({req}){extra}")
        else:
            req = "required" if spec.get("required") else "optional"
            lines.append(f"- {field_name} ({req})")
    return lines


def render_mediation_inference_contract_lines(
    *,
    sample_source_id: str = "lmi:cand:example-source",
) -> str:
    contract = load_librarian_mediation_inference_contract()
    schema_id = contract["schema_id"]
    example = json.loads(json.dumps(contract["minimal_valid_example"]))
    if example.get("selected_items"):
        example["selected_items"][0]["source_id"] = sample_source_id
    if example.get("synthesis_entries"):
        example["synthesis_entries"][0]["source_ids"] = [sample_source_id]

    lines = [
        f"Required output contract for schema {schema_id}:",
        "",
        "Top-level object MUST include:",
        f'- schema: exact string "{schema_id}"',
        f"- required fields: {', '.join(contract.get('required_top_level', []))}",
        "",
        "Field specifications:",
        *_render_field_specs(contract.get("field_specs") or {}),
        "",
        "Forbidden field aliases (do NOT use):",
    ]
    for alias in contract.get("forbidden_field_aliases") or []:
        lines.append(f"- {alias.get('path')} — use {alias.get('use_instead')} instead")
    lines.append("")
    lines.append("Forbidden behaviors:")
    for rule in contract.get("forbidden_behaviors") or []:
        lines.append(f"- {rule}")
    lines.append("")
    lines.append("Minimal valid example (replace source_id with catalog values):")
    lines.append(json.dumps(example, ensure_ascii=False, indent=2))
    return "\n".join(lines)
