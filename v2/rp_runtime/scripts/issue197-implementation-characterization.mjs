/**
 * Issue #197 implementation-time bounded characterization.
 * Run from v2/rp_runtime: node scripts/issue197-implementation-characterization.mjs
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
import { runPlayerVisibilityTriagePhase } from '../src/plugins/hg-phase-executors/player-visibility-triage-phase.mjs';
import { startDomainApi } from '../tests/helpers/domain-api.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

const SCENARIOS = [
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
    id: 'f06_observable_only',
    content: 'Kizzie glanced up, double-checking the house number, and knocked.',
    expected: 'uniform_projection',
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
    id: 'pos_simple_action',
    content: 'The player sets the lantern on the table and steps back.',
    expected: 'uniform_projection',
  },
];

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
      };
    }
  }
  return null;
}

async function main() {
  const evidenceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'issue197-impl-char-'));
  const port = 29970 + Math.floor(Math.random() * 30);
  const host = await startDomainApi(port, { withSession: true, cast: ['Ayame', 'Kizzie', 'Harley'] });
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
  const sessionId = `issue197-impl-char-${Date.now()}`;
  await api.createSession({ cast: ['Ayame', 'Kizzie'], hg_session_id: sessionId });

  const results = [];
  for (const scenario of SCENARIOS) {
    const inferenceId = `issue197-impl-${scenario.id}`;
    const result = await runPlayerVisibilityTriagePhase({
      api,
      runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
      hgSessionId: sessionId,
      hgSceneId: sessionId,
      hgRoundId: `round-${scenario.id}`,
      inferenceId,
      playerContent: scenario.content,
      modelProfile: triageProfile,
      verificationModelProfile: verificationProfile,
    });
    const triageTiming = summarizeAttempt(evidenceRoot, sessionId, inferenceId);
    const verifyTiming = result.checkerResult?.verification?.inference_id
      ? summarizeAttempt(evidenceRoot, sessionId, result.checkerResult.verification.inference_id)
      : null;
    results.push({
      ...scenario,
      route: result.route,
      checker_result: result.checkerResult,
      triage_timing: triageTiming,
      verification_timing: verifyTiming,
      classification: result.route === scenario.expected ? 'correct' : 'misroute',
    });
  }

  const provenance = resolveGitProvenance(REPO_ROOT);
  const report = {
    schema: 'issue197_implementation_characterization_v1',
    generated_at: new Date().toISOString(),
    git_sha: provenance.git_sha,
    provenance,
    results,
    summary: {
      correct: results.filter((r) => r.classification === 'correct').length,
      misroute: results.filter((r) => r.classification === 'misroute').length,
      f06_blocked: results.find((r) => r.id === 'f06_mixed')?.route === 'full_pvr',
    },
    evidence_root: evidenceRoot,
  };
  const outPath = path.join(REPO_ROOT, 'governance', 'records', 'issue-197-implementation-characterization-2026-09-14.json');
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report.summary, null, 2));
  host.close?.();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
