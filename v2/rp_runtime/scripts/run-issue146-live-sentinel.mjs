/**
 * Issue #146 bounded live Storyteller orientation→assessment binding sentinel (single attempt).
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import { LIVE_INFERENCE_TRANSPORT_PROMPT } from '../src/lib/live-inference-prompts.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { startDomainApi } from '../tests/helpers/domain-api.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');
const CANDIDATE_SHA = process.env.ISSUE146_CANDIDATE_SHA ?? 'unknown';

function loadAttempt(evidenceRoot, sessionId, evidenceId) {
  if (!sessionId || !evidenceId) return null;
  const attemptPath = path.join(evidenceRoot, sessionId, 'attempts', `${evidenceId}.json`);
  if (!fs.existsSync(attemptPath)) return null;
  return JSON.parse(fs.readFileSync(attemptPath, 'utf8'));
}

function packageUsefulness(packagePayload) {
  const observations = packagePayload?.observations ?? [];
  const opportunities = packagePayload?.progression_opportunities ?? [];
  return observations.length > 0 || opportunities.length > 0;
}

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    throw new Error('DEEPSEEK_API_KEY not set');
  }

  const gateRoot = path.join(
    REPO_ROOT,
    'data',
    'issue146_live_sentinel',
    new Date().toISOString().replace(/[:.]/g, '-'),
  );
  const sessionsDir = path.join(gateRoot, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const previous = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
    HG_EXECUTION_EVIDENCE_DIR: process.env.HG_EXECUTION_EVIDENCE_DIR,
  };
  process.env.HG_DATA_DIR = gateRoot;
  process.env.HG_EXECUTION_EVIDENCE = 'on';
  process.env.HG_EXECUTION_EVIDENCE_DIR = path.join(gateRoot, 'execution_evidence');
  fs.mkdirSync(process.env.HG_EXECUTION_EVIDENCE_DIR, { recursive: true });

  const host = await startDomainApi(undefined, { sessionsDir });
  const api = createDomainApiClient(host.baseUrl);
  const { ctx, orchestrator } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
    inference: {
      mountDeepSeek: true,
      defaultProfile: deepseekInferenceProfile({ reasoningEffort: 'low' }),
    },
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl: host.baseUrl },
    session: { mode: 'create', cast: ['Mara', 'Jon'] },
    skipPlotCognitionOrchestration: true,
    storytellerAllowDeterministicFallback: false,
    roleProfiles: {
      storyteller: deepseekInferenceProfile({ reasoningEffort: 'low' }),
      director: deepseekInferenceProfile({ reasoningEffort: 'low' }),
    },
    mockDirectorResponses: [JSON.stringify({
      next_actor: 'Mara',
      end_round: true,
      reason: 'Stop after storyteller probe.',
      environment_event: '',
      tension_shift: 'steady',
    })],
  });

  await ctx.fiber.dispose();
  await host.stop();

  const storyteller = result.storyteller ?? {};
  const evidenceRoot = process.env.HG_EXECUTION_EVIDENCE_DIR;
  const sessionId = result.hg_session_id;

  const orientationEvidence = loadAttempt(
    evidenceRoot,
    sessionId,
    storyteller.orientation_evidence_id
      ?? assessmentEvidence?.associations?.orientation_evidence_id,
  );
  const assessmentEvidence = loadAttempt(
    evidenceRoot,
    sessionId,
    storyteller.assessment_evidence_id,
  );

  let prepareContract = null;
  try {
    const sceneId = result.hg_scene_id;
    const roundId = result.hg_round_id;
    if (sceneId && roundId && orientationEvidence) {
      const orientFinalize = await api.finalizeStorytellerOrientation({
        hg_scene_id: sceneId,
        hg_round_id: roundId,
        inference_id: `inf-storyteller-${roundId}`,
        orientation_result: orientationEvidence.response?.assistant_text ?? '{}',
      });
      const bundle = {
        bundle_id: 'bundle-live-146',
        request_id: 'req-live-146',
        entries: [],
        satisfaction: { focus_questions: [] },
        degradation: { level: 'none', mode: 'none' },
        validity: { validity_scope: 'stage_current', bound_hg_round_id: roundId },
      };
      const prepared = await api.prepareStorytellerAssessmentContext({
        hg_scene_id: sceneId,
        inference_id: `inf-storyteller-${roundId}`,
        orientation: orientFinalize.orientation,
        bundle,
      });
      const instructions = (prepared.contributions ?? []).filter(
        (item) => item.source_kind === 'inference_instruction',
      );
      const structural = instructions.find((item) =>
        String(item.contribution_id).includes('storyteller_assessment_response_contract'));
      prepareContract = {
        manifest_id: prepared.manifest_id,
        contribution_ids: (prepared.contributions ?? []).map((item) => item.contribution_id),
        structural_provenance: structural?.provenance ?? null,
        structural_content: structural?.content ?? null,
      };
    }
  } catch {
    prepareContract = null;
  }

  const orientationAccepted = orientationEvidence?.decision?.storyteller_orientation?.accepted;
  const assessmentAccepted = assessmentEvidence?.decision?.storyteller_advisory?.assessment_accepted;
  const assessmentReason = assessmentEvidence?.decision?.storyteller_advisory?.assessment_reason;
  const advisoryPackage = result.storyteller?.package ?? null;
  const mappedItems = storyteller.mapped_preview?.director?.items_mapped ?? 0;
  const usefulness = packageUsefulness(advisoryPackage)
    || mappedItems > 0
    || (assessmentEvidence?.response?.assistant_text?.includes('progression_opportunities') ?? false);

  const report = {
    schema: 'issue146_live_sentinel_report_v1',
    candidate_sha: CANDIDATE_SHA,
    provider: 'deepseek-official',
    model: 'deepseek-v4-flash',
    reasoning: 'low',
    dsh_transport_prompt: LIVE_INFERENCE_TRANSPORT_PROMPT,
    prepare_contract: prepareContract,
    orientation_evidence_id: orientationEvidence?.evidence_id ?? null,
    assessment_evidence_id: assessmentEvidence?.evidence_id ?? null,
    raw_assessment_output: assessmentEvidence?.response?.assistant_text ?? null,
    orientation_finalize: {
      accepted: orientationAccepted ?? null,
      reason: orientationEvidence?.decision?.storyteller_orientation?.reason ?? null,
    },
    assessment_finalize: {
      accepted: assessmentAccepted ?? null,
      reason: assessmentReason ?? null,
    },
    storyteller_round: storyteller,
    advisory_package_structure: advisoryPackage
      ? {
          observations: advisoryPackage.observations?.length ?? 0,
          progression_opportunities: advisoryPackage.progression_opportunities?.length ?? 0,
        }
      : null,
    success_gate: {
      orientation_accepted: orientationAccepted === true,
      assessment_accepted: assessmentAccepted === true,
      storyteller_bound: storyteller.bound === true,
      operational_usefulness: usefulness,
      passed:
        orientationAccepted === true
        && assessmentAccepted === true
        && storyteller.bound === true
        && usefulness,
    },
    gate_root: gateRoot,
    evidence_anchors: {
      hg_session_id: sessionId ?? null,
      hg_round_id: result.hg_round_id ?? null,
      orientation_evidence_id: orientationEvidence?.evidence_id ?? null,
      assessment_evidence_id: assessmentEvidence?.evidence_id ?? null,
    },
  };

  const outPath = path.join(gateRoot, 'issue146-live-sentinel-report.json');
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  fs.writeFileSync(
    path.join(gateRoot, 'round-result.json'),
    `${JSON.stringify(result, null, 2)}\n`,
    'utf8',
  );

  for (const [key, value] of Object.entries(previous)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }

  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  if (!report.success_gate.passed) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
