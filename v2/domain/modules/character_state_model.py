from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

PROTECTED_IDENTITY_FIELDS = (
    "long_term_goal",
    "medium_term_goal",
    "core_goals",
    "voice_profile",
    "reaction_profile",
    "speech_fingerprint",
    "personality",
    "description",
    "hidden_agenda",
)


def _format_profile(profile: dict[str, Any]) -> str:
    if not profile:
        return ""

    return ", ".join(f"{key}: {value}" for key, value in profile.items())


def _compact_history(history: list[str], limit: int = 8) -> list[str]:
    return history[-limit:] if len(history) > limit else history


def _relationship_text(value: Any) -> str:
    return str(value or "").strip()


def _has_targeted_goal_thread(relationship: dict[str, Any]) -> bool:
    return any(
        _relationship_text(relationship.get(field_name))
        for field_name in ("long_term_goal", "medium_term_goal", "current_objective")
    )


def _has_lightweight_relationship_posture(relationship: dict[str, Any]) -> bool:
    return any(
        _relationship_text(relationship.get(field_name))
        for field_name in ("stance", "tactical_posture", "threat_level", "usefulness")
    )


@dataclass
class CharacterState:
    """Tracks the evolving state of a character in a scene.

    This is private to each character - they know their own state,
    but not other characters' private states.
    """

    name: str
    description: str = ""
    personality: str = ""
    long_term_goal: str = ""
    medium_term_goal: str = ""
    short_term_tactic: str = ""
    current_objective: str = ""
    local_task_goal: str = ""
    local_task_tactic: str = ""
    core_goals: list[str] = field(default_factory=list)
    voice_profile: dict[str, Any] = field(default_factory=dict)
    reaction_profile: dict[str, Any] = field(default_factory=dict)
    speech_fingerprint: dict[str, Any] = field(default_factory=dict)
    emotional_state: str = "neutral"
    stress_level: int = 0
    trust_toward_player: int = 5
    private_memories: list[str] = field(default_factory=list)
    character_memory_summary: list[str] = field(default_factory=list)
    recent_observations: list[str] = field(default_factory=list)
    hidden_agenda: str = ""
    relationships: dict[str, dict] = field(default_factory=dict)

    def identity_anchor_snapshot(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {}
        for field_name in PROTECTED_IDENTITY_FIELDS:
            value = getattr(self, field_name)
            if isinstance(value, dict):
                snapshot[field_name] = value.copy()
            elif isinstance(value, list):
                snapshot[field_name] = value[:]
            else:
                snapshot[field_name] = value
        return snapshot

    def _restore_identity_anchors(self, snapshot: dict[str, Any]) -> None:
        for field_name, value in snapshot.items():
            if isinstance(value, dict):
                setattr(self, field_name, value.copy())
            elif isinstance(value, list):
                setattr(self, field_name, value[:])
            else:
                setattr(self, field_name, value)

    def update_from_move(
        self, action: str, dialogue: str, motivation: dict[str, Any] | str | None
    ) -> None:
        identity_snapshot = self.identity_anchor_snapshot()
        motivation_data = motivation if isinstance(motivation, dict) else {}
        if isinstance(motivation, str) and motivation and not motivation_data:
            motivation_data = {"goal": motivation}

        if motivation_data.get("goal"):
            self.local_task_goal = str(motivation_data["goal"])
            if not self.current_objective:
                self.current_objective = str(motivation_data["goal"])
        if motivation_data.get("tactic"):
            self.local_task_tactic = str(motivation_data["tactic"])
            if not self.short_term_tactic:
                self.short_term_tactic = str(motivation_data["tactic"])
        if motivation_data.get("emotional_driver"):
            self.emotional_state = str(motivation_data["emotional_driver"])

        timestamp = datetime.now(timezone.utc).isoformat()
        self.recent_observations.append(f"[{timestamp}] I did: {action}")
        if dialogue:
            self.recent_observations.append(f"[{timestamp}] I said: {dialogue}")
        if motivation_data:
            goal = motivation_data.get("goal", "")
            tactic = motivation_data.get("tactic", "")
            emotional_driver = motivation_data.get("emotional_driver", "")
            risk_level = motivation_data.get("risk_level", "")
            self.recent_observations.append(
                f"[{timestamp}] My motivation: goal={goal}; tactic={tactic}; emotional_driver={emotional_driver}; risk_level={risk_level}"
            )

        self._restore_identity_anchors(identity_snapshot)

        if len(self.recent_observations) > 20:
            self.recent_observations = self.recent_observations[-20:]

    def remember_event(self, event_summary: str, interpretation: str = "") -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        memory_entry = f"[{timestamp}] {event_summary}"
        self.private_memories.append(memory_entry)

        if interpretation:
            summary_entry = f"[{timestamp}] {interpretation}"
            self.character_memory_summary.append(summary_entry)
        else:
            self.character_memory_summary.append(memory_entry)

        if len(self.private_memories) > 20:
            self.private_memories = self.private_memories[-20:]
        if len(self.character_memory_summary) > 12:
            self.character_memory_summary = self.character_memory_summary[-12:]

    def remember_user_interaction(self, user_name: str, summary: str) -> None:
        if not user_name or not summary:
            return
        relationship = self.relationships.setdefault(
            user_name,
            {
                "entity_type": "user",
                "history": [],
                "trust": self.trust_toward_player,
                "trust_history": [],
                "interaction_count": 0,
                "last_summary": "",
                "relationship_trend": "stable",
            },
        )
        relationship["interaction_count"] = (
            int(relationship.get("interaction_count", 0)) + 1
        )
        relationship["trust"] = self.trust_toward_player
        relationship["last_summary"] = summary
        history = [str(item) for item in relationship.get("history", [])]
        history.append(summary)
        relationship["history"] = _compact_history(history)
        trust_history = [
            int(item)
            for item in relationship.get("trust_history", [])
            if isinstance(item, int | float)
        ]
        trust_history.append(self.trust_toward_player)
        relationship["trust_history"] = trust_history[-8:]
        if len(trust_history) >= 2:
            if trust_history[-1] > trust_history[0]:
                relationship["relationship_trend"] = "improving"
            elif trust_history[-1] < trust_history[0]:
                relationship["relationship_trend"] = "declining"
            else:
                relationship["relationship_trend"] = "stable"

    def cross_session_user_context(self, user_name: str, limit: int = 3) -> list[str]:
        relationship = self.relationships.get(user_name, {}) if user_name else {}
        history = [
            str(item).strip()
            for item in relationship.get("history", [])
            if str(item).strip()
        ]
        return history[-limit:] if limit > 0 else history

    def set_relationship_context(
        self,
        target_name: str,
        *,
        entity_type: str = "character",
        stance: str = "",
        tactical_posture: str = "",
        long_term_goal: str = "",
        medium_term_goal: str = "",
        current_objective: str = "",
        threat_level: str = "",
        usefulness: str = "",
    ) -> None:
        if not target_name:
            return
        relationship = self.relationships.setdefault(
            target_name, {"entity_type": entity_type}
        )
        relationship["entity_type"] = _relationship_text(entity_type) or str(
            relationship.get("entity_type", "character")
        )
        updates = {
            "stance": stance,
            "tactical_posture": tactical_posture,
            "long_term_goal": long_term_goal,
            "medium_term_goal": medium_term_goal,
            "current_objective": current_objective,
            "threat_level": threat_level,
            "usefulness": usefulness,
        }
        for field_name, value in updates.items():
            text = _relationship_text(value)
            if text:
                relationship[field_name] = text

    def relationship_prompt_snapshot(
        self,
        *,
        focus_names: list[str] | None = None,
        secondary_names: list[str] | None = None,
    ) -> dict[str, list[dict[str, str]]]:
        focus_names = [
            str(name).strip() for name in (focus_names or []) if str(name).strip()
        ]
        secondary_names = [
            str(name).strip() for name in (secondary_names or []) if str(name).strip()
        ]
        focus_seen: set[str] = set()
        secondary_seen: set[str] = set()
        focused_threads: list[dict[str, str]] = []
        secondary_threads: list[dict[str, str]] = []

        for target_name in focus_names:
            if target_name in focus_seen:
                continue
            relationship = self.relationships.get(target_name, {})
            if (
                not isinstance(relationship, dict)
                or relationship.get("entity_type") == "user"
            ):
                continue
            focus_seen.add(target_name)
            if not _has_targeted_goal_thread(relationship):
                continue
            focused_threads.append(
                {
                    "name": target_name,
                    "stance": _relationship_text(relationship.get("stance")),
                    "long_term_goal": _relationship_text(
                        relationship.get("long_term_goal")
                    ),
                    "medium_term_goal": _relationship_text(
                        relationship.get("medium_term_goal")
                    ),
                    "current_objective": _relationship_text(
                        relationship.get("current_objective")
                    ),
                    "tactical_posture": _relationship_text(
                        relationship.get("tactical_posture")
                    ),
                }
            )

        for target_name in secondary_names:
            if target_name in secondary_seen or target_name in focus_seen:
                continue
            relationship = self.relationships.get(target_name, {})
            if (
                not isinstance(relationship, dict)
                or relationship.get("entity_type") == "user"
            ):
                continue
            secondary_seen.add(target_name)
            if _has_targeted_goal_thread(relationship):
                continue
            if not _has_lightweight_relationship_posture(relationship):
                continue
            secondary_threads.append(
                {
                    "name": target_name,
                    "stance": _relationship_text(relationship.get("stance")),
                    "tactical_posture": _relationship_text(
                        relationship.get("tactical_posture")
                    ),
                    "threat_level": _relationship_text(
                        relationship.get("threat_level")
                    ),
                    "usefulness": _relationship_text(relationship.get("usefulness")),
                }
            )

        return {
            "focused_threads": focused_threads,
            "secondary_threads": secondary_threads,
        }

    def update_emotional_state(self, event_description: str, impact: int) -> None:
        self.stress_level = max(0, min(10, self.stress_level + (impact < 0)))

        if impact > 5:
            self.emotional_state = "positive"
        elif impact < -5:
            self.emotional_state = "distressed"
        elif impact < -2:
            self.emotional_state = "concerned"

        self.recent_observations.append(
            f"[Emotional shift due to: {event_description}]"
        )

    def to_prompt_identity_context(
        self,
        *,
        relationship_focus_names: list[str] | None = None,
        relationship_secondary_names: list[str] | None = None,
    ) -> str:
        """Goals, voice, relationships, and user context for prompts (no episodic lists).

        Episodic sections (``character_memory_summary``, ``recent_observations``) are
        formatted by ``memory_layer.retrieval`` for read-side ownership (Phase B).
        """
        parts = [
            "Your current state:",
            f"- Core goals: {', '.join(self.core_goals) if self.core_goals else self.long_term_goal}",
            f"- Long-term goal: {self.long_term_goal}",
            f"- Emotional state: {self.emotional_state}",
            f"- Stress level: {self.stress_level}/10",
        ]

        if self.medium_term_goal:
            parts.append(f"- Medium-term goal: {self.medium_term_goal}")
        if self.short_term_tactic:
            parts.append(f"- Current tactic: {self.short_term_tactic}")
        if self.current_objective:
            parts.append(f"- Immediate objective: {self.current_objective}")
        if self.local_task_goal and self.local_task_goal != self.current_objective:
            parts.append(f"- Current local task: {self.local_task_goal}")
        if self.local_task_tactic and self.local_task_tactic != self.short_term_tactic:
            parts.append(f"- Local execution method: {self.local_task_tactic}")
        if self.voice_profile:
            parts.append(f"- Voice profile: {_format_profile(self.voice_profile)}")
        if self.reaction_profile:
            parts.append(
                f"- Reaction profile: {_format_profile(self.reaction_profile)}"
            )
        if self.speech_fingerprint:
            parts.append(
                f"- Speech fingerprint: {_format_profile(self.speech_fingerprint)}"
            )
        if self.hidden_agenda:
            parts.append(f"- Hidden agenda: {self.hidden_agenda}")

        relationship_snapshot = self.relationship_prompt_snapshot(
            focus_names=relationship_focus_names,
            secondary_names=relationship_secondary_names,
        )
        focused_threads = relationship_snapshot["focused_threads"]
        if focused_threads:
            parts.append("\nKey relationship goal threads:")
            for thread in focused_threads:
                parts.append(f"  - {thread['name']}:")
                if thread["stance"]:
                    parts.append(f"    - Stance: {thread['stance']}")
                if thread["long_term_goal"]:
                    parts.append(
                        f"    - Long-term goal toward them: {thread['long_term_goal']}"
                    )
                if thread["medium_term_goal"]:
                    parts.append(
                        f"    - Medium-term goal toward them: {thread['medium_term_goal']}"
                    )
                if thread["current_objective"]:
                    parts.append(
                        f"    - Immediate objective toward them: {thread['current_objective']}"
                    )
                if thread["tactical_posture"]:
                    parts.append(
                        f"    - Tactical posture: {thread['tactical_posture']}"
                    )

        secondary_threads = relationship_snapshot["secondary_threads"]
        if secondary_threads:
            parts.append("\nSecondary present-character posture:")
            for thread in secondary_threads:
                details: list[str] = []
                if thread["stance"]:
                    details.append(f"stance={thread['stance']}")
                if thread["tactical_posture"]:
                    details.append(f"tactical_posture={thread['tactical_posture']}")
                if thread["threat_level"]:
                    details.append(f"threat_level={thread['threat_level']}")
                if thread["usefulness"]:
                    details.append(f"usefulness={thread['usefulness']}")
                if details:
                    parts.append(f"  - {thread['name']}: {'; '.join(details)}")

        user_relationships = [
            (name, rel)
            for name, rel in self.relationships.items()
            if isinstance(rel, dict) and rel.get("entity_type") == "user"
        ]
        if user_relationships:
            parts.append("\nCross-session user relationship context:")
            for rel_name, rel in user_relationships[:1]:
                last_summary = str(rel.get("last_summary", "") or "").strip()
                trend = str(rel.get("relationship_trend", "") or "").strip()
                current_trust = rel.get("trust")
                if last_summary:
                    parts.append(f"  • {rel_name}: {last_summary}")
                if trend:
                    if isinstance(current_trust, int):
                        parts.append(
                            f"  • Relationship trend: {trend} (trust {current_trust}/10)"
                        )
                    else:
                        parts.append(f"  • Relationship trend: {trend}")

        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "personality": self.personality,
            "long_term_goal": self.long_term_goal,
            "medium_term_goal": self.medium_term_goal,
            "short_term_tactic": self.short_term_tactic,
            "current_objective": self.current_objective,
            "local_task_goal": self.local_task_goal,
            "local_task_tactic": self.local_task_tactic,
            "core_goals": self.core_goals,
            "voice_profile": self.voice_profile,
            "reaction_profile": self.reaction_profile,
            "speech_fingerprint": self.speech_fingerprint,
            "emotional_state": self.emotional_state,
            "stress_level": self.stress_level,
            "trust_toward_player": self.trust_toward_player,
            "private_memories": self.private_memories,
            "character_memory_summary": self.character_memory_summary,
            "recent_observations": self.recent_observations,
            "hidden_agenda": self.hidden_agenda,
            "relationships": self.relationships,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CharacterState":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            personality=data.get("personality", ""),
            long_term_goal=data.get("long_term_goal", ""),
            medium_term_goal=data.get("medium_term_goal", ""),
            short_term_tactic=data.get("short_term_tactic", ""),
            current_objective=data.get("current_objective", ""),
            local_task_goal=data.get("local_task_goal", ""),
            local_task_tactic=data.get("local_task_tactic", ""),
            core_goals=data.get("core_goals", []),
            voice_profile=data.get("voice_profile", {}),
            reaction_profile=data.get("reaction_profile", {}),
            speech_fingerprint=data.get("speech_fingerprint", {}),
            emotional_state=data.get("emotional_state", "neutral"),
            stress_level=data.get("stress_level", 0),
            trust_toward_player=data.get("trust_toward_player", 5),
            private_memories=data.get("private_memories", []),
            character_memory_summary=data.get(
                "character_memory_summary", data.get("private_memories", [])
            ),
            recent_observations=data.get("recent_observations", []),
            hidden_agenda=data.get("hidden_agenda", ""),
            relationships=data.get("relationships", {}),
        )
