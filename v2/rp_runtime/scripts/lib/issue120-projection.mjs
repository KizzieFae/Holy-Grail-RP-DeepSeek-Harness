import { projectPlayerEntryForViewer } from './project-player-entry-for-viewer.mjs';

export const JAPAN_TOKEN = 'they were not in Japan, but hold habits died hard.';

/**
 * Legacy harness bug (G-122-01): recordUserTurn metadata does not include projection.
 */
export function readProjectionFromRecordUserTurnMetadata(entry) {
  const metadata = entry?.metadata ?? {};
  return metadata.perceptual_visibility_projection ?? {};
}

export function analyzeSemantics(units) {
  const japanUnit = (units ?? []).find((unit) => String(unit.text ?? '').includes('not in Japan'));
  return {
    unit_count: Array.isArray(units) ? units.length : 0,
    units: (units ?? []).map((unit) => ({
      unit_id: unit.unit_id,
      kind: unit.kind,
      scope: unit.recipients?.scope ?? null,
      text_preview: String(unit.text ?? '').slice(0, 120),
    })),
    japan_unit: japanUnit
      ? {
        unit_id: japanUnit.unit_id,
        kind: japanUnit.kind,
        scope: japanUnit.recipients?.scope ?? null,
        text: japanUnit.text,
      }
      : null,
    japan_is_internal: japanUnit?.kind === 'internal',
    has_observable_seiza: (units ?? []).some(
      (unit) => unit.kind === 'observable_event' && /seiza|sieza|cushion/i.test(unit.text ?? ''),
    ),
    speech_units: (units ?? []).filter((unit) => unit.kind === 'speech').length,
    hesitation_unit: (units ?? []).find(
      (unit) => unit.kind === 'observable_event' && /hesittat|looking up/i.test(unit.text ?? ''),
    ) ?? null,
    seiza_unit: (units ?? []).find(
      (unit) => unit.kind === 'observable_event' && /seiza|sieza|cushion/i.test(unit.text ?? ''),
    ) ?? null,
    speech_unit_ids: (units ?? []).filter((unit) => unit.kind === 'speech').map((unit) => unit.unit_id),
  };
}

export function evaluateAyameProjection({
  semantics,
  assembly,
  japanToken = JAPAN_TOKEN,
}) {
  const included = new Set(assembly?.included_unit_ids ?? []);
  const excluded = new Set(assembly?.excluded_unit_ids ?? []);
  const japanUnitId = semantics.japan_unit?.unit_id ?? null;
  const japanExcluded = japanUnitId ? excluded.has(japanUnitId) : null;
  const japanExclusionReason = japanUnitId
    ? assembly?.exclusion_reasons?.[japanUnitId] ?? null
    : null;
  const ayameContent = String(assembly?.content ?? '');
  const japanTokenInContent = ayameContent.includes(japanToken);
  const seizaIncluded = semantics.seiza_unit
    ? included.has(semantics.seiza_unit.unit_id)
    : null;
  const hesitationIncluded = semantics.hesitation_unit
    ? included.has(semantics.hesitation_unit.unit_id)
    : null;
  const speechIncluded = (semantics.speech_unit_ids ?? []).every((unitId) => included.has(unitId));

  const projectionPass = Boolean(
    japanExcluded === true
    && japanExclusionReason === 'player_internal_ineligible'
    && !japanTokenInContent
    && seizaIncluded === true
    && hesitationIncluded === true
    && speechIncluded === true,
  );

  return {
    japan_excluded_from_ayame: japanExcluded,
    japan_exclusion_reason: japanExclusionReason,
    japan_token_in_ayame_content: japanTokenInContent,
    seiza_included_for_ayame: seizaIncluded,
    hesitation_included_for_ayame: hesitationIncluded,
    speech_included_for_ayame: speechIncluded,
    included_unit_ids: [...included],
    excluded_unit_ids: [...excluded],
    exclusion_reasons: assembly?.exclusion_reasons ?? {},
    projection_pass: projectionPass,
  };
}

export async function projectPlayerUserTurnForAyame({
  api,
  sessionId,
  content,
  decomposition,
  speaker = 'Kizzie',
  viewerCharacter = 'Ayame',
  presentCharacters,
}) {
  const entry = await api.recordUserTurn({
    hg_session_id: sessionId,
    content,
    speaker,
    player_decomposition: decomposition,
  });
  const metadata = entry.metadata ?? {};
  const pvr = metadata.perceptual_visibility ?? {};
  const audit = metadata.perceptual_visibility_validation ?? metadata.validation_audit ?? {};
  const assembly = projectPlayerEntryForViewer({
    entry,
    viewerCharacter,
    presentCharacters,
  });
  return {
    entry,
    validation_accepted: Boolean(audit.accepted),
    validation_status: pvr.validation_status ?? null,
    failure_class: pvr.recovery?.failure_class ?? null,
    units: pvr.units ?? [],
    assembly,
    legacy_projection: readProjectionFromRecordUserTurnMetadata(entry),
  };
}

export function buildSemanticPass({ semantics, projection }) {
  return Boolean(
    semantics.japan_is_internal
    && semantics.has_observable_seiza
    && semantics.speech_units >= 2
    && projection.projection_pass === true,
  );
}
