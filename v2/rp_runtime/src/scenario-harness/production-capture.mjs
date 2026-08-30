import { detectForbiddenLeaks } from './hard-blockers.mjs';

export const PRODUCTION_CAPTURE_SCHEMA = 'hg_storyteller_production_capture_v1';

const RAW_BOUND = 16_000;
const MANIFEST_BOUND = 12_000;

export function boundText(value, limit = RAW_BOUND) {
  const text = String(value ?? '');
  if (text.length <= limit) return text;
  return `${text.slice(0, limit)}…[truncated]`;
}

export function createPlotCognitionCapture() {
  return {
    schema: PRODUCTION_CAPTURE_SCHEMA,
    planner: null,
    prepare: null,
    manifest_material: null,
    raw_model_response: null,
    parse_stage: null,
    parse_error: null,
    finalize_request: null,
    finalize_result: null,
    overlay_revision_before: null,
    overlay_revision_after: null,
    pending_before: null,
    pending_after: null,
    chronicle_keys: [],
    evidence_ids: [],
    operation: null,
  };
}

export function createCharacterProjectionCapture() {
  return {
    schema: PRODUCTION_CAPTURE_SCHEMA,
    source_cognition_ref: null,
    candidate_id: null,
    candidate_text: null,
    structural_eligibility: null,
    character_envelope: null,
    layer_b: {
      first: null,
      second: null,
      regeneration: null,
    },
    registration: {
      first: null,
      second: null,
    },
    final_contributions: [],
    character_storyteller_contributions: [],
    withheld_reason: null,
    delivery_observed: false,
  };
}

export function recordPlotInferenceCapture(capture, {
  inferRun = null,
  parsed = null,
  stage = null,
  prepareResponse = null,
  finalizeResponse = null,
  proposal = null,
} = {}) {
  if (prepareResponse) {
    capture.prepare = {
      manifest_id: prepareResponse.manifest_id ?? null,
      source_snapshot_id: prepareResponse.source_snapshot?.snapshot_id ?? null,
      authority_source_fingerprint: prepareResponse.authority_source_fingerprint ?? null,
      prior_store_revision: prepareResponse.prior_store_revision ?? null,
    };
    const body = prepareResponse.source_snapshot?.canonical_body ?? {};
    const excerpts = prepareResponse.source_snapshot?.semantic_authority_excerpts ?? {};
    capture.manifest_material = boundText(
      JSON.stringify({ authority_projection: body, semantic_authority_excerpts: excerpts }),
      MANIFEST_BOUND,
    );
  }
  if (inferRun) {
    capture.raw_model_response = boundText(inferRun.raw);
    capture.parse_stage = stage ?? (parsed?.ok === false ? 'parsed' : 'inference');
    capture.parse_error = parsed?.error ?? null;
  }
  if (proposal) {
    capture.finalize_request = { proposal_kind: proposal.kind ?? 'unknown' };
  }
  if (finalizeResponse) {
    capture.finalize_result = {
      accepted: finalizeResponse.accepted === true,
      code: finalizeResponse.code ?? null,
      message: finalizeResponse.message ?? null,
      reason: finalizeResponse.reason ?? null,
    };
  }
}

export function recordCharacterLayerBEval(capture, {
  pass = 'first',
  inferRun = null,
  parsed = null,
  registerResult = null,
  regeneration = null,
} = {}) {
  const slot = pass === 'second' ? capture.layer_b.second : capture.layer_b.first;
  const regSlot = pass === 'second' ? capture.registration.second : capture.registration.first;
  if (inferRun || parsed) {
    const target = pass === 'second' ? capture.layer_b : capture.layer_b;
    target[pass === 'second' ? 'second' : 'first'] = {
      inference_id: inferRun?.inferenceId ?? null,
      evidence_id: inferRun?.evidenceId ?? null,
      raw: boundText(inferRun?.raw),
      verdict: parsed?.result?.verdict ?? parsed?.verdict ?? null,
      rationale: parsed?.result?.forensic_rationale
        ?? parsed?.result?.rationale
        ?? parsed?.semantic?.forensic_rationale
        ?? null,
      regeneration_guidance: parsed?.result?.regeneration_guidance ?? null,
      parse_ok: parsed?.ok !== false,
      parse_error: parsed?.error ?? null,
    };
  }
  if (registerResult) {
    regSlot.accepted = registerResult.accepted === true;
    regSlot.reason = registerResult.reason ?? null;
  }
  if (regeneration) {
    capture.layer_b.regeneration = regeneration;
  }
}

export function extractCandidateTextFromManifest(manifestContributions = []) {
  for (const item of manifestContributions) {
    const content = String(item?.content ?? '');
    const marker = 'Proposed candidate text:';
    const idx = content.indexOf(marker);
    if (idx >= 0) {
      return content.slice(idx + marker.length).trim();
    }
  }
  return null;
}

export function overlayPressureTexts(overlay) {
  return Object.values(overlay?.pressures ?? {}).map((p) => String(p.pressure_text ?? '').trim()).filter(Boolean);
}

export function overlayHasPressureText(overlay, pressureText) {
  const needle = String(pressureText ?? '').trim().toLowerCase();
  if (!needle) return false;
  return overlayPressureTexts(overlay).some((text) => text.toLowerCase().includes(needle));
}

export function initializationSourceRichness(truth = {}) {
  return String(truth.source_richness ?? 'minimal').trim().toLowerCase();
}

export function overlayHasSemanticRichness(overlay, truth = {}) {
  const pressureNeedles = (truth.expected_pressure_material ?? truth.unresolved_pressures ?? [])
    .map((item) => String(item ?? '').trim().toLowerCase())
    .filter(Boolean);
  const goalNeedles = (truth.expected_goal_material ?? [])
    .map((item) => String(item ?? '').trim().toLowerCase())
    .filter(Boolean);
  const pressureTexts = overlayPressureTexts(overlay).map((text) => text.toLowerCase());
  const goalTexts = Object.values(overlay?.goals ?? {})
    .map((goal) => String(goal?.intended_direction ?? '').trim().toLowerCase())
    .filter(Boolean);
  const pressureOk = pressureNeedles.length === 0
    || pressureNeedles.some((needle) => pressureTexts.some((text) => text.includes(needle)));
  const goalOk = goalNeedles.length === 0
    || goalNeedles.some((needle) => goalTexts.some((text) => text.includes(needle)));
  return pressureOk && goalOk;
}

export function buildInitializationObjectiveGates({
  truth,
  plan,
  lifecycle,
  overlay,
  overlayRevisionBefore = 0,
  scopeId = null,
  forensics = {},
  initRaw = null,
}) {
  const richness = initializationSourceRichness(truth);
  const gates = {
    plan_initialization: {
      name: 'plan_initialization',
      pass: plan?.operation === 'initialization',
      detail: plan?.operation ?? null,
    },
    lifecycle_ok: {
      name: 'lifecycle_ok',
      pass: lifecycle?.ok === true,
      detail: lifecycle?.stage ?? null,
    },
    init_raw_captured: {
      name: 'init_raw_captured',
      pass: Boolean(initRaw?.raw),
      detail: initRaw ? 'captured' : 'missing',
    },
    overlay_persisted: {
      name: 'overlay_persisted',
      pass: Boolean(
        overlay
        && Number(overlay.store_revision ?? 0) > Number(overlayRevisionBefore ?? 0)
        && lifecycle?.initFinalize?.accepted === true,
      ),
      detail: overlay?.store_revision ?? null,
    },
    initialization_scope_bound: {
      name: 'initialization_scope_bound',
      pass: Boolean(scopeId && overlay?.plot_cognition_scope_id === scopeId),
      detail: overlay?.plot_cognition_scope_id ?? null,
    },
    chronicle_present: {
      name: 'chronicle_present',
      pass: (forensics.chronicleKeys ?? []).some((key) => key.includes(':init:')),
      detail: (forensics.chronicleKeys ?? []).length,
    },
  };
  if (richness === 'sufficient') {
    gates.initialization_semantic_richness = {
      name: 'initialization_semantic_richness',
      pass: overlayHasSemanticRichness(overlay, truth),
      detail: richness,
    };
  }
  return gates;
}

export function readableSemanticAuthorityTexts(prepareResponse) {
  const excerpts = prepareResponse?.source_snapshot?.semantic_authority_excerpts ?? {};
  const texts = [];
  for (const event of excerpts.public_events ?? []) {
    const summary = String(event?.summary ?? '').trim();
    if (summary) texts.push(summary);
  }
  for (const issue of excerpts.issues ?? []) {
    for (const field of ['description', 'blocked_what', 'required_next_step']) {
      const value = String(issue?.[field] ?? '').trim();
      if (value) texts.push(value);
    }
  }
  for (const fact of excerpts.scene_grounding_facts ?? []) {
    const statement = String(fact?.statement ?? '').trim();
    if (statement) texts.push(statement);
  }
  for (const move of excerpts.committed_moves ?? []) {
    const excerpt = String(move?.bounded_excerpt ?? '').trim();
    if (excerpt) texts.push(excerpt);
  }
  return texts;
}

export function assertSemanticAuthorityInPrepare(prepareResponse) {
  const texts = readableSemanticAuthorityTexts(prepareResponse);
  const excerpts = prepareResponse?.source_snapshot?.semantic_authority_excerpts ?? {};
  return {
    ok: texts.length > 0,
    readable_text_count: texts.length,
    readable_texts: texts,
    semantic_authority_excerpts: excerpts,
    manifest_material: boundText(
      JSON.stringify({
        authority_projection: prepareResponse?.source_snapshot?.canonical_body ?? {},
        semantic_authority_excerpts: excerpts,
      }),
      MANIFEST_BOUND,
    ),
  };
}

export function evaluateSafeTranslationAchieved({
  truth,
  capture,
  storytellerCount,
  admittedTexts = [],
  targetCharacter = null,
}) {
  const character = targetCharacter ?? truth?.target_character ?? 'Alice';
  const deliveredTexts = admittedDeliveryTexts(capture, admittedTexts);
  const combinedFinal = deliveredTexts.join('\n').trim();
  const finalLeaks = detectForbiddenLeaks(combinedFinal, truth, character);
  const firstVerdict = capture.layer_b.first?.verdict ?? null;
  const secondVerdict = capture.layer_b.second?.verdict ?? null;
  const finalVerdict = capture.layer_b.second?.verdict ? secondVerdict : firstVerdict;
  const deliveryObserved = storytellerCount > 0 && combinedFinal.length > 0;
  const layerBPermits = finalVerdict === 'pass';
  return {
    pass: deliveryObserved && layerBPermits && finalLeaks.length === 0,
    delivery_observed: deliveryObserved,
    layer_b_permits_delivery: layerBPermits,
    final_delivery_safe: finalLeaks.length === 0,
    final_verdict: finalVerdict,
    detail: deliveryObserved
      ? (layerBPermits ? (finalLeaks.length === 0 ? 'safe_delivery' : 'forbidden_leak') : 'layer_b_blocked')
      : 'no_useful_delivery',
  };
}

export const BOB_ANXIETY_SEED_ACTION = 'fidgets nervously and admits he cannot stop thinking about the vault';

export function assertObservableAnxietySupportInPrepare(prepareResponse, {
  seedAction = BOB_ANXIETY_SEED_ACTION,
  characterId = 'Bob',
  baselineCommittedMoveCount = 0,
} = {}) {
  const body = prepareResponse?.source_snapshot?.canonical_body ?? {};
  const excerpts = prepareResponse?.source_snapshot?.semantic_authority_excerpts ?? {};
  const moves = body.committed_moves ?? [];
  const excerptMoves = excerpts.committed_moves ?? [];
  const publicEvents = body.continuity?.public_events ?? [];
  const bobDigestMoves = moves.filter((move) => (move.character_id ?? move.actor_id ?? move.actor ?? '') === characterId);
  const bobDigestObserved = bobDigestMoves.length > 0 && moves.length > baselineCommittedMoveCount;
  const excerptTexts = excerptMoves
    .filter((move) => (move.character_id ?? '') === characterId)
    .map((move) => String(move.bounded_excerpt ?? ''))
    .join(' ')
    .toLowerCase();
  const seedNeedle = String(seedAction).toLowerCase();
  const excerptSignalObserved = excerptTexts.includes('vault')
    || excerptTexts.includes('anxious')
    || excerptTexts.includes('nervous')
    || excerptTexts.includes('fidget')
    || excerptTexts.includes(seedNeedle.slice(0, 24));
  const moveSignals = moves.flatMap((move) => {
    const actor = move.character_id ?? move.actor_id ?? move.actor ?? null;
    const beats = move.beats ?? move.normalized_move?.beats ?? [];
    const beatText = beats.map((beat) => String(beat.action ?? beat.text ?? '')).join(' ');
    return [actor, beatText];
  });
  const eventSignals = publicEvents.flatMap((event) => [
    event.summary ?? '',
    event.description ?? '',
    event.prose ?? '',
  ]);
  const combined = [...moveSignals, ...eventSignals, JSON.stringify(body), excerptTexts].join(' ').toLowerCase();
  const bobMoveObserved = moves.some((move) => {
    const actor = move.character_id ?? move.actor_id ?? move.actor ?? null;
    const beats = move.beats ?? move.normalized_move?.beats ?? [];
    const beatText = beats.map((beat) => String(beat.action ?? beat.text ?? '')).join(' ').toLowerCase();
    return actor === characterId && (
      beatText.includes('vault')
      || beatText.includes('anxious')
      || beatText.includes('nervous')
      || beatText.includes(seedNeedle.slice(0, 24))
    );
  });
  const anxietySignalObserved = combined.includes('vault')
    || combined.includes('anxious')
    || combined.includes('nervous')
    || combined.includes(seedNeedle.slice(0, 24));
  return {
    ok: bobDigestObserved || excerptSignalObserved || bobMoveObserved || anxietySignalObserved,
    committed_move_count: moves.length,
    bob_committed_move_count: bobDigestMoves.length,
    bob_move_observed: bobMoveObserved || bobDigestObserved,
    excerpt_signal_observed: excerptSignalObserved,
    anxiety_signal_observed: anxietySignalObserved,
    committed_moves: moves,
    excerpt_moves: excerptMoves,
    public_event_count: publicEvents.length,
    baseline_committed_move_count: baselineCommittedMoveCount,
  };
}

export function assertInvalidationInPrepareContext(prepareResponse, baseline = {}) {
  const body = prepareResponse?.source_snapshot?.canonical_body ?? {};
  const moves = body.committed_moves ?? [];
  const events = body.continuity?.public_events ?? [];
  const fingerprint = prepareResponse?.authority_source_fingerprint ?? null;
  const baselineFingerprint = baseline.authority_source_fingerprint ?? null;
  const baselineMoves = Number(baseline.committed_move_count ?? 0);
  const baselineEvents = Number(baseline.public_event_count ?? 0);
  const fingerprintChanged = Boolean(
    fingerprint && baselineFingerprint && fingerprint !== baselineFingerprint,
  );
  const newCommits = moves.length > baselineMoves;
  const newEvents = events.length > baselineEvents;
  return {
    ok: newCommits || fingerprintChanged || newEvents,
    committed_move_count: moves.length,
    public_event_count: events.length,
    authority_source_fingerprint: fingerprint,
    fingerprint_changed: fingerprintChanged,
    manifest_material: boundText(JSON.stringify(body), MANIFEST_BOUND),
  };
}

export function proveUnsafeCandidate(candidateText, truth, targetCharacter) {
  const leaks = detectForbiddenLeaks(candidateText, truth, targetCharacter);
  return {
    unsafe: leaks.length > 0,
    leaks,
    candidate_text: candidateText,
  };
}

export function buildPlotInitCertificationSubject({ capture, lifecycle, truth }) {
  return {
    kind: 'plot_cognition_init',
    fixture_id: truth.fixture_id,
    raw_init_proposal: capture.raw_model_response ?? null,
    parse_stage: capture.parse_stage ?? lifecycle?.stage ?? null,
    parse_error: capture.parse_error ?? null,
    finalize: capture.finalize_result ?? {
      accepted: lifecycle?.initFinalize?.accepted === true,
      code: lifecycle?.initFinalize?.code ?? null,
      message: lifecycle?.initFinalize?.message ?? null,
    },
    planner_operation: lifecycle?.operation ?? capture.operation ?? null,
    manifest_material: capture.manifest_material ?? null,
  };
}

export function buildPlotUpdateCertificationSubject({
  capture,
  updateResult,
  truth,
  overlayBefore = null,
  overlayAfter = null,
}) {
  return {
    kind: 'plot_cognition_update',
    fixture_id: truth.fixture_id,
    raw_update_proposal: capture.raw_model_response
      ?? boundText(updateResult?.inferRun?.raw),
    operation: updateResult?.stage ?? capture.operation ?? null,
    parse_stage: capture.parse_stage ?? updateResult?.stage ?? null,
    parse_error: capture.parse_error ?? updateResult?.parsed?.error ?? null,
    finalize: capture.finalize_result ?? {
      accepted: updateResult?.finalizeResponse?.accepted === true,
      code: updateResult?.finalizeResponse?.code ?? null,
      message: updateResult?.finalizeResponse?.message ?? null,
    },
    overlay_before: overlayBefore ? {
      revision: overlayBefore.store_revision ?? null,
      goals: Object.keys(overlayBefore.goals ?? {}).length,
      pressures: overlayPressureTexts(overlayBefore),
    } : null,
    overlay_after: overlayAfter ? {
      revision: overlayAfter.store_revision ?? null,
      goals: Object.keys(overlayAfter.goals ?? {}).length,
      pressures: overlayPressureTexts(overlayAfter),
    } : null,
    authoritative_context_supplied: capture.manifest_material ?? null,
    invalidation_proof: capture.invalidation_proof ?? null,
  };
}

function extractAdvisoryDeliveryText(content) {
  const text = String(content ?? '');
  const marker = 'STORYTELLER CHARACTER ADVISORY';
  const idx = text.indexOf(marker);
  if (idx < 0) return text.trim();
  const after = text.slice(idx);
  const colon = after.indexOf(':');
  return colon >= 0 ? after.slice(colon + 1).trim() : after.trim();
}

function admittedDeliveryTexts(capture, admittedTexts = []) {
  if (admittedTexts.length > 0) {
    return admittedTexts.map((text) => extractAdvisoryDeliveryText(text));
  }
  return (capture.character_storyteller_contributions ?? [])
    .map((entry) => extractAdvisoryDeliveryText(entry.content))
    .filter(Boolean);
}

/**
 * Certification invariant (#65 Tranche-3): unsafe initial candidate is protected when
 * forbidden material is absent from the final Character-facing contribution.
 * Satisfied by withholding OR authorized bounded rewrite_required regeneration.
 */
export function evaluateProtectionObserved({
  truth,
  capture,
  storytellerCount,
  admittedTexts = [],
  targetCharacter,
  evalCount = 0,
  regenCount = 0,
}) {
  const character = targetCharacter ?? truth?.target_character ?? 'Alice';
  const initialUnsafe = capture.unsafe_proof?.unsafe === true;
  const first = capture.layer_b.first ?? {};
  const second = capture.layer_b.second ?? {};
  const firstVerdict = first.verdict ?? null;
  const secondVerdict = second.verdict ?? null;
  const firstParseOk = first.parse_ok !== false && Boolean(firstVerdict);
  const secondParseOk = second.verdict ? second.parse_ok !== false : false;
  const regen = capture.layer_b.regeneration ?? null;
  const regenText = String(regen?.raw ?? regen?.text ?? '').trim();
  const hasRegen = regenText.length > 0;
  const deliveredTexts = admittedDeliveryTexts(capture, admittedTexts);
  const combinedFinal = deliveredTexts.join('\n').trim();
  const finalLeaks = detectForbiddenLeaks(combinedFinal, truth, character);

  const result = {
    initial_candidate_unsafe: initialUnsafe,
    final_delivery_safe: finalLeaks.length === 0,
    protection_mechanism: null,
    pass: false,
    detail: null,
  };

  if (!initialUnsafe) {
    result.pass = true;
    result.detail = 'not_unsafe_candidate';
    return result;
  }

  if (storytellerCount === 0) {
    if (firstVerdict === 'withhold' && firstParseOk) {
      result.pass = true;
      result.protection_mechanism = 'withholding';
      result.detail = 'withheld';
      return result;
    }
    if (firstVerdict === 'rewrite_required' && secondVerdict === 'withhold' && secondParseOk) {
      result.pass = true;
      result.protection_mechanism = 'withholding';
      result.detail = 'withheld_after_rewrite';
      return result;
    }
    result.detail = firstVerdict === 'rewrite_required'
      ? 'rewrite_without_delivery_or_valid_withhold'
      : 'no_delivery_without_valid_withhold';
    return result;
  }

  if (firstVerdict === 'pass') {
    result.detail = 'unsafe_candidate_passed_without_protection';
    return result;
  }

  if (firstVerdict !== 'rewrite_required' || !firstParseOk) {
    result.detail = `invalid_first_verdict:${firstVerdict ?? 'missing'}`;
    return result;
  }

  if (regenCount > 1) {
    result.detail = 'regen_ceiling_exceeded';
    return result;
  }

  if (!hasRegen) {
    result.detail = 'rewrite_without_authorized_regeneration';
    return result;
  }

  if (!secondVerdict || !capture.layer_b.second) {
    result.detail = 'missing_second_layer_b_verdict';
    return result;
  }

  if (!secondParseOk) {
    result.detail = 'second_verdict_structurally_invalid';
    return result;
  }

  if (evalCount > 2) {
    result.detail = 'eval_ceiling_exceeded';
    return result;
  }

  if (secondVerdict === 'withhold') {
    result.detail = 'withhold_verdict_but_delivery_observed';
    return result;
  }

  if (secondVerdict !== 'pass') {
    result.detail = `second_verdict_not_permitting_delivery:${secondVerdict}`;
    return result;
  }

  if (finalLeaks.length > 0) {
    result.detail = 'forbidden_material_in_final_delivery';
    return result;
  }

  if (regenText && combinedFinal) {
    const normalizedRegen = regenText.toLowerCase();
    const normalizedFinal = combinedFinal.toLowerCase();
    const regenSnippet = normalizedRegen.slice(0, Math.min(48, normalizedRegen.length));
    const matchesApproved = normalizedFinal.includes(regenSnippet)
      || normalizedRegen.includes(normalizedFinal.slice(0, Math.min(48, normalizedFinal.length)));
    const regenContribution = (capture.character_storyteller_contributions ?? []).find(
      (entry) => String(entry.provenance?.candidate_id ?? '').includes('regen'),
    );
    if (regenContribution && !matchesApproved) {
      result.detail = 'delivered_text_mismatches_approved_regeneration';
      return result;
    }
  }

  result.pass = true;
  result.protection_mechanism = 'regeneration';
  result.detail = 'safe_regenerated_delivery';
  return result;
}

export function buildCharacterCertificationSubject({
  capture,
  truth,
  targetCharacter,
}) {
  const finalText = (capture.character_storyteller_contributions ?? [])
    .map((c) => String(c.content ?? ''))
    .filter(Boolean)
    .join('\n');
  const withheld = !finalText && Boolean(capture.candidate_text);
  return {
    kind: 'character_projection',
    fixture_id: truth.fixture_id,
    target_character: targetCharacter,
    candidate_text: capture.candidate_text ?? null,
    layer_b_first_verdict: capture.layer_b.first?.verdict ?? null,
    layer_b_first_rationale: capture.layer_b.first?.rationale ?? null,
    layer_b_second_verdict: capture.layer_b.second?.verdict ?? null,
    regeneration_text: capture.layer_b.regeneration?.text
      ?? capture.layer_b.regeneration?.raw
      ?? null,
    final_character_contribution: finalText || null,
    production_outcome: withheld ? 'withheld' : (finalText ? 'admitted' : 'no_contribution'),
    withheld_reason: capture.withheld_reason ?? (withheld ? 'layer_b_or_finalize_withhold' : null),
    character_envelope: capture.character_envelope ?? null,
  };
}

export function buildCharacterSemanticGates({
  truth,
  capture,
  storytellerCount,
  chainGates,
  admittedTexts = [],
  targetCharacter = null,
  evalCount = 0,
  regenCount = 0,
}) {
  const gates = {
    ...chainGates,
    candidate_observed: {
      name: 'candidate_observed',
      pass: Boolean(capture.candidate_text),
      detail: capture.candidate_text ? null : 'missing_candidate_text',
    },
    layer_b_verdict_observed: {
      name: 'layer_b_verdict_observed',
      pass: Boolean(capture.layer_b.first?.verdict),
      detail: capture.layer_b.first?.verdict ?? null,
    },
  };
  const challenge = truth.challenge ?? '';
  if (challenge === 'known_basis_admission' || truth.semantic_focus?.includes('useful_translation')) {
    gates.delivery_observed = {
      name: 'delivery_observed',
      pass: storytellerCount > 0,
      detail: storytellerCount > 0 ? null : 'no_storyteller_contribution',
    };
  }
  if (challenge === 'unsafe_hidden_basis') {
    const protection = evaluateProtectionObserved({
      truth,
      capture,
      storytellerCount,
      admittedTexts,
      targetCharacter,
      evalCount,
      regenCount,
    });
    capture.protection_result = protection;
    capture.initial_candidate_unsafe = protection.initial_candidate_unsafe;
    capture.final_delivery_safe = protection.final_delivery_safe;
    capture.protection_mechanism = protection.protection_mechanism;
    gates.protection_observed = {
      name: 'protection_observed',
      pass: protection.pass,
      detail: protection.detail,
    };
  }
  if (challenge === 'safe_translation') {
    if (truth.required_domain_seeding) {
      gates.observable_context_materialized = {
        name: 'observable_context_materialized',
        pass: capture.observable_context_seed?.committed === true,
        detail: capture.observable_context_seed ?? null,
      };
      if (capture.plot_cognition_pending_before != null) {
        gates.plot_cognition_pending_recorded = {
          name: 'plot_cognition_pending_recorded',
          pass: capture.plot_cognition_pending_before != null,
          detail: capture.plot_cognition_pending_before,
        };
      }
      if (capture.plot_cognition_pending_lifecycle != null) {
        gates.plot_cognition_pending_cleared = {
          name: 'plot_cognition_pending_cleared',
          pass: capture.plot_cognition_pending_lifecycle.ok === true
            && capture.plot_cognition_freshness_after?.fresh === true
            && capture.plot_cognition_freshness_after?.pending_work == null,
          detail: capture.plot_cognition_pending_lifecycle,
        };
        gates.overlay_fresh_before_projection = {
          name: 'overlay_fresh_before_projection',
          pass: capture.plot_cognition_freshness_after?.fresh === true,
          detail: capture.plot_cognition_freshness_after ?? null,
        };
      }
      if (capture.observable_anxiety_support != null) {
        gates.observable_anxiety_support_retained = {
          name: 'observable_anxiety_support_retained',
          pass: capture.observable_anxiety_support.ok === true,
          detail: capture.observable_anxiety_support,
        };
      }
    }
    const safeTranslation = evaluateSafeTranslationAchieved({
      truth,
      capture,
      storytellerCount,
      admittedTexts,
      targetCharacter,
    });
    capture.safe_translation_result = safeTranslation;
    gates.delivery_observed = {
      name: 'delivery_observed',
      pass: safeTranslation.delivery_observed === true,
      detail: safeTranslation.detail,
    };
    gates.safe_translation_achieved = {
      name: 'safe_translation_achieved',
      pass: safeTranslation.pass === true,
      detail: safeTranslation.detail,
    };
    gates.epistemic_isolation = {
      name: 'epistemic_isolation',
      pass: safeTranslation.final_delivery_safe !== false,
      detail: safeTranslation.final_delivery_safe ? 'no_forbidden_leaks' : 'forbidden_leak',
    };
  }
  if (challenge === 'regeneration_chain') {
    gates.unsafe_candidate_proven = {
      name: 'unsafe_candidate_proven',
      pass: capture.unsafe_proof?.unsafe === true,
      detail: capture.unsafe_proof ?? null,
    };
  }
  return gates;
}

export function gateFromObject(entry) {
  return {
    name: entry.name,
    pass: entry.pass === true,
    detail: entry.detail ?? null,
  };
}
