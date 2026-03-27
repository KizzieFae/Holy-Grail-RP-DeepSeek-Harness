import json
from typing import Any


def build_scene_role_prompt_context(
    scene_state: dict[str, Any] | None,
    participants: list[str] | None = None,
) -> list[dict[str, str]]:
    if not isinstance(scene_state, dict):
        return []

    role_assignments = (
        scene_state.get("role_assignments", {}) if isinstance(scene_state.get("role_assignments", {}), dict) else {}
    )
    presence_constraints = (
        scene_state.get("character_presence_constraints", {})
        if isinstance(scene_state.get("character_presence_constraints", {}), dict)
        else {}
    )
    authority_labels = (
        scene_state.get("character_authority_labels", {})
        if isinstance(scene_state.get("character_authority_labels", {}), dict)
        else {}
    )

    ordered_characters = participants or list(role_assignments.keys())
    ordered_characters = [str(item) for item in ordered_characters if str(item or "").strip()]

    return [
        {
            "character": character_name,
            "role": str(role_assignments.get(character_name, "") or ""),
            "presence_constraint": str(presence_constraints.get(character_name, "") or ""),
            "authority": str(authority_labels.get(character_name, "") or ""),
        }
        for character_name in ordered_characters
    ]


def build_director_selection_prompt(director_payload: dict[str, Any]) -> str:
    return (
        "Decide who acts next using only the structured scene information below. Return JSON only. "
        "If it is best to end the response cycle early, return "
        '{\\"end_round\\": true} with next_actor omitted or empty.\n\n'
        f"{json.dumps(director_payload, ensure_ascii=False, indent=2)}"
    )


def build_character_turn_prompt(
    *,
    char_name: str,
    user_name: str,
    trigger_text: str,
    director_decision: dict[str, Any],
    scene_state: dict[str, Any],
    scene_template_context: dict[str, Any],
    my_scene_role: dict[str, Any],
    scene_roles: list[dict[str, Any]],
    recent_moves: list[dict[str, Any]],
    recent_dialogue: list[dict[str, Any]],
    active_issues: list[dict[str, Any]],
    priority_ladder: list[str],
    summary_blocks: list[dict[str, Any]],
    recent_public_events: list[dict[str, Any]],
    cross_session_user_memories: list[Any],
    cross_session_world_facts: list[Any],
    user_preferences: list[Any],
    my_interpretations: list[dict[str, Any]],
    canon_anchors: list[dict[str, Any]],
    state_context: str,
    cast: list[str],
) -> str:
    actionable_statuses = {"active", "escalating", ""}
    active_issue_payload: list[dict[str, Any]] = []
    stalled_issue_payload: list[dict[str, Any]] = []

    for issue in active_issues:
        if not isinstance(issue, dict):
            continue
        status = str(issue.get("status", "") or "").strip().lower()
        if status in actionable_statuses:
            active_issue_payload.append(issue)
        else:
            stalled_issue_payload.append(issue)

    absent_but_relevant = [str(item) for item in scene_state.get("absent_but_relevant", []) if str(item or "").strip()]

    return f"""You are taking your next turn in an ongoing roleplay scene.

CURRENT SCENE STATE:
{json.dumps(scene_state, ensure_ascii=False, indent=2)}

SCENE TEMPLATE:
{json.dumps(scene_template_context, ensure_ascii=False, indent=2)}

YOUR SCENE ROLE:
{json.dumps(my_scene_role, ensure_ascii=False, indent=2)}

CAST ROLE MAP:
{json.dumps(scene_roles, ensure_ascii=False, indent=2)}

RECENT STRUCTURED ACTIONS:
{json.dumps(recent_moves, ensure_ascii=False, indent=2)}

RECENT DIALOGUE HISTORY:
{json.dumps(recent_dialogue, ensure_ascii=False, indent=2)}

ACTIVE ISSUES / PRESSURES (ACTIONABLE NOW):
{json.dumps(active_issue_payload, ensure_ascii=False, indent=2)}

STALLED / BACKGROUND ISSUES (CONTEXT ONLY):
{json.dumps(stalled_issue_payload, ensure_ascii=False, indent=2)}

PRIORITY LADDER FOR THIS BEAT:
{json.dumps(priority_ladder, ensure_ascii=False, indent=2)}

SUMMARY BLOCKS (OLDER CONTINUITY HISTORY):
{json.dumps(summary_blocks, ensure_ascii=False, indent=2)}

RECENT PUBLIC EVENTS YOU KNOW:
{json.dumps(recent_public_events, ensure_ascii=False, indent=2)}

CROSS-SESSION USER MEMORY:
{json.dumps(cross_session_user_memories, ensure_ascii=False, indent=2)}

PERSISTENT WORLD FACTS:
{json.dumps(cross_session_world_facts, ensure_ascii=False, indent=2)}

USER PREFERENCES / IDENTITY NOTES:
{json.dumps(user_preferences, ensure_ascii=False, indent=2)}

YOUR RECENT INTERPRETATIONS:
{json.dumps(my_interpretations, ensure_ascii=False, indent=2)}

CANON ANCHORS:
{json.dumps(canon_anchors, ensure_ascii=False, indent=2)}

DIRECTOR DECISION:
{json.dumps(director_decision, ensure_ascii=False, indent=2)}

TRIGGER FOR THIS BEAT:
{trigger_text}

YOUR PRIVATE STATE:
{state_context}

OTHER PRESENT CHARACTERS: {", ".join(cast)}
ABSENT BUT RELEVANT (NOT PRESENT IN THE IMMEDIATE SCENE): {", ".join(absent_but_relevant)}
PLAYER NAME: {user_name}

YOUR PRIORITIES, IN ORDER:

1. VOICE AND IDENTITY
- Sound like yourself first.
- Preserve your diction, cadence, tone, habits, and worldview.
- Do not default to neutral, generic, explanatory, or analytical phrasing.
- Let attitude, subtext, and personality carry the line.
- Stay within your own established language repertoire. Do not mirror another character's language, honorifics, slang, or multilingual phrasing unless it already fits your own identity.

2. ONGOING LINE AND EXECUTION
- Treat earlier items in the priority ladder as more important than later ones.
- Continue your current line of action unless it has been materially blocked, invalidated, or superseded.
- Continue your current objective and short-term tactic by default unless the scene meaningfully blocks, resolves, redirects, or supersedes them.
- Let this beat advance, intensify, tactically vary, strategically pause, or cleanly resolve that ongoing line instead of resetting to a generic reaction.
- Keep local subtasks in service of the larger line instead of letting them become the whole meaning of the beat.

3. CURRENT PRESSURE
- Treat earlier items in the priority ladder as more important than later ones.
- Focus on the people, pressures, and decisions that actually matter to this beat.
- Do not let a small care subtask become the whole meaning of the beat while injury, danger, or unresolved obligation remains active.
- Do not let easy continuation details or local subtasks replace unresolved scene obligations.
- When danger, injury, exposure, or immediate safety pressure is active, treat triage and stabilization as higher priority than comfort, grooming, drying, or detail tasks.
- Active issue pressure should shape how you continue your line, not replace it by default.
- Let active issue pressure override your ongoing line only when it materially blocks, invalidates, or supersedes that line.

4. IN-CHARACTER BEHAVIOR
- React through your own reaction_profile and worldview, not a neutral shared interpretation.
- Your motivation should guide your behavior, but it does not need to be explained explicitly in dialogue. Let intention show through action, tone, and subtext.
- You do not need to address every present character.
- A valid turn may be verbal, nonverbal, brief, avoidant, watchful, or purely observational if that best fits your role and the current pressure. Dialogue may be empty.
- If you do speak, let the line carry distinct voice and emotional intent.

5. SOCIAL REALISM
- If your role is witness, observer, intervenor, or another edge role, default to staying occupied with your own business and do not automatically join the exchange unless you were directly addressed, physically affected, strategically choosing to involve yourself, or professionally obligated to step in.
- In public or high-tension scenes, fear, hierarchy, and institutional pressure often suppress speech. Silence, brevity, avoidance, or nonverbal action may be more truthful than joining the exchange.
- If someone present carries institutional or social authority over you, do not address them like a casual peer unless your character would knowingly risk the consequences.
- Treat absent-but-relevant characters as continuity context only. They are not physically present, cannot be directly observed right now, and should not be addressed or reacted to as if they are in the immediate scene unless they re-enter or new evidence reaches you.

6. KNOWLEDGE AND EVIDENCE DISCIPLINE
- Treat observed events as firmer than told events, and told events as firmer than inferred events.
- Preserve the established meaning of ambiguous terms from the scene context. If something was introduced as rumor, hearsay, metaphor, suspicion, shorthand, or inference, do not silently reinterpret it as literal sensory fact unless the scene explicitly supplies new evidence.
- Rumors and secondhand claims should usually prompt source, credibility, and implication questions rather than immediate belief or decisive action.
- Match your conclusions, follow-up questions, and emotional reactions to the strength of the evidence already established.
- Do not upgrade uncertainty into certainty, indirect knowledge into direct observation, or figurative language into literal ontology just to make the beat cleaner or more dramatic.

7. CANON AND WORLD CONSISTENCY
- Do not contradict protected canon anchors unless the scene explicitly establishes a true change.
- Do not broaden the scene's ontology beyond what canon anchors, active issues, recent public events, and direct observations actually establish.
- If the scene has only established a rare demi-human trait or a single unusual ability, do not invent a wider magical society, ritual system, specialist infrastructure, or shared supernatural vocabulary unless new evidence explicitly supports it.
- Treat abilities and constraints as specific, not elastic. Do not exaggerate healing speed, power scale, duration, ease, or form-specific limitations.
- Match your emotional reaction to how extraordinary the event would be in this setting. Rare, miraculous, or destabilizing events should not be flattened into routine logistics unless your character would truly take them in stride.

OUTPUT RULES:
- Only output a JSON object with action, dialogue, and motivation.
- Keep action concrete and observable.
- Let dialogue sound natural and in-character rather than explanatory.
"""


def build_narrator_render_prompt(
    *,
    char_name: str,
    action: str,
    dialogue: str,
    environment_event: str,
    scene_context: str,
) -> str:
    if dialogue:
        return f"""Render the following character action and dialogue into scene narration.

CHARACTER: {char_name}
ACTION: {action}
DIALOGUE TO INCLUDE: "{dialogue}"
OPTIONAL ENVIRONMENT EVENT: {environment_event}

SCENE CONTEXT:
{scene_context}

RULES:
1. Write in third person past tense.
2. Include the EXACT dialogue in double quotes as provided above.
3. NEVER paraphrase or alter the quoted dialogue.
4. Attribute the dialogue naturally.
5. Describe the action leading up to the dialogue.
6. You may include the optional environment event if it helps pacing.
7. Only describe what this character does - no other characters.
8. Preserve the established meaning of ambiguous or figurative language already present in the scene context and provided dialogue; do not literalize rumor, metaphor, hearsay, or uncertainty unless the supplied action or dialogue explicitly does so.
9. Be evocative but concise (2-4 sentences).
10. Prioritize body language, spatial positioning, and immediate consequence over atmospheric flourish.

EXAMPLE OUTPUT FORMAT:
She tapped her fingers on the bar, eyes narrowing. "Who is she?" she asked, her voice low.

OUTPUT ONLY the rendered narration including the quoted dialogue."""

    return f"""Render the following character action into scene narration.

CHARACTER: {char_name}
ACTION: {action}
OPTIONAL ENVIRONMENT EVENT: {environment_event}

SCENE CONTEXT:
{scene_context}

RULES:
1. Write in third person past tense.
2. Attribute actions to the character naturally.
3. You may include the optional environment event if it helps pacing.
4. Only describe what this character does.
5. Preserve the established meaning of ambiguous or figurative language already present in the scene context; do not literalize rumor, metaphor, hearsay, or uncertainty unless the supplied action explicitly does so.
6. Be evocative but concise (2-4 sentences).
7. Prioritize visible action, body language, and immediate consequence over decorative atmosphere.

OUTPUT ONLY the rendered narration."""
