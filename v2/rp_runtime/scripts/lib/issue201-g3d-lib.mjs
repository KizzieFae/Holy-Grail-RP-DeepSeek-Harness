import fs from 'node:fs';
import path from 'node:path';

import {
  loadAttempts,
  filterAttemptsForRound,
  summarizeAttempts,
  A2_PROHIBITED_KINDS,
} from './issue201-g3-b-lib.mjs';
import { createSpatialClaimsResolver } from './issue201-g3-c-lib.mjs';

export { loadAttempts, filterAttemptsForRound, summarizeAttempts, createSpatialClaimsResolver };

export const STORYTELLER_KINDS = [
  'storyteller_orientation',
  'storyteller_assessment',
  'storyteller_post_commit_issue_pressure',
  'storyteller_post_commit_issue_pressure_contract_correction',
];

export const PLOT_KINDS = [
  'plot_cognition_init',
  'plot_cognition_update',
];

export function readJsonIfExists(filePath) {
  if (!fs.existsSync(filePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return null;
  }
}

export function extractContinuityForensics(hgSessionId, sessionsDir) {
  const sessionPath = path.join(sessionsDir, `${hgSessionId}.json`);
  const session = readJsonIfExists(sessionPath);
  if (!session) return { session_found: false };
  const manager = session.continuity_manager ?? session.manager ?? session;
  const overlays = manager.issue_pressure_semantic_overlays ?? {};
  const issues = manager.issues ?? manager.continuity_issues ?? {};
  const activeIssues = Object.entries(issues)
    .filter(([, v]) => {
      const state = typeof v === 'object' ? (v.state ?? v.status) : null;
      return state === 'ACTIVE' || state === 'ESCALATING';
    })
    .map(([id]) => id);
  return {
    session_found: true,
    continuity_version: manager.continuity_version ?? session.continuity_version ?? null,
    issue_pressure_semantic_overlays: overlays,
    active_issue_ids: activeIssues,
    plot_cognition_scope_id: session.plot_cognition_scope_id
      ?? manager.plot_cognition_scope_id
      ?? null,
  };
}

export function extractPlotForensics(plotScopeId, sessionsDir) {
  if (!plotScopeId) return { overlay_found: false };
  const safe = String(plotScopeId).replace(/[/\\]/g, '_');
  const overlayPath = path.join(sessionsDir, '_plot_cognition_overlay', `${safe}.json`);
  const payload = readJsonIfExists(overlayPath);
  if (!payload) return { overlay_found: false, overlay_path: overlayPath };
  const pressures = payload.unresolved_narrative_pressures
    ?? payload.pressures
    ?? {};
  return {
    overlay_found: true,
    overlay_path: overlayPath,
    overlay_revision: payload.revision ?? null,
    unresolved_narrative_pressures: pressures,
    plot_goals: payload.plot_goals ?? payload.goals ?? {},
    global_plot_frame: payload.global_plot_frame ?? null,
    advisory_authority: 'advisory_only',
  };
}

export function plotPressureKeys(forensics) {
  return Object.keys(forensics?.unresolved_narrative_pressures ?? {});
}

export function storytellerAbsenceProof(attempts) {
  const violations = attempts.filter((a) => STORYTELLER_KINDS.includes(a.inference_kind));
  return { pass: violations.length === 0, violations, count: violations.length };
}

export function plotOffAbsenceProof(attempts) {
  const violations = attempts.filter((a) => PLOT_KINDS.includes(a.inference_kind));
  return { pass: violations.length === 0, violations, count: violations.length };
}

export function a2ProhibitedSupportProof(attempts, { allowPlot = false } = {}) {
  const prohibited = allowPlot
    ? A2_PROHIBITED_KINDS
    : [...A2_PROHIBITED_KINDS, ...PLOT_KINDS];
  const violations = attempts.filter((a) => prohibited.includes(a.inference_kind));
  return { pass: violations.length === 0, violations, prohibited };
}

export function buildCrossTurnConsumptionEvidence(turns) {
  const links = [];
  for (let i = 0; i < turns.length - 1; i += 1) {
    const current = turns[i];
    const next = turns[i + 1];
    const afterKeys = plotPressureKeys(current.plot_forensics?.after);
    const beforeNextKeys = plotPressureKeys(next.plot_forensics?.before);
    const persisted = afterKeys.filter((k) => beforeNextKeys.includes(k));
    const plotRan = (current.plot_forensics?.inference?.plot_inference_count ?? 0) > 0;
    links.push({
      from_turn: current.turn_index,
      to_turn: next.turn_index,
      plot_update_ran: plotRan,
      pressures_after_turn: afterKeys,
      pressures_before_next: beforeNextKeys,
      persisted_keys: persisted,
      revision_after: current.plot_forensics?.after?.overlay_revision ?? null,
      revision_before_next: next.plot_forensics?.before?.overlay_revision ?? null,
      classification: persisted.length > 0 && plotRan
        ? 'transported'
        : plotRan ? 'updated_no_persisted_keys' : 'no_plot_update',
    });
  }
  return links;
}

export function classifyPlotDecisionValue(turn) {
  const records = [];
  const plotAttempts = (turn.inference?.kinds ?? []).filter((k) => PLOT_KINDS.includes(k.inference_kind));
  const before = turn.plot_forensics?.before ?? {};
  const after = turn.plot_forensics?.after ?? {};
  const beforeKeys = plotPressureKeys(before);
  const afterKeys = plotPressureKeys(after);
  const added = afterKeys.filter((k) => !beforeKeys.includes(k));
  const removed = beforeKeys.filter((k) => !afterKeys.includes(k));
  for (const k of plotAttempts) {
    records.push({
      turn_index: turn.turn_index,
      inference_kind: k.inference_kind,
      unique_information: added.length ? `pressures_added:${added.join(',')}` : 'overlay_revision_or_frame_update',
      consumer: 'next_turn_advisory_substrate',
      downstream_decision: added.length || (after.overlay_revision !== before.overlay_revision)
        ? 'persisted_advisory_state'
        : 'neutral_update',
      classification: added.length ? 'consequential' : (k.count > 0 ? 'transported_or_duplicate' : 'none'),
      plot_post_commit_wall_ms: turn.timing?.plot_post_commit_wall_ms ?? null,
    });
  }
  return records;
}

export function buildBlindSequencePacket(sequences, outputsDir) {
  const eligible = sequences.filter((s) => s.all_committed && !s.failed);
  const shuffled = [...eligible];
  const seed = 20130;
  let s = seed;
  for (let i = shuffled.length - 1; i > 0; i -= 1) {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    const j = s % (i + 1);
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  shuffled.forEach((seq, i) => {
    seq.blind_label = `SEQ-${String.fromCharCode(65 + i)}`;
  });
  const briefing = {
    arkham_asylum_mess_hall_arena: {
      setting: 'Arkham Asylum cafeteria. Harley Quinn and Poison Ivy at a table; Magpie (player) at another table. Guards on the margin.',
      player_character: 'Magpie',
    },
    ayame_household_entry_evaluation: {
      setting: 'Ayame household entry evaluation. Kizzie (applicant) at the threshold; Ayame (host) inside.',
      player_character: 'Kizzie',
    },
  };
  const packetPath = path.join(outputsDir, 'issue201-g3d-f3-blind-sequence-packet.json');
  const keyPath = path.join(outputsDir, 'issue201-g3d-f3-blind-sequence-answer-key.json');
  const packet = {
    schema: 'issue201_blind_sequence_packet_v1',
    purpose: 'Issue #201 G3-D F3 — longitudinal Plot/Scribe ON vs OFF (complete sequence bundles)',
    causal_question:
      'Can the accepted primary path preserve multi-turn narrative intelligence when persistent Plot/Scribe operates outside the player-visible critical path?',
    instructions:
      'Score each complete 4-turn sequence using the 10 sequence-level longitudinal dimensions plus overall RP usefulness. Do not request arm, Plot state, operational metadata, or latency metadata until after scoring is locked.',
    sequence_level_dimensions: [
      'unresolved-thread retention',
      'escalation/progression',
      'character-agenda continuity',
      'delayed-consequence handling',
      'momentum',
      'initiative',
      'loop avoidance',
      'no premature resolution',
      'plot/narrative drift',
      'continuity',
    ],
    adjunct_dimensions: ['overall_rp_usefulness'],
    sequences: shuffled.map((seq) => ({
      blind_label: seq.blind_label,
      scenario_briefing: briefing[seq.scenario_id] ?? { setting: seq.scenario_id },
      turns: seq.turns.map((t) => ({
        turn_index: t.turn_index,
        player_stimulus: t.exact_player_stimulus,
        presentation_text: t.presentation_text,
      })),
    })),
  };
  const answerKey = shuffled.map((seq) => ({
    blind_label: seq.blind_label,
    sequence_id: seq.sequence_id,
    arm_id: seq.arm_id,
    scenario_key: seq.scenario_key,
    scenario_id: seq.scenario_id,
    repetition_index: seq.repetition_index,
    policy_id: seq.policy_id,
    policy_hash: seq.policy_hash,
    branch_trajectory: seq.branch_trajectory,
    plot_on: seq.plot_on,
  }));
  fs.writeFileSync(packetPath, `${JSON.stringify(packet, null, 2)}\n`);
  fs.writeFileSync(keyPath, `${JSON.stringify(answerKey, null, 2)}\n`);
  const packetText = JSON.stringify(packet).toLowerCase();
  const forbiddenPatterns = [/\ba2\b/, /\bplot_on\b/, /\bplot_off\b/, /\binference\b/, /wall_ms/, /\btopology\b/];
  const leaked = forbiddenPatterns.filter((re) => re.test(packetText)).map((re) => re.source);
  return {
    packetPath,
    keyPath,
    sequence_count: shuffled.length,
    excluded: sequences.length - eligible.length,
    blinding_integrity: { pass: leaked.length === 0, leaked_patterns: leaked },
    answer_key_opened: false,
  };
}
