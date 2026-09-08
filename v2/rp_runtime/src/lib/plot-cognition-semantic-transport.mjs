export const PLANNING_HORIZONS = Object.freeze(['LONG', 'MEDIUM', 'SHORT']);

export function plotCognitionApplicabilitySemanticsPromptLines() {
  return [
    'Applicability semantics (#58 / #162 — involved_character_ids is projection scope, not everyone mentioned in text):',
    '- character: cognition owned by ONE Character. primary_character_id = owner; involved_character_ids = [owner] only.',
    '  A character-specific goal ABOUT another Character still lists only its owner in involved_character_ids;',
    '  mention the other Character in intended_direction or pressure_text instead.',
    '- relational: genuinely multi-character cognition. involved_character_ids must include two or more Characters;',
    '  primary_character_id must be one of them. Merely interacting with another Character does not make cognition relational.',
    '- global: scene-wide cognition. primary_character_id = null; involved_character_ids = [].',
  ];
}

export function plotCognitionSemanticTransportPromptLines() {
  return [
    'Cognition item semantic transport (#68 Part C — model supplies semantic content only):',
    '- Do NOT emit item schema, creation_provenance, or activity_state; runtime stamps those deterministically.',
    'Each goal object must include: goal_id, intended_direction, planning_horizon (LONG|MEDIUM|SHORT), applicability.',
    'Each pressure object must include: pressure_id, pressure_text, dramatic_rationale, applicability.',
    'applicability object: applicability_kind (character|relational|global), primary_character_id, involved_character_ids.',
    'dramatic_rationale is per-pressure semantic rationale; do not substitute package-level replan_rationale.',
    ...plotCognitionApplicabilitySemanticsPromptLines(),
  ];
}

function applicabilityStructurallyPresent(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return false;
  return Boolean(String(raw.applicability_kind ?? '').trim());
}

export function validateSemanticGoalTransport(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return 'replan_cognition_item_incomplete';
  }
  const goalId = String(raw.goal_id ?? '').trim();
  const direction = String(raw.intended_direction ?? '').trim();
  if (!goalId || !direction) return 'replan_cognition_item_incomplete';
  const horizon = String(raw.planning_horizon ?? '').trim();
  if (!horizon) return 'goal_missing_planning_horizon';
  if (!PLANNING_HORIZONS.includes(horizon)) return 'goal_planning_horizon_invalid';
  if (!applicabilityStructurallyPresent(raw.applicability)) return 'goal_missing_applicability';
  return null;
}

export function validateSemanticPressureTransport(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return 'replan_cognition_item_incomplete';
  }
  const pressureId = String(raw.pressure_id ?? '').trim();
  const pressureText = String(raw.pressure_text ?? '').trim();
  if (!pressureId) return 'replan_cognition_item_incomplete';
  if (!pressureText) {
    if (String(raw.description ?? '').trim()) {
      return 'replan_pressure_missing_pressure_text';
    }
    return 'replan_cognition_item_incomplete';
  }
  const dramaticRationale = String(raw.dramatic_rationale ?? '').trim();
  if (!dramaticRationale) return 'pressure_missing_dramatic_rationale';
  if (!applicabilityStructurallyPresent(raw.applicability)) return 'pressure_missing_applicability';
  return null;
}

export function validateSemanticCognitionItems(goals, pressures) {
  if (!Array.isArray(goals) || !Array.isArray(pressures)) {
    return 'replan_cognition_item_incomplete';
  }
  for (const goal of goals) {
    const error = validateSemanticGoalTransport(goal);
    if (error) return error;
  }
  for (const pressure of pressures) {
    const error = validateSemanticPressureTransport(pressure);
    if (error) return error;
  }
  return null;
}

export function plotCognitionSemanticTransportCorrectionGuidance(structuralError) {
  const error = String(structuralError ?? '').trim();
  if (!error) return [];
  const lines = [];
  if (error === 'goal_missing_planning_horizon') {
    lines.push('- Each goal must include planning_horizon (LONG, MEDIUM, or SHORT).');
  } else if (error === 'goal_planning_horizon_invalid') {
    lines.push('- Each goal planning_horizon must be LONG, MEDIUM, or SHORT.');
  } else if (error === 'goal_missing_applicability') {
    lines.push('- Each goal must include applicability with applicability_kind.');
  } else if (error === 'pressure_missing_dramatic_rationale') {
    lines.push('- Each pressure must include dramatic_rationale (per-pressure semantic rationale).');
    lines.push('- Do not substitute replan_rationale or assimilation_rationale for dramatic_rationale.');
  } else if (error === 'pressure_missing_applicability') {
    lines.push('- Each pressure must include applicability with applicability_kind.');
  }
  if (lines.length > 0) {
    lines.push(...plotCognitionApplicabilitySemanticsPromptLines());
    lines.push('- Do NOT add schema, creation_provenance, or activity_state; runtime supplies those.');
  }
  return lines;
}

export function semanticTransportGoalFixture(overrides = {}) {
  return {
    goal_id: 'hg-plot-goal-fixture',
    intended_direction: 'Pursue the revised direction.',
    planning_horizon: 'MEDIUM',
    applicability: {
      applicability_kind: 'character',
      primary_character_id: 'Alice',
      involved_character_ids: ['Alice'],
    },
    ...overrides,
  };
}

export function semanticTransportPressureFixture(overrides = {}) {
  return {
    pressure_id: 'hg-plot-pressure-fixture',
    pressure_text: 'Unresolved dramatic tension remains.',
    dramatic_rationale: 'Maintains narrative pressure without prescribing action.',
    applicability: {
      applicability_kind: 'character',
      primary_character_id: 'Alice',
      involved_character_ids: ['Alice'],
    },
    ...overrides,
  };
}
