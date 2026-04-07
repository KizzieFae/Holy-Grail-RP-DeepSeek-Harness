"""Pattern-based consequence classifier for continuity system.

Uses structured move data (goal, tactic, action, dialogue) to detect
semantic consequence categories via intent + behavior pattern matching.
"""

import re
from typing import Any

# Geometry: "turn" only counts as movement when a standalone verb and not negated
# (avoids "did not turn", "didn't turn", "not turning", etc.).
_GEOMETRY_NEGATED_TURN_PHRASE = re.compile(
    r"(?:did\s+not|didn't|does\s+not|don't)\s+turn(?:ed|s|ing)?\b|\bnot\s+turn(?:ed|s|ing)?\b",
    re.IGNORECASE,
)
_GEOMETRY_TURN_VERB = re.compile(r"\bturn(?:ed|s|ing)?\b", re.IGNORECASE)

# REFUSAL legacy: standalone words only (avoids "nothing", "notice", "know", "snow", etc.).
_REFUSAL_LEGACY_NO_OR_NOT_WORD = re.compile(r"\b(?:no|not)\b", re.IGNORECASE)

# ACCESS_GRANTED: "can" must not match inside "can't" (ASCII or Unicode apostrophe).
_ACCESS_GRANTED_CAN_WORD = re.compile(
    r"\bcan\b(?!['\u2019]t\b)",
    re.IGNORECASE,
)
# AGREEMENT: whole-word only (avoids yes/yesterday, agree/disagree, fine/refine).
_AGREEMENT_BOUNDARY_WORDS = re.compile(
    r"\b(?:yes|agree|fine|alright)\b",
    re.IGNORECASE,
)
# COMMITMENT: "will" must not match inside compounds like "goodwill".
_COMMITMENT_WILL_WORD = re.compile(r"\bwill\b", re.IGNORECASE)

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
        "disengage",
        "ultimatum",
        "stalemate",
        "walk away",
        "walking away",
        "withhold",
        "noncompliant",
        "non-compliant",
        "break the stalemate",
        "break stalemate",
        "forcing a",
        "force a",
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
        "call the bluff",
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

    # Discrete loci for interaction-geometry repositioning (action/dialogue substrings).
    INTERACTION_LOCUS_MARKERS = frozenset(
        {
            "table",
            "chair",
            "door",
            "doorway",
            "counter",
            "kitchen",
            "sink",
            "window",
            "hall",
            "hallway",
            "couch",
            "sofa",
            "bed",
            "desk",
            "wall",
            "corner",
            "backrest",
            "apartment",
            "room",
        }
    )

    # Path / transition cues: movement between or around loci (primarily action).
    INTERACTION_TRANSITION_MARKERS = [
        " to the ",
        " to ",
        " from the ",
        " off the ",
        " off of ",
        " around ",
        " behind ",
        " toward",
        " towards",
        " into the ",
        " into ",
        " across ",
        " back to",
        " away from",
        " out of",
        " over to",
        " up to",
        " onto ",
        " around the",
        " behind the",
    ]

    # Strong movement lemmas (substring match on action). "turn" handled via
    # ``_geometry_movement_present`` (word-boundary + negation scrub).
    GEOMETRY_MOVEMENT_MARKERS = [
        "walk",
        "step",
        "mov",
        "push",
        "pull",
        "cross",
        "circl",
        "retreat",
        "advanc",
        "withdraw",
        "pace",
        "rush",
        "dart",
        "stalk",
        "stomp",
        "lung",
        "round the",
        "straighten",
        "rose ",
        "rise ",
    ]

    # Stasis / cosmetic posture: no geometry path unless paired with movement markers above.
    GEOMETRY_STASIS_LEADERS = (
        "remained ",
        "stayed ",
        "still leaning",
        "still seated",
        "still sitting",
    )
    GEOMETRY_COSMETIC_ONLY_MARKERS = [
        "exhaled",
        "exhale",
        "narrowed her",
        "narrowed his",
        "narrowed their",
        "tilted her head",
        "tilted his head",
        "tapped the",
        "smiled",
        "nodded",
        "shrugged",
    ]

    # REFUSAL: curated dialogue substrings (no bare "no"/"not" alone — those stay in legacy).
    REFUSAL_DIALOGUE_MARKERS = [
        "bullshit",
        "ultimatum",
        "no deal",
        "won't",
        "wont",
        "done pretending",
        "screw you",
        "hell no",
        "fat chance",
        "not happening",
        "not buying",
        "over my dead",
        "never going to",
        "ain't going",
        "aren't going",
        "won't work",
        "not your terms",
        "not interested",
    ]

    # Strong refusal stance in goal/tactic only (second factor without dialogue markers).
    REFUSAL_STRONG_INTENT_MARKERS = [
        "ultimatum",
        "disengage",
        "withhold compliance",
        "withhold agreement",
        "reject terms",
        "reject the terms",
        "deny the demand",
        "break off",
        "walk away",
        "walking away",
        "noncompliant",
        "non-compliant",
    ]

    # Legacy dialogue gate (still requires resist/challenge intent via merged logic).
    # "no"/"not" use word-boundary matching in _detect_agreement; other tokens stay substring.
    REFUSAL_LEGACY_DIALOGUE_MARKERS = ["no", "not", "won't", "refuse", "deny"]

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
            self._detect_agreement(
                acting_character, intent, behavior, action, dialogue, goal, tactic
            )
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

        return self._dedupe_detected_consequences(consequences)

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

    def _geometry_movement_present(self, action: str) -> bool:
        """True if action has a geometry-relevant movement cue (substring markers or non-negated *turn* verb)."""
        lowered = action.lower()
        for m in self.GEOMETRY_MOVEMENT_MARKERS:
            if m in lowered:
                return True
        scrubbed = _GEOMETRY_NEGATED_TURN_PHRASE.sub(" ", lowered)
        return bool(_GEOMETRY_TURN_VERB.search(scrubbed))

    def _dedupe_detected_consequences(
        self, items: list[DetectedConsequence]
    ) -> list[DetectedConsequence]:
        """Keep first occurrence per category; preserve multi-label distinct categories."""
        seen: set[str] = set()
        out: list[DetectedConsequence] = []
        for item in items:
            key = item.category.value
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    def _is_geometry_stasis_or_cosmetic_dominant(self, action: str) -> bool:
        """True when action reads as in-place posture/micro-motion without locomotion."""
        if any(leader in action for leader in self.GEOMETRY_STASIS_LEADERS):
            if not self._geometry_movement_present(action):
                return True
        # Cosmetic-only markers without locomotion cues
        if any(c in action for c in self.GEOMETRY_COSMETIC_ONLY_MARKERS):
            if not self._geometry_movement_present(action):
                return True
        return False

    def _action_indicates_geometry_repositioning(
        self, action: str, dialogue: str
    ) -> bool:
        """Meaningful interaction-geometry change: locomotion + transition/locus."""
        if self._is_geometry_stasis_or_cosmetic_dominant(action):
            return False
        if not self._geometry_movement_present(action):
            return False
        has_transition = any(t in action for t in self.INTERACTION_TRANSITION_MARKERS)
        has_locus_action = any(
            locus in action for locus in self.INTERACTION_LOCUS_MARKERS
        )
        has_locus_dialogue = any(
            locus in dialogue for locus in self.INTERACTION_LOCUS_MARKERS
        )
        dialogue_path_transition = any(
            t in dialogue for t in (" to the ", " into the ", " toward", " towards")
        )

        if has_transition and (has_locus_action or has_locus_dialogue):
            return True
        # Movement + locus in action + spatial relation (e.g. around/behind/toward chair)
        if has_locus_action and (
            " around " in action
            or " behind " in action
            or " toward" in action
            or " towards" in action
            or " off the " in action
            or " off of " in action
        ):
            return True
        # Optional: dialogue names locus + path language; action still shows locomotion
        if has_locus_dialogue and dialogue_path_transition:
            return True
        return False

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

        # REPOSITIONING: blocking/interposition OR meaningful geometry change; not exit/mediation
        repositioning = False
        if not intent["mediate"] and not behavior["exit"]:
            if behavior["positional"]:
                repositioning = True
            elif self._action_indicates_geometry_repositioning(action, dialogue):
                repositioning = True
        if repositioning:
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
        goal: str,
        tactic: str,
    ) -> list[DetectedConsequence]:
        """Detect agreement, refusal, and commitment patterns."""
        results = []

        # REFUSAL: (resist OR challenge) intent from goal/tactic AND (dialogue OR strong intent)
        intent_refusal = intent["resist"] or intent["challenge"]
        combined_gt = f"{goal} {tactic}"
        if intent_refusal:
            legacy_short = bool(_REFUSAL_LEGACY_NO_OR_NOT_WORD.search(dialogue))
            legacy_other = any(
                ref in dialogue
                for ref in self.REFUSAL_LEGACY_DIALOGUE_MARKERS
                if ref not in ("no", "not")
            )
            legacy_hit = legacy_short or legacy_other
            curated_hit = any(
                tok in dialogue for tok in self.REFUSAL_DIALOGUE_MARKERS
            )
            strong_intent_hit = any(
                tok in combined_gt for tok in self.REFUSAL_STRONG_INTENT_MARKERS
            )
            if legacy_hit or curated_hit or strong_intent_hit:
                results.append(
                    DetectedConsequence(
                        category=ConsequenceCategory.REFUSAL,
                        confidence="strong",
                        source_fields=["motivation.goal", "motivation.tactic", "dialogue"],
                        excerpt=dialogue[:80] or action[:80],
                    )
                )

        # AGREEMENT: comply intent + explicit acceptance language
        if intent["comply"] and (
            _AGREEMENT_BOUNDARY_WORDS.search(dialogue) or "accept" in dialogue
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
        if intent["control"] and (
            _COMMITMENT_WILL_WORD.search(dialogue)
            or any(com in dialogue for com in ["promise", "commit", "shall"])
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

        # Same phrases for denied and for suppressing false "enter" grant evidence.
        access_denial_markers = (
            "can't",
            "can\u2019t",
            "cannot",
            "not allowed",
            "stay out",
            "no access",
        )
        denial_in_dialogue = any(m in dialogue for m in access_denial_markers)

        # ACCESS_DENIED: control/resist intent + blocking language
        if (intent["control"] or intent["resist"]) and denial_in_dialogue:
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.ACCESS_DENIED,
                    confidence="strong",
                    source_fields=["motivation.goal", "dialogue"],
                    excerpt=dialogue[:80],
                )
            )

        # ACCESS_GRANTED: control/comply intent + permission language
        enter_grant_evidence = "enter" in dialogue and not denial_in_dialogue
        if (intent["control"] or intent["comply"]) and (
            _ACCESS_GRANTED_CAN_WORD.search(dialogue)
            or any(
                allow in dialogue
                for allow in ["allowed", "permission", "go ahead"]
            )
            or enter_grant_evidence
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
