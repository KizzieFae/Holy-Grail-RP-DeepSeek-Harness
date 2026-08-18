"""Character turn: authored retrieval index load, bundle selection, episodic merge (sole runtime selector path)."""

from __future__ import annotations

import logging
from typing import Any

from episodic_memory_cache import get_or_compile_episodic_candidate_pool
from episodic_memory_inputs import continuity_sequences_for_episodic
from episodic_memory_prompt import is_episodic_memory_enabled
from episodic_memory_select import select_episodic_items_for_character
from retrieved_context_select import (
    get_index_path_from_env,
    load_authored_retrieval_index,
    log_retrieval_if_active,
    merge_retrieved_context_with_episodic,
    select_retrieved_context_bundle,
    structured_prompt_id_sets_for_episodic_suppression,
)
from runtime_packets import RetrievedContextBundle

_episodic_merge_log = logging.getLogger("rp_app.episodic_prompt")


def _prompt_dedup_texts_for_retrieval(
    scene_state: dict[str, Any],
    canon_anchors: list[dict[str, Any]],
    summary_blocks: list[dict[str, Any]],
) -> tuple[str, ...]:
    out: list[str] = []
    for key in ("scene_premise", "opening_description"):
        v = scene_state.get(key)
        if v is not None and str(v).strip():
            out.append(str(v))
    for ca in canon_anchors:
        if isinstance(ca, dict):
            for v in ca.values():
                if isinstance(v, str) and v.strip():
                    out.append(v)
    for sb in summary_blocks:
        if isinstance(sb, dict):
            for v in sb.values():
                if isinstance(v, str) and v.strip():
                    out.append(v)
    return tuple(out)


def build_character_retrieved_context_bundle(
    *,
    st_module: Any,
    scene_state: dict[str, Any],
    canon_anchors: list[dict[str, Any]],
    summary_blocks: list[dict[str, Any]],
    char_name: str,
    relationship_focus_names: list[str],
    cast: list[str],
    active_issues: list[dict[str, Any]],
    recent_public_events: list[dict[str, Any]],
    my_interpretations: list[dict[str, Any]],
    continuity_manager: Any | None,
) -> RetrievedContextBundle:
    """Load index from env, select or merge exactly once, log retrieval, set session nonempty-bundle flag."""
    _retrieval_index = load_authored_retrieval_index(get_index_path_from_env())
    _dedup_texts = _prompt_dedup_texts_for_retrieval(
        scene_state, canon_anchors, summary_blocks
    )
    _tid = str(scene_state.get("scene_template_id", "") or "")
    _rf = tuple(sorted(relationship_focus_names))
    _cast_t = tuple(sorted(cast))
    if is_episodic_memory_enabled() and continuity_manager is not None:
        pe, itp, isu, ca = continuity_sequences_for_episodic(continuity_manager)
        pool = get_or_compile_episodic_candidate_pool(
            st_module.session_state,
            public_events=pe,
            interpretations=itp,
            issues=isu,
            canon_anchors=ca,
        )
        _sup_issue_ids, _sup_evt_ids, _sup_int_ids = (
            structured_prompt_id_sets_for_episodic_suppression(
                active_issues=active_issues,
                recent_public_events=recent_public_events,
                my_interpretations=my_interpretations,
            )
        )
        episodic_selected = select_episodic_items_for_character(
            pool,
            char_name,
            structured_prompt_issue_ids=_sup_issue_ids,
            structured_prompt_public_event_ids=_sup_evt_ids,
            structured_prompt_interpretation_ids=_sup_int_ids,
        )
        retrieved_bundle = merge_retrieved_context_with_episodic(
            index=_retrieval_index,
            char_name=char_name,
            scene_template_id=_tid,
            relationship_focus_names=_rf,
            cast=_cast_t,
            dedup_against_texts=_dedup_texts,
            episodic_items=episodic_selected,
            structured_prompt_issue_ids=_sup_issue_ids,
            structured_prompt_public_event_ids=_sup_evt_ids,
            structured_prompt_interpretation_ids=_sup_int_ids,
        )
        _episodic_merge_log.info(
            "episodic merge char=%s pool_len=%d selected_len=%d bundle_items=%d",
            char_name,
            len(pool),
            len(episodic_selected),
            len(retrieved_bundle.items),
        )
    else:
        retrieved_bundle = select_retrieved_context_bundle(
            index=_retrieval_index,
            char_name=char_name,
            scene_template_id=_tid,
            relationship_focus_names=_rf,
            cast=_cast_t,
            dedup_against_texts=_dedup_texts,
        )
    log_retrieval_if_active(retrieved_bundle, char_name=char_name)
    if retrieved_bundle.items:
        st_module.session_state["sim_retrieval_saw_nonempty_bundle"] = True
    return retrieved_bundle
