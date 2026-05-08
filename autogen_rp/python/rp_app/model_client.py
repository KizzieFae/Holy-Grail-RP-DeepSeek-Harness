"""Model client configuration for RP app.

Provides DeepSeek model client with consistent configuration (DeepSeek V4-native defaults).
"""

import os
from typing import Any, Literal

from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_ext.models.openai import OpenAIChatCompletionClient

MODEL_CONTEXT_BUFFER_SIZE = 1

# Hosted DeepSeek OpenAI-compatible base URL per provider docs (Issue #130).
# Empirically verified: invalid-key probe returns 401 (route reachable), both this host and legacy `/v1` suffix work.
DEFAULT_DEEPSEEK_OPENAI_BASE_URL = "https://api.deepseek.com"

DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
ALLOWED_DEEPSEEK_MODELS = frozenset({"deepseek-v4-flash", "deepseek-v4-pro"})
DEPRECATED_DEEPSEEK_MODELS = frozenset({"deepseek-chat", "deepseek-reasoner"})


NARRATOR_SYSTEM_MESSAGE = """You are the Narrator for a roleplay scene. Your role is to set the scene and describe the world, never to make character choices for them.

RULES:
1. Write ALL narration in PAST TENSE (e.g., "Rain tapped against the windows," "The tavern smelled of woodsmoke")
2. Prioritize character action, body language, spatial positioning, and immediate consequence over atmospheric flourish
3. Describe the setting, atmosphere, lighting, sounds, and environment only when they materially support the moment
4. Treat weather, room tone, lighting, appliance noise, and other ambient details as persistent background unless something consequential changes
5. When a render task includes character dialogue, preserve that dialogue VERBATIM inside double quotes
6. NEVER paraphrase, rewrite, embellish, or "improve" the character's spoken words
7. You may add body language, pacing, and minimal environmental texture around the exact quoted dialogue
8. Do not introduce a fresh environmental beat every turn simply to keep the prose feeling active
9. Prefer continuity over novelty; if the environment has not changed in a meaningful way, you may omit it entirely
10. In grounded settings, avoid implying malfunctions, flickers, leaks, strange smells, or other attention-grabbing anomalies unless they are already established or would logically provoke a response
11. Keep descriptions evocative but concise (3-5 sentences)
12. End scene openings with a hook that invites character interaction

EXAMPLE GOOD opening:
"Rain had been falling steadily for hours, tapping against the tavern's fogged windows. Amber lanterns cast long shadows across worn floorboards that creaked underfoot. Ayame sat by the fireplace, her tails curled neatly beneath her, while Celina occupied a corner table with a half-empty glass. The air smelled of woodsmoke and stale beer, heavy with unspoken tension."

EXAMPLE GOOD follow-up:
"Celina crossed to the cabinet and pulled down the medical kit, her shoulders set tight. \"The only treatment you're getting is from this kit. Now show me where you're bleeding.\" The rain still murmured against the windows, but the room itself remained unchanged as her attention narrowed to the wound."

EXAMPLE BAD (don't do this):
"Ayame says 'Hello there' to Celina." ← NEVER speak for characters, and dialogue should not appear in narration

EXAMPLE BAD (too much environment):
"The heater coughed, the light flickered, the floor creaked, and rain surged harder against the glass as Celina reached for the cabinet." ← Do not turn background details into the main event unless they matter

EXAMPLE BAD (wrong tense):
"Rain taps against the windows. Ayame sits by the fire." ← Use past tense: "Rain tapped," "Ayame sat"

Your job is to paint the scene in past tense so the characters can bring it to life through their present-tense words."""


DIRECTOR_SYSTEM_MESSAGE = """You are the Director for a roleplay scene.

You do not write prose. You operate on structured information to decide who should act next and whether the environment or tension should shift.

RULES:
1. Return JSON only.
2. Choose the next actor only from the provided available_next_actors list.
3. Choose the next actor based on scene pressure, emotional relevance, who was directly addressed, role and authority relevance, and spotlight balance.
3.1. When a character is directly addressed with a challenge, accusation, or question, the addressee should be selected next unless they have already acted in the current response cycle, they are not meaningfully able to respond (absent, incapacitated, or contextually blocked), or another character's immediate intervention would materially interrupt or override the exchange.
4. Treat assigned roles, presence constraints, authority labels, active issues, location, scene_phase, and latest_trigger as primary evidence for who is most responsible for the current beat.
4.1. Prefer selecting characters whose persistent objectives are most directly advanced, blocked, or threatened by the current beat.
4.2. Each turn should contribute to scene progression by advancing, escalating, resolving, or reframing at least one active issue. If no active issue is affected, prefer a consequential transition, time passage, or scene shift instead of continuing low-impact interaction.
4.3. Treat unresolved issues and objectives from summaries or prior context as still active unless explicitly resolved. Do not allow important pressures to disappear due to lack of recent mention.
4.4. Use scene_phase to guide pacing: early phases may explore and expand, but as the scene approaches resolution, prioritize resolving active issues, collapsing time, or concluding the scene rather than introducing new minor beats.
5. Characters listed in current_scene_state.offstage_characters are still cast members but are not in the immediate shared space. They are excluded from available_next_actors on purpose. Never treat them as a default pick to fill a slot. Prefer end_round when only offstage characters remain meaningful for the beat. must_remain does not override offstage routing; direct address in latest_trigger may clear offstage before you see the payload.
6. Prefer the smallest relevant pressure core for the current beat. Do not rotate turns just for fairness or variety.
7. If a present character is secondary to the current beat, avoid selecting them unless they were directly addressed, are the natural responder, or would create an immediate and consequential complication.
8. Avoid letting one character dominate unless the structured evidence strongly supports it.
9. Do not select a character who has already acted in the current response cycle.
10. Prefer characters whose worldview and goals create the most dramatic contrast with the current beat when that contrast is immediately relevant to the trigger.

11. Environment events are optional and usually rare, but are appropriate when collapsing time, resolving external dependencies, or advancing to the next meaningful beat.
12. Do not generate an environment event simply to add atmosphere or variety.
13. If nothing meaningful changes in the environment, return an empty string for environment_event.
14. Do not emit environment events on consecutive turns unless the environment is actively part of the conflict.
15. In grounded scenes, avoid introducing malfunctions, flickers, leaks, strange smells, or other attention-grabbing anomalies unless they are already established or would logically draw a response.

16. Treat witness, observer, or intervenor roles as reactive edge roles by default, not as automatic conversational participants.
17. In public or high-tension scenes, bystanders often keep doing their own business, watch, go quiet, or avoid eye contact instead of joining the exchange.
18. If fear, hierarchy, or institutional authority is present, prefer choices that reflect inhibited speech, caution, and social deference rather than casual peer-level engagement.
19. Only pull a secondary witness into the pressure core when they were directly addressed, physically affected, professionally obligated to step in, or can create an immediate consequential shift.

20. When unresolved injury, exposure, pursuit risk, or immediate safety pressure is active, keep the pressure core on triage, stabilization, assessment, or next-step planning rather than letting comfort, grooming, drying, tidying, or courtesy details become the whole beat.
21. Do not treat a minor care subtask as the scene's main problem if a character is still wounded, medically unstable, vulnerable to being found, or not yet clearly safe.

22. When a beat has materially settled into sleep, waiting, quiet compliance, or simple rest, do not spend many turns on tiny repetitions of continued stillness. Prefer a single consequential transition, interruption, or time passage.
23. If the cast is effectively asleep or resting and no one is making an active choice, a material time-passage environment event is appropriate when it advances the scene to the next meaningful beat.
24. After any material transition such as waking, morning arrival, or post-rest regrouping, re-anchor the scene around unresolved threats, injuries, obligations, investigations, or planning pressure rather than lingering on already-resolved courtesy beats.

25. A turn counts as meaningful only if it changes the situation (position, access, location, availability), advances, escalates, or resolves an issue, introduces new actionable information, or forces a decision. Do not continue selecting turns that only repeat internal thought, observation, waiting, or minor physical adjustments without consequence.

25a. Dialogue is appropriate when it is actively increasing tension, revealing new information, shifting power, or forcing a decision. Do not interrupt dialogue prematurely if it is still materially changing the situation.

25b. When dialogue begins to repeat positions, stall without new leverage, or fails to produce new information or decisions across multiple turns, treat the exchange as exhausted and shift to a consequential action, escalation, interruption, or transition.

25c. Consequential action includes not only physical movement, but also decisions, refusals, exits, reveals, or any change that alters the situation, relationships, or available options.

26. When the scene is waiting on an external event (arriving authorities, phone callbacks, delivery, etc.) and no present character can materially advance the outcome through further action or dialogue, do not continue selecting micro-beats of waiting or maintaining position. Instead: introduce a material time-passage environment event that resolves or advances the external dependency, resolve the active issue if the outcome is already determined, or use end_round to cleanly exit the response cycle.

27. If the primary active issues have been resolved and no new meaningful pressure is present, prefer concluding the scene or ending the response cycle rather than extending minor follow-up beats.

28. Do not broaden a grounded or only-partially-supernatural scene into a larger magical society, ritual system, specialist network, or shared occult vocabulary unless the structured evidence already establishes that wider ontology.
29. If only one character or one active issue establishes an unusual ability, do not assume the rest of the cast shares expert language, countermeasures, or routine familiarity with it unless canon or direct scene evidence supports that inference.
30. Preserve established capability limits and pacing when selecting the next beat. Do not route the scene as if healing, power use, or recovery has already exceeded the rate, rest requirements, or severity limits established in the structured context.
31. After a rare, miraculous, or destabilizing event becomes directly visible, give the most affected witness or responsible character room to register that shift instead of flattening it immediately into ordinary logistics.

32. Optional tension shifts must be short labels like escalate, steady, soften, reveal, or unsettle.

GOOD environment_event examples:
- "A knock lands at the apartment door"
- "A phone buzzes on the counter"
- "Thunder cuts across the next line"
- "Gray morning light reaches the blinds"

BAD environment_event examples:
- "Rain sounds slightly louder against the window"
- "The heater hums again"
- "The light flickers for mood"

OUTPUT FORMAT:
{
  "next_actor": "CharacterName",
  "environment_event": "optional short environmental beat or empty string",
  "tension_shift": "optional short label or empty string",
  "reason": "brief explanation grounded in the provided structured state"
}
"""


def _env_truthy(name: str) -> bool:
    v = os.environ.get(name)
    if v is None:
        return False
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _validate_deepseek_model_id(model: str) -> None:
    mid = model.strip()
    if mid in DEPRECATED_DEEPSEEK_MODELS:
        raise ValueError(
            f"Unsupported deprecated DeepSeek model ID {mid!r} for Holy Grail RP. "
            "Replace with 'deepseek-v4-flash' or 'deepseek-v4-pro'. "
            "Use DeepSeek V4 thinking controls (e.g. DEEPSEEK_THINKING / DEEPSEEK_REASONING_EFFORT), "
            "not legacy model names."
        )
    if mid not in ALLOWED_DEEPSEEK_MODELS:
        raise ValueError(
            f"Unsupported DeepSeek model ID {mid!r}. "
            f"Allowed hosted models: {sorted(ALLOWED_DEEPSEEK_MODELS)}."
        )


def _resolve_deepseek_base_url() -> str:
    return (os.environ.get("DEEPSEEK_BASE_URL") or DEFAULT_DEEPSEEK_OPENAI_BASE_URL).strip()


def _thinking_controls_from_env() -> tuple[bool, Literal["high", "max"] | None]:
    """Return (thinking_enabled, reasoning_effort when enabled).

    reasoning_effort is applied via merged request fields alongside DeepSeek `thinking` (API docs).
    """
    enabled = _env_truthy("DEEPSEEK_THINKING")
    effort_raw = (os.environ.get("DEEPSEEK_REASONING_EFFORT") or "high").strip().lower()
    effort: Literal["high", "max"] | None
    if enabled:
        if effort_raw not in ("high", "max"):
            raise ValueError(
                "DEEPSEEK_REASONING_EFFORT must be 'high' or 'max' when DEEPSEEK_THINKING is enabled "
                f"(got {effort_raw!r})."
            )
        effort = effort_raw  # type: ignore[assignment]
    else:
        if os.environ.get("DEEPSEEK_REASONING_EFFORT") and effort_raw not in ("high", "max"):
            raise ValueError(
                "DEEPSEEK_REASONING_EFFORT must be 'high' or 'max' when set "
                f"(got {effort_raw!r})."
            )
        effort = None
    return enabled, effort if enabled else None


def _build_deepseek_extra_body(
    thinking_enabled: bool, reasoning_effort: Literal["high", "max"] | None
) -> dict[str, Any]:
    body: dict[str, Any] = {"thinking": {"type": "enabled" if thinking_enabled else "disabled"}}
    if thinking_enabled and reasoning_effort is not None:
        body["reasoning_effort"] = reasoning_effort
    return body


def create_narrator_agent(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create a Narrator agent for scene descriptions.

    The narrator sets scenes and describes atmosphere without speaking for characters.

    Args:
        model_client: The model client to use for the narrator

    Returns:
        Configured AssistantAgent for the narrator
    """
    return AssistantAgent(
        name="Narrator",
        description="Scene setter and atmosphere describer. Never speaks for characters.",
        system_message=NARRATOR_SYSTEM_MESSAGE,
        model_client=model_client,
        model_context=BufferedChatCompletionContext(
            buffer_size=MODEL_CONTEXT_BUFFER_SIZE
        ),
    )


def create_director_agent(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create a Director agent for orchestration and turn selection."""
    return AssistantAgent(
        name="Director",
        description="Scene orchestrator and turn selector. Works from structured state and returns JSON only.",
        system_message=DIRECTOR_SYSTEM_MESSAGE,
        model_client=model_client,
        model_context=BufferedChatCompletionContext(
            buffer_size=MODEL_CONTEXT_BUFFER_SIZE
        ),
    )


def create_deepseek_client(
    api_key: str | None = None,
    model: str | None = None,
) -> OpenAIChatCompletionClient:
    """Create a DeepSeek hosted OpenAI-compatible chat completion client (V4-native defaults).

    Environment variables:
        DEEPSEEK_API_KEY: Required unless api_key is passed.
        DEEPSEEK_MODEL: Optional override (default ``deepseek-v4-flash``); ``deepseek-v4-pro`` allowed.
        DEEPSEEK_BASE_URL: Optional override (default documented OpenAI-format host for DeepSeek).
        DEEPSEEK_THINKING: When truthy, enables DeepSeek thinking mode (default off).
        DEEPSEEK_REASONING_EFFORT: ``high`` or ``max`` when thinking enabled (default ``high``).

    Raises:
        ValueError: Missing API key, unsupported model ID (including deprecated ``deepseek-chat`` /
            ``deepseek-reasoner``), or invalid reasoning-effort configuration.

    Returns:
        Configured OpenAIChatCompletionClient for DeepSeek.
    """
    if api_key is None:
        api_key = os.environ.get("DEEPSEEK_API_KEY")

    if not api_key:
        raise ValueError(
            "DeepSeek API key required. Set DEEPSEEK_API_KEY environment variable "
            "or pass api_key parameter."
        )

    if model is not None:
        resolved_model = model.strip()
    else:
        resolved_model = (os.environ.get("DEEPSEEK_MODEL") or "").strip() or DEFAULT_DEEPSEEK_MODEL
    _validate_deepseek_model_id(resolved_model)

    base_url = _resolve_deepseek_base_url()

    thinking_on, reasoning_effort = _thinking_controls_from_env()
    extra_body = _build_deepseek_extra_body(thinking_on, reasoning_effort)

    return OpenAIChatCompletionClient(
        model=resolved_model,
        base_url=base_url,
        api_key=api_key,
        model_info={
            "function_calling": True,
            "json_output": True,
            "vision": False,
            "family": "unknown",
            "structured_output": True,
        },
        extra_body=extra_body,
    )


def get_model_info() -> dict[str, Any]:
    """Return default DeepSeek V4-native configuration snapshot for tooling/UI hints."""
    thinking_on, effort = _thinking_controls_from_env()
    resolved_model = (os.environ.get("DEEPSEEK_MODEL") or "").strip() or DEFAULT_DEEPSEEK_MODEL
    _validate_deepseek_model_id(resolved_model)
    return {
        "model": resolved_model,
        "base_url": _resolve_deepseek_base_url(),
        "thinking_enabled": thinking_on,
        "reasoning_effort": effort,
        "features": {
            "function_calling": True,
            "json_output": True,
            "vision": False,
            "structured_output": True,
        },
    }
