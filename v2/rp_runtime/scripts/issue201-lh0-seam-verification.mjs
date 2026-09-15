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

const __dirname = path.dirname(fileURLToPath(import.meta.url));

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
  return path.join(REPO_ROOT, 'data/investigation_runs', `issue201-lh0-apparatus-${stamp}`);
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.validateApparatus) {
    console.error('Usage: node issue201-lh0-seam-verification.mjs --validate-apparatus [--output-dir PATH]');
    process.exit(1);
  }

  const outputDir = args.outputDir ?? defaultOutputDir();
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
