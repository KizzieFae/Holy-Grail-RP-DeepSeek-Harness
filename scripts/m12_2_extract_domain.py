#!/usr/bin/env python3
"""M12.2 bulk domain extraction: move V2 closure modules to v2/domain/modules."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RP_APP = REPO / "autogen_rp" / "python" / "rp_app"
MODULES = REPO / "v2" / "domain" / "modules"

# V2 transitive closure (AST-derived); character_loader stays as V1 shim.
TOP_LEVEL = [
    "app_memory_summary",
    "app_state_scene",
    "canonical_compile_adapters",
    "character_move_adapters",
    "character_move_ingress",
    "character_state",
    "character_state_manager",
    "character_state_model",
    "continuity_audit_origin",
    "continuity_canon_anchors",
    "continuity_consequence_classifier",
    "continuity_consequence_classifier_constants",
    "continuity_consequence_classifier_dedupe",
    "continuity_consequence_classifier_detect_outcome_language",
    "continuity_consequence_classifier_detect_scene_dynamics",
    "continuity_consequence_classifier_grounding",
    "continuity_consequence_classifier_move_tools",
    "continuity_consequence_classifier_regexes",
    "continuity_consequence_classifier_signals",
    "continuity_consequence_phrase_maps",
    "continuity_event_promotion_policy",
    "continuity_issue_helpers",
    "continuity_issue_lexicon",
    "continuity_issue_lifecycle",
    "continuity_issue_manager_wiring",
    "continuity_issue_matching",
    "continuity_issue_pressure",
    "continuity_issue_retrieval",
    "continuity_issue_transitions",
    "continuity_knowledge_helpers",
    "continuity_manager",
    "continuity_manager_canon_surface",
    "continuity_manager_event_surface",
    "continuity_manager_excursions",
    "continuity_manager_issue_surface",
    "continuity_manager_presence_surface",
    "continuity_manager_queries",
    "continuity_mutation_pipeline",
    "continuity_mutation_pipeline_apply",
    "continuity_mutation_pipeline_audit",
    "continuity_mutation_pipeline_compose",
    "continuity_mutation_pipeline_extract",
    "continuity_mutation_pipeline_normalize",
    "continuity_mutation_pipeline_types",
    "continuity_mutation_pipeline_validate",
    "continuity_presence_helpers",
    "continuity_presence_pipeline",
    "continuity_process_turn_orchestration",
    "continuity_reintegration",
    "continuity_resolved_outcomes",
    "continuity_scene_helpers",
    "continuity_scene_state_update",
    "continuity_semantic_proposals",
    "continuity_setup_seam_v77",
    "continuity_state",
    "continuity_state_canon",
    "continuity_state_consequence",
    "continuity_state_datetime",
    "continuity_state_excursion",
    "continuity_state_interpretation",
    "continuity_state_issue",
    "continuity_state_public_event",
    "continuity_state_resolved_outcome",
    "continuity_state_scene",
    "continuity_state_snapshot",
    "continuity_state_summary",
    "continuity_summary_helpers",
    "continuity_turn_classification",
    "cross_session_memory_policy",
    "issue240_semantic_evaluation",
    "perception_audibility",
    "perception_audibility_constants",
    "perception_audibility_events",
    "perception_audibility_formatting",
    "perception_audibility_history",
    "perception_audibility_normalize",
    "perception_audibility_player",
    "perception_audibility_quote_policy",
    "perception_audibility_structured",
    "perception_audibility_visibility",
    "progression_simulation_scenarios",
    "prompt_builders",
    "resolved_outcome_access_location_entry",
    "resolved_outcome_communication_housing_call",
    "resolved_outcome_engine",
    "resolved_outcome_lodging_sleep_surface",
    "resolved_outcome_medical_suppressant_formulation",
    "resolved_outcome_normalize",
    "resolved_outcome_registry",
    "resolved_outcome_spec",
    "resolved_outcome_transaction_scene_commitment",
    "response_validation",
    "response_validation_binding_sleeping_surface",
    "response_validation_content",
    "response_validation_drift",
    "response_validation_investigation_recall",
    "response_validation_parsing",
    "response_validation_presence",
    "response_validation_registry_slots",
    "response_validation_selection",
    "scene_exit_detection",
    "scene_grounding",
    "scene_opener",
    "scene_template",
    "scene_template_cohesion",
    "semantic_eval_profiles",
    "session_manager",
    "tension_pacing_policy",
    "user_presence_signals",
]

SKIP = {"character_loader"}  # already a V1 shim over v2/domain/character_cards

SHIM_HEADER = '''\
"""Legacy V1 import shim — implementation in v2/domain/modules/{relpath}."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_IMPL = Path(__file__).resolve().parents[3] / "v2" / "domain" / "modules" / "{relpath}"
if not _IMPL.is_file():
    raise ImportError(f"Domain module not found: {{_IMPL}}")

_MOD_NAME = "_domain_shim_{modname}"
_spec = importlib.util.spec_from_file_location(_MOD_NAME, _IMPL)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load domain module: {{_IMPL}}")
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_MOD_NAME] = _mod
_spec.loader.exec_module(_mod)
globals().update({{k: v for k, v in _mod.__dict__.items() if not k.startswith("_")}})
'''


def write_shim(dest: Path, relpath: str, modname: str) -> None:
    dest.write_text(
        SHIM_HEADER.format(relpath=relpath.replace("\\", "/"), modname=modname),
        encoding="utf-8",
    )


def main() -> int:
    MODULES.mkdir(parents=True, exist_ok=True)
    (MODULES / "memory_layer").mkdir(parents=True, exist_ok=True)

    moved: list[str] = []
    for name in TOP_LEVEL:
        src = RP_APP / f"{name}.py"
        if not src.is_file():
            print(f"SKIP missing: {src}", file=sys.stderr)
            continue
        dest = MODULES / f"{name}.py"
        if dest.exists():
            print(f"SKIP already moved: {name}")
            continue
        shutil.move(str(src), str(dest))
        write_shim(src, f"{name}.py", name)
        moved.append(name)

    # memory_layer package (closure uses retrieval, storage, writes; move whole package)
    ml_src = RP_APP / "memory_layer"
    ml_dest = MODULES / "memory_layer"
    for fname in ("__init__.py", "retrieval.py", "storage.py", "writes.py", "facade.py"):
        s = ml_src / fname
        if not s.is_file():
            continue
        d = ml_dest / fname
        if d.exists():
            continue
        shutil.move(str(s), str(d))

    # memory_layer shims
    ml_init = ml_src / "__init__.py"
    ml_init.write_text(
        '''\
"""Legacy V1 memory_layer shim — implementation in v2/domain/modules/memory_layer/."""

from __future__ import annotations

import sys
from pathlib import Path

_MODULES = Path(__file__).resolve().parents[4] / "v2" / "domain" / "modules"
if str(_MODULES) not in sys.path:
    sys.path.insert(0, str(_MODULES))

from memory_layer.facade import *  # noqa: F403
''',
        encoding="utf-8",
    )
    for fname in ("retrieval.py", "storage.py", "writes.py", "facade.py"):
        shim = ml_src / fname
        write_shim(shim, f"memory_layer/{fname}", f"memory_layer_{fname[:-3]}")

    print(f"Moved {len(moved)} top-level modules + memory_layer package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
