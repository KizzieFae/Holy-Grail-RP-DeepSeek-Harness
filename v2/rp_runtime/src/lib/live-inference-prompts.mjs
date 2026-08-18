/** Default user prompts for live provider inference (not mock-specific). */

export const LIVE_DIRECTOR_PROMPT = [
  'Respond with ONLY one JSON object. No markdown, no commentary.',
  'Required keys: next_actor (string), end_round (boolean), reason (string),',
  'environment_event (string), tension_shift (string).',
  'Select next_actor from the eligible cast in context. Set end_round false unless the scene should stop.',
].join(' ');

export const LIVE_CHARACTER_PROMPT = [
  'Respond with ONLY one JSON object. No markdown, no commentary.',
  'Required shape exactly:',
  '{"move_schema_version":2,',
  '"beats":[{"type":"action","action":"<short action text>"}],',
  '"motivation":{"goal":"...","tactic":"...","emotional_driver":"...","risk_level":"low"},',
  '"semantic_evaluation":{"decision":"no_covered_change"}}.',
  'Action beats use the key "action" (not description or intent).',
  'risk_level must be lowercase: low, medium, or high.',
].join(' ');

export const LIVE_NARRATOR_PROMPT = 'Render the committed character move as scene narration only. Plain prose, no JSON.';
