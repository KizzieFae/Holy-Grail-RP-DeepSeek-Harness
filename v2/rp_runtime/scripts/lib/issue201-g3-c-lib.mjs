import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

export {
  LEAN_A4_ROUND_OPTIONS,
  loadAttempts,
  filterAttemptsForRound,
  summarizeAttempts,
  prohibitedCognitionProof,
  ingressPvrObservations,
} from './issue201-g3-b-lib.mjs';

export function loadAttemptRaw(evidenceRoot, sessionId, attemptId) {
  const p = path.join(evidenceRoot, sessionId, 'attempts', `${attemptId}.json`);
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

export function extractSpatialClaimsFromAssistantText(raw) {
  if (!raw) return null;
  let stripped = String(raw).trim();
  if (stripped.startsWith('```')) {
    stripped = stripped.replace(/^```(?:json)?\s*/, '').replace(/\s*```$/, '').trim();
  }
  if (!stripped.startsWith('{')) return null;
  try {
    const payload = JSON.parse(stripped);
    if (payload?.spatial_claims) return payload.spatial_claims;
    if (payload?.presentation?.spatial_claims) return payload.presentation.spatial_claims;
  } catch {
    return null;
  }
  return null;
}

export function createSpatialClaimsResolver(evidenceRoot, sessionId) {
  const indexPath = path.join(evidenceRoot, sessionId, 'index.json');
  return async function resolveSpatialClaimsFromEvidence({ hgRoundId }) {
    if (!fs.existsSync(indexPath)) return null;
    const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
    for (const attemptId of index.attempt_ids ?? []) {
      const attempt = loadAttemptRaw(evidenceRoot, sessionId, attemptId);
      const corr = attempt?.correlation ?? {};
      if (corr.inference_kind !== 'narrator_presentation') continue;
      if (hgRoundId && corr.hg_round_id !== hgRoundId) continue;
      const raw = attempt?.response?.assistant_text ?? '';
      const claims = extractSpatialClaimsFromAssistantText(raw);
      if (claims) return claims;
    }
    return null;
  };
}

export function runSampleERegression(repoRoot) {
  const testPath = 'v2/domain/tests/test_issue_201_g3a_spatial_kernel.py';
  try {
    const out = execFileSync(
      'python',
      ['-m', 'pytest', testPath, '-q'],
      { cwd: repoRoot, encoding: 'utf8' },
    );
    return { pass: true, output: out.trim() };
  } catch (err) {
    return { pass: false, output: String(err.stdout ?? err.stderr ?? err.message) };
  }
}

export function buildBlindPacket({
  runs, outputsDir, purpose, scenarioBriefing, playerStimulus,
}) {
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
  const packetPath = path.join(outputsDir, 'issue201-g3c-f2-blind-eval-packet.json');
  const keyPath = path.join(outputsDir, 'issue201-g3c-f2-blind-eval-answer-key.json');
  const transportPath = path.join(outputsDir, 'issue201-g3c-f2-blind-eval-transport.md');
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
  fs.writeFileSync(transportPath, `# Issue #201 G3-C F2 Blind Transport\n\nPacket: \`${packetPath}\`\nKey: \`${keyPath}\` (concealed)\n`, 'utf8');
  const packetStr = JSON.stringify(packet).toLowerCase();
  const forbiddenPatterns = [
    /\ba2\b/, /\ba4\b/, /\blean.a4\b/, /\bablated\b/, /\bcontrol\b/, /\binference\b/, /wall_ms/, /\btopology\b/,
  ];
  const leaked = forbiddenPatterns
    .filter((re) => re.test(packetStr))
    .map((re) => re.source);
  return {
    packetPath, keyPath, transportPath, sample_count: samples.length,
    blinding_integrity: { pass: leaked.length === 0, leaked_forbidden_substrings: leaked },
  };
}

export const A2_F2_PROHIBITED_ROUND_KINDS = [
  'narrator_semantic_qa',
  'narrator_environment_cognition',
  'director_semantic_qa',
  'storyteller_post_commit_issue_pressure',
  'librarian_mediation',
  'character_orientation',
  'character_semantic_evaluation',
  'plot_cognition_epistemic_eval',
];

export function a2F2ProhibitedProof(roundInference) {
  const violations = A2_F2_PROHIBITED_ROUND_KINDS.filter((kind) => {
    const key = kind.replace(/plot_cognition_epistemic_eval/, 'plot_cognition_sync_count');
    const map = {
      narrator_semantic_qa: roundInference.narrator_semantic_qa_count,
      narrator_environment_cognition: roundInference.narrator_environment_cognition_count,
      director_semantic_qa: roundInference.director_semantic_qa_count,
      storyteller_post_commit_issue_pressure: roundInference.storyteller_post_commit_count,
      librarian_mediation: roundInference.librarian_mediation_count,
      character_orientation: roundInference.character_orientation_count,
      character_semantic_evaluation: roundInference.character_semantic_evaluation_count,
      plot_cognition_epistemic_eval: 0,
    };
    return (map[kind] ?? 0) > 0;
  });
  return { violations, pass: violations.length === 0 };
}
