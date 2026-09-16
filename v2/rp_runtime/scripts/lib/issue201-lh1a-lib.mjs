/**
 * Issue #201 LH-1A — apparatus library entry.
 */
import fs from 'node:fs';
import path from 'node:path';

import { gitSha, REPO_ROOT } from './issue201-lh0-lib.mjs';
import { buildCampaignPlan } from './issue201-lh1a-orchestrator.mjs';
import {
  buildLh1aAnswerKey,
  buildLh1aBlindPacket,
  validateLh1aBlindPacketIntegrity,
  writeLh1aBlindArtifacts,
} from './issue201-lh1a-blind-packet.mjs';
import { runLh1aApparatusValidationSuite } from './issue201-lh1a-validation-lib.mjs';
import { LH1A_SCHEMAS } from './issue201-lh1a-contract.mjs';

export { REPO_ROOT, gitSha, runLh1aApparatusValidationSuite, buildCampaignPlan };

export function runValidateLh1aApparatus({ outputDir } = {}) {
  const candidateSha = gitSha();
  const validation = runLh1aApparatusValidationSuite();
  const campaignPlan = buildCampaignPlan({ candidateSha });
  const rubricPath = path.join(REPO_ROOT, 'governance/records/issue201-lh1a-rubric/lh1a_blind_rubric_v1.json');
  const rubric = JSON.parse(fs.readFileSync(rubricPath, 'utf8'));
  const blindPacket = buildLh1aBlindPacket({ campaignPlan, rubric });
  const answerKey = buildLh1aAnswerKey(campaignPlan);
  const blindIntegrity = validateLh1aBlindPacketIntegrity(blindPacket);

  const report = {
    schema: LH1A_SCHEMAS.VALIDATION,
    campaign: 'lh1a_apparatus_deterministic_validation',
    candidate_sha: candidateSha,
    validation,
    campaign_plan: campaignPlan,
    blind_integrity: blindIntegrity,
    frozen_artifacts: validation.frozen_artifacts,
    live_execution_authorized: false,
    readiness_for_governance_execution_gate: validation.all_pass,
  };

  if (outputDir) {
    fs.mkdirSync(outputDir, { recursive: true });
    fs.writeFileSync(
      path.join(outputDir, 'issue201-lh1a-apparatus-validation-report.json'),
      `${JSON.stringify(report, null, 2)}\n`,
    );
    fs.writeFileSync(
      path.join(outputDir, 'issue201-lh1a-campaign-plan.json'),
      `${JSON.stringify(campaignPlan, null, 2)}\n`,
    );
    writeLh1aBlindArtifacts({ outputDir, packet: blindPacket, answerKey });
  }

  return report;
}
