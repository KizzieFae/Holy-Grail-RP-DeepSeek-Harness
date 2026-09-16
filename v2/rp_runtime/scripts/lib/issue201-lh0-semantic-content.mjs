/**
 * Issue #201 LH-0 — semantic obligation payloads, causal design, and evidence helpers.
 */
import { loadLh0FixtureManifest } from './issue201-lh0-fixtures.mjs';
import { LIFECYCLE_STATES } from './issue201-lifecycle-states.mjs';
import { evaluateActivationPredicate } from './issue201-lh0-persistent-store.mjs';

export const LH0_SEMANTIC_PROJECTION_PRIORITY = 18;
const BOOKKEEPING_PATTERN = /^LH0-OBL-[A-Z0-9_-]+:\s*(plot_scribe_tracked|persistent_|consolidated_|fixture_seed)/i;

export function fixtureObligationById(fixture, obligationId) {
  return fixture.obligations.find((o) => o.obligation_id === obligationId) ?? null;
}

export function resolveLh0ModelFacingContent(obligation, fixture = null) {
  const fx = fixture ?? loadLh0FixtureManifest();
  const row = obligation?.obligation_id
    ? fixtureObligationById(fx, obligation.obligation_id)
    : null;
  const content = String(
    obligation?.semantic_content
    ?? row?.semantic_content
    ?? obligation?.obligation_text
    ?? '',
  ).trim();
  if (!content || isBookkeepingOnlySemanticContent(content)) {
    throw new Error(`missing semantic model-facing content for ${obligation?.obligation_id ?? 'unknown'}`);
  }
  return content;
}

export function isBookkeepingOnlySemanticContent(content) {
  const text = String(content ?? '').trim();
  if (!text) return true;
  if (BOOKKEEPING_PATTERN.test(text)) return true;
  if (/^LH0-OBL-[A-Z0-9_-]+:/.test(text)) return true;
  return false;
}

export function seedLh0ObligationFromFixture(fixtureObligation, { mechanism, source }) {
  return {
    ...fixtureObligation,
    semantic_content: fixtureObligation.semantic_content,
    obligation_text: fixtureObligation.semantic_content,
    summary: fixtureObligation.semantic_content,
    source,
    cognition_mechanism: mechanism,
  };
}

export function loadLh0CausalDesign(fixture = null) {
  const fx = fixture ?? loadLh0FixtureManifest();
  if (!fx.causal_design) {
    throw new Error('fixture missing causal_design');
  }
  return fx.causal_design;
}

export function listDecisionForks(fixture = null) {
  return loadLh0CausalDesign(fixture).decision_forks ?? [];
}

function normalizeHaystack(...parts) {
  return parts.map((p) => String(p ?? '').toLowerCase()).join('\n');
}

function matchesAnyMarker(haystack, markers = []) {
  return markers.some((m) => haystack.includes(String(m).toLowerCase()));
}

const GUEST_PROHIBITION_PROPOSITION_MARKERS = [
  'overnight guests are not',
  "overnight guests aren't",
  'no overnight guests',
  'no overnight visitors',
  'guests are not permitted',
  'never permitted',
  'do not stay overnight',
  "don't stay overnight",
  'no one stays overnight',
  'guests do not stay',
  'visitors do not stay',
  'not allowed to stay overnight',
];

export function communicatesGuestProhibition(haystack) {
  const text = normalizeHaystack(haystack);
  return GUEST_PROHIBITION_PROPOSITION_MARKERS.some((m) => text.includes(m));
}

export function adjudicateGuestPolicySemanticUse({ moveText = '', presentationText = '' }) {
  const haystack = `${moveText}\n${presentationText}`;
  const communicates = communicatesGuestProhibition(haystack);
  if (communicates) {
    return {
      category: 'S2',
      communicates_prohibition: true,
      rationale: 'Committed output clearly communicates overnight-guest prohibition.',
    };
  }
  const text = normalizeHaystack(haystack);
  const incidentalGuest = text.includes('guest') && !text.includes('overnight');
  if (incidentalGuest || text.length < 40) {
    return {
      category: 'S0',
      communicates_prohibition: false,
      rationale: 'No clear communication or operationalization of overnight-guest prohibition.',
    };
  }
  return {
    category: 'S1',
    communicates_prohibition: false,
    rationale: 'Response may be compatible with awareness but does not establish prohibition communication.',
  };
}

export function classifyBehaviorAgainstFork({ fork, haystack }) {
  const text = normalizeHaystack(haystack);
  const withClass = (fork.with_obligation_choice_classes ?? []).find((c) => (
    matchesAnyMarker(text, c.behavior_markers)
  ));
  const withoutClass = (fork.without_obligation_choice_classes ?? []).find((c) => (
    matchesAnyMarker(text, c.behavior_markers)
  ));
  return { withClass, withoutClass };
}

export function evaluateTurnCausalEvidence({
  turnIndex,
  moveText = '',
  presentationText = '',
  receivedObligationIds = [],
  fixture = null,
}) {
  const fx = fixture ?? loadLh0FixtureManifest();
  const forks = listDecisionForks(fx).filter((f) => f.decision_turn === turnIndex);
  const haystack = normalizeHaystack(moveText, presentationText);
  const matchedForks = [];
  const influencedObligationIds = new Set();
  let consumerUsed = false;
  let decisionInfluenced = false;

  for (const fork of forks) {
    const linked = (fork.obligation_ids ?? []).filter((id) => receivedObligationIds.includes(id));
    if (!linked.length) continue;
    const { withClass, withoutClass } = classifyBehaviorAgainstFork({ fork, haystack });
    if (withClass) {
      consumerUsed = true;
      decisionInfluenced = true;
      for (const id of linked) influencedObligationIds.add(id);
      matchedForks.push({
        fork_id: fork.fork_id,
        choice_class: withClass.class_id,
        obligation_ids: linked,
        direction: 'with_obligation',
      });
    } else if (withoutClass) {
      matchedForks.push({
        fork_id: fork.fork_id,
        choice_class: withoutClass.class_id,
        obligation_ids: linked,
        direction: 'without_obligation_pattern',
      });
    }
  }

  return {
    turn_index: turnIndex,
    consumer_used: consumerUsed,
    decision_influenced: decisionInfluenced,
    influenced_obligation_ids: [...influencedObligationIds],
    matched_forks: matchedForks,
  };
}

export function buildInformationUniquenessReport({ manifestContributions = [], fixture = null }) {
  const fx = fixture ?? loadLh0FixtureManifest();
  const design = loadLh0CausalDesign(fx);
  const probeIds = design.information_uniqueness_obligations ?? [];
  const nonLh0Text = (manifestContributions ?? [])
    .filter((c) => !c?.provenance?.lh0_obligation_id)
    .map((c) => String(c.content ?? '').toLowerCase())
    .join('\n');

  const entries = probeIds.map((obligationId) => {
    const row = fixtureObligationById(fx, obligationId);
    const semantic = String(row?.semantic_content ?? '').toLowerCase();
    const markerTerms = listDecisionForks(fx)
      .filter((f) => (f.obligation_ids ?? []).includes(obligationId))
      .flatMap((f) => (f.with_obligation_choice_classes ?? []).flatMap((c) => c.behavior_markers ?? []))
      .map((m) => String(m).toLowerCase());

    const duplicateMarkers = markerTerms.filter((m) => nonLh0Text.includes(m));
    const semanticDuplicated = semantic
      ? nonLh0Text.includes(semantic.slice(0, Math.min(40, semantic.length)))
      : false;

    return {
      obligation_id: obligationId,
      unique_to_persistent_cognition: duplicateMarkers.length === 0 && !semanticDuplicated,
      duplicate_markers_elsewhere: duplicateMarkers,
      semantic_fragment_duplicated: semanticDuplicated,
      independently_in_scenario_context: false,
      independently_in_transcript: duplicateMarkers.length > 0,
    };
  });

  return {
    schema: 'issue201_lh0_information_uniqueness_v1',
    obligations: entries,
    all_unique: entries.every((e) => e.unique_to_persistent_cognition),
  };
}

export function buildSalienceComparabilityReport(projectionsByArm) {
  const arms = Object.keys(projectionsByArm);
  const snapshots = arms.map((arm) => {
    const projection = projectionsByArm[arm];
    const contrib = projection?.contributions?.[0] ?? {};
    return {
      arm,
      source_kind: contrib.source_kind ?? null,
      priority: contrib.priority ?? null,
      content_length: String(contrib.content ?? '').length,
      section: contrib.source_kind ?? 'active_constraints',
    };
  });
  const priorities = snapshots.map((s) => s.priority);
  const kinds = snapshots.map((s) => s.source_kind);
  return {
    schema: 'issue201_lh0_salience_comparability_v1',
    snapshots,
    comparable: new Set(priorities).size <= 1 && new Set(kinds).size <= 1,
  };
}

export function deferredObligationWithheldBeforeActivation(store, obligationId, turn) {
  const ob = store.obligations.find((o) => o.obligation_id === obligationId);
  if (!ob) return false;
  const active = evaluateActivationPredicate(ob.activation_predicate, turn);
  if (active) return true;
  return ob.lifecycle_state === LIFECYCLE_STATES.DEFERRED_VALID
    || turn < (ob.activation_horizon_turn ?? 999);
}

export function obligationMetDeferredLaterChain(store, obligationId, { turns = [] } = {}) {
  const ob = store.obligations.find((o) => o.obligation_id === obligationId);
  if (!ob) return false;
  const hadDeferred = store.events.some((e) => (
    e.obligation_id === obligationId
    && (e.event_type === 'deferred_valid' || e.lifecycle_state === LIFECYCLE_STATES.DEFERRED_VALID)
  ));
  if (!hadDeferred || ob.activated_turn == null) return false;
  if (ob.lifecycle_state !== LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL) return false;

  const earlyReceipt = turns.some((t) => (
    t.turn_index < ob.activated_turn
    && (t.audit?.character_consumer_receipt?.received_obligation_ids ?? []).includes(obligationId)
  ));
  if (earlyReceipt) return false;

  const activationReceipt = turns.some((t) => (
    t.turn_index >= ob.activated_turn
    && (t.audit?.character_consumer_receipt?.consumer_received === true)
    && (t.audit?.character_consumer_receipt?.received_obligation_ids ?? []).includes(obligationId)
  ));
  return activationReceipt;
}
