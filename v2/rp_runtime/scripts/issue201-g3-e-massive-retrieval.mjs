#!/usr/bin/env node
/**
 * Issue #201 G3-E — massive-knowledge experimental apparatus harness.
 * --validate-apparatus: deterministic/mock smoke only (no live 14/28 campaign).
 */
import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { deriveObligationSignals } from '../src/lib/a2-obligation-dispatch.mjs';
import { runA2IndexedRetrievalStep } from '../src/lib/a2-indexed-retrieval.mjs';
import { G3_SCENARIOS } from './lib/issue201-g3-scenarios.mjs';
import { LEAN_A4_ROUND_OPTIONS } from './lib/issue201-g3-b-lib.mjs';
import {
  G3E_ARMS,
  REPO_ROOT,
  runValidateApparatus,
  buildTopologyWiringEvidence,
} from './lib/issue201-g3e-lib.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function gitSha() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  } catch {
    return 'unknown';
  }
}

function parseArgs(argv) {
  const args = { validateApparatus: false, outputDir: null };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--validate-apparatus') args.validateApparatus = true;
    if (argv[i] === '--output-dir' && argv[i + 1]) {
      args.outputDir = argv[i + 1];
      i += 1;
    }
  }
  return args;
}

function defaultOutputDir() {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  return path.join(REPO_ROOT, 'data/investigation_runs', `issue201-g3e-apparatus-${stamp}`);
}

function buildHarnessManifest() {
  const scenario = G3_SCENARIOS.ayame_archive_interview;
  const a2Indexed = runA2IndexedRetrievalStep({ caseId: 'K3', viewerCharacterId: 'ayame' });
  const topology = buildTopologyWiringEvidence();
  const dispatch = deriveObligationSignals({
    scenarioKey: scenario.scenario_key,
    eligibleActors: ['ayame'],
    roleAssignments: scenario.roleAssignments,
    uniformProjectionEligible: true,
    retrievalManifestGap: true,
  });
  return {
    schema: 'issue201_g3e_harness_manifest_v1',
    proposal_sha: 'a438635',
    implementation_base_sha: gitSha(),
    arms: {
      [G3E_ARMS.A2_INDEXED]: {
        enableIndexedRetrieval: true,
        retrievalManifestGap: true,
        skipPostCommitPlot: true,
        librarian_invocation_expected: 0,
        sample_k3_indexed_retrieval: a2Indexed,
        obligation_dispatch: dispatch,
      },
      [G3E_ARMS.LEAN_A4]: {
        round_options: { ...LEAN_A4_ROUND_OPTIONS, skipPostCommitPlot: true },
        plot_absent: true,
      },
    },
    scenario: {
      id: scenario.id,
      scenario_key: scenario.scenario_key,
    },
    topology,
    live_campaign_authorized: false,
    live_campaign_executed: false,
  };
}

async function main() {
  const args = parseArgs(process.argv);
  const outputDir = path.resolve(args.outputDir ?? defaultOutputDir());
  fs.mkdirSync(outputDir, { recursive: true });

  const manifest = buildHarnessManifest();
  fs.writeFileSync(path.join(outputDir, 'harness-manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);

  if (!args.validateApparatus) {
    console.error('G3-E live comparison campaign is NOT authorized. Use --validate-apparatus.');
    process.exit(2);
  }

  const validation = runValidateApparatus({ outputDir });
  const report = {
    schema: 'issue201_g3e_apparatus_run_v1',
    output_dir: outputDir,
    harness_manifest: manifest,
    validation,
    readiness_for_live_execution: validation.corpus.truth_manifest_valid
      && validation.k3.all_production_stages_pass
      && validation.blind_packet_integrity.labels_stripped
      && validation.live_campaign_executed === false,
  };
  fs.writeFileSync(path.join(outputDir, 'apparatus-run-report.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({
    output_dir: outputDir,
    record_count: validation.corpus.record_count,
    k3_production_stages_pass: validation.k3.all_production_stages_pass,
    readiness_for_live_execution: report.readiness_for_live_execution,
  }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
