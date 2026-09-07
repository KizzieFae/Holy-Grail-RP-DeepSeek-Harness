/**
 * Issue #136 G4 — full bounded Tier-2 semantic validation campaign.
 * Runs approved fixture matrix + sentinel via runIssue136Tier2Campaign.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  deriveIssue136SafetyGuard,
  proveProductionInferenceUnchanged,
  runIssue136Tier2Campaign,
  ISSUE136_IMPLEMENTATION_SHA,
  ISSUE136_REPETITIONS,
} from '../src/scenario-harness/issue136-tier2-campaign.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    throw new Error('DEEPSEEK_API_KEY not set');
  }

  const executionSha = process.env.ISSUE136_EXECUTION_SHA ?? null;
  const guard = deriveIssue136SafetyGuard();
  const productionProof = proveProductionInferenceUnchanged();

  const report = await runIssue136Tier2Campaign({ mode: 'live' });

  const envelope = {
    schema: 'issue136_g4_campaign_report_v1',
    gate: 'G4',
    execution_sha: executionSha,
    candidate_sha: ISSUE136_IMPLEMENTATION_SHA,
    g3_pre_campaign_slice: {
      separate_from_campaign_tooling: true,
      prior_g3_evidence: 'data/issue136_g2_g3_gates/2026-09-07T03-34-38-127Z/',
      prior_g3_fixture: '136-T2-A-STABILITY',
      prior_g3_repetition: 1,
      prior_g3_classification: 'PASS',
      counts_toward_a_in_campaign_runner: false,
      total_a_evidence_runs: '1 (G3) + 3 (campaign) = 4',
    },
    approved_matrix: ISSUE136_REPETITIONS,
    campaign_runs_in_matrix: 15,
    sentinel_included: true,
    safety_guard_recorded: guard,
    production_inference_proof: productionProof,
    production_composition_note: productionProof.unchanged
      ? 'no diff vs tooling anchor'
      : 'authorized composition diff (Storyteller transport exports + Character/Director transport-only)',
    ...report,
  };

  const outDir = report.campaign_data_dir;
  const outPath = path.join(outDir, 'g4-campaign-report.json');
  fs.writeFileSync(outPath, `${JSON.stringify(envelope, null, 2)}\n`, 'utf8');
  process.stdout.write(`${JSON.stringify({
    report_path: outPath,
    campaign_data_dir: outDir,
    runs: report.runs.length,
    limits: report.limits,
    campaign_state: report.campaign_state,
    production_unchanged: productionProof.unchanged,
  }, null, 2)}\n`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
