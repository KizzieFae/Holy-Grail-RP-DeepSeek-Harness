#!/usr/bin/env node
/**
 * Issue #201 G3-E — massive-knowledge experimental harness.
 * --validate-apparatus: deterministic/mock smoke only.
 * --execute-live: authorized 28-run live campaign (pre-decode; no answer-key decode).
 */
import { execFileSync } from 'node:child_process';
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
import { executeLiveCampaign, gitSha } from './lib/issue201-g3e-live-lib.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const args = { validateApparatus: false, executeLive: false, outputDir: null, executionSeed: null };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--validate-apparatus') args.validateApparatus = true;
    if (argv[i] === '--execute-live') args.executeLive = true;
    if (argv[i] === '--output-dir' && argv[i + 1]) {
      args.outputDir = argv[i + 1];
      i += 1;
    }
    if (argv[i] === '--execution-seed' && argv[i + 1]) {
      args.executionSeed = argv[i + 1];
      i += 1;
    }
  }
  return args;
}

function defaultOutputDir(prefix) {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  return path.join(REPO_ROOT, 'data/investigation_runs', `${prefix}-${stamp}`);
}

function buildHarnessManifest({ liveAuthorized }) {
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
    apparatus_sha: 'eff2021',
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
    live_campaign_authorized: liveAuthorized,
    live_campaign_executed: false,
  };
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.validateApparatus && !args.executeLive) {
    console.error('Specify --validate-apparatus or --execute-live');
    process.exit(2);
  }
  if (args.validateApparatus && args.executeLive) {
    console.error('Choose only one mode per invocation');
    process.exit(2);
  }

  const prefix = args.executeLive ? 'issue201-g3e-live' : 'issue201-g3e-apparatus';
  const outputDir = path.resolve(args.outputDir ?? defaultOutputDir(prefix));
  fs.mkdirSync(outputDir, { recursive: true });

  const manifest = buildHarnessManifest({ liveAuthorized: args.executeLive });
  fs.writeFileSync(path.join(outputDir, 'harness-manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);

  if (args.validateApparatus) {
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
    return;
  }

  const report = await executeLiveCampaign({
    outputDir,
    executionSeed: args.executionSeed ?? 'issue201-g3e-live-eff2021',
  });
  manifest.live_campaign_executed = true;
  fs.writeFileSync(path.join(outputDir, 'harness-manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(JSON.stringify({
    output_dir: outputDir,
    completed_runs: report.completed_runs,
    scored_runs: report.scored_runs,
    blind_packet: report.blind_eval.packet_path,
    blind_packet_sha256: report.blind_eval.packet_sha256,
    answer_key_path: report.blind_eval.answer_key_path,
    decode_executed: false,
  }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
