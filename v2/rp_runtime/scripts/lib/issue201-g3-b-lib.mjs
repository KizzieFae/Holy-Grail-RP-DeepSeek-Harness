import fs from 'node:fs';
import path from 'node:path';

export const F06_PLAYER_STIMULUS =
  'Kizzie glanced up, double-checking the house number and then steeled herself before knocking.';

export const LEAN_A4_ROUND_OPTIONS = {
  skipStorytellerCognition: true,
  skipLibrarianProposalGeneration: true,
  directorSemanticQaEnabled: false,
  narratorSemanticQaEnabled: false,
};

export const A2_PROHIBITED_KINDS = [
  'storyteller_orientation',
  'storyteller_assessment',
  'storyteller_post_commit_issue_pressure',
  'director_semantic_qa',
  'narrator_semantic_qa',
  'narrator_environment_cognition',
  'character_orientation',
  'librarian_mediation',
  'plot_cognition_epistemic_eval',
  'character_semantic_evaluation',
  'player_decomposition',
];

export function loadAttempts(evidenceRoot, sessionId) {
  const indexPath = path.join(evidenceRoot, sessionId, 'index.json');
  if (!fs.existsSync(indexPath)) return [];
  const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
  return (index.attempt_ids ?? []).map((attemptId) => {
    const attempt = JSON.parse(fs.readFileSync(
      path.join(evidenceRoot, sessionId, 'attempts', `${attemptId}.json`),
      'utf8',
    ));
    const usage = attempt.response?.usage ?? {};
    const timing = attempt.inference_health?.timing ?? attempt.timing ?? {};
    const corr = attempt.correlation ?? {};
    return {
      evidence_id: attempt.evidence_id ?? attemptId,
      inference_kind: corr.inference_kind ?? null,
      role: corr.role ?? null,
      hg_round_id: corr.hg_round_id ?? corr.hgRoundId ?? null,
      attempt_index: corr.attempt_index ?? 0,
      wall_ms: timing.inference_wall_clock_ms ?? timing.wall_ms ?? timing.duration_ms ?? null,
      input_tokens: usage.inputTokens ?? usage.input_tokens ?? null,
      output_tokens: usage.outputTokens ?? usage.output_tokens ?? null,
      reasoning_tokens: usage.reasoningTokens ?? usage.reasoning_tokens ?? null,
      decision: attempt.decision ?? {},
      correlation: corr,
    };
  });
}

export function filterAttemptsForRound(attempts, hgRoundId) {
  if (!hgRoundId) return attempts;
  return attempts.filter((row) => row.hg_round_id === hgRoundId);
}

export function summarizeAttempts(attempts) {
  const byKind = {};
  for (const row of attempts) {
    const key = row.inference_kind ?? 'unknown';
    if (!byKind[key]) byKind[key] = [];
    byKind[key].push(row);
  }
  const kindRows = (name) => byKind[name] ?? [];
  const narratorPresentation = kindRows('narrator_presentation');
  return {
    inference_count: attempts.length,
    synchronous_llm_count: attempts.filter((r) => r.inference_kind && r.inference_kind !== 'unknown').length,
    narrator_semantic_qa_count: kindRows('narrator_semantic_qa').length,
    narrator_environment_cognition_count: kindRows('narrator_environment_cognition').length,
    director_semantic_qa_count: kindRows('director_semantic_qa').length,
    storyteller_post_commit_count: kindRows('storyteller_post_commit_issue_pressure').length,
    librarian_mediation_count: kindRows('librarian_mediation').length,
    character_orientation_count: kindRows('character_orientation').length,
    character_semantic_evaluation_count: kindRows('character_semantic_evaluation').length,
    player_decomposition_count: kindRows('player_decomposition').length,
    plot_cognition_sync_count: kindRows('plot_cognition_init').length
      + kindRows('plot_cognition_update').length
      + kindRows('plot_cognition_epistemic_eval').length,
    character_move_count: kindRows('character_move').length,
    narrator_presentation_count: narratorPresentation.length,
    director_turn_count: kindRows('director_turn').length,
    wall_ms_total: attempts.reduce((s, r) => s + (r.wall_ms ?? 0), 0),
    input_tokens_total: attempts.reduce((s, r) => s + (r.input_tokens ?? 0), 0),
    output_tokens_total: attempts.reduce((s, r) => s + (r.output_tokens ?? 0), 0),
    reasoning_tokens_total: attempts.reduce((s, r) => s + (r.reasoning_tokens ?? 0), 0),
    retry_count: attempts.filter((r) => (r.attempt_index ?? 0) > 0).length,
    kinds: Object.entries(byKind)
      .filter(([k]) => k && k !== 'unknown')
      .map(([kind, rows]) => ({
        inference_kind: kind,
        count: rows.length,
        wall_ms_total: rows.reduce((s, r) => s + (r.wall_ms ?? 0), 0),
        reasoning_tokens_total: rows.reduce((s, r) => s + (r.reasoning_tokens ?? 0), 0),
      })),
  };
}

export function prohibitedCognitionProof(inference, architectureArm, { scope = 'session' } = {}) {
  if (architectureArm === 'lean_a4_ablated') {
    return {
      architecture_arm: architectureArm,
      scope,
      narrator_semantic_qa_absent: inference.narrator_semantic_qa_count === 0,
      director_semantic_qa_absent: inference.director_semantic_qa_count === 0,
      storyteller_post_commit_absent: inference.storyteller_post_commit_count === 0,
      pass: inference.narrator_semantic_qa_count === 0
        && inference.director_semantic_qa_count === 0
        && inference.storyteller_post_commit_count === 0,
    };
  }
  const map = {
    storyteller_orientation: inference.character_orientation_count,
    storyteller_assessment: 0,
    storyteller_post_commit_issue_pressure: inference.storyteller_post_commit_count,
    director_semantic_qa: inference.director_semantic_qa_count,
    narrator_semantic_qa: inference.narrator_semantic_qa_count,
    narrator_environment_cognition: inference.narrator_environment_cognition_count,
    character_orientation: inference.character_orientation_count,
    librarian_mediation: inference.librarian_mediation_count,
    plot_cognition_epistemic_eval: inference.plot_cognition_sync_count ?? 0,
    character_semantic_evaluation: inference.character_semantic_evaluation_count,
    player_decomposition: inference.player_decomposition_count,
  };
  const violations = A2_PROHIBITED_KINDS.filter((kind) => (map[kind] ?? 0) > 0);
  return {
    architecture_arm: architectureArm,
    scope,
    violations,
    pass: violations.length === 0,
  };
}

export function ingressPvrObservations(allAttempts, playerDecomposition) {
  const ingressKinds = ['player_visibility_triage', 'player_uniform_eligibility_verification', 'player_decomposition', 'opening_segmentation'];
  const ingress = allAttempts.filter((row) => ingressKinds.includes(row.inference_kind));
  const uniformEligible = playerDecomposition?.uniform_projection_eligible === true;
  const decompositionRan = ingress.some((row) => row.inference_kind === 'player_decomposition');
  return {
    uniform_projection_eligible: uniformEligible,
    player_decomposition_in_ingress: decompositionRan,
    uniform_path_violation: uniformEligible && decompositionRan,
    ingress_inference_kinds: ingress.map((row) => row.inference_kind),
  };
}

export function buildBlindPacket({ runs, outputsDir, purpose, scenarioBriefing, playerStimulus }) {
  const samples = runs.map((run) => ({
    blind_label: null,
    case_id: run.case_id,
    architecture_arm: run.architecture_arm,
    presentation_text: run.presentation_text,
  }));
  for (let i = samples.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [samples[i], samples[j]] = [samples[j], samples[i]];
  }
  samples.forEach((s, i) => {
    s.blind_label = String.fromCharCode(65 + i);
  });
  const packetPath = path.join(outputsDir, 'issue201-g3b-f1-blind-eval-packet.json');
  const keyPath = path.join(outputsDir, 'issue201-g3b-f1-blind-eval-answer-key.json');
  const transportPath = path.join(outputsDir, 'issue201-g3b-f1-blind-eval-transport.md');
  const packet = {
    schema: 'issue201_blind_eval_packet_v1',
    purpose,
    rubric: {
      primary: 'issue201-stage2-human-evaluator-worksheet.md (11 dimensions, 1-5 each)',
      adjunct_dimensions: ['environmental_grounding', 'overall_rp_usefulness'],
    },
    scenario_briefing: scenarioBriefing,
    player_stimulus: playerStimulus,
    instructions: 'Score presentation_text only. Do not request architecture, latency, usage metadata, or experimental metadata.',
    samples: samples.map(({ blind_label, presentation_text }) => ({
      blind_label,
      presentation_text,
    })),
  };
  const answerKey = samples.map(({ blind_label, case_id, architecture_arm }) => ({
    blind_label, case_id, architecture_arm,
  }));
  fs.writeFileSync(packetPath, `${JSON.stringify(packet, null, 2)}\n`);
  fs.writeFileSync(keyPath, `${JSON.stringify(answerKey, null, 2)}\n`);
  const forbidden = ['a2', 'a4', 'lean', 'ablated', 'control', 'inference', 'wall_ms', 'semantic_qa', 'hg-session'];
  const leaked = forbidden.filter((f) => JSON.stringify(packet).toLowerCase().includes(f));
  fs.writeFileSync(transportPath, `# Issue #201 G3-B F1 Blind Transport

**Packet:** \`${packetPath}\`  
**Answer key:** \`${keyPath}\` — concealed until Governance locks scores

Use \`governance/records/issue201-stage2-human-evaluator-worksheet.md\`.
`, 'utf8');
  return {
    packetPath,
    keyPath,
    transportPath,
    sample_count: samples.length,
    blinding_integrity: { pass: leaked.length === 0, leaked_forbidden_substrings: leaked },
  };
}
