"""Session manager for RP app.

Handles saving and loading conversation state between sessions.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from character_loader import make_agent_identifier
from cross_session_memory_policy import (
    append_load_item,
    should_promote_cross_session,
)

SESSION_INDEX_FILE_NAME = "_session_index.json"
SESSION_INDEX_VERSION = 2


class SessionManager:
    """Manages saving and loading RP session state."""

    def __init__(self, sessions_dir: str | Path = None) -> None:
        """Initialize the session manager.

        Args:
            sessions_dir: Directory for session files.
                         Defaults to data/sessions/ relative to project root.
        """
        if sessions_dir is None:
            self.sessions_dir = Path(__file__).parent.parent / "data" / "sessions"
        else:
            self.sessions_dir = Path(sessions_dir)

        # Ensure sessions directory exists
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.sessions_dir / SESSION_INDEX_FILE_NAME
        self._index_cache: dict[str, Any] | None = None

    def _iter_session_files(self) -> list[Path]:
        if not self.sessions_dir.exists():
            return []
        return sorted(
            [
                path
                for path in self.sessions_dir.glob("*.json")
                if path.name != SESSION_INDEX_FILE_NAME
            ],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    def _extract_user_relationships(
        self, metadata: dict[str, Any]
    ) -> dict[str, dict[str, dict[str, Any]]]:
        character_states = metadata.get("character_states", {})
        relationships_by_character: dict[str, dict[str, dict[str, Any]]] = {}
        for char_name, state in character_states.items():
            if not isinstance(state, dict):
                continue
            raw_relationships = state.get("relationships", {})
            if not isinstance(raw_relationships, dict):
                continue
            user_relationships: dict[str, dict[str, Any]] = {}
            for entity_name, relationship in raw_relationships.items():
                if not isinstance(relationship, dict):
                    continue
                if relationship.get("entity_type") != "user":
                    continue
                user_relationships[str(entity_name)] = {
                    "entity_type": "user",
                    "history": [
                        str(item)
                        for item in relationship.get("history", [])
                        if str(item).strip()
                    ][-8:],
                    "trust": relationship.get("trust"),
                    "interaction_count": int(relationship.get("interaction_count", 0)),
                    "last_summary": str(
                        relationship.get("last_summary", "") or ""
                    ).strip(),
                    "trust_history": [
                        int(item)
                        for item in relationship.get("trust_history", [])
                        if isinstance(item, int | float)
                    ][-8:],
                }
            if user_relationships:
                display_name = str(state.get("name", "") or "").strip()
                aliases = {
                    str(char_name),
                    display_name,
                    make_agent_identifier(str(char_name)),
                    make_agent_identifier(display_name),
                }
                for alias in aliases:
                    normalized_alias = str(alias or "").strip()
                    if normalized_alias:
                        relationships_by_character[normalized_alias] = (
                            user_relationships
                        )
        return relationships_by_character

    def _name_aliases(self, name: str) -> set[str]:
        raw_name = str(name or "").strip()
        if not raw_name:
            return set()
        return {
            raw_name,
            make_agent_identifier(raw_name),
        }

    def _build_session_index_entry(
        self, session_file: Path, session_data: dict[str, Any]
    ) -> dict[str, Any]:
        metadata = session_data.get("metadata", {})
        memory_buckets = metadata.get("memory_buckets", {})
        return {
            "session_id": str(session_data.get("session_id", session_file.stem)),
            "file_name": session_file.name,
            "file_mtime_ns": session_file.stat().st_mtime_ns,
            "saved_at": str(session_data.get("saved_at", "") or ""),
            "characters": [
                str(item) for item in session_data.get("characters", []) if str(item)
            ],
            "summary": str(metadata.get("summary", "No summary") or "No summary"),
            "scene_status": str(metadata.get("scene_status", "") or ""),
            "memory_buckets": {
                "session_summary": str(
                    memory_buckets.get("session_summary", "") or ""
                ).strip(),
                "persistent_world_facts": [
                    str(item)
                    for item in memory_buckets.get("persistent_world_facts", [])
                    if str(item).strip()
                ][-12:],
                "user_preferences": [
                    str(item)
                    for item in memory_buckets.get("user_preferences", [])
                    if str(item).strip()
                ][-12:],
            },
            "user_relationships": self._extract_user_relationships(metadata),
        }

    def _write_index(self, index: dict[str, Any]) -> None:
        self.index_file.write_text(
            json.dumps(index, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._index_cache = index

    def _rebuild_index(self) -> dict[str, Any]:
        sessions: dict[str, dict[str, Any]] = {}
        for session_file in self._iter_session_files():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue
            entry = self._build_session_index_entry(session_file, session_data)
            sessions[entry["session_id"]] = entry
        index = {
            "version": SESSION_INDEX_VERSION,
            "sessions": sessions,
        }
        self._write_index(index)
        return index

    def _index_is_current(self, index: dict[str, Any]) -> bool:
        if index.get("version") != SESSION_INDEX_VERSION:
            return False
        indexed_entries = index.get("sessions", {})
        if not isinstance(indexed_entries, dict):
            return False
        session_files = self._iter_session_files()
        indexed_by_file = {
            str(entry.get("file_name", "")): entry
            for entry in indexed_entries.values()
            if isinstance(entry, dict)
        }
        if len(indexed_by_file) != len(session_files):
            return False
        for session_file in session_files:
            indexed_entry = indexed_by_file.get(session_file.name)
            if indexed_entry is None:
                return False
            if (
                int(indexed_entry.get("file_mtime_ns", -1))
                != session_file.stat().st_mtime_ns
            ):
                return False
        return True

    def _get_index(self) -> dict[str, Any]:
        if self._index_cache is not None and self._index_is_current(self._index_cache):
            return self._index_cache
        if self.index_file.exists():
            try:
                index = json.loads(self.index_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                index = None
            if isinstance(index, dict) and self._index_is_current(index):
                self._index_cache = index
                return index
        return self._rebuild_index()

    def _sorted_index_entries(self) -> list[dict[str, Any]]:
        index = self._get_index()
        entries = [
            entry
            for entry in index.get("sessions", {}).values()
            if isinstance(entry, dict)
        ]
        return sorted(
            entries,
            key=lambda item: str(item.get("saved_at", "") or ""),
            reverse=True,
        )

    def _upsert_index_entry(
        self, session_file: Path, session_data: dict[str, Any]
    ) -> None:
        index = self._get_index()
        sessions = index.setdefault("sessions", {})
        entry = self._build_session_index_entry(session_file, session_data)
        sessions[entry["session_id"]] = entry
        self._write_index(index)

    def _remove_index_entry(self, session_id: str) -> None:
        index = self._get_index()
        sessions = index.setdefault("sessions", {})
        sessions.pop(session_id, None)
        self._write_index(index)

    def _build_relationship_trend(
        self,
        trust_samples: list[int],
        summaries: list[str],
        last_seen_at: str,
    ) -> dict[str, Any]:
        if not trust_samples and not summaries:
            return {}
        trend = "stable"
        if len(trust_samples) >= 2:
            if trust_samples[-1] > trust_samples[0]:
                trend = "improving"
            elif trust_samples[-1] < trust_samples[0]:
                trend = "declining"
        return {
            "trend": trend,
            "trust_samples": trust_samples[-8:],
            "starting_trust": trust_samples[0] if trust_samples else None,
            "current_trust": trust_samples[-1] if trust_samples else None,
            "last_seen_at": last_seen_at,
            "recent_summaries": summaries[-4:],
        }

    def save_session(
        self,
        session_id: str,
        team_state: dict[str, Any],
        characters: list[str],
        metadata: dict[str, Any] | None = None,
        player_character: str | None = None,
        chat_history: list[dict] | None = None,
    ) -> Path:
        """Save a session to disk.

        Args:
            session_id: Unique identifier for the session
            team_state: Team state from team.save_state()
            characters: List of character names in the session
            metadata: Optional additional metadata (summary, title, etc.)
            player_character: The character file the player is controlling (if any)
            chat_history: The conversation history to restore

        Returns:
            Path to the saved session file
        """
        session_data = {
            "session_id": session_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "characters": characters,
            "team_state": team_state,
            "player_character": player_character,
            "chat_history": chat_history or [],
            "metadata": metadata or {},
        }

        # Add summary if not provided
        if "summary" not in session_data["metadata"]:
            session_data["metadata"][
                "summary"
            ] = f"Session with {', '.join(characters)}"

        session_file = self.sessions_dir / f"{session_id}.json"

        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        self._upsert_index_entry(session_file, session_data)

        return session_file

    def load_session(self, session_id: str) -> dict[str, Any]:
        """Load a session from disk.

        Args:
            session_id: Session identifier

        Returns:
            Session data dictionary with team_state, characters, metadata

        Raises:
            FileNotFoundError: If session doesn't exist
        """
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        with open(session_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all available sessions with metadata.

        Returns:
            List of session info dictionaries
        """
        return [
            {
                "session_id": entry.get("session_id", ""),
                "saved_at": entry.get("saved_at", "Unknown"),
                "characters": entry.get("characters", []),
                "summary": entry.get("summary", "No summary"),
            }
            for entry in self._sorted_index_entries()
        ]

    def get_cross_session_memories(
        self,
        character_names: list[str],
        user_name: str,
        exclude_session_id: str | None = None,
        limit: int = 8,
        *,
        injection_report: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Aggregate lightweight cross-session memory buckets from saved sessions.

        When ``injection_report`` is provided, append load-stage trace entries and
        apply ``should_promote_cross_session`` for eligible string buckets.
        """
        summaries: list[str] = []
        world_facts: list[str] = []
        user_preferences: list[str] = []
        character_user_memories: dict[str, list[str]] = {
            name: [] for name in character_names
        }
        cross_session_relationships: dict[str, dict[str, Any]] = {
            name: {} for name in character_names
        }
        relationship_summaries: dict[str, list[str]] = {
            name: [] for name in character_names
        }
        trust_samples: dict[str, list[int]] = {name: [] for name in character_names}
        relationship_last_seen: dict[str, str] = {name: "" for name in character_names}
        character_aliases = {name: self._name_aliases(name) for name in character_names}
        character_name_set = {
            alias for aliases in character_aliases.values() for alias in aliases
        }

        def _maybe_record_session_summary(src_sid: str, text: str) -> None:
            if not text or text in summaries:
                return
            mt = "session_summary"
            inj = "session_summary_memory_bucket"
            dest = ["session_summaries_aggregate"]
            promote = should_promote_cross_session(text, mt)
            if injection_report is not None:
                append_load_item(
                    injection_report,
                    memory_type=mt,
                    injection_reason=inj,
                    source_session_id=src_sid,
                    target_character=None,
                    preview=text,
                    prompt_destination=dest,
                    promoted=promote,
                )
            if promote:
                summaries.append(text)

        def _maybe_record_world_fact(src_sid: str, fact_text: str) -> None:
            if not fact_text or fact_text in world_facts:
                return
            mt = "persistent_world_fact"
            inj = (
                "location_recurring"
                if fact_text.lower().startswith("recent recurring location:")
                else "world_fact_memory_bucket"
            )
            dest = ["PERSISTENT WORLD FACTS"]
            promote = should_promote_cross_session(fact_text, mt)
            if injection_report is not None:
                append_load_item(
                    injection_report,
                    memory_type=mt,
                    injection_reason=inj,
                    source_session_id=src_sid,
                    target_character=None,
                    preview=fact_text,
                    prompt_destination=dest,
                    promoted=promote,
                )
            if promote:
                world_facts.append(fact_text)

        def _maybe_record_user_pref(src_sid: str, pref_text: str) -> None:
            if not pref_text or pref_text in user_preferences:
                return
            mt = "user_preference"
            inj = "user_preference_memory_bucket"
            dest = ["USER PREFERENCES"]
            promote = should_promote_cross_session(pref_text, mt)
            if injection_report is not None:
                append_load_item(
                    injection_report,
                    memory_type=mt,
                    injection_reason=inj,
                    source_session_id=src_sid,
                    target_character=None,
                    preview=pref_text,
                    prompt_destination=dest,
                    promoted=promote,
                )
            if promote:
                user_preferences.append(pref_text)

        def _maybe_record_history_line(
            src_sid: str, char_name: str, line: str
        ) -> None:
            if not line or line in character_user_memories[char_name]:
                return
            mt = "relationship_history"
            inj = "relationship_history_shared_cast"
            dest = [
                "CROSS-SESSION USER MEMORY",
                "PRIVATE STATE",
            ]
            promote = should_promote_cross_session(line, mt)
            if injection_report is not None:
                append_load_item(
                    injection_report,
                    memory_type=mt,
                    injection_reason=inj,
                    source_session_id=src_sid,
                    target_character=char_name,
                    preview=line,
                    prompt_destination=dest,
                    promoted=promote,
                )
            if promote:
                character_user_memories[char_name].append(line)

        for entry in self._sorted_index_entries():
            session_id = str(entry.get("session_id", "") or "")
            if exclude_session_id and session_id == exclude_session_id:
                continue
            session_characters: set[str] = set()
            for item in entry.get("characters", []):
                session_characters.update(self._name_aliases(str(item)))
            if not session_characters.intersection(character_name_set):
                continue

            memory_buckets = entry.get("memory_buckets", {})
            session_summary = str(
                memory_buckets.get("session_summary", "") or ""
            ).strip()
            _maybe_record_session_summary(session_id, session_summary)

            for fact in memory_buckets.get("persistent_world_facts", []):
                _maybe_record_world_fact(session_id, str(fact).strip())

            for pref in memory_buckets.get("user_preferences", []):
                _maybe_record_user_pref(session_id, str(pref).strip())

            relationships_by_character = entry.get("user_relationships", {})
            for char_name in character_names:
                relationship: dict[str, Any] = {}
                if isinstance(relationships_by_character, dict):
                    for alias in character_aliases.get(char_name, set()):
                        relationship = relationships_by_character.get(alias, {}).get(
                            user_name, {}
                        )
                        if isinstance(relationship, dict) and relationship:
                            break
                if not isinstance(relationship, dict) or not relationship:
                    continue

                history = [
                    str(item).strip()
                    for item in relationship.get("history", [])
                    if str(item).strip()
                ]
                for item in history:
                    _maybe_record_history_line(session_id, char_name, item)

                last_summary = str(relationship.get("last_summary", "") or "").strip()
                if (
                    last_summary
                    and last_summary not in relationship_summaries[char_name]
                ):
                    relationship_summaries[char_name].append(last_summary)

                trust_history = [
                    int(item)
                    for item in relationship.get("trust_history", [])
                    if isinstance(item, int | float)
                ]
                trust_value = relationship.get("trust")
                if isinstance(trust_value, int | float):
                    trust_history.append(int(trust_value))
                for trust_sample in trust_history:
                    if trust_sample not in trust_samples[char_name]:
                        trust_samples[char_name].append(trust_sample)

                if relationship and not cross_session_relationships[char_name]:
                    cross_session_relationships[char_name] = relationship
                    if injection_report is not None:
                        snap_prev = (
                            f"trust={relationship.get('trust')} "
                            f"history_len={len(relationship.get('history', []) or [])}"
                        )
                        append_load_item(
                            injection_report,
                            memory_type="relationship_snapshot",
                            injection_reason="relationship_snapshot_shared_cast",
                            source_session_id=session_id,
                            target_character=char_name,
                            preview=snap_prev,
                            prompt_destination=["PRIVATE STATE"],
                            promoted=True,
                        )
                relationship_last_seen[char_name] = str(
                    entry.get("saved_at", relationship_last_seen[char_name]) or ""
                )

            if (
                len(summaries) >= limit
                and len(world_facts) >= limit
                and len(user_preferences) >= limit
            ):
                if all(
                    len(character_user_memories[name]) >= limit
                    for name in character_names
                ):
                    break

        relationship_trends = {
            name: self._build_relationship_trend(
                list(reversed(trust_samples[name])),
                list(reversed(relationship_summaries[name])),
                relationship_last_seen[name],
            )
            for name in character_names
        }

        indexed = len(self._sorted_index_entries())
        return {
            "session_summaries": summaries[:limit],
            "persistent_world_facts": world_facts[:limit],
            "user_preferences": user_preferences[:limit],
            "character_user_memories": {
                name: items[:limit] for name, items in character_user_memories.items()
            },
            "cross_session_relationships": cross_session_relationships,
            "relationship_trends": relationship_trends,
            "indexed_session_count": indexed,
            "_cross_session_enabled": True,
        }

    def finalize_incomplete_sessions(self) -> list[str]:
        recovered_session_ids: list[str] = []

        if not self.sessions_dir.exists():
            return recovered_session_ids

        for session_file in self._iter_session_files():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

            metadata = data.setdefault("metadata", {})
            if metadata.get("scene_status") != "active":
                continue

            metadata["scene_status"] = "closed"
            metadata["scene_closed_reason"] = "startup_recovery"
            metadata["recovered_on_startup"] = True

            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self._upsert_index_entry(session_file, data)

            recovered_session_ids.append(str(data.get("session_id", session_file.stem)))

        return recovered_session_ids

    def delete_session(self, session_id: str) -> bool:
        """Delete a session file.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        session_file = self.sessions_dir / f"{session_id}.json"

        if session_file.exists():
            session_file.unlink()
            self._remove_index_entry(session_id)
            return True
        return False

    def generate_session_id(self, characters: list[str]) -> str:
        """Generate a unique session ID.

        Args:
            characters: Character names in the session

        Returns:
            Unique session ID string
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        char_slug = "_".join(c.lower().replace(" ", "_") for c in characters[:2])
        return f"{char_slug}_{timestamp}"
