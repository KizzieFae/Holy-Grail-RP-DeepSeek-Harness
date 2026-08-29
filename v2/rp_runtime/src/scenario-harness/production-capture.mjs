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
    capture.manifest_material = boundText(JSON.stringify(body), MANIFEST_BOUND);
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
    gates.protection_observed = {
      name: 'protection_observed',
      pass: storytellerCount === 0,
      detail: storytellerCount === 0 ? 'withheld' : 'unexpected_delivery',
    };
  }
  if (challenge === 'safe_translation') {
    gates.delivery_or_explicit_withhold = {
      name: 'delivery_or_explicit_withhold',
      pass: storytellerCount > 0 || capture.layer_b.first?.verdict === 'withhold',
      detail: capture.layer_b.first?.verdict ?? null,
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
