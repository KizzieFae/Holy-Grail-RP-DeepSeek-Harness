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
import {
  executeLh0FinalQualificationCampaign,
  executeLh0LiveCampaign,
  executeLh0TurnAlignedVerificationCampaign,
  executeLh0ConsumerValueVerificationCampaign,
  verifyCandidateDrift,
} from './lib/issue201-lh0-live-lib.mjs';
import { runLh0RemediationValidationSuite } from './lib/issue201-lh0-remediation-lib.mjs';
import { runLh0SemanticValidationSuite } from './lib/issue201-lh0-semantic-validation-lib.mjs';
import { runLh0TimingValidationSuite } from './lib/issue201-lh0-timing-validation-lib.mjs';
import { runLh0ConsumerValueValidationSuite } from './lib/issue201-lh0-consumer-value-validation-lib.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const args = {
    validateApparatus: false,
    validateRemediation: false,
    validateSemantic: false,
    validateTiming: false,
    executeLive: false,
    executeFinalQualification: false,
    executeTurnAlignedVerification: false,
    executeConsumerValueVerification: false,
    validateConsumerValue: false,
    outputDir: null,
  };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--validate-apparatus') args.validateApparatus = true;
    if (argv[i] === '--validate-remediation') args.validateRemediation = true;
    if (argv[i] === '--validate-semantic') args.validateSemantic = true;
    if (argv[i] === '--validate-timing') args.validateTiming = true;
    if (argv[i] === '--validate-consumer-value') args.validateConsumerValue = true;
    if (argv[i] === '--execute-live') args.executeLive = true;
    if (argv[i] === '--execute-final-qualification') args.executeFinalQualification = true;
    if (argv[i] === '--execute-turn-aligned-verification') args.executeTurnAlignedVerification = true;
    if (argv[i] === '--execute-consumer-value-verification') args.executeConsumerValueVerification = true;
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
  if (!args.validateApparatus && !args.validateRemediation && !args.validateSemantic
    && !args.validateTiming && !args.validateConsumerValue && !args.executeLive
    && !args.executeFinalQualification && !args.executeTurnAlignedVerification
    && !args.executeConsumerValueVerification) {
    console.error('Usage: node issue201-lh0-seam-verification.mjs (--validate-apparatus | --validate-remediation | --validate-semantic | --validate-timing | --validate-consumer-value | --execute-live | --execute-final-qualification | --execute-turn-aligned-verification | --execute-consumer-value-verification) [--output-dir PATH]');
    process.exit(1);
  }

  if (args.validateConsumerValue) {
    const consumerValue = runLh0ConsumerValueValidationSuite();
    console.log(JSON.stringify(consumerValue, null, 2));
    process.exit(consumerValue.readiness_for_consumer_value_qualification ? 0 : 1);
  }

  if (args.validateTiming) {
    const timing = runLh0TimingValidationSuite();
    console.log(JSON.stringify(timing, null, 2));
    process.exit(timing.readiness_for_turn_aligned_qualification ? 0 : 1);
  }

  if (args.validateSemantic) {
    const semantic = runLh0SemanticValidationSuite();
    console.log(JSON.stringify(semantic, null, 2));
    process.exit(semantic.readiness_for_final_qualification ? 0 : 1);
  }

  if (args.validateRemediation) {
    const remediation = runLh0RemediationValidationSuite();
    console.log(JSON.stringify(remediation, null, 2));
    process.exit(remediation.readiness_for_corrective_live_execution ? 0 : 1);
  }

  const outputDir = args.outputDir ?? defaultOutputDir(
    args.executeLive ? 'issue201-lh0-live' : 'issue201-lh0-apparatus',
  );

  if (args.executeConsumerValueVerification) {
    const consumerValue = runLh0ConsumerValueValidationSuite();
    if (!consumerValue.readiness_for_consumer_value_qualification) {
      console.error(JSON.stringify({ error: 'LH-0 consumer-value validation failed', consumerValue }, null, 2));
      process.exit(3);
    }
    const outputDir = args.outputDir ?? defaultOutputDir('issue201-lh0-consumer-value-verification');
    const report = await executeLh0ConsumerValueVerificationCampaign({ outputDir });
    console.log(JSON.stringify({
      schema: 'issue201_lh0_consumer_value_verification_run_v1',
      output_dir: outputDir,
      candidate_sha: report.candidate_sha,
      pass_fail_matrix: report.pass_fail_matrix,
      lh1a_readiness: report.lh1a_readiness,
      t5_semantic_adjudication: report.t5_semantic_adjudication,
      counterfactual_interpretation: report.counterfactual_interpretation,
    }, null, 2));
    process.exit(0);
  }

  if (args.executeTurnAlignedVerification) {
    const timing = runLh0TimingValidationSuite();
    if (!timing.readiness_for_turn_aligned_qualification) {
      console.error(JSON.stringify({ error: 'LH-0 timing validation failed', timing }, null, 2));
      process.exit(3);
    }
    const outputDir = args.outputDir ?? defaultOutputDir('issue201-lh0-turn-aligned-verification');
    const report = await executeLh0TurnAlignedVerificationCampaign({ outputDir });
    console.log(JSON.stringify({
      schema: 'issue201_lh0_turn_aligned_verification_run_v1',
      output_dir: outputDir,
      candidate_sha: report.candidate_sha,
      pass_fail_matrix: report.pass_fail_matrix,
      lh1a_readiness: report.lh1a_readiness,
      counterfactual_interpretation: report.counterfactual_interpretation,
    }, null, 2));
    process.exit(0);
  }

  if (args.executeFinalQualification) {
    const semantic = runLh0SemanticValidationSuite();
    if (!semantic.readiness_for_final_qualification) {
      console.error(JSON.stringify({ error: 'LH-0 semantic validation failed', semantic }, null, 2));
      process.exit(3);
    }
    const outputDir = args.outputDir ?? defaultOutputDir('issue201-lh0-final-qualification');
    const report = await executeLh0FinalQualificationCampaign({ outputDir });
    console.log(JSON.stringify({
      schema: 'issue201_lh0_final_qualification_run_v1',
      output_dir: outputDir,
      candidate_sha: report.candidate_sha,
      pass_fail_matrix: report.pass_fail_matrix,
      lh1a_readiness: report.lh1a_readiness,
      counterfactual_interpretation: report.counterfactual_interpretation,
    }, null, 2));
    process.exit(0);
  }

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
