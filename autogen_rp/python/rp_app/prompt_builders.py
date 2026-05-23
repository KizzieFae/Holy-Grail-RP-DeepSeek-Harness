import json
from typing import Any, Callable

from character_move_adapters import is_canonical_v2_move

_EVIDENCE_AUTHORITY_DISCIPLINE_BLOCK = """## **EVIDENCE & AUTHORITY DISCIPLINE (HIGH PRIORITY)**

**Authoritative and institutional framing**—including **clinical** language, **institutional** framing, and a **"recorded"** or **"noted"** tone—**must not introduce unsupported specifics** (concrete who / what / where / when). You may **accuse, pressure, and bluff** in a strong voice, but you must **not present unsupported specific facts as established truth**, especially in those voices.

**Do not introduce new specific facts in an authoritative or institutional tone unless they already appear as facts in this prompt** (e.g. in perception-filtered moves, transcript, public events, scene state, binding constraints, or canon anchors).

**Bluffing is allowed** when it is **contestable in-scene** and framed as **pressure, accusation, hypothesis, or conditional** ("If you were near X…," "Convince me you weren't…," "We'll **treat** this as… unless you explain").

**Bluffing is not allowed** when it is framed as **objective institutional truth** or **settled record** while embedding **new unsupported specifics**—for example, "**Noted**: your commentary **redirected** from **your proximity to the perimeter** during the alarm" when **proximity** was **never** already stated as fact in this prompt.

**Allowed without that support:** Subjective reads ("Your tone **reads** as evasive"), procedural demands ("**Account** for your movements during the alarm"), and **explicitly conditional** or **interrogative** specifics ("**Were** you near the perimeter?").

**Not allowed:** Unsupported particulars presented as **established truth** in **clinical**, **institutional**, or **recorded / noted** voice when those particulars are **not already stated as fact in this prompt**.

"""


def prompt_identity_same(
    a: str,
    b: str,
    display_fn: Callable[[str], str],
) -> bool:
    """True if two labels refer to the same character for prompt purposes (id vs display)."""
    sa = str(a or "").strip()
    sb = str(b or "").strip()
    if not sa or not sb:
        return False
    if sa == sb:
        return True
    ca = str(display_fn(sa)).strip().casefold()
    cb = str(display_fn(sb)).strip().casefold()
    if not ca or not cb:
        return False
    return ca == cb


def build_cast_and_scene_role_participants(
    char_name: str,
    present_characters: list[str] | None,
    session_agent_names: list[str] | None,
    display_fn: Callable[[str], str],
) -> tuple[list[str], list[str]]:
    """Filter others-only cast (ordered, deduped) and participant list for CAST ROLE MAP.

    When ``present_characters`` is non-empty but all entries are the actor (under any label),
    falls back to ``session_agent_names`` like the legacy ``if not cast`` branch.
    """
    actor = str(char_name or "").strip()
    present = [str(x).strip() for x in (present_characters or []) if str(x or "").strip()]
    session = [str(x).strip() for x in (session_agent_names or []) if str(x or "").strip()]

    def _deduped_others(source: list[str]) -> list[str]:
        cast_out: list[str] = []
        for label in source:
            if prompt_identity_same(label, actor, display_fn):
                continue
            if any(prompt_identity_same(label, ex, display_fn) for ex in cast_out):
                continue
            cast_out.append(label)
        return cast_out

    if present:
        cast_out = _deduped_others(present)
        if cast_out:
            return cast_out, [actor] + cast_out
    cast_out = _deduped_others(session)
    return cast_out, [actor] + cast_out


def build_responder_obligation_director_prompt_prefix(
    responder_obligation: dict[str, Any] | None,
) -> str:
    if not isinstance(responder_obligation, dict):
        return ""
    if not responder_obligation.get("active"):
        return ""
    return (
        "[responder_obligation] The JSON payload may include responder_obligation.\n"
        "- Treat responder_obligation as advisory only. It is not forced routing.\n"
        "- Prefer the available actor with the clearest immediate obligation to respond.\n"
        "- Strong obligation comes from direct address, explicit question, accusation or challenge, or a required response to the prior move.\n"
        "- If responder_obligation.confidence is \"high\" and primary_actor is present, you SHOULD prefer that actor unless another available actor more clearly advances the immediate beat; if so, explain why in reason.\n"
        "- If responder_obligation.confidence is \"medium\", treat the listed candidates as plausible obligated responders and use scene judgment.\n"
        "- Do not substitute broad dramatic relevance for a clearly obligated responder.\n\n"
    )


def build_action_responsibility_director_prompt_prefix(
    action_responsibility: dict[str, Any] | None,
) -> str:
    if not isinstance(action_responsibility, dict):
        return ""
    if not action_responsibility.get("active"):
        return ""
    return (
        "[action_responsibility] The JSON payload may include action_responsibility.\n"
        "- Treat action_responsibility as advisory only. It is not forced routing.\n"
        "- Use it only when the next beat is a bounded action handoff or concrete directive outcome rather than a reply beat.\n"
        "- Strong action responsibility comes from ownership of a controlled next step or being the clear target of a concrete immediate directive.\n"
        "- If action_responsibility.confidence is \"high\" and primary_actor is present, you SHOULD prefer that actor unless another available actor more clearly advances the immediate beat; if so, explain why in reason.\n"
        "- If action_responsibility.confidence is \"medium\", treat the listed candidates as plausible bounded action owners and use scene judgment.\n"
        "- Do not substitute broad dramatic relevance for a clearly bounded action owner.\n\n"
    )


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
    payload = dict(director_payload)
    prog = payload.pop("progression_director_hints", None)
    prog_prefix = ""
    if isinstance(prog, dict) and prog.get("active"):
        prog_prefix = str(prog.get("prompt_prefix", "") or "")
    hints = payload.pop("beat_shift_director_hints", None)
    beat_prefix = ""
    if isinstance(hints, dict) and hints.get("active"):
        beat_prefix = str(hints.get("prompt_prefix", "") or "")
    anti = payload.pop("anti_regression_director_hints", None)
    anti_prefix = ""
    if isinstance(anti, dict) and anti.get("active"):
        anti_prefix = str(anti.get("prompt_prefix", "") or "")
    lowp = payload.pop("low_pressure_turn_director_hints", None)
    lowp_prefix = ""
    if isinstance(lowp, dict) and lowp.get("active"):
        lowp_prefix = str(lowp.get("prompt_prefix", "") or "")
    obligation_hints = payload.pop("responder_obligation_director_hints", None)
    obligation_prefix = ""
    if isinstance(obligation_hints, dict) and obligation_hints.get("active"):
        obligation_prefix = build_responder_obligation_director_prompt_prefix(
            payload.get("responder_obligation")
        )
    action_responsibility_hints = payload.pop("action_responsibility_director_hints", None)
    action_responsibility_prefix = ""
    if isinstance(action_responsibility_hints, dict) and action_responsibility_hints.get(
        "active"
    ):
        action_responsibility_prefix = (
            build_action_responsibility_director_prompt_prefix(
                payload.get("action_responsibility")
            )
        )
    settled = str(payload.pop("settled_scene_facts_prompt", "") or "")
    settled_prefix = f"{settled}\n" if settled.strip() else ""
    prefix = (
        f"{prog_prefix}{beat_prefix}{anti_prefix}{lowp_prefix}{obligation_prefix}"
        f"{action_responsibility_prefix}"
        f"{settled_prefix}"
    )
    body = (
        "Decide who acts next using only the structured scene information below. Return JSON only. "
        "If it is best to end the response cycle early, return "
        '{\\"end_round\\": true} with next_actor omitted or empty.\n\n'
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
    return f"{prefix}{body}"


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
    scene_grounding_section: str = "",
    scene_binding_constraints_section: str = "",
    retrieved_context_section: str = "",
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
    offstage_names = [
        str(item)
        for item in (scene_state.get("offstage_characters") or [])
        if str(item or "").strip()
    ]
    offstage_header = ""
    if char_name in offstage_names:
        offstage_header = (
            "OFFSTAGE / PERCEPTUAL SCOPE (CRITICAL):\n"
            "You are not in the immediate shared space with on-stage characters unless the TRIGGER or "
            "DIRECTOR DECISION explicitly establishes a channel (open door, shout, phone/video, etc.).\n"
            "Do not write as if you heard in-room dialogue or saw in-room detail from others unless that "
            "access is justified.\n"
            "RECENT SCENE TRANSCRIPT and RECENT STRUCTURED ACTIONS below are filtered to Traveler posts and "
            "your own prior beats; treat other in-room developments as unknown unless clearly established "
            "otherwise.\n\n"
        )

    grounding = str(scene_grounding_section or "").strip()
    grounding_block = f"{grounding}\n\n" if grounding else ""
    binding_constraints = str(scene_binding_constraints_section or "").strip()
    binding_constraints_block = (
        f"{binding_constraints}\n\n" if binding_constraints else ""
    )
    retrieved = str(retrieved_context_section or "").strip()
    retrieved_block = f"{retrieved}\n\n" if retrieved else ""

    positive_sleeping_assignment_example = json.dumps(
        {
            "move_schema_version": 2,
            "beats": [
                {"type": "action", "action": "pointed at the couch"},
                {"type": "speech", "dialogue": "Take the couch tonight. That's final."},
            ],
            "motivation": {
                "goal": "settle the room",
                "tactic": "issue a firm instruction",
                "emotional_driver": "protective resolve",
                "risk_level": "medium",
            },
            "scene_state_updates": {
                "sleeping_surface_assignment": {
                    "assignee_id": "Kizzie",
                    "surface_id": "couch",
                }
            },
        },
        ensure_ascii=False,
    )
    negative_sleeping_assignment_example = json.dumps(
        {
            "move_schema_version": 2,
            "beats": [
                {"type": "action", "action": "gestured between the couch and the floor"},
                {"type": "speech", "dialogue": "You can take the couch if you want."},
            ],
            "motivation": {
                "goal": "offer an option",
                "tactic": "keep the decision open",
                "emotional_driver": "tentative concern",
                "risk_level": "low",
            },
        },
        ensure_ascii=False,
    )

    return f"""You are taking your next turn in an ongoing roleplay scene.

{offstage_header}{grounding_block}{retrieved_block}CURRENT SCENE STATE:
{json.dumps(scene_state, ensure_ascii=False, indent=2)}

SCENE TEMPLATE:
{json.dumps(scene_template_context, ensure_ascii=False, indent=2)}

YOUR SCENE ROLE:
{json.dumps(my_scene_role, ensure_ascii=False, indent=2)}

CAST ROLE MAP:
{json.dumps(scene_roles, ensure_ascii=False, indent=2)}

RECENT STRUCTURED ACTIONS (PERCEPTION-FILTERED FOR THIS CHARACTER):
{json.dumps(recent_moves, ensure_ascii=False, indent=2)}

RECENT SCENE TRANSCRIPT (PERCEPTION-FILTERED FOR THIS CHARACTER):
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

{binding_constraints_block}{_EVIDENCE_AUTHORITY_DISCIPLINE_BLOCK}
OUTPUT RULES:
- Only output a single JSON object: canonical character move v2 (integer ``move_schema_version`` 2, non-empty ``beats[]``, ``motivation``, optional ``scene_state_updates``, required ``semantic_evaluation``).
- Do not emit root-level ``action``, ``dialogue``, ``audibility``, or ``audience``. Put visible action and speech only inside ``beats[]`` as ``type: action`` or ``type: speech`` objects, in true beat order.
- Root ``semantic_evaluation`` (required every beat): ``decision`` is ``covered_change`` or ``no_covered_change``; include non-empty ``proposals`` only when ``decision`` is ``covered_change`` (self-only proposal items: kinds ``off_focal`` | ``reentry`` | ``excursion_lifecycle``; ``operation`` required only for ``excursion_lifecycle``). When ``decision`` is ``no_covered_change``, omit ``proposals``. Do not emit root ``semantic_proposals`` or ``semantic_proposals: []``.
- Each ``type: action`` beat has non-empty ``action`` (visible self-only, third person). Each ``type: speech`` beat has non-empty ``dialogue``. On speech beats, optional ``audibility`` is one of ``public``, ``directed``, ``private``; omit for public. For ``directed`` or ``private``, include non-empty ``audience`` (names). For public, omit ``audience`` or use ``[]``.
- Keep action beats concrete and observable; let speech sound natural and in-character rather than explanatory.
 - Only include scene_state_updates when your move deterministically settles a bounded scene fact already supported by the beat.
 - For sleeping arrangement settlement, you may include only scene_state_updates.sleeping_surface_assignment with assignee_id and surface_id.
 - For a shared housing / res-life call reaching terminal outcome, you may include only scene_state_updates.housing_call_outcome with status.
- For current suppressant formulation compatibility settlement, you may include only scene_state_updates.suppressant_formulation_outcome with subject_id and status.
- For current location entry permission settlement, you may include only scene_state_updates.location_entry_outcome with subject_id, location_id, and status.
 - surface_id must be exactly one valid allowed surface_id value already present in CURRENT SCENE STATE or SCENE TEMPLATE, or one generic fallback value: floor, couch, cot, or unassigned.
 - Emit sleeping_surface_assignment only when you, as the acting speaker, are establishing, actively enforcing against present resistance or dispute, or explicitly reassigning where someone will sleep in this turn.
 - Contested enforcement vs reminder: Include sleeping_surface_assignment when another present character has just challenged the existing sleeping plan in the current exchange, and your move directly responds by keeping the same assignee_id on the same surface_id, even if your tone is soft, conciliatory, or framed as "already settled." That is contested enforcement, not a reminder. Do not use tone as the deciding factor. Do not include the field when no such challenge is present and your move is only informational, referential, or housekeeping about an assignment nobody is contesting in that exchange.
 - Do not include sleeping_surface_assignment for suggestions, pressure, questions, negotiation, teasing, reactions, observations, reminders, restating prior state, or unresolved argument.
 - Do not include sleeping_surface_assignment solely because the assignment is unchanged unless the contested-enforcement case above applies.
 - Emit housing_call_outcome only when you, as the acting speaker, are explicitly settling the shared housing / res-life call by making it completed or failed in this turn.
 - housing_call_outcome.status must be exactly one of: completed or failed.
 - Do not include housing_call_outcome for discussing, planning, attempting, dialing, waiting on hold, leaving voicemail, or asking whether someone called.
- Emit suppressant_formulation_outcome only when you, as the acting speaker, are explicitly settling whether a named subject's current suppressant formulation is compatible or incompatible in this turn.
- suppressant_formulation_outcome.status must be exactly one of: compatible or incompatible.
- Do not include suppressant_formulation_outcome for symptoms alone, suspicion, diagnosis, dosage changes, treatment planning, or historical formulations.
- Emit location_entry_outcome only when you, as the acting speaker, explicitly settle a named subject's current permission to enter one bounded location in this turn.
- Emit it only for direct permission rulings such as "you may enter" or "you are not allowed inside."
- Do not include location_entry_outcome for requests, predictions, preferences, blocked paths, locked doors, or physical obstruction.
- Do not treat "not yet," "for now," "stay here," "wait," or "until I say otherwise" as permission settlement. These are control instructions, not allowed/denied outcomes.
- Do not include location_entry_outcome for partial, conditional, or fragmented permission that does not clearly resolve to allowed or denied for the specified location.
- Base location_entry_outcome emission on the in-fiction assertion made in the turn, not on whether the speaker has real authority.
- location_entry_outcome.location_id must match the intended in-fiction location exactly. Do not remap, normalize, or substitute it. If the location is outside the allowed set, emit it as-is and let validation reject it.
- location_entry_outcome.status must be exactly one of: allowed or denied.
 - Positive example: {positive_sleeping_assignment_example}
 - Negative example: {negative_sleeping_assignment_example}

"""


def build_narrator_render_prompt(
    *,
    char_name: str,
    action: str,
    dialogue: str,
    environment_event: str,
    scene_context: str,
    structured_move: dict[str, Any] | None = None,
) -> str:
    if structured_move is not None and is_canonical_v2_move(structured_move):
        sm = json.dumps(structured_move, ensure_ascii=False, indent=2)
        return f"""Render the following structured character turn (v2 ``beats[]``) into third-person past-tense scene narration.

CHARACTER: {char_name}
STRUCTURED MOVE (authoritative; render only this visibility scope; do not invent speech):
{sm}
OPTIONAL ENVIRONMENT EVENT: {environment_event}

SCENE CONTEXT:
{scene_context}

RULES:
1. Preserve ``beats[]`` order: do not reorder beats.
2. For each ``type: speech`` beat, the ``dialogue`` string must appear in your output as a contiguous **verbatim** substring, in the same order as in ``beats`` (you may add connective narrator prose between beats; adjacent speech may be merged in prose only if every speech line still appears as an exact, ordered substring).
3. For ``type: action`` beats, you may paraphrase the action text in third person; do not treat action text as a verbatim substring requirement.
4. Do not add new spoken lines or quoted speech that are not substrings of the provided speech lines (narrator connective prose without quotes is allowed between beats).
5. If you include optional environment event material, work it in naturally; do not contradict the structured move.
6. Only describe this character for action/speech; no other character dialogue.
7. Be concise (roughly 2-6 short sentences or one tight paragraph).
8. Write in third person past tense.

OUTPUT ONLY the rendered narration (no preface, no JSON)."""

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
