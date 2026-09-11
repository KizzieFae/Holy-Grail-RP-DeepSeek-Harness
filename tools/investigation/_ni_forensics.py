"""Read-only NI forensic investigation over hg_ni_forensics_v1 (#46 Package B)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

NI_FORENSICS_CONTRACT = "hg_ni_forensics_v1"
INVESTIGATOR_SCHEMA = "hg_ni_investigator_v1"

_CATALOG_PATH_PARTS = ("docs", "llm-call-catalog.json")


def load_catalog_inference_kinds(repo_root: Path | None = None) -> tuple[str, ...]:
    """Production-utilized kinds from #152 authoritative catalog (fallback: legacy tuple)."""
    root = repo_root or Path(__file__).resolve().parents[2]
    catalog_path = root.joinpath(*_CATALOG_PATH_PARTS)
    if catalog_path.is_file():
        doc = json.loads(catalog_path.read_text(encoding="utf-8"))
        kinds = {
            str(row.get("canonical_inference_kind", "")).strip()
            for row in doc.get("primary_runtime", [])
            if row.get("canonical_inference_kind")
        }
        if kinds:
            return tuple(sorted(kinds))
    return _LEGACY_INFERENCE_KINDS


_LEGACY_INFERENCE_KINDS = (
    "character_orientation",
    "librarian_mediation",
    "storyteller_orientation",
    "storyteller_assessment",
    "character_move",
    "director_decision",
    "librarian_proposal",
)

INFERENCE_KINDS = load_catalog_inference_kinds()

DISPOSITION_PROPAGATED = "propagated"
DISPOSITION_OMITTED = "omitted"
DISPOSITION_INCOMPLETE = "incomplete"
DISPOSITION_INDETERMINATE = "indeterminate"

def _empty_ni_index() -> dict[str, Any]:
    return {
        "evidence_contract": NI_FORENSICS_CONTRACT,
        "by_round": {},
        "by_commit": {},
        "by_tag": {},
    }


def _empty_semantic_index() -> dict[str, Any]:
    return {
        "by_dimension": {},
        "hard_findings": [],
        "soft_findings": [],
        "residual_soft": [],
        "multi_candidate_inferences": [],
        "exhausted_hard_loops": [],
        "successful_correction_chains": [],
        "evaluator_failures": [],
        "evaluation_chains": {},
        "qa_by_target_role": {},
        "qa_pass_chains": {},
    }


def normalize_source_id(source_id: str) -> tuple[str, str]:
    """Return (source_id, candidate_id) for lmi:cand: or bare candidate ids."""
    raw = str(source_id or "").strip()
    if raw.startswith("lmi:cand:"):
        candidate = raw.split(":", 2)[-1]
        return raw, candidate
    if raw.startswith("lmi:"):
        return raw, raw.rsplit(":", 1)[-1]
    return f"lmi:cand:{raw}", raw


def librarian_omitted_candidate_id(
    catalog_source_ids: list[str],
    selected_source_ids: list[str],
    candidate_id: str,
) -> str | None:
    source_id = f"lmi:cand:{candidate_id}"
    if source_id not in catalog_source_ids:
        return None
    if source_id in selected_source_ids:
        return None
    return candidate_id


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


def artifact_ref(
    hg_session_id: str,
    evidence_id: str | None = None,
    *,
    tag_id: str | None = None,
    subpath: str | None = None,
) -> dict[str, str]:
    ref: dict[str, str] = {"hg_session_id": hg_session_id}
    if evidence_id:
        ref["evidence_id"] = evidence_id
        ref["path"] = f"execution_evidence/{hg_session_id}/attempts/{evidence_id}.json"
    if tag_id:
        ref["tag_id"] = tag_id
        ref["path"] = f"audit_tags/{hg_session_id}/tags/{tag_id}.json"
    if subpath:
        ref["path"] = subpath
    return ref


def build_envelope(
    *,
    view: str,
    hg_session_id: str,
    index_source: str,
    payload: dict[str, Any],
    limitations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema": INVESTIGATOR_SCHEMA,
        "view": view,
        "hg_session_id": hg_session_id,
        "index_source": index_source,
        "evidence_contract": NI_FORENSICS_CONTRACT,
        "limitations": limitations or [],
        "payload": payload,
    }


@dataclass
class NiSession:
    hg_session_id: str
    evidence_root: Path
    tags_root: Path | None = None
    rebuild_index: bool = False
    index: dict[str, Any] = field(default_factory=dict)
    index_source: str = "persisted"
    _attempt_cache: dict[str, dict[str, Any] | None] = field(default_factory=dict)

    @classmethod
    def open(
        cls,
        hg_session_id: str,
        evidence_root: Path,
        *,
        tags_root: Path | None = None,
        rebuild_index: bool = False,
    ) -> NiSession:
        session = cls(
            hg_session_id=hg_session_id,
            evidence_root=evidence_root,
            tags_root=tags_root,
            rebuild_index=rebuild_index,
        )
        session._load_index()
        return session

    def session_dir(self) -> Path:
        return self.evidence_root / self.hg_session_id

    def index_path(self) -> Path:
        return self.session_dir() / "index.json"

    def attempt_path(self, evidence_id: str) -> Path:
        return self.session_dir() / "attempts" / f"{evidence_id}.json"

    def _load_index(self) -> None:
        index_path = self.index_path()
        if not index_path.is_file():
            raise FileNotFoundError(f"Missing index.json under {self.session_dir()}")
        self.index = json.loads(index_path.read_text(encoding="utf-8"))
        ni = self.index.get("ni")
        if self.rebuild_index or not ni or not isinstance(ni, dict):
            self.index = self._rebuild_index_in_memory()
            self.index_source = "rebuilt"
        elif ni.get("evidence_contract") != NI_FORENSICS_CONTRACT:
            self.index = self._rebuild_index_in_memory()
            self.index_source = "rebuilt"
        else:
            self.index_source = "persisted"

    def _rebuild_index_in_memory(self) -> dict[str, Any]:
        base = dict(self.index)
        base["semantic"] = _empty_semantic_index()
        base["participation_by_round"] = {}
        base["ni"] = _empty_ni_index()
        for evidence_id in base.get("attempt_ids") or []:
            attempt = self.load_attempt(evidence_id, use_cache=False)
            if not attempt:
                continue
            correlation = attempt.get("correlation") or {}
            if correlation.get("role") == "participation":
                round_id = correlation.get("hg_round_id")
                if round_id:
                    key = str(round_id)
                    bucket = base["participation_by_round"].setdefault(key, [])
                    if evidence_id not in bucket:
                        bucket.append(evidence_id)
                continue
            if attempt.get("evidence_contract") == NI_FORENSICS_CONTRACT:
                self._index_ni_attempt(base, evidence_id, attempt)
        return base

    def _index_ni_attempt(
        self,
        index: dict[str, Any],
        evidence_id: str,
        attempt: dict[str, Any],
    ) -> None:
        correlation = attempt.get("correlation") or {}
        inference_kind = correlation.get("inference_kind")
        parent_inference_id = correlation.get("parent_inference_id") or correlation.get(
            "inference_id"
        )
        round_id = correlation.get("hg_round_id")
        commit_id = (
            correlation.get("domain_commit_id")
            or (attempt.get("associations") or {}).get("domain_commit_id")
            or (attempt.get("decision") or {}).get("commit", {}).get("domain_commit_id")
            or (attempt.get("decision") or {}).get("post_commit_semantic", {}).get("batch_id")
            or (attempt.get("decision") or {}).get("librarian_proposal", {}).get("batch_id")
        )
        ni = index["ni"]

        if round_id and parent_inference_id and inference_kind:
            round_key = str(round_id)
            parent_key = str(parent_inference_id)
            ni.setdefault("by_round", {}).setdefault(round_key, {}).setdefault(parent_key, {})[
                inference_kind
            ] = evidence_id

        proposal_commit_id = (attempt.get("associations") or {}).get(
            "domain_commit_id"
        ) or (attempt.get("decision") or {}).get("post_commit_semantic", {}).get("batch_id") or (
            attempt.get("decision") or {}
        ).get("librarian_proposal", {}).get("batch_id")
        if (
            inference_kind in {"librarian_proposal", "storyteller_post_commit_issue_pressure"}
            and proposal_commit_id
        ):
            ni.setdefault("by_commit", {}).setdefault(str(proposal_commit_id), {})[
                "proposal_evidence_id"
            ] = evidence_id
            ni["by_commit"][str(proposal_commit_id)]["domain_commit_id"] = correlation.get(
                "domain_commit_id"
            )
        if inference_kind == "post_commit_semantic_disposition" and commit_id:
            ni.setdefault("by_commit", {}).setdefault(str(commit_id), {})[
                "semantic_disposition_evidence_id"
            ] = evidence_id
            ni["by_commit"][str(commit_id)]["domain_commit_id"] = correlation.get(
                "domain_commit_id"
            )

        if (
            commit_id
            and inference_kind == "character_move"
            and (attempt.get("decision") or {}).get("commit", {}).get("committed")
        ):
            commit_key = str(correlation.get("domain_commit_id") or commit_id)
            ni.setdefault("by_commit", {}).setdefault(commit_key, {})["move_evidence_id"] = (
                evidence_id
            )

    def load_attempt(self, evidence_id: str, *, use_cache: bool = True) -> dict[str, Any] | None:
        if use_cache and evidence_id in self._attempt_cache:
            return self._attempt_cache[evidence_id]
        path = self.attempt_path(evidence_id)
        if not path.is_file():
            self._attempt_cache[evidence_id] = None
            return None
        attempt = json.loads(path.read_text(encoding="utf-8"))
        self._attempt_cache[evidence_id] = attempt
        return attempt

    def has_ni_contract(self) -> bool:
        for evidence_id in self.index.get("attempt_ids") or []:
            attempt = self.load_attempt(evidence_id)
            if attempt and attempt.get("evidence_contract") == NI_FORENSICS_CONTRACT:
                return True
        return False

    def ni_limitation_if_unavailable(self) -> dict[str, Any] | None:
        if self.has_ni_contract():
            return None
        return limitation(
            "ni_contract_unavailable",
            "Session lacks hg_ni_forensics_v1 evidence; NI views are best-effort only.",
            detail={
                "legacy_cli": "python tools/investigation/list_execution_evidence.py "
                f"{self.hg_session_id} --chain director|narrator|character|participation",
            },
        )

    def load_tag(self, tag_id: str) -> dict[str, Any] | None:
        if not self.tags_root:
            return None
        path = self.tags_root / self.hg_session_id / "tags" / f"{tag_id}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def resolve_tag_forensic_scope(self, tag: dict[str, Any]) -> dict[str, Any]:
        anchor = tag.get("anchor") or {}
        base = {
            "hg_round_id": anchor.get("hg_round_id"),
            "domain_commit_id": anchor.get("domain_commit_id"),
            "entry_sequence_index": anchor.get("sequence_index"),
        }
        ni_lim = self.ni_limitation_if_unavailable()
        if ni_lim:
            return {
                "resolution_status": "ni_contract_unavailable",
                **base,
            }
        ni = (self.index.get("ni") or {})
        round_id = anchor.get("hg_round_id")
        commit_id = anchor.get("domain_commit_id")
        round_chains = (ni.get("by_round") or {}).get(str(round_id or ""), {})
        commit_chain = (ni.get("by_commit") or {}).get(str(commit_id or ""), {})
        evidence_entry_points: dict[str, Any] = {
            "storyteller_chain": {},
            "character_chains": {},
            "proposal_evidence_id": commit_chain.get("proposal_evidence_id"),
            "move_evidence_id": commit_chain.get("move_evidence_id"),
        }
        for parent_inference_id, kinds in round_chains.items():
            if kinds.get("storyteller_assessment"):
                evidence_entry_points["storyteller_chain"]["assessment_evidence_id"] = kinds[
                    "storyteller_assessment"
                ]
            if kinds.get("storyteller_orientation"):
                evidence_entry_points["storyteller_chain"]["orientation_evidence_id"] = kinds[
                    "storyteller_orientation"
                ]
            if kinds.get("librarian_mediation") and "storyteller" in parent_inference_id:
                evidence_entry_points["storyteller_chain"]["mediation_evidence_id"] = kinds[
                    "librarian_mediation"
                ]
            if "character" in parent_inference_id or kinds.get("character_move"):
                evidence_entry_points["character_chains"][parent_inference_id] = {
                    "move_evidence_id": kinds.get("character_move"),
                    "orientation_evidence_id": kinds.get("character_orientation"),
                    "mediation_evidence_id": kinds.get("librarian_mediation"),
                }
        has_pointers = bool(
            evidence_entry_points.get("proposal_evidence_id")
            or evidence_entry_points.get("move_evidence_id")
            or evidence_entry_points["storyteller_chain"]
            or evidence_entry_points["character_chains"]
        )
        stored = tag.get("forensic_scope") or {}
        status = stored.get("resolution_status")
        if status in ("evidence_disabled", "evidence_unavailable", "resolution_failed"):
            return {**base, **stored}
        return {
            "resolution_status": "complete" if has_pointers else "partial",
            **base,
            "evidence_entry_points": evidence_entry_points,
        }

    def find_mediation_for_character(self) -> dict[str, Any] | None:
        for evidence_id in self.index.get("attempt_ids") or []:
            attempt = self.load_attempt(evidence_id)
            if not attempt:
                continue
            correlation = attempt.get("correlation") or {}
            if correlation.get("inference_kind") != "librarian_mediation":
                continue
            parent = str(correlation.get("parent_inference_id") or "")
            if parent.startswith("inf-character") or "character" in parent:
                return attempt
        return None

    def find_mediation_attempt(self) -> dict[str, Any] | None:
        """Prefer character-chain mediation; fall back to any librarian_mediation."""
        mediation = self.find_mediation_for_character()
        if mediation:
            return mediation
        for evidence_id in self.index.get("attempt_ids") or []:
            attempt = self.load_attempt(evidence_id)
            if not attempt:
                continue
            if (attempt.get("correlation") or {}).get("inference_kind") == "librarian_mediation":
                return attempt
        return None

    def find_character_move(self) -> dict[str, Any] | None:
        for evidence_id in self.index.get("attempt_ids") or []:
            attempt = self.load_attempt(evidence_id)
            if not attempt:
                continue
            if (attempt.get("correlation") or {}).get("inference_kind") != "character_move":
                continue
            if (attempt.get("decision") or {}).get("commit", {}).get("committed"):
                return attempt
        return None

    def attempts_by_kind(self, kind: str) -> list[dict[str, Any]]:
        results = []
        for evidence_id in self.index.get("attempt_ids") or []:
            attempt = self.load_attempt(evidence_id)
            if attempt and (attempt.get("correlation") or {}).get("inference_kind") == kind:
                results.append(attempt)
        return results

    def request_text(self, attempt: dict[str, Any]) -> str:
        contributions = (attempt.get("request") or {}).get("contributions") or []
        return "\n".join(str(item.get("content") or "") for item in contributions)

    def summarize_attempt(self, attempt: dict[str, Any]) -> dict[str, Any]:
        correlation = attempt.get("correlation") or {}
        decision = attempt.get("decision") or {}
        return {
            "evidence_id": attempt.get("evidence_id"),
            "evidence_contract": attempt.get("evidence_contract"),
            "role": correlation.get("role"),
            "inference_kind": correlation.get("inference_kind"),
            "inference_id": correlation.get("inference_id"),
            "parent_inference_id": correlation.get("parent_inference_id"),
            "hg_round_id": correlation.get("hg_round_id"),
            "domain_commit_id": correlation.get("domain_commit_id"),
            "outcome": decision.get("outcome"),
            "artifact_ref": artifact_ref(self.hg_session_id, attempt.get("evidence_id")),
        }

    def trace_lineage(self, source_id: str) -> dict[str, Any]:
        source_id, candidate_id = normalize_source_id(source_id)
        limitations: list[dict[str, Any]] = []
        ni_lim = self.ni_limitation_if_unavailable()
        if ni_lim:
            limitations.append(ni_lim)
            return build_envelope(
                view="lineage",
                hg_session_id=self.hg_session_id,
                index_source=self.index_source,
                limitations=limitations,
                payload={
                    "source_id": source_id,
                    "candidate_id": candidate_id,
                    "disposition": DISPOSITION_INDETERMINATE,
                    "steps": [],
                },
            )

        mediation = self.find_mediation_attempt()
        if not mediation:
            limitations.append(
                limitation(
                    "mediation_not_found",
                    "No librarian_mediation evidence found for character chain.",
                )
            )
            return build_envelope(
                view="lineage",
                hg_session_id=self.hg_session_id,
                index_source=self.index_source,
                limitations=limitations,
                payload={
                    "source_id": source_id,
                    "candidate_id": candidate_id,
                    "disposition": DISPOSITION_INCOMPLETE,
                    "steps": [],
                },
            )

        med = (mediation.get("decision") or {}).get("librarian_mediation") or {}
        catalog = list(med.get("catalog_source_ids") or [])
        selected = list(med.get("selected_source_ids") or [])
        retrieval_returned: list[str] = []
        for item in med.get("retrieval_disposition") or []:
            retrieval_returned.extend(item.get("candidate_ids_returned") or [])

        steps: list[dict[str, Any]] = []
        steps.append(
            {
                "stage": "retrieval",
                "observed": candidate_id in retrieval_returned,
                "candidate_ids_returned": retrieval_returned,
                "evidence_id": mediation.get("evidence_id"),
            }
        )
        in_catalog = source_id in catalog
        steps.append(
            {
                "stage": "librarian_catalog",
                "observed": in_catalog,
                "catalog_source_ids": catalog,
                "evidence_id": mediation.get("evidence_id"),
            }
        )
        is_selected = source_id in selected
        steps.append(
            {
                "stage": "librarian_selection",
                "observed": is_selected,
                "selected_source_ids": selected,
                "evidence_id": mediation.get("evidence_id"),
            }
        )

        disposition = DISPOSITION_INDETERMINATE
        owning_seam: str | None = None
        is_retrieval_candidate = source_id.startswith("lmi:cand:")

        if is_retrieval_candidate and candidate_id not in retrieval_returned:
            disposition = DISPOSITION_INCOMPLETE
            steps.append(
                {
                    "stage": "retrieval_boundary",
                    "observed": False,
                    "note": "Candidate not in recorded retrieval_disposition.",
                }
            )
        elif not in_catalog:
            disposition = DISPOSITION_INCOMPLETE
            steps.append(
                {
                    "stage": "catalog_boundary",
                    "observed": False,
                    "note": "Source not in mediation catalog.",
                }
            )
        elif not is_selected:
            disposition = DISPOSITION_OMITTED
            owning_seam = "librarian_mediation"
            steps.append(
                {
                    "stage": "omission",
                    "observed": True,
                    "owning_seam": owning_seam,
                    "omitted_source_id": source_id,
                }
            )
        elif is_retrieval_candidate:
            entry_id = (med.get("source_id_to_entry_id") or {}).get(source_id)
            steps.append(
                {
                    "stage": "bundle_mapping",
                    "observed": bool(entry_id),
                    "bundle_id": med.get("bundle_id"),
                    "bundle_entry_id": entry_id,
                    "evidence_id": mediation.get("evidence_id"),
                }
            )
            character_move = self.find_character_move()
            if not character_move:
                disposition = DISPOSITION_INCOMPLETE
                limitations.append(
                    limitation(
                        "character_move_missing",
                        "Librarian selected source but committed character_move evidence not found.",
                    )
                )
            else:
                packaging = (character_move.get("associations") or {}).get(
                    "packaging_disposition"
                ) or {}
                mapped_ids = list(packaging.get("mapped_contribution_ids") or [])
                contributions = (character_move.get("request") or {}).get("contributions") or []
                mapped_contributions = [
                    item
                    for item in contributions
                    if str(item.get("contribution_id") or "") in mapped_ids
                ]
                request_text = self.request_text(character_move)
                entry_id = (med.get("source_id_to_entry_id") or {}).get(source_id)
                content_present = bool(mapped_contributions) or bool(
                    entry_id and entry_id in request_text
                )
                steps.append(
                    {
                        "stage": "packaging",
                        "observed": bool(mapped_ids),
                        "mapped_contribution_ids": mapped_ids,
                        "evidence_id": character_move.get("evidence_id"),
                    }
                )
                steps.append(
                    {
                        "stage": "character_request",
                        "observed": content_present,
                        "mapped_contribution_count": len(mapped_contributions),
                        "note": "Recorded contribution/content presence only; semantic adequacy not assessed.",
                        "artifact_ref": artifact_ref(
                            self.hg_session_id, character_move.get("evidence_id")
                        ),
                    }
                )
                if is_selected and content_present:
                    disposition = DISPOSITION_PROPAGATED
                elif is_selected and entry_id:
                    disposition = DISPOSITION_INCOMPLETE
                    limitations.append(
                        limitation(
                            "request_content_not_located",
                            "Librarian selected source but mapped contribution/content not located in retained character request.",
                        )
                    )
                else:
                    disposition = DISPOSITION_INCOMPLETE
        else:
            disposition = DISPOSITION_INCOMPLETE
            limitations.append(
                limitation(
                    "non_candidate_propagation_unresolved",
                    "Authority/catalog source selected but downstream character propagation not deterministically resolved for non-candidate sources.",
                )
            )

        payload: dict[str, Any] = {
            "source_id": source_id,
            "candidate_id": candidate_id,
            "disposition": disposition,
            "owning_seam": owning_seam,
            "steps": steps,
        }
        return build_envelope(
            view="lineage",
            hg_session_id=self.hg_session_id,
            index_source=self.index_source,
            limitations=limitations,
            payload=payload,
        )

    def view_mediation(self, evidence_id: str | None = None) -> dict[str, Any]:
        limitations: list[dict[str, Any]] = []
        ni_lim = self.ni_limitation_if_unavailable()
        if ni_lim:
            limitations.append(ni_lim)
        attempt = None
        if evidence_id:
            attempt = self.load_attempt(evidence_id)
            if not attempt:
                limitations.append(
                    limitation("missing_artifact", f"Attempt not found: {evidence_id}")
                )
        else:
            attempt = self.find_mediation_attempt()
        if not attempt:
            return build_envelope(
                view="mediation",
                hg_session_id=self.hg_session_id,
                index_source=self.index_source,
                limitations=limitations,
                payload={"mediation": None},
            )
        med = (attempt.get("decision") or {}).get("librarian_mediation") or {}
        catalog = list(med.get("catalog_source_ids") or [])
        selected = list(med.get("selected_source_ids") or [])
        omitted = [sid for sid in catalog if sid not in selected]
        omissions = []
        for sid in omitted:
            if sid.startswith("lmi:cand:"):
                cid = sid.split(":", 2)[-1]
                omissions.append(
                    {
                        "candidate_id": cid,
                        "source_id": sid,
                        "owning_seam": "librarian_mediation",
                    }
                )
        return build_envelope(
            view="mediation",
            hg_session_id=self.hg_session_id,
            index_source=self.index_source,
            limitations=limitations,
            payload={
                "summary": self.summarize_attempt(attempt),
                "catalog_source_ids": catalog,
                "selected_source_ids": selected,
                "omitted_source_ids": omitted,
                "omissions": omissions,
                "retrieval_disposition": med.get("retrieval_disposition") or [],
                "source_id_to_entry_id": med.get("source_id_to_entry_id") or {},
                "bundle_id": med.get("bundle_id"),
                "consumers": self._mediation_consumers(attempt.get("evidence_id")),
            },
        )

    def _mediation_consumers(self, mediation_evidence_id: str | None) -> list[dict[str, Any]]:
        if not mediation_evidence_id:
            return []
        consumers = []
        for evidence_id in self.index.get("attempt_ids") or []:
            attempt = self.load_attempt(evidence_id)
            if not attempt:
                continue
            assoc = attempt.get("associations") or {}
            if assoc.get("librarian_mediation_evidence_id") == mediation_evidence_id:
                consumers.append(self.summarize_attempt(attempt))
        return consumers

    def view_character(self, parent_inference_id: str | None = None) -> dict[str, Any]:
        limitations: list[dict[str, Any]] = []
        ni_lim = self.ni_limitation_if_unavailable()
        if ni_lim:
            limitations.append(ni_lim)
        move = self.find_character_move()
        mediation = self.find_mediation_attempt()
        orientation = self.attempts_by_kind("character_orientation")
        orientation_attempt = orientation[0] if orientation else None
        if not move:
            limitations.append(
                limitation("character_move_missing", "No committed character_move evidence found.")
            )
        chain = {
            "orientation": self.summarize_attempt(orientation_attempt)
            if orientation_attempt
            else None,
            "mediation": self.summarize_attempt(mediation) if mediation else None,
            "character_move": self.summarize_attempt(move) if move else None,
        }
        request_excerpt = None
        contribution_refs: list[dict[str, Any]] = []
        if move:
            contributions = (move.get("request") or {}).get("contributions") or []
            for item in contributions:
                contribution_refs.append(
                    {
                        "contribution_id": item.get("contribution_id"),
                        "source_kind": item.get("source_kind"),
                        "content_excerpt": str(item.get("content") or "")[:240],
                    }
                )
            request_excerpt = self.request_text(move)[:480]
        return build_envelope(
            view="character",
            hg_session_id=self.hg_session_id,
            index_source=self.index_source,
            limitations=limitations,
            payload={
                "parent_inference_id": parent_inference_id,
                "chain": chain,
                "packaging_disposition": (move or {}).get("associations", {}).get(
                    "packaging_disposition"
                ),
                "request_excerpt": request_excerpt,
                "contributions": contribution_refs,
                "semantic_adequacy_note": (
                    "Tooling reports recorded propagation/presence only. "
                    "Semantic adequacy and understanding require investigator review."
                ),
            },
        )

    def view_storyteller(self, round_id: str | None = None) -> dict[str, Any]:
        limitations: list[dict[str, Any]] = []
        ni_lim = self.ni_limitation_if_unavailable()
        if ni_lim:
            limitations.append(ni_lim)
        assessments = self.attempts_by_kind("storyteller_assessment")
        orientations = self.attempts_by_kind("storyteller_orientation")
        directors = self.attempts_by_kind("director_decision")
        influences = []
        for director in directors:
            assoc = director.get("associations") or {}
            influences.append(
                {
                    "director": self.summarize_attempt(director),
                    "storyteller_assessment_evidence_id": assoc.get(
                        "storyteller_assessment_evidence_id"
                    ),
                    "packaging_disposition": assoc.get("packaging_disposition"),
                    "request_excerpt": self.request_text(director)[:240],
                }
            )
        return build_envelope(
            view="storyteller",
            hg_session_id=self.hg_session_id,
            index_source=self.index_source,
            limitations=limitations,
            payload={
                "round_id": round_id,
                "orientation": [
                    self.summarize_attempt(a) for a in orientations
                ],
                "assessment": [
                    self.summarize_attempt(a) for a in assessments
                ],
                "director_influence": influences,
            },
        )

    def view_s4(self, domain_commit_id: str) -> dict[str, Any]:
        limitations: list[dict[str, Any]] = []
        ni_lim = self.ni_limitation_if_unavailable()
        if ni_lim:
            limitations.append(ni_lim)
        commit_chain = (self.index.get("ni") or {}).get("by_commit", {}).get(
            str(domain_commit_id), {}
        )
        move_id = commit_chain.get("move_evidence_id")
        proposal_id = commit_chain.get("proposal_evidence_id")
        move = self.load_attempt(move_id) if move_id else None
        proposal = self.load_attempt(proposal_id) if proposal_id else None
        if move_id and not move:
            limitations.append(
                limitation("missing_artifact", f"Move evidence not found: {move_id}")
            )
        if proposal_id and not proposal:
            limitations.append(
                limitation("missing_artifact", f"Proposal evidence not found: {proposal_id}")
            )
        disposition_id = commit_chain.get("semantic_disposition_evidence_id")
        disposition = self.load_attempt(disposition_id) if disposition_id else None
        proposal_decision = (
            (proposal or {}).get("decision", {}).get("post_commit_semantic")
            or (proposal or {}).get("decision", {}).get("librarian_proposal")
            or {}
        )
        chain_steps = []
        if move:
            chain_steps.append({"stage": "character_move", "summary": self.summarize_attempt(move)})
        if disposition:
            chain_steps.append(
                {
                    "stage": "post_commit_semantic_disposition",
                    "summary": self.summarize_attempt(disposition),
                }
            )
        if proposal:
            chain_steps.append(
                {"stage": "post_commit_semantic", "summary": self.summarize_attempt(proposal)}
            )
            chain_steps.append(
                {
                    "stage": "host_validation",
                    "host_accepted": proposal_decision.get("host_accepted"),
                    "host_rejection_codes": proposal_decision.get("host_rejection_codes") or [],
                }
            )
            chain_steps.append(
                {
                    "stage": "continuity_disposition",
                    "continuity_accepted_count": proposal_decision.get(
                        "continuity_accepted_count"
                    ),
                    "continuity_rejected_count": proposal_decision.get(
                        "continuity_rejected_count"
                    ),
                    "durable_mutation_applied": proposal_decision.get(
                        "durable_mutation_applied"
                    ),
                    "item_dispositions": proposal_decision.get("item_dispositions") or [],
                }
            )
        if not chain_steps:
            limitations.append(
                limitation(
                    "s4_chain_incomplete",
                    "No S4 chain entries found for domain_commit_id.",
                    detail={"domain_commit_id": domain_commit_id},
                )
            )
        return build_envelope(
            view="s4",
            hg_session_id=self.hg_session_id,
            index_source=self.index_source,
            limitations=limitations,
            payload={
                "domain_commit_id": domain_commit_id,
                "move_evidence_id": move_id,
                "proposal_evidence_id": proposal_id,
                "chain": chain_steps,
            },
        )

    def view_round(self, round_id: str) -> dict[str, Any]:
        limitations: list[dict[str, Any]] = []
        ni_lim = self.ni_limitation_if_unavailable()
        if ni_lim:
            limitations.append(ni_lim)
        round_chains = (self.index.get("ni") or {}).get("by_round", {}).get(str(round_id), {})
        activities = []
        seen: set[tuple[str, str]] = set()
        for parent_id, kinds in round_chains.items():
            for kind, evidence_id in kinds.items():
                attempt = self.load_attempt(evidence_id)
                if not attempt:
                    limitations.append(
                        limitation(
                            "missing_artifact",
                            f"Indexed attempt missing: {evidence_id}",
                        )
                    )
                    continue
                seen.add((parent_id, kind))
                activities.append(
                    {
                        "parent_inference_id": parent_id,
                        "inference_kind": kind,
                        "summary": self.summarize_attempt(attempt),
                        "decision_keys": list((attempt.get("decision") or {}).keys()),
                    }
                )
        for evidence_id in (self.index.get("rounds") or {}).get(str(round_id), []):
            attempt = self.load_attempt(evidence_id)
            if not attempt or attempt.get("evidence_contract") != NI_FORENSICS_CONTRACT:
                continue
            correlation = attempt.get("correlation") or {}
            kind = correlation.get("inference_kind")
            parent_id = correlation.get("parent_inference_id") or correlation.get(
                "inference_id"
            )
            if not kind or not parent_id:
                continue
            key = (str(parent_id), str(kind))
            if key in seen:
                continue
            seen.add(key)
            activities.append(
                {
                    "parent_inference_id": parent_id,
                    "inference_kind": kind,
                    "summary": self.summarize_attempt(attempt),
                    "decision_keys": list((attempt.get("decision") or {}).keys()),
                }
            )
        activities.sort(key=lambda item: (item["inference_kind"], item["parent_inference_id"]))
        s4_commits = []
        for commit_id, chain in (self.index.get("ni") or {}).get("by_commit", {}).items():
            move_id = chain.get("move_evidence_id")
            if not move_id:
                continue
            move = self.load_attempt(move_id)
            if (move or {}).get("correlation", {}).get("hg_round_id") == round_id:
                s4_commits.append(
                    {
                        "domain_commit_id": commit_id,
                        "move_evidence_id": move_id,
                        "proposal_evidence_id": chain.get("proposal_evidence_id"),
                    }
                )
        return build_envelope(
            view="round",
            hg_session_id=self.hg_session_id,
            index_source=self.index_source,
            limitations=limitations,
            payload={
                "hg_round_id": round_id,
                "activities": activities,
                "s4_commits": s4_commits,
            },
        )

    def view_session(self) -> dict[str, Any]:
        limitations: list[dict[str, Any]] = []
        ni_lim = self.ni_limitation_if_unavailable()
        if ni_lim:
            limitations.append(ni_lim)
        ni = self.index.get("ni") or {}
        rounds = []
        for round_id, chains in (ni.get("by_round") or {}).items():
            kinds_present = sorted(
                {kind for kinds in chains.values() for kind in kinds.keys()}
            )
            rounds.append(
                {
                    "hg_round_id": round_id,
                    "inference_parent_count": len(chains),
                    "inference_kinds": kinds_present,
                }
            )
        commits = [
            {
                "domain_commit_id": commit_id,
                "move_evidence_id": data.get("move_evidence_id"),
                "proposal_evidence_id": data.get("proposal_evidence_id"),
            }
            for commit_id, data in (ni.get("by_commit") or {}).items()
        ]
        ni_attempts = []
        for evidence_id in self.index.get("attempt_ids") or []:
            attempt = self.load_attempt(evidence_id)
            if attempt and attempt.get("evidence_contract") == NI_FORENSICS_CONTRACT:
                ni_attempts.append(self.summarize_attempt(attempt))
        return build_envelope(
            view="session",
            hg_session_id=self.hg_session_id,
            index_source=self.index_source,
            limitations=limitations,
            payload={
                "attempt_count": len(self.index.get("attempt_ids") or []),
                "ni_attempt_count": len(ni_attempts),
                "rounds": rounds,
                "commits": commits,
                "ni_attempts": ni_attempts,
            },
        )

    def view_tag(self, tag_id: str, *, resolve: bool = False) -> dict[str, Any]:
        limitations: list[dict[str, Any]] = []
        tag = self.load_tag(tag_id)
        if not tag:
            return build_envelope(
                view="tag",
                hg_session_id=self.hg_session_id,
                index_source=self.index_source,
                limitations=[limitation("tag_not_found", f"Tag not found: {tag_id}")],
                payload={"tag_id": tag_id},
            )
        scope = (
            self.resolve_tag_forensic_scope(tag)
            if resolve
            else (tag.get("forensic_scope") or self.resolve_tag_forensic_scope(tag))
        )
        status = scope.get("resolution_status")
        if status in ("evidence_disabled", "evidence_unavailable"):
            limitations.append(
                limitation(
                    "evidence_disabled",
                    f"Tag forensic_scope status: {status}",
                )
            )
        elif status == "partial":
            limitations.append(
                limitation(
                    "forensic_scope_partial",
                    "Tag forensic_scope is partial; intrinsic anchors remain authoritative.",
                )
            )
        elif status == "ni_contract_unavailable":
            limitations.append(limitation("ni_contract_unavailable", scope.get("message", status)))
        entry_points = scope.get("evidence_entry_points") or {}
        chains = []
        for parent_id, kinds in entry_points.get("character_chains", {}).items():
            chains.append({"parent_inference_id": parent_id, "entry_points": kinds})
        return build_envelope(
            view="tag",
            hg_session_id=self.hg_session_id,
            index_source=self.index_source,
            limitations=limitations,
            payload={
                "tag_id": tag_id,
                "tag_index": tag.get("tag_index"),
                "anchor": tag.get("anchor"),
                "comment": tag.get("comment"),
                "forensic_scope": scope,
                "storyteller_chain": entry_points.get("storyteller_chain"),
                "character_chains": chains,
                "s4": {
                    "proposal_evidence_id": entry_points.get("proposal_evidence_id"),
                    "move_evidence_id": entry_points.get("move_evidence_id"),
                },
                "artifact_ref": artifact_ref(self.hg_session_id, tag_id=tag_id),
            },
        )


def format_human_report(envelope: dict[str, Any], *, excerpt_len: int = 240) -> str:
    lines = [
        f"schema: {envelope.get('schema')}",
        f"view: {envelope.get('view')}",
        f"session: {envelope.get('hg_session_id')}",
        f"index_source: {envelope.get('index_source')}",
        "",
    ]
    for lim in envelope.get("limitations") or []:
        lines.append(f"LIMITATION [{lim.get('code')}]: {lim.get('message')}")
    if envelope.get("limitations"):
        lines.append("")

    payload = envelope.get("payload") or {}
    view = envelope.get("view")

    if view == "lineage":
        lines.append(f"source_id: {payload.get('source_id')}")
        lines.append(f"disposition: {payload.get('disposition')}")
        if payload.get("owning_seam"):
            lines.append(f"owning_seam: {payload.get('owning_seam')}")
        lines.append("")
        for step in payload.get("steps") or []:
            lines.append(f"  - {step.get('stage')}: observed={step.get('observed')}")
            if step.get("owning_seam"):
                lines.append(f"    owning_seam: {step['owning_seam']}")
            if step.get("note"):
                lines.append(f"    note: {step['note']}")
    elif view == "tag":
        lines.append(f"tag_id: {payload.get('tag_id')}")
        anchor = payload.get("anchor") or {}
        lines.append(
            f"anchor: entry={anchor.get('entry_id')} round={anchor.get('hg_round_id')} "
            f"commit={anchor.get('domain_commit_id')}"
        )
        scope = payload.get("forensic_scope") or {}
        lines.append(f"forensic_scope.status: {scope.get('resolution_status')}")
        s4 = payload.get("s4") or {}
        if s4.get("proposal_evidence_id") or s4.get("move_evidence_id"):
            lines.append(
                f"s4: move={s4.get('move_evidence_id')} proposal={s4.get('proposal_evidence_id')}"
            )
        for chain in payload.get("character_chains") or []:
            ep = chain.get("entry_points") or {}
            lines.append(
                f"  character_chain {chain.get('parent_inference_id')}: "
                f"orientation={ep.get('orientation_evidence_id')} "
                f"mediation={ep.get('mediation_evidence_id')} "
                f"move={ep.get('move_evidence_id')}"
            )
        ref = payload.get("artifact_ref") or {}
        if ref.get("path"):
            lines.append(f"artifact_ref: {ref.get('path')}")
    elif view == "session":
        lines.append(f"attempt_count: {payload.get('attempt_count')}")
        lines.append(f"ni_attempt_count: {payload.get('ni_attempt_count')}")
        for rnd in payload.get("rounds") or []:
            lines.append(
                f"  round {rnd.get('hg_round_id')}: kinds={','.join(rnd.get('inference_kinds') or [])}"
            )
        for commit in payload.get("commits") or []:
            lines.append(
                f"  commit {commit.get('domain_commit_id')}: "
                f"move={commit.get('move_evidence_id')} proposal={commit.get('proposal_evidence_id')}"
            )
    elif view == "round":
        lines.append(f"round: {payload.get('hg_round_id')}")
        for act in payload.get("activities") or []:
            summary = act.get("summary") or {}
            lines.append(
                f"  - {act.get('inference_kind')} parent={act.get('parent_inference_id')} "
                f"evidence={summary.get('evidence_id')}"
            )
        for commit in payload.get("s4_commits") or []:
            lines.append(
                f"  s4 commit {commit.get('domain_commit_id')}: "
                f"move={commit.get('move_evidence_id')} proposal={commit.get('proposal_evidence_id')}"
            )
    elif view == "mediation":
        med = payload
        summary = med.get("summary") or {}
        if summary.get("evidence_id"):
            lines.append(f"evidence_id: {summary.get('evidence_id')}")
        lines.append(f"catalog: {med.get('catalog_source_ids')}")
        lines.append(f"selected: {med.get('selected_source_ids')}")
        lines.append(f"omitted: {med.get('omitted_source_ids')}")
        for omission in med.get("omissions") or []:
            lines.append(
                f"  omission {omission.get('candidate_id')} @ {omission.get('owning_seam')}"
            )
        for consumer in med.get("consumers") or []:
            lines.append(f"  consumer: {consumer.get('evidence_id')} role={consumer.get('role')}")
    elif view == "character":
        lines.append(payload.get("semantic_adequacy_note", ""))
        chain = payload.get("chain") or {}
        for key in ("orientation", "mediation", "character_move"):
            item = chain.get(key)
            if item:
                lines.append(f"  {key}: {item.get('evidence_id')}")
    elif view == "storyteller":
        for item in payload.get("director_influence") or []:
            director = item.get("director") or {}
            lines.append(
                f"  director {director.get('evidence_id')} "
                f"<- storyteller {item.get('storyteller_assessment_evidence_id')}"
            )
    elif view == "s4":
        lines.append(f"commit: {payload.get('domain_commit_id')}")
        for step in payload.get("chain") or []:
            lines.append(f"  - {step.get('stage')}")

    return "\n".join(lines).rstrip() + "\n"


def ni_cli_handoff(hg_session_id: str, view: str, *args: str) -> str:
    base = f"python tools/investigation/trace_ni_forensics.py {hg_session_id} {view}"
    if args:
        return base + " " + " ".join(args)
    return base
