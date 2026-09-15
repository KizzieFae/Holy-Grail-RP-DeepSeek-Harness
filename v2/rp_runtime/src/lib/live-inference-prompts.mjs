/** Default user prompts for live provider inference (not mock-specific). */

/** DSH transport envelope only — role schema/domain contracts live in Host inference_instruction. */
export const LIVE_INFERENCE_TRANSPORT_PROMPT =
  'Return only the requested JSON object. No markdown or commentary.';

export const LIVE_STORYTELLER_ORIENTATION_PROMPT = LIVE_INFERENCE_TRANSPORT_PROMPT;

export const LIVE_STORYTELLER_ASSESSMENT_PROMPT = LIVE_INFERENCE_TRANSPORT_PROMPT;

export const LIVE_DIRECTOR_PROMPT = LIVE_INFERENCE_TRANSPORT_PROMPT;
export const LIVE_CHARACTER_PROMPT = LIVE_INFERENCE_TRANSPORT_PROMPT;

export const LIVE_NARRATOR_PROMPT = 'Render the committed character move as scene narration only. Plain prose, no JSON.';

/** Issue #201 G3-C F2 — harness-only Narrator envelope with spatial claims surface. */
export const LIVE_A2_F2_NARRATOR_SPATIAL_PROMPT =
  'Return JSON only: {"presentation_text":"<player-visible prose>","spatial_claims":{"schema":"hg_presentation_spatial_claims_v1","claims":[{"entity_id":"<character>","relation":"located_at","zone_id":"<zone>"}]}}. '
  + 'Include spatial claims only for relationships you assert in the presentation. Use authoritative zone ids when known (harley_ivy_table, across_room, staff_margin, mess_hall_general). Empty claims array is valid if no spatial relationship is asserted. No markdown.';
