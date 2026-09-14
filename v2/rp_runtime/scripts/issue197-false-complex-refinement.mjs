/**
 * Issue #197 false-complex refinement characterization.
 * Run from v2/rp_runtime:
 *   node scripts/issue197-false-complex-refinement.mjs --phase pre
 *   node scripts/issue197-false-complex-refinement.mjs --phase post
 */
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { modelProfileForInferenceKind, resolveApplicationRoleProfiles } from '../src/application/application-settings.mjs';
import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { resolveGitProvenance } from '../src/lib/git-provenance.mjs';
import { HG_DEEPSEEK_DEFAULT_MODEL } from '../src/lib/inference-profile.mjs';
import { runPlayerVisibilityTriagePhase } from '../src/plugins/hg-phase-executors/player-visibility-triage-phase.mjs';
import { startDomainApi } from '../tests/helpers/domain-api.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');
const CAST = ['Ayame', 'Kizzie', 'Harley', 'Celina'];
const POSITIVE_REPEAT = 3;
const NEGATIVE_REPEAT = 1;

const NEGATIVE_CONTROLS = [
  {
    id: 'f06_mixed',
    content: 'Kizzie glanced up, double-checking the house number and then steeled herself before knocking.',
    expected: 'full_pvr',
  },
  {
    id: 'f06_paraphrase',
    content: 'Kizzie checked the address by the door, quietly braced herself, and knocked.',
    expected: 'full_pvr',
  },
  {
    id: 'neg_internal',
    content: 'The player wonders whether anyone here can be trusted, but says nothing.',
    expected: 'full_pvr',
  },
  {
    id: 'neg_concealed',
    content: 'The player smiles at Harley while slipping a folded note into their sleeve unseen.',
    expected: 'full_pvr',
  },
  {
    id: 'neg_directed_speech',
    content: 'The player leans toward Ayame and whispers, "Meet me after dark."',
    expected: 'full_pvr',
  },
];

function loadPositiveCorpus() {
  const script = `
import json
from player_visibility_triage_corpus import build_issue_121_checker_corpus
print(json.dumps([
  {"case_id": c.case_id, "content": c.content, "expected_route": c.expected_route}
  for c in build_issue_121_checker_corpus()
  if c.category == "uniform_safe_positive"
]))
`;
  const result = spawnSync('python', ['-c', script], {
    cwd: path.join(REPO_ROOT, 'v2', 'domain', 'modules'),
    encoding: 'utf8',
  });
  if (result.status !== 0) {
    throw new Error(result.stderr || 'failed to load positive corpus');
  }
  return JSON.parse(result.stdout.trim());
}

function summarizeAttempt(evidenceRoot, sessionId, inferenceId) {
  const indexPath = path.join(evidenceRoot, sessionId, 'index.json');
  if (!fs.existsSync(indexPath)) return null;
  const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
  for (const attemptId of index.attempt_ids ?? []) {
    const attempt = JSON.parse(fs.readFileSync(
      path.join(evidenceRoot, sessionId, 'attempts', `${attemptId}.json`),
      'utf8',
    ));
    if (attempt.correlation?.inference_id === inferenceId) {
      const usage = attempt.response?.usage ?? {};
      const timing = attempt.inference_health?.timing ?? attempt.timing ?? {};
      return {
        wall_ms: timing.inference_wall_clock_ms ?? timing.wall_ms ?? null,
        input_tokens: usage.inputTokens ?? usage.input_tokens ?? null,
        output_tokens: usage.outputTokens ?? usage.output_tokens ?? null,
        raw: attempt.response?.assistant_text ?? null,
      };
    }
  }
  return null;
}

function parsePhase(argv) {
  const index = argv.indexOf('--phase');
  if (index === -1 || !argv[index + 1]) {
    throw new Error('usage: node scripts/issue197-false-complex-refinement.mjs --phase pre|post');
  }
  return argv[index + 1];
}

async function runCase({
  api,
  phaseExecutors,
  evidenceRoot,
  sessionId,
  caseId,
  content,
  expected,
  runIndex,
  triageProfile,
  verificationProfile,
}) {
  const inferenceId = `issue197-fc-${caseId}-r${runIndex}`;
  const result = await runPlayerVisibilityTriagePhase({
    api,
    runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
    hgSessionId: sessionId,
    hgSceneId: sessionId,
    hgRoundId: `round-${caseId}-${runIndex}`,
    inferenceId,
    playerContent: content,
    modelProfile: triageProfile,
    verificationModelProfile: verificationProfile,
  });
  const triageEvidence = summarizeAttempt(evidenceRoot, sessionId, inferenceId);
  const verifyInferenceId = result.checkerResult?.verification?.inference_id ?? null;
  const verifyEvidence = verifyInferenceId
    ? summarizeAttempt(evidenceRoot, sessionId, verifyInferenceId)
    : null;
  const triageAffirmative = result.checkerResult?.uniform_projection_safe === true
    || result.checkerResult?.triage_affirmative === true
    || (triageEvidence?.raw?.includes('"uniform_projection_safe": true') ?? false);
  return {
    case_id: caseId,
    run_index: runIndex,
    content,
    expected_route: expected,
    triage_affirmative: triageAffirmative,
    triage_raw: triageEvidence?.raw ?? null,
    triage_reason: result.checkerResult?.reason ?? null,
    verifier_invoked: Boolean(verifyInferenceId),
    verifier_raw: verifyEvidence?.raw ?? null,
    verifier_disposition: result.checkerResult?.verification?.disposition ?? null,
    verifier_reason: result.checkerResult?.verification?.reason ?? null,
    verifier_audit_note: result.checkerResult?.verification?.audit_note ?? null,
    final_route: result.route,
    classification: result.route === expected ? 'correct' : (expected === 'uniform_projection' ? 'false_complex' : 'false_simple'),
    triage_timing: triageEvidence ? {
      wall_ms: triageEvidence.wall_ms,
      input_tokens: triageEvidence.input_tokens,
      output_tokens: triageEvidence.output_tokens,
    } : null,
    verification_timing: verifyEvidence ? {
      wall_ms: verifyEvidence.wall_ms,
      input_tokens: verifyEvidence.input_tokens,
      output_tokens: verifyEvidence.output_tokens,
    } : null,
  };
}

function aggregateByCase(runs) {
  const grouped = new Map();
  for (const run of runs) {
    const bucket = grouped.get(run.case_id) ?? [];
    bucket.push(run);
    grouped.set(run.case_id, bucket);
  }
  return [...grouped.entries()].map(([caseId, caseRuns]) => {
    const affirmative = caseRuns.filter((r) => r.triage_affirmative).length;
    const clearGivenAffirmative = caseRuns.filter(
      (r) => r.triage_affirmative && r.verifier_disposition === 'clear',
    ).length;
    const uniform = caseRuns.filter((r) => r.final_route === 'uniform_projection').length;
    return {
      case_id: caseId,
      runs: caseRuns.length,
      triage_affirmative_rate: affirmative / caseRuns.length,
      verifier_clear_rate_given_affirmative: affirmative ? clearGivenAffirmative / affirmative : null,
      final_uniform_rate: uniform / caseRuns.length,
      disqualification_reasons: [...new Set(caseRuns
        .filter((r) => r.verifier_disposition === 'disqualified')
        .map((r) => r.verifier_reason)
        .filter(Boolean))],
    };
  });
}

async function main() {
  const phase = parsePhase(process.argv);
  const evidenceRoot = fs.mkdtempSync(path.join(os.tmpdir(), `issue197-fc-${phase}-`));
  const port = 29990 + Math.floor(Math.random() * 10);
  const host = await startDomainApi(port, { withSession: true, cast: CAST });
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
  const triageProfile = modelProfileForInferenceKind(baseProfile, 'player_visibility_triage', {}, { inferenceMode: 'live' });
  const verificationProfile = modelProfileForInferenceKind(
    baseProfile,
    'player_uniform_eligibility_verification',
    {},
    { inferenceMode: 'live' },
  );
  const sessionId = `issue197-fc-${phase}-${Date.now()}`;
  await api.createSession({ cast: CAST, hg_session_id: sessionId });

  const positives = loadPositiveCorpus();
  const positiveRuns = [];
  for (const caseItem of positives) {
    for (let runIndex = 1; runIndex <= POSITIVE_REPEAT; runIndex += 1) {
      positiveRuns.push(await runCase({
        api,
        phaseExecutors,
        evidenceRoot,
        sessionId,
        caseId: caseItem.case_id,
        content: caseItem.content,
        expected: caseItem.expected_route,
        runIndex,
        triageProfile,
        verificationProfile,
      }));
    }
  }

  const negativeRuns = [];
  if (phase === 'post') {
    for (const control of NEGATIVE_CONTROLS) {
      for (let runIndex = 1; runIndex <= NEGATIVE_REPEAT; runIndex += 1) {
        negativeRuns.push(await runCase({
          api,
          phaseExecutors,
          evidenceRoot,
          sessionId,
          caseId: control.id,
          content: control.content,
          expected: control.expected,
          runIndex,
          triageProfile,
          verificationProfile,
        }));
      }
    }
  }

  const provenance = resolveGitProvenance(REPO_ROOT);
  const report = {
    schema: 'issue197_false_complex_refinement_v1',
    phase,
    generated_at: new Date().toISOString(),
    candidate_sha: provenance.execution_head,
    provenance,
    design: {
      positive_repeat: POSITIVE_REPEAT,
      negative_repeat: NEGATIVE_REPEAT,
      design_record: 'governance/records/issue-197-false-complex-refinement-design-2026-09-14.md',
    },
    positive_runs,
    positive_aggregates: aggregateByCase(positiveRuns),
    negative_runs,
    summary: {
      positive_total_runs: positiveRuns.length,
      positive_uniform_runs: positiveRuns.filter((r) => r.final_route === 'uniform_projection').length,
      positive_false_complex_runs: positiveRuns.filter((r) => r.classification === 'false_complex').length,
      negative_false_simple_runs: negativeRuns.filter((r) => r.classification === 'false_simple').length,
    },
    evidence_root: evidenceRoot,
  };
  const outName = phase === 'pre'
    ? 'issue-197-false-complex-refinement-pre-2026-09-14.json'
    : 'issue-197-false-complex-refinement-post-2026-09-14.json';
  const outPath = path.join(REPO_ROOT, 'governance', 'records', outName);
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report.summary, null, 2));
  console.log(JSON.stringify(report.positive_aggregates, null, 2));
  if (report.summary.negative_false_simple_runs > 0) {
    process.exitCode = 1;
  }
  host.close?.();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
