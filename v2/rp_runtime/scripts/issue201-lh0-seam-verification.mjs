#!/usr/bin/env node
/**
 * Issue #201 LH-0 — mechanical seam verification apparatus.
 * --validate-apparatus: deterministic validation only (no live micro-runs).
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  REPO_ROOT,
  runValidateApparatus,
  buildLh0ExecutionProtocol,
  gitSha,
} from './lib/issue201-lh0-lib.mjs';
import { executeLh0LiveCampaign, verifyCandidateDrift } from './lib/issue201-lh0-live-lib.mjs';
import { runLh0RemediationValidationSuite } from './lib/issue201-lh0-remediation-lib.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const args = { validateApparatus: false, validateRemediation: false, executeLive: false, outputDir: null };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--validate-apparatus') args.validateApparatus = true;
    if (argv[i] === '--validate-remediation') args.validateRemediation = true;
    if (argv[i] === '--execute-live') args.executeLive = true;
    if (argv[i] === '--output-dir' && argv[i + 1]) {
      args.outputDir = argv[i + 1];
      i += 1;
    }
  }
  return args;
}

function defaultOutputDir(prefix = 'issue201-lh0-apparatus') {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  return path.join(REPO_ROOT, 'data/investigation_runs', `${prefix}-${stamp}`);
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.validateApparatus && !args.validateRemediation && !args.executeLive) {
    console.error('Usage: node issue201-lh0-seam-verification.mjs (--validate-apparatus | --validate-remediation | --execute-live) [--output-dir PATH]');
    process.exit(1);
  }

  if (args.validateRemediation) {
    const remediation = runLh0RemediationValidationSuite();
    console.log(JSON.stringify(remediation, null, 2));
    process.exit(remediation.readiness_for_corrective_live_execution ? 0 : 1);
  }

  const outputDir = args.outputDir ?? defaultOutputDir(
    args.executeLive ? 'issue201-lh0-live' : 'issue201-lh0-apparatus',
  );

  if (args.executeLive) {
    const drift = verifyCandidateDrift('a96886b');
    if (!drift.apparatus_files_present) {
      console.error(JSON.stringify({ error: 'LH-0 apparatus files missing', drift }, null, 2));
      process.exit(2);
    }
    const remediation = runLh0RemediationValidationSuite();
    if (!remediation.readiness_for_corrective_live_execution) {
      console.error(JSON.stringify({ error: 'LH-0 remediation validation failed', remediation }, null, 2));
      process.exit(3);
    }
    const report = await executeLh0LiveCampaign({ outputDir });
    console.log(JSON.stringify({
      schema: 'issue201_lh0_live_run_v1',
      output_dir: outputDir,
      candidate_sha: gitSha(),
      lh1a_readiness: report.lh1a_readiness,
      pass_fail_matrix: report.pass_fail_matrix,
    }, null, 2));
    process.exit(0);
  }

  const report = runValidateApparatus({ outputDir });
  const protocol = buildLh0ExecutionProtocol();
  fs.writeFileSync(
    path.join(outputDir, 'issue201-lh0-execution-protocol.json'),
    `${JSON.stringify(protocol, null, 2)}\n`,
  );

  const summary = {
    schema: 'issue201_lh0_apparatus_run_v1',
    implementation_base_sha: gitSha(),
    activation_commit: '741e1ce',
    output_dir: outputDir,
    readiness_for_lh0_micro_execution: report.readiness_for_lh0_micro_execution,
    live_micro_runs_executed: false,
    deterministic_checks_pass: report.deterministic_validation.all_pass,
  };
  fs.writeFileSync(
    path.join(outputDir, 'issue201-lh0-apparatus-run.json'),
    `${JSON.stringify(summary, null, 2)}\n`,
  );

  console.log(JSON.stringify(summary, null, 2));
  process.exit(report.readiness_for_lh0_micro_execution ? 0 : 1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
