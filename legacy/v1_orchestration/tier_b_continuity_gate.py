"""Deterministic Tier B continuity-grounded gate (GitHub #214).

Inspects character ``*_full.json`` audits for committed excursion lifecycle and
``SceneState`` mirror fields — **not** Tier A perception/v2 speech and not
perception redaction as proof (#216 closed; Tier B uses continuity artifacts only).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TierBContinuityGateError(RuntimeError):
    """Raised when a Tier B continuity-grounded audit session fails deterministic checks."""


def _scan_character_full_audits(session_root: Path) -> list[Path]:
    return sorted(session_root.rglob("audit_*_*_full.json"))


def _sort_audit_rows(paths: list[Path]) -> list[tuple[Path, dict[str, Any]]]:
    rows: list[tuple[tuple[int, int, str], Path, dict[str, Any]]] = []
    for path in paths:
        if "_narrator_" in path.name:
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if str(raw.get("bot_type") or "") != "character":
            continue
        if not isinstance(raw, dict):
            continue
        rn = int(raw.get("round_number") or 0)
        tn = int(raw.get("turn_number") or 0)
        rows.append(((rn, tn, path.name), path, raw))
    rows.sort(key=lambda x: x[0])
    return [(p, r) for _k, p, r in rows]


def _excursion_status_for_id(digest: Any, excursion_id: str) -> str | None:
    if not isinstance(digest, list):
        return None
    eid = str(excursion_id or "").strip()
    for row in digest:
        if not isinstance(row, dict):
            continue
        if str(row.get("excursion_id") or "").strip() == eid:
            return str(row.get("status") or "").strip().lower()
    return None


def _scene_state_participation_restored(
    scene_state_after: dict[str, Any], participant: str
) -> tuple[bool, str | None]:
    """Return (ok, reason) for focal participation mirrors after excursion close (#216)."""
    if not participant:
        return False, "empty participant id"
    present = scene_state_after.get("present_characters")
    if not isinstance(present, list):
        return False, "present_characters missing or not a list"
    names = [str(x).strip() for x in present if str(x or "").strip()]
    if participant not in names:
        return False, "participant not in present_characters"

    off = scene_state_after.get("offstage_characters")
    if isinstance(off, list):
        off_names = {str(x).strip() for x in off if str(x or "").strip()}
        if participant in off_names:
            return False, "participant appears in offstage_characters while present"

    cps = scene_state_after.get("character_presence_status")
    if isinstance(cps, dict):
        stt = str(cps.get(participant) or "").strip().lower()
        if stt in ("temporary_offstage", "departed"):
            return False, f"character_presence_status[{participant!r}] is {stt!r}"

    return True, None


def _analyze_tier_b_session(session_dir: Path) -> tuple[list[str], dict[str, Any]]:
    root = session_dir.resolve()
    errors: list[str] = []
    if not root.is_dir():
        return [f"session dir not found: {root}"], {}

    manifest_path = root / "_manifest.json"
    if not manifest_path.is_file():
        errors.append("missing _manifest.json (Tier B gate requires session manifest)")
        return errors, {}

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"_manifest.json: invalid JSON ({exc})"], {}

    meta = manifest.get("audit_scenario_metadata")
    if not isinstance(meta, dict):
        errors.append("manifest missing audit_scenario_metadata object")
        return errors, {}

    tier = str(meta.get("audit_validation_tier") or "").strip().lower()
    if tier != "tier_b_continuity_grounded":
        errors.append(
            f"manifest audit_validation_tier is {tier!r}, expected 'tier_b_continuity_grounded'"
        )

    gate = meta.get("tier_b_continuity_gate")
    if not isinstance(gate, dict):
        errors.append("manifest missing tier_b_continuity_gate object")
        return errors, {}

    excursion_id = str(gate.get("excursion_id") or "").strip()
    participant = str(gate.get("excursion_participant_agent") or "").strip()
    if not excursion_id or not participant:
        errors.append("tier_b_continuity_gate missing excursion_id or excursion_participant_agent")
        return errors, {}

    audit_rows = _sort_audit_rows(_scan_character_full_audits(root))
    if not audit_rows:
        errors.append("no character *_full.json rows found under session")
        return errors, {"excursion_id": excursion_id, "participant": participant}

    saw_digest = False
    saw_pipeline_turn = False
    statuses_in_order: list[str] = []
    participation_restored_after_close = False
    closed_mirror_checked_rows = 0

    for path, row in audit_rows:
        md = row.get("metadata")
        if not isinstance(md, dict):
            md = {}
        origin = md.get("continuity_audit_origin")
        if isinstance(origin, dict) and str(origin.get("kind") or "").strip() == "pipeline_turn":
            saw_pipeline_turn = True

        digest = md.get("excursion_audit_digest_v1")
        st = _excursion_status_for_id(digest, excursion_id)
        if isinstance(digest, list) and digest:
            saw_digest = True

        if st:
            statuses_in_order.append(st)

        ctx = row.get("context_snapshot")
        if st == "active" and isinstance(ctx, dict):
            ss = ctx.get("scene_state_after")
            if isinstance(ss, dict):
                present = ss.get("present_characters")
                names = (
                    [str(x).strip() for x in present if str(x or "").strip()]
                    if isinstance(present, list)
                    else []
                )
                if participant in names:
                    errors.append(
                        f"{path.name}: excursion active for {excursion_id!r} but "
                        f"scene_state_after.present_characters still includes participant "
                        f"{participant!r}"
                    )

        if st == "closed" and isinstance(ctx, dict):
            ss = ctx.get("scene_state_after")
            if isinstance(ss, dict):
                closed_mirror_checked_rows += 1
                ok_rest, reason = _scene_state_participation_restored(ss, participant)
                if ok_rest:
                    participation_restored_after_close = True
                elif reason:
                    errors.append(
                        f"{path.name}: excursion closed for {excursion_id!r} but "
                        f"scene_state_after does not show restored focal participation "
                        f"for {participant!r} ({reason})"
                    )

    if not saw_digest:
        errors.append(
            "no non-empty metadata.excursion_audit_digest_v1 on character rows — "
            "cannot prove excursion lifecycle (perception-only / redaction-only is insufficient)"
        )

    if not saw_pipeline_turn:
        errors.append(
            "no character row with metadata.continuity_audit_origin.kind=='pipeline_turn' "
            "(continuity must commit via process_turn / #81 pipeline)"
        )

    if "active" not in statuses_in_order:
        errors.append(
            f"excursion {excursion_id!r} never reached active status in per-turn digest timeline"
        )
    if "closed" not in statuses_in_order:
        errors.append(
            f"excursion {excursion_id!r} never reached closed status in per-turn digest timeline"
        )
    first_active_i: int | None = None
    first_closed_i: int | None = None
    for i, s in enumerate(statuses_in_order):
        if s == "active" and first_active_i is None:
            first_active_i = i
        if s == "closed" and first_closed_i is None:
            first_closed_i = i

    if first_active_i is not None and first_closed_i is not None and first_closed_i <= first_active_i:
        errors.append(
            "excursion digest timeline does not show closed strictly after the first active beat"
        )

    if "closed" in statuses_in_order and not participation_restored_after_close:
        if closed_mirror_checked_rows == 0:
            errors.append(
                "excursion reached closed in digest but no character audit row includes "
                "context_snapshot.scene_state_after for mirror checks (Tier B full lifecycle)"
            )

    ctar_excursion_signals = 0
    for _path, row in audit_rows:
        md = row.get("metadata")
        if not isinstance(md, dict):
            continue
        ctar = md.get("ctar")
        if not isinstance(ctar, dict):
            continue
        # Shallow hint only — optional corroboration
        blob = json.dumps(ctar, ensure_ascii=False)
        if "excursion" in blob.lower() or "EXCURSION" in blob:
            ctar_excursion_signals += 1

    report_meta: dict[str, Any] = {
        "excursion_id": excursion_id,
        "participant": participant,
        "character_rows_scanned": len(audit_rows),
        "digest_status_timeline": list(statuses_in_order),
        "participation_restored_after_close": participation_restored_after_close,
        "closed_mirror_checked_rows": closed_mirror_checked_rows,
        "ctar_excursion_hint_rows": ctar_excursion_signals,
    }
    return errors, report_meta


def validate_tier_b_continuity_grounded_session(session_dir: Path) -> dict[str, Any]:
    """Validate Tier B continuity evidence under ``session_dir``.

    Raises:
        TierBContinuityGateError: on any validation failure.
    """
    errors, meta = _analyze_tier_b_session(session_dir)
    report: dict[str, Any] = {"ok": not errors, "errors": errors, **meta}
    if errors:
        raise TierBContinuityGateError(
            "Tier B continuity gate failed:\n- " + "\n- ".join(errors)
        )
    return report


def validate_tier_b_continuity_grounded_session_report_only(
    session_dir: Path,
) -> dict[str, Any]:
    """Same analysis as :func:`validate_tier_b_continuity_grounded_session` but never raises."""
    errors, meta = _analyze_tier_b_session(session_dir)
    return {"ok": not errors, "errors": errors, **meta}
