/**
 * Live checker semantic validation for Issue #121.
 * Run from v2/rp_runtime: node scripts/issue121-checker-validation.mjs
 *
 * Options:
 *   --mock         use mock inference (deterministic corpus routing)
 *   --repeat N     repeat full corpus N times (default 3)
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { deepseekInferenceProfile, mockInferenceProfile } from '../src/lib/inference-profile.mjs';
import { modelProfileForInferenceKind } from '../src/application/application-settings.mjs';
import { runPlayerVisibilityTriagePhase } from '../src/plugins/hg-phase-executors/player-visibility-triage-phase.mjs';
import { startDomainApi } from '../tests/helpers/domain-api.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

const CAST = ['Ayame', 'Kizzie', 'Harley', 'Celina'];

function loadCorpusFromPython() {
  const script = `
import json
from player_visibility_triage_corpus import build_issue_121_checker_corpus
print(json.dumps([
  {
    "case_id": c.case_id,
    "content": c.content,
    "expected_route": c.expected_route,
    "category": c.category,
    "safety_critical": c.safety_critical,
  }
  for c in build_issue_121_checker_corpus()
]))
`;
  const result = spawnSync('python', ['-c', script], {
    cwd: path.join(REPO_ROOT, 'v2', 'domain', 'modules'),
    encoding: 'utf8',
  });
  if (result.status !== 0) {
    throw new Error(result.stderr || 'failed to load corpus from python');
  }
  return JSON.parse(result.stdout.trim());
}

function parseRepeat(argv) {
  const index = argv.indexOf('--repeat');
  if (index === -1) return 3;
  const value = Number(argv[index + 1]);
  return Number.isFinite(value) && value > 0 ? value : 3;
}

function classifyResult(caseItem, actualRoute) {
  const expected = caseItem.expected_route;
  if (expected === 'full_pvr' && actualRoute === 'uniform_projection') {
    return 'false_simple';
  }
  if (expected === 'uniform_projection' && actualRoute === 'full_pvr') {
    return 'false_complex';
  }
  if (expected === actualRoute) {
    return 'correct';
  }
  return 'unexpected';
}

function mockResponseForCase(caseItem) {
  return JSON.stringify({
    uniform_projection_safe: caseItem.expected_route === 'uniform_projection',
    reason: caseItem.expected_route === 'uniform_projection'
      ? 'affirmative_uniform_present'
      : 'requires_semantic_decomposition',
  });
}

async function main() {
  const repeat = parseRepeat(process.argv);
  const useMock = process.argv.includes('--mock');
  const corpus = loadCorpusFromPython();
  const evidenceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'issue121-checker-'));
  const reportPath = path.join(evidenceRoot, 'issue121-checker-validation-report.json');

  const port = 29910 + Math.floor(Math.random() * 100);
  const host = await startDomainApi(port, { withSession: true, cast: CAST });
  const api = createDomainApiClient(host.baseUrl);
  const baseProfile = useMock ? mockInferenceProfile() : deepseekInferenceProfile({ reasoningEffort: 'low' });
  const modelProfile = modelProfileForInferenceKind(baseProfile, 'player_visibility_triage');
  const { ctx, phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
    requireDomainHost: true,
    inference: useMock
      ? { defaultProfile: mockInferenceProfile() }
      : {
        mountDeepSeek: true,
        executionEvidence: { enabled: true, root: evidenceRoot },
        defaultProfile: deepseekInferenceProfile({ reasoningEffort: 'low' }),
      },
  });
  const noopTrace = { emit: () => {} };
  const sceneAgent = { session: { append: () => {} } };

  const runs = [];
  try {
    for (let runIndex = 0; runIndex < repeat; runIndex += 1) {
      for (const caseItem of corpus) {
        const session = await api.createSession({
          cast: CAST,
          hg_session_id: `issue121-checker-${caseItem.case_id}-run${runIndex + 1}`,
        });
        const hgSessionId = session.hg_session_id;
        const inferenceId = `issue121-${caseItem.case_id}-run${runIndex + 1}`;
        const triage = await runPlayerVisibilityTriagePhase({
          runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
          trace: noopTrace,
          api,
          sceneAgent,
          hgSessionId,
          hgSceneId: hgSessionId,
          hgRoundId: `run-${runIndex + 1}`,
          inferenceId,
          playerContent: caseItem.content,
          modelProfile,
          mockResponses: useMock ? [mockResponseForCase(caseItem)] : undefined,
        });
        const classification = classifyResult(caseItem, triage.route);
        runs.push({
          run_index: runIndex + 1,
          case_id: caseItem.case_id,
          category: caseItem.category,
          safety_critical: caseItem.safety_critical,
          expected_route: caseItem.expected_route,
          actual_route: triage.route,
          classification,
          checker_result: triage.checkerResult,
          present_characters: CAST,
        });
      }
    }
  } finally {
    await ctx.fiber.dispose();
    await host.stop();
  }

  const falseSimple = runs.filter((row) => row.classification === 'false_simple');
  const falseComplex = runs.filter((row) => row.classification === 'false_complex');
  const safetyCriticalRuns = runs.filter((row) => row.safety_critical);
  const safetyFalseSimple = safetyCriticalRuns.filter((row) => row.classification === 'false_simple');

  const report = {
    generated_at: new Date().toISOString(),
    repeat,
    mock: useMock,
    corpus_size: corpus.length,
    total_runs: runs.length,
    false_simple_count: falseSimple.length,
    false_complex_count: falseComplex.length,
    safety_critical_false_simple_count: safetyFalseSimple.length,
    false_simple: falseSimple,
    false_complex: falseComplex,
    runs,
    evidence_root: evidenceRoot,
  };
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

  console.log(`Report: ${reportPath}`);
  console.log(`False-simple: ${falseSimple.length}`);
  console.log(`False-complex: ${falseComplex.length}`);
  console.log(`Safety-critical false-simple: ${safetyFalseSimple.length}`);

  if (falseSimple.length > 0) {
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
