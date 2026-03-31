"""Pattern-based consequence classifier for continuity system.

Uses structured move data (goal, tactic, action, dialogue) to detect
semantic consequence categories via intent + behavior pattern matching.
"""

from typing import Any

try:
    from continuity_resolved_outcomes import extract_sleeping_surface_candidates
except ImportError:
    from python.rp_app.continuity_resolved_outcomes import (
        extract_sleeping_surface_candidates,
    )

try:
    from scene_exit_detection import (
        detect_exit_from_scene,
        dialogue_has_territorial_removal_language,
    )
except ImportError:
    from python.rp_app.scene_exit_detection import (
        detect_exit_from_scene,
        dialogue_has_territorial_removal_language,
    )

try:
    from continuity_state import ConsequenceCategory, DetectedConsequence
except ImportError:
    from python.rp_app.continuity_state import ConsequenceCategory, DetectedConsequence


class ConsequenceClassifier:
    """Deterministic classifier using intent (goal/tactic) + behavior (action/dialogue) patterns.

    Multi-label by default: accumulates all supported categories per turn
    rather than stopping at first match.
    """

    # Intent signal seeds - broad categories, not exhaustive phrase lists
    INTENT_CONTROL = [
        "control",
        "dominate",
        "assert",
        "claim",
        "establish",
        "maintain control",
        "keep control",
        "hold ground",
        "protect",
        "keep",
        "safe",
        "press",
        "pressure",
    ]
    INTENT_RESIST = [
        "resist",
        "reject",
        "defy",
        "push back",
        "refuse",
        "not submit",
        "not comply",
        "stand ground",
    ]
    INTENT_MEDIATE = [
        "mediate",
        "manage",
        "de-escalate",
        "keep peace",
        "control situation",
        "calm",
        "settle",
    ]
    INTENT_CHALLENGE = [
        "challenge",
        "test",
        "provoke",
        "push limits",
        "assert self",
        "establish presence",
    ]
    INTENT_COMPLY = [
        "comply",
        "accept",
        "agree",
        "go along",
        "follow",
        "cooperate",
        "yield",
    ]
    INTENT_ESCALATE = ["escalate", "intensify", "ramp up", "push harder"]

    # Behavior signal seeds
    BEHAVIOR_DIRECTIVE = [
        "command",
        "order",
        "demand",
        "tell",
        "instruct",
        "warn",
        "threaten",
        "insist",
        "require",
    ]
    BEHAVIOR_POSITIONAL = [
        "stepped between",
        "blocked",
        "moved in front",
        "positioned",
        "interposed",
        "stood before",
        "holds",
        "hold",
    ]
    BEHAVIOR_DISMISSIVE = [
        "dismiss",
        "mock",
        "belittle",
        "ignore",
        "blow off",
        "laugh at",
        "ridicule",
        "taunt",
    ]
    BEHAVIOR_COUNTER = [
        "shove",
        "push away",
        "jerk away",
        "step forward",
        "move into space",
        "close distance",
    ]
    BEHAVIOR_ENTRY = [
        "stepped inside",
        "entered",
        "came in",
        "arrived",
        "stepped in",
        "walked in",
    ]

    def classify_turn(
        self,
        acting_character: str,
        move: dict[str, Any],
        director_decision: dict[str, Any],
        scene_state: dict[str, Any] | None = None,
    ) -> list[DetectedConsequence]:
        """Classify a turn into consequence categories.

        Multi-label: returns all applicable categories, not just first match.
        """
        # Extract structured fields
        goal = str(move.get("motivation", {}).get("goal", "")).lower()
        tactic = str(move.get("motivation", {}).get("tactic", "")).lower()
        action = str(move.get("action", "")).lower()
        dialogue = str(move.get("dialogue", "")).lower()
        tension_shift = str(director_decision.get("tension_shift", "")).lower()
        environment_event = str(director_decision.get("environment_event", "")).lower()

        # Build signal profiles
        intent = self._extract_intent_signals(goal, tactic)
        behavior = self._extract_behavior_signals(action, dialogue)
        if detect_exit_from_scene(move, scene_state, acting_character):
            behavior["exit"] = True

        # Accumulate all detected consequences
        consequences: list[DetectedConsequence] = []

        # Authority patterns
        consequences.extend(
            self._detect_authority(
                acting_character, intent, behavior, action, dialogue, goal
            )
        )

        # Territory patterns
        consequences.extend(
            self._detect_territory(
                acting_character, intent, behavior, action, dialogue, tension_shift
            )
        )

        # Mediation patterns
        consequences.extend(
            self._detect_mediation(
                acting_character, intent, behavior, action, dialogue, goal
            )
        )

        # Tension trajectory
        consequences.extend(
            self._detect_tension(
                acting_character, intent, behavior, action, dialogue, tension_shift
            )
        )

        # Agreement/refusal
        consequences.extend(
            self._detect_agreement(acting_character, intent, behavior, action, dialogue)
        )

        consequences.extend(
            self._detect_structured_sleeping_assignment(
                move=move,
                scene_state=scene_state,
                goal=goal,
                tactic=tactic,
                action=action,
                dialogue=dialogue,
            )
        )

        # Access patterns
        consequences.extend(
            self._detect_access(acting_character, intent, behavior, action, dialogue)
        )

        # Information state
        consequences.extend(
            self._detect_information(
                acting_character, intent, behavior, action, dialogue, goal, tactic
            )
        )

        # Deterministic persistent scene-state signals (shared with scene_grounding)
        consequences.extend(self._detect_persistent_scene_state(move))

        return consequences

    def _detect_persistent_scene_state(
        self, move: dict[str, Any]
    ) -> list[DetectedConsequence]:
        """Lexical scene-state signals; must match ``grounding_state_signals_from_move``."""
        try:
            from scene_grounding import (
                SIGNAL_BANDAGE_APPLIED,
                SIGNAL_PHONE_BROKEN,
                SIGNAL_WEAPON_ON_TABLE,
                grounding_state_signals_from_move,
            )
        except ImportError:
            from python.rp_app.scene_grounding import (
                SIGNAL_BANDAGE_APPLIED,
                SIGNAL_PHONE_BROKEN,
                SIGNAL_WEAPON_ON_TABLE,
                grounding_state_signals_from_move,
            )

        signals = grounding_state_signals_from_move(move)
        results: list[DetectedConsequence] = []
        excerpt_src = f"{move.get('dialogue', '')} {move.get('action', '')}".strip()
        excerpt = excerpt_src[:80] if excerpt_src else ""

        if SIGNAL_PHONE_BROKEN in signals or SIGNAL_WEAPON_ON_TABLE in signals:
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.PHYSICAL_STATE_SET,
                    confidence="strong",
                    source_fields=["dialogue", "action"],
                    excerpt=excerpt,
                )
            )
        if SIGNAL_BANDAGE_APPLIED in signals:
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.MEDICAL_STATE_SET,
                    confidence="strong",
                    source_fields=["dialogue", "action"],
                    excerpt=excerpt,
                )
            )
        return results

    def _extract_intent_signals(self, goal: str, tactic: str) -> dict[str, bool]:
        """Extract intent categories from goal and tactic fields."""
        combined = f"{goal} {tactic}"
        return {
            "control": any(marker in combined for marker in self.INTENT_CONTROL),
            "resist": any(marker in combined for marker in self.INTENT_RESIST),
            "mediate": any(marker in combined for marker in self.INTENT_MEDIATE),
            "challenge": any(marker in combined for marker in self.INTENT_CHALLENGE),
            "comply": any(marker in combined for marker in self.INTENT_COMPLY),
            "escalate": any(marker in combined for marker in self.INTENT_ESCALATE),
        }

    def _extract_behavior_signals(self, action: str, dialogue: str) -> dict[str, bool]:
        """Extract behavior categories from action and dialogue."""
        combined = f"{action} {dialogue}"
        return {
            "directive": any(marker in combined for marker in self.BEHAVIOR_DIRECTIVE),
            "positional": any(
                marker in combined for marker in self.BEHAVIOR_POSITIONAL
            ),
            "dismissive": any(
                marker in combined for marker in self.BEHAVIOR_DISMISSIVE
            ),
            "counter": any(marker in combined for marker in self.BEHAVIOR_COUNTER),
            "entry": any(marker in combined for marker in self.BEHAVIOR_ENTRY),
            "exit": False,
        }

    def _detect_authority(
        self,
        character: str,
        intent: dict[str, bool],
        behavior: dict[str, bool],
        action: str,
        dialogue: str,
        goal: str,
    ) -> list[DetectedConsequence]:
        """Detect authority assertion and challenge patterns."""
        results = []

        # AUTHORITY_ASSERTED: control intent + directive or positional behavior
        if intent["control"] and (behavior["directive"] or behavior["positional"]):
            confidence = "strong" if behavior["directive"] else "moderate"
            source = ["motivation.goal"]
            if behavior["directive"]:
                source.append("dialogue")
            if behavior["positional"]:
                source.append("action")

            excerpt = dialogue[:80] if behavior["directive"] else action[:80]
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.AUTHORITY_ASSERTED,
                    confidence=confidence,
                    source_fields=source,
                    excerpt=excerpt,
                )
            )

        # AUTHORITY_CHALLENGED: challenge/resist intent + dismissive/counter behavior
        if (intent["challenge"] or intent["resist"]) and (
            behavior["dismissive"] or behavior["counter"]
        ):
            confidence = "strong" if behavior["dismissive"] else "moderate"
            source = ["motivation.goal"]
            if behavior["dismissive"]:
                source.append("dialogue")
            if behavior["counter"]:
                source.append("action")

            excerpt = dialogue[:80] if behavior["dismissive"] else action[:80]
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.AUTHORITY_CHALLENGED,
                    confidence=confidence,
                    source_fields=source,
                    excerpt=excerpt,
                )
            )

        return results

    def _detect_territory(
        self,
        character: str,
        intent: dict[str, bool],
        behavior: dict[str, bool],
        action: str,
        dialogue: str,
        tension_shift: str,
    ) -> list[DetectedConsequence]:
        """Detect territorial claim, denial, and repositioning patterns."""
        results = []

        # TERRITORIAL_CLAIM: entry with tension escalation
        if behavior["entry"] and tension_shift == "escalate":
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.TERRITORIAL_CLAIM,
                    confidence="strong",
                    source_fields=["action", "director_decision.tension_shift"],
                    excerpt=action[:80],
                )
            )

        # TERRITORIAL_DENIAL: control intent + deterministic removal phrasing only
        if intent["control"] and dialogue_has_territorial_removal_language(dialogue):
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.TERRITORIAL_DENIAL,
                    confidence="strong",
                    source_fields=["motivation.goal", "dialogue"],
                    excerpt=dialogue[:100],
                )
            )

        # REPOSITIONING: positional behavior without full mediation intent
        if behavior["positional"] and not intent["mediate"]:
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.REPOSITIONING,
                    confidence="moderate",
                    source_fields=["action"],
                    excerpt=action[:80],
                )
            )

        # ARRIVAL/EXIT: pure presence changes
        if behavior["entry"] and tension_shift != "escalate":
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.ARRIVAL,
                    confidence="moderate",
                    source_fields=["action"],
                    excerpt=action[:80],
                )
            )

        if behavior["exit"]:
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.EXIT,
                    confidence="strong",
                    source_fields=["action"],
                    excerpt=action[:80],
                )
            )

        return results

    def _detect_mediation(
        self,
        character: str,
        intent: dict[str, bool],
        behavior: dict[str, bool],
        action: str,
        dialogue: str,
        goal: str,
    ) -> list[DetectedConsequence]:
        """Detect mediation and interception patterns."""
        results = []

        # MEDIATION_ATTEMPTED: mediate intent + positional behavior
        if intent["mediate"] and behavior["positional"]:
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.MEDIATION_ATTEMPTED,
                    confidence="strong",
                    source_fields=["motivation.goal", "action"],
                    excerpt=action[:80],
                )
            )

        # INTERCEPTION: resist/control intent + counter-mediator behavior
        if (intent["resist"] or intent["control"]) and behavior["counter"]:
            if "mediat" in goal or any(
                med in action for med in ["shoved", "pushed", "jerked"]
            ):
                results.append(
                    DetectedConsequence(
                        category=ConsequenceCategory.INTERCEPTION,
                        confidence="strong",
                        source_fields=["motivation.goal", "action"],
                        excerpt=action[:80],
                    )
                )

        return results

    def _detect_tension(
        self,
        character: str,
        intent: dict[str, bool],
        behavior: dict[str, bool],
        action: str,
        dialogue: str,
        tension_shift: str,
    ) -> list[DetectedConsequence]:
        """Detect escalation and de-escalation patterns."""
        results = []

        # ESCALATION: tension shift + challenge/escalate intent
        if tension_shift == "escalate" and (
            intent["challenge"] or intent["escalate"] or behavior["directive"]
        ):
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.ESCALATION,
                    confidence="strong" if intent["escalate"] else "moderate",
                    source_fields=[
                        "director_decision.tension_shift",
                        "motivation.goal",
                    ],
                    excerpt=f"tension_shift=escalate, goal excerpt: {action[:40]}",
                )
            )

        # DEESCALATION: soften tension + mediate/comply intent
        if tension_shift == "soften" and (intent["mediate"] or intent["comply"]):
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.DEESCALATION,
                    confidence="moderate",
                    source_fields=[
                        "director_decision.tension_shift",
                        "motivation.goal",
                    ],
                    excerpt=f"tension_shift=soften",
                )
            )

        return results

    def _detect_agreement(
        self,
        character: str,
        intent: dict[str, bool],
        behavior: dict[str, bool],
        action: str,
        dialogue: str,
    ) -> list[DetectedConsequence]:
        """Detect agreement, refusal, and commitment patterns."""
        results = []

        # REFUSAL: resist intent + explicit refusal language
        if intent["resist"] and any(
            ref in dialogue for ref in ["no", "not", "won't", "refuse", "deny"]
        ):
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.REFUSAL,
                    confidence="strong",
                    source_fields=["motivation.goal", "dialogue"],
                    excerpt=dialogue[:80],
                )
            )

        # AGREEMENT: comply intent + explicit acceptance language
        if intent["comply"] and any(
            acc in dialogue for acc in ["yes", "agree", "accept", "fine", "alright"]
        ):
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.AGREEMENT,
                    confidence="strong",
                    source_fields=["motivation.goal", "dialogue"],
                    excerpt=dialogue[:80],
                )
            )

        # COMMITMENT: control intent + future-oriented language
        if intent["control"] and any(
            com in dialogue for com in ["will", "promise", "commit", "shall"]
        ):
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.COMMITMENT,
                    confidence="moderate",
                    source_fields=["motivation.goal", "dialogue"],
                    excerpt=dialogue[:80],
                )
            )

        return results

    def _detect_access(
        self,
        character: str,
        intent: dict[str, bool],
        behavior: dict[str, bool],
        action: str,
        dialogue: str,
    ) -> list[DetectedConsequence]:
        """Detect access granted/denied patterns."""
        results = []

        # ACCESS_DENIED: control/resist intent + blocking language
        if (intent["control"] or intent["resist"]) and any(
            block in dialogue
            for block in ["can't", "cannot", "not allowed", "stay out", "no access"]
        ):
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.ACCESS_DENIED,
                    confidence="strong",
                    source_fields=["motivation.goal", "dialogue"],
                    excerpt=dialogue[:80],
                )
            )

        # ACCESS_GRANTED: control/comply intent + permission language
        if (intent["control"] or intent["comply"]) and any(
            allow in dialogue
            for allow in ["can", "allowed", "permission", "go ahead", "enter"]
        ):
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.ACCESS_GRANTED,
                    confidence="moderate",
                    source_fields=["motivation.goal", "dialogue"],
                    excerpt=dialogue[:80],
                )
            )

        return results

    def _detect_structured_sleeping_assignment(
        self,
        *,
        move: dict[str, Any],
        scene_state: dict[str, Any] | None,
        goal: str,
        tactic: str,
        action: str,
        dialogue: str,
    ) -> list[DetectedConsequence]:
        candidates, _ = extract_sleeping_surface_candidates(move, scene_state)
        if len(candidates) != 1:
            return []

        combined = f"{goal} {tactic} {action} {dialogue}".lower()
        if any(token in combined for token in ("maybe", "might", "guess", "suggest", "option", "?")):
            return []

        results: list[DetectedConsequence] = []
        if any(
            token in combined
            for token in (
                "settle",
                "assign",
                "decide",
                "plan",
                "commit",
                "take the",
                "sleep tonight",
                "sleeps tonight",
                "that's the plan",
                "actual plan",
            )
        ):
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.DECISION_MADE,
                    confidence="strong",
                    source_fields=[
                        "scene_state_updates.sleeping_surface_assignment",
                        "motivation.goal",
                        "motivation.tactic",
                    ],
                    excerpt=dialogue[:80] or action[:80],
                )
            )
        if any(token in combined for token in ("tonight", "will", "plan", "commit")):
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.PLAN_COMMITTED,
                    confidence="moderate",
                    source_fields=[
                        "scene_state_updates.sleeping_surface_assignment",
                        "motivation.goal",
                        "motivation.tactic",
                    ],
                    excerpt=dialogue[:80] or action[:80],
                )
            )
        return results

    def _detect_information(
        self,
        character: str,
        intent: dict[str, bool],
        behavior: dict[str, bool],
        action: str,
        dialogue: str,
        goal: str,
        tactic: str,
    ) -> list[DetectedConsequence]:
        """Detect revelation and concealment patterns."""
        results = []

        # REVELATION: goal/tactic mentions revealing truth
        if any(
            rev in f"{goal} {tactic}"
            for rev in ["reveal", "truth", "admit", "confess", "disclose"]
        ):
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.REVELATION,
                    confidence="moderate",
                    source_fields=["motivation.goal", "motivation.tactic"],
                    excerpt=f"{goal[:60]}...",
                )
            )

        # CONCEALMENT: goal/tactic mentions hiding or deception
        if any(
            con in f"{goal} {tactic}"
            for con in ["conceal", "hide", "keep secret", "not reveal"]
        ):
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.CONCEALMENT,
                    confidence="moderate",
                    source_fields=["motivation.goal", "motivation.tactic"],
                    excerpt=f"{goal[:60]}...",
                )
            )

        return results
