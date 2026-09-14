/**
 * Issue #199 supplemental validation — bounded live semantic evaluator checks.
 * Run from v2/rp_runtime: node scripts/issue199-supplemental-semantic-validation.mjs
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { modelProfileForInferenceKind, resolveApplicationRoleProfiles } from '../src/application/application-settings.mjs';
import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { resolveGitProvenance } from '../src/lib/git-provenance.mjs';
import { HG_DEEPSEEK_DEFAULT_MODEL } from '../src/lib/inference-profile.mjs';
import { runSemanticEvaluation, parseSemanticEvaluationResult } from '../src/plugins/hg-phase-executors/character-semantic-evaluation.mjs';
import { startDomainApi } from '../tests/helpers/domain-api.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

const F06_OPENING =
  'Kizzie glanced up, double-checking the house number and then steeled herself before knocking.';

const STRAIN_CANDIDATE = {
  move_schema_version: 2,
  beats: [
    {
      type: 'action',
      action:
        'Her gaze moves over Kizzie from shoes to face, lingering without hurry, cataloguing posture, clothing, and the faint tells of recent strain.',
    },
  ],
  motivation: {
    goal: 'evaluate applicant composure',
    tactic: 'controlled scrutiny',
    emotional_driver: 'predatory calm',
    risk_level: 'medium',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const TREMBLING_INTERPRETATION_CANDIDATE = {
  move_schema_version: 2,
  beats: [
    {
      type: 'action',
      action:
        'Ayame notices the trembling in Kizzie\'s hands and reads it as nerves rather than cold.',
    },
  ],
  motivation: {
    goal: 'assess composure',
    tactic: 'observe bodily cues',
    emotional_driver: 'curiosity',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const DECOMPOSITIONS = JSON.parse(
  fs.readFileSync(
    path.join(REPO_ROOT, 'governance', 'records', 'issue-199-supplemental-decompositions.json'),
    'utf8',
  ),
);

function summarizeEvaluatorAttempt(evidenceRoot, sessionId, inferenceId) {
  const indexPath = path.join(evidenceRoot, sessionId, 'index.json');
  if (!fs.existsSync(indexPath)) return null;
  const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
  for (const attemptId of index.attempt_ids ?? []) {
    const attempt = JSON.parse(fs.readFileSync(
      path.join(evidenceRoot, sessionId, 'attempts', `${attemptId}.json`),
      'utf8',
    ));
    if (attempt.correlation?.inference_id?.includes(inferenceId)) {
      const usage = attempt.response?.usage ?? {};
      const timing = attempt.inference_health?.timing ?? attempt.timing ?? {};
      return {
        evidence_id: attemptId,
        model: attempt.request?.model ?? attempt.response?.model ?? null,
        wall_ms: timing.inference_wall_clock_ms ?? timing.wall_ms ?? null,
        input_tokens: usage.inputTokens ?? usage.input_tokens ?? null,
        output_tokens: usage.outputTokens ?? usage.output_tokens ?? null,
        assistant_text: attempt.response?.assistant_text ?? null,
      };
    }
  }
  return null;
}

function inventorySummary(authorityRefs) {
  const master = authorityRefs.find((ref) => String(ref.ref_id ?? '').startsWith('perception_fact:authorized_inventory:'));
  const entitled = authorityRefs.filter((ref) => String(ref.ref_id ?? '').startsWith('perception_fact:entitled:'));
  return {
    master_ref_id: master?.ref_id ?? null,
    master_text: master?.text ?? null,
    entitled_count: entitled.length,
    entitled_sample: entitled.slice(0, 3).map((ref) => ({ ref_id: ref.ref_id, text: ref.text })),
  };
}

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    console.error('DEEPSEEK_API_KEY required for supplemental live semantic validation');
    process.exit(2);
  }

  const evidenceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'issue199-supplemental-'));
  const port = 30110 + Math.floor(Math.random() * 20);
  const host = await startDomainApi(port);
  const api = createDomainApiClient(host.baseUrl);
  const { phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
    requireDomainHost: true,
    inference: {
      mountDeepSeek: true,
      executionEvidence: { enabled: true, root: evidenceRoot },
      defaultProfile: resolveApplicationRoleProfiles({
        inferenceMode: 'live',
        roleRouting: 'simple',
        model: HG_DEEPSEEK_DEFAULT_MODEL,
      }).character,
    },
  });

  const baseProfile = resolveApplicationRoleProfiles({
    inferenceMode: 'live',
    roleRouting: 'simple',
    model: HG_DEEPSEEK_DEFAULT_MODEL,
  }).character;
  const semanticEvaluatorProfile = modelProfileForInferenceKind(
    baseProfile,
    'character_semantic_evaluation',
    {},
    { inferenceMode: 'live' },
  );

  const openers = await api.listTemplateOpeners('ayame_household_entry_evaluation');
  const session = await api.createSession({
    characters: ['ayame', 'kizzie'],
    scene_template_id: 'ayame_household_entry_evaluation',
    role_assignments: { ayame: 'host', kizzie: 'applicant' },
    opening: { mode: 'template', opener_id: openers[0].opener_id },
    player_character_file_id: 'kizzie',
  });
  const round = await api.startRound({ hg_scene_id: session.hg_session_id });
  const state = await api.getSceneState(session.hg_session_id);

  await api.recordUserTurn({
    hg_session_id: session.hg_session_id,
    content: F06_OPENING,
    speaker: 'Kizzie',
    player_decomposition: DECOMPOSITIONS.f06_opening,
    hg_round_id: round.hg_round_id,
  });

  const negativeEval = await runSemanticEvaluation({
    api,
    runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    characterInferenceId: 'issue199-supplemental-strain',
    characterId: 'Ayame',
    role: 'host',
    turnIndex: Number(state.turn_counter ?? 0),
    evaluationPassId: 'issue199-unsupported-strain',
    candidateMove: STRAIN_CANDIDATE,
    rawModelOutput: JSON.stringify(STRAIN_CANDIDATE),
    semanticEvaluatorProfile,
  });
  const negativeParsed = negativeEval.ok
    ? { ok: true, result: negativeEval.result }
    : parseSemanticEvaluationResult(
      negativeEval.raw ?? '',
      negativeEval.contextResponse?.authority_references ?? [],
    );
  const negativeInventory = inventorySummary(negativeEval.contextResponse?.authority_references ?? []);

  const copresentSession = await api.createSession({
    cast: ['Ayame', 'Kizzie'],
    location: 'Evaluation room',
    player_character_file_id: 'kizzie',
  });
  const copresentRound = await api.startRound({ hg_scene_id: copresentSession.hg_session_id });
  const copresentState = await api.getSceneState(copresentSession.hg_session_id);
  const trembleContent = "Kizzie's hands trembled visibly as she waited.";
  await api.recordUserTurn({
    hg_session_id: copresentSession.hg_session_id,
    content: trembleContent,
    speaker: 'Kizzie',
    player_decomposition: DECOMPOSITIONS.trembling,
    hg_round_id: copresentRound.hg_round_id,
  });

  const positiveEval = await runSemanticEvaluation({
    api,
    runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
    hgSessionId: copresentSession.hg_session_id,
    hgSceneId: copresentSession.hg_session_id,
    hgRoundId: copresentRound.hg_round_id,
    characterInferenceId: 'issue199-supplemental-tremble',
    characterId: 'Ayame',
    role: 'host',
    turnIndex: Number(copresentState.turn_counter ?? 0),
    evaluationPassId: 'issue199-legitimate-tremble',
    candidateMove: TREMBLING_INTERPRETATION_CANDIDATE,
    rawModelOutput: JSON.stringify(TREMBLING_INTERPRETATION_CANDIDATE),
    semanticEvaluatorProfile,
  });
  const positiveParsed = positiveEval.ok
    ? { ok: true, result: positiveEval.result }
    : parseSemanticEvaluationResult(
      positiveEval.raw ?? '',
      positiveEval.contextResponse?.authority_references ?? [],
    );
  const positiveInventory = inventorySummary(positiveEval.contextResponse?.authority_references ?? []);

  const provenance = resolveGitProvenance(REPO_ROOT);
  const report = {
    schema: 'issue199_supplemental_semantic_validation_v1',
    generated_at: new Date().toISOString(),
    candidate_sha: provenance.execution_head,
    provenance,
    model: HG_DEEPSEEK_DEFAULT_MODEL,
    semantic_evaluator_profile: {
      reasoningEffort: semanticEvaluatorProfile.reasoningEffort,
      maxTokens: semanticEvaluatorProfile.maxTokens,
    },
    unsupported_perception: {
      session_id: session.hg_session_id,
      opening: F06_OPENING,
      inventory: negativeInventory,
      parsed: negativeParsed,
      evaluator_attempt: summarizeEvaluatorAttempt(
        evidenceRoot,
        session.hg_session_id,
        'issue199-supplemental-strain-semantic',
      ),
      pass: negativeParsed.ok
        && (negativeParsed.result.overall_result === 'reject_hard'
          || negativeParsed.result.findings.some((f) => f.dimension === 'R02b' && f.severity === 'hard')),
    },
    legitimate_observable: {
      session_id: copresentSession.hg_session_id,
      player_content: trembleContent,
      inventory: positiveInventory,
      parsed: positiveParsed,
      evaluator_attempt: summarizeEvaluatorAttempt(
        evidenceRoot,
        copresentSession.hg_session_id,
        'issue199-supplemental-tremble-semantic',
      ),
      pass: positiveParsed.ok && ['pass', 'reject_soft'].includes(positiveParsed.result.overall_result),
    },
    evidence_root: evidenceRoot,
  };

  const outPath = path.join(
    REPO_ROOT,
    'governance',
    'records',
    'issue-199-supplemental-semantic-validation-2026-09-14.json',
  );
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({
    candidate_sha: report.candidate_sha,
    unsupported_pass: report.unsupported_perception.pass,
    legitimate_pass: report.legitimate_observable.pass,
    outPath,
  }, null, 2));

  await host.stop?.();
  if (!report.unsupported_perception.pass || !report.legitimate_observable.pass) {
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
