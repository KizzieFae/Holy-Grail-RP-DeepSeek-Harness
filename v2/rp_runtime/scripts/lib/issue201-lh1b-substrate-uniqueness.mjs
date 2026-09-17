/**
 * Issue #201 LH-1B — actual lean-substrate uniqueness at decision inference.
 */
import { LH1B_SCHEMAS } from './issue201-lh1b-contract.mjs';
import { obligationById } from './issue201-lh1b-fixtures.mjs';

const PERSISTENCE_PROVENANCE_KEYS = [
  'lh0_obligation_id',
  'lh0_fixture_class',
  'lh0_harness',
  'finalized_projection',
];

function normalizeText(parts) {
  return parts.map((p) => String(p ?? '').toLowerCase()).join('\n');
}

function contributionText(c) {
  return String(c?.content ?? '');
}

function isPersistenceContribution(c) {
  if (!c) return false;
  if (c?.provenance?.lh0_obligation_id) return true;
  if (c?.provenance?.finalized_projection) return true;
  for (const kid of c?.knowledge_ids ?? []) {
    if (String(kid).startsWith('lh0-obligation:')) return true;
  }
  return false;
}

function nonPersistenceContributions(contributions = []) {
  return (contributions ?? []).filter((c) => !isPersistenceContribution(c));
}

function markerHits(haystack, markers = []) {
  return markers.filter((m) => haystack.includes(String(m).toLowerCase()));
}

function semanticFragmentPresent(haystack, semantic) {
  const text = String(semantic ?? '').toLowerCase().trim();
  if (!text) return false;
  const slice = text.slice(0, Math.min(48, text.length));
  return slice.length >= 12 && haystack.includes(slice);
}

function classifyContributionSources(contributions = []) {
  const kinds = new Set((contributions ?? []).map((c) => c.source_kind).filter(Boolean));
  return [...kinds];
}

/**
 * Classify whether lean substrate at decision turn already supplies fork-relevant information.
 * @param {object} params
 * @param {object} params.fixture
 * @param {object} params.fork
 * @param {object[]} params.manifestContributions — full consumer manifest at decision turn
 * @param {string} [params.playerStimulus]
 * @param {string} [params.presentationTranscript] — diagnostic recent transcript text
 */
export function classifyActualSubstrateUniqueness({
  fixture,
  fork,
  manifestContributions = [],
  playerStimulus = '',
  presentationTranscript = '',
  continuitySnapshot = null,
  retrievalContributions = [],
} = {}) {
  const obligationId = fork?.obligation_ids?.[0] ?? null;
  const row = obligationId ? obligationById(fixture, obligationId) : null;
  const semantic = row?.semantic_content ?? fork?.semantic_information_expected ?? '';
  const markers = (fork?.with_obligation_choice_classes ?? [])
    .flatMap((c) => c.behavior_markers ?? []);

  const leanContribs = nonPersistenceContributions(manifestContributions);
  const transcriptLikeKinds = new Set([
    'recent_scene_transcript',
    'immediate_user_turn_context',
    'triggering_user_context',
    'scene_progression',
    'user_turn_trigger',
  ]);
  const transcriptLikeContribs = leanContribs.filter((c) => transcriptLikeKinds.has(c.source_kind));
  const leanHaystack = normalizeText([
    playerStimulus,
    ...leanContribs.map(contributionText),
    ...(retrievalContributions ?? []).map(contributionText),
  ]);
  const transcriptHaystack = normalizeText([
    presentationTranscript,
    ...transcriptLikeContribs.map(contributionText),
  ]);

  const stimulusHits = markerHits(normalizeText([playerStimulus]), markers);
  const transcriptHits = markerHits(transcriptHaystack, markers);
  const leanManifestHits = markerHits(leanHaystack, markers);
  const semanticInLean = semanticFragmentPresent(leanHaystack, semantic);
  const continuityText = normalizeText([
    continuitySnapshot?.character_state ?? '',
    continuitySnapshot?.scene_props ?? '',
    continuitySnapshot?.authored_premise ?? '',
  ]);
  const continuityHits = markerHits(continuityText, markers);
  const retrievalHits = markerHits(
    normalizeText((retrievalContributions ?? []).map(contributionText)),
    markers,
  );

  const memoryKinds = ['character_memory', 'character_private', 'character_orientation'];
  const memoryContribs = leanContribs.filter((c) => memoryKinds.includes(c.source_kind));
  const memoryHits = markerHits(normalizeText(memoryContribs.map(contributionText)), markers);

  const flags = {
    stimulus_sufficient: stimulusHits.length > 0 || semanticFragmentPresent(normalizeText([playerStimulus]), semantic),
    transcript_sufficient: transcriptHits.length > 0,
    continuity_sufficient: continuityHits.length > 0 || semanticFragmentPresent(continuityText, semantic),
    retrieval_sufficient: retrievalHits.length > 0,
    memory_or_summary_sufficient: memoryHits.length > 0,
    other_substrate_sufficient: leanManifestHits.length > 0 && !semanticInLean,
  };

  const anySufficiency = Object.values(flags).some(Boolean);
  let primary = 'persistence_unique';
  if (!anySufficiency && !semanticInLean) {
    primary = 'persistence_unique';
  } else if (flags.stimulus_sufficient) {
    primary = 'stimulus_sufficient';
  } else if (flags.retrieval_sufficient) {
    primary = 'retrieval_sufficient';
  } else if (flags.continuity_sufficient) {
    primary = 'continuity_sufficient';
  } else if (flags.memory_or_summary_sufficient) {
    primary = 'memory_or_summary_sufficient';
  } else if (flags.transcript_sufficient) {
    primary = 'transcript_sufficient';
  } else if (flags.other_substrate_sufficient) {
    primary = 'other_substrate_sufficient';
  } else if (leanManifestHits.length > 0 || semanticInLean) {
    primary = 'ambiguous';
  }

  return {
    schema: LH1B_SCHEMAS.SUBSTRATE_UNIQUENESS,
    fork_id: fork?.fork_id ?? null,
    obligation_id: obligationId,
    primary_classification: primary,
    flags,
    marker_hits: {
      stimulus: stimulusHits,
      transcript_diagnostic: transcriptHits,
      lean_manifest: leanManifestHits,
      continuity: continuityHits,
      retrieval: retrievalHits,
      memory: memoryHits,
    },
    semantic_fragment_in_lean_substrate: semanticInLean,
    lean_source_kinds: classifyContributionSources(leanContribs),
    persistence_unique: primary === 'persistence_unique',
  };
}

export function buildForkSubstrateReports({
  fixture,
  forks = [],
  manifestContributions = [],
  playerStimulus = '',
  presentationTranscript = '',
  continuitySnapshot = null,
  retrievalContributions = [],
}) {
  return forks.map((fork) => classifyActualSubstrateUniqueness({
    fixture,
    fork,
    manifestContributions,
    playerStimulus,
    presentationTranscript,
    continuitySnapshot,
    retrievalContributions,
  }));
}
