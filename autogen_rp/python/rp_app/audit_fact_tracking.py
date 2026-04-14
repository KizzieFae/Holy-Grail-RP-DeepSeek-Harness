"""Deterministic fact tracking over existing character audits (GitHub #58, #62).

Offline post-processor only: reads character ``*_full.json`` rows; emits
``failure_classification`` in {``support_loss``, ``utilization_failure``, ``indeterminate``}.
Does not import runtime turn assembly or continuity.

``run_fact_track_postprocess`` (GitHub #62) is the shared post-run entry: it calls
``analyze_fact_tracking``, writes a companion JSON file (not ``_audit_summary.json``), and
returns the analysis dict plus ``companion_artifact_path``.

Uses the same row shape as ``issue29_investigation.load_character_audit_rows`` and
reuses ``diff_support_manifests`` / Issue #29 non-envelope diff semantics for support
path disruption alongside literal presence checks.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Final

from audit_support_manifest import diff_support_manifests
from issue29_investigation import load_character_audit_rows

FACT_SPEC_SCHEMA_VERSION: Final[str] = "fact_spec.v1"


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def fact_spec_sha256(spec: dict[str, Any]) -> str:
    """Stable SHA-256 over canonical JSON of the spec (for reproducibility)."""
    payload = _canonical_json(spec).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _row_prompt(row: dict[str, Any]) -> str:
    return str(row.get("content", "") or "")


def _combined_move(po: dict[str, Any]) -> str:
    if not isinstance(po, dict):
        return ""
    return f"{po.get('dialogue', '')}\n{po.get('action', '')}"


def _rule_prompt_literals_all(row: dict[str, Any], rule: dict[str, Any]) -> bool:
    literals = rule.get("literals")
    if not isinstance(literals, list) or not literals:
        return False
    p = _row_prompt(row)
    return all(str(lit) in p for lit in literals if str(lit))


def _rule_parsed_literals_all(row: dict[str, Any], rule: dict[str, Any]) -> bool:
    literals = rule.get("literals")
    if not isinstance(literals, list) or not literals:
        return False
    po = row.get("parsed_output")
    if not isinstance(po, dict):
        po = {}
    c = _combined_move(po)
    return all(str(lit) in c for lit in literals if str(lit))


def _eval_rule(row: dict[str, Any], rule: dict[str, Any], *, purpose: str) -> bool:
    if not isinstance(rule, dict):
        return False
    kind = str(rule.get("kind", "") or "")
    if kind == "prompt_literals_all":
        return _rule_prompt_literals_all(row, rule)
    if kind == "parsed_output_literals_all":
        return _rule_parsed_literals_all(row, rule)
    raise ValueError(f"unsupported rule kind for {purpose}: {kind!r}")


def _filter_rows_actor(
    rows: list[dict[str, Any]], scope: dict[str, Any]
) -> list[dict[str, Any]]:
    if not isinstance(scope, dict):
        return list(rows)
    kind = str(scope.get("kind", "") or "")
    if kind in ("", "all_characters"):
        return list(rows)
    if kind == "character_name":
        name = str(scope.get("name", "") or "").strip()
        if not name:
            return list(rows)
        return [r for r in rows if str(r.get("bot_name", "") or "").strip() == name]
    raise ValueError(f"unsupported actor_scope.kind: {kind!r}")


def _manifest(row: dict[str, Any]) -> dict[str, Any] | None:
    md = row.get("metadata")
    if not isinstance(md, dict):
        return None
    sm = md.get("support_manifest")
    return sm if isinstance(sm, dict) else None


def _manifest_diff_non_envelope_only(diff: dict[str, Any]) -> bool:
    """True if diff involves any unit type other than prompt_envelope (Issue #29)."""

    def _types(entries: Any) -> set[str]:
        out: set[str] = set()
        if not isinstance(entries, list):
            return out
        for e in entries:
            if isinstance(e, dict) and isinstance(e.get("type"), str):
                out.add(e["type"])
        return out

    for key in ("support_absent", "support_new"):
        for t in _types(diff.get(key)):
            if t != "prompt_envelope":
                return True
    for e in diff.get("support_changed") or []:
        if isinstance(e, dict) and e.get("type") != "prompt_envelope":
            return True
    return False


def _consecutive_manifest_disruption(
    rows: list[dict[str, Any]], intro_i: int, end_i: int
) -> bool:
    """True if any adjacent character rows in [intro_i, end_i] show non-envelope manifest diff."""
    if intro_i < 0 or end_i >= len(rows) or end_i <= intro_i:
        return False
    for k in range(intro_i + 1, end_i + 1):
        prev = rows[k - 1]
        cur = rows[k]
        mp = _manifest(prev)
        mc = _manifest(cur)
        if mp is None or mc is None:
            continue
        d = diff_support_manifests(mp, mc)
        if _manifest_diff_non_envelope_only(d):
            return True
    return False


def validate_fact_spec(spec: dict[str, Any]) -> tuple[bool, str]:
    if not isinstance(spec, dict):
        return False, "spec_not_object"
    if str(spec.get("schema_version", "") or "") != FACT_SPEC_SCHEMA_VERSION:
        return False, "bad_schema_version"
    if not str(spec.get("probe_id", "") or "").strip():
        return False, "missing_probe_id"
    for key in ("establishment_rule", "support_predicate", "behavior_rule"):
        rule = spec.get(key)
        if not isinstance(rule, dict):
            return False, f"missing_{key}"
        kind = str(rule.get("kind", "") or "")
        if kind not in ("prompt_literals_all", "parsed_output_literals_all"):
            return False, f"bad_kind_{key}"
        lit = rule.get("literals")
        if not isinstance(lit, list) or not lit:
            return False, f"missing_literals_{key}"
    scope = spec.get("actor_scope")
    if scope is not None and not isinstance(scope, dict):
        return False, "bad_actor_scope"
    if isinstance(scope, dict):
        sk = str(scope.get("kind", "") or "")
        if sk and sk not in ("all_characters", "character_name"):
            return False, "bad_actor_scope_kind"
        if sk == "character_name" and not str(scope.get("name", "") or "").strip():
            return False, "actor_scope_name_empty"
    return True, "ok"


def analyze_fact_tracking(
    session_dir: Path,
    fact_spec: dict[str, Any],
) -> dict[str, Any]:
    """Run Phase-1 fact tracking for one audit session directory and one ``fact_spec``."""
    session_dir = session_dir.resolve()
    ok, reason = validate_fact_spec(fact_spec)
    sha = fact_spec_sha256(fact_spec)
    base: dict[str, Any] = {
        "schema_version": "audit_fact_tracking.v1",
        "session_dir": str(session_dir),
        "probe_id": str(fact_spec.get("probe_id", "") or ""),
        "fact_spec_sha256": sha,
        "T_intro": None,
        "T_support_last": None,
        "T_divergence": None,
        "support_state_at_divergence": None,
        "failure_classification": "indeterminate",
        "indeterminate_reason": reason if not ok else None,
        "path_manifest_disruption": None,
    }
    if not ok:
        return base

    rows_all = load_character_audit_rows(session_dir)
    scope = fact_spec.get("actor_scope")
    rows = _filter_rows_actor(rows_all, scope if isinstance(scope, dict) else {})

    est = fact_spec["establishment_rule"]
    sup = fact_spec["support_predicate"]
    beh = fact_spec["behavior_rule"]

    if not rows:
        base["indeterminate_reason"] = "no_character_rows"
        return base

    intro_i: int | None = None
    for i, row in enumerate(rows):
        try:
            if _eval_rule(row, est, purpose="establishment"):
                intro_i = i
                break
        except ValueError as e:
            base["indeterminate_reason"] = str(e)
            return base

    if intro_i is None:
        base["indeterminate_reason"] = "no_establishment"
        return base

    diver_i: int | None = None
    for j in range(intro_i + 1, len(rows)):
        try:
            if not _eval_rule(rows[j], beh, purpose="behavior"):
                diver_i = j
                break
        except ValueError as e:
            base["indeterminate_reason"] = str(e)
            return base

    if diver_i is None:
        base["T_intro"] = _turn_anchor(rows[intro_i], intro_i)
        base["indeterminate_reason"] = "no_divergence"
        return base

    support_flags: list[bool] = []
    try:
        for k in range(intro_i, diver_i + 1):
            support_flags.append(_eval_rule(rows[k], sup, purpose="support"))
    except ValueError as e:
        base["indeterminate_reason"] = str(e)
        return base

    support_at_div = support_flags[-1]
    any_support_gap = not all(support_flags)
    manifest_disrupt = _consecutive_manifest_disruption(rows, intro_i, diver_i)

    if any_support_gap:
        failure = "support_loss"
    elif manifest_disrupt:
        failure = "support_loss"
    elif support_at_div:
        failure = "utilization_failure"
    else:
        failure = "indeterminate"
        base["indeterminate_reason"] = "ambiguous_support_at_divergence"

    last_support_idx = intro_i
    for k in range(intro_i, diver_i + 1):
        try:
            if _eval_rule(rows[k], sup, purpose="support"):
                last_support_idx = k
        except ValueError:
            break

    base.update(
        {
            "T_intro": _turn_anchor(rows[intro_i], intro_i),
            "T_divergence": _turn_anchor(rows[diver_i], diver_i),
            "T_support_last": _turn_anchor(rows[last_support_idx], last_support_idx),
            "support_state_at_divergence": support_at_div,
            "path_manifest_disruption": manifest_disrupt,
            "failure_classification": failure,
        }
    )
    if failure != "indeterminate":
        base["indeterminate_reason"] = None
    return base


def _fact_track_probe_slug(probe_id: str) -> str:
    raw = str(probe_id or "").strip() or "unknown"
    safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in raw)
    return safe[:120] if safe else "unknown"


def run_fact_track_postprocess(
    session_dir: Path | str,
    fact_spec: dict[str, Any],
    *,
    companion_path: Path | str | None = None,
) -> dict[str, Any]:
    """Run fact tracking on a completed audit session and write a companion artifact.

    Calls :func:`analyze_fact_tracking` (deterministic). Writes UTF-8 JSON to
    ``companion_path`` or to ``<session_dir>/fact_track__<probe_slug>__<sha16>.json``.
    The file contains only the analysis payload (no ``companion_artifact_path`` key).

    Return value is the analysis dict plus ``companion_artifact_path`` (absolute path string)
    for orchestration. Does not read or write ``_audit_summary.json``.
    """
    sd = Path(session_dir).resolve()
    result = analyze_fact_tracking(sd, fact_spec)
    sha = str(result.get("fact_spec_sha256") or fact_spec_sha256(fact_spec))
    probe_key = str(fact_spec.get("probe_id", "") or result.get("probe_id") or "")
    slug = _fact_track_probe_slug(probe_key)
    if companion_path is None:
        out_path = sd / f"fact_track__{slug}__{sha[:16]}.json"
    else:
        out_path = Path(companion_path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    merged: dict[str, Any] = dict(result)
    merged["companion_artifact_path"] = str(out_path)
    return merged


def _turn_anchor(row: dict[str, Any], row_index: int) -> dict[str, Any]:
    path = row.get("_path")
    return {
        "row_index": row_index,
        "round_number": int(row.get("round_number", 0) or 0),
        "turn_number": int(row.get("turn_number", 0) or 0),
        "bot_name": str(row.get("bot_name", "") or ""),
        "path": str(path) if path is not None else "",
    }
