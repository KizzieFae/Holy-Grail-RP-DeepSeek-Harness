"""Issue #81 Slice C — excursion reintegration (continuity-authoritative, atomic)."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from continuity_audit_origin import (
    CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_OOR_REINTEGRATION,
)
from continuity_state import (
    ExcursionRecord,
    ExcursionStatus,
    IssueState,
    IssueStatus,
    PublicEvent,
    ResolvedOutcome,
)

MAX_REINTEGRATION_COMMIT_ID_LEN = 128
_COMMIT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

_REINTEGRATION_TOP_KEYS = frozenset(
    {"reintegration_commit_id", "events", "issues", "resolved_outcomes"}
)
_EVENT_KEYS = frozenset(
    {
        "summary",
        "event_type",
        "significance",
        "participants",
        "state_changes",
        "actionable_implications",
        "grounding_markers",
        "known_by",
        "observed_by",
    }
)
_SIGNIFICANCE = frozenset({"minor", "major", "pivotal"})


def _err() -> Any:
    from continuity_mutation_pipeline import ContinuityMutationError

    return ContinuityMutationError


def normalize_reintegration_commit_id(value: Any) -> str:
    Exc = _err()
    if not isinstance(value, str):
        raise Exc("reintegration.reintegration_commit_id must be a string")
    s = value.strip()
    if not s:
        raise Exc("reintegration.reintegration_commit_id must be non-empty")
    if len(s) > MAX_REINTEGRATION_COMMIT_ID_LEN:
        raise Exc("reintegration.reintegration_commit_id exceeds maximum length")
    if _COMMIT_ID_RE.match(s) is None:
        raise Exc(
            "reintegration.reintegration_commit_id must match [A-Za-z0-9_-]{1,128}"
        )
    return s


def extract_and_validate_reintegration_block(
    raw_excursion: dict[str, Any],
    *,
    operation: str,
) -> Optional[dict[str, Any]]:
    """Return normalized reintegration dict or None. Raises ContinuityMutationError."""
    Exc = _err()
    if "reintegration" not in raw_excursion:
        return None
    if operation != "close":
        raise Exc("reintegration is only allowed on excursion_lifecycle.operation close")
    r = raw_excursion.get("reintegration")
    if r is None:
        return None
    if not isinstance(r, dict):
        raise Exc("excursion_lifecycle.reintegration must be an object")
    extra = set(r.keys()) - _REINTEGRATION_TOP_KEYS
    if extra:
        raise Exc(f"reintegration has unknown keys: {sorted(extra)}")
    commit_id = normalize_reintegration_commit_id(r.get("reintegration_commit_id"))
    events = _parse_events_v1(r.get("events"))
    issues = _parse_issues_v1(r.get("issues"))
    outcomes = _parse_outcomes_v1(r.get("resolved_outcomes"))
    return {
        "reintegration_commit_id": commit_id,
        "events": events,
        "issues": issues,
        "resolved_outcomes": outcomes,
    }


def _parse_events_v1(raw: Any) -> list[dict[str, Any]]:
    Exc = _err()
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise Exc("reintegration.events must be a list")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise Exc(f"reintegration.events[{i}] must be an object")
        xk = set(item.keys()) - _EVENT_KEYS
        if xk:
            raise Exc(f"reintegration.events[{i}] unknown keys: {sorted(xk)}")
        summary = item.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise Exc(f"reintegration.events[{i}].summary must be a non-empty string")
        parts = item.get("participants")
        if not isinstance(parts, list) or not parts:
            raise Exc(f"reintegration.events[{i}].participants must be a non-empty list")
        pl: list[str] = []
        for p in parts:
            if not isinstance(p, str) or not p.strip():
                raise Exc(
                    f"reintegration.events[{i}].participants must be non-empty strings"
                )
            pl.append(p.strip())
        et = str(item.get("event_type", "reintegration") or "reintegration").strip()
        sig = str(item.get("significance", "minor") or "minor").strip().lower()
        if sig not in _SIGNIFICANCE:
            raise Exc(f"reintegration.events[{i}].significance must be minor|major|pivotal")

        def _str_list(key: str) -> list[str]:
            v = item.get(key)
            if v is None:
                return []
            if not isinstance(v, list):
                raise Exc(f"reintegration.events[{i}].{key} must be a list")
            o2: list[str] = []
            for x in v:
                if not isinstance(x, str):
                    raise Exc(f"reintegration.events[{i}].{key} entries must be strings")
                if x.strip():
                    o2.append(x.strip())
            return o2

        kb = _str_list("known_by")
        ob = _str_list("observed_by")
        if not kb:
            kb = list(pl)
        if not ob:
            ob = list(pl)
        out.append(
            {
                "summary": summary.strip(),
                "event_type": et or "reintegration",
                "significance": sig,
                "participants": pl,
                "state_changes": _str_list("state_changes"),
                "actionable_implications": _str_list("actionable_implications"),
                "grounding_markers": _str_list("grounding_markers"),
                "known_by": kb,
                "observed_by": ob,
            }
        )
    return out


def _parse_issues_v1(raw: Any) -> list[dict[str, Any]]:
    Exc = _err()
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise Exc("reintegration.issues must be a list")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise Exc(f"reintegration.issues[{i}] must be an object")
        op = item.get("operation")
        if not isinstance(op, str):
            raise Exc(f"reintegration.issues[{i}].operation must be a string")
        opn = op.strip().lower()
        if opn not in ("create", "resolve"):
            raise Exc("reintegration.issues[].operation must be create or resolve")
        iid = item.get("issue_id")
        if not isinstance(iid, str) or not iid.strip():
            raise Exc(f"reintegration.issues[{i}].issue_id must be a non-empty string")
        iid = iid.strip()
        if opn == "create":
            desc = item.get("description")
            if not isinstance(desc, str) or not desc.strip():
                raise Exc(
                    f"reintegration.issues[{i}].description required for create"
                )
            parts = item.get("participants")
            if not isinstance(parts, list) or not parts:
                raise Exc(
                    f"reintegration.issues[{i}].participants required for create"
                )
            pl = [str(p).strip() for p in parts if str(p or "").strip()]
            if not pl:
                raise Exc(
                    f"reintegration.issues[{i}].participants must be non-empty"
                )
            raw_st = item.get("status", IssueStatus.ACTIVE.value)
            if isinstance(raw_st, IssueStatus):
                st = raw_st
            else:
                st_raw = str(raw_st or "").strip().lower()
                try:
                    st = IssueStatus(st_raw)
                except ValueError as exc:
                    raise Exc(
                        f"reintegration.issues[{i}].status invalid: {raw_st!r}"
                    ) from exc
            out.append(
                {
                    "operation": "create",
                    "issue_id": iid,
                    "description": desc.strip(),
                    "participants": pl,
                    "status": st,
                }
            )
        else:
            out.append({"operation": "resolve", "issue_id": iid})
    return out


def _parse_outcomes_v1(raw: Any) -> list[dict[str, Any]]:
    Exc = _err()
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise Exc("reintegration.resolved_outcomes must be a list")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise Exc(f"reintegration.resolved_outcomes[{i}] must be an object")
        allowed = frozenset(
            {
                "outcome_id",
                "category",
                "key",
                "subject_id",
                "value",
                "aspect_id",
                "slot_key",
                "status",
                "source_event_id",
                "source_issue_id",
                "rule_id",
            }
        )
        xk = set(item.keys()) - allowed
        if xk:
            raise Exc(
                f"reintegration.resolved_outcomes[{i}] unknown keys: {sorted(xk)}"
            )
        oid = item.get("outcome_id")
        if not isinstance(oid, str) or not oid.strip():
            raise Exc(
                f"reintegration.resolved_outcomes[{i}].outcome_id must be a string"
            )
        oid = oid.strip()
        if oid in seen:
            raise Exc("reintegration duplicate outcome_id in payload")
        seen.add(oid)
        cat = item.get("category")
        key = item.get("key")
        sub = item.get("subject_id")
        if not isinstance(cat, str) or not cat.strip():
            raise Exc(f"reintegration.resolved_outcomes[{i}].category required")
        if not isinstance(key, str) or not key.strip():
            raise Exc(f"reintegration.resolved_outcomes[{i}].key required")
        if not isinstance(sub, str) or not sub.strip():
            raise Exc(f"reintegration.resolved_outcomes[{i}].subject_id required")
        val = item.get("value")
        if not isinstance(val, dict):
            raise Exc(f"reintegration.resolved_outcomes[{i}].value must be an object")
        v2: dict[str, str] = {}
        for vk, vv in val.items():
            if not isinstance(vk, str):
                raise Exc("reintegration outcome value keys must be strings")
            v2[vk] = str(vv) if vv is not None else ""
        asp = str(item.get("aspect_id", "") or "").strip()
        sk = str(item.get("slot_key", "") or "").strip()
        if not asp or not sk:
            raise Exc(
                f"reintegration.resolved_outcomes[{i}] requires aspect_id and slot_key"
            )
        out.append(
            {
                "outcome_id": oid,
                "category": cat.strip(),
                "key": key.strip(),
                "subject_id": sub.strip(),
                "value": v2,
                "aspect_id": asp,
                "slot_key": sk,
                "status": str(item.get("status", "active") or "active"),
                "source_event_id": str(item.get("source_event_id", "") or ""),
                "source_issue_id": item.get("source_issue_id"),
                "rule_id": str(item.get("rule_id", "") or ""),
            }
        )
    return out


def validate_close_reintegration_globally(
    *,
    excursion_id: str,
    reintegration: Optional[dict[str, Any]],
    continuity_manager: Any,
) -> None:
    """Validation phase: no writes."""
    Exc = _err()
    if reintegration is None:
        return
    eid = excursion_id
    ex_store = getattr(continuity_manager, "excursions", {}) or {}
    rec = ex_store.get(eid)
    if rec is None:
        raise Exc(f"unknown excursion_id: {eid!r}")
    commit_id = reintegration["reintegration_commit_id"]
    applied = getattr(rec, "reintegration_commit_id_applied", None)
    if applied == commit_id:
        return
    if applied is not None and applied != commit_id:
        raise Exc(
            "reintegration_commit_id conflicts with already-applied reintegration "
            f"for excursion {eid!r}"
        )
    st = getattr(rec, "status", None)
    if st == ExcursionStatus.ACTIVE:
        return
    if st == ExcursionStatus.CLOSED and applied is None:
        return
    raise Exc("invalid excursion state for reintegration")


@dataclass(frozen=True)
class _PreparedReintegration:
    events: list[PublicEvent]
    issue_creates: list[dict[str, Any]]
    issue_resolves: list[str]
    outcomes: list[ResolvedOutcome]


def _prepare_bundle(
    *,
    manager: Any,
    excursion_id: str,
    reintegration: dict[str, Any],
    turn_index: int,
    timestamp: datetime,
) -> _PreparedReintegration:
    Exc = _err()
    commit_id = reintegration["reintegration_commit_id"]
    evs: list[PublicEvent] = []
    for i, ed in enumerate(reintegration["events"]):
        eid_ev = (
            f"evt_reintegration_{excursion_id[:24]}_{commit_id[:16]}_{i}_{turn_index}"
        )
        evs.append(
            PublicEvent(
                event_id=eid_ev,
                timestamp=timestamp,
                event_type=ed["event_type"],
                participants=list(ed["participants"]),
                summary=ed["summary"],
                turn_index=turn_index,
                location=(
                    manager.scene_state.location if manager.scene_state else None
                ),
                significance=ed["significance"],
                observed_by=list(ed["observed_by"]),
                known_by=list(ed["known_by"]),
                state_changes=list(ed["state_changes"]),
                actionable_implications=list(ed["actionable_implications"]),
                grounding_markers=list(ed["grounding_markers"]),
            )
        )
    creates: list[dict[str, Any]] = []
    resolves: list[str] = []
    existing_o = {o.outcome_id for o in getattr(manager, "resolved_outcomes", [])}
    for op in reintegration["issues"]:
        if op["operation"] == "create":
            iid = op["issue_id"]
            if iid in getattr(manager, "issues", {}):
                raise Exc(f"reintegration issue create conflicts with existing {iid!r}")
            creates.append(op)
        else:
            iid = op["issue_id"]
            issues = getattr(manager, "issues", {})
            if iid not in issues:
                raise Exc(f"reintegration resolve unknown issue_id {iid!r}")
            if issues[iid].status == IssueStatus.RESOLVED:
                raise Exc(f"reintegration resolve issue already resolved {iid!r}")
            resolves.append(iid)
    outcomes: list[ResolvedOutcome] = []
    for od in reintegration["resolved_outcomes"]:
        oid = od["outcome_id"]
        if oid in existing_o:
            raise Exc(f"reintegration outcome_id already exists {oid!r}")
        existing_o.add(oid)
        outcomes.append(
            ResolvedOutcome(
                outcome_id=oid,
                category=od["category"],
                key=od["key"],
                subject_id=od["subject_id"],
                value=dict(od["value"]),
                status=od["status"],
                source_event_id=od["source_event_id"],
                source_issue_id=(
                    str(od["source_issue_id"])
                    if od.get("source_issue_id") is not None
                    else None
                ),
                rule_id=od["rule_id"],
                created_turn_index=turn_index,
                aspect_id=od["aspect_id"],
                slot_key=od["slot_key"],
            )
        )
    return _PreparedReintegration(
        events=evs,
        issue_creates=creates,
        issue_resolves=resolves,
        outcomes=outcomes,
    )


def _snapshot_excursion(rec: ExcursionRecord) -> dict[str, Any]:
    return {
        "status": rec.status,
        "closed_at_turn": rec.closed_at_turn,
        "reintegration_commit_id_applied": rec.reintegration_commit_id_applied,
    }


def _restore_excursion(rec: ExcursionRecord, snap: dict[str, Any]) -> None:
    rec.status = snap["status"]
    rec.closed_at_turn = snap["closed_at_turn"]
    rec.reintegration_commit_id_applied = snap["reintegration_commit_id_applied"]


def apply_excursion_close_reintegration_mutation(
    manager: Any,
    excursion_id: str,
    payload: dict[str, Any],
    *,
    commit_turn_index: int,
    timestamp: datetime,
) -> None:
    """Commit phase: close + merge + identity, with rollback on failure."""
    Exc = _err()
    prev_inside = getattr(manager, "_continuity_in_reintegration_apply", False)
    manager._continuity_in_reintegration_apply = True
    try:
        reint = payload.get("reintegration")
        if reint is None:
            if not getattr(manager, "_continuity_pipeline_turn_active", False):
                manager._record_continuity_audit_event(
                    CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_OOR_REINTEGRATION,
                    int(commit_turn_index),
                )
            manager.close_excursion(excursion_id, closed_at_turn=commit_turn_index)
            return

        eid = excursion_id
        rec = manager.excursions.get(eid)
        if rec is None:
            raise Exc(f"unknown excursion_id: {eid!r}")
        commit_id = reint["reintegration_commit_id"]

        if (
            rec.status == ExcursionStatus.CLOSED
            and rec.reintegration_commit_id_applied == commit_id
        ):
            return

        if not getattr(manager, "_continuity_pipeline_turn_active", False):
            manager._record_continuity_audit_event(
                CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_OOR_REINTEGRATION,
                int(commit_turn_index),
            )

        bundle = _prepare_bundle(
            manager=manager,
            excursion_id=eid,
            reintegration=reint,
            turn_index=commit_turn_index,
            timestamp=timestamp,
        )

        pe_len = len(manager.public_events)
        ro_len = len(manager.resolved_outcomes)
        recent_ids = (
            list(manager.scene_state.recent_event_ids)
            if manager.scene_state is not None
            else []
        )
        event_ctr = int(getattr(manager, "event_counter", 0))
        issues_snap = {
            k: copy.deepcopy(v)
            for k, v in manager.issues.items()
            if k in {c["issue_id"] for c in bundle.issue_creates}
            or k in set(bundle.issue_resolves)
        }
        active_ids_snap = (
            list(manager.scene_state.active_issue_ids)
            if manager.scene_state is not None
            else []
        )
        ex_snap = _snapshot_excursion(rec)
        created_issue_ids: list[str] = []

        try:
            if rec.status == ExcursionStatus.ACTIVE:
                manager.close_excursion(eid, closed_at_turn=commit_turn_index)

            for ev in bundle.events:
                manager.public_events.append(ev)
                manager.event_counter = int(manager.event_counter) + 1
                if manager.scene_state is not None:
                    manager.scene_state.recent_event_ids.append(ev.event_id)
                    manager.scene_state.recent_event_ids = (
                        manager.scene_state.recent_event_ids[-10:]
                    )

            for c in bundle.issue_creates:
                iid = c["issue_id"]
                manager.issues[iid] = IssueState(
                    issue_id=iid,
                    description=c["description"],
                    participants=list(c["participants"]),
                    status=c["status"],
                    created_at=timestamp,
                    last_updated=timestamp,
                    last_turn_index=commit_turn_index,
                )
                created_issue_ids.append(iid)
                if manager.scene_state is not None:
                    if iid not in manager.scene_state.active_issue_ids:
                        manager.scene_state.active_issue_ids.append(iid)

            for iid in bundle.issue_resolves:
                issue = manager.issues[iid]
                issue.status = IssueStatus.RESOLVED
                issue.resolved_at = timestamp
                issue.last_updated = timestamp
                issue.last_turn_index = commit_turn_index

            if manager.scene_state is not None:
                manager.scene_state.active_issue_ids = [
                    x
                    for x in manager.scene_state.active_issue_ids
                    if x in manager.issues
                    and manager.issues[x].status
                    in (IssueStatus.ACTIVE, IssueStatus.ESCALATING)
                ]

            for out in bundle.outcomes:
                manager.resolved_outcomes.append(out)

            rec.reintegration_commit_id_applied = commit_id
        except Exception:
            manager.public_events[:] = manager.public_events[:pe_len]
            manager.resolved_outcomes[:] = manager.resolved_outcomes[:ro_len]
            manager.event_counter = event_ctr
            if manager.scene_state is not None:
                manager.scene_state.recent_event_ids = recent_ids
                manager.scene_state.active_issue_ids = active_ids_snap
            for iid in created_issue_ids:
                manager.issues.pop(iid, None)
            for k, v in issues_snap.items():
                manager.issues[k] = v
            _restore_excursion(rec, ex_snap)
            manager._resync_presence_through_authority()
            raise
    finally:
        manager._continuity_in_reintegration_apply = prev_inside


def validate_reintegration_move_shape(move: dict[str, Any] | None) -> tuple[bool, str]:
    """Non-throwing structural check for bot validation."""
    if not move or not isinstance(move, dict):
        return True, ""
    raw = move.get("excursion_lifecycle")
    if not isinstance(raw, dict) or "reintegration" not in raw:
        return True, ""
    try:
        op = raw.get("operation")
        if not isinstance(op, str):
            return False, "[REINTEGRATION] excursion_lifecycle.operation required"
        extract_and_validate_reintegration_block(raw, operation=op.strip().lower())
    except Exception as exc:
        return False, f"[REINTEGRATION] {exc!s}"
    return True, ""
