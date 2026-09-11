"""Production session repository backed by V1 SessionManager persistence."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain.paths import execution_evidence_data_dir, plot_cognition_forensics_data_dir  # noqa: E402
from character_state_model import CharacterState  # noqa: E402
from continuity_manager import ContinuityManager  # noqa: E402
from session_manager import SessionManager  # noqa: E402

from .contract import CommitResponse  # noqa: E402
from .cross_scope_memory_repository import CrossScopeMemoryRepository  # noqa: E402
from .knowledge_service import KnowledgeService  # noqa: E402
from .memory_service import MemoryService  # noqa: E402
from .scope_knowledge_repository import ScopeKnowledgeRepository  # noqa: E402
from .story_knowledge_repository import StoryKnowledgeRepository  # noqa: E402
from .plot_cognition_forensics_repository import PlotCognitionForensicsRepository  # noqa: E402
from .plot_cognition_forensics_service import PlotCognitionForensicsService  # noqa: E402
from .plot_cognition_overlay_repository import PlotCognitionOverlayRepository  # noqa: E402
from .plot_cognition_scope import resolve_plot_cognition_scope_id  # noqa: E402
from .player_identity import resolve_player_display_name  # noqa: E402
from .session_lock import SessionLockRegistry  # noqa: E402
from .session_setup import create_live_session_from_setup  # noqa: E402
from .session_state import (  # noqa: E402
    EXECUTION_EVIDENCE_METADATA_KEY,
    V2_HOST_METADATA_KEY,
    LiveSession,
    initialize_live_session,
)


class PersistenceError(RuntimeError):
    """Raised when authoritative state cannot be durably persisted."""


@dataclass(frozen=True)
class CommitDedupRecord:
    domain_commit_id: str
    continuity_turn_index: int
    response: CommitResponse


class SessionStore(Protocol):
    def create_scene(self, **kwargs: Any) -> LiveSession: ...

    def require(self, hg_scene_id: str) -> LiveSession: ...

    def get(self, hg_scene_id: str) -> LiveSession | None: ...


class SessionRepository:
    """Authoritative session store with synchronous V1 file persistence."""

    def __init__(self, sessions_dir: str | Path | None = None) -> None:
        self._session_manager = SessionManager(sessions_dir)
        self._cache: dict[str, LiveSession] = {}
        self._commit_dedup: dict[str, CommitDedupRecord] = {}
        self._cross_scope_repo = CrossScopeMemoryRepository(
            self._session_manager.sessions_dir / "_cross_scope_memory"
        )
        self._scope_knowledge_repo = ScopeKnowledgeRepository(
            self._session_manager.sessions_dir / "_scope_knowledge"
        )
        self._story_knowledge_repo = StoryKnowledgeRepository(
            self._session_manager.sessions_dir / "_story_knowledge"
        )
        self._plot_cognition_overlay_repo = PlotCognitionOverlayRepository(
            self._session_manager.sessions_dir / "_plot_cognition_overlay"
        )
        self._plot_cognition_forensics_repo = PlotCognitionForensicsRepository(
            plot_cognition_forensics_data_dir()
        )
        self._plot_cognition_forensics = PlotCognitionForensicsService(
            self._plot_cognition_forensics_repo
        )
        self.memory_service = MemoryService(self._cross_scope_repo)
        self.knowledge_service = KnowledgeService(
            self._scope_knowledge_repo,
            story_knowledge_repo=self._story_knowledge_repo,
        )
        self._session_locks = SessionLockRegistry()

    @property
    def sessions_dir(self) -> Path:
        return self._session_manager.sessions_dir

    @property
    def scope_knowledge_repo(self) -> ScopeKnowledgeRepository:
        return self._scope_knowledge_repo

    @property
    def story_knowledge_repo(self) -> StoryKnowledgeRepository:
        return self._story_knowledge_repo

    @property
    def plot_cognition_overlay_repo(self) -> PlotCognitionOverlayRepository:
        return self._plot_cognition_overlay_repo

    @property
    def plot_cognition_forensics_service(self) -> PlotCognitionForensicsService:
        return self._plot_cognition_forensics

    def health_ok(self) -> bool:
        return self._session_manager.sessions_dir.exists()

    def create_session(
        self,
        *,
        cast: list[str] | None = None,
        characters: list[str] | None = None,
        scene_template_id: str | None = None,
        role_assignments: dict[str, str] | None = None,
        opening: dict[str, Any] | None = None,
        location: str = "Workshop",
        hg_session_id: str | None = None,
        opening_description: str | None = None,
        characters_dir: str | Path | None = None,
        memory_scope_id: str | None = None,
        plot_cognition_scope_id: str | None = None,
        player_character_file_id: str | None = None,
        user_persona_id: str | None = None,
        seed_active_issue: bool = False,
    ) -> LiveSession:
        if characters:
            session = create_live_session_from_setup(
                character_files=list(characters),
                scene_template_id=scene_template_id,
                role_assignments=role_assignments,
                opening=opening,
                location=location if location != "Workshop" else None,
                hg_session_id=hg_session_id,
                characters_dir=characters_dir,
                memory_scope_id=memory_scope_id,
                plot_cognition_scope_id=plot_cognition_scope_id,
                player_character_file_id=player_character_file_id,
                user_persona_id=user_persona_id,
            )
        else:
            session = initialize_live_session(
                hg_session_id=hg_session_id,
                location=location,
                cast=cast,
                opening_description=opening_description
                or "A quiet workshop for Holy Grail domain host sessions.",
                memory_scope_id=memory_scope_id,
                plot_cognition_scope_id=plot_cognition_scope_id,
                seed_active_issue=seed_active_issue,
            )
        self._cache[session.hg_scene_id] = session
        self.persist(session)
        return session

    def open_session(self, hg_session_id: str) -> LiveSession:
        if hg_session_id in self._cache:
            return self._cache[hg_session_id]
        session_data = self._session_manager.load_session(hg_session_id)
        session = self._hydrate_session(hg_session_id, session_data)
        self._cache[session.hg_scene_id] = session
        self._restore_commit_dedup(session)
        return session

    def create_scene(self, **kwargs: Any) -> LiveSession:
        """Transitional alias for prototype ``POST /v1/scenes`` compatibility."""
        return self.create_session(
            cast=kwargs.get("cast"),
            location=kwargs.get("location", "Workshop"),
            hg_session_id=kwargs.get("hg_scene_id") or kwargs.get("hg_session_id"),
        )

    def get(self, hg_scene_id: str) -> LiveSession | None:
        if hg_scene_id in self._cache:
            return self._cache[hg_scene_id]
        session_file = self._session_manager.sessions_dir / f"{hg_scene_id}.json"
        if not session_file.exists():
            return None
        try:
            return self.open_session(hg_scene_id)
        except FileNotFoundError:
            return None

    def require(self, hg_scene_id: str) -> LiveSession:
        session = self.get(hg_scene_id)
        if session is None:
            raise KeyError(f"unknown hg_scene_id: {hg_scene_id}")
        return session

    def session_scope(self, hg_scene_id: str):
        """Per-session re-entrant lock for concurrent HTTP handler safety (#39)."""
        return self._session_locks.session_scope(hg_scene_id)

    def persist(self, session: LiveSession) -> None:
        session.continuity_version += 1
        payload = self._build_session_payload(session)
        try:
            self._session_manager.save_session(**payload)
        except OSError as exc:
            session.continuity_version -= 1
            raise PersistenceError(f"failed to persist session {session.hg_session_id}") from exc

    def commit_dedup_key(
        self,
        *,
        hg_scene_id: str,
        inference_id: str,
        expected_turn_index: int,
        character_id: str,
        validated_move: dict[str, Any],
        director_decision: dict[str, Any],
    ) -> str:
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "validated_move": validated_move,
                    "director_decision": director_decision,
                    "character_id": character_id,
                },
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        return (
            f"{hg_scene_id}:{inference_id}:{expected_turn_index}:{character_id}:{fingerprint}"
        )

    def get_commit_dedup(self, dedup_key: str) -> CommitDedupRecord | None:
        return self._commit_dedup.get(dedup_key)

    def record_commit_dedup(
        self, dedup_key: str, record: CommitDedupRecord, session: LiveSession
    ) -> None:
        self._commit_dedup[dedup_key] = record
        session.commit_dedup_index[dedup_key] = {
            "domain_commit_id": record.domain_commit_id,
            "continuity_turn_index": record.continuity_turn_index,
            "response": asdict(record.response),
        }

    def _restore_commit_dedup(self, session: LiveSession) -> None:
        for key, entry in session.commit_dedup_index.items():
            response_data = entry.get("response") or {}
            self._commit_dedup[key] = CommitDedupRecord(
                domain_commit_id=str(entry["domain_commit_id"]),
                continuity_turn_index=int(entry["continuity_turn_index"]),
                response=CommitResponse(**response_data),
            )

    def snapshot_manager(self, session: LiveSession) -> dict[str, Any]:
        return session.manager.to_dict()

    def restore_manager(self, session: LiveSession, snapshot: dict[str, Any]) -> None:
        session.manager = ContinuityManager.from_dict(snapshot)

    def _build_session_payload(self, session: LiveSession) -> dict[str, Any]:
        assert session.manager.scene_state is not None
        char_states_dict = {
            name: state.to_dict() for name, state in session.character_states.items()
        }
        metadata: dict[str, Any] = {
            "summary": f"V2 domain host session with {', '.join(session.cast)}",
            "character_states": char_states_dict,
            "continuity_state": session.manager.to_dict(),
            V2_HOST_METADATA_KEY: {
                "committed_move_count": session.committed_move_count,
                "commit_ids": list(session.commit_ids),
                "character_private_secrets": dict(session.character_private_secrets),
                "continuity_version": session.continuity_version,
                "commit_dedup_index": dict(session.commit_dedup_index),
                "rp_history": list(session.rp_history),
                "setup_snapshot": copy.deepcopy(session.setup_snapshot),
                "character_file_ids": dict(session.character_file_ids),
                "memory_scope_id": session.memory_scope_id,
                "plot_cognition_scope_id": session.plot_cognition_scope_id,
                "librarian_proposal_audit_log": list(
                    getattr(session, "librarian_proposal_audit_log", []) or []
                ),
                "runtime_build_provenance": copy.deepcopy(
                    getattr(session, "runtime_build_provenance", None)
                ),
                "runtime_effective_configuration": copy.deepcopy(
                    getattr(session, "runtime_effective_configuration", None)
                ),
            },
            "scene_role_assignments": dict(
                getattr(session.manager.scene_state, "role_assignments", {}) or {}
            ),
        }
        evidence_session_dir = execution_evidence_data_dir() / session.hg_session_id
        if evidence_session_dir.is_dir():
            metadata[EXECUTION_EVIDENCE_METADATA_KEY] = {
                "schema": "hg_execution_evidence_index_v1",
                "session_root": f"execution_evidence/{session.hg_session_id}",
            }
        player_file = None
        player_display = None
        if session.setup_snapshot:
            player_file = session.setup_snapshot.get("player_character_file_id")
            names_by_file = dict(session.setup_snapshot.get("names_by_file") or {})
            player_display = resolve_player_display_name(
                player_character_file_id=str(player_file) if player_file else None,
                names_by_file=names_by_file,
            )
        return {
            "session_id": session.hg_session_id,
            "team_state": {
                "type": "v2_domain_host_minimal",
                "scene_state": {
                    "opening_description": str(
                        session.manager.scene_state.opening_description or ""
                    ),
                    "location": str(session.manager.scene_state.location or ""),
                },
            },
            "characters": list(session.cast),
            "metadata": metadata,
            "player_character": player_display,
            "chat_history": [],
        }

    def _hydrate_session(self, hg_session_id: str, session_data: dict[str, Any]) -> LiveSession:
        metadata = session_data.get("metadata") or {}
        continuity_data = metadata.get("continuity_state")
        if not continuity_data:
            raise ValueError(f"session {hg_session_id} missing continuity_state metadata")

        manager = ContinuityManager.from_dict(continuity_data)
        cast = [str(name) for name in session_data.get("characters") or []]
        if not cast and manager.scene_state is not None:
            cast = list(manager.scene_state.present_characters or [])

        character_states: dict[str, CharacterState] = {}
        for name, state_dict in (metadata.get("character_states") or {}).items():
            if isinstance(state_dict, dict):
                character_states[str(name)] = CharacterState.from_dict(state_dict)

        host_state = metadata.get(V2_HOST_METADATA_KEY) or {}
        secrets = dict(host_state.get("character_private_secrets") or {})
        if not secrets:
            for name in cast:
                state = character_states.get(name)
                if state and state.private_memories:
                    secrets[name] = str(state.private_memories[0])

        memory_scope = str(host_state.get("memory_scope_id") or "")
        plot_scope_raw = str(host_state.get("plot_cognition_scope_id") or "")
        plot_scope = (
            plot_scope_raw
            if plot_scope_raw.strip()
            else resolve_plot_cognition_scope_id(None, memory_scope)
        )
        return LiveSession(
            hg_session_id=hg_session_id,
            hg_scene_id=hg_session_id,
            manager=manager,
            cast=cast,
            character_states=character_states,
            committed_move_count=int(host_state.get("committed_move_count", 0)),
            commit_ids=list(host_state.get("commit_ids") or []),
            character_private_secrets=secrets,
            continuity_version=int(host_state.get("continuity_version", 0)),
            commit_dedup_index=dict(host_state.get("commit_dedup_index") or {}),
            rp_history=list(host_state.get("rp_history") or []),
            setup_snapshot=dict(host_state.get("setup_snapshot") or {}),
            character_file_ids=dict(host_state.get("character_file_ids") or {}),
            memory_scope_id=memory_scope,
            plot_cognition_scope_id=plot_scope,
            librarian_proposal_audit_log=list(
                host_state.get("librarian_proposal_audit_log") or []
            ),
            runtime_build_provenance=dict(host_state.get("runtime_build_provenance") or {})
            if host_state.get("runtime_build_provenance")
            else None,
            runtime_effective_configuration=dict(
                host_state.get("runtime_effective_configuration") or {}
            )
            if host_state.get("runtime_effective_configuration")
            else None,
            rounds=[],
        )

    def clear_cache(self) -> None:
        """Drop in-memory cache (for restart simulation tests)."""
        self._cache.clear()
        self._commit_dedup.clear()
