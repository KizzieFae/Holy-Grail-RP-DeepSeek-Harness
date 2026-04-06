"""Heuristic per-turn narrator audits (v1). Pure, non-mutating builders."""

from __future__ import annotations

import re
from typing import Any

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "as",
        "by",
        "with",
        "her",
        "his",
        "their",
        "she",
        "he",
        "they",
        "it",
        "was",
        "were",
        "is",
        "are",
    }
)

_EXCERPT_LEN = 240

_PRESENT_MARKERS = re.compile(
    r"\b(is|are|am|walks|runs|stands|sits|looks|says|turns|moves|reaches)\b",
    re.IGNORECASE,
)


def _excerpt(s: str) -> str:
    t = str(s or "")
    if len(t) <= _EXCERPT_LEN:
        return t
    return t[:_EXCERPT_LEN] + "…"


def _tokenize_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", str(text or "").lower())


def _meaningful_tokens(text: str) -> list[str]:
    return [w for w in _tokenize_words(text) if w not in _STOPWORDS and len(w) > 1]


def _strip_double_quoted_regions(text: str) -> str:
    return re.sub(r'"[^"]*"', " ", str(text or ""))


def prior_assistant_rendered_content(
    chat_history: list[dict[str, Any]],
) -> str | None:
    for message in reversed(chat_history):
        if str(message.get("role", "")) != "assistant":
            continue
        content = str(message.get("content", "") or "").strip()
        if content:
            return content
    return None


def build_narrator_output_audit_v1(
    *,
    next_actor: str,
    move: dict[str, Any],
    decision: dict[str, Any],
    rendered_final: str,
    char_names: list[str],
    acting_display_name: str,
) -> dict[str, Any]:
    action = str(move.get("action", "") or "")
    render_for_action = _strip_double_quoted_regions(rendered_final)
    action_toks = set(_meaningful_tokens(action))
    render_toks = set(_meaningful_tokens(render_for_action))
    if not action_toks:
        overlap_ratio = 0.0
        hits = 0
        action_empty = True
    else:
        inter = action_toks & render_toks
        union = action_toks | render_toks
        overlap_ratio = len(inter) / len(union) if union else 0.0
        hits = len(inter)
        action_empty = False
    rl = rendered_final.lower()
    acting_name_in_render = next_actor.lower() in rl or acting_display_name.lower() in rl
    if action_empty:
        passes_action = True
    else:
        passes_action = overlap_ratio >= 0.12 or (
            hits >= 1 and acting_name_in_render
        )

    env_raw = str(decision.get("environment_event", "") or "").strip()
    environment_event_present = bool(env_raw)
    if not environment_event_present:
        env_status = "cue_empty"
        token_hits = 0
        passes_env = True
    else:
        env_tokens = [w for w in _tokenize_words(env_raw) if len(w) >= 3]
        token_hits = sum(1 for w in env_tokens if w in rl) if env_tokens else 0
        if token_hits > 0:
            env_status = "incorporated_weak"
            passes_env = True
        else:
            env_status = "not_found_in_render"
            passes_env = False

    other_found = [
        n
        for n in char_names
        if n and n != next_actor and str(n).lower() in rl
    ]

    return {
        "schema_version": 1,
        "layer": "narrator_output",
        "scope_note": "per_turn_only_v1; opening_excluded",
        "methods_note": "v1 heuristic only; LLM deferred to v1.1",
        "checks": {
            "action_coverage_heuristic": {
                "method": "heuristic_v1",
                "action_token_overlap_ratio": round(overlap_ratio, 4),
                "action_non_stopword_hits": hits,
                "acting_name_in_render": acting_name_in_render,
                "passes_bar": passes_action,
                "limitations": "Token overlap only; ignores paraphrase quality; quoted dialogue stripped from render window.",
            },
            "environment_event_heuristic": {
                "method": "heuristic_v1",
                "environment_event_present": environment_event_present,
                "environment_event_text": env_raw,
                "status": env_status,
                "token_hits_in_render": token_hits,
                "passes_bar": passes_env,
                "limitations": "Substring token match only; tension_shift not scored.",
            },
            "single_actor_scope_heuristic": {
                "method": "heuristic_v1",
                "other_cast_names_found": other_found,
                "passes_bar": len(other_found) == 0,
                "limitations": "Other names may appear legitimately in third-person narration.",
            },
        },
    }


def build_narrator_validation_audit_v1(
    *,
    narrator_raw: str,
    rendered_after_render_call: str,
    rendered_final: str,
    deterministic_dialogue_fallback_applied: bool,
    narrator_semantic_assessment: dict[str, Any] | None,
    semantic_fallback_effective: bool,
    semantic_fallback_llm_requested: bool,
    semantic_fallback_deterministic_critical: bool,
) -> dict[str, Any]:
    semantic = narrator_semantic_assessment or {}
    types_ordered: list[str] = []
    if deterministic_dialogue_fallback_applied:
        types_ordered.append("dialogue_missing")
    if semantic_fallback_effective:
        types_ordered.append("semantic_failure")
    fallback_triggered = bool(types_ordered)
    if not types_ordered:
        fb_type = "none"
    elif deterministic_dialogue_fallback_applied:
        fb_type = "dialogue_missing"
    else:
        fb_type = "semantic_failure"
    output_replaced = (
        deterministic_dialogue_fallback_applied or semantic_fallback_effective
    )
    original_vs_final_changed = rendered_final != rendered_after_render_call

    observed_payload = dict(semantic) if semantic else {}

    return {
        "schema_version": 1,
        "layer": "narrator_validation",
        "scope_note": "per_turn_only_v1; opening_excluded",
        "observed": {
            "narrator_raw": narrator_raw,
            "rendered_after_render_call": rendered_after_render_call,
            "rendered_final": rendered_final,
            "deterministic_dialogue_fallback_applied": deterministic_dialogue_fallback_applied,
            "semantic_validator_payload": observed_payload,
        },
        "derived": {
            "fallback_triggered": fallback_triggered,
            "fallback_type": fb_type,
            "fallback_types_ordered": list(types_ordered),
            "output_replaced": output_replaced,
            "original_vs_final_changed": original_vs_final_changed,
            "semantic_fallback_effective": semantic_fallback_effective,
            "semantic_fallback_llm_requested": semantic_fallback_llm_requested,
            "semantic_fallback_deterministic_critical": semantic_fallback_deterministic_critical,
        },
        "excerpts": {
            "narrator_raw": _excerpt(narrator_raw),
            "rendered_after_render_call": _excerpt(rendered_after_render_call),
            "rendered_final": _excerpt(rendered_final),
        },
        "provenance": {
            "deterministic_path": "app_turn_rendering.render_character_move",
            "semantic_path": "semantic_validation.assess_narrator_render_semantics",
        },
    }


def build_prose_dialogue_audit_v1(
    *,
    next_actor: str,
    move: dict[str, Any],
    rendered_final: str,
    prior_assistant_content: str | None,
    acting_display_name: str,
) -> dict[str, Any]:
    words = _tokenize_words(rendered_final)
    sentences = re.split(r"[.!?]+", rendered_final)
    sentences = [s.strip() for s in sentences if str(s).strip()]
    sentence_count = max(len(sentences), 1)
    avg_word_length = (
        sum(len(w) for w in words) / len(words) if words else 0.0
    )
    long_token_ratio = (
        sum(1 for w in words if len(w) > 6) / len(words) if words else 0.0
    )
    passes_read = avg_word_length <= 9.0 and long_token_ratio <= 0.35

    dialogue = str(move.get("dialogue", "") or "").strip()
    dialogue_non_empty = bool(dialogue)
    exact_quoted = bool(dialogue) and f'"{dialogue}"' in rendered_final
    passes_dialogue = (not dialogue_non_empty) or exact_quoted

    if prior_assistant_content:
        a = set(_meaningful_tokens(rendered_final))
        b = set(_meaningful_tokens(prior_assistant_content))
        union = a | b
        jaccard = len(a & b) / len(union) if union else 0.0
        prior_turns_used = 1
    else:
        jaccard = 0.0
        prior_turns_used = 0
    passes_redundancy = prior_turns_used == 0 or jaccard < 0.65

    quote_idx = rendered_final.find('"')
    window_start = max(0, quote_idx - 80)
    pre_quote = rendered_final[window_start:quote_idx].lower()
    name_tokens = {next_actor.lower(), acting_display_name.lower()}
    attribution_ok = (not dialogue_non_empty) or quote_idx < 0 or any(
        n in pre_quote for n in name_tokens if n
    )

    present_hits = len(_PRESENT_MARKERS.findall(rendered_final))
    passes_tone = present_hits <= 2

    return {
        "schema_version": 1,
        "layer": "prose_dialogue",
        "scope_note": "per_turn_only_v1; opening_excluded",
        "methods_note": "v1 heuristic proxies only; LLM deferred to v1.1",
        "checks": {
            "readability_proxy": {
                "method": "heuristic_v1",
                "sentence_count": sentence_count,
                "avg_word_length": round(avg_word_length, 3),
                "long_token_ratio": round(long_token_ratio, 4),
                "passes_bar": passes_read,
            },
            "redundancy_vs_prior": {
                "method": "heuristic_v1",
                "prior_turns_used": prior_turns_used,
                "jaccard_word_overlap": round(jaccard, 4),
                "passes_bar": passes_redundancy,
                "limitations": "High overlap may be intentional anaphora.",
            },
            "dialogue_integration_proxy": {
                "method": "heuristic_v1",
                "dialogue_non_empty": dialogue_non_empty,
                "exact_dialogue_quoted_in_render": exact_quoted,
                "passes_bar": passes_dialogue,
            },
            "attribution_proxy": {
                "method": "heuristic_v1",
                "acting_surname_or_display_token_near_quote": attribution_ok,
                "passes_bar": attribution_ok,
                "limitations": "Pronoun-only attribution yields false negatives.",
            },
            "tone_consistency_local": {
                "method": "heuristic_v1",
                "present_tense_verb_hits": present_hits,
                "passes_bar": passes_tone,
                "limitations": "Crude past-tense proxy.",
            },
        },
    }
