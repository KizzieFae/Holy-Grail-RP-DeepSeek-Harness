/**
 * Issue #136 — turn-zero opening perception bootstrap for validation fixtures.
 *
 * Encodes transient visible stimuli through canonical opening + PVR, not scene_premise.
 */
import {
  loadIssue136TruthFixture,
} from './issue136-fixture-truth.mjs';

/** Opening presentation prose used for narrator mocks and turn-zero PVR attachment. */
export const ISSUE136_OPENING_PROSE_BY_FIXTURE = {
  '136-T2-A-STABILITY': [
    'Jon approached Mara at the workbench with routine workshop business; nothing new had changed between them.',
  ],
  '136-T2-B-POS-CHANGE': [
    'Before the gathered shop steward, Jon publicly acknowledged the breach, named the harm to Mara, and offered concrete restitution.',
    'The steward witnessed the restitution offer; Mara must now respond.',
  ],
  '136-T2-C-NEG-CHANGE': [
    'The shop steward confronted Jon with falsified safety records implicating Mara and confirmed the betrayal authoritatively.',
    'The betrayal was now authoritatively confirmed; Mara must respond.',
  ],
  '136-T2-D-INACTION': [
    'A distant scraping sound came from behind a sealed inspection panel, but no immediate danger was visible.',
  ],
  '136-T2-E-ENTITLEMENT': [
    'Alice waited in the vault antechamber, uncertain what Bob knew.',
    'Bob stepped to the keypad and entered a code without speaking the digits aloud; the vault door clicked unlocked.',
    'The door stood open, but Alice had heard no code spoken aloud.',
  ],
  '136-T2-F-ACTION-REQUIRED': [
    'A support bracket cracked visibly above a colleague\'s station; immediate harm looked likely without intervention.',
  ],
};

/** Fixtures whose semantic claims require turn-zero Character-perceivable opening PVR. */
export const ISSUE136_TURN_ZERO_PVR_FIXTURES = new Set([
  '136-T2-F-ACTION-REQUIRED',
  '136-T2-D-INACTION',
]);

export function fixtureRequiresTurnZeroPerception(fixtureId) {
  return ISSUE136_TURN_ZERO_PVR_FIXTURES.has(fixtureId);
}

export function turnZeroOpeningProse(truth) {
  const explicit = String(truth.turn_zero_observable_stimulus ?? '').trim();
  if (explicit) return explicit;
  const lines = ISSUE136_OPENING_PROSE_BY_FIXTURE[truth.fixture_id] ?? [];
  const fromNarrator = String(lines[0] ?? '').trim();
  if (fromNarrator) return fromNarrator;
  return String(truth.scene_stimulus ?? '').trim();
}

export function buildTurnZeroPerceptualVisibility({
  prose,
  unitIdPrefix = 'issue136_turn_zero',
  extraUnits = [],
} = {}) {
  const text = String(prose ?? '').trim();
  if (!text) {
    throw new Error('issue136_turn_zero_pvr_missing_prose');
  }
  const units = [
    {
      unit_id: `${unitIdPrefix}_observable_scene`,
      kind: 'observable_scene',
      text,
      recipients: { scope: 'public' },
    },
    ...extraUnits,
  ];
  return { units };
}

export async function attachIssue136TurnZeroPerception(api, hgSessionId, truth) {
  if (!fixtureRequiresTurnZeroPerception(truth.fixture_id)) {
    return null;
  }
  const prose = turnZeroOpeningProse(truth);
  const perceptual_visibility = buildTurnZeroPerceptualVisibility({
    prose,
    unitIdPrefix: truth.fixture_id.replace(/[^a-zA-Z0-9]+/g, '_').toLowerCase(),
  });
  const validated = await api.validatePerceptualVisibility({
    hg_session_id: hgSessionId,
    perceptual_visibility,
  });
  if (!validated.accepted || !validated.record) {
    throw new Error(
      validated.reason
      ?? `issue136_turn_zero_pvr_validation_failed:${truth.fixture_id}`,
    );
  }
  return api.attachOpeningPerceptualVisibility({
    hg_session_id: hgSessionId,
    perceptual_visibility: validated.record,
  });
}

export function analyzeCharacterManifest(manifest) {
  const contributions = manifest?.contributions ?? [];
  const byKind = new Map();
  for (const item of contributions) {
    byKind.set(item.source_kind, item);
  }
  return {
    contributions,
    recentSceneTranscript: byKind.get('recent_scene_transcript') ?? null,
    sceneContext: byKind.get('scene_context') ?? null,
    sceneSetup: byKind.get('scene_setup') ?? null,
    directorContext: byKind.get('director_context') ?? null,
  };
}

export async function prepareIssue136CharacterManifestGate({
  api,
  hgSessionId,
  truth,
  directorDecision = null,
}) {
  const round = await api.startRound({ hg_scene_id: hgSessionId });
  const sceneState = await api.getSceneState(hgSessionId);
  const turnIndex = Number(sceneState.turn_counter ?? 0);
  const manifest = await api.prepareCharacterContext({
    hg_scene_id: hgSessionId,
    hg_round_id: round.hg_round_id,
    inference_id: `issue136-manifest-gate-${truth.fixture_id}`,
    character_id: truth.character_id,
    role: 'guest',
    turn_index: turnIndex,
    attempt_index: 0,
    director_decision: directorDecision,
  });
  const directorManifest = await api.prepareDirectorContext({
    hg_scene_id: hgSessionId,
    hg_round_id: round.hg_round_id,
    inference_id: `issue136-director-gate-${truth.fixture_id}`,
    turn_index: turnIndex,
    attempt_index: 0,
  });
  const history = await api.getSessionHistory(hgSessionId);
  const opening = (history.entries ?? []).find((entry) => entry.kind === 'opening');
  return {
    round,
    sceneState,
    manifest,
    directorManifest,
    opening,
    analysis: analyzeCharacterManifest(manifest),
    directorKinds: new Set((directorManifest.contributions ?? []).map((c) => c.source_kind)),
  };
}

export function loadIssue136TruthForPerception(fixtureId) {
  const truth = loadIssue136TruthFixture(fixtureId);
  if (fixtureRequiresTurnZeroPerception(fixtureId) && truth.turn_zero_perception !== true) {
    throw new Error(`issue136_truth_missing_turn_zero_perception:${fixtureId}`);
  }
  return truth;
}
