"""Read-only unified turn/commit forensic navigator (#101)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from investigation._ni_forensics import NiSession, ni_cli_handoff
from investigation._plot_cognition_forensics import resolve_scope

TURN_INVESTIGATOR_SCHEMA = "hg_turn_investigator_v1"
V2_HOST_METADATA_KEY = "v2_host_state"

ViewKind = Literal["commit", "round"]

AUTHORITY_AUTHORITATIVE = "authoritative"
AUTHORITY_OBSERVATIONAL = "observational"
AUTHORITY_FORENSIC = "forensic"
AUTHORITY_MEDIATED = "mediated"
AUTHORITY_DERIVED = "derived"
AUTHORITY_ADVISORY = "advisory"
AUTHORITY_REBUILDABLE = "rebuildable"


def limitation(
    code: str,
    message: str,
    *,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {"code": code, "message": message}
    if detail:
        item["detail"] = detail
    return item


def _sorted_unique_str(values: list[str]) -> list[str]:
    return sorted({str(item) for item in values if str(item or "").strip()})


def _sorted_unique_int(values: list[int]) -> list[int]:
    return sorted({int(item) for item in values})


def _surface_sort_key(surface: dict[str, Any]) -> tuple[str, str]:
    return (str(surface.get("contract") or ""), str(surface.get("reference") or ""))


def _limitation_sort_key(item: dict[str, Any]) -> tuple[str, str]:
    return (str(item.get("code") or ""), str(item.get("message") or ""))


def _conflict_sort_key(item: dict[str, Any]) -> tuple[str, str]:
    return (str(item.get("field") or ""), str(item.get("note") or ""))


@dataclass
class TurnForensicsPaths:
    sessions_root: Path
    evidence_root: Path
    tags_root: Path
    story_knowledge_root: Path
    plot_cognition_root: Path


@dataclass
class ResolvedAnchors:
    hg_round_id: str | None = None
    domain_commit_ids: list[str] = field(default_factory=list)
    continuity_turn_indexes: list[int] = field(default_factory=list)
    entry_ids: list[str] = field(default_factory=list)
    memory_scope_id: str | None = None
    plot_cognition_scope_id: str | None = None


@dataclass
class TurnForensicsSession:
    hg_session_id: str
    paths: TurnForensicsPaths
    session_data: dict[str, Any] = field(default_factory=dict)
    _evidence_index: dict[str, Any] | None = None
    _evidence_index_error: str | None = None

    @classmethod
    def open(
        cls,
        hg_session_id: str,
        *,
        sessions_root: Path,
        evidence_root: Path,
        tags_root: Path,
        story_knowledge_root: Path,
        plot_cognition_root: Path,
    ) -> TurnForensicsSession:
        session = cls(
            hg_session_id=hg_session_id,
            paths=TurnForensicsPaths(
                sessions_root=sessions_root,
                evidence_root=evidence_root,
                tags_root=tags_root,
                story_knowledge_root=story_knowledge_root,
                plot_cognition_root=plot_cognition_root,
            ),
        )
        session._load_session()
        session._load_evidence_index()
        return session

    def _session_path(self) -> Path:
        return self.paths.sessions_root / f"{self.hg_session_id}.json"

    def _load_session(self) -> None:
        path = self._session_path()
        if not path.is_file():
            raise FileNotFoundError(f"Session not found: {path}")
        self.session_data = json.loads(path.read_text(encoding="utf-8"))

    def _load_evidence_index(self) -> None:
        index_path = self.paths.evidence_root / self.hg_session_id / "index.json"
        if not index_path.is_file():
            self._evidence_index = None
            return
        try:
            self._evidence_index = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self._evidence_index = None
            self._evidence_index_error = str(exc)

    @property
    def metadata(self) -> dict[str, Any]:
        return dict(self.session_data.get("metadata") or {})

    @property
    def host_state(self) -> dict[str, Any]:
        return dict(self.metadata.get(V2_HOST_METADATA_KEY) or {})

    @property
    def continuity_state(self) -> dict[str, Any]:
        return dict(self.metadata.get("continuity_state") or {})

    @property
    def rp_history(self) -> list[dict[str, Any]]:
        return list(self.host_state.get("rp_history") or [])

    @property
    def commit_ids(self) -> list[str]:
        return [str(item) for item in self.host_state.get("commit_ids") or []]

    def memory_scope_id(self) -> str | None:
        value = str(self.host_state.get("memory_scope_id") or "").strip()
        return value or None

    def plot_cognition_scope_id(self) -> str | None:
        value = str(self.host_state.get("plot_cognition_scope_id") or "").strip()
        return value or None

    def turn_metadata(self, continuity_turn_index: int) -> dict[str, Any]:
        bucket = self.continuity_state.get("turn_metadata_by_index") or {}
        return dict(bucket.get(str(continuity_turn_index)) or bucket.get(continuity_turn_index) or {})

    def public_events_for_turn(self, continuity_turn_index: int) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for event in self.continuity_state.get("public_events") or []:
            if not isinstance(event, dict):
                continue
            turn_index = event.get("turn_index")
            if turn_index is not None and int(turn_index) == int(continuity_turn_index):
                events.append(event)
        return events

    def history_entries_for_commit(self, domain_commit_id: str) -> list[dict[str, Any]]:
        commit_id = str(domain_commit_id)
        return [
            entry
            for entry in self.rp_history
            if str(entry.get("domain_commit_id") or "") == commit_id
        ]

    def history_entries_for_round(self, hg_round_id: str) -> list[dict[str, Any]]:
        round_id = str(hg_round_id)
        return [
            entry
            for entry in self.rp_history
            if str(entry.get("hg_round_id") or "") == round_id
        ]

    def committed_turn_for_commit(self, domain_commit_id: str) -> dict[str, Any] | None:
        for entry in self.rp_history:
            if entry.get("kind") != "committed_turn":
                continue
            if str(entry.get("domain_commit_id") or "") == str(domain_commit_id):
                return entry
        return None

    def continuity_turn_index_for_commit(self, domain_commit_id: str) -> int | None:
        entry = self.committed_turn_for_commit(domain_commit_id)
        if not entry:
            return None
        meta = dict(entry.get("metadata") or {})
        turn_index = meta.get("continuity_turn_index")
        return int(turn_index) if turn_index is not None else None

    def domain_commit_ids_for_round(self, hg_round_id: str) -> list[str]:
        commits: list[tuple[int, str]] = []
        for entry in self.rp_history:
            if entry.get("kind") != "committed_turn":
                continue
            if str(entry.get("hg_round_id") or "") != str(hg_round_id):
                continue
            commit_id = str(entry.get("domain_commit_id") or "").strip()
            if not commit_id:
                continue
            seq = int(entry.get("sequence_index") or 0)
            commits.append((seq, commit_id))
        commits.sort(key=lambda item: item[0])
        return _sorted_unique_str([commit_id for _, commit_id in commits])

    def resolve_commit_anchor(self, domain_commit_id: str) -> tuple[ResolvedAnchors, list[dict[str, Any]], ViewKind]:
        commit_id = str(domain_commit_id).strip()
        limitations: list[dict[str, Any]] = []
        if commit_id not in self.commit_ids and not self.committed_turn_for_commit(commit_id):
            limitations.append(
                limitation(
                    "correlation_incomplete",
                    f"domain_commit_id {commit_id!r} not found in session commit history",
                    detail={"field": "domain_commit_id", "contract": "session"},
                )
            )
        committed = self.committed_turn_for_commit(commit_id)
        turn_index = self.continuity_turn_index_for_commit(commit_id)
        hg_round_id = str(committed.get("hg_round_id") or "") if committed else ""
        entry_ids = _sorted_unique_str(
            [str(entry.get("entry_id") or "") for entry in self.history_entries_for_commit(commit_id)]
        )
        resolved = ResolvedAnchors(
            hg_round_id=hg_round_id or None,
            domain_commit_ids=[commit_id] if commit_id else [],
            continuity_turn_indexes=[turn_index] if turn_index is not None else [],
            entry_ids=entry_ids,
            memory_scope_id=self.memory_scope_id(),
            plot_cognition_scope_id=self.plot_cognition_scope_id(),
        )
        return resolved, limitations, "commit"

    def resolve_round_anchor(self, hg_round_id: str) -> tuple[ResolvedAnchors, list[dict[str, Any]], ViewKind]:
        round_id = str(hg_round_id).strip()
        limitations: list[dict[str, Any]] = []
        history = self.history_entries_for_round(round_id)
        if not history and not self._round_attempt_ids(round_id):
            limitations.append(
                limitation(
                    "correlation_incomplete",
                    f"hg_round_id {round_id!r} not found in durable session or execution evidence",
                    detail={"field": "hg_round_id", "contract": "session"},
                )
            )
        domain_commit_ids = self.domain_commit_ids_for_round(round_id)
        turn_indexes: list[int] = []
        entry_ids = _sorted_unique_str([str(entry.get("entry_id") or "") for entry in history])
        for commit_id in domain_commit_ids:
            turn_index = self.continuity_turn_index_for_commit(commit_id)
            if turn_index is not None:
                turn_indexes.append(turn_index)
        resolved = ResolvedAnchors(
            hg_round_id=round_id,
            domain_commit_ids=domain_commit_ids,
            continuity_turn_indexes=_sorted_unique_int(turn_indexes),
            entry_ids=entry_ids,
            memory_scope_id=self.memory_scope_id(),
            plot_cognition_scope_id=self.plot_cognition_scope_id(),
        )
        return resolved, limitations, "round"

    def resolve_turn_anchor(self, continuity_turn_index: int) -> tuple[ResolvedAnchors, list[dict[str, Any]], ViewKind]:
        turn_index = int(continuity_turn_index)
        limitations: list[dict[str, Any]] = []
        commit_id: str | None = None
        hg_round_id: str | None = None
        for entry in self.rp_history:
            if entry.get("kind") != "committed_turn":
                continue
            meta = dict(entry.get("metadata") or {})
            if int(meta.get("continuity_turn_index") or -1) != turn_index:
                continue
            commit_id = str(entry.get("domain_commit_id") or "").strip() or None
            hg_round_id = str(entry.get("hg_round_id") or "").strip() or None
            break
        if commit_id is None:
            meta = self.turn_metadata(turn_index)
            if not meta:
                limitations.append(
                    limitation(
                        "correlation_incomplete",
                        f"continuity_turn_index {turn_index} has no committed_turn mapping",
                        detail={"field": "continuity_turn_index", "contract": "session"},
                    )
                )
            return (
                ResolvedAnchors(
                    continuity_turn_indexes=[turn_index],
                    memory_scope_id=self.memory_scope_id(),
                    plot_cognition_scope_id=self.plot_cognition_scope_id(),
                ),
                limitations,
                "commit",
            )
        return self.resolve_commit_anchor(commit_id)

    def resolve_entry_anchor(self, entry_id: str) -> tuple[ResolvedAnchors, list[dict[str, Any]], ViewKind]:
        entry_key = str(entry_id).strip()
        entry = next((item for item in self.rp_history if str(item.get("entry_id") or "") == entry_key), None)
        if entry is None:
            raise ValueError(f"entry_id not found: {entry_key}")
        commit_id = str(entry.get("domain_commit_id") or "").strip() or None
        round_id = str(entry.get("hg_round_id") or "").strip() or None
        if commit_id:
            resolved, limitations, _ = self.resolve_commit_anchor(commit_id)
            resolved.entry_ids = _sorted_unique_str([entry_key] + resolved.entry_ids)
            return resolved, limitations, "commit"
        limitations = [
            limitation(
                "correlation_incomplete",
                f"entry_id {entry_key!r} has no domain_commit_id; round-scoped correlation only",
                detail={"field": "domain_commit_id", "contract": "session_rp_history", "entry_id": entry_key},
            )
        ]
        if round_id:
            resolved, round_limits, view = self.resolve_round_anchor(round_id)
            resolved.entry_ids = _sorted_unique_str([entry_key] + resolved.entry_ids)
            return resolved, limitations + round_limits, view
        return (
            ResolvedAnchors(entry_ids=[entry_key], memory_scope_id=self.memory_scope_id()),
            limitations,
            "round",
        )

    def resolve_tag_anchor(self, tag_id: str) -> tuple[ResolvedAnchors, list[dict[str, Any]], ViewKind]:
        tag = self._load_tag(tag_id)
        if tag is None:
            raise ValueError(f"tag_id not found: {tag_id}")
        anchor = dict(tag.get("anchor") or {})
        commit_id = str(anchor.get("domain_commit_id") or "").strip() or None
        round_id = str(anchor.get("hg_round_id") or "").strip() or None
        entry_id = str(anchor.get("entry_id") or "").strip() or None
        if commit_id:
            resolved, limitations, view = self.resolve_commit_anchor(commit_id)
        elif round_id:
            resolved, limitations, view = self.resolve_round_anchor(round_id)
        else:
            resolved = ResolvedAnchors(memory_scope_id=self.memory_scope_id())
            limitations = [
                limitation(
                    "correlation_incomplete",
                    f"tag {tag_id!r} lacks commit and round anchors",
                    detail={"contract": "audit_tags", "tag_id": tag_id},
                )
            ]
            view = "round"
        if entry_id:
            resolved.entry_ids = _sorted_unique_str([entry_id] + resolved.entry_ids)
        return resolved, limitations, view

    def _load_tag(self, tag_id: str) -> dict[str, Any] | None:
        path = self.paths.tags_root / self.hg_session_id / "tags" / f"{tag_id}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _round_attempt_ids(self, hg_round_id: str | None) -> list[str]:
        if not self._evidence_index or not hg_round_id:
            return []
        rounds = self._evidence_index.get("rounds") or {}
        return list(rounds.get(str(hg_round_id)) or [])

    def _load_attempt(self, evidence_id: str) -> dict[str, Any] | None:
        path = self.paths.evidence_root / self.hg_session_id / "attempts" / f"{evidence_id}.json"
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def _execution_evidence_limitations(self) -> list[dict[str, Any]]:
        if self._evidence_index_error:
            return [
                limitation(
                    "evidence_corrupt",
                    "execution evidence index.json is unreadable",
                    detail={"contract": "execution_evidence", "error": self._evidence_index_error},
                )
            ]
        if self._evidence_index is None:
            return [
                limitation(
                    "evidence_missing",
                    "execution evidence store not present for session",
                    detail={"contract": "execution_evidence", "path": f"execution_evidence/{self.hg_session_id}/"},
                )
            ]
        return []

    def _ni_contract_limitation(self) -> dict[str, Any] | None:
        if self._evidence_index is None:
            return None
        ni = self._evidence_index.get("ni") or {}
        if ni.get("evidence_contract") != "hg_ni_forensics_v1":
            return limitation(
                "contract_unavailable",
                "NI forensic contract unavailable for this session evidence tree",
                detail={"contract": "ni_forensics"},
            )
        return None

    def _story_knowledge_records(
        self,
        *,
        domain_commit_id: str | None = None,
        event_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        scope_id = self.memory_scope_id()
        if not scope_id:
            return []
        path = self.paths.story_knowledge_root / scope_id / "records.jsonl"
        if not path.is_file():
            return []
        matches: list[dict[str, Any]] = []
        event_id_set = {str(item) for item in (event_ids or [])}
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            source_commit = str(record.get("source_domain_commit_id") or "")
            event_id = str(record.get("event_id") or "")
            if domain_commit_id and source_commit == str(domain_commit_id):
                matches.append({**record, "_line": line_no})
                continue
            if event_id and event_id in event_id_set:
                matches.append({**record, "_line": line_no})
        matches.sort(key=lambda item: (str(item.get("story_record_id") or item.get("event_id") or ""), int(item.get("_line") or 0)))
        return matches

    def _plot_cognition_records_for_commit(self, scope_id: str, domain_commit_id: str) -> list[str]:
        scope = resolve_scope(scope_id, forensics_root=self.paths.plot_cognition_root)
        if scope is None:
            return []
        index = scope.index()
        return list((index.get("by_commit") or {}).get(str(domain_commit_id)) or [])

    def _plot_cognition_records_for_round(self, scope_id: str, hg_round_id: str) -> list[str]:
        scope = resolve_scope(scope_id, forensics_root=self.paths.plot_cognition_root)
        if scope is None:
            return []
        record_ids: list[str] = []
        for record in scope.timeline():
            correlation = record.get("correlation") or {}
            if str(correlation.get("hg_round_id") or "") == str(hg_round_id):
                record_ids.append(str(record.get("record_id") or ""))
        return sorted(record_id for record_id in record_ids if record_id)

    def _librarian_audit_for_commit(self, domain_commit_id: str) -> dict[str, Any] | None:
        for entry in reversed(self.host_state.get("librarian_proposal_audit_log") or []):
            if str(entry.get("librarian_proposal_domain_commit_id") or "") == str(domain_commit_id):
                return dict(entry)
        return None

    def _surface(
        self,
        *,
        contract: str,
        authority: str,
        reference: str,
        correlation: dict[str, Any],
        establishes: str,
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "contract": contract,
            "authority": authority,
            "reference": reference,
            "correlation": correlation,
            "establishes": establishes,
            "summary": summary,
        }

    def surfaces_for_commit(self, resolved: ResolvedAnchors) -> list[dict[str, Any]]:
        surfaces: list[dict[str, Any]] = []
        commit_id = resolved.domain_commit_ids[0] if resolved.domain_commit_ids else None
        if not commit_id:
            return surfaces

        for entry in self.history_entries_for_commit(commit_id):
            entry_id = str(entry.get("entry_id") or "")
            surfaces.append(
                self._surface(
                    contract="session_rp_history",
                    authority=AUTHORITY_AUTHORITATIVE,
                    reference=f"data/sessions/{self.hg_session_id}.json#rp_history[{entry_id}]",
                    correlation={
                        "entry_id": entry_id,
                        "domain_commit_id": commit_id,
                        "hg_round_id": entry.get("hg_round_id"),
                        "sequence_index": entry.get("sequence_index"),
                    },
                    establishes="Canonical committed or presentation history row for this commit",
                    summary={
                        "kind": entry.get("kind"),
                        "actor_id": entry.get("actor_id"),
                        "content_excerpt": str(entry.get("content") or "")[:240],
                    },
                )
            )

        turn_index = resolved.continuity_turn_indexes[0] if resolved.continuity_turn_indexes else None
        if turn_index is not None:
            meta = self.turn_metadata(turn_index)
            if meta:
                surfaces.append(
                    self._surface(
                        contract="session_continuity",
                        authority=AUTHORITY_OBSERVATIONAL,
                        reference=(
                            f"data/sessions/{self.hg_session_id}.json#"
                            f"metadata.continuity_state.turn_metadata_by_index.{turn_index}"
                        ),
                        correlation={"continuity_turn_index": turn_index, "domain_commit_id": commit_id},
                        establishes="Classifier/promotion observational metadata for this continuity turn",
                        summary=dict(meta),
                    )
                )
            for event in self.public_events_for_turn(turn_index):
                surfaces.append(
                    self._surface(
                        contract="session_continuity",
                        authority=AUTHORITY_AUTHORITATIVE,
                        reference=(
                            f"data/sessions/{self.hg_session_id}.json#"
                            f"metadata.continuity_state.public_events[{event.get('event_id')}]"
                        ),
                        correlation={
                            "event_id": event.get("event_id"),
                            "continuity_turn_index": turn_index,
                            "domain_commit_id": commit_id,
                        },
                        establishes="Authoritative public event promoted for this continuity turn",
                        summary={
                            "event_id": event.get("event_id"),
                            "event_type": event.get("event_type"),
                            "summary_excerpt": str(event.get("summary") or "")[:240],
                        },
                    )
                )

        if self._evidence_index is not None:
            attempt_ids = self._round_attempt_ids(resolved.hg_round_id)
            for evidence_id in sorted(attempt_ids):
                attempt = self._load_attempt(evidence_id)
                if not attempt:
                    continue
                correlation = dict(attempt.get("correlation") or {})
                assoc_commit = str(
                    correlation.get("domain_commit_id")
                    or (attempt.get("associations") or {}).get("domain_commit_id")
                    or (attempt.get("decision") or {}).get("commit", {}).get("domain_commit_id")
                    or ""
                )
                role = correlation.get("role")
                if assoc_commit and assoc_commit != commit_id and role not in {"narrator", "librarian"}:
                    continue
                if not assoc_commit and role not in {"narrator", "librarian"} and role != "character":
                    continue
                decision = attempt.get("decision") or {}
                surfaces.append(
                    self._surface(
                        contract="execution_evidence",
                        authority=AUTHORITY_FORENSIC,
                        reference=f"data/execution_evidence/{self.hg_session_id}/attempts/{evidence_id}.json",
                        correlation={
                            "evidence_id": evidence_id,
                            "inference_id": correlation.get("inference_id"),
                            "domain_commit_id": assoc_commit or None,
                            "hg_round_id": correlation.get("hg_round_id"),
                            "role": role,
                            "inference_kind": correlation.get("inference_kind"),
                        },
                        establishes="Inference/decision forensic attempt relevant to this commit or round presentation",
                        summary={
                            "outcome": decision.get("outcome"),
                            "terminal_disposition": decision.get("terminal_disposition"),
                            "attempt_index": correlation.get("attempt_index"),
                            "prior_attempt_id": correlation.get("prior_attempt_id"),
                        },
                    )
                )

        audit = self._librarian_audit_for_commit(commit_id)
        if audit:
            surfaces.append(
                self._surface(
                    contract="librarian_proposal_audit",
                    authority=AUTHORITY_MEDIATED,
                    reference=(
                        f"data/sessions/{self.hg_session_id}.json#"
                        f"metadata.v2_host_state.librarian_proposal_audit_log"
                    ),
                    correlation={"librarian_proposal_domain_commit_id": commit_id},
                    establishes="Host-mediated S4 finalize/apply terminal disposition for this commit",
                    summary={
                        "durable_mutation_applied": audit.get("librarian_proposal_durable_mutation_applied"),
                        "continuity_accepted_count": audit.get("continuity_accepted_count"),
                    },
                )
            )

        tag_index_path = self.paths.tags_root / self.hg_session_id / "index.json"
        if tag_index_path.is_file():
            tag_index = json.loads(tag_index_path.read_text(encoding="utf-8"))
            for tag_id in sorted(tag_index.get("tag_ids") or []):
                tag = self._load_tag(str(tag_id))
                if not tag:
                    continue
                anchor = tag.get("anchor") or {}
                if str(anchor.get("domain_commit_id") or "") != commit_id:
                    continue
                surfaces.append(
                    self._surface(
                        contract="audit_tags",
                        authority=AUTHORITY_OBSERVATIONAL,
                        reference=f"data/audit_tags/{self.hg_session_id}/tags/{tag_id}.json",
                        correlation={
                            "tag_id": tag_id,
                            "entry_id": anchor.get("entry_id"),
                            "domain_commit_id": commit_id,
                            "hg_round_id": anchor.get("hg_round_id"),
                        },
                        establishes="Human observational audit tag anchored to this commit",
                        summary={
                            "resolution_status": (tag.get("forensic_scope") or {}).get("resolution_status"),
                        },
                    )
                )

        if resolved.memory_scope_id:
            event_ids = [
                str(event.get("event_id") or "")
                for turn in resolved.continuity_turn_indexes
                for event in self.public_events_for_turn(turn)
            ]
            records = self._story_knowledge_records(domain_commit_id=commit_id, event_ids=event_ids)
            for record in records:
                surfaces.append(
                    self._surface(
                        contract="story_knowledge",
                        authority=AUTHORITY_DERIVED,
                        reference=(
                            f"data/sessions/_story_knowledge/{resolved.memory_scope_id}/records.jsonl"
                            f"#line:{record.get('_line')}"
                        ),
                        correlation={
                            "story_record_id": record.get("story_record_id"),
                            "event_id": record.get("event_id"),
                            "source_domain_commit_id": record.get("source_domain_commit_id"),
                            "record_kind": record.get("record_kind"),
                        },
                        establishes="Derived story-knowledge record pointer correlated to this commit/event",
                        summary={
                            "record_kind": record.get("record_kind"),
                            "event_id": record.get("event_id"),
                        },
                    )
                )

        if resolved.plot_cognition_scope_id:
            for record_id in self._plot_cognition_records_for_commit(resolved.plot_cognition_scope_id, commit_id):
                scope = resolve_scope(
                    resolved.plot_cognition_scope_id,
                    forensics_root=self.paths.plot_cognition_root,
                )
                record = scope.load_record(record_id) if scope else None
                surfaces.append(
                    self._surface(
                        contract="plot_cognition_chronicle",
                        authority=AUTHORITY_FORENSIC,
                        reference=(
                            f"data/plot_cognition_forensics/{resolved.plot_cognition_scope_id}/"
                            f"records/{record_id}.json"
                        ),
                        correlation={
                            "record_id": record_id,
                            "domain_commit_id": commit_id,
                            "batch_id": (record or {}).get("correlation", {}).get("batch_id"),
                        },
                        establishes="Plot Cognition forensic chronicle record for this commit",
                        summary={
                            "record_class": (record or {}).get("record_class"),
                            "operation_kind": (record or {}).get("operation_kind"),
                            "integrity_status": (record or {}).get("integrity_status"),
                        },
                    )
                )

        if self._evidence_index is not None:
            surfaces.append(
                self._surface(
                    contract="execution_evidence_index",
                    authority=AUTHORITY_REBUILDABLE,
                    reference=f"data/execution_evidence/{self.hg_session_id}/index.json",
                    correlation={"domain_commit_id": commit_id, "hg_round_id": resolved.hg_round_id},
                    establishes="Rebuildable navigation index for execution evidence (not semantic proof)",
                    summary={"schema": self._evidence_index.get("schema")},
                )
            )

        surfaces.sort(key=_surface_sort_key)
        return surfaces

    def surfaces_for_round(self, resolved: ResolvedAnchors) -> list[dict[str, Any]]:
        surfaces: list[dict[str, Any]] = []
        round_id = resolved.hg_round_id
        if not round_id:
            return surfaces

        for entry in sorted(self.history_entries_for_round(round_id), key=lambda item: int(item.get("sequence_index") or 0)):
            entry_id = str(entry.get("entry_id") or "")
            surfaces.append(
                self._surface(
                    contract="session_rp_history",
                    authority=AUTHORITY_AUTHORITATIVE,
                    reference=f"data/sessions/{self.hg_session_id}.json#rp_history[{entry_id}]",
                    correlation={
                        "entry_id": entry_id,
                        "domain_commit_id": entry.get("domain_commit_id"),
                        "hg_round_id": round_id,
                        "sequence_index": entry.get("sequence_index"),
                    },
                    establishes="Canonical history row participating in this orchestration round",
                    summary={
                        "kind": entry.get("kind"),
                        "actor_id": entry.get("actor_id"),
                        "content_excerpt": str(entry.get("content") or "")[:240],
                    },
                )
            )

        if self._evidence_index is not None:
            for evidence_id in sorted(self._round_attempt_ids(round_id)):
                attempt = self._load_attempt(evidence_id)
                if not attempt:
                    continue
                correlation = dict(attempt.get("correlation") or {})
                decision = attempt.get("decision") or {}
                surfaces.append(
                    self._surface(
                        contract="execution_evidence",
                        authority=AUTHORITY_FORENSIC,
                        reference=f"data/execution_evidence/{self.hg_session_id}/attempts/{evidence_id}.json",
                        correlation={
                            "evidence_id": evidence_id,
                            "inference_id": correlation.get("inference_id"),
                            "domain_commit_id": correlation.get("domain_commit_id"),
                            "hg_round_id": round_id,
                            "role": correlation.get("role"),
                            "inference_kind": correlation.get("inference_kind"),
                        },
                        establishes="Round-scoped inference/decision forensic attempt",
                        summary={
                            "outcome": decision.get("outcome"),
                            "terminal_disposition": decision.get("terminal_disposition"),
                            "attempt_index": correlation.get("attempt_index"),
                            "prior_attempt_id": correlation.get("prior_attempt_id"),
                        },
                    )
                )
            pc_bucket = (self._evidence_index.get("plot_cognition") or {}).get("by_round") or {}
            for evidence_id in sorted(pc_bucket.get(round_id) or []):
                surfaces.append(
                    self._surface(
                        contract="execution_evidence_index",
                        authority=AUTHORITY_REBUILDABLE,
                        reference=f"data/execution_evidence/{self.hg_session_id}/index.json#plot_cognition.by_round",
                        correlation={"evidence_id": evidence_id, "hg_round_id": round_id},
                        establishes="Rebuildable Plot Cognition execution-evidence navigation pointer",
                        summary={"bucket": "plot_cognition.by_round"},
                    )
                )

        for commit_id in resolved.domain_commit_ids:
            audit = self._librarian_audit_for_commit(commit_id)
            if audit:
                surfaces.append(
                    self._surface(
                        contract="librarian_proposal_audit",
                        authority=AUTHORITY_MEDIATED,
                        reference=(
                            f"data/sessions/{self.hg_session_id}.json#"
                            f"metadata.v2_host_state.librarian_proposal_audit_log"
                        ),
                        correlation={"librarian_proposal_domain_commit_id": commit_id, "hg_round_id": round_id},
                        establishes="Host-mediated S4 audit entry for a commit within this round",
                        summary={
                            "durable_mutation_applied": audit.get("librarian_proposal_durable_mutation_applied"),
                        },
                    )
                )

        if resolved.plot_cognition_scope_id:
            for record_id in self._plot_cognition_records_for_round(resolved.plot_cognition_scope_id, round_id):
                scope = resolve_scope(
                    resolved.plot_cognition_scope_id,
                    forensics_root=self.paths.plot_cognition_root,
                )
                record = scope.load_record(record_id) if scope else None
                surfaces.append(
                    self._surface(
                        contract="plot_cognition_chronicle",
                        authority=AUTHORITY_FORENSIC,
                        reference=(
                            f"data/plot_cognition_forensics/{resolved.plot_cognition_scope_id}/"
                            f"records/{record_id}.json"
                        ),
                        correlation={
                            "record_id": record_id,
                            "hg_round_id": round_id,
                            "domain_commit_id": (record or {}).get("correlation", {}).get("domain_commit_id"),
                        },
                        establishes="Plot Cognition forensic chronicle record participating in this round",
                        summary={
                            "record_class": (record or {}).get("record_class"),
                            "operation_kind": (record or {}).get("operation_kind"),
                            "integrity_status": (record or {}).get("integrity_status"),
                        },
                    )
                )

        surfaces.sort(key=_surface_sort_key)
        return surfaces

    def detect_conflicts(self, surfaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        presentation_by_authority: dict[str, str] = {}
        presentation_refs: dict[str, dict[str, Any]] = {}
        for surface in surfaces:
            if surface.get("contract") != "session_rp_history":
                continue
            summary = surface.get("summary") or {}
            if summary.get("kind") != "presentation":
                continue
            text = str(summary.get("content_excerpt") or "").strip()
            if text:
                presentation_by_authority[AUTHORITY_AUTHORITATIVE] = text
                presentation_refs[AUTHORITY_AUTHORITATIVE] = surface
        for surface in surfaces:
            if surface.get("contract") != "execution_evidence":
                continue
            summary = surface.get("summary") or {}
            correlation = surface.get("correlation") or {}
            if correlation.get("role") != "narrator":
                continue
            attempt = self._load_attempt(str(correlation.get("evidence_id") or ""))
            if not attempt:
                continue
            candidate = str((attempt.get("decision") or {}).get("candidate_presentation_text") or "").strip()
            if not candidate:
                continue
            authoritative = presentation_by_authority.get(AUTHORITY_AUTHORITATIVE)
            if authoritative and authoritative != candidate[:240] and authoritative != candidate:
                conflicts.append(
                    {
                        "field": "presentation_text",
                        "surfaces": [
                            {
                                "contract": presentation_refs[AUTHORITY_AUTHORITATIVE]["contract"],
                                "authority": AUTHORITY_AUTHORITATIVE,
                                "reference": presentation_refs[AUTHORITY_AUTHORITATIVE]["reference"],
                            },
                            {
                                "contract": surface["contract"],
                                "authority": AUTHORITY_FORENSIC,
                                "reference": surface["reference"],
                            },
                        ],
                        "note": (
                            "Investigator does not arbitrate; authoritative transcript vs forensic "
                            "candidate presentation record"
                        ),
                    }
                )
        conflicts.sort(key=_conflict_sort_key)
        return conflicts

    def build_handoffs(self, view: ViewKind, resolved: ResolvedAnchors) -> list[dict[str, Any]]:
        handoffs: list[dict[str, Any]] = []
        if resolved.hg_round_id:
            handoffs.append(
                {
                    "tool": "list_execution_evidence.py",
                    "command": (
                        f"python tools/investigation/list_execution_evidence.py {self.hg_session_id} "
                        f"--chain director --round {resolved.hg_round_id} --summary"
                    ),
                    "purpose": "Director causal chain for the round",
                }
            )
            handoffs.append(
                {
                    "tool": "list_execution_evidence.py",
                    "command": (
                        f"python tools/investigation/list_execution_evidence.py {self.hg_session_id} "
                        f"--chain narrator --round {resolved.hg_round_id} --summary"
                    ),
                    "purpose": "Narrator retry/fidelity chain for the round",
                }
            )
            if self._ni_contract_limitation() is None:
                handoffs.append(
                    {
                        "tool": "trace_ni_forensics.py",
                        "command": ni_cli_handoff(self.hg_session_id, "round", resolved.hg_round_id),
                        "purpose": "NI round activity map",
                    }
                )
        if view == "commit" and resolved.domain_commit_ids:
            commit_id = resolved.domain_commit_ids[0]
            if self._ni_contract_limitation() is None:
                handoffs.append(
                    {
                        "tool": "trace_ni_forensics.py",
                        "command": ni_cli_handoff(self.hg_session_id, "s4", commit_id),
                        "purpose": "NI S4 chain for this commit",
                    }
                )
        if resolved.plot_cognition_scope_id and resolved.domain_commit_ids:
            handoffs.append(
                {
                    "tool": "trace_plot_cognition_forensics.py",
                    "command": (
                        "python tools/investigation/trace_plot_cognition_forensics.py "
                        f"{resolved.plot_cognition_scope_id} commit {resolved.domain_commit_ids[0]}"
                    ),
                    "purpose": "Detailed Plot Cognition chronicle commit effects",
                }
            )
        handoffs.sort(key=lambda item: (str(item.get("tool") or ""), str(item.get("command") or "")))
        return handoffs

    def investigate(
        self,
        *,
        anchor_type: str,
        anchor_value: str,
    ) -> dict[str, Any]:
        anchor_resolvers = {
            "domain_commit_id": lambda value: self.resolve_commit_anchor(value),
            "hg_round_id": lambda value: self.resolve_round_anchor(value),
            "continuity_turn_index": lambda value: self.resolve_turn_anchor(int(value)),
            "entry_id": lambda value: self.resolve_entry_anchor(value),
            "tag_id": lambda value: self.resolve_tag_anchor(value),
        }
        resolver = anchor_resolvers.get(anchor_type)
        if resolver is None:
            raise ValueError(f"Unsupported anchor_type: {anchor_type}")
        resolved, anchor_limitations, view = resolver(anchor_value)
        limitations = list(anchor_limitations)
        limitations.extend(self._execution_evidence_limitations())
        ni_limit = self._ni_contract_limitation()
        if ni_limit is not None:
            limitations.append(ni_limit)
        if not resolved.memory_scope_id:
            limitations.append(
                limitation(
                    "scope_unresolved",
                    "memory_scope_id is not available on the session",
                    detail={"field": "memory_scope_id", "contract": "story_knowledge"},
                )
            )
        if not resolved.plot_cognition_scope_id:
            limitations.append(
                limitation(
                    "scope_unresolved",
                    "plot_cognition_scope_id is not available on the session",
                    detail={"field": "plot_cognition_scope_id", "contract": "plot_cognition_chronicle"},
                )
            )
        if (self.paths.sessions_root.parent / "rp_audits").exists():
            limitations.append(
                limitation(
                    "legacy_surface_only",
                    "Legacy V1 rp_audits trees may exist but are not auto-joined by this navigator",
                    detail={"hint": "data/rp_audits/session_*"},
                )
            )

        surfaces = self.surfaces_for_commit(resolved) if view == "commit" else self.surfaces_for_round(resolved)
        conflicts = self.detect_conflicts(surfaces)
        handoffs = self.build_handoffs(view, resolved)
        limitations.sort(key=_limitation_sort_key)

        return {
            "schema": TURN_INVESTIGATOR_SCHEMA,
            "view": view,
            "hg_session_id": self.hg_session_id,
            "query": {"anchor_type": anchor_type, "anchor_value": str(anchor_value)},
            "resolved": {
                "hg_round_id": resolved.hg_round_id,
                "domain_commit_ids": list(resolved.domain_commit_ids),
                "continuity_turn_indexes": list(resolved.continuity_turn_indexes),
                "entry_ids": list(resolved.entry_ids),
                "memory_scope_id": resolved.memory_scope_id,
                "plot_cognition_scope_id": resolved.plot_cognition_scope_id,
            },
            "surfaces": surfaces,
            "handoffs": handoffs,
            "limitations": limitations,
            "conflicts": conflicts,
        }


def format_human_report(envelope: dict[str, Any]) -> str:
    lines = [
        f"schema: {envelope.get('schema')}",
        f"view: {envelope.get('view')}",
        f"session: {envelope.get('hg_session_id')}",
        f"anchor: {envelope.get('query', {}).get('anchor_type')}={envelope.get('query', {}).get('anchor_value')}",
        "",
    ]
    resolved = envelope.get("resolved") or {}
    lines.append(f"resolved.hg_round_id: {resolved.get('hg_round_id')}")
    lines.append(f"resolved.domain_commit_ids: {resolved.get('domain_commit_ids')}")
    lines.append(f"resolved.continuity_turn_indexes: {resolved.get('continuity_turn_indexes')}")
    lines.append("")
    lines.append(f"surfaces: {len(envelope.get('surfaces') or [])}")
    for surface in envelope.get("surfaces") or []:
        correlation = surface.get("correlation") or {}
        summary = surface.get("summary") or {}
        lines.append(
            f"  - {surface.get('contract')} [{surface.get('authority')}] "
            f"ref={surface.get('reference')} "
            f"role={correlation.get('role')} evidence_id={correlation.get('evidence_id')}"
        )
        if summary.get("kind"):
            lines.append(f"      kind={summary.get('kind')}")
    if envelope.get("limitations"):
        lines.append("")
        lines.append("limitations:")
        for item in envelope["limitations"]:
            lines.append(f"  - {item.get('code')}: {item.get('message')}")
    if envelope.get("conflicts"):
        lines.append("")
        lines.append("conflicts:")
        for item in envelope["conflicts"]:
            lines.append(f"  - {item.get('field')}: {item.get('note')}")
    if envelope.get("handoffs"):
        lines.append("")
        lines.append("handoffs:")
        for item in envelope["handoffs"]:
            lines.append(f"  - {item.get('tool')}: {item.get('command')}")
    return "\n".join(lines).rstrip() + "\n"
