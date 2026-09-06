/** Default user prompts for live provider inference (not mock-specific). */

/** DSH transport envelope only — role schema/domain contracts live in Host inference_instruction. */
export const LIVE_INFERENCE_TRANSPORT_PROMPT =
  'Return only the requested JSON object. No markdown or commentary.';

export const LIVE_DIRECTOR_PROMPT = LIVE_INFERENCE_TRANSPORT_PROMPT;
export const LIVE_CHARACTER_PROMPT = LIVE_INFERENCE_TRANSPORT_PROMPT;

export const LIVE_NARRATOR_PROMPT = 'Render the committed character move as scene narration only. Plain prose, no JSON.';
