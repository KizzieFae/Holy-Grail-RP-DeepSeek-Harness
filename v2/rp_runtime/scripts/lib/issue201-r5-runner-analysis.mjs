/**
 * Issue #201 R5 — runner-level substrate extraction, diff, and establishment checks.
 */
import crypto from 'node:crypto';

import { classifyActualSubstrateUniqueness } from './issue201-lh1b-substrate-uniqueness.mjs';
import { obligationById, primaryR5Fork } from './issue201-r5-fixtures.mjs';
import { proveEstablishmentEquivalence } from './issue201-r5-establishment-equivalence.mjs';

const TRANSCRIPT_KINDS = new Set([
  'recent_scene_transcript',
  'immediate_user_turn_context',
  'triggering_user_context',
  'scene_progression',
  'user_turn_trigger',
]);

const RETRIEVAL_KINDS = new Set([
  'indexed_retrieval',
  'semantic_retrieval',
  'retrieval',
  'knowledge_retrieval',
]);

const MEMORY_KINDS = new Set([
  'character_memory',
  'character_private',
  'character_orientation',
  'character_summary',
  'scene_summary',
]);

const ROLE_PRIVATE_KINDS = new Set([
  'character_private',
  'role_private_knowledge',
  'private_character_knowledge',
]);

const PERSISTENCE_KEYS = ['lh0_obligation_id', 'finalized_projection'];

function normalize(text) {
  return String(text ?? '').toLowerCase().replace(/\s+/g, ' ').trim();
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

export function contributionsFromAssembledRequest(assembled) {
  return assembled?.contributions ?? [];
}

export function partitionManifestContributions(contributions = []) {
  const lean = [];
  const persistence = [];
  const retrieval = [];
  const memory = [];
  const rolePrivate = [];
  const transcript = [];
  for (const c of contributions) {
    if (isPersistenceContribution(c)) {
      persistence.push(c);
      continue;
    }
    lean.push(c);
    const kind = c?.source_kind ?? '';
    if (RETRIEVAL_KINDS.has(kind)) retrieval.push(c);
    if (MEMORY_KINDS.has(kind)) memory.push(c);
    if (ROLE_PRIVATE_KINDS.has(kind)) rolePrivate.push(c);
    if (TRANSCRIPT_KINDS.has(kind)) transcript.push(c);
  }
  return { lean, persistence, retrieval, memory, rolePrivate, transcript };
}

export function presentationTranscriptFromContributions(contributions = []) {
  return contributions
    .filter((c) => TRANSCRIPT_KINDS.has(c?.source_kind))
    .map((c) => c.content)
    .join('\n');
}

export function classifyRunnerSubstrate({
  fixture,
  assembledRequest,
  playerStimulus,
  continuitySnapshot = null,
}) {
  const fork = primaryR5Fork(fixture);
  const contributions = contributionsFromAssembledRequest(assembledRequest);
  const parts = partitionManifestContributions(contributions);
  const classification = classifyActualSubstrateUniqueness({
    fixture,
    fork,
    manifestContributions: contributions,
    playerStimulus,
    presentationTranscript: presentationTranscriptFromContributions(contributions),
    continuitySnapshot,
    retrievalContributions: parts.retrieval,
  });
  const stripped = contributions.filter((c) => !isPersistenceContribution(c));
  const strippedClass = classifyActualSubstrateUniqueness({
    fixture,
    fork,
    manifestContributions: stripped,
    playerStimulus,
    presentationTranscript: presentationTranscriptFromContributions(stripped),
    continuitySnapshot,
    retrievalContributions: parts.retrieval,
  });
  return {
    fork_id: fork.fork_id,
    contributions,
    partitioned: parts,
    classification,
    stripped_classification: strippedClass,
    persistence_contributions: parts.persistence,
  };
}

function semanticRulePresent(haystack, fixture) {
  const semantic = obligationById(fixture, fixture.obligations[0].obligation_id)?.semantic_content ?? '';
  const slice = normalize(semantic).slice(0, 48);
  const text = normalize(haystack);
  return slice.length >= 12 && text.includes(slice);
}

export function proveRunnerEstablishmentEquivalence({ t6RowA, t6RowB, fixture }) {
  const est = fixture.establishment;
  const staticEquiv = proveEstablishmentEquivalence(fixture);
  const stimulusMatch = normalize(t6RowA.exact_player_stimulus) === normalize(t6RowB.exact_player_stimulus);
  const moveMatch = normalize(t6RowA.move_text) === normalize(t6RowB.move_text);
  const presentationMatch = normalize(t6RowA.presentation_text) === normalize(t6RowB.presentation_text);
  const establishmentHaystack = normalize([
    t6RowA.presentation_text,
    t6RowA.move_text,
    t6RowB.presentation_text,
    t6RowB.move_text,
  ].join('\n'));
  const requiredInPresentation = (fixture.qualification.establishment_entailment_required_phrases ?? [])
    .every((p) => establishmentHaystack.includes(normalize(p)));
  const plotA = t6RowA.lh0_post_commit?.plot_post_commit ?? null;
  const plotB = t6RowB.lh0_post_commit?.plot_post_commit ?? null;
  const plotRanB = t6RowB.lh0_post_commit?.skipped !== true && plotB != null;
  const plotSkippedA = t6RowA.lh0_post_commit?.skipped === true || !t6RowA.lh0_post_commit;

  return {
    rg1_pass: stimulusMatch && moveMatch && presentationMatch && requiredInPresentation,
    rg2_pass: staticEquiv.g2_entailment_no_extra_facts && plotRanB && plotSkippedA,
    detail: {
      stimulus_match: stimulusMatch,
      move_match: moveMatch,
      presentation_match: presentationMatch,
      required_phrases_in_both_presentations: requiredInPresentation,
      static_g1: staticEquiv.g1_shared_establishment,
      static_g2: staticEquiv.g2_entailment_no_extra_facts,
      plot_post_commit_arm_a_skipped: plotSkippedA,
      plot_post_commit_arm_b_active: plotRanB,
      t6_player_stimulus: t6RowA.exact_player_stimulus,
      t6_move_a: t6RowA.move_text,
      t6_move_b: t6RowB.move_text,
      t6_presentation_a: t6RowA.presentation_text,
      t6_presentation_b: t6RowB.presentation_text,
      plot_scribe_source_fixture: est.plot_scribe_source_excerpt,
    },
  };
}

const INCIDENTAL_PATTERNS = [
  /^inference_id$/i,
  /^manifest_id$/i,
  /^session_id$/i,
  /^hg_round_id$/i,
  /^correlation/i,
];

function contributionSignature(c) {
  if (!c) return null;
  return {
    source_kind: c.source_kind ?? null,
    authority_class: c.authority_class ?? null,
    content_norm: normalize(c.content).slice(0, 500),
    persistence: isPersistenceContribution(c),
    obligation_id: c?.provenance?.lh0_obligation_id ?? null,
  };
}

export function normalizedSubstrateDiff(manifestA, manifestB) {
  const contribsA = contributionsFromAssembledRequest(manifestA);
  const contribsB = contributionsFromAssembledRequest(manifestB);
  const sigA = contribsA.map(contributionSignature);
  const sigB = contribsB.map(contributionSignature);

  const persistenceOnlyB = contribsB.filter(isPersistenceContribution)
    .filter((pb) => !contribsA.some(isPersistenceContribution));
  const leanA = contribsA.filter((c) => !isPersistenceContribution(c));
  const leanB = contribsB.filter((c) => !isPersistenceContribution(c));

  const leanSigA = leanA.map(contributionSignature);
  const leanSigB = leanB.map(contributionSignature);
  const leanHashA = crypto.createHash('sha256').update(JSON.stringify(leanSigA)).digest('hex');
  const leanHashB = crypto.createHash('sha256').update(JSON.stringify(leanSigB)).digest('hex');

  const potentiallyCausal = [];
  if (leanHashA !== leanHashB) {
    const kindsA = new Map(leanA.map((c) => [c.source_kind, normalize(c.content)]));
    const kindsB = new Map(leanB.map((c) => [c.source_kind, normalize(c.content)]));
    for (const [kind, textA] of kindsA) {
      const textB = kindsB.get(kind);
      if (textB == null || textB !== textA) {
        potentiallyCausal.push({ source_kind: kind, arm_a_excerpt: textA.slice(0, 200), arm_b_excerpt: String(textB ?? '').slice(0, 200) });
      }
    }
    for (const kind of kindsB.keys()) {
      if (!kindsA.has(kind)) {
        potentiallyCausal.push({ source_kind: kind, arm_a_excerpt: null, arm_b_excerpt: kindsB.get(kind).slice(0, 200) });
      }
    }
  }

  return {
    expected_persistence_difference: persistenceOnlyB.map(contributionSignature),
    lean_substrate_hash_a: leanHashA,
    lean_substrate_hash_b: leanHashB,
    lean_substrate_equivalent: leanHashA === leanHashB,
    potentially_causal_non_persistence_differences: potentiallyCausal.filter(
      (d) => !INCIDENTAL_PATTERNS.some((re) => re.test(d.source_kind ?? '')),
    ),
    signatures_a: sigA,
    signatures_b: sigB,
  };
}

export function reviewInterveningTurnsForRuleRefresh(turns, fixture) {
  const establishmentTurn = fixture.establishment.turn_index;
  const decisionTurn = fixture.qualification.decision_turn_index;
  const reviews = [];
  for (const row of turns) {
    const idx = row.turn_index;
    if (idx <= establishmentTurn || idx >= decisionTurn) continue;
    const stim = row.exact_player_stimulus ?? '';
    const refresh = semanticRulePresent(stim, fixture)
      || semanticRulePresent(row.presentation_text ?? '', fixture)
      || semanticRulePresent(row.move_text ?? '', fixture);
    reviews.push({
      turn_index: idx,
      objective_refresh_risk: refresh,
      player_stimulus: stim,
    });
  }
  return {
    pass: reviews.every((r) => !r.objective_refresh_risk),
    reviews,
  };
}

export function stimulusLeakageOnActualStimulus(stimulus, fixture) {
  const fork = primaryR5Fork(fixture);
  const sub = classifyActualSubstrateUniqueness({
    fixture,
    fork,
    manifestContributions: [],
    playerStimulus: stimulus,
  });
  const forbidden = ['pantry alcove', 'staff pantry', 'trial staff meals', 'not at the household dining table'];
  const lower = normalize(stimulus);
  const forbiddenHits = forbidden.filter((f) => lower.includes(f));
  return {
    pass: !sub.flags.stimulus_sufficient && forbiddenHits.length === 0,
    stimulus_sufficient: sub.flags.stimulus_sufficient,
    forbidden_phrase_hits: forbiddenHits,
    stimulus,
  };
}
